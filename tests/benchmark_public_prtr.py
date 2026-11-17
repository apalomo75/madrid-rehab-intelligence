"""Offline candidate reconciliation; does not activate or distribute PRTR."""

import argparse
import json
from pathlib import Path
import resource
import sqlite3
import time

import pandas as pd

from madrid_rehab import public_prtr as prtr
from madrid_rehab.commercial_filters import combine
from madrid_rehab.ingest import digest


def audit(candidate, output):
    if output.exists():
        raise FileExistsError("New report required")
    start = time.perf_counter()
    meta = json.loads((candidate / "manifest.json").read_text())
    for name, info in meta["files"].items():
        assert digest(candidate / name) == info["sha256"], name
    rows = pd.read_parquet(candidate / prtr.PRODUCT)
    assert (len(rows), rows.expediente_id.nunique(), rows.parcel_ref14.nunique()) == (
        5072,
        5046,
        4378,
    )
    assert rows.match_status.isin(prtr.CONFIRMED).all()
    assert not rows.identity_conflict.any() and not rows.territorial_conflict.any()
    assert "raw_json" not in rows and "rnt_uc" not in rows
    before = json.loads(Path("data/deployment/madrid_rehab_v1_02/manifest.json").read_text())
    for name, info in before["files"].items():
        assert digest(Path("data/deployment/madrid_rehab_v1_02") / name) == info["sha256"]
        if name != "catalogue/catalogue.sqlite":
            assert meta["files"][name]["sha256"] == info["sha256"]
    combinations, municipal = [], []
    with sqlite3.connect(
        candidate.resolve().as_uri() + "/catalogue/catalogue.sqlite?mode=ro", uri=True
    ) as db:
        for code in meta["counts"]:
            index = pd.read_sql_query(
                "SELECT * FROM parcels WHERE municipality_code=? AND public_visible=1",
                db,
                params=(code,),
            )
            city_rows = rows[rows.municipality_code.eq(code)]
            assert set(index.loc[index.prtr.eq(1), "parcel_ref14"]) == set(city_rows.parcel_ref14)
            municipal.append(
                dict(
                    code=code,
                    parcels=city_rows.parcel_ref14.nunique(),
                    cases=city_rows.expediente_id.nunique(),
                    catalog=len(index),
                )
            )
            for program in prtr.PROGRAMS:
                selected = (
                    city_rows if program == "any" else city_rows[city_rows.programa.eq(program)]
                )
                refs = set(selected.parcel_ref14)
                current = index.copy()
                current["prtr"] = current.parcel_ref14.isin(refs)
                for evidence in ("energy", "rehabilita", "ite"):
                    other = (
                        set(current.loc[current[evidence].eq(1), "parcel_ref14"])
                        if evidence != "ite"
                        else set(meta["inspection_refs"]) & set(current.parcel_ref14)
                    )
                    for logic in ("AND", "OR"):
                        result = combine(
                            current,
                            ["prtr", evidence],
                            logic,
                            ite_refs=meta["inspection_refs"] if code == "28079" else (),
                        )
                        expected = refs & other if logic == "AND" else refs | other
                        assert set(result.parcel_ref14) == expected
                        combinations.append(
                            dict(
                                code=code,
                                program=program,
                                evidence=evidence,
                                logic=logic,
                                parcels=len(result),
                            )
                        )
            # Same identity set supplies the map; validate every selected parcel geometry.
            source = (
                Path("data/processed/session_2/parcels_audited.parquet")
                if code == "28079"
                else prtr.LINKS / code / "cp.parquet"
            )
            geometry = pd.read_parquet(
                candidate / source,
                filters=[("parcel_ref14", "in", list(city_rows.parcel_ref14))],
                columns=["parcel_ref14", "usable_geometry"],
            )
            assert set(geometry.loc[geometry.usable_geometry, "parcel_ref14"]) == set(
                city_rows.parcel_ref14
            )
    # All programmes share the same unique-case records, without allocating amounts to links.
    unique = rows.drop_duplicates("expediente_id")
    report = dict(
        status=(
            "release_validated_owner_confirmed"
            if meta.get("prtr_authorization", {}).get("status") == "owner_confirmed"
            else "local_candidate_validated_not_authorized"
        ),
        files_verified=len(meta["files"]),
        base_intact=True,
        other_sources_unchanged=True,
        confirmed_cases=len(unique),
        confirmed_parcels=rows.parcel_ref14.nunique(),
        confirmed_links=len(rows),
        product_bytes=(candidate / prtr.PRODUCT).stat().st_size,
        dataframe_bytes=int(rows.memory_usage(deep=True).sum()),
        elapsed_seconds=time.perf_counter() - start,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        cloud_memory_measured=False,
        webgl_validated=False,
        municipalities=municipal,
        combinations=combinations,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"combinations"}}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.candidate, args.output)
