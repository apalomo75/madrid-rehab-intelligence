"""Local browser review for S30; existing Chromium required, no downloads."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from browser_session39 import touch_parcel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8512")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report = {"status": "blocked", "visual_validation": False}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(args.url, wait_until="networkidle")
            page.locator(".st-key-welcome_open_explore button").click()
            touch_parcel(page, page.locator(".st-key-commercial_results canvas").first, False)
            page.get_by_role("button", name="Ampliar ficha", exact=True).wait_for()
            page.screenshot(path=str(args.output_dir / "desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(args.output_dir / "mobile.png"), full_page=True)
            report.update(
                status="screenshots_captured_human_review_pending", visual_validation=False
            )
            browser.close()
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
    (args.output_dir / "browser.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
