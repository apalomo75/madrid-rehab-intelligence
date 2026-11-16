"""Bilingual public journeys over immutable local evidence; not visual validation."""

import ast
import os
from pathlib import Path
from string import Formatter
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab import i18n


class DictionaryTests(unittest.TestCase):
    def test_spanish_default_and_safe_fallback(self):
        with patch.object(i18n._st, "session_state", {}):
            self.assertEqual(i18n.language(), "es")
            self.assertEqual(i18n.t("nav.explore"), "Explorar inmuebles")
        with patch.object(i18n, "language", return_value="en"):
            self.assertEqual(i18n.t("nav.explore"), "Explore properties")
            self.assertEqual(i18n.t("missing.key"), "missing.key")
            with patch.dict(i18n.MESSAGES, {"temporary": {"es": "Dato {count:,}"}}):
                self.assertEqual(i18n.t("temporary", count=1234), "Dato 1,234")

    def test_dictionary_integrity(self):
        spanish = []
        for key, message in i18n.MESSAGES.items():
            with self.subTest(key=key):
                self.assertEqual(set(message), {"es", "en"})
                self.assertTrue(message["es"])
                self.assertTrue(message["en"])

                def placeholders(s):
                    return {field for _, field, _, _ in Formatter().parse(s) if field}

                self.assertEqual(placeholders(message["es"]), placeholders(message["en"]))
                spanish.append(message["es"])
        # Templates may intentionally repeat a static phrase, but keys remain unique.
        self.assertGreater(len(set(spanish)), 400)

    def test_critical_warnings_and_original_data(self):
        from madrid_rehab.commercial_filters import PUBLIC_BLOCK
        from madrid_rehab.commercial_fiche import Quality

        with patch.object(i18n, "language", return_value="en"):
            self.assertIn("External publication blocked", i18n.translate(PUBLIC_BLOCK))
            self.assertEqual(
                i18n.translate(str(Quality.UNCOVERED)), "Source not covered for this municipality"
            )
            address = "CALLE DE ALCALÁ 25 — Madrid"
            self.assertEqual(i18n.translate(address), address)
            self.assertEqual(i18n.t("explore.area_label", area="441:4469"), "Area 441:4469")
            self.assertEqual(i18n.translate("12345"), "12345")
            frame = pd.DataFrame(
                {
                    "Dirección original": [address],
                    "Concesión del expediente (€)": [1200.50],
                    "Calidad": [str(Quality.PARCEL)],
                }
            )
            before = frame.copy(deep=True)
            translated = i18n.localize_frame(frame)
            pd.testing.assert_frame_equal(frame, before)
            self.assertEqual(translated["Original address"].iloc[0], address)
            self.assertEqual(translated["Case award (€)"].iloc[0], 1200.50)
            self.assertEqual(translated["Quality"].iloc[0], "Information linked to a parcel")

    def test_html_export_translation_preserves_identity_and_restrictions(self):
        from madrid_rehab import demo
        from madrid_rehab.cadastral_identity import resolve_object

        ref = "0010510VK4701A"
        cp = resolve_object("28079", ref, "cp")[1]
        document = demo.export_html("28079", "Madrid", ref, cp)
        with patch.object(i18n, "language", return_value="es"):
            self.assertEqual(i18n.localize_html(document), document)
        with patch.object(i18n, "language", return_value="en"):
            translated = i18n.localize_html(document)
            self.assertIn('lang="en"', translated)
            self.assertIn(ref, translated)
            self.assertIn("Evidence excluded from the export", translated)
            self.assertNotIn("<title>Ficha", translated)
            self.assertIn("Dirección General del Catastro", translated)
            self.assertNotIn("ITE/IEE inspection results", translated)

    def test_static_public_messages_are_translated(self):
        files = [
            "about_view",
            "commercial_explorer",
            "commercial_catalog_view",
            "address_view",
            "commercial_view",
            "municipal_fiche",
            "plan_rehabilita_view",
            "rec_view",
        ]
        display = {
            "title",
            "subheader",
            "caption",
            "info",
            "warning",
            "error",
            "expander",
            "button",
            "checkbox",
            "selectbox",
            "text_input",
            "link_button",
        }
        missing = []
        with patch.object(i18n, "language", return_value="en"):
            for module in files:
                for node in ast.walk(ast.parse(Path(f"src/madrid_rehab/{module}.py").read_text())):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in display
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                    ):
                        text = node.args[0].value
                        if any(
                            word in text.lower()
                            for word in [
                                "consulta",
                                "seleccion",
                                "información",
                                "fuente",
                                "parcela",
                                "dirección",
                                "expediente",
                                "proyecto",
                                "incidencia",
                            ]
                        ):
                            if i18n.translate(text) == text:
                                missing.append((module, text))
        self.assertEqual(missing, [])


