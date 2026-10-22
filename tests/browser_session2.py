"""Verificación opcional con Chromium, exclusivamente contra la aplicación en localhost.

PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src \
.venv/bin/python tests/browser_session2.py
"""

import json
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright, expect

from madrid_rehab.map_view import filtered_view

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/session_2"
REPORT = ROOT / "reports/session_2"


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    meta = json.loads((DATA / "quality_metrics.json").read_text())
    buildings = pd.read_parquet(DATA / "pilot_buildings.parquet")
    certificates = pd.read_parquet(DATA / "pilot_certificates.parquet")
    contexts = pd.read_parquet(DATA / "building_certificate_contexts.parquet")
    objects, visible, _ = filtered_view(buildings, certificates, contexts)
    errors, external = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader",
            ],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda e: errors.append(e.text) if e.type == "error" else None)
        page.on(
            "request",
            lambda r: external.append(r.url)
            if not r.url.startswith(("http://127.0.0.1", "ws://127.0.0.1", "data:", "blob:"))
            else None,
        )
        page.goto("http://127.0.0.1:8512", wait_until="networkidle")
        page.get_by_text("Distrito piloto · Chamberí", exact=True).wait_for(timeout=45000)
        canvas = page.locator("canvas").first
        canvas.wait_for(timeout=30000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(REPORT / "mapa_piloto.png"), full_page=True)
        target_id = objects.loc[objects.certificate_count.gt(0), "building_id"].iloc[0]
        picker = page.get_by_role("combobox").last
        picker.fill(target_id)
        page.get_by_role("option", name=target_id, exact=True).click()
        page.get_by_text("Ficha del objeto catastral", exact=True).wait_for(timeout=15000)
        page.screenshot(path=str(REPORT / "ficha_piloto.png"), full_page=True)
        # El filtro cambia registros, sin asignar letras a BU.
        page.get_by_role("combobox").nth(0).click()
        page.get_by_role("option", name="Vivienda", exact=True).click()
        count = page.get_by_test_id("stMetricValue").nth(1)
        expect(count).not_to_have_text(f"{len(visible):,}", timeout=15000)
        after_scope = int(count.inner_text().replace(",", ""))
        assert 0 < after_scope < len(visible)
        assert page.get_by_test_id("stException").count() == 0
        assert not errors, errors
        assert not external, external
        metrics = {
            "url": "http://127.0.0.1:8512",
            "district": meta["pilot"]["district_name"],
            "default_objects": len(objects),
            "default_certificate_records": len(visible),
            "identifier_selector_opens_detail": True,
            "map_click_selection": "disabled; not reliably verified for GeoJsonLayer in this environment",
            "scope_filter_exercised": True,
            "records_after_dwelling_filter": after_scope,
            "javascript_errors": errors,
            "external_requests": external,
            "screenshots": ["mapa_piloto.png", "ficha_piloto.png"],
        }
        (REPORT / "browser_validation.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n"
        )
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
