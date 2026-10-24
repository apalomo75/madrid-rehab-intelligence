"""Medición reproducible de carga verificada y caché, sin medir navegador."""

import argparse
import json
import statistics
import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from madrid_rehab.analysis_store import load_snapshot, snapshot_signature
from madrid_rehab.analysis_view import cached_snapshot
from madrid_rehab.profiles import filter_parcels, csv_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/session_6_audited"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports/session_6_deepening"))
    args = parser.parse_args()
    root = str(args.input_dir.resolve())
    uncached, cached = [], []
    for _ in range(5):
        start = time.perf_counter()
        snapshot = load_snapshot(root, snapshot_signature(root))
        uncached.append(time.perf_counter() - start)
    cached_snapshot.clear()
    cached_snapshot(root, snapshot_signature(root))
    with patch("madrid_rehab.analysis_store.pd.read_parquet", wraps=pd.read_parquet) as reader:
        for _ in range(10):
            start = time.perf_counter()
            snapshot = cached_snapshot(root, snapshot_signature(root))
            cached.append(time.perf_counter() - start)
        warm_reads = reader.call_count
    frame = snapshot["parcel_features.parquet"]
    start = time.perf_counter()
    selected = filter_parcels(
        frame, minimum_records=3, sort_by="ceee_records_observed", ascending=False
    )
    filter_seconds = time.perf_counter() - start
    start = time.perf_counter()
    body = csv_export(selected)
    result = {
        "scope": "Python load/filter/CSV only; no browser or GPU timing",
        "parcels": len(frame),
        "uncached_load_median_seconds": statistics.median(uncached),
        "cached_load_median_seconds": statistics.median(cached),
        "warm_parquet_reads_for_10_calls": warm_reads,
        "filter_seconds": filter_seconds,
        "selected_parcels": len(selected),
        "csv_bytes": len(body),
        "csv_seconds": time.perf_counter() - start,
    }
    assert warm_reads == 0
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "analysis_performance.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
