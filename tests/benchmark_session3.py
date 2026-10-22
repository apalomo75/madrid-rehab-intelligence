"""Medición local de preparación del mapa real; no mide renderizado en navegador."""

import json
import time
from pathlib import Path

import pandas as pd
import shapely as sh
from pyproj import Transformer
from shapely.ops import transform

from madrid_rehab.map_view import deck, filtered_view


def main():
    root = Path("data/processed/session_2")
    start = time.perf_counter()
    b, c, contexts, districts = [
        pd.read_parquet(root / f"{n}.parquet")
        for n in [
            "pilot_buildings",
            "pilot_certificates",
            "building_certificate_contexts",
            "districts",
        ]
    ]
    load = time.perf_counter() - start
    geo = transform(
        Transformer.from_crs(25830, 4326, always_xy=True).transform,
        sh.from_wkt(districts[districts.district_code.eq("07")].iloc[0].geometry_wkt).simplify(
            1, preserve_topology=True
        ),
    )
    feature = {"type": "Feature", "properties": {}, "geometry": sh.geometry.mapping(geo)}
    scenarios = []
    for residential in [True, False]:
        start = time.perf_counter()
        objects, visible, _ = filtered_view(b, c, contexts, residential=residential)
        filtered = time.perf_counter() - start
        start = time.perf_counter()
        chart = deck(objects, feature, None, urban=True)
        body = chart.to_json()
        scenarios.append(
            {
                "residential": residential,
                "objects": len(objects),
                "certificate_records": len(visible),
                "polygon_members": len(chart.layers[1].data),
                "filter_seconds": filtered,
                "map_serialization_seconds": time.perf_counter() - start,
                "json_bytes": len(body.encode()),
            }
        )
    result = {
        "scope": "Python preparation only; browser timing blocked separately",
        "load_seconds": load,
        "scenarios": scenarios,
    }
    report = Path("reports/session_3/performance.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n")
    print(report.read_text())


if __name__ == "__main__":
    main()
