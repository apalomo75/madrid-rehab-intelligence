"""Real-browser demo check. Start Streamlit first; output must be a new directory."""

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from madrid_rehab.demo import CASES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    result = {"status": "not_completed", "cases": [], "human_review": "pending"}
    started = time.perf_counter()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1500, "height": 1100})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:8512", wait_until="networkidle")
            expect(
                page.get_by_role("heading", name="Madrid Rehab Intelligence", exact=True)
            ).to_be_visible(timeout=45000)
            for title, (code, ref) in CASES.items():
                page.get_by_test_id("stSelectbox").filter(
                    has_text="Caso real de demostración"
                ).locator('[role="combobox"]').click()
                page.get_by_role("option", name=title, exact=True).click()
                expect(page.get_by_role("heading", name="Ficha de parcela · " + ref)).to_be_visible(
                    timeout=45000
                )
                page.get_by_role("tab", name="Certificados CEEE", exact=True).click()
                expect(page.get_by_test_id("stDataFrame").first).to_be_visible()
                page.get_by_role(
                    "tab", name="Calidad, limitaciones y procedencia", exact=True
                ).click()
                with page.expect_download() as download:
                    page.get_by_role(
                        "button", name="Exportar ficha HTML · identificación y limitaciones"
                    ).click()
                download.value.save_as(args.output_dir / f"{code}.html")
                page.screenshot(path=str(args.output_dir / f"{code}.png"), full_page=True)
                result["cases"].append(
                    {"municipality": code, "reference": ref, "navigation_and_download": "passed"}
                )
            if errors:
                raise AssertionError(errors)
            result["status"] = "browser_checks_passed_human_visual_review_pending"
            browser.close()
    except Exception as exc:
        result.update(status="blocked_or_failed", error_type=type(exc).__name__, error=str(exc))
    result["elapsed_s"] = time.perf_counter() - started
    (args.output_dir / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(result["status"])
    return 0 if result["status"].startswith("browser_checks_passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
