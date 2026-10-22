"""Prueba de aceptación real: clics de ratón en polígonos, nunca eventos sintéticos.

Requiere el servidor local de README y Chromium de requirements-browser.lock.
Guarda capturas solo tras renderizado y aserciones satisfactorias.
"""

import json
import math
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import expect, sync_playwright
from shapely.geometry import shape
from pyproj import Transformer
from shapely.ops import transform
import shapely as sh

from madrid_rehab.map_view import filtered_view

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/session_3"
DATA = ROOT / "data/processed/session_2"


def world(lon, lat, zoom=13.8):
    size = 512 * 2**zoom
    return (
        (lon + 180) / 360 * size,
        (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * size,
    )


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    b = pd.read_parquet(DATA / "pilot_buildings.parquet")
    c = pd.read_parquet(DATA / "pilot_certificates.parquet")
    links = pd.read_parquet(DATA / "building_certificate_contexts.parquet")
    objects, visible, _ = filtered_view(b, c, links)
    districts = pd.read_parquet(DATA / "districts.parquet")
    geo = transform(
        Transformer.from_crs(25830, 4326, always_xy=True).transform,
        sh.from_wkt(districts[districts.district_code.eq("07")].iloc[0].geometry_wkt).simplify(
            1, preserve_topology=True
        ),
    )
    west, south, east, north = geo.bounds
    cx, cy = world((west + east) / 2, (south + north) / 2)
    errors, tiles, requests = [], [], []
    started = time.perf_counter()
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
        page = browser.new_page(viewport={"width": 1800, "height": 1200}, device_scale_factor=1)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on(
            "response",
            lambda r: tiles.append(r.status) if "tile.openstreetmap.org" in r.url else None,
        )
        page.on("request", lambda r: requests.append(r.url))
        page.goto("http://127.0.0.1:8512", wait_until="networkidle")
        expect(page.get_by_text("Distrito piloto · Chamberí", exact=True)).to_be_visible(
            timeout=45000
        )
        chart = page.get_by_test_id("stDeckGlJsonChart")
        canvas = chart.locator('canvas[id^="deckgl"]').first
        canvas.wait_for(timeout=30000)
        expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text(f"{len(objects):,}")
        expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text(f"{len(visible):,}")
        page.wait_for_timeout(2000)
        assert any(status == 200 for status in tiles), (
            "No se ha verificado la carga real de teselas urbanas"
        )
        page.screenshot(path=str(REPORT / "mapa_urbano.png"), full_page=True)
        first_render = time.perf_counter() - started

        def click_object(has_certificates):
            canvas.scroll_into_view_if_needed()
            box = canvas.bounding_box()
            candidates = []
            for row in objects.itertuples():
                if bool(row.certificate_count) != has_certificates:
                    continue
                geometry = shape(json.loads(row.geometry_geojson))
                point = geometry.representative_point()
                wx, wy = world(point.x, point.y)
                x, y = box["width"] / 2 + wx - cx, box["height"] / 2 + wy - cy
                if 40 < x < box["width"] - 40 and 40 < y < box["height"] - 40:
                    candidates.append((geometry.area, row.building_id, x, y))
            assert candidates, "No hay geometría candidata dentro de la vista real"
            _, identifier, x, y = max(candidates)
            before = time.perf_counter()
            page.mouse.click(box["x"] + x, box["y"] + y)
            expect(page.get_by_text("Ficha del objeto catastral", exact=True)).to_be_visible(
                timeout=15000
            )
            expect(
                page.get_by_text(f"Identificador público: {identifier}", exact=True)
            ).to_be_visible(timeout=15000)
            assert page.get_by_test_id("stException").count() == 0
            return identifier, time.perf_counter() - before

        identifier, latency = click_object(True)
        page.screenshot(path=str(REPORT / "ficha_seleccionada.png"), full_page=True)
        # Navegación real sin modificar el estado de Streamlit ni disparar callbacks manualmente.
        box = canvas.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.wheel(0, -250)
        page.mouse.down()
        page.mouse.move(
            box["x"] + box["width"] / 2 + 70, box["y"] + box["height"] / 2 + 30, steps=12
        )
        page.mouse.up()
        page.wait_for_timeout(1000)
        expect(page.get_by_text(f"Identificador público: {identifier}", exact=True)).to_be_visible()
        page.get_by_role("button", name="Limpiar selección", exact=True).click()
        expect(page.get_by_text("Consulta una parcela", exact=True)).to_be_visible()
        page.wait_for_timeout(1000)
        no_cert_id, _ = click_object(False)
        expect(
            page.get_by_text(
                "No hay certificados vinculados en esta captura. Esto no demuestra ausencia de certificación energética.",
                exact=True,
            )
        ).to_be_visible()
        page.get_by_role("button", name="Limpiar selección", exact=True).click()
        # Desactivar teselas y bloquear la red exterior: el clic debe seguir abriendo la ficha.
        page.get_by_label("Mapa urbano · requiere internet").uncheck()
        page.wait_for_timeout(1000)
        offline_requests = []

        def block_external(route):
            if not route.request.url.startswith(
                ("http://127.0.0.1", "ws://127.0.0.1", "data:", "blob:")
            ):
                offline_requests.append(route.request.url)
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_external)
        offline_id, _ = click_object(True)
        page.screenshot(path=str(REPORT / "mapa_sin_conexion.png"), full_page=True)
        assert not offline_requests, offline_requests
        # Excluir todos los certificados físicos confirmados y los elementos sin datos.
        page.get_by_text("Exploración energética", exact=True).click()
        combos = page.get_by_role("combobox")
        combos.nth(3).click()
        page.get_by_role("option", name="Edificio físico · cobertura", exact=True).click()
        combos.nth(4).click()
        page.get_by_role("option", name="Confirmado al nivel elegido", exact=True).click()
        page.get_by_role(
            "checkbox", name="Incluir elementos sin CEEE vinculados en esta captura"
        ).uncheck()
        expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text("0", timeout=15000)
        expect(page.get_by_text("Consulta una parcela", exact=True)).to_be_visible()
        assert not errors, errors
        result = {
            "status": "passed",
            "default_objects": len(objects),
            "default_records": len(visible),
            "clicked_bu": identifier,
            "clicked_without_certificates": no_cert_id,
            "clicked_offline": offline_id,
            "first_render_seconds": first_render,
            "click_detail_seconds": latency,
            "urban_tiles_200": tiles.count(200),
            "selection_persists_after_pan_zoom": True,
            "cleared_by_button_and_excluding_filter": True,
            "offline_external_requests": offline_requests,
            "javascript_errors": errors,
            "screenshots": ["mapa_urbano.png", "ficha_seleccionada.png", "mapa_sin_conexion.png"],
        }
        (REPORT / "browser_validation.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        REPORT.mkdir(parents=True, exist_ok=True)
        (REPORT / "browser_validation.json").write_text(
            json.dumps(
                {
                    "status": "failed_or_blocked",
                    "error": str(exc),
                    "screenshots_generated_this_run": False,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        raise
