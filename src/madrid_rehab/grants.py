"""PRTR local: expedientes, relaciones sin importes y trazabilidad reproducible."""

import argparse
import json
import math
import re
import resource
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import shapely as sh
from pyproj import Transformer

from .ingest import digest

DEFAULT = Path("data/processed/grants/session_11_final_03")
SOURCE = Path("data/raw/subvenciones/prtr/concesiones_prtr_20261024.geojson")
URL = "https://visorrehabilitaprtrmadrid.coam.org/api/main.cgi?method=resum&pr=all"
VERSION = "prtr-v1"
MAPPING = {
    "expediente": "expediente_id",
    "pr": "programa",
    "pr_det": "subprograma",
    "imp_con": "importe_bruto",
    "catref": "referencia_catastral",
    "refs": "referencias_adicionales",
    "etapa": "etapa_administrativa",
    "age": "ano_construccion",
    "viviendas": "numero_viviendas",
    "viviendas_sup": "superficie",
    "sup_vivienda": "superficie_vivienda",
    "address": "direccion",
}
PROGRAMS = {
    "P1": "Rehabilitación a nivel de barrio",
    "P3": "Rehabilitación a nivel de edificio",
    "P4": "Mejora de eficiencia energética en viviendas",
    "P5": "Libro del edificio existente y proyectos de rehabilitación",
}


def write_json(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    )


def reference(value):
    raw = str(value or "").strip().upper()
    # Urban map sheets can include letters in the first seven positions.
    urban = r"[0-9A-Z]{7}[A-Z]{2}[0-9]{4}[A-Z]"
    rural = r"[0-9]{5}[A-Z][0-9]{8}"
    return raw[:14] if re.fullmatch(f"(?:{urban}|{rural})(?:[0-9]{4}[A-Z]{2})?", raw) else None


