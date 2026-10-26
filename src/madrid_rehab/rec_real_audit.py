"""Reproduce exclusivamente el contraste local de la ficha REC aportada."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

from .rec import parse_rec

REAL_SHA256 = "22c9f480465abf5fb8dd0a6f19f21512418105fc0254df674c3463e556be7b9f"
DEFAULT_HTML = Path("data/raw/rec/real_11140360_01/ficha.html")
BRIDGE = Path("data/processed/administrative_events/session_10_final_01/ndp_bridge.parquet")


def audit(html, output):
    content = html.read_bytes()
    if hashlib.sha256(content).hexdigest() != REAL_SHA256:
        raise ValueError("La ficha no coincide con la evidencia revisada")
    result = parse_rec(
        content, source_id=str(html), observed_at="2026-10-26", encoding="iso-8859-1"
    )
    source = result["source_records"][0]
    # El NDP procede de la solicitud aportada, no figura como dato en el HTML.
    request = dict(
        method="GET",
        url="https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons?opcion=6&origen=I&ndp=11140360",
        ndp="11140360",
        http_status_reported_by_user=200,
        response_headers_preserved=False,
        capture_timestamp=None,
        local_review_date="2026-10-26",
        source_sha256=REAL_SHA256,
        origin="Archivo /tmp/rec-test/ficha.html aportado por el usuario desde Ubuntu",
        automation_permission="not_established",
        rec_specific_reuse="not_established",
    )
    bridge = pd.read_parquet(BRIDGE)
    rows = bridge[bridge.ndp.astype(str).eq(request["ndp"])]
    assert len(rows) == 1
    b = rows.iloc[0]
    assert (b.street, b.number_raw, b.via_code) == ("EZEQUIEL PEÑALVER", "8", "285300")
    assert b.match_status == "unmatched" and not b.parcel_ref14
    assert result["accesses"][0]["address_raw"] == "CALLE DE EZEQUIEL PEÑALVER 8"
    checks = []
    for e in source["field_evidence"]:
        cells = source["rows"][e["row_index"]][1]
        assert e["value"] in cells
        checks.append(dict(e, literal_cell_match=True))
    assert len(checks) == 67, len(checks)
    from collections import Counter

    expected = Counter((e["field"], e["value"]) for e in checks)
    actual = Counter()
    for entity in result["accesses"] + result["inspections"] + result["events"]:
        for field, value in entity.items():
            if isinstance(value, str) and (field, value) in expected:
                actual[(field, value)] += 1
    # inspection_type is normalized separately, with the original retained in blocks.
    actual[("inspection_type", "I.E.E.")] = sum(
        b.get("inspection_type") == "I.E.E." for b in source["blocks"]
    )
    assert actual == expected, (actual - expected, expected - actual)
    source["validation"] = "reviewed_real_layout_single_sha256"
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    products = dict(
        request_access_link=dict(
            ndp=request["ndp"],
            access_id=result["accesses"][0]["access_id"],
            basis="user_supplied_request_and_official_address_concordance",
            html_contains_ndp=False,
        ),
        result=result,
        provenance=request,
        field_checks=checks,
        bridge=dict(
            path=str(BRIDGE),
            sha256=hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
            rows=json.loads(rows.to_json(orient="records", force_ascii=False)),
            ndp_origin="request_parameter_not_html",
            address_concordance=True,
            confirmed_cp=None,
            physical_building_confirmed=False,
        ),
    )
    for name, value in products.items():
        p = output / (name + ".json")
        p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        p.chmod(0o600)
    shutil.copyfile(html, output / "ficha.html")
    (output / "ficha.html").chmod(0o600)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    audit(args.html, args.output_dir)


if __name__ == "__main__":
    main()
