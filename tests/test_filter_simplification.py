"""Final public interface over the immutable v1_03 bundle; no WebGL claim."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from madrid_rehab import commercial_filters as filters
from madrid_rehab import production_bundle as bundle
from madrid_rehab.commercial_view import certificate_summary
from madrid_rehab.commercial_data import load_fiche


class CertificateSummaryTests(unittest.TestCase):
    def test_distributions_deduplicate_certificates_and_exclude_ambiguous(self):
        from madrid_rehab.commercial_fiche import Evidence, Quality

        records = [
            Evidence(
                "CEEE",
                {"Consumo": consumption, "Emisiones": emissions},
                "CEEE",
                identifier,
                quality,
                scope,
            )
            for identifier, scope, consumption, emissions, quality in [
                ("1", "individual_unit", "E", "E", Quality.PARCEL),
                ("1", "individual_unit", "E", "E", Quality.PARCEL),
                ("2", "individual_unit", "F", "E", Quality.PARCEL),
                ("3", "whole_building", "B", "C", Quality.PARCEL),
                ("4", "unknown", "G", "G", Quality.UNAVAILABLE),
            ]
        ]
        table = certificate_summary(records)
        self.assertEqual(table["N.º de certificados"].tolist(), [1, 2])
        self.assertEqual(table["Calificación de consumo"].tolist(), ["B (1)", "E (1) · F (1)"])
        self.assertEqual(table["Calificación de emisiones"].tolist(), ["C (1)", "E (2)"])


@unittest.skipUnless(
    Path("data/deployment/madrid_rehab_v1_03/manifest.json").exists(), "v1_03 unavailable"
)
class SimplificationTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(
            os.environ,
            {
                "MADRID_REHAB_PUBLIC": "1",
                "MADRID_REHAB_OFFLINE": "1",
                "MADRID_REHAB_BUNDLE_DIR": str(
                    Path("data/deployment/madrid_rehab_v1_03").resolve()
                ),
                "MADRID_REHAB_DEMO": "0",
                "MADRID_REHAB_PILOT": "0",
                "MADRID_REHAB_DEV": "0",
            },
        )
        env.start()
        self.addCleanup(env.stop)

    def test_checkboxes_scope_reset_prtr_logic_and_language(self):
        app = AppTest.from_string(
            "from madrid_rehab.i18n import language_selector\nlanguage_selector()\n"
            "from madrid_rehab.commercial_catalog_view import render\nrender()",
            default_timeout=180,
        ).run()
        self.assertFalse(app.exception)
        baseline = app.metric[0].value
        self.assertFalse(app.checkbox(key="priority_28079_energy").value)
        self.assertEqual(app.selectbox(key="energy_scope_28079").value, "any")
        app.checkbox(key="priority_28079_energy").check().run()
        self.assertEqual(
            int(app.metric[0].value.replace(",", "")), len(filters.query("28079", ["energy"]))
        )
        app.checkbox(key="priority_28079_energy").uncheck().run()
        self.assertEqual(app.metric[0].value, baseline)
        for scope in ("whole_building", "individual_unit", "other", "unknown"):
            app.selectbox(key="energy_scope_28079").set_value(scope).run()
            self.assertFalse(app.exception)
            self.assertTrue(app.checkbox(key="priority_28079_energy").value)
            expected = len(filters.query("28079", ["energy"], scope=scope))
            self.assertEqual(int(app.metric[0].value.replace(",", "")), expected)
            app.checkbox(key="priority_28079_energy").uncheck().run()
            self.assertEqual(app.selectbox(key="energy_scope_28079").value, "any")
            self.assertEqual(app.metric[0].value, baseline)
        app.checkbox(key="priority_28079_prtr").check().run()
        self.assertFalse(app.checkbox(key="priority_28079_prtr").disabled)
        self.assertEqual(app.metric[0].value, "3,300")
        self.assertFalse(any(s.key == "prtr_program_28079" for s in app.selectbox))
        energy = set(filters.query("28079", ["energy"]).parcel_ref14)
        prtr = set(filters.query("28079", ["prtr"]).parcel_ref14)
        app.selectbox(key="energy_scope_28079").set_value("individual_unit").run()
        scoped = set(filters.query("28079", ["energy"], scope="individual_unit").parcel_ref14)
        for logic, expected in (("OR", scoped | prtr), ("AND", scoped & prtr)):
            app.radio(key="priority_logic_28079").set_value(logic).run()
            self.assertFalse(app.exception)
            self.assertEqual(int(app.metric[0].value.replace(",", "")), len(expected))
        app.selectbox(key="energy_scope_28079").set_value("any").run()
        for logic, expected in (("OR", energy | prtr), ("AND", energy & prtr)):
            app.radio(key="priority_logic_28079").set_value(logic).run()
            self.assertEqual(int(app.metric[0].value.replace(",", "")), len(expected))
        app.radio(key="language_selector").set_value("EN").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.checkbox(key="priority_28079_energy").value)
        self.assertEqual(
            app.selectbox(key="energy_scope_28079").label, "Filter by certificate type"
        )
        next(b for b in app.button if b.label == "Clear filters").click().run()
        self.assertEqual(app.selectbox(key="energy_scope_28079").value, "any")
        self.assertFalse(app.checkbox(key="priority_28079_energy").value)
        self.assertEqual(app.metric[0].value, baseline)

    def test_real_ribadavia_and_mixed_scopes(self):
        from madrid_rehab import energy_scope, energy_view, demo
        from madrid_rehab.municipal_navigation import object_source

        def fiche(ref):
            root, path = object_source("28079", "cp")
            objects = demo.read(root, path, [("parcel_ref14", "==", ref)])
            return load_fiche("28079", "Madrid", ref, objects, public_catalog=True)

        with filters.store.connect() as db:
            rows = db.execute(
                "SELECT parcel_ref14,address FROM postal_labels WHERE upper(address) LIKE '%RIBADAVIA%' OR upper(address) LIKE '%SINESIO DELGADO%'"
            ).fetchall()
        candidates = [
            ref
            for ref, address in rows
            if ("RIBADAVIA" in address.upper() and "12" in address)
            or ("SINESIO DELGADO" in address.upper() and "42" in address)
        ]
        self.assertTrue(candidates)
        found = False
        for ref in set(candidates):
            model, _, errors, _ = fiche(ref)
            self.assertFalse(errors)
            table = certificate_summary(model.energy)
            if len(table) == 1 and table.iloc[0]["N.º de certificados"] == 5:
                self.assertEqual(
                    table.iloc[0].to_dict(),
                    {
                        "Ámbito": "Vivienda individual",
                        "N.º de certificados": 5,
                        "Calificación de consumo": "E (5)",
                        "Calificación de emisiones": "E (5)",
                    },
                )
                found = True
        self.assertTrue(found, candidates)
        certs = energy_view.read("municipalities/28079/certificates.parquet")
        links = energy_view.read("municipalities/28079/links.parquet")
        memberships = energy_scope.memberships(certs, links)
        mixed = memberships.groupby("parcel_ref14").scope_group.nunique()
        ref = mixed[mixed > 1].index[0]
        model, _, errors, _ = fiche(ref)
        self.assertFalse(errors)
        table = certificate_summary(model.energy)
        self.assertGreater(len(table), 1)
        self.assertTrue(table["N.º de certificados"].gt(0).all())
        self.assertEqual(table["N.º de certificados"].sum(), memberships.parcel_ref14.eq(ref).sum())
        self.assertTrue(bundle.allowed_prtr())


if __name__ == "__main__":
    unittest.main()
