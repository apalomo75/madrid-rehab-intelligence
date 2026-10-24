"""Perfil por parcela, independiente del visor y sin imputar ausencia administrativa."""

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from .ingest import digest
from .features import parcel_features, confirmed_energy
from .analysis_audit import audit_analysis
from .profiles import add_profiles, sensitivity_analysis
from .event_features import aggregate_event_features, load_event_snapshot


def exploratory_score(frame, age_weight=0.5, minimum_records=3):
    """Comparador B: priorización de revisión de evidencia, nunca IPR del inmueble."""
    if not 0 <= age_weight <= 1 or minimum_records < 1:
        raise ValueError("Pesos y mínimo fuera de dominio")
    eligible = (
        frame.construction_available
        & frame.ceee_valid_grade_count.ge(minimum_records)
        & frame.cp_rows.eq(1)
    )
    age = ((2026 - frame.construction_oldest_year) / 100).clip(0, 1)
    score = 100 * (age_weight * age + (1 - age_weight) * frame.ceee_efg_share_observed)
    return score.where(eligible & frame.ceee_efg_share_observed.notna())


def coverage(frame):
    return {
        "parcels": len(frame),
        "construction_available": int(frame.construction_available.sum()),
        "energy_available": int(frame.energy_available.sum()),
        "both_dimensions": int(frame.observed_dimensions.eq(2).sum()),
        "neither_dimension": int(frame.observed_dimensions.eq(0).sum()),
        "inspection_available": int(frame.inspection_records_observed.gt(0).sum())
        if "inspection_records_observed" in frame
        else None,
        "grant_available": int(frame.grant_awards_observed.gt(0).sum())
        if "grant_awards_observed" in frame
        else None,
        "global_ipr_eligible": 0,
        "missing_by_column": {k: int(v) for k, v in frame.isna().sum().items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/session_2"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/session_6_audited"))
    parser.add_argument("--inspections-dir", type=Path, help="Captura canónica ITE/IEE revisada")
    parser.add_argument("--grants-dir", type=Path, help="Captura canónica de ayudas revisada")
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError("Usar una salida nueva")
    start = time.perf_counter()
    names = [
        "parcels_audited",
        "buildings_audited",
        "certificates_integrated",
        "certificate_reference_links",
    ]
    hashes = {n: digest(args.input_dir / (n + ".parquet")) for n in names}
    source_manifest_hash = digest(args.input_dir / "quality_metrics.json")
    source_manifest = json.loads((args.input_dir / "quality_metrics.json").read_text())
    for name, sha in hashes.items():
        if source_manifest["outputs"][name + ".parquet"]["sha256"] != sha:
            raise ValueError("Entrada no coincide con el manifiesto de sesión 2")
    frames = [pd.read_parquet(args.input_dir / (n + ".parquet")) for n in names]
    event_inputs = {}
    events = {}
    for kind, path in [("inspection", args.inspections_dir), ("grant", args.grants_dir)]:
        if path is not None:
            events[kind], event_inputs[kind] = load_event_snapshot(
                path, kind, hashes["parcels_audited"]
            )
    features = add_profiles(
        aggregate_event_features(
            parcel_features(*frames),
            inspections=events.get("inspection"),
            grants=events.get("grant"),
        )
    )
    # Malla métrica explícita, no barrios: punto CP de una identidad única.
    cp = frames[0]
    if {"x", "y", "coordinate_crs"}.issubset(cp.columns):
        spatial = cp[cp.parcel_ref14.isin(features.parcel_ref14)].copy()
        spatial = spatial[spatial.parcel_ref14.map(cp.groupby("parcel_ref14").size()).eq(1)]
        spatial["analysis_zone"] = None
        x, y = pd.to_numeric(spatial.x, errors="coerce"), pd.to_numeric(spatial.y, errors="coerce")
        valid = (
            spatial.coordinate_crs.eq("EPSG:25830")
            & x.between(350000, 500000)
            & y.between(4400000, 4550000)
        )
        spatial.loc[valid, "analysis_zone"] = [
            f"E{int(a // 500) * 500}_N{int(b // 500) * 500}" for a, b in zip(x[valid], y[valid])
        ]
        features["analysis_zone"] = features.parcel_ref14.map(
            spatial.set_index("parcel_ref14").analysis_zone
        )
    audit, comparison = audit_analysis(*frames, features)
    energy = confirmed_energy(frames[0], frames[2], frames[3])
    energy = energy[energy.parcel_ref14.isin(features.parcel_ref14)]
    observations = energy[
        [
            "record_id",
            "parcel_ref14",
            "certificate_scope",
            "cal_norenovglobal",
            "date_parsed",
            "year",
        ]
    ].copy()
    sensitivity_summary = sensitivity_analysis(features, exploratory_score)
    scores = pd.DataFrame({"parcel_ref14": features.parcel_ref14})
    for weight in [0.25, 0.5, 0.75]:
        scores[str(weight)] = exploratory_score(features, weight)
    scores["weight_range"] = scores[["0.25", "0.5", "0.75"]].max(axis=1) - scores[
        ["0.25", "0.5", "0.75"]
    ].min(axis=1)
    result = coverage(features)
    result["comparison_B"] = {
        "eligible": int(scores["0.5"].notna().sum()),
        "median_weight_range": None
        if scores.weight_range.dropna().empty
        else float(scores.weight_range.median()),
        "max_weight_range": None
        if scores.weight_range.dropna().empty
        else float(scores.weight_range.max()),
        "decision": "A principal; B solo auditoría de sensibilidad, no IPR",
    }
    if source_manifest_hash != digest(args.input_dir / "quality_metrics.json"):
        raise ValueError("Manifiesto de sesión 2 modificado durante ejecución")
    args.output_dir.mkdir(parents=True)
    features.to_parquet(args.output_dir / "parcel_features.parquet", index=False)
    scores.to_parquet(args.output_dir / "sensitivity.parquet", index=False)
    comparison.to_csv(args.output_dir / "construction_periods.csv", index=False)
    observations.to_parquet(args.output_dir / "energy_observations.parquet", index=False)
    sensitivity_summary.to_parquet(args.output_dir / "sensitivity_summary.parquet", index=False)
    (args.output_dir / "audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False))
    (args.output_dir / "coverage.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    if any(digest(args.input_dir / (n + ".parquet")) != h for n, h in hashes.items()):
        raise ValueError("Entradas modificadas durante ejecución")
    manifest = {
        "version": "session6-v2",
        "reference_year": 2026,
        "district_code": "07",
        "inputs": hashes,
        "source_manifest_sha256": source_manifest_hash,
        "event_inputs": event_inputs,
        "code_sha256": {
            name: digest(Path(__file__).with_name(name))
            for name in [
                "analytics.py",
                "features.py",
                "profiles.py",
                "analysis_audit.py",
                "event_features.py",
                "events.py",
            ]
        },
        "parameters": {
            "grid_size_m": 500,
            "minimum_comparison_parcels": 20,
            "minimum_comparison_observed_parcels": 5,
            "sensitivity_weights": [0, 0.25, 0.5, 0.75, 1],
            "sensitivity_minimum_records": [1, 3, 5, 10],
        },
        "seconds": time.perf_counter() - start,
        "outputs": {p.name: digest(p) for p in args.output_dir.iterdir()},
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
