"""Smoke tests con resultados reales locales; se omiten si no se ha ejecutado sesión 2."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest
import pandas as pd


@unittest.skipUnless(
    Path("data/processed/session_2/quality_metrics.json").exists(),
    "Ejecutar primero sesión 2 para pruebas con datos reales",
)
class LocalAppTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file("src/madrid_rehab/app.py", default_timeout=45).run()

    def test_real_default_view_and_detail(self):
        app = self.app()
        self.assertEqual(len(app.exception), 0)
        self.assertGreater(int(app.metric[0].value.replace(",", "")), 0)
        objects = pd.read_parquet("data/processed/session_2/pilot_buildings.parquet")
        identifier = objects[objects.current_use.eq("1_residential")].building_id.iloc[0]
        # AppTest no representa WebGL; browser_session3.py exige clic real.
        app.session_state["selected_bu"] = identifier
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Ficha del objeto catastral", [w.value for w in app.subheader])

    def test_scope_and_grade_filters_keep_consistent_counts(self):
        app = self.app()
        app.radio[0].set_value("Exploración energética").run()
        scope = next(w for w in app.selectbox if w.label == "Ámbito energético")
        scope.select("dwelling").run()
        before = int(app.metric[1].value.replace(",", ""))
        grade = next(
            w for w in app.selectbox if w.label == "Calificación energética del certificado"
        )
        grade.select("A").run()
        self.assertEqual(len(app.exception), 0)
        self.assertLessEqual(int(app.metric[1].value.replace(",", "")), before)

    def test_physical_confirmed_filter_never_shows_dwelling_grade_as_building(self):
        app = self.app()
        app.radio[0].set_value("Exploración energética").run()
        level = next(w for w in app.selectbox if w.label == "Nivel de vinculación")
        level.select("physical_status").run()
        self.assertEqual(app.metric[2].value, "0")
        status = next(w for w in app.selectbox if w.label == "Estado de vinculación")
        status.select("confirmed").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[1].value, "0")

    def test_selection_persists_and_clear_button_removes_detail(self):
        app = self.app()
        b = pd.read_parquet("data/processed/session_2/pilot_buildings.parquet")
        identifier = b[b.current_use.eq("1_residential")].building_id.iloc[0]
        app.session_state["selected_bu"] = identifier
        app.run().run()
        self.assertEqual(app.session_state["selected_bu"], identifier)
        next(w for w in app.button if w.label == "Limpiar selección").click().run()
        self.assertIsNone(app.session_state["selected_bu"])
        self.assertNotIn("Ficha del objeto catastral", [w.value for w in app.subheader])

    def test_filters_exclude_selection_and_offline_mode_has_no_raster(self):
        app = self.app()
        b = pd.read_parquet("data/processed/session_2/pilot_buildings.parquet")
        app.session_state["selected_bu"] = b[b.current_use.ne("1_residential")].building_id.iloc[0]
        app.run()
        self.assertIsNone(app.session_state["selected_bu"])
        app.toggle[0].set_value(False).run()
        self.assertEqual(len(app.exception), 0)
        chart = app.get("deck_gl_json_chart")[0]
        import base64
        import json

        style = json.loads(chart.proto.json)["mapStyle"]
        self.assertEqual(json.loads(base64.b64decode(style.split(",", 1)[1]))["sources"], {})

    def test_energy_panel_lists_all_parcel_certificates_despite_map_filter(self):
        app = self.app()
        c = pd.read_parquet("data/processed/session_2/pilot_certificates.parquet")
        links = pd.read_parquet("data/processed/session_2/building_certificate_contexts.parquet")
        b = pd.read_parquet("data/processed/session_2/pilot_buildings.parquet")
        eligible = set(b[b.current_use.eq("1_residential")].building_id)
        counts = (
            links[links.building_id.isin(eligible)].groupby("building_id").certificate_id.nunique()
        )
        identifier = counts.idxmax()
        app.session_state["selected_bu"] = identifier
        app.run()
        self.assertEqual(len(app.exception), 0)
        ids = links.loc[links.building_id.eq(identifier), "certificate_id"]
        parcel_certificates = c[c.record_id.isin(ids)]
        expected = parcel_certificates.record_id.nunique()
        app.radio[0].set_value("Exploración energética").run()
        grade = parcel_certificates.cal_norenovglobal.value_counts().index[0]
        next(
            w for w in app.selectbox if w.label == "Calificación energética del certificado"
        ).select(grade).run()
        self.assertEqual(app.session_state["selected_bu"], identifier)
        table = next(w.value for w in app.dataframe if "Código de certificado" in w.value)
        self.assertEqual(len(table), expected)
        self.assertGreater(expected, 1)
        self.assertIn("Ámbito original", table)

    def test_real_selected_object_without_certificates_has_explicit_empty_state(self):
        app = self.app()
        b = pd.read_parquet("data/processed/session_2/pilot_buildings.parquet")
        links = pd.read_parquet("data/processed/session_2/building_certificate_contexts.parquet")
        identifier = b[
            b.current_use.eq("1_residential") & ~b.building_id.isin(links.building_id)
        ].building_id.iloc[0]
        app.session_state["selected_bu"] = identifier
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("Esto no demuestra ausencia de certificación" in w.value for w in app.info)
        )
        self.assertFalse(any("Código de certificado" in w.value for w in app.dataframe))
