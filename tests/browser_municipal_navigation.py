"""Mouse-only territory/grid/object transitions against the local Streamlit app.

Requires an unrestricted Ubuntu session and a server on port 8512. No DOM
injection, widget-state injection or RC search substitutes for the initial clicks.
"""

import argparse
import json
from pathlib import Path

import shapely as sh
from playwright.sync_api import expect, sync_playwright
from pyproj import Transformer

from browser_session3 import world
from madrid_rehab import demo
from madrid_rehab.municipal_fiche import SECTIONS
from madrid_rehab.municipal_navigation import (
    covered_municipalities,
    object_index,
    object_source,
    zone_frame,
    zone_page,
)
from madrid_rehab.regional_view import geometry_deck


def mouse_pick(page, frame, field, zoom, wanted=None):
    """Project real interior points using the exact view emitted by the app."""
    expect(page.get_by_test_id("stDeckGlJsonChart")).to_have_count(1)
    canvas = page.get_by_test_id("stDeckGlJsonChart").locator('canvas[id^="deckgl"]').first
    canvas.wait_for(timeout=30000)
    canvas.scroll_into_view_if_needed()
    page.wait_for_timeout(1500)
    bounds = canvas.bounding_box()
    view = geometry_deck(frame, field, zoom).initial_view_state
    cx, cy = world(view.longitude, view.latitude, zoom)
    project = Transformer.from_crs(25830, 4326, always_xy=True).transform
    candidates = []
    for row in frame.itertuples():
        identifier = getattr(row, field)
        if wanted and identifier != wanted:
            continue
        geom = sh.from_wkt(row.geometry_wkt)
        point = geom.representative_point()
        wx, wy = world(*project(point.x, point.y), zoom)
        x, y = bounds["width"] / 2 + wx - cx, bounds["height"] / 2 + wy - cy
        if 15 < x < bounds["width"] - 15 and 15 < y < bounds["height"] - 15:
            candidates.append((geom.area, identifier, x, y))
    assert candidates, f"No interior point visible for {wanted or field}"
    _, identifier, x, y = max(candidates)
    page.mouse.click(bounds["x"] + x, bounds["y"] + y)
    return identifier


def selector(page, label):
    return (
        page.get_by_test_id("stSelectbox")
        .filter(has=page.get_by_text(label, exact=True))
        .get_by_role("combobox")
    )


def check_fiche(page, ref, kind="parcela"):
    expect(page.get_by_role("heading", name=f"Ficha de {kind} · {ref}", exact=True)).to_be_visible(
        timeout=30000
    )
    assert tuple(page.get_by_role("tab").all_text_contents()) == SECTIONS
    assert page.get_by_test_id("stException").count() == 0
    assert page.get_by_test_id("stAlert").filter(has_text="No se puede").count() == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report = {"status": "not_completed", "municipalities": [], "human_visual_review": "pending"}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                timeout=10000,
                args=[
                    "--no-sandbox",
                    "--use-gl=angle",
                    "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader",
                ],
            )
            page = browser.new_page(viewport={"width": 1800, "height": 1100})
            page.goto("http://127.0.0.1:8512", wait_until="networkidle", timeout=15000)
            towns = covered_municipalities()
            territories = demo.read(demo.TERRITORY, "municipality_boundaries.parquet")
            territories = territories[
                territories.municipality_code.isin(towns.municipality_code)
            ].copy()
            territories["unit_id"] = territories.municipality_code
            for town in towns.itertuples():
                page.get_by_role("button", name="Ver municipios en el mapa", exact=True).click()
                mouse_pick(page, territories, "unit_id", 8, town.municipality_code)
                expect(selector(page, "Municipio")).to_have_text(town.name, timeout=30000)
                checks = {
                    "code": town.municipality_code,
                    "territory_mouse": "passed",
                    "objects": [],
                }
                for kind in ["cp", "bu"]:
                    if kind == "bu":
                        page.get_by_text("Objetos BU independientes", exact=True).click()
                    index = object_index(town.municipality_code, kind)
                    zone = mouse_pick(page, zone_frame(index), "unit_id", 11)
                    expect(selector(page, "Zona de exploración")).to_contain_text(
                        zone, timeout=30000
                    )
                    refs = zone_page(index, zone, 0)
                    root, relative = object_source(town.municipality_code, kind)
                    field = "parcel_ref14" if kind == "cp" else "building_id"
                    frame = demo.read(root, relative, [(field, "in", refs)]).copy()
                    frame["unit_id"] = frame[field]
                    ref = mouse_pick(page, frame, "unit_id", 15)
                    check_fiche(page, ref, "parcela" if kind == "cp" else "objeto BU")
                    page.get_by_role("button", name="Limpiar selección", exact=True).click()
                    expect(
                        page.get_by_role(
                            "heading",
                            name=f"Ficha de {'parcela' if kind == 'cp' else 'objeto BU'} · {ref}",
                            exact=True,
                        )
                    ).to_have_count(0)
                    mouse_pick(page, frame, "unit_id", 15, ref)
                    check_fiche(page, ref, "parcela" if kind == "cp" else "objeto BU")
                    alternatives = frame[frame.unit_id.ne(ref)]
                    if not alternatives.empty:
                        other = mouse_pick(page, frame, "unit_id", 15, alternatives.iloc[0].unit_id)
                        check_fiche(page, other, "parcela" if kind == "cp" else "objeto BU")
                    checks["objects"].append(
                        {
                            "kind": kind,
                            "reference": ref,
                            "grid_mouse": "passed",
                            "object_mouse": "passed",
                            "clear_reselect": "passed",
                        }
                    )
                    page.get_by_role("button", name="Volver a cuadrículas", exact=True).click()
                    expect(selector(page, "Zona de exploración")).to_contain_text("Vista general")
                page.screenshot(
                    path=str(args.output_dir / f"{town.municipality_code}.png"), full_page=True
                )
                report["municipalities"].append(checks)
                # Reset CP before opening the next municipality.
                page.get_by_text("Parcelas", exact=True).click()
            selector(page, "Municipio").click()
            page.get_by_role("option", name="Alcalá de Henares", exact=True).click()
            for ref in ["8727902VK6882N", "4731501VK6843S"]:
                page.get_by_label("Referencia catastral de parcela (14 caracteres)").fill(ref)
                page.get_by_label("Referencia catastral de parcela (14 caracteres)").press("Enter")
                check_fiche(page, ref)
                report.setdefault("alcala_search", []).append(ref)
            browser.close()
            report["status"] = "browser_checks_passed_human_review_pending"
    except Exception as exc:
        report.update(status="blocked_or_failed", error_type=type(exc).__name__, error=str(exc))
    (args.output_dir / "browser.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(report["status"])
    return 0 if report["status"].startswith("browser_checks_passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
