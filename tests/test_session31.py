"""Scope classification and mixed-certificate parcel reconciliation."""

import unittest
from unittest.mock import patch

import pandas as pd

from madrid_rehab.energy_scope import classify, memberships, restrict


class ScopeTests(unittest.TestCase):
    def test_original_types(self):
        for original, expected in [
            ("ViviendaIndividualEnBloque", "individual_unit"),
            ("ViviendaUnifamiliar", "individual_unit"),
            ("BloqueDeViviendaCompleto", "whole_building"),
            ("EdificioUsoTerciario", "whole_building"),
            ("LocalUsoTerciario", "commercial_unit"),
            ("", "unknown"),
            (None, "unknown"),
            ("inventado", "unknown"),
        ]:
            self.assertEqual(classify(original), expected)

    def test_mixed_parcel_and_quarantine(self):
        certificates = pd.DataFrame(
            {
                "certificate_id": list("abcd"),
                "edif_tipo": [
                    "ViviendaIndividualEnBloque",
                    "BloqueDeViviendaCompleto",
                    "",
                    "LocalUsoTerciario",
                ],
                "identity_status": ["unique_registration_content"] * 3 + ["conflict"],
                "date_after_capture": [False] * 4,
            }
        )
        links = pd.DataFrame(
            {"certificate_id": list("aabcd"), "parcel_ref14": ["p"] * 5, "link_level": ["A"] * 5}
        )
        rows = memberships(certificates, links)
        self.assertEqual(len(rows), 3)
        self.assertEqual(set(rows.scope_group), {"individual_unit", "whole_building", "unknown"})
        index = pd.DataFrame({"parcel_ref14": ["p", "q"]})
        groups = {g: frozenset(f.parcel_ref14) for g, f in rows.groupby("scope_group")}
        with (
            patch("madrid_rehab.energy_scope._memberships", return_value=groups),
            patch("madrid_rehab.energy_view.root_path") as root,
            patch("pathlib.Path.stat"),
        ):
            root.return_value = __import__("pathlib").Path("unused")
            for code in ("28079", "28005", "28007", "28065", "28074", "28092"):
                for scope in ("individual_unit", "whole_building", "unknown"):
                    self.assertEqual(restrict(index, code, scope).parcel_ref14.tolist(), ["p"])
            self.assertEqual(len(restrict(index, "28079", "all")), 2)


class FinalInterfaceTests(unittest.TestCase):
    def test_scope_participates_in_or_and(self):
        from madrid_rehab import commercial_filters as filters

        index = pd.DataFrame(
            {
                "parcel_ref14": ["p", "q", "r"],
                "energy": [True, True, False],
                "rehabilita": [False, True, True],
                "prtr": [False] * 3,
            }
        )
        with (
            patch.object(filters.store, "parcel_index", return_value=index),
            patch.object(filters.store, "mode", return_value="local"),
            patch.object(filters, "inspection_refs", return_value=()),
            patch("madrid_rehab.energy_scope.restrict", return_value=index.iloc[:1]),
        ):
            self.assertEqual(
                filters.query(
                    "28079", ["energy", "rehabilita"], "OR", scope="whole_building"
                ).parcel_ref14.tolist(),
                ["p", "q", "r"],
            )
            self.assertEqual(
                len(
                    filters.query("28079", ["energy", "rehabilita"], "AND", scope="whole_building")
                ),
                0,
            )
            self.assertEqual(len(filters.query("28079")), 3)

    def test_labels_dates_and_plural(self):
        from madrid_rehab import i18n
        from madrid_rehab.commercial_filters import result_label

        self.assertEqual(result_label("REF1", {"address": ""}, "Madrid"), "REF1 · Madrid")
        self.assertEqual(
            result_label("REF1", {"address": "CALLE REAL 1"}, "Madrid"), "CALLE REAL 1"
        )
        for lang, expected in [("es", "3 de febrero de 2024"), ("en", "3 February 2024")]:
            with patch.object(i18n, "language", return_value=lang):
                self.assertEqual(i18n.readable_date("2024-02-03"), expected)
                self.assertIn(
                    "1 certificate" if lang == "en" else "1 certificado",
                    i18n.t("ux.certificates", count=1),
                )
                self.assertIn(
                    "2 certificates" if lang == "en" else "2 certificados",
                    i18n.t("ux.certificates", count=2),
                )
                self.assertEqual(i18n.readable_date("sin fecha"), "sin fecha")


class PublicBundleTests(unittest.TestCase):
    def test_scope_district_language_and_fiche(self):
        import os
        from pathlib import Path
        from streamlit.testing.v1 import AppTest

        bundle = Path("data/deployment/madrid_rehab_v1_02")
        if not bundle.exists():
            self.skipTest("Real production bundle unavailable")
        with patch.dict(
            os.environ,
            {
                "MADRID_REHAB_PUBLIC": "1",
                "MADRID_REHAB_OFFLINE": "1",
                "MADRID_REHAB_BUNDLE_DIR": str(bundle),
            },
        ):
            app = AppTest.from_string(
                "from madrid_rehab.i18n import language_selector\nlanguage_selector()\n"
                "from madrid_rehab.commercial_catalog_view import render\nrender()",
                default_timeout=180,
            ).run()
            self.assertFalse(app.exception)
            app.selectbox(key="energy_scope_28079").set_value("whole_building").run()
            self.assertEqual(app.metric[0].value, "18,953")
            app.selectbox(key="catalog_district").set_value("07").run()
            self.assertEqual(app.metric[0].value, "421")
            next(b for b in app.button if b.label == "Abrir ficha").click().run()
            identity = app.session_state["fiche_identity"]
            self.assertIsNotNone(identity)
            app.radio(key="language_selector").set_value("EN").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["fiche_identity"], identity)
            self.assertEqual(app.selectbox(key="energy_scope_28079").value, "whole_building")
            self.assertEqual(
                app.selectbox(key="energy_scope_28079").label, "Filter by certificate type"
            )
            self.assertTrue(app.checkbox(key="priority_28079_prtr").disabled)
            app.selectbox(key="catalog_district").set_value("11").run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.session_state["fiche_identity"])


if __name__ == "__main__":
    unittest.main()
