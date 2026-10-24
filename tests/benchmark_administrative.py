"""Benchmark real de lectura administrativa, sin navegador ni datos sintéticos."""

import argparse
import json
import resource
from pathlib import Path

from madrid_rehab.administrative import DEFAULT
from madrid_rehab.administrative_view import benchmark


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Usar salida nueva")
    results = [benchmark(args.input_dir, code) for code in ["01", "07", "06", "11", "03", "19"]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "partitions": results,
                "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
