"""Sesión 7: productos municipales y distritales reproducibles, exclusivamente locales."""

import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
import pandas as pd
import shapely as sh
from pyproj import Transformer

from . import districts as boundary_source
from .analytics import coverage, exploratory_score
from .city_audit import district_summary, quality_links, reconcile, source_coverage
from .event_features import aggregate_event_features, load_event_snapshot
from .features import parcel_features, construction_years
from .ingest import digest
from .profiles import add_profiles, group_comparison, sensitivity_analysis
from .territory import add_grid, grid_code, resolve_district, validate_districts

VERSION = "session7-v1"
INPUTS = (
    "parcels_audited",
    "buildings_audited",
    "certificates_integrated",
    "certificate_reference_links",
    "districts",
    "building_certificate_contexts",
)
OBSERVATIONS = [
    "record_id",
    "parcel_ref14",
    "certificate_scope",
    "cal_norenovglobal",
    "date_parsed",
    "year",
]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def load_inputs(root):
    root = Path(root)
    manifest_hash = digest(root / "quality_metrics.json")
    declared = json.loads((root / "quality_metrics.json").read_text())["outputs"]
    hashes = {}
    for name in INPUTS:
        path = root / (name + ".parquet")
        hashes[name] = digest(path)
        if hashes[name] != declared[path.name]["sha256"]:
            raise ValueError(f"Entrada modificada: {name}")
    frames = {name: pd.read_parquet(root / (name + ".parquet")) for name in INPUTS}
    validate_districts(frames["districts"])
    return frames, hashes, manifest_hash


def display_geometries(frame, kind, zone_by_reference=None):
    """Copia visual vectorizada; WKT originales permanecen en sesión 2."""
    frame = frame.loc[frame.usable_geometry].copy().reset_index(drop=True)
    geometries = sh.from_wkt(frame.geometry_wkt.to_numpy(), on_invalid="ignore")
    simplified = sh.simplify(geometries, 0.25, preserve_topology=True)
    original_area = sh.area(geometries)
    change = np.abs(sh.area(simplified) - original_area) / original_area
    fallback = ~sh.is_valid(simplified) | sh.is_empty(simplified) | (change > 0.01)
    simplified[fallback] = geometries[fallback]
    transformer = Transformer.from_crs(25830, 4326, always_xy=True)
    projected = sh.transform(simplified, transformer.transform, interleaved=False)
    frame["geometry_geojson"] = sh.to_geojson(projected)
    frame["display_area_change_percent"] = (
        100 * np.abs(sh.area(simplified) - original_area) / original_area
    )
    points = sh.point_on_surface(geometries)
    frame["map_zone"] = [grid_code(x, y) for x, y in zip(sh.get_x(points), sh.get_y(points))]
    if zone_by_reference is not None:
        mapped = frame.parcel_ref14.map(zone_by_reference)
        frame["map_zone"] = mapped.where(mapped.notna(), frame.map_zone)
    common = [
        "parcel_ref14",
        "record_id",
        "district_code",
        "geometry_geojson",
        "map_zone",
        "crosses_district_boundary",
        "source_url",
        "captured_at",
        "source_date",
        "display_area_change_percent",
        "usable_geometry",
    ]
    if kind == "bu":
        frame = construction_years(frame)
        common += [
            "building_id",
            "current_use",
            "construction_oldest_year",
            "construction_newest_year",
            "dwellings_raw",
            "building_units_raw",
        ]
    return (
        frame[[column for column in common if column in frame]]
        .sort_values("record_id")
        .reset_index(drop=True)
    )


def observations_for(energy, features):
    return energy.loc[energy.parcel_ref14.isin(features.parcel_ref14), OBSERVATIONS].reset_index(
        drop=True
    )


