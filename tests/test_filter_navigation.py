"""Commercial list/map selection context in Streamlit (not WebGL validation)."""

import os
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


class FilterNavigationTests(unittest.TestCase):
    def test_list_fiche_return_and_filter_persistence(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}):
            app = AppTest.from_string(
                "from madrid_rehab.commercial_catalog_view import render\nrender()",
                default_timeout=180,
            ).run()
            self.assertFalse(app.exception)
            app.checkbox(key="priority_28079_rehabilita").check().run()
            self.assertFalse(app.exception)
            count = app.metric[0].value
            self.assertEqual(count, "1,919")
            next(b for b in app.button if b.label == "Abrir ficha").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value, count)
            self.assertIsNotNone(app.session_state["fiche_identity"])
            next(b for b in app.button if b.label == "Volver al mapa").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.checkbox(key="priority_28079_rehabilita").value)
            self.assertEqual(app.metric[0].value, count)
            next(b for b in app.button if b.label == "Limpiar filtros").click().run()
            self.assertFalse(app.checkbox(key="priority_28079_rehabilita").value)
            self.assertFalse(app.exception)

    def test_public_restricted_controls(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            app = AppTest.from_string(
                "from madrid_rehab.commercial_catalog_view import render\nrender()",
                default_timeout=180,
            ).run()
            self.assertFalse(app.exception)
            self.assertTrue(app.checkbox(key="priority_28079_prtr").disabled)
            self.assertTrue(app.checkbox(key="priority_28079_rehabilita").disabled)
            self.assertTrue(any("Publicación externa bloqueada" in w.value for w in app.warning))
