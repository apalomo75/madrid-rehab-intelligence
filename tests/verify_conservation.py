"""Verificación offline de productos, procedencia, replay y baseline histórica."""

import argparse
import json
from pathlib import Path

from madrid_rehab.ingest import digest


def verify(snapshot, compare=None, historical_baseline=None):
    metadata = json.loads((snapshot / "manifest.json").read_text())
    errors = []
    for name, expected in metadata["outputs"].items():
        if digest(snapshot / name) != expected:
            errors.append("output:" + name)
    for path, expected in metadata["inputs"].items():
        if digest(Path(path)) != expected:
            errors.append("input:" + path)
    for name, expected in metadata["code_sha256"].items():
        if digest(Path("src/madrid_rehab") / name) != expected:
            errors.append("code:" + name)
    compared = 0
    if compare:
        other = json.loads((compare / "manifest.json").read_text())
        if metadata["outputs"] != other["outputs"]:
            errors.append("replay_manifest_outputs")
        for name, expected in metadata["outputs"].items():
            if digest(compare / name) != expected:
                errors.append("replay:" + name)
            compared += 1
    history = {}
    if historical_baseline:
        history = json.loads(historical_baseline.read_text())
        for path, expected in history.items():
            if digest(Path(path)) != expected:
                errors.append("historical:" + path)
    return dict(
        verified_outputs=len(metadata["outputs"]),
        verified_inputs=len(metadata["inputs"]),
        replay_outputs_compared=compared,
        historical_files_unchanged=len(history),
        errors=errors,
        ok=not errors,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot", type=Path, default=Path("data/processed/conservation/session_14_final_02")
    )
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--historical-baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = verify(args.snapshot, args.compare, args.historical_baseline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ok"] else 1)
