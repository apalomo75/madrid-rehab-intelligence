"""Benchmark real local: lectura escalonada, caché, filtros y serialización; sin GPU."""

import argparse
import json
import resource
import statistics
import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from madrid_rehab.city_app import cached_overview
from madrid_rehab.city_maps import cap_units, detailed_deck, overview_deck
from madrid_rehab.city_store import load_overview, load_district, signature
from madrid_rehab.district_view import cached_district
from madrid_rehab.map_view import filtered_view


def measure(function):
    start = time.perf_counter()
    result = function()
    return result, time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/session_7_final"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports/session_7"))
    args = parser.parse_args()
    root = str(args.input_dir.resolve())
    overview, overview_seconds = measure(lambda: load_overview(root, signature(root)))
    cached_overview.clear()
    cached_overview(root, signature(root))
    warm = []
    with patch("madrid_rehab.city_store.pd.read_parquet", wraps=pd.read_parquet) as reader:
        for _ in range(5):
            _, elapsed = measure(lambda: cached_overview(root, signature(root)))
            warm.append(elapsed)
        warm_overview_reads = reader.call_count
    municipal_json, overview_map_seconds = measure(
        lambda: overview_deck(
            overview["districts.parquet"], overview["district_summary.parquet"]
        ).to_json()
    )
    scenarios = []
    for code in overview["manifest"]["available_districts"]:
        data, cold = measure(lambda: load_district(root, code, signature(root, code)))
        cached_district.clear()
        cached_district(root, code, signature(root, code))
        with patch("madrid_rehab.city_store.pd.read_parquet", wraps=pd.read_parquet) as reader:
            _, warm_time = measure(lambda: cached_district(root, code, signature(root, code)))
            warm_reads = reader.call_count
        b, p, c, context = (
            data[name]
            for name in [
                "map_buildings.parquet",
                "map_parcels.parquet",
                "certificates.parquet",
                "contexts.parquet",
            ]
        )
        (filtered, _, _), filter_time = measure(
            lambda: filtered_view(b, c, context, residential=False)
        )
        zone = b.map_zone.value_counts().index[0] if len(b) else p.map_zone.value_counts().index[0]
        shown_b = filtered[filtered.map_zone.eq(zone)]
        shown_p = p[p.map_zone.eq(zone)].assign(certificate_count=0)
        shown_b, shown_p, capped = cap_units(shown_b, shown_p)
        geom = json.loads(
            overview["districts.parquet"].set_index("district_code").loc[code, "geometry_geojson"]
        )
        body, serialize_time = measure(
            lambda: detailed_deck(shown_b, shown_p, geom, zone).to_json()
        )
        zones = pd.concat(
            [b[["map_zone", "geometry_geojson"]], p[["map_zone", "geometry_geojson"]]]
        )
        max_zone_geometry_bytes = int(
            zones.assign(length=zones.geometry_geojson.str.len())
            .groupby("map_zone")
            .length.sum()
            .max()
        )
        scenarios.append(
            {
                "district_code": code,
                "bu_loaded": len(b),
                "cp_rows_loaded": len(p),
                "cold_load_seconds": cold,
                "warm_load_seconds": warm_time,
                "warm_parquet_reads": warm_reads,
                "filter_seconds": filter_time,
                "default_zone_units": len(shown_b) + len(shown_p),
                "map_capped": capped,
                "serialization_seconds": serialize_time,
                "json_bytes": len(body.encode()),
                "largest_zone_geometry_bytes": max_zone_geometry_bytes,
                "loaded_frame_memory_mib": float(
                    sum(f.memory_usage(deep=True).sum() for f in [b, p, c, context]) / 1024**2
                ),
            }
        )
    assert warm_overview_reads == 0 and all(s["warm_parquet_reads"] == 0 for s in scenarios)
    result = {
        "scope": "Datos reales; tiempos Python, no navegador/GPU",
        "overview_cold_seconds": overview_seconds,
        "overview_warm_median_seconds": statistics.median(warm),
        "overview_warm_parquet_reads": warm_overview_reads,
        "overview_json_bytes": len(municipal_json.encode()),
        "overview_serialization_seconds": overview_map_seconds,
        "districts": scenarios,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "viewer_benchmark.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "districts"}, indent=2))
    print("Districts measured:", len(scenarios))


if __name__ == "__main__":
    main()
