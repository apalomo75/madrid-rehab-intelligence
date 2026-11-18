"""Commercial browser journeys; existing local server and Chromium required."""

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
    result = dict(status="not_completed", visual_review="pending", journeys=[])
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.goto(args.url, wait_until="networkidle")
            page.locator(".st-key-welcome_open_address button").click()
            for query, title, section in [
                (
                    "CALLE BAILEN 16",
                    "CALLE DE BAILÉN 16 — Madrid",
                    "Consultar antecedentes, fechas y fuentes",
                ),
                (
                    "CALLE CRISTO DE LA VICTORIA 239",
                    "CALLE DEL CRISTO DE LA VICTORIA 239 — Madrid",
                    "Consultar certificados, fechas y fuentes",
                ),
                (
                    "CALLE RIBADAVIA 16",
                    "CALLE DE RIBADAVIA 16 — Madrid",
                    "Consultar expedientes y procedencia",
                ),
            ]:
                page.get_by_label("Calle o dirección", exact=True).fill(query)
                page.get_by_role("button", name="Buscar", exact=True).click()
                selector = page.get_by_test_id("stSelectbox").filter(
                    has_text="Seleccione la dirección correcta"
                )
                selector.locator('[data-baseweb="select"]').click()
                page.get_by_role("option").first.click()
                page.get_by_role("button", name="Abrir ficha del inmueble", exact=True).click()
                expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
                expect(
                    page.get_by_role("heading", name="Antes de preparar una propuesta", exact=True)
                ).to_be_visible()
                page.get_by_text(section, exact=True).click()
                page.get_by_text(
                    "Detalles técnicos · seis secciones y datos originales", exact=True
                ).click()
                expect(
                    page.get_by_role("tab", name="Certificados CEEE", exact=True)
                ).to_be_visible()
                page.screenshot(
                    path=str(args.output_dir / f"journey_{len(result['journeys']) + 1}.png"),
                    full_page=True,
                )
                page.get_by_role("button", name="Volver a los resultados", exact=True).click()
                expect(page.get_by_label("Calle o dirección", exact=True)).to_have_value(query)
                result["journeys"].append(query)
            result["horizontal_document_overflow"] = page.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth"
            )
            browser.close()
            result["status"] = "passed_browser_human_review_pending"
    except Exception as exc:
        result.update(status="blocked_or_failed", error_type=type(exc).__name__, error=str(exc))
    (args.output_dir / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"].startswith("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
