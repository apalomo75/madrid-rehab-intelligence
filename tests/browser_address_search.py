"""Real browser commercial route; local app.py server required. No WebGL dependency."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8512")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    result = {"status": "not_completed", "independent_address_verification": False}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 1050})
            page.goto(args.url, wait_until="networkidle")
            expect(page.get_by_text("Buscar un inmueble por dirección", exact=True)).to_be_visible()
            page.get_by_label("Calle o dirección", exact=True).fill("CL BAILEN 12")
            page.get_by_label("Calle o dirección", exact=True).press("Enter")
            selector = page.get_by_test_id("stSelectbox").filter(
                has_text="Seleccione la dirección correcta"
            )
            expect(selector).to_be_visible()
            selector.locator('[data-baseweb="select"]').click()
            page.get_by_role("option").first.click()  # Explicit selection by this test user.
            page.get_by_role("button", name="Abrir ficha del inmueble", exact=True).click()
            expect(page.get_by_text("Dirección localizada", exact=True)).to_be_visible()
            expect(page.get_by_role("tab", name="Certificados CEEE", exact=True)).to_be_visible()
            page.screenshot(path=str(args.output_dir / "address_fiche.png"), full_page=True)
            page.get_by_role("button", name="Volver a los resultados", exact=True).click()
            expect(page.get_by_label("Calle o dirección", exact=True)).to_have_value("CL BAILEN 12")
            page.get_by_role("button", name="Limpiar búsqueda", exact=True).click()
            page.get_by_label("Calle o dirección", exact=True).fill("VIA INEXISTENTE SESION XX")
            page.get_by_role("button", name="Buscar", exact=True).click()
            expect(
                page.get_by_text(
                    "No hemos encontrado esta dirección en las fuentes integradas.", exact=True
                )
            ).to_be_visible()
            page.screenshot(path=str(args.output_dir / "no_results.png"), full_page=True)
            browser.close()
            result["status"] = "passed_browser_human_review_pending"
    except Exception as exc:
        result.update(status="blocked_or_failed", error_type=type(exc).__name__, error=str(exc))
    (args.output_dir / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"].startswith("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
