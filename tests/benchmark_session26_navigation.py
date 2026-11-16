"""Offline geographic/evidence reconciliation, without browser or data writes."""

import argparse
import json
import os
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from madrid_rehab import commercial_filters as filters
from madrid_rehab.address_search import NAMES
from madrid_rehab.commercial_geography import district_names, restrict
from madrid_rehab.commercial_catalog_store import metadata, root_path
from madrid_rehab.ingest import digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a new report path")
    rows = []
    for mode in ["0", "1"]:
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": mode}):
            for code, name in NAMES.items():
                for selected in [
                    [],
                    ["energy"],
                    ["ite"],
                    ["rehabilita"],
                    ["prtr"],
                    ["energy", "rehabilita"],
                ]:
                    for logic in ["OR", "AND"] if len(selected) > 1 else ["OR"]:
                        start = perf_counter()
                        frame = filters.query(code, selected, logic)
                        row = dict(
                            mode="public_preview_blocked" if mode == "1" else "local",
                            municipality=name,
                            code=code,
                            filters=selected,
                            logic=logic,
                            parcels=len(frame),
                            seconds=perf_counter() - start,
                        )
                        if code == "28079":
                            row["districts"] = {
                                name: len(restrict(frame, district))
                                for district, name in district_names().items()
                            }
                            row["unassigned"] = len(frame) - sum(row["districts"].values())
                            assert row["unassigned"] >= 0
                        rows.append(row)
    meta = metadata()
    verified = {path: digest(Path(path)) == sha for path, sha in meta["inputs"].items()}
    verified.update(
        {
            str(root_path() / path): digest(root_path() / path) == sha
            for path, sha in meta["outputs"].items()
        }
    )
    assert all(verified.values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            dict(visual_validation=False, rows=rows, canonical_hashes_verified=verified),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
