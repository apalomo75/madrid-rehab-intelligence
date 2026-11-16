"""Inventory existing products for S28; no ETL, network or publication."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from madrid_rehab.deployment import catalog_requirements


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    base = Path.cwd()
    startup = set(catalog_requirements(base))
    paths = set(startup)
    # The public postal route still authenticates its historical input snapshot.
    postal = json.loads((base / "data/processed/addresses/session_20_01/manifest.json").read_text())
    paths.update((base / name).resolve() for name in postal["inputs"])
    patterns = [
        "data/processed/cadastre/session_18_enriched_01/**/*",
        "data/processed/cadastre/session_12_2_partial_validated_01/*/bu.parquet",
        "data/processed/cadastre/session_12_2_partial_validated_01/*/manifest.json",
        "data/processed/cadastre/session_12_2_partial_validated_01/summary.json",
        "data/processed/conservation/session_14_final_02/parcels/**/*",
        "data/processed/territory/session_12_1_final_01/manifest.json",
        "data/processed/territory/session_12_1_final_01/municipality_boundaries.parquet",
        "data/processed/session_7_final/districts.parquet",
    ]
    for code in ["28079", "28065", "28092", "28074", "28007", "28005"]:
        patterns.append(f"data/processed/energy/session_13_final_03/municipalities/{code}/*")
    for pattern in patterns:
        paths.update(p.resolve() for p in base.glob(pattern) if p.is_file())
    rows = []
    for path in sorted(paths):
        name = str(path.relative_to(base))
        with path.open("rb") as handle:
            sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
        family = (
            "energy"
            if "/energy/" in name
            else "conservation"
            if "/conservation/" in name
            else "rehabilita"
            if "/plan_rehabilita/" in name
            else "prtr"
            if "/grants/" in name or path.name == "grant_parcel_links.parquet"
            else "addresses"
            if "/addresses/" in name
            else "catalogue"
            if "/commercial_catalog/" in name
            else "cadastre/territory"
        )
        rows.append(
            dict(
                path=name,
                bytes=path.stat().st_size,
                sha256=sha256,
                family=family,
                use="startup authentication" if path in startup else "runtime fiche/map",
                production_authorized=False,
                replacement="future reviewed derivative; current hash contract requires exact bytes",
            )
        )
    with (args.output_dir / "files.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(
        files=len(rows),
        bytes=sum(r["bytes"] for r in rows),
        startup_files=len(startup),
        startup_bytes=sum(p.stat().st_size for p in startup),
        files_over_100_mib=[r["path"] for r in rows if r["bytes"] > 100 * 1024**2],
        note="Conservative runtime envelope, not an approved public package. No raw ZIP/GML.",
    )
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
