"""Measure reader alone, excluding exhaustive audit DataFrames and Streamlit UI."""

import json
import resource
import time
from pathlib import Path

from madrid_rehab import enriched_cadastre as ec


if __name__ == "__main__":
    audit = json.loads(Path("reports/session_19_integration/real_validation.json").read_text())
    results = []
    baseline = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    for case in audit["municipalities"]:
        start = time.perf_counter()
        rows, issues = ec.parcel_buildings(case["code"], case["largest_cp"])
        cp_seconds = time.perf_counter() - start
        start = time.perf_counter()
        ec.parcel_buildings(case["code"], case["largest_cp"])
        cached = time.perf_counter() - start
        start = time.perf_counter()
        bu = ec.building(case["code"], rows.building_id.iloc[0])
        bu_seconds = time.perf_counter() - start
        results.append(
            dict(
                code=case["code"],
                cp=case["largest_cp"],
                count=len(rows),
                cp_cold_including_verification_s=cp_seconds,
                cp_cached_s=cached,
                bu_uncached_s=bu_seconds,
                result_bytes=int(
                    rows.memory_usage(deep=True).sum()
                    + issues.memory_usage(deep=True).sum()
                    + bu.memory_usage(deep=True).sum()
                ),
            )
        )
    Path("reports/session_19_integration/reader_performance.json").write_text(
        json.dumps(
            dict(
                baseline_peak_rss_MiB=baseline,
                final_peak_rss_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                cache=ec._query.cache_info()._asdict(),
                cases=results,
            ),
            indent=2,
        )
    )
