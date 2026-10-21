"""Interfaz de ejecución de una muestra, con reproducción sin red."""

import argparse
import json

from .pipeline import run


def main():
    parser = argparse.ArgumentParser(description="Muestra limitada Catastro–CEEE (máx. 5 MiB)")
    parser.add_argument("--config", default="config/sample.json")
    parser.add_argument("--raw-dir", default="data/raw/sample")
    parser.add_argument("--output-dir", default="data/processed/sample")
    parser.add_argument("--report-dir", default="reports/sample")
    parser.add_argument("--offline-snapshot", help="Reproduce snapshot.json sin peticiones de red")
    args = parser.parse_args()
    with open(args.config) as stream:
        config = json.load(stream)
    try:
        report = run(config, args.raw_dir, args.output_dir, args.report_dir, args.offline_snapshot)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(json.dumps({"status": report["status"], "metrics": report["metrics"], "pilot": report["pilot"]},
                     indent=2, ensure_ascii=False))
    return 2 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
