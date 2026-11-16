"""Offline real-set reconciliation and bounded geometry timing; no source changes."""

import argparse
import itertools
import json
import os
from pathlib import Path
from time import perf_counter

from madrid_rehab import commercial_filters as f
from madrid_rehab.address_search import NAMES
from madrid_rehab.cadastral_identity import object_source
from madrid_rehab import demo
from madrid_rehab.municipal_navigation import zone_frame, zone_page

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
output = parser.parse_args().output
if output.exists():
    raise FileExistsError(output)
report = {
    "municipalities": [],
    "units": "distinct parcel_ref14",
    "external_deployment": "blocked: licenses and visual review pending",
}
for mode in ("local", "public"):
    os.environ["MADRID_REHAB_PUBLIC"] = "1" if mode == "public" else "0"
    for code, name in NAMES.items():
        start = perf_counter()
        index = f.query(code)
        cold_ms = (perf_counter() - start) * 1000
        counts, samples, timings = {}, {}, {}
        for key in f.LABELS:
            start = perf_counter()
            selected = f.query(code, [key])
            timings[key] = (perf_counter() - start) * 1000
            counts[key] = len(selected)
            samples[key] = selected.parcel_ref14.head(3).tolist()
            assert selected.parcel_ref14.is_unique
        pairs = []
        for a, b in itertools.combinations(f.LABELS, 2):
            left = set(f.query(code, [a]).parcel_ref14)
            right = set(f.query(code, [b]).parcel_ref14)
            union = f.query(code, [a, b])
            intersection = f.query(code, [a, b], "AND")
            assert set(union.parcel_ref14) == left | right
            assert set(intersection.parcel_ref14) == left & right
            pairs.append({"filters": [a, b], "OR": len(union), "AND": len(intersection)})
        start = perf_counter()
        zones = zone_frame(index)
        assert set(zones.unit_id) == set(index.zone)
        assert int(index.groupby("zone").size().sum()) == len(index)
        refs = zone_page(index, index.zone.iloc[0], 0)
        root, relative = object_source(code, "cp")
        geometry = demo.read(root, relative, [("parcel_ref14", "in", refs)])
        assert set(geometry.parcel_ref14) == set(refs)
        assert len(geometry) <= 500
        report["municipalities"].append(
            dict(
                mode=mode,
                code=code,
                name=name,
                total=len(index),
                counts=counts,
                samples=samples,
                pairs=pairs,
                cold_query_ms=cold_ms,
                query_ms=timings,
                geometry_page_ms=(perf_counter() - start) * 1000,
                geometry_rows=len(geometry),
            )
        )
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
