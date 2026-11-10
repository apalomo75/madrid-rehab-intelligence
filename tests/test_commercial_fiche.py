"""Commercial interpretation rules and real map-free navigation regressions."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab.commercial_fiche import Quality, build_model


class ModelTests(unittest.TestCase):
    def model(self, **overrides):
        params = dict(
            code="28079",
            name="Madrid",
            identifier="9540103VK3794B",
            kind="cp",
            cp=pd.DataFrame([{"source_date": "2026-08-21"}]),
            construction=pd.DataFrame(),
            accesses=pd.DataFrame(),
            energy=pd.DataFrame(),
            grants=pd.DataFrame(),
            events=pd.DataFrame(),
            states={"energy": Quality.PARTIAL},
        )
        params.update(overrides)
        return build_model(**params)

    def test_missing_and_null_data(self):
        m = self.model(
            construction=pd.DataFrame(
                [{"current_use": None, "construction_oldest_year": float("nan")}]
            )
        )
        self.assertTrue(all(e.value is None for e in m.characteristics))
        self.assertFalse(m.energy)
        self.assertTrue(any("certificado energético" in s for s in m.recommendations))
        self.assertFalse(any("rehabilitar" in s for s in m.recommendations))

    def test_plural_uses_year_scope_and_no_sum(self):
        m = self.model(
            construction=pd.DataFrame(
                [
                    {
                        "building_id": "one",
                        "source_feature_type": "Building",
                        "current_use": "1_residential",
                        "construction_oldest_year": 1890,
                        "dwellings_raw": "11",
                    },
                    {
                        "building_id": "part",
                        "source_feature_type": "BuildingPart",
                        "current_use": "4_2_retail",
                        "construction_oldest_year": 1950,
                        "dwellings_raw": "2",
                    },
                ]
            )
        )
        self.assertEqual(
            {e.value for e in m.characteristics if e.label == "Uso declarado"},
            {"Residencial", "Comercio"},
        )
        self.assertEqual(
            {e.value for e in m.characteristics if e.label.startswith("Años")}, {1890, 1950}
        )
        self.assertTrue(
            all(e.quality == Quality.PARCEL for e in m.characteristics if e.value is not None)
        )
        self.assertFalse(any(e.value == 13 for e in m.characteristics))
        self.assertTrue(any("financiación" in s for s in m.recommendations))

    def test_access_plurality_and_postal_identity(self):
        postal = {
            "original": "CALLE DE BAILÉN 16",
            "id": "version",
            "access_id": "access",
            "refs": '["9540103VK3794B", "other"]',
        }
        accesses = pd.DataFrame(
            [dict(access_id=a, link_status="confirmed_access_parcel") for a in ["a", "b", "b"]]
        )
        m = self.model(postal=postal, accesses=accesses)
        self.assertEqual(m.title, "CALLE DE BAILÉN 16 — Madrid")
        self.assertEqual(next(e.value for e in m.identity if e.label.startswith("Accesos")), 2)
        self.assertTrue(any("portal" in s for s in m.recommendations))

    def test_energy_scopes_and_ambiguous_not_confirmed(self):
        energy = pd.DataFrame(
            [
                dict(
                    certificate_id=str(i),
                    scope=scope,
                    observation_date="2025-01-01",
                    consumption_rating="E",
                    emissions_rating="D",
                    source_id="capture",
                    link_level=level,
                    identity_status="unique_registration_content",
                    date_after_capture=False,
                )
                for i, (scope, level) in enumerate(
                    [("individual_unit", "A"), ("whole_building", "A"), ("unknown", "D")]
                )
            ]
        )
        m = self.model(energy=energy)
        self.assertEqual(len(m.energy), 3)
        self.assertEqual(sum(e.quality == Quality.PARCEL for e in m.energy), 2)
        self.assertEqual(m.energy[0].scope, "individual_unit")
        self.assertFalse(any("certificado energético" in s for s in m.recommendations))
        energy.loc[0, "date_after_capture"] = True
        self.assertEqual(self.model(energy=energy).energy[0].quality, Quality.AMBIGUOUS)

    def test_historical_conservation_and_award(self):
        events = pd.DataFrame(
            [
                dict(
                    event_type=k,
                    date="2018-01-01",
                    date_semantics="resolution_date",
                    administrative_status="ARCHIVADO",
                    source_file="source",
                    event_id=k,
                    match_status="confirmed",
                    identity_conflict=False,
                )
                for k in ["order", "ite_pending", "iee_pending"]
            ]
        )
        grants = pd.DataFrame(
            [
                dict(
                    programa="P3",
                    importe_concedido=10000.0,
                    expediente_id="case",
                    match_status="confirmed",
                    fecha_concesion=None,
                )
            ]
        )
        m = self.model(events=events, grants=grants)
        self.assertEqual(m.grants[0].value["Concesión del expediente (€)"], 10000.0)
        self.assertIn("no contrastada", m.grants[0].period)
        self.assertTrue(any("compatibilidad" in s for s in m.recommendations))
        self.assertTrue(any("resultado vigente" in s for s in m.recommendations))
        self.assertTrue(all("no acredita" in e.limitations for e in m.conservation))

    def test_grant_cases_are_unique_without_discarding_ambiguity(self):
        rows = pd.DataFrame(
            [
                dict(
                    programa="P4",
                    importe_concedido=100.0,
                    expediente_id="case",
                    match_status=status,
                )
                for status in ["confirmed", "confirmed_reference"]
            ]
        )
        self.assertEqual(len(self.model(grants=rows).grants), 1)
        rows.loc[1, "match_status"] = "ambiguous"
        m = self.model(grants=rows)
        self.assertEqual(m.grants[0].quality, Quality.AMBIGUOUS)
        self.assertIn("ambiguous", m.grants[0].value["Estados documentales"])
        self.assertFalse(any("compatibilidad" in r for r in m.recommendations))

    def test_unknown_coverage_is_not_empty_capture(self):
        for state in [Quality.UNAVAILABLE, Quality.UNCOVERED]:
            m = self.model(code="28065", states={"energy": state, "events": Quality.UNCOVERED})
            self.assertEqual(m.identity[0].quality, Quality.UNCOVERED)
            self.assertFalse(m.recommendations)

    def test_unknown_use_does_not_imply_nonresidential(self):
        m = self.model(construction=pd.DataFrame([{"current_use": "unknown"}]))
        self.assertFalse(any("financiación" in s for s in m.recommendations))

    def test_bu_does_not_inherit_parcel_recommendations(self):
        m = self.model(kind="bu")
        self.assertFalse(m.recommendations)
        self.assertFalse(m.energy)
        self.assertFalse(m.grants)


class RealCommercialTests(unittest.TestCase):
    def test_six_real_cases(self):
        from benchmark_commercial_fiche import real_cases
        from madrid_rehab.cadastral_identity import resolve_object
        from madrid_rehab.commercial_data import load_fiche

        for label, code, ref in real_cases():
            with self.subTest(case=label):
                status, cp = resolve_object(code, ref, "cp")
                self.assertFalse(cp.empty, status)
                m, tables, errors, _ = load_fiche(code, code, ref, cp)
                self.assertFalse(errors)
                if label == "Bailén 16":
                    self.assertEqual(
                        next(e.value for e in m.identity if e.label.startswith("Accesos")), 2
                    )
                    self.assertIn(1890, [e.value for e in m.characteristics])
                    self.assertFalse(m.energy)
                    self.assertFalse(m.grants)
                    self.assertEqual([e.label for e in m.conservation], ["declaration"])
                elif label == "Madrid CEEE":
                    self.assertTrue(any(e.quality == Quality.PARCEL for e in m.energy))
                elif label == "Madrid PRTR":
                    self.assertTrue(any(e.quality == Quality.PARCEL for e in m.grants))
                elif label == "Madrid conservación":
                    self.assertTrue(
                        any(
                            e.label in {"order", "ite_pending", "iee_pending"}
                            for e in m.conservation
                        )
                    )
                elif label.startswith("Getafe"):
                    self.assertGreater(len(tables["construction"]), 100)
                    self.assertEqual(m.states["events"], Quality.UNCOVERED)
                else:
                    self.assertFalse(m.energy or m.grants or m.conservation)
                    self.assertTrue(m.recommendations)

    def test_search_open_return_and_new_search(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0", "MADRID_REHAB_DEMO": "0"}):
            app = AppTest.from_string(
                "from madrid_rehab.address_view import render\nrender()", default_timeout=120
            ).run()
            app.text_input(key="postal_street").set_value("CALLE BAILEN 16")
            next(b for b in app.button if b.label == "Buscar").click().run()
            app.selectbox(key="postal_result_choice").set_value(self.first_bailen_id()).run()
            next(b for b in app.button if b.label == "Abrir ficha del inmueble").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["fiche_identity"], ("28079", "cp", "9540103VK3794B"))
            self.assertTrue(any("BAILÉN 16" in h.value for h in app.subheader))
            self.assertEqual(len(app.tabs), 6)
            self.assertTrue(any(e.label.startswith("Detalles técnicos") for e in app.expander))
            next(b for b in app.button if b.label == "Volver a los resultados").click().run()
            self.assertNotIn("postal_open", app.session_state)
            self.assertEqual(app.text_input(key="postal_street").value, "CALLE BAILEN 16")
            app.text_input(key="postal_street").set_value("CALLE BAILEN 12")
            next(b for b in app.button if b.label == "Buscar").click().run()
            self.assertIsNone(app.selectbox(key="postal_result_choice").value)
            self.assertFalse(app.exception)

    @staticmethod
    def first_bailen_id():
        from madrid_rehab.address_search import search

        return search("28079", "CALLE BAILEN 16")[0][0]["id"]

    def test_public_and_bu_skip_evidence_retrieval(self):
        from madrid_rehab.commercial_data import load_fiche

        with (
            patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}),
            patch("madrid_rehab.energy_view.read") as read,
        ):
            m, _, _, _ = load_fiche("28079", "Madrid", "ref", pd.DataFrame())
            self.assertFalse(m.energy or m.grants or m.conservation)
            read.assert_not_called()
        with (
            patch("madrid_rehab.commercial_data.grant_records") as grants,
            patch("madrid_rehab.conservation_view.parcel_evidence") as events,
        ):
            m, _, _, _ = load_fiche("28079", "Madrid", "bu", pd.DataFrame(), kind="bu")
            self.assertFalse(m.energy or m.grants or m.conservation)
            grants.assert_not_called()
            events.assert_not_called()

    def test_failed_source_not_interpreted_as_no_records(self):
        from madrid_rehab.commercial_data import load_fiche

        with patch(
            "madrid_rehab.commercial_data.grant_records", side_effect=ValueError("incompatible")
        ):
            from madrid_rehab.cadastral_identity import resolve_object

            _, objects = resolve_object("28079", "9540103VK3794B", "cp")
            m, _, errors, _ = load_fiche("28079", "Madrid", "9540103VK3794B", objects)
            self.assertEqual(m.states["grants"], Quality.UNAVAILABLE)
            self.assertIn("grants", errors)

    def test_real_case_artifact_is_json_serializable(self):
        path = Path("reports/session_21_commercial_fiche/real_cases.json")
        if not path.exists():
            self.skipTest("Benchmark artifact not generated")
        data = json.loads(path.read_text())
        self.assertEqual(len(data["cases"]), 6)


if __name__ == "__main__":
    unittest.main()