def analytic_audit(features, observations):
    grades = features[[f"ceee_grade_{g}" for g in "ABCDEFG"]].sum(axis=1)
    expected = (
        observations.groupby("parcel_ref14")
        .record_id.nunique()
        .reindex(features.parcel_ref14, fill_value=0)
    )
    share = features[[f"ceee_grade_{g}" for g in "EFG"]].sum(axis=1) / grades.replace(
        0, float("nan")
    )
    actual = features.ceee_efg_share_observed
    checks = {
        "unique_parcels": features.parcel_ref14.is_unique,
        "record_counts_reconciled": expected.tolist() == features.ceee_records_observed.tolist(),
        "grade_denominator_reconciled": grades.eq(features.ceee_valid_grade_count).all(),
        "efg_reconciled": ((share - actual).abs().lt(1e-12) | (share.isna() & actual.isna())).all(),
        "no_global_ipr": not features.global_ipr_eligible.any(),
    }
    if not all(checks.values()):
        raise ValueError(f"Auditoría distrital fallida: {checks}")
    return {
        "checks": {k: bool(v) for k, v in checks.items()},
        "record_parcel_pairs": len(observations),
        "unique_certificate_records": int(observations.record_id.nunique()),
        "sparse_observation_parcels": int(features.ceee_valid_grade_count.between(1, 2).sum()),
        "mixed_scope_parcels": int(features.ceee_scope_count.gt(1).sum()),
    }


