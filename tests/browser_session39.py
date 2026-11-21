"""Review the public v1.04 map and postal experience on local Chromium."""

import argparse
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect, sync_playwright

SEARCHES = {
    "Madrid": "C/Bailén 12",
    "Getafe": "Av. Manuel Azaña 13",
    "Móstoles": "Cl Joaquín Blume 9",
    "Leganés": "Av Bélgica 83",
    "Alcorcón": "Cl Berlín 16",
    "Alcalá de Henares": "Cl Santa Mónica 10",
}


def choose(page, label, option):
    page.locator(f".st-key-{label}").get_by_role("combobox").click()
    page.get_by_role("option", name=option, exact=True).click()


def touch_parcel(page, canvas, mobile, *, software_renderer=False):
    expect(page.get_by_test_id("stApp")).to_have_attribute("data-test-script-state", "notRunning")
    canvas.scroll_into_view_if_needed()
    pixels = Image.open(BytesIO(canvas.screenshot(scale="css"))).convert("RGB")

    def yellow(x, y):
        red, green, blue = pixels.getpixel((x, y))
        return red >= 150 and red - green >= 14 and green - blue >= 18

    candidates = [
        (x, y)
        for x in range(15, pixels.width - 50)
        for y in range(15, pixels.height - 15)
        if yellow(x, y)
        and all(yellow(x + dx, y + dy) for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)])
    ]
    assert candidates, "No yellow polygon interior painted on the WebGL canvas"
    x, y = candidates[len(candidates) // 2]
    box = canvas.bounding_box()
    point = (round(box["x"] + x), round(box["y"] + y))
    # SwiftShader can block the pointer handler beyond the 250 ms tap window.
    # Preserve normal event dispatch while isolating the emulator's clock.
    if software_renderer:
        page.clock.set_fixed_time(datetime.now(timezone.utc))
    if mobile:
        page.touchscreen.tap(*point)
    else:
        page.mouse.move(*point)
        page.mouse.click(*point)


def no_horizontal_overflow(page):
    assert page.locator('[data-testid="stMain"]').evaluate(
        "el => el.scrollWidth <= el.clientWidth + 1"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8512")
    parser.add_argument(
        "--software-renderer",
        action="store_true",
        help="Use SwiftShader and a fixed gesture-test clock for slow headless hosts.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    expect.set_options(timeout=45000)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox", "--enable-unsafe-swiftshader"])
        for width in (1440, 320, 390):
            mobile = width < 500
            page = browser.new_page(
                viewport={"width": width, "height": 1000}, is_mobile=mobile, has_touch=mobile
            )
            print(f"Validating {width}px", flush=True)
            page.goto(args.url)
            page.locator(".st-key-welcome_open_explore button").click()
            canvas = page.locator(".st-key-commercial_results canvas").first
            expect(canvas).to_be_visible()
            assert page.evaluate("document.characterSet") == "UTF-8"
            expect(page.get_by_text("Lista de inmuebles", exact=True)).to_have_count(0)
            no_horizontal_overflow(page)
            page.get_by_role("button", name="Siguiente", exact=True).click()
            expect(page.get_by_text("Página 2 de 228", exact=True)).to_be_visible()
            expect(canvas).to_be_visible()
            print(f"{width}px map page 2 rendered", flush=True)
            touch_parcel(page, canvas, mobile, software_renderer=args.software_renderer)
            close = page.get_by_role("button", name="Cerrar ficha")
            expect(close).to_be_visible()
            print(f"{width}px parcel selected", flush=True)
            if mobile:
                assert close.bounding_box()["y"] > canvas.bounding_box()["y"]
            else:
                assert close.bounding_box()["x"] > canvas.bounding_box()["x"]
            no_horizontal_overflow(page)
            page.screenshot(path=args.output_dir / f"ficha_{width}.png")
            page.get_by_role("button", name="Ampliar ficha").click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.get_by_role("dialog").get_by_role("button", name="Close", exact=True).click()
            close.click()
            expect(close).to_have_count(0)
            expect(page.get_by_text("Página 2 de 228", exact=True)).to_be_visible()
            if width == 1440:
                page.get_by_text("Filtros y zona", exact=True).click()
                for label, count in [
                    ("Solo CEEE", "51,842"),
                    ("Solo ITE/IEE", "0"),
                    ("Solo Plan Rehabilita", "1,919"),
                    ("Ayudas NextGenerationEU", "3,300"),
                    ("Libro del Edificio / proyectos (P5)", "491"),
                ]:
                    page.get_by_text(label, exact=True).click()
                    metric = page.get_by_test_id("stMetricValue").first
                    expect(metric).to_have_text(count)
                    if count != "0":
                        expect(canvas).to_be_visible()
                    page.get_by_role("button", name="Limpiar filtros").click()
                page.get_by_text("Solo CEEE", exact=True).click()
                page.get_by_text("Libro del Edificio / proyectos (P5)", exact=True).click()
                expect(metric).to_have_text("52,001")
                page.get_by_text("Todas (AND)", exact=True).click()
                expect(metric).to_have_text("332")
                page.get_by_test_id("stSidebar").get_by_text("EN", exact=True).click()
                expect(page.get_by_role("heading", name="Explore properties")).to_be_visible()
                expect(metric).to_have_text("332")
                page.get_by_test_id("stSidebar").get_by_text("ES", exact=True).click()
                sidebar = page.get_by_test_id("stSidebar")
                sidebar.get_by_text("Acerca del proyecto", exact=True).click()
                expect(
                    page.get_by_role("heading", name="Acerca de Madrid Rehab Intelligence")
                ).to_be_visible()
                sidebar.get_by_text("Inicio", exact=True).click()
            else:
                page.goto(args.url)
            page.locator(".st-key-welcome_open_address button").click()
            searches = SEARCHES if width == 1440 else {"Madrid": SEARCHES["Madrid"]}
            for municipality, query in searches.items():
                if municipality != "Madrid":
                    choose(page, "postal_municipality", municipality)
                page.get_by_role("textbox", name="Calle o dirección").fill(query)
                expect(page.get_by_role("textbox", name="Complemento (opcional)")).to_have_count(0)
                page.get_by_role("button", name="Buscar", exact=True).click()
                page.get_by_role("combobox", name="Seleccione la dirección correcta").click()
                page.get_by_role("option").first.click()
                if municipality != "Madrid":
                    page.get_by_role("button", name="Abrir ficha del inmueble").click()
                expect(page.get_by_role("button", name="Ampliar ficha")).to_be_visible()
                no_horizontal_overflow(page)
                print(width, municipality, query, flush=True)
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
