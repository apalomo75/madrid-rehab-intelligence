"""Local desktop/mobile ES/EN capture; requires installed Chromium, never downloads it."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8512")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report = {"status": "blocked", "visual_validation": False, "webgl_validation": False}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(args.url, wait_until="networkidle")
            page.locator(".st-key-welcome_open_explore button").click()
            page.get_by_text("Filtros y zona", exact=True).click()

            def choose(label, option):
                page.get_by_role("combobox", name=label, exact=True).click()
                page.get_by_role("option", name=option, exact=True).click()

            choose("Distrito", "Villaverde")
            choose("Barrio", "Los Rosales")
            page.get_by_text("904", exact=True).wait_for()
            page.get_by_role("button", name="Siguiente", exact=True).click()
            page.get_by_text("Página 2 de 2", exact=True).wait_for()
            page.screenshot(path=str(args.output_dir / "los_rosales_page2_es.png"), full_page=True)
            choose("Distrito", "Chamberí")
            choose("Barrio", "Gaztambide")
            page.get_by_text("555", exact=True).wait_for()
            page.screenshot(path=str(args.output_dir / "gaztambide_es.png"), full_page=True)
            page.get_by_role("radio", name="EN", exact=True).click()
            page.get_by_role("button", name="Next", exact=True).wait_for()
            page.screenshot(path=str(args.output_dir / "gaztambide_en.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(args.output_dir / "mobile_en.png"), full_page=True)
            report["mobile_no_document_overflow"] = page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            page.get_by_role("radio", name="ES", exact=True).click()
            page.get_by_role("button", name="Siguiente", exact=True).wait_for()
            page.screenshot(path=str(args.output_dir / "mobile_es.png"), full_page=True)
            report.update(status="screenshots_captured_human_review_pending")
            browser.close()
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
    (args.output_dir / "browser.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