def write_analytics(root, features, observations, extra=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    features = features.reset_index(drop=True)
    features.to_parquet(root / "parcel_features.parquet", index=False)
    observations.to_parquet(root / "energy_observations.parquet", index=False)
    sensitivity_analysis(features, exploratory_score).to_parquet(
        root / "sensitivity_summary.parquet", index=False
    )
    group_comparison(features, observations=observations).to_csv(
        root / "construction_periods.csv", index=False
    )
    write_json(root / "coverage.json", coverage(features))
    audit = analytic_audit(features, observations)
    if extra:
        audit.update(extra)
    write_json(root / "audit.json", audit)


def check_chamberi(root, features, observations, display_ids):
    root = Path(root)
    if not (root / "manifest.json").exists():
        return {"status": "unavailable", "reason": "Captura histórica no presente"}
    manifest = json.loads((root / "manifest.json").read_text())
    for name in ["parcel_features.parquet", "energy_observations.parquet"]:
        if digest(root / name) != manifest["outputs"][name]:
            raise ValueError("Referencia histórica de Chamberí alterada")
    historical = (
        pd.read_parquet(root / "parcel_features.parquet").set_index("parcel_ref14").sort_index()
    )
    current = features[features.district_code.eq("07")].set_index("parcel_ref14").sort_index()
    for col in historical:
        pd.testing.assert_series_equal(historical[col], current[col], check_dtype=False)
    old_energy = pd.read_parquet(root / "energy_observations.parquet")
    current_energy = observations[observations.parcel_ref14.isin(current.index)]
    if set(old_energy.record_id) != set(current_energy.record_id):
        raise ValueError("Regresión en registros CEEE de Chamberí")
    old_bu_path = root.parent / "session_2" / "pilot_buildings.parquet"
    if old_bu_path.exists() and set(
        pd.read_parquet(old_bu_path, columns=["building_id"]).building_id
    ) != set(display_ids):
        raise ValueError("Regresión de identidades BU en mapa Chamberí")
    return {
        "status": "passed",
        "shared_columns_checked": len(historical.columns),
        "parcels": len(current),
        "unique_certificates": int(current_energy.record_id.nunique()),
        "map_bu": len(display_ids),
    }


def run(
    input_dir,
    output_dir,
    boundary_dir,
    district="all",
    chamberi_reference="data/processed/session_6_audited",
    inspections_dir=None,
    grants_dir=None,
):
    started = time.perf_counter()
    source, target = Path(input_dir), Path(output_dir)
    if target.exists():
        raise FileExistsError("Usar una salida nueva de sesión 7")
    frames, hashes, source_manifest_hash = load_inputs(source)
    cp, bu, cert, links, boundaries, contexts = (frames[n] for n in INPUTS)
    checked_boundaries, boundary_metadata = boundary_source.load(boundary_dir)
    validate_districts(checked_boundaries)
    if (
        not np.array_equal(
            boundaries.district_code.to_numpy(), checked_boundaries.district_code.to_numpy()
        )
        or not sh.equals_exact(
            sh.from_wkt(boundaries.geometry_wkt.to_numpy()),
            sh.from_wkt(checked_boundaries.geometry_wkt.to_numpy()),
            tolerance=0.000001,
        ).all()
    ):
        raise ValueError("Los límites locales no coinciden con los usados en sesión 2")
    selected = resolve_district(district, boundaries)
    codes = boundaries.district_code.tolist() if selected == "all" else [selected]
    source_report = source_coverage(cp, bu, cert, links, boundaries)
    # Reproducir la asignación geoespacial de toda la captura, no solo confiar en etiquetas.
    spatial_checks = {}
    for name, frame in [("cp", cp), ("bu", bu)]:
        assigned = boundary_source.assign(
            sh.from_wkt(frame.geometry_wkt.to_numpy(), on_invalid="ignore"), boundaries
        )
        for column in assigned:
            if (
                not assigned[column]
                .fillna("")
                .equals(frame[column].reset_index(drop=True).fillna(""))
            ):
                raise ValueError(f"Asignación espacial no reproducida: {name}/{column}")
        spatial_checks[name] = True
    print("A/B: fuentes y asignación espacial verificadas", flush=True)
    quality, energy = quality_links(cp, cert, links)
    event_inputs, events = {}, {}
    for kind, path in [("inspection", inspections_dir), ("grant", grants_dir)]:
        if path is not None:
            events[kind], event_inputs[kind] = load_event_snapshot(
                path, kind, hashes["parcels_audited"]
            )
    features = add_grid(
        add_profiles(
            aggregate_event_features(
                parcel_features(cp, bu, cert, links, "all"),
                events.get("inspection"),
                events.get("grant"),
            )
        ),
        cp,
    )
    summary = district_summary(features, bu, cp, energy, quality, boundaries)
    reconciled = reconcile(features, bu, cp, energy, summary)
    processing_seconds = time.perf_counter() - started
    print("C/D: agregación municipal reconciliada", flush=True)
    chamberi = check_chamberi(
        chamberi_reference,
        features,
        energy,
        set(bu.loc[bu.district_code.eq("07") & bu.usable_geometry, "building_id"]),
    )
    scoped = features if selected == "all" else features[features.district_code.eq(selected)]
    observations = observations_for(energy, scoped)
    target.mkdir(parents=True)
    summary.to_parquet(target / "district_summary.parquet", index=False)
    summary.to_csv(target / "district_summary.csv", index=False)
    quality.to_parquet(target / "quality_links.parquet", index=False)
    features[features.district_code.isna()].to_parquet(
        target / "unassigned_parcels.parquet", index=False
    )
    scoped.to_parquet(target / "parcel_features.parquet", index=False)
    observations.to_parquet(target / "energy_observations.parquet", index=False)
    write_json(target / "source_coverage.json", source_report)
    write_json(
        target / "reconciliation.json",
        {**reconciled, "spatial_reassignment": spatial_checks, "chamberi_regression": chamberi},
    )
    # Solo 21 geometrías simplificadas en el producto municipal.
    district_map = boundaries.copy()
    district_map["geometry_geojson"] = sh.to_geojson(
        sh.transform(
            sh.simplify(sh.from_wkt(boundaries.geometry_wkt.to_numpy()), 5, preserve_topology=True),
            Transformer.from_crs(25830, 4326, always_xy=True).transform,
            interleaved=False,
        )
    )
    district_map.drop(columns="geometry_wkt").to_parquet(target / "districts.parquet", index=False)
    partition_times = {}
    partition_hashes = {}
    zones = features.set_index("parcel_ref14").analysis_zone
    for code in codes:
        start = time.perf_counter()
        partition = target / "districts" / code
        f = features[features.district_code.eq(code)].copy()
        obs = observations_for(energy, f)
        write_analytics(partition, f, obs, {"district_code": code})
        b = display_geometries(bu[bu.district_code.eq(code)], "bu", zones)
        p = display_geometries(cp[cp.district_code.eq(code)], "cp", zones)
        p["cp_rows"] = p.parcel_ref14.map(features.set_index("parcel_ref14").cp_rows)
        b.to_parquet(partition / "map_buildings.parquet", index=False)
        p.to_parquet(partition / "map_parcels.parquet", index=False)
        context = contexts[contexts.building_id.isin(b.building_id)]
        context.to_parquet(partition / "contexts.parquet", index=False)
        relevant = links[links.parcel_ref14.isin(set(p.parcel_ref14) | set(b.parcel_ref14))]
        ids = set(context.certificate_id) | set(relevant.certificate_id)
        cert[cert.record_id.isin(ids)].to_parquet(partition / "certificates.parquet", index=False)
        relevant.to_parquet(partition / "links.parquet", index=False)
        metadata = {
            "version": "session6-v2",
            "city_version": VERSION,
            "district_code": code,
            "district_name": boundaries.set_index("district_code").loc[code, "district_name"],
            "inputs": hashes,
            "event_inputs": event_inputs,
            "outputs": {p.name: digest(p) for p in sorted(partition.iterdir())},
        }
        write_json(partition / "manifest.json", metadata)
        partition_hashes[code] = digest(partition / "manifest.json")
        partition_times[code] = time.perf_counter() - start
        print(
            f"E: distrito {code}, {len(f)} parcelas analíticas, {len(b)} BU visualizables",
            flush=True,
        )
    if digest(source / "quality_metrics.json") != source_manifest_hash or any(
        digest(source / (n + ".parquet")) != sha for n, sha in hashes.items()
    ):
        raise ValueError("Entradas modificadas durante ejecución")
    benchmark = {
        "processing_seconds": processing_seconds,
        "district_generation_seconds": partition_times,
        "total_seconds": time.perf_counter() - started,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "frame_memory_mib": {
            name: float(frame.memory_usage(deep=True).sum() / 1024**2)
            for name, frame in frames.items()
        },
    }
    write_json(target / "benchmark.json", benchmark)
    manifest = {
        "version": VERSION,
        "city": "madrid",
        "municipality_code": "28079",
        "district": selected,
        "available_districts": codes,
        "inputs": hashes,
        "source_manifest_sha256": source_manifest_hash,
        "boundary_sha256": boundary_metadata["sha256"],
        "boundary_license": boundary_metadata["license"],
        "event_inputs": event_inputs,
        "district_manifests": partition_hashes,
        "municipal": {
            "parcel_rows": len(cp),
            "parcel_references": len(features),
            "bu_objects": len(bu),
            "ceee_records": len(cert),
            "parcels_with_energy": int(features.energy_available.sum()),
            "confirmed_certificate_records": int(energy.record_id.nunique()),
            "record_parcel_pairs": len(energy),
            "unassigned_parcel_references": int(features.district_code.isna().sum()),
        },
        "outputs": {p.name: digest(p) for p in sorted(target.iterdir()) if p.is_file()},
        "code_sha256": {
            name: digest(Path(__file__).with_name(name))
            for name in [
                "city_pipeline.py",
                "city_audit.py",
                "territory.py",
                "features.py",
                "profiles.py",
                "analytics.py",
                "event_features.py",
                "events.py",
                "districts.py",
            ]
        },
    }
    write_json(target / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", choices=["madrid"], default="madrid")
    parser.add_argument(
        "--district", default="all", help="all, código oficial o nombre, p.ej. chamberi"
    )
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/session_2"))
    parser.add_argument("--boundary-dir", type=Path, default=Path("data/raw/session_2/districts"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/session_7_final"))
    parser.add_argument(
        "--chamberi-reference", type=Path, default=Path("data/processed/session_6_audited")
    )
    parser.add_argument("--inspections-dir", type=Path)
    parser.add_argument("--grants-dir", type=Path)
    args = parser.parse_args()
    result = run(
        args.input_dir,
        args.output_dir,
        args.boundary_dir,
        args.district,
        args.chamberi_reference,
        args.inspections_dir,
        args.grants_dir,
    )
    print(json.dumps(result["municipal"], indent=2))


if __name__ == "__main__":
    main()
