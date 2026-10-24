"""Compara dos ejecuciones reales CEEE sin modificar snapshots."""

from pathlib import Path
import json
from madrid_rehab.ingest import digest, save_json
from madrid_rehab.regional_energy import DEFAULT
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--original", type=Path, default=DEFAULT)
parser.add_argument("--replay", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise FileExistsError(args.output)
root = args.original
replay = args.replay
a = json.loads((root / "manifest.json").read_text())
b = json.loads((replay / "manifest.json").read_text())
parquets = [p for p in a["outputs"] if p.endswith(".parquet")]
assert a["inputs"] == b["inputs"]
assert a["code_sha256"] == b["code_sha256"]
checks = {p: digest(root / p) == digest(replay / p) for p in parquets}
assert all(checks.values()), [p for p, ok in checks.items() if not ok]
qa = json.loads((root / "energy_quality.json").read_text())
qb = json.loads((replay / "energy_quality.json").read_text())
volatile = {
    "normalization_including_read_seconds",
    "matching_seconds",
    "total_seconds",
    "peak_rss_mib",
}
assert {k: v for k, v in qa.items() if k not in volatile} == {
    k: v for k, v in qb.items() if k not in volatile
}
save_json(
    args.output,
    {
        "parquet_files_identical": len(checks),
        "inputs_identical": True,
        "code_identical": True,
        "quality_except_performance_identical": True,
        "replay_manifest_sha256": digest(replay / "manifest.json"),
        "replay_seconds": qb["total_seconds"],
        "replay_peak_rss_mib": qb["peak_rss_mib"],
        "note": "Replay concurrent with full test suite; runtime not directly comparable to isolated pipeline",
    },
)
print(len(checks), "Parquet idénticos byte a byte")
