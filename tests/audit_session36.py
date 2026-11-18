"""Offline audit of original P5 records and unchanged v1.04 product."""

import argparse
from collections import Counter
import json
from pathlib import Path

import pandas as pd

from madrid_rehab.ingest import digest
from madrid_rehab.public_prtr import CONFIRMED, ORIGINAL_SHA256, select


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    raw = Path("data/raw/subvenciones/prtr/concesiones_prtr_20261024.geojson")
    assert digest(raw) == ORIGINAL_SHA256
    original = json.loads(raw.read_text())["features"]
    grants = pd.read_parquet("data/processed/grants/session_11_final_03/grants.parquet")
    links = pd.read_parquet(
        "data/processed/cadastre/session_12_2_partial_validated_01/grant_parcel_links.parquet"
    )
    confirmed = select(links, grants)
    bundle_path = Path("data/deployment/madrid_rehab_v1_04_candidate_01/prtr/confirmed.parquet")
    bundle = pd.read_parquet(bundle_path)
    p5 = grants[grants.programa.eq("P5")]
    public = bundle[bundle.programa.eq("P5")]
    originals = {f["properties"]["expediente"]: f["properties"] for f in original}
    assert len(original) == 7532 and len(p5) == 899
    assert public.match_status.isin(CONFIRMED).all()
    for row in public.itertuples():
        source = originals[row.expediente_id]
        assert source["pr"] == "pr5"
        assert source["imp_con"] == row.importe_concedido
        assert source["etapa"] == row.etapa_administrativa
    result = {
        "source_sha256": digest(raw),
        "bundle_product_sha256": digest(bundle_path),
        "original_cases": len(original),
        "p5_original_cases": len(p5),
        "p5_original_types": dict(Counter(p5.subprograma)),
        "p5_confirmed_cases_all_validated_cp": confirmed[
            confirmed.programa.eq("P5")
        ].expediente_id.nunique(),
        "p5_bundle_cases": public.expediente_id.nunique(),
        "p5_bundle_links": len(public),
        "p5_bundle_parcels": public.parcel_ref14.nunique(),
        "p5_bundle_cases_by_municipality": public.groupby("municipality_code")
        .expediente_id.nunique()
        .to_dict(),
        "p5_bundle_types_from_offline_audit_only": dict(
            Counter(p5.set_index("expediente_id").loc[public.expediente_id.unique()].subprograma)
        ),
        "individual_award_dates_present": int(p5.fecha_concesion.notna().sum()),
        "states": dict(Counter(p5.etapa_administrativa)),
        "completed_logbook_evidence": False,
        "bundle_modified": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