class PublicLanguageTests(unittest.TestCase):
    def app(self, public="0"):
        env = patch.dict(
            os.environ,
            {"MADRID_REHAB_PUBLIC": public, "MADRID_REHAB_DEMO": "0", "MADRID_REHAB_DEV": "0"},
        )
        env.start()
        self.addCleanup(env.stop)
        app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=180).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="language_selector").value, "ES")
        return app

    def switch(self, app, language):
        app.radio(key="language_selector").set_value(language).run()
        self.assertFalse(app.exception)

    def test_map_fiche_and_pages_survive_es_en_es(self):
        app = self.app()
        app.selectbox(key="catalog_district").set_value("11").run()
        app.checkbox(key="priority_28079_rehabilita").check().run()
        prefix = "municipal_28079__cp_catalog_local_OR_rehabilita"
        app.selectbox(key=prefix + "_list_page").set_value(1).run()
        next(b for b in app.button if b.label == "Abrir ficha").click().run()
        identity = app.session_state["fiche_identity"]
        count = app.metric[0].value
        for language in ["EN", "ES"]:
            self.switch(app, language)
            self.assertEqual(app.session_state["fiche_identity"], identity)
            self.assertEqual(app.session_state[prefix + "_saved_page"], 1)
            self.assertEqual(app.selectbox(key="catalog_municipality").value, "28079")
            self.assertEqual(app.selectbox(key="catalog_district").value, "11")
            self.assertTrue(app.checkbox(key="priority_28079_rehabilita").value)
            self.assertEqual(app.radio(key="priority_logic_28079").value, "OR")
            self.assertEqual(app.metric[0].value, count)
            area_labels = app.selectbox(key=prefix + "_area").options
            expected = "Area " if language == "EN" else "Área "
            self.assertTrue(all(label.startswith(expected) for label in area_labels[1:]))
            self.assertEqual(app.radio(key="city_navigation").value, "Explorar inmuebles")
            self.assertEqual(
                app.title[0].value,
                "Explore properties" if language == "EN" else "Explorar inmuebles",
            )
        self.switch(app, "EN")
        next(b for b in app.button if b.label == "Back to the list").click().run()
        self.assertIsNone(app.session_state["fiche_identity"])
        self.assertEqual(app.selectbox(key=prefix + "_list_page").value, 1)

    def test_all_filters_logic_and_map_page_persist(self):
        app = self.app()
        for kind in ["energy", "ite", "rehabilita", "prtr"]:
            app.checkbox(key="priority_28079_" + kind).check().run()
        app.radio(key="priority_logic_28079").set_value("AND").run()
        count = app.metric[0].value
        self.switch(app, "EN")
        for kind in ["energy", "ite", "rehabilita", "prtr"]:
            self.assertTrue(app.checkbox(key="priority_28079_" + kind).value)
        self.assertEqual(app.radio(key="priority_logic_28079").value, "AND")
        self.assertEqual(app.metric[0].value, count)
        next(b for b in app.button if b.label == "Clear filters").click().run()
        prefix = "municipal_28079__cp_catalog_local_OR_"
        app.selectbox(key=prefix + "_map_page_all").set_value(2).run()
        self.switch(app, "ES")
        self.assertEqual(app.selectbox(key=prefix + "_map_page_all").value, 2)

    def test_postal_fiche_and_input_persist(self):
        app = self.app()
        app.radio(key="city_navigation").set_value("Buscar por dirección").run()
        app.text_input(key="postal_street").set_value("CL BAILEN")
        app.text_input(key="postal_number").set_value("12")
        next(b for b in app.button if b.label == "Buscar").click().run()
        result = app.selectbox(key="postal_result_choice")
        from madrid_rehab import commercial_catalog_store as catalog

        uid = catalog.search("28079", "CL BAILEN", "12", "")[0][0]["id"]
        result.set_value(uid).run()
        next(b for b in app.button if b.label == "Abrir ficha del inmueble").click().run()
        identity = app.session_state["fiche_identity"]
        for language in ["EN", "ES"]:
            self.switch(app, language)
            self.assertEqual(app.session_state["fiche_identity"], identity)
            self.assertEqual(app.text_input(key="postal_street").value, "CL BAILEN")
            self.assertEqual(app.text_input(key="postal_number").value, "12")
            self.assertEqual(app.selectbox(key="postal_result_choice").value, uid)
            if language == "EN":
                self.assertTrue(
                    all(
                        "PORTAL" not in option
                        for option in app.selectbox(key="postal_result_choice").options
                    )
                )
            self.assertEqual(app.radio(key="city_navigation").value, "Buscar por dirección")

    def test_about_and_public_restrictions(self):
        app = self.app(public="1")
        prtr = app.checkbox(key="priority_28079_prtr")
        self.assertEqual(prtr.label, "Ayudas NextGenerationEU")
        self.assertEqual(prtr.proto.help, i18n.MESSAGES["filters.prtr_help"]["es"])
        self.assertTrue(prtr.disabled)
        self.switch(app, "EN")
        prtr = app.checkbox(key="priority_28079_prtr")
        self.assertEqual(prtr.label, "EU recovery grants (NextGenerationEU)")
        self.assertEqual(prtr.proto.help, i18n.MESSAGES["filters.prtr_help"]["en"])
        self.assertTrue(app.checkbox(key="priority_28079_rehabilita").disabled)
        self.assertTrue(app.checkbox(key="priority_28079_prtr").disabled)
        self.assertTrue(any("External publication blocked" in w.value for w in app.warning))
        self.assertFalse(any(s.key == "technical_navigation" for s in app.selectbox))
        app.radio(key="city_navigation").set_value("Acerca del proyecto").run()
        self.assertEqual(app.title[0].value, "About Madrid Rehab Intelligence")
        content = "\n".join(m.value for m in app.markdown)
        self.assertIn("personal project", content)
        self.assertIn("does not determine whether a building needs renovation", content)
        self.assertIn("Recovery, Transformation and Resilience", content)
        self.switch(app, "ES")
        self.assertEqual(app.title[0].value, "Acerca de Madrid Rehab Intelligence")
        self.assertEqual(app.radio(key="city_navigation").value, "Acerca del proyecto")

    def test_pilot_identity_and_secondary_cases(self):
        app = self.app()
        app.selectbox(key="catalog_municipality").set_value("28065").run()
        next(b for b in app.button if b.label == "Abrir ficha").click().run()
        identity = app.session_state["fiche_identity"]
        self.switch(app, "EN")
        self.assertEqual(app.session_state["fiche_identity"], identity)
        self.assertEqual(app.selectbox(key="catalog_municipality").value, "28065")
        self.assertFalse(any(s.key == "catalog_district" for s in app.selectbox))
        app.selectbox(key="catalog_municipality").set_value("28079").run()
        app.checkbox(key="show_rehabilita_cases").check().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.label == "Call for applications" for m in app.multiselect))
        self.assertTrue(any(m.label == "Work type · source component" for m in app.multiselect))
        self.switch(app, "ES")
        self.assertTrue(app.checkbox(key="show_rehabilita_cases").value)
