"""Benchmark PRTR y comparación municipal, sin sobrescribir informes anteriores."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from madrid_rehab.city_store import load_district, signature
from madrid_rehab.grants_view import benchmark_views


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Usar informe nuevo")
    results = benchmark_views()
    root = Path("data/processed/session_7_final")
    start = perf_counter()
    load_district(root, "07", signature(root, "07"))
    results["existing_chamberi_load_s"] = perf_counter() - start
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
