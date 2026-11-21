"""Review the public welcome page with a running local Streamlit server."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8512")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        expect.set_options(timeout=20000)
        page.goto(args.url)

        def capture(name):
            viewport = page.viewport_size
            height = page.locator(".st-key-welcome").bounding_box()["height"]
            page.set_viewport_size(
                {"width": viewport["width"], "height": max(viewport["height"], int(height) + 100)}
            )
            page.screenshot(path=args.output_dir / f"{name}.png")
            page.set_viewport_size(viewport)

        def background():
            return page.get_by_test_id("stApp").evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )

        def check_illustration(alt_start, caption, layer):
            figure = page.locator(".welcome-map")
            illustration = figure.get_by_role("img", name=alt_start, exact=False)
            expect(illustration).to_be_visible()
            assert illustration.evaluate("img => img.complete && img.naturalWidth > 0")
            expect(figure.get_by_text(caption, exact=True)).to_be_visible()
            expect(figure.get_by_text(layer, exact=True)).to_be_visible()
            box = figure.bounding_box()
            assert 0 <= box["x"] and box["x"] + box["width"] <= page.viewport_size["width"]
            assert page.get_by_test_id("stApp").evaluate("el => el.scrollWidth <= el.clientWidth")

        hero = page.locator(".st-key-welcome_hero")
        cards = page.locator(".st-key-welcome_cards button")
        expect(hero.get_by_role("heading", name="Madrid Rehab Intelligence")).to_be_visible()
        expect(hero.get_by_text("Desarrollado por Alejandro Palomo")).to_be_visible()
        expect(cards).to_have_count(3)
        sidebar = page.get_by_test_id("stSidebar")
        expect(sidebar).to_be_hidden()
        expect(page.get_by_test_id("stSidebarCollapsedControl")).to_be_hidden()
        expect(hero.get_by_text("ES", exact=True)).to_be_visible()
        assert len({round(card.bounding_box()["y"]) for card in cards.all()}) == 1
        expect(page.locator("canvas")).to_have_count(0)
        check_illustration(
            "Esquema de calles",
            "Ilustración conceptual de Madrid y sus capas de información pública",
            "Libro del Edificio / P5",
        )
        assert page.locator(".welcome-map").bounding_box()["height"] <= 200
        assert all(
            box["y"] + box["height"] <= 900 for box in (card.bounding_box() for card in cards.all())
        )
        home_background = background()
        capture("portada_es")

        for route, title in [
            ("explore", "Explorar inmuebles"),
            ("address", "Buscar un inmueble por dirección"),
            ("about", "Acerca de Madrid Rehab Intelligence"),
        ]:
            page.locator(f".st-key-welcome_open_{route} button").click()
            expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible(timeout=60000)
            expect(sidebar).to_be_visible()
            assert background() == home_background
            expect(page.locator(".welcome-map")).to_have_count(0)
            page.screenshot(path=args.output_dir / f"interior_{route}.png")
            sidebar.get_by_text("Inicio", exact=True).click()
            expect(cards).to_have_count(3)

        page.locator(".st-key-welcome_open_explore button").click()
        page.get_by_text("Filtros y zona", exact=True).click()
        p5_label = "Libro del Edificio / proyectos (P5)"
        p5 = page.get_by_role("checkbox", name=p5_label)
        expect(p5).to_be_enabled()
        page.get_by_text(p5_label, exact=True).click()
        expect(p5).to_be_checked()
        page.get_by_text("Inicio", exact=True).click()
        expect(cards).to_have_count(3)
        page.locator(".st-key-welcome_open_explore button").click()
        page.get_by_text("Filtros y zona", exact=True).click()
        expect(p5).to_be_checked()
        page.get_by_text("Inicio", exact=True).click()
        expect(cards).to_have_count(3)

        hero.get_by_text("EN", exact=True).click()
        expect(hero.get_by_text("Developed by Alejandro Palomo")).to_be_visible()
        check_illustration(
            "Schematic streets",
            "Conceptual illustration of Madrid and its layers of public information",
            "Building Logbook / P5",
        )
        capture("portada_en")
        page.locator(".st-key-welcome_open_address button").click()
        expect(page.get_by_role("heading", name="Search by address", exact=True)).to_be_visible()
        expect(sidebar.get_by_text("EN", exact=True)).to_be_visible()
        sidebar.get_by_text("Home", exact=True).click()
        expect(sidebar).to_be_hidden()
        expect(hero.get_by_text("Developed by Alejandro Palomo")).to_be_visible()

        for width in (320, 390):
            page.set_viewport_size({"width": width, "height": 844})
            page.reload()
            expect(cards).to_have_count(3)
            expect(sidebar).to_be_hidden()
            expect(page.get_by_test_id("stExpandSidebarButton")).to_be_hidden()
            bounds = [card.bounding_box() for card in cards.all()]
            assert bounds[0]["y"] < bounds[1]["y"] < bounds[2]["y"]
            assert all(0 <= box["x"] and box["x"] + box["width"] <= width for box in bounds)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            check_illustration(
                "Esquema de calles",
                "Ilustración conceptual de Madrid y sus capas de información pública",
                "Libro del Edificio / P5",
            )
            capture(f"portada_{width}px")
        browser.close()


if __name__ == "__main__":
    main()
