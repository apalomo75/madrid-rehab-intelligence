"""Session 30 public bundle interactions; no claim of WebGL validation."""

import json
import os
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab.address_search import parse_query
from madrid_rehab.commercial_map import selected_deck


class GeometryTests(unittest.TestCase):
    def test_fit_uses_selected_geometry_without_changing_wkt(self):
        frame = pd.DataFrame(
            {
                "parcel_ref14": ["a", "b"],
                "geometry_wkt": [
                    "POLYGON ((440000 4470000, 440050 4470000, 440050 4470050, 440000 4470050, 440000 4470000))",
                    "POLYGON ((450000 4480000, 450050 4480000, 450050 4480050, 450000 4480050, 450000 4480000))",
                ],
            }
        )
        original = frame.copy(deep=True)
        first = json.loads(selected_deck(frame, "a").to_json())
        second = json.loads(selected_deck(frame, "b").to_json())
        self.assertGreater(first["initialViewState"]["zoom"], 16)
        self.assertNotEqual(
            first["initialViewState"]["longitude"], second["initialViewState"]["longitude"]
        )
        self.assertTrue(first["layers"][0]["data"]["features"][0]["properties"]["selected"])
        pd.testing.assert_frame_equal(frame, original)

    def test_street_and_number_only_once(self):
        self.assertEqual(parse_query("Calle Bailén 12"), parse_query("Calle Bailén", "12"))


class SummaryTests(unittest.TestCase):
    def test_multiple_scopes_and_plan_are_visible_without_a_building_rating(self):
        script = """
from madrid_rehab.commercial_fiche import CommercialFiche, Evidence, Quality
from madrid_rehab.commercial_view import render
model = CommercialFiche("28065", "Getafe", "test", "cp", "Dirección de prueba")
for identifier, scope, consumption, emissions in [("unit", "individual_unit", "A", "B"), ("building", "whole_building", "F", "G")]:
    model.energy.append(Evidence("Contenido CEEE", {"Consumo": consumption, "Emisiones": emissions, "Fecha declarada": "2024-01-01", "Ámbito": scope}, "CEEE", identifier, Quality.PARCEL, scope))
model.municipal_grants.append(Evidence("Plan Rehabilita", {"Convocatoria": "2023", "Expediente": "case-1", "Actuaciones por componente fuente": "Accesibilidad", "Subvención revisada del expediente (€)": 1234.5}, "Ayuntamiento de Madrid", "case-1", Quality.PARCEL, "Expediente", "2024"))
render(model, {})
"""
        app = AppTest.from_string(script, default_timeout=60).run()
        self.assertFalse(app.exception)
        text = "\n".join(item.value for item in app.markdown)
        summary = app.dataframe[0].value
        self.assertEqual(summary["N.º de certificados"].tolist(), [1, 1])
        self.assertEqual(summary["Ámbito"].tolist(), ["Edificio completo", "Vivienda individual"])
        self.assertEqual(summary["Calificación de consumo"].tolist(), ["F (1)", "A (1)"])
        self.assertEqual(summary["Calificación de emisiones"].tolist(), ["G (1)", "B (1)"])
        self.assertEqual(
            sum("Los certificados individuales no acreditan" in c.value for c in app.caption), 1
        )
        self.assertIn("case-1", text)
        self.assertIn("1,234.50", text)
        self.assertIn("No hay resultados reales sistemáticos", text)
        self.assertTrue(any("sin suma" in item.value for item in app.caption))


class PublicUXTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "MADRID_REHAB_PUBLIC": "1",
                "MADRID_REHAB_OFFLINE": "1",
                "MADRID_REHAB_DEV": "0",
                "MADRID_REHAB_DEMO": "0",
                "MADRID_REHAB_PILOT": "0",
                "MADRID_REHAB_BUNDLE_DIR": "data/deployment/madrid_rehab_v1_02",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_list_replace_return_page_and_dialog(self):
        app = AppTest.from_string(
            "from madrid_rehab.city_app import main\nmain()", default_timeout=180
        ).run()
        self.assertFalse(app.exception)
        prefix = "municipal_28079__cp_catalog_public_OR_none"
        page = next(s for s in app.selectbox if s.label == "Página de inmuebles")
        key = page.key
        prefix = key.removesuffix("_list_page")
        page.set_value(1).run()
        next(b for b in app.button if b.label == "Abrir ficha").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(any(s.label == "Página de inmuebles" for s in app.selectbox))
        self.assertTrue(app.get("deck_gl_json_chart"))
        next(b for b in app.button if b.label == "Ampliar ficha").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.get("dialog"))
        # A fresh rerun closes the test dialog without modifying parcel or filters.
        app.run()
        next(b for b in app.button if b.label == "Volver a la lista").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key=prefix + "_list_page").value, 1)

    def test_serialized_map_event_preserves_district_and_opens_fiche(self):
        from test_municipal_map_events import send_chart_event

        app = AppTest.from_string(
            "from madrid_rehab.city_app import main\nmain()", default_timeout=180
        ).run()
        app.selectbox(key="catalog_district").set_value("07").run()
        app.selectbox(key="energy_scope_28079").set_value("any").run()
        chart = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
        ref = chart["layers"][0]["data"]["features"][0]["properties"]["unit_id"]
        send_chart_event(app, ref)
        self.assertEqual(app.session_state["fiche_identity"], ("28079", "cp", ref))
        self.assertEqual(app.selectbox(key="catalog_district").value, "07")
        self.assertEqual(app.selectbox(key="energy_scope_28079").value, "any")
        chart = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
        highlighted = [
            f for f in chart["layers"][0]["data"]["features"] if f["properties"]["selected"]
        ]
        self.assertEqual([f["properties"]["unit_id"] for f in highlighted], [ref])

    def test_bailen_auto_map_and_fallback(self):
        from madrid_rehab import commercial_catalog_store as store

        app = AppTest.from_string(
            "from madrid_rehab.address_view import render\nrender()", default_timeout=180
        ).run()
        app.text_input(key="postal_street").set_value("Calle Bailén 12")
        next(b for b in app.button if b.label == "Buscar").click().run()
        uid = store.search("28079", "Calle Bailén 12")[0][0]["id"]
        labels = app.selectbox(key="postal_result_choice").options
        self.assertTrue(all("versión" not in label and "acceso" not in label for label in labels))
        app.selectbox(key="postal_result_choice").set_value(uid).run()
        self.assertFalse(app.exception)
        self.assertIsNotNone(app.session_state["fiche_identity"])
        deck = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
        self.assertEqual(len(deck["layers"][0]["data"]["features"]), 1)
        self.assertGreater(deck["initialViewState"]["zoom"], 14)
        self.assertTrue(any("registro oficial" in b.label for b in app.get("link_button")))
        self.assertTrue(any("No hay resultados reales" in m.value for m in app.markdown))
        with patch("madrid_rehab.commercial_map.parcel_frame", return_value=pd.DataFrame()):
            app.run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get("deck_gl_json_chart"))
        self.assertTrue(any("Geometría no disponible" in x.value for x in app.info))
        self.assertIsNotNone(app.session_state["fiche_identity"])
