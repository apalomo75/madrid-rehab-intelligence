"""Real browser CP→BU→CP flow; requires local offline server, no state injection."""

import argparse
import json
from pathlib import Path

import pandas as pd
from playwright.sync_api import expect, sync_playwright

from browser_municipal_navigation import check_fiche, selector
from madrid_rehab import demo, enriched_cadastre as ec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    result = {"status": "not_completed", "cases": [], "webgl_picking": "not_tested_by_this_script"}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--use-gl=angle",
                    "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader",
                ],
            )
            page = browser.new_page(viewport={"width": 1800, "height": 1100})
            page.goto("http://127.0.0.1:8512", wait_until="networkidle")
            page.locator(".st-key-welcome_open_explore button").click()
            for code in json.loads((ec.ROOT / "manifest.json").read_text())["municipality_codes"]:
                name = demo.municipalities().set_index("municipality_code").loc[code, "name"]
                selector(page, "Municipio").click()
                page.get_by_role("option", name=name, exact=True).click()
                links = pd.read_parquet(
                    ec.ROOT / code / "cp_bu_documentary_links.parquet",
                    columns=["cp_reference_normalized", "link_class"],
                )
                ref = (
                    links[links.link_class.eq("A")].cp_reference_normalized.value_counts().index[0]
                )
                search = page.get_by_label("Referencia catastral de parcela (14 caracteres)")
                search.fill(ref)
                search.press("Enter")
                check_fiche(page, ref)
                zone = selector(page, "Zona de exploración").inner_text()
                page.get_by_role("tab", name="Características constructivas", exact=True).click()
                bu = selector(page, "Construcción relacionada").inner_text()
                page.get_by_role("button", name="Consultar construcción", exact=True).click()
                check_fiche(page, bu, "objeto BU")
                page.get_by_role("tab", name="Características constructivas", exact=True).click()
                expect(page.get_by_test_id("stDataFrame").first).to_be_visible()
                page.screenshot(path=str(args.output_dir / f"{code}_bu.png"), full_page=True)
                page.get_by_role(
                    "button", name="Volver al objeto de origen · " + ref, exact=True
                ).click()
                check_fiche(page, ref)
                expect(selector(page, "Zona de exploración")).to_have_text(zone)
                expect(page.get_by_test_id("stDeckGlJsonChart")).to_have_count(1)
                page.screenshot(path=str(args.output_dir / f"{code}_cp.png"), full_page=True)
                result["cases"].append(dict(code=code, cp=ref, bu=bu, zone=zone, result="passed"))
            browser.close()
            result["status"] = "passed_human_review_pending"
    except Exception as exc:
        result.update(status="blocked_or_failed", error=str(exc), error_type=type(exc).__name__)
    (args.output_dir / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"].startswith("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
