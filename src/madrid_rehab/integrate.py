"""Cruce de identidades; nunca agrega calificaciones al edificio."""

import hashlib
import json
import math

import pandas as pd

from .normalize import address_key, certification_scope, reference, split_references, text_key


LINK_COLUMNS = [
    "certificate_row_id", "source_record_id", "certificate_code_raw", "reference_position",
    "reference_raw", "reference_normalized", "reference_kind", "reference_format_valid",
    "parcel_ref14", "property_ref20", "checksum_status", "address_raw", "address_normalized",
    "municipality_raw", "certificate_scope_raw", "certificate_scope", "certificate_date_raw",
    "energy_grade_raw", "emissions_grade_raw", "energy_consumption_raw", "emissions_raw",
    "parcel_exists", "property_exists", "match_status", "match_level", "pending_reason",
    "candidate_building_ids", "building_id", "x", "y", "coordinate_crs", "coordinate_scope",
]


def _finite_point(row):
    if row.get("coordinate_crs") != "EPSG:25830":
        return False
    try:
        x, y = float(row["x"]), float(row["y"])
        # Madrid municipality envelope, intentionally generous; not a district assignment.
        return math.isfinite(x) and math.isfinite(y) and 350000 < x < 500000 and 4400000 < y < 4550000
    except (ValueError, TypeError, KeyError):
        return False


