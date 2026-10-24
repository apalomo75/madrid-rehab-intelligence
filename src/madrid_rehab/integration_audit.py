"""Auditoría offline sin eventos nuevos; no simula cobertura."""

import argparse
import json
from pathlib import Path

import pandas as pd

from .city_store import load_overview, signature
from .ingest import digest


def audit_existing_capture(root, output_dir):
    root, output_dir = Path(root), Path(output_dir)
    if output_dir.exists():
        raise FileExistsError("Usar una salida nueva")
    overview = load_overview(root, signature(root))
    if overview["manifest"].get("event_inputs"):
        raise ValueError("Hay capturas de eventos: se requiere auditoría específica")
    coverage = overview["district_summary.parquet"][
        [
            "district_code",
            "district_name",
            "parcels",
            "parcels_with_energy",
            "observed_energy_coverage",
        ]
    ].copy()
    # Nulo: fuente no integrada, nunca tasa nula de conservación o ayudas.
    for source in ["ite_iee", "urban_inspection", "grant_award"]:
        coverage[source + "_source_status"] = "not_integrated"
        coverage[source + "_records_observed"] = pd.Series(
            pd.NA, index=coverage.index, dtype="Int64"
        )
    report = {
        "scenario": "D",
        "new_verified_records_integrated": 0,
        "new_parcel_links": 0,
        "new_territorial_records": 0,
        "source_manifest_sha256": digest(root / "manifest.json"),
        "limitations": [
            "No new verified event snapshots",
            "Unknown source coverage is not zero occurrence",
        ],
        "municipal": overview["manifest"]["municipal"],
    }
    output_dir.mkdir(parents=True)
    coverage.to_parquet(output_dir / "source_coverage_by_district.parquet", index=False)
    report["coverage_sha256"] = digest(output_dir / "source_coverage_by_district.parquet")
    (output_dir / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/session_7_final"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            audit_existing_capture(args.input_dir, args.output_dir), ensure_ascii=False, indent=2
        )
    )


if __name__ == "__main__":
    main()
