"""Real data replay: municipal detail, programme separation and bounded reader latency."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import pandas as pd

from madrid_rehab import plan_rehabilita as pr
from madrid_rehab.cadastral_identity import resolve_object
from madrid_rehab.commercial_data import load_fiche
from madrid_rehab.ingest import digest


def run():
    cases = pd.read_parquet(pr.DEFAULT / "cases.parquet")
    links = pd.read_parquet(pr.DEFAULT / "locations.parquet")
    known = links[links.link_class.eq("A")].copy()
    municipal = known.merge(cases, on="case_id", validate="one_to_one")
    refs = [
        ("Primer expediente confirmado", municipal.sort_values("case_id").iloc[0].parcel_ref14),
        ("Varios expedientes municipales", known.parcel_ref14.value_counts().index[0]),
        ("América", "8781605VK4788B"),
        ("Moncloa", "9377401VK3797G"),
    ]
    regional = pd.read_parquet(
        "data/processed/cadastre/session_12_2_partial_validated_01/grant_parcel_links.parquet"
    )
    overlap = set(known.parcel_ref14) & set(
        regional.loc[
            regional.match_status.isin(["confirmed", "confirmed_historical_madrid"]), "parcel_ref14"
        ]
    )
    if overlap:
        refs.append(("Plan Rehabilita y PRTR", sorted(overlap)[0]))
    pending = links[links.link_class.eq("B")]
    # An unconfirmed address does not produce a municipal grant at any candidate CP.
    expected_by_cp = known.groupby("parcel_ref14").case_id.agg(set).to_dict()
    results = []
    for label, ref in refs:
        status, cp = resolve_object("28079", ref, "cp")
        if cp.empty:
            raise ValueError(status)
        model, tables, errors, cold = load_fiche("28079", "Madrid", ref, cp)
        assert not errors, errors
        _, _, warm_errors, warm = load_fiche("28079", "Madrid", ref, cp)
        assert not warm_errors
        actual = {e.entity_id for e in model.municipal_grants}
        assert actual == expected_by_cp.get(ref, set())
        assert len(actual) == len(model.municipal_grants)
        assert not actual.intersection({e.entity_id for e in model.grants})
        expected = municipal[municipal.parcel_ref14.eq(ref)]
        expected_amounts = dict(zip(expected.case_id, expected.SUB_AYTO_R_cents))
        for e in model.municipal_grants:
            assert (
                round(e.value["Subvención revisada del expediente (€)"] * 100)
                == expected_amounts[e.entity_id]
            )
        results.append(
            dict(
                label=label,
                cp=ref,
                cold=cold,
                warm=warm,
                municipal_case_ids=sorted(actual),
                prtr_case_ids=[e.entity_id for e in model.grants],
                model=asdict(model),
            )
        )
    return dict(
        cases=results,
        pending_cases=len(pending),
        documentary_validation=True,
        browser_visual_validation=False,
        immutable_product_manifest_sha256=digest(pr.DEFAULT / "manifest.json"),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(run(), ensure_ascii=False, indent=2, default=str) + "\n")