def integrate(records, parcels, buildings, properties, resource_id, scope_map=None):
    parcel_index = {}
    for row in parcels:
        parcel_index.setdefault(row.get("parcel_ref14"), []).append(row)
    property_refs = {p["property_ref20"] for p in properties if p.get("authority_confirmed")}
    building_index = {}
    for building in buildings:
        if building.get("building_id"):
            building_index.setdefault(building.get("parcel_ref14"), set()).add(building["building_id"])
    output = []
    for position, record in enumerate(records):
        # Resource + _id denotes a source row, NOT necessarily one distinct certificate.
        source_id = str(record.get("_id", f"position:{position}"))
        cert_id = hashlib.sha256(f"{resource_id}:{source_id}".encode()).hexdigest()[:24]
        for ref_position, raw in enumerate(split_references(record.get("edif_refcat"))):
            ref = reference(raw)
            candidates = parcel_index.get(ref["parcel_ref14"], [])
            property_exists = ref["property_ref20"] in property_refs
            parcel_exists = len(candidates) == 1
            if not ref["reference_format_valid"]:
                status, level, reason = "pending_validation", None, "invalid_or_unsupported_reference"
            elif not parcel_exists:
                status, level, reason = "pending_validation", None, (
                    "ambiguous_parcel_response" if len(candidates) > 1 else "parcel_not_confirmed"
                )
            elif ref["reference_kind"] == "property" and not property_exists:
                status, level, reason = "pending_validation", "parcel_candidate", "property_not_confirmed"
            else:
                status, level, reason = "matched", (
                    "property_identity_parcel_location" if property_exists else "parcel"
                ), None
            point = candidates[0] if parcel_exists and _finite_point(candidates[0]) else {}
            output.append({
                "certificate_row_id": cert_id, "source_record_id": source_id,
                "certificate_code_raw": record.get("edif_codreg"), "reference_position": ref_position,
                **ref,
                "address_raw": record.get("edif_direc"),
                "address_normalized": address_key(record.get("edif_direc")),
                "municipality_raw": record.get("edif_muni"),
                "certificate_scope_raw": record.get("edif_tipo"),
                "certificate_scope": certification_scope(record.get("edif_tipo"), scope_map),
                "certificate_date_raw": record.get("edif_fecha"),
                "energy_grade_raw": record.get("cal_norenovglobal"),
                "emissions_grade_raw": record.get("cal_co2global"),
                "energy_consumption_raw": record.get("norenov_global"),
                "emissions_raw": record.get("norenov_co2global"),
                "parcel_exists": parcel_exists, "property_exists": property_exists,
                "match_status": status, "match_level": level, "pending_reason": reason,
                "candidate_building_ids": json.dumps(sorted(building_index.get(ref["parcel_ref14"], []))),
                # A shared parcel (even one BU object) is insufficient evidence of physical block.
                "building_id": None,
                "x": point.get("x") if status == "matched" else None,
                "y": point.get("y") if status == "matched" else None,
                "coordinate_crs": point.get("coordinate_crs") if status == "matched" else None,
                "coordinate_scope": point.get("coordinate_scope") if status == "matched" else None,
            })
    frame = pd.DataFrame(output, columns=LINK_COLUMNS)
    for column in ["reference_format_valid", "parcel_exists", "property_exists"]:
        frame[column] = frame[column].astype("boolean")
    for column in ["x", "y"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Float64")
    frame["reference_position"] = frame["reference_position"].astype("Int64")
    for column in frame.columns.difference([
        "reference_format_valid", "parcel_exists", "property_exists", "x", "y", "reference_position"
    ]):
        frame[column] = frame[column].astype("string")
    return frame


def quality(frame, records, buildings):
    matched = frame[frame.match_status == "matched"]
    fully_matched = frame.groupby("certificate_row_id").match_status.agg(lambda x: (x == "matched").all())
    count = len(records)
    return {
        "source_rows_processed": count,
        "reference_rows": len(frame),
        "references_valid_format": int(frame.reference_format_valid.sum()),
        "unique_references_valid_format": int(frame.loc[frame.reference_format_valid, "reference_normalized"].nunique()),
        "checksum_validated_count": 0,
        "unique_authority_confirmed_properties": int(frame.loc[frame.property_exists, "property_ref20"].nunique()),
        "unique_confirmed_parcels": int(frame.loc[frame.parcel_exists, "parcel_ref14"].nunique()),
        "matched_reference_rows": len(matched),
        "reference_match_percent": round(100 * len(matched) / len(frame), 2) if len(frame) else None,
        "fully_matched_source_rows": int(fully_matched.sum()),
        "source_row_match_percent": round(100 * fully_matched.sum() / count, 2) if count else None,
        "geolocated_parcels": int(matched.loc[matched.x.notna(), "parcel_ref14"].nunique()),
        "building_objects_with_geometry_structural_only": len({
            b["building_id"] for b in buildings
            if b.get("building_id") and b.get("building_geometry_status") == "structural_only"
        }),
        "certificate_buildings_reliably_geolocated": 0,
        "scope_counts_source_rows": frame.drop_duplicates("certificate_row_id").certificate_scope.value_counts().to_dict(),
        "pending_reasons": frame.pending_reason.dropna().value_counts().to_dict(),
        "duplicate_source_row_ids": count - len({str(r.get('_id')) for r in records}),
        "repeated_certificate_codes": _repeated_codes(records),
        "unknown_scope_source_rows": int((frame.drop_duplicates("certificate_row_id").certificate_scope == "unknown").sum()),
        "invalid_energy_grades_source_rows": sum(
            r.get("cal_norenovglobal") is not None
            and text_key(r["cal_norenovglobal"]).strip() not in list("ABCDEFG") for r in records
        ),
    }


def _repeated_codes(records):
    codes = [r["edif_codreg"] for r in records if r.get("edif_codreg")]
    return len(codes) - len(set(codes))


def schema_profile(records, declared_fields):
    """Tipos JSON observados y tipos pandas, sin confundirlos con el diccionario web."""
    frame = pd.DataFrame(records)
    fields = {f["id"]: f.get("type") for f in declared_fields}
    return {str(column): {
        "source_declared_type": fields.get(column),
        "json_types": sorted({type(r.get(column)).__name__ for r in records}),
        "pandas_inferred_dtype": str(frame[column].dtype),
        "nulls": int(frame[column].isna().sum()),
    } for column in frame}