def cents(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            return None
        return int((amount * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize(document):
    if document.get("type") != "FeatureCollection":
        raise ValueError("Se requiere FeatureCollection")
    crs = document.get("crs", {}).get("properties", {}).get("name")
    if crs not in (None, "urn:ogc:def:crs:OGC:1.3:CRS84", "EPSG:4326"):
        raise ValueError("CRS no admitido: no interpretar coordenadas sin transformación")
    rows, relations, issues = [], [], []
    for position, feature in enumerate(document["features"], 1):
        p = feature["properties"]
        row = {target: p.get(original) for original, target in MAPPING.items()}
        row["source_row"] = position
        row["expediente_id"] = str(p.get("expediente") or "")
        row["programa"] = str(p.get("pr") or "").upper().replace("PR", "P", 1)
        row["importe_centimos"] = cents(p.get("imp_con"))
        row["importe_concedido"] = (
            None if row["importe_centimos"] is None else row["importe_centimos"] / 100
        )
        row["referencias_adicionales"] = json.dumps(p.get("refs"), ensure_ascii=False)
        row["raw_json"] = json.dumps(p, ensure_ascii=False, sort_keys=True)
        row.update(
            fecha_disponible=None,
            fecha_concesion=None,
            fecha_pago=None,
            tipo_edificio=None,
            datos_energeticos=None,
            municipio=None,
            origen=URL,
            fecha_captura="2026-10-24",
            fecha_actualizacion="2026-07-20",
            version=VERSION,
            fase="award" if p.get("etapa") == "APROBACIÓN CONCESIÓN" else "unknown",
            actuacion=PROGRAMS.get(row["programa"]),
        )
        geometry = feature.get("geometry") or {}
        xy = geometry.get("coordinates", [])
        valid = (
            geometry.get("type") == "Point"
            and len(xy) == 2
            and all(isinstance(v, (int, float)) and math.isfinite(v) for v in xy)
            and -180 <= xy[0] <= 180
            and -90 <= xy[1] <= 90
        )
        row.update(
            longitude=xy[0] if valid else None,
            latitude=xy[1] if valid else None,
            geometry_valid=valid,
        )
        flags = []
        if not valid:
            flags.append("invalid_point")
        elif not (-4.6 <= xy[0] <= -3.0 and 39.8 <= xy[1] <= 41.2):
            flags.append("outside_regional_envelope_not_boundary_test")
        if row["importe_centimos"] is None or row["importe_centimos"] < 0:
            flags.append("invalid_amount")
        elif row["importe_centimos"] > 100_000_000:
            flags.append("amount_over_1m_review")
        if row["programa"] not in PROGRAMS:
            flags.append("unknown_program")
        if row["fase"] == "unknown":
            flags.append("unknown_phase")
        for col, lower, upper in [
            ("ano_construccion", 1600, 2026),
            ("numero_viviendas", 1, 1000),
            ("superficie", 10, 20000),
            ("superficie_vivienda", 10, 500),
        ]:
            v = row[col]
            if v is None or not isinstance(v, (int, float)) or not lower <= v <= upper:
                flags.append(col + "_review")
        additional = p.get("refs")
        if not isinstance(additional, list):
            flags.append("invalid_refs_list")
            additional = []
        literals = [p.get("catref")] + additional
        refs = {}
        for literal in literals:
            ref = reference(literal)
            if ref is None:
                flags.append("invalid_reference")
            refs[str(literal)] = ref
        # Preserve every distinct literal, deduplicate a relation by canonical RC14.
        canonical = sorted({r for r in refs.values() if r})
        row["refs_literal_multiple"] = len(additional) > 1
        row["multiparcela"] = len(canonical) > 1
        row["reference_count"] = len(canonical)
        row["address_madrid_declared"] = str(p.get("address") or "").endswith(" MADRID (MADRID)")
        if reference(p.get("catref")) not in {reference(r) for r in additional}:
            flags.append("primary_not_in_refs")
        row["calidad"] = "|".join(sorted(set(flags)))
        rows.append(row)
        for ref in canonical:
            relations.append(
                {
                    "expediente_id": row["expediente_id"],
                    "parcel_ref14": ref,
                    "reference_literals": json.dumps([v for v, r in refs.items() if r == ref]),
                }
            )
        for flag in sorted(set(flags)):
            issues.append(
                {"expediente_id": row["expediente_id"], "source_row": position, "issue": flag}
            )
    frame = pd.DataFrame(rows)
    duplicate = frame.expediente_id.duplicated(keep=False) | frame.expediente_id.eq("")
    for r in frame[duplicate].itertuples():
        issues.append(
            {
                "expediente_id": r.expediente_id,
                "source_row": r.source_row,
                "issue": "identity_conflict",
            }
        )
    frame["identity_conflict"] = duplicate
    return (
        frame,
        pd.DataFrame(
            relations, columns=["expediente_id", "parcel_ref14", "reference_literals"]
        ).drop_duplicates(["expediente_id", "parcel_ref14"]),
        pd.DataFrame(issues, columns=["expediente_id", "source_row", "issue"]),
    )


def match_parcels(grants, links, cp):
    counts = cp.groupby("parcel_ref14").size()
    unique = cp[cp.parcel_ref14.map(counts).eq(1)].set_index("parcel_ref14")
    out = links.copy()
    out["cp_rows"] = out.parcel_ref14.map(counts).fillna(0).astype(int)
    out["district_code"] = out.parcel_ref14.map(unique.district_code)
    out["distance_m"] = float("nan")
    out["match_status"] = "regional_cp_pending"
    out.loc[out.cp_rows.gt(1), "match_status"] = "ambiguous_cp"
    points = grants.drop_duplicates("expediente_id").set_index("expediente_id")
    transform = Transformer.from_crs(4326, 25830, always_xy=True)
    for idx, link in out[out.cp_rows.eq(1)].iterrows():
        g = points.loc[link.expediente_id]
        parcel = unique.loc[link.parcel_ref14]
        status = "candidate"
        if g.geometry_valid and parcel.geometry_crs == "EPSG:25830" and parcel.usable_geometry:
            point = sh.Point(*transform.transform(g.longitude, g.latitude))
            distance = point.distance(sh.from_wkt(parcel.geometry_wkt))
            out.at[idx, "distance_m"] = distance
            status = "confirmed" if distance <= 100 else "contradictory"
        if g.identity_conflict:
            status = "identity_conflict"
        out.at[idx, "match_status"] = status
    return out


def assign_territory(grants, links):
    out = grants.copy()
    out["territorial_quality"] = "unassigned"
    out["municipality_code"] = None
    out["district_code"] = None
    for idx, row in out.iterrows():
        subset = links[links.expediente_id.eq(row.expediente_id)]
        confirmed = subset[subset.match_status.eq("confirmed")]
        if subset.match_status.isin(["contradictory", "identity_conflict"]).any():
            out.at[idx, "territorial_quality"] = "contradictory"
        elif not confirmed.empty:
            if row.direccion and not row.address_madrid_declared:
                out.at[idx, "territorial_quality"] = "contradictory"
                continue
            out.at[idx, "territorial_quality"] = "madrid_confirmed"
            out.at[idx, "municipality_code"] = "28079"
            out.at[idx, "municipio"] = "Madrid"
            districts = confirmed.district_code.dropna().unique()
            # Do not allocate an award to one district if some relations are unresolved.
            if len(districts) == 1 and len(confirmed) == len(subset):
                out.at[idx, "district_code"] = districts[0]
        elif row.geometry_valid:
            out.at[idx, "territorial_quality"] = "territorial_candidate"
    return out


def aggregate(frame, keys):
    eligible = frame[~frame.identity_conflict].drop_duplicates("expediente_id")
    return (
        eligible.groupby(keys, dropna=False)
        .agg(
            expedientes=("expediente_id", "nunique"),
            importe_centimos=("importe_centimos", "sum"),
            mediana_importe=("importe_concedido", "median"),
            viviendas_declaradas=("numero_viviendas", "sum"),
            geometries_valid=("geometry_valid", "sum"),
            multiparcela=("multiparcela", "sum"),
            referencias_validas=("reference_count", lambda s: int(s.gt(0).sum())),
        )
        .reset_index()
    )


def run(source=SOURCE, output=DEFAULT, municipalities=None, municipalities_manifest=None):
    output, source = Path(output), Path(source)
    if output.exists():
        raise FileExistsError("Usar un directorio nuevo: " + str(output))
    start = time.perf_counter()
    source_hash = digest(source)
    document = json.loads(source.read_text())
    parsed = time.perf_counter()
    grants, links, quality = normalize(document)
    normalized = time.perf_counter()
    cp_path = Path("data/processed/session_2/parcels_audited.parquet")
    cp_hash = digest(cp_path)
    city = json.loads(Path("data/processed/session_7_final/manifest.json").read_text())
    if city["inputs"]["parcels_audited"] != cp_hash:
        raise ValueError("CP municipal incompatible")
    cp = pd.read_parquet(cp_path)
    links = match_parcels(grants, links, cp)
    grants = assign_territory(grants, links)
    regional_catalog = None
    if municipalities is not None:
        from .regional import load_official_boundaries, reconcile_municipalities

        if municipalities_manifest is None:
            raise ValueError("Manifiesto oficial municipal obligatorio")
        regional_catalog = load_official_boundaries(municipalities, municipalities_manifest)
        grants = reconcile_municipalities(grants, links, regional_catalog)
    matched = time.perf_counter()
    output.mkdir(parents=True)
    tables = {
        "grants": grants,
        "grant_parcel_links": links,
        "grant_quality": quality,
        "grant_municipality_links": grants[
            ["expediente_id", "municipality_code", "municipio", "territorial_quality"]
        ],
        "program_summary": aggregate(grants, ["programa"]),
        "municipality_summary": aggregate(
            grants, ["municipality_code", "territorial_quality", "programa"]
        ),
        "district_summary": aggregate(grants, ["district_code", "programa"]),
    }
    # Registry only contains verified official identities, never 178 invented rows.
    tables["municipalities"] = pd.DataFrame(
        [
            dict(
                municipality_code="28079",
                name="Madrid",
                province="Madrid",
                autonomous_community="Comunidad de Madrid",
                cp_available=True,
                bu_available=True,
                ceee_available=True,
                prtr_available=True,
                municipal_events_available=True,
                processing_status="municipal_snapshot",
                cp_path=str(cp_path),
                geometry_available=False,
                area_km2=None,
                source="Catastro INSPIRE CP; captura municipal sesión 7",
            )
        ]
    )
    if regional_catalog is not None:
        tables["municipalities"] = regional_catalog
    features_path = Path("data/processed/session_7_final/parcel_features.parquet")
    if digest(features_path) != city["outputs"]["parcel_features.parquet"]:
        raise ValueError("Contextos municipales alterados")
    features = pd.read_parquet(features_path)
    confirmed = links[links.match_status.eq("confirmed")].copy()
    profiles = confirmed.merge(features, on="parcel_ref14", how="left", suffixes=("", "_context"))
    profiles = profiles.merge(
        grants[["expediente_id", "programa", "subprograma"]], on="expediente_id", how="left"
    )
    profiles["perfil_rehabilitacion_p3"] = profiles.programa.eq("P3")
    profiles["perfil_proyecto_p5"] = profiles.programa.eq("P5") & profiles.subprograma.isin(
        ["pr5_Proyecto", "pr5_Todo"]
    )
    profiles["perfil_energia_prtr"] = profiles.energy_available
    admin_path = Path("data/processed/administrative_events/session_10_final_01")
    admin_manifest = json.loads((admin_path / "manifest.json").read_text())
    if admin_manifest["cp_sha256"] != cp_hash:
        raise ValueError("Eventos administrativos con CP incompatible")
    event_frames = []
    for code in range(1, 22):
        path = admin_path / "districts" / f"{code:02}" / "events.parquet"
        if digest(path) != admin_manifest["outputs"][str(path.relative_to(admin_path))]:
            raise ValueError("Partición administrativa alterada")
        a = pd.read_parquet(
            path, columns=["event_id", "event_type", "parcel_ref14", "match_status"]
        )
        event_frames.append(a[a.match_status.eq("confirmed")])
    events = pd.concat(event_frames)
    cooccurrences = confirmed[["expediente_id", "parcel_ref14"]].merge(
        events[["event_id", "event_type", "parcel_ref14"]], on="parcel_ref14"
    )
    tables["grant_administrative_cooccurrences"] = cooccurrences
    for kind in ["order", "license", "declaration", "ite_pending", "iee_pending"]:
        observed = set(cooccurrences.loc[cooccurrences.event_type.eq(kind), "parcel_ref14"])
        profiles["perfil_" + kind + "_prtr"] = profiles.parcel_ref14.isin(observed)
    tables["grant_parcel_profiles"] = profiles
    for name, frame in tables.items():
        frame.to_parquet(output / (name + ".parquet"), index=False)
    if digest(source) != source_hash:
        raise ValueError("Original cambió durante la ejecución")
    manifest = dict(
        version=VERSION,
        source_url=URL,
        source_file=str(source),
        source_sha256=source_hash,
        source_bytes=source.stat().st_size,
        source_crs=document.get("crs"),
        source_update="2026-07-20",
        source_update_evidence="Metadato del visor indicado en la entrega; no figura en GeoJSON",
        capture_date="2026-10-24",
        cp_sha256=cp_hash,
        admin_manifest_sha256=digest(admin_path / "manifest.json"),
        records=len(grants),
        unique_expedientes=grants.expediente_id.nunique(),
        parcel_links=len(links),
        unique_refs=links.parcel_ref14.nunique(),
        multiparcela=int(grants.multiparcela.sum()),
        identity_conflicts=int(grants.identity_conflict.sum()),
        territorial_counts=grants.territorial_quality.value_counts().to_dict(),
        match_counts=links.match_status.value_counts().to_dict(),
        program_totals=tables["program_summary"].to_dict("records"),
        fields_null={
            k: int(v)
            for k, v in pd.DataFrame([f["properties"] for f in document["features"]])
            .isna()
            .sum()
            .items()
        },
        quality_counts=quality.issue.value_counts().to_dict(),
        field_mapping=MAPPING,
        license="unverified_local_only",
        public_exposure_default=False,
        boundaries_available=regional_catalog is not None,
        boundaries_sha256=digest(municipalities) if municipalities else None,
        outputs={p.name: digest(p) for p in sorted(output.glob("*.parquet"))},
    )
    write_json(output / "grant_source_manifest.json", manifest)
    end = time.perf_counter()
    write_json(
        output / "benchmark.json",
        dict(
            parse_s=parsed - start,
            normalize_s=normalized - parsed,
            matching_s=matched - normalized,
            analytics_write_s=end - matched,
            total_s=end - start,
            max_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        ),
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--municipalities", type=Path)
    parser.add_argument("--municipalities-manifest", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.input, args.output_dir, args.municipalities, args.municipalities_manifest),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
