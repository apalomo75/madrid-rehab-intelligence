"""Medición real de lectura selectiva del visor, sin navegador."""

import argparse
import json
from pathlib import Path

from madrid_rehab.energy_view import benchmark, read
from madrid_rehab.ingest import save_json
from madrid_rehab.regional_energy import DEFAULT

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/session_13/benchmark.json"))
    args = parser.parse_args()
    result = benchmark()
    links = read("municipalities/28065/links.parquet")
    confirmed = links[links.link_level.eq("A")]
    from time import perf_counter

    ref = confirmed.parcel_ref14.iloc[0]
    start = perf_counter()
    selected = read("municipalities/28065/links.parquet", ref=ref)
    cert = read(
        "municipalities/28065/certificates.parquet",
        ids=tuple(selected.certificate_id.unique()),
        columns=["certificate_id", "scope", "consumption_rating"],
    )
    result["parcel_read_seconds"] = perf_counter() - start
    result["parcel_observations"] = len(cert)
    result["pipeline"] = json.loads((DEFAULT / "energy_quality.json").read_text())
    target = args.output
    if target.exists():
        raise FileExistsError(target)
    save_json(target, result)
    print(json.dumps({k: v for k, v in result.items() if k != "pipeline"}, indent=2))
