"""Benchmark selectivo: no es validación visual ni mide buffers nativos Arrow."""

import argparse
import json
from pathlib import Path

from madrid_rehab.conservation_view import benchmark

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(benchmark(), indent=2) + "\n")
