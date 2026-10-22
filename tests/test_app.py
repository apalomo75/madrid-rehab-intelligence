"""Smoke tests con resultados reales locales; se omiten si no se ha ejecutado sesión 2."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


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
        picker = next(
            w for w in app.selectbox if w.label == "Consultar ficha por identificador catastral"
        )
        picker.select(picker.options[1]).run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Ficha del objeto catastral", [w.value for w in app.subheader])

    def test_scope_and_grade_filters_keep_consistent_counts(self):
        app = self.app()
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
        level = next(w for w in app.selectbox if w.label == "Nivel de vinculación")
        level.select("physical_status").run()
        self.assertEqual(app.metric[2].value, "0")
        status = next(w for w in app.selectbox if w.label == "Estado de vinculación")
        status.select("confirmed").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[1].value, "0")
