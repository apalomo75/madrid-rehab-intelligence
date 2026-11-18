"""Commercial product routes and real geographic reconciliation; no WebGL claim."""

import json
import os
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from madrid_rehab import commercial_filters as filters
from madrid_rehab.commercial_geography import district_index, district_names, restrict
from madrid_rehab.navigation import ROUTES


class Session26Tests(unittest.TestCase):
    def app(self, public="0", dev="0"):
        env = patch.dict(
            os.environ,
            {"MADRID_REHAB_PUBLIC": public, "MADRID_REHAB_DEV": dev, "MADRID_REHAB_DEMO": "0"},
        )
        env.start()
        self.addCleanup(env.stop)
        app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=180).run()
        app.button(key="welcome_open_explore").click().run()
        self.assertFalse(app.exception)
        return app

    def test_three_routes_and_saved_context(self):
        app = self.app()
        self.assertEqual(app.radio(key="city_navigation").options, list(ROUTES))
        app.selectbox(key="catalog_district").set_value("11").run()
        app.checkbox(key="priority_28079_rehabilita").check().run()
        self.assertEqual(app.metric[0].value, "153")
        next(b for b in app.button if b.label == "Abrir ficha").click().run()
        self.assertFalse(app.exception)
        identity = app.session_state["fiche_identity"]
        self.assertIsNotNone(identity)
        app.radio(key="city_navigation").set_value("Inicio").run()
        self.assertFalse(app.get("deck_gl_json_chart"))
        app.button(key="welcome_open_explore").click().run()
        self.assertEqual(app.session_state["fiche_identity"], identity)
        next(b for b in app.button if b.label == "Volver a la lista").click().run()
        self.assertTrue(app.checkbox(key="priority_28079_rehabilita").value)
        app.radio(key="city_navigation").set_value("Acerca del proyecto").run()
        self.assertTrue(any("experimental" in i.value for i in app.info))
        self.assertTrue(any("Fuentes y metodología" in e.label for e in app.expander))
        app.radio(key="city_navigation").set_value("Buscar por dirección").run()
        self.assertTrue(any(i.key == "postal_street" for i in app.text_input))
        app.radio(key="city_navigation").set_value("Explorar inmuebles").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="catalog_district").value, "11")
        self.assertTrue(app.checkbox(key="priority_28079_rehabilita").value)
        self.assertEqual(app.metric[0].value, "153")

    def test_district_filters_reconcile(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}):
            self.assertEqual(len(district_names()), 21)
            assignments = district_index()
            for selected in [
                [],
                ["energy"],
                ["ite"],
                ["rehabilita"],
                ["prtr"],
                ["energy", "rehabilita"],
            ]:
                for logic in ["OR", "AND"]:
                    whole = filters.query("28079", selected, logic)
                    sets = []
                    for district in district_names():
                        part = restrict(whole, district)
                        expected = set(whole.parcel_ref14) & set(
                            assignments.loc[assignments.district_code.eq(district), "parcel_ref14"]
                        )
                        self.assertEqual(set(part.parcel_ref14), expected)
                        self.assertFalse(part.parcel_ref14.duplicated().any())
                        sets.append(set(part.parcel_ref14))
                    self.assertEqual(sum(map(len, sets)), len(set().union(*sets)))

    def test_pilots_and_district_change(self):
        app = self.app()
        app.checkbox(key="priority_28079_energy").check().run()
        next(b for b in app.button if b.label == "Abrir ficha").click().run()
        app.selectbox(key="catalog_district").set_value("07").run()
        self.assertIsNone(app.session_state["fiche_identity"])
        self.assertTrue(app.checkbox(key="priority_28079_energy").value)
        for code in ["28065", "28092", "28074", "28007", "28005"]:
            app.selectbox(key="catalog_municipality").set_value(code).run()
            self.assertFalse(app.exception)
            self.assertFalse(any(s.label == "Distrito" for s in app.selectbox))
            app.checkbox(key="priority_" + code + "_energy").check().run()
            self.assertEqual(app.metric[0].value, f"{len(filters.query(code, ['energy'])):,}")

    def test_map_and_list_share_district_and_evidence(self):
        from test_municipal_map_events import send_chart_event

        app = self.app()
        app.selectbox(key="catalog_district").set_value("11").run()
        app.checkbox(key="priority_28079_rehabilita").check().run()
        expected = set(restrict(filters.query("28079", ["rehabilita"]), "11").parcel_ref14)
        chart = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
        mapped = {f["properties"]["unit_id"] for f in chart["layers"][0]["data"]["features"]}
        self.assertEqual(mapped, expected)  # all 153 fit in the bounded map page
        listed = {b.key.split("_open_")[-1] for b in app.button if b.label == "Abrir ficha"}
        self.assertLessEqual(listed, expected)
        self.assertEqual(len(listed), 10)
        ref = sorted(mapped)[0]
        send_chart_event(app, ref)
        self.assertEqual(app.session_state["fiche_identity"][2], ref)
        self.assertEqual(app.selectbox(key="catalog_district").value, "11")
        self.assertTrue(app.checkbox(key="priority_28079_rehabilita").value)

    def test_public_and_secondary_access(self):
        app = self.app(public="1", dev="1")
        self.assertFalse(any(s.key == "technical_navigation" for s in app.selectbox))
        self.assertTrue(app.checkbox(key="priority_28079_rehabilita").disabled)
        self.assertTrue(app.checkbox(key="priority_28079_prtr").disabled)
        self.assertFalse(any(c.key == "show_rehabilita_cases" for c in app.checkbox))
        self.assertTrue(any("Consulta bloqueada" in i.value for i in app.info))

    def test_private_secondary_cases(self):
        app = self.app(dev="1")
        self.assertTrue(any(s.key == "technical_navigation" for s in app.selectbox))
        app.checkbox(key="show_rehabilita_cases").check().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(s.key == "rehabilita_call" for s in app.multiselect))
        app.selectbox(key="technical_navigation").set_value("Consulta técnica · direcciones").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Consulta técnica completa" in c.value for c in app.caption))
