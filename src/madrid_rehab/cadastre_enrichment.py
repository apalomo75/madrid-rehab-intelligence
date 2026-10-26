"""Immutable offline enrichment of the five accepted cadastral pilot partitions.

No viewer activation, network client, spatial assignment or energy/grant propagation.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import time
import zipfile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely as sh

from .cadastre_attributes import ATTRIBUTES, encoded, flat_attributes, iter_features, parse_feature
from .ingest import digest, save_json
from .normalize import reference
from .partial_cadastre import normalized_tree, encoded as legacy_encoded

CODES = ("28005", "28007", "28065", "28074", "28092")
ACCEPTED = Path("data/processed/cadastre/session_12_2_partial_validated_01")
RAW = Path("data/raw/cadastre/session_12_2_capture_01")
DEFAULT = Path("data/processed/cadastre/session_18_enriched_01")
POLICY = "documentary-enrichment-v1-overlap95-other05"
MIN_OVERLAP = 0.95
MAX_OTHER_OVERLAP = 0.05
STATES = ("absent", "present_empty", "declared", "invalid", "pending_interpretation")
EXTRA_STRINGS = [
    *[name for key in ATTRIBUTES for name in ("recovered_" + key, "recovered_" + key + "_state")],
    "attributes_json",
    "documentary_references_json",
    "address_references_json",
    "external_references_json",
    "source_declarations_json",
    "enrichment_source_zip",
    "enrichment_captured_at",
    "enrichment_rule",
    "enrichment_xml_normalized_sha256",
]


def code_hashes():
    return {
        str(p): digest(p)
        for p in [
            Path(__file__),
            Path(__file__).with_name("cadastre_attributes.py"),
            Path(__file__).with_name("sources.py"),
            Path(__file__).with_name("normalize.py"),
            Path(__file__).with_name("partial_cadastre.py"),
        ]
    }


def verify_inputs(code, accepted, raw):
    root = accepted / code
    manifest = json.loads((root / "manifest.json").read_text())
    parent = json.loads((accepted / "manifest.json").read_text())
    if digest(root / "manifest.json") != parent["outputs"][code + "/manifest.json"]:
        raise ValueError("Historical municipality manifest hash mismatch")
    if (
        manifest["quality"]["municipality_code"] != code
        or manifest.get("version") != "partial-cadastre-v1"
    ):
        raise ValueError("Wrong accepted snapshot contract")
    paths = [
        accepted / "manifest.json",
        root / "manifest.json",
        raw / code / "bu.zip",
        raw / code / "bu.zip.json",
        raw / code / "cp.zip.json",
    ]
    for name in ("bu.parquet", "bu_all.parquet", "cp.parquet", "cp_all.parquet"):
        path = root / name
        if digest(path) != manifest["outputs"][name]:
            raise ValueError("Historical product hash mismatch: " + str(path))
        paths.append(path)
    zip_path = raw / code / "bu.zip"
    if digest(zip_path) != manifest["inputs"][str(zip_path)]:
        raise ValueError("ZIP differs from the accepted capture")
    meta = json.loads(zip_path.with_suffix(".zip.json").read_text())
    if meta["sha256"] != digest(zip_path):
        raise ValueError("ZIP metadata hash mismatch")
    return {str(p): digest(p) for p in paths}, manifest, meta


def validate_partition_frames(bu, cp, cp_all, code):
    for frame in (bu, cp):
        if (
            not frame.municipality_code.eq(code).all()
            or not frame.selection_status.eq("accepted").all()
            or not frame.usable_geometry.all()
        ):
            raise ValueError("Cross-municipal or nonaccepted input")
    if not bu.building_id.is_unique or not cp.parcel_id.is_unique or not cp.parcel_ref14.is_unique:
        raise ValueError("Ambiguous accepted identity")
    if not cp_all.source_municipality_code.eq(code).all():
        raise ValueError("CP full input belongs to another municipality")
    if not bu.geometry_crs.eq("EPSG:25830").all() or not cp.geometry_crs.eq("EPSG:25830").all():
        raise ValueError("Unsupported or inconsistent CRS")


def classify_link(row):
    """Document first; no geometry can manufacture a reference or select another CP."""
    if not row.get("explicit_documentary_reference"):
        return "D", "no_usable_documentary_reference"
    if row.get("reference_integrity_issue"):
        return "B", row["reference_integrity_issue"]
    if row.get("cp_all_count", 0) > 1 or row.get("accepted_cp_count", 0) > 1:
        return "B", "ambiguous_cp_identity"
    if not row.get("cp_reference_normalized"):
        return "C", "unsupported_reference_format"
    if row.get("accepted_cp_count", 0) != 1:
        return "C", "cp_quarantined" if row.get("cp_all_count", 0) else "cp_not_observed"
    if not row.get("geometry_valid"):
        return "B", "invalid_or_unavailable_geometry"
    if row.get("intersection_ratio", 0) < MIN_OVERLAP:
        return "B", row.get("spatial_status", "insufficient_overlap")
    if row.get("other_cp_material_overlap_count", 0):
        return "B", "material_overlap_with_other_cp"
    return "A", "explicit_reference_unique_accepted_cp_and_geometry_concordant"


def resolve_links(links, bu, cp, cp_all, code):
    """Resolve exact documentary keys and audit all geometry without spatial reassignment."""
    lookup = cp.set_index("parcel_ref14").to_dict("index")
    originals = (
        cp_all.groupby("reference_original", dropna=True)
        .agg(
            count=("parcel_id", "size"),
            reasons=("selection_reason", lambda s: ";".join(sorted(set(s)))),
        )
        .to_dict("index")
    )
    bg = sh.from_wkt(bu.geometry_wkt.to_numpy(), on_invalid="ignore")
    cg = sh.from_wkt(cp.geometry_wkt.to_numpy(), on_invalid="ignore")
    index = dict(zip(bu.building_id, range(len(bu))))
    cpindex = dict(zip(cp.parcel_ref14, range(len(cp))))
    valid_bu = sh.is_valid(bg) & ~sh.is_empty(bg)
    valid_cp = sh.is_valid(cg) & ~sh.is_empty(cg)
    # These counts are diagnostics. The tree is never used to choose a target CP.
    tree = sh.STRtree(cg[valid_cp])
    valid_cp_indices = np.flatnonzero(valid_cp)
    safe_bg = bg.copy()
    safe_bg[~valid_bu] = None
    pairs = tree.query(safe_bg, predicate="intersects")
    pairs[1] = valid_cp_indices[pairs[1]]
    areas = sh.area(bg)
    intersection_areas = sh.area(sh.intersection(bg[pairs[0]], cg[pairs[1]]))
    ratios = np.divide(
        intersection_areas,
        areas[pairs[0]],
        out=np.zeros(len(intersection_areas)),
        where=areas[pairs[0]] > 0,
    )
    counts = np.bincount(pairs[0], minlength=len(bu))
    positive = np.bincount(pairs[0][intersection_areas > 0], minlength=len(bu))
    material = np.bincount(pairs[0][ratios > MAX_OTHER_OVERLAP], minlength=len(bu))
    rows = []
    for link in links:
        ref = link["cp_reference_original"]
        normalized = reference(ref)["parcel_ref14"] if ref else None
        # Only the exact normalized 14-character CP reference is supported here.
        if ref and reference(ref)["reference_kind"] != "parcel":
            normalized = None
        target = lookup.get(normalized)
        original = originals.get(ref, {})
        row = {
            **link,
            "municipality_code": code,
            "cp_reference_normalized": normalized,
            "accepted_cp_count": int(target is not None),
            "cp_all_count": original.get("count", 0),
            "cp_rejection_reasons": original.get("reasons", ""),
            "parcel_id": target["parcel_id"] if target else None,
            "accepted_cp_candidate_ids_json": encoded([target["parcel_id"]] if target else []),
            "geometry_valid": False,
            "intersection_ratio": None,
            "distance_to_declared_cp_m": None,
            "spatial_status": "cp_not_resolved",
            "record_version_dates_differ": None,
            "temporal_cause_established": False,
            "spatial_assignment_created": False,
            "physical_building_confirmed": False,
        }
        i = index[link["building_id"]]
        row.update(
            intersecting_cp_count=int(counts[i]),
            positive_area_cp_count=int(positive[i]),
            other_cp_material_overlap_count=0,
        )
        if target:
            j = cpindex[normalized]
            row["geometry_valid"] = bool(valid_bu[i] and valid_cp[j] and areas[i] > 0)
            row["cp_source_zip_sha256"] = target["source_zip_sha256"]
            row["cp_lifespan_begin"] = target.get("lifespan_begin")
            row["record_version_dates_differ"] = link.get("bu_lifespan_begin") != target.get(
                "lifespan_begin"
            )
            if row["geometry_valid"]:
                ratio = float(sh.area(sh.intersection(bg[i], cg[j])) / areas[i])
                distance = float(sh.distance(bg[i], cg[j]))
                row.update(
                    intersection_ratio=ratio,
                    distance_to_declared_cp_m=distance,
                    bu_geometry_multipart=sh.get_num_geometries(bg[i]) > 1,
                    cp_geometry_multipart=sh.get_num_geometries(cg[j]) > 1,
                    other_cp_material_overlap_count=int(material[i])
                    - int(ratio > MAX_OTHER_OVERLAP),
                )
                row["spatial_status"] = (
                    "contained"
                    if sh.covered_by(bg[i], cg[j])
                    else "disjoint"
                    if sh.disjoint(bg[i], cg[j])
                    else "boundary_touch"
                    if ratio == 0
                    else "partial_overlap"
                )
        # Missing geometry metrics must not silently pass the threshold.
        state, reason = classify_link({**row, "intersection_ratio": row["intersection_ratio"] or 0})
        row.update(
            link_class=state,
            validation_reason=reason,
            relation_validated=state == "A",
            cause_assessment="not_established_no_automatic_correction"
            if state == "B"
            else "not_applicable",
        )
        rows.append(row)
    result = pd.DataFrame(rows)
    return result


def relation_records(record, source):
    references = record["documentary_references"] or [
        dict(
            source_element="cadastralParcels/@xlink:href",
            source_qname=None,
            source_href=None,
            cp_reference_original=None,
            reference_state="absent",
        )
    ]
    distinct = {
        r["cp_reference_original"] for r in references if r["reference_state"] == "explicit"
    }
    external = set(record["external_references"])
    issue = (
        "multiple_documentary_cp_references"
        if len(distinct) > 1
        else "unusable_additional_documentary_reference"
        if distinct and any(r["reference_state"] != "explicit" for r in references)
        else "external_reference_disagrees"
        if external and distinct and external != distinct
        else None
    )
    return [
        {
            **r,
            **source,
            "building_id": record["building_id"],
            "source_feature_type": record["source_feature_type"],
            "documentary_occurrence": ordinal,
            "documentary_evidence_type": "GML_cadastralParcels_GetParcel_refcat",
            "explicit_documentary_reference": r["reference_state"] == "explicit",
            "reference_integrity_issue": issue,
            "bu_lifespan_begin": record["attributes"]["lifespan_begin"]["value"],
        }
        for ordinal, r in enumerate(references, 1)
    ]


def check_resume(directory, expected_inputs, fingerprint):
    meta = json.loads((directory / "manifest.json").read_text())
    if (
        meta.get("policy") != POLICY
        or meta.get("inputs") != expected_inputs
        or meta.get("code_sha256") != fingerprint
        or meta.get("validation_status") != "validated"
    ):
        raise ValueError("Resume incompatible with inputs/code/validation")
    for name, sha in meta["outputs"].items():
        if digest(directory / name) != sha:
            raise ValueError("Validated product altered: " + name)
    return meta


def enrich_municipality(code, output=DEFAULT, accepted=ACCEPTED, raw=RAW, resume=False):
    if code not in CODES:
        raise ValueError("Only the five reviewed pilot municipalities are authorized")
    output, accepted, raw = map(Path, (output, accepted, raw))
    inputs, original_manifest, metadata = verify_inputs(code, accepted, raw)
    fingerprint = code_hashes()
    destination = output / code
    if destination.exists():
        if not resume:
            raise FileExistsError(
                "Validated municipality exists; --resume verifies without overwriting"
            )
        return check_resume(destination, inputs, fingerprint)
    if (output / "manifest.json").exists():
        raise FileExistsError("Root snapshot finalized; use a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="." + code + "-", dir=output))
    save_json(stage / "work.json", dict(code=code, inputs=inputs, policy=POLICY))
    bu_path = accepted / code / "bu.parquet"
    bu, cp, cp_all = [
        pd.read_parquet(accepted / code / name)
        for name in ("bu.parquet", "cp.parquet", "cp_all.parquet")
    ]
    validate_partition_frames(bu, cp, cp_all, code)
    bu = bu.sort_values("building_id", kind="stable").reset_index(drop=True)
    accepted_rows = bu.set_index("building_id", drop=False).to_dict("index")
    schema = pq.read_schema(bu_path)
    for name in EXTRA_STRINGS:
        if name in schema.names:
            raise ValueError("Cannot overwrite original column")
        schema = schema.append(pa.field(name, pa.string()))
    source_schema = pa.schema(
        [
            (name, pa.string())
            for name in [
                "building_id",
                "source_feature_type",
                "source_zip",
                "source_zip_sha256",
                "source_gml_member",
                "source_ordinal",
                "source_normalized_sha256",
                "source_only_reason",
                "capture_source_municipality_code",
                "source_geometry_crs",
                *EXTRA_STRINGS,
            ]
        ]
    )
    observed, quality, seen, batch, source_batch, links, improved = (
        Counter(),
        Counter(),
        set(),
        [],
        [],
        [],
        Counter(),
    )
    examples = []
    duplicate_ids = []
    zip_path = raw / code / "bu.zip"
    with (
        zipfile.ZipFile(zip_path) as archive,
        pq.ParquetWriter(
            stage / "buildings_enriched.parquet", schema, compression="zstd"
        ) as writer,
        pq.ParquetWriter(
            stage / "source_only_objects.parquet", source_schema, compression="zstd"
        ) as other_writer,
    ):
        members = sorted(
            n
            for n in archive.namelist()
            if n.lower().endswith(("building.gml", "buildingpart.gml", "otherconstruction.gml"))
        )
        if len(members) != 3:
            raise ValueError("Expected three original BU GML members")
        for member in members:
            with archive.open(member) as stream:
                for ordinal, node in iter_features(stream):
                    record = parse_feature(node)
                    bid, typ = record["building_id"], record["source_feature_type"]
                    observed[typ] += 1
                    if bid in seen:
                        duplicate_ids.append(bid)
                    seen.add(bid)
                    normalized_sha = hashlib.sha256(
                        legacy_encoded(normalized_tree(node)).encode()
                    ).hexdigest()
                    flat = flat_attributes(record)
                    flat.update(
                        enrichment_source_zip=str(zip_path),
                        enrichment_captured_at=metadata.get("captured_at"),
                        enrichment_rule=POLICY,
                        enrichment_xml_normalized_sha256=normalized_sha,
                    )
                    if bid in accepted_rows:
                        original = accepted_rows[bid]
                        if (
                            original["source_feature_type"] != typ
                            or original["source_gml_member"] != member
                            or original["source_ordinal"] != ordinal
                            or original["normalized_sha256"] != normalized_sha
                        ):
                            raise ValueError(
                                "Original object/attributes/geometry identity mismatch: " + bid
                            )
                        row = {**original, **flat}
                        batch.append(row)
                        for key, attr in record["attributes"].items():
                            quality[(typ, key, attr["state"])] += 1
                        useful = [
                            key
                            for key in (
                                "floors_above",
                                "floors_below",
                                "height_below",
                                "height_above",
                                "official_area",
                                "condition",
                            )
                            if record["attributes"][key]["state"] == "declared"
                        ]
                        if useful:
                            improved[typ] += 1
                            # Prefer parts and Buildings, two each per municipality, with full provenance.
                            if sum(e["source_feature_type"] == typ for e in examples) < 2:
                                examples.append(
                                    {
                                        "building_id": bid,
                                        "source_feature_type": typ,
                                        "useful_fields": useful,
                                        "source_gml_member": member,
                                        "source_ordinal": ordinal,
                                        "source_zip_sha256": original["source_zip_sha256"],
                                        "attributes": record["attributes"],
                                    }
                                )
                        links.extend(
                            relation_records(
                                record,
                                dict(
                                    source_zip=str(zip_path),
                                    source_zip_sha256=original["source_zip_sha256"],
                                    source_gml_member=member,
                                    source_ordinal=ordinal,
                                    source_record_id=original["source_record_id"],
                                    captured_at=metadata.get("captured_at"),
                                ),
                            )
                        )
                    else:
                        source_batch.append(
                            dict(
                                building_id=bid,
                                source_feature_type=typ,
                                source_zip=str(zip_path),
                                source_zip_sha256=metadata["sha256"],
                                source_gml_member=member,
                                source_ordinal=str(ordinal),
                                source_normalized_sha256=normalized_sha,
                                source_only_reason="not_in_accepted_bu_snapshot",
                                capture_source_municipality_code=code,
                                source_geometry_crs=encoded(
                                    sorted(
                                        {e.get("srsName") for e in node.iter() if e.get("srsName")}
                                    )
                                ),
                                **flat,
                            )
                        )
                    if len(batch) >= 1000:
                        writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                        batch.clear()
                    if len(source_batch) >= 1000:
                        other_writer.write_table(
                            pa.Table.from_pylist(source_batch, schema=source_schema)
                        )
                        source_batch.clear()
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
        if source_batch:
            other_writer.write_table(pa.Table.from_pylist(source_batch, schema=source_schema))
    if duplicate_ids:
        raise ValueError(
            "Duplicate IDs in original GML; no representative selected: " + repr(duplicate_ids[:5])
        )
    if set(accepted_rows) - seen:
        raise ValueError("Accepted objects missing from original GML")
    if (
        observed["Building"] + observed["BuildingPart"]
        != original_manifest["quality"]["bu"]["observed"]
    ):
        raise ValueError("Original GML count differs from accepted capture")
    enriched = pd.read_parquet(stage / "buildings_enriched.parquet", columns=list(bu.columns))
    pd.testing.assert_frame_equal(
        bu, enriched.sort_values("building_id").reset_index(drop=True), check_like=False
    )
    relations = resolve_links(links, bu, cp, cp_all, code)
    relations.to_parquet(stage / "cp_bu_documentary_links.parquet", index=False, compression="zstd")
    issues = relations[relations.link_class.ne("A")]
    issues.to_parquet(stage / "cp_bu_link_issues.parquet", index=False, compression="zstd")
    quality_rows = []
    previous = {
        "current_use": "current_use",
        "construction_begin": "construction_begin",
        "construction_end": "construction_end",
        "dwellings": "dwellings_raw",
        "building_units": "building_units_raw",
    }
    for typ in sorted(bu.source_feature_type.unique()):
        group = bu[bu.source_feature_type.eq(typ)]
        for key in ATTRIBUTES:
            before = (
                int(
                    (
                        group[previous[key]].notna()
                        & group[previous[key]].astype(str).str.strip().ne("")
                    ).sum()
                )
                if key in previous
                else 0
            )
            for state in STATES:
                quality_rows.append(
                    dict(
                        municipality_code=code,
                        source_feature_type=typ,
                        attribute=key,
                        state=state,
                        objects=quality[(typ, key, state)],
                        denominator=len(group),
                        previous_nonempty=before,
                    )
                )
    pd.DataFrame(quality_rows).to_parquet(stage / "attribute_quality.parquet", index=False)
    valid_refs = set(relations.loc[relations.link_class.eq("A"), "cp_reference_normalized"])
    sensitivity = {
        str(threshold): int(
            (
                relations.accepted_cp_count.eq(1)
                & relations.geometry_valid
                & relations.intersection_ratio.ge(threshold)
            ).sum()
        )
        for threshold in (0.9, 0.95, 0.99, 1.0)
    }
    summary = dict(
        municipality_code=code,
        accepted_bu=len(bu),
        enriched_bu=len(enriched),
        accepted_types=bu.source_feature_type.value_counts().to_dict(),
        original_types=dict(observed),
        useful_attributes_recovered=dict(improved),
        unmatched_accepted_bu=len(set(accepted_rows) - seen),
        source_only_objects=sum(observed.values()) - len(bu),
        original_bu_duplicate_ids=len(duplicate_ids),
        documentary_links=len(relations),
        link_classes=relations.link_class.value_counts().to_dict(),
        link_reasons=relations.validation_reason.value_counts().to_dict(),
        accepted_cp_with_documentary_reference=relations.loc[
            relations.accepted_cp_count.eq(1), "cp_reference_normalized"
        ].nunique(),
        accepted_cp_with_validated_bu=len(valid_refs),
        resolved_accepted_links=int(relations.accepted_cp_count.eq(1).sum()),
        resolved_disjoint=int(
            (relations.accepted_cp_count.eq(1) & relations.spatial_status.eq("disjoint")).sum()
        ),
        spatial_status=relations.spatial_status.value_counts().to_dict(),
        overlap_sensitivity_before_other_checks=sensitivity,
    )
    save_json(stage / "summary.json", summary)
    save_json(stage / "examples.json", examples)
    # Rehash on completion; refuse publication if any input changed while reading.
    for path, sha in inputs.items():
        if digest(path) != sha:
            raise ValueError("Input changed during enrichment: " + path)
    outputs = {p.name: digest(p) for p in sorted(stage.iterdir()) if p.name != "work.json"}
    manifest = dict(
        version="cadastre-enriched-v1",
        policy=POLICY,
        municipality_code=code,
        validation_status="validated",
        inputs=inputs,
        code_sha256=fingerprint,
        outputs=outputs,
        summary=summary,
        minimum_bu_area_overlap=MIN_OVERLAP,
        maximum_other_cp_area_overlap=MAX_OTHER_OVERLAP,
        physical_building_identity_confirmed=False,
        energy_or_grant_propagation=False,
        public_exposure=False,
        activation_pointer_created=False,
    )
    save_json(stage / "manifest.json", manifest)
    (stage / "work.json").unlink()
    stage.rename(destination)
    return manifest


def run(output=DEFAULT, codes=CODES, accepted=ACCEPTED, raw=RAW, resume=False):
    output = Path(output)
    for code in sorted(set(codes)):
        start = time.perf_counter()
        meta = enrich_municipality(code, output, accepted, raw, resume)
        print(
            encoded(
                dict(code=code, seconds=round(time.perf_counter() - start, 3), **meta["summary"])
            ),
            flush=True,
        )
    # Per-municipality invocations can accumulate safely. Seal the root only once all five exist.
    if (
        all((output / code / "manifest.json").exists() for code in CODES)
        and not (output / "manifest.json").exists()
    ):
        save_json(
            output / "manifest.json",
            dict(
                version="cadastre-enriched-collection-v1",
                policy=POLICY,
                municipality_codes=list(CODES),
                outputs={
                    code + "/manifest.json": digest(output / code / "manifest.json")
                    for code in CODES
                },
                validation_status="validated",
                activation_pointer_created=False,
                public_exposure=False,
            ),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--municipality", choices=CODES, action="append")
    parser.add_argument("--accepted-dir", type=Path, default=ACCEPTED)
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run(args.output_dir, args.municipality or CODES, args.accepted_dir, args.raw_dir, args.resume)


if __name__ == "__main__":
    main()
