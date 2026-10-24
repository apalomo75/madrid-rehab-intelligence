"""Benchmark de zonas reales de distrito; tiempos Python, no navegador."""

import json
from pathlib import Path
from time import perf_counter

from madrid_rehab.city_store import load_overview, load_district, signature
from madrid_rehab.city_maps import zone_records, district_deck


def main():
    root = Path("data/processed/session_7_final")
    overview = load_overview(root, signature(root))
    results = []
    for code in ["07", "06", "19"]:
        start = perf_counter()
        data = load_district(root, code, signature(root, code))
        loaded = perf_counter()
        records = zone_records(data["map_buildings.parquet"], data["map_parcels.parquet"])
        prepared = perf_counter()
        geometry = json.loads(
            overview["districts.parquet"].set_index("district_code").loc[code].geometry_geojson
        )
        body = district_deck(geometry, records).to_json()
        results.append(
            {
                "district": code,
                "load_seconds": loaded - start,
                "grid_seconds": prepared - loaded,
                "serialize_seconds": perf_counter() - prepared,
                "zones": len(records),
                "json_bytes": len(body.encode()),
            }
        )
    path = Path("reports/session_7_1/benchmark.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2))
    print(path.read_text())


if __name__ == "__main__":
    main()
