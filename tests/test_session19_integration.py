"""Real enriched pilot records and map-independent CP/BU fiche routing."""

import json
import os
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab import enriched_cadastre as ec
from madrid_rehab.municipal_fiche import SECTIONS


class Session19Tests(unittest.TestCase):
    def test_real_five_products_and_exact_attributes(self):
        for code in json.loads((ec.ROOT / "manifest.json").read_text())["municipality_codes"]:
            with self.subTest(code=code):
                ec.metadata(code)
                relations = pd.read_parquet(ec.ROOT / code / "cp_bu_documentary_links.parquet")
                for cls in ("A", "B", "C"):
                    row = relations[relations.link_class.eq(cls)].iloc[0]
                    actual = ec.building(code, row.building_id)
                    expected = pd.read_parquet(
                        ec.ROOT / code / "buildings_enriched.parquet",
                        filters=[("building_id", "==", row.building_id)],
                    )
                    pd.testing.assert_frame_equal(actual, expected)
                    self.assertEqual(ec.links(code, row.building_id, "bu").link_class.iloc[0], cls)
                ref = relations[relations.link_class.eq("A")].cp_reference_normalized.iloc[0]
                records, issues = ec.parcel_buildings(code, ref)
                expected_ids = set(
                    relations.loc[
                        relations.link_class.eq("A") & relations.cp_reference_normalized.eq(ref),
                        "building_id",
                    ]
                )
                self.assertEqual(set(records.building_id), expected_ids)
                self.assertFalse(issues.link_class.eq("A").any())
                # Caller mutation never corrupts cached values.
                records.iloc[0, 0] = "mutated"
                self.assertEqual(set(ec.parcel_buildings(code, ref)[0].building_id), expected_ids)

    def test_map_free_fiche_navigation_and_no_evidence_transfer(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}):
            app = AppTest.from_string(
                """import streamlit as st
from madrid_rehab.municipal_fiche import render_fiche
code = st.selectbox("Municipio", ["28005", "28007", "28065", "28074", "28092"])
ref = st.text_input("Identidad", "0015301VK7801N")
render_fiche(code, code, ref)
""",
                default_timeout=120,
            ).run()
            for code in ("28005", "28007", "28065", "28074", "28092"):
                links = pd.read_parquet(
                    ec.ROOT / code / "cp_bu_documentary_links.parquet",
                    columns=["cp_reference_normalized", "link_class"],
                )
                refs = (
                    links[links.link_class.eq("A")].cp_reference_normalized.value_counts().index[:2]
                )
                app.selectbox[0].set_value(code)
                app.text_input[0].set_value(refs[0]).run()
                self.assertFalse(app.exception)
                self.assertEqual(tuple(t.label for t in app.tabs), SECTIONS)
                selected = next(
                    s for s in app.selectbox if s.label == "Construcción relacionada"
                ).value
                next(b for b in app.button if b.label == "Consultar construcción").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(tuple(app.session_state["fiche_identity"]), (code, "bu", selected))
                self.assertFalse(any("Expediente" in d.value.columns for d in app.dataframe))
                self.assertTrue(any("Tipo de objeto:" in m.value for m in app.markdown))
                next(b for b in app.button if b.label.startswith("Volver al objeto")).click().run()
                self.assertEqual(tuple(app.session_state["fiche_identity"]), (code, "cp", refs[0]))
                app.text_input[0].set_value(refs[1]).run()
                self.assertEqual(tuple(app.session_state["fiche_identity"]), (code, "cp", refs[1]))
                self.assertFalse(app.exception)

    def test_wrong_municipality_and_cache_bounds(self):
        with self.assertRaises(ValueError):
            ec.building("28065", "ES.SDGC.BU.000300100VK78C")
        self.assertEqual(ec._query.cache_info().maxsize, 32)
        self.assertEqual(ec._verify.cache_info().maxsize, 8)

    def test_map_context_survives_related_navigation(self):
        import test_municipal_map_events as events

        app = events.MapEventTests().make_app()
        app.selectbox(key="town").set_value("28005").run()
        app.text_input[0].set_value("0015301VK7801N").run()
        prefix = "municipal_28005__cp"
        zone = app.session_state[prefix + "_zone"]
        page_key = prefix + "_page_" + zone
        page = app.session_state[page_key]
        selected = app.session_state[prefix + "_selected"]
        next(b for b in app.button if b.label == "Consultar construcción").click().run()
        self.assertEqual(app.session_state[prefix + "_zone"], zone)
        self.assertEqual(app.session_state[page_key], page)
        self.assertEqual(app.session_state[prefix + "_selected"], selected)
        next(b for b in app.button if b.label.startswith("Volver al objeto")).click().run()
        self.assertEqual(tuple(app.session_state["fiche_identity"]), ("28005", "cp", selected))
        self.assertEqual(app.session_state[prefix + "_zone"], zone)
        next(b for b in app.button if b.label == "Consultar construcción").click().run()
        next(b for b in app.button if b.label == "Limpiar selección").click().run()
        self.assertIsNone(app.session_state["fiche_identity"])
        app.text_input[0].set_value(selected).run()
        self.assertEqual(tuple(app.session_state["fiche_identity"]), ("28005", "cp", selected))

    def test_bu_routes_and_parcel_evidence_is_never_called_for_bu(self):
        source = """import streamlit as st
from madrid_rehab.municipal_fiche import render_fiche
identifier = st.text_input("BU", "ES.SDGC.BU.000300100VK78C")
render_fiche("28005", "Alcalá de Henares", identifier, kind="bu")
"""
        relations = pd.read_parquet(ec.ROOT / "28005/cp_bu_documentary_links.parquet")
        with (
            patch("madrid_rehab.energy_view.render_energy_parcel") as energy,
            patch("madrid_rehab.municipal_fiche.render_prtr") as grants,
            patch("madrid_rehab.conservation_view.render_conservation_parcel") as conservation,
        ):
            app = AppTest.from_string(source, default_timeout=120).run()
            for cls in ("A", "B", "C"):
                row = relations[relations.link_class.eq(cls)].iloc[0]
                app.text_input[0].set_value(row.building_id).run()
                self.assertFalse(app.exception)
                self.assertTrue(
                    any(
                        "link_class" in d.value.columns and cls in d.value.link_class.values
                        for d in app.dataframe
                    )
                )
                energy.assert_not_called()
                grants.assert_not_called()
                conservation.assert_not_called()
                buttons = [b for b in app.button if b.label.startswith("Abrir parcela relacionada")]
                self.assertEqual(len(buttons), int(cls == "A"))
                if cls == "A":
                    buttons[0].click().run()
                    self.assertEqual(
                        tuple(app.session_state["fiche_identity"]),
                        ("28005", "cp", row.cp_reference_normalized),
                    )
                    energy.assert_called_once_with("28005", row.cp_reference_normalized)
                    grants.assert_called_once_with("28005", row.cp_reference_normalized)
                    energy.reset_mock()
                    grants.reset_mock()
                    conservation.reset_mock()
                    next(
                        b for b in app.button if b.label.startswith("Volver al objeto")
                    ).click().run()

    def test_real_cp_energy_and_unique_grants_survive_roundtrip(self):
        from madrid_rehab import demo, energy_view
        from madrid_rehab.regional_view import regional_root_path

        code, ref = "28005", "0015301VK7801N"
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}):
            expected_energy = energy_view.read(f"municipalities/{code}/links.parquet", ref)
            expected_grants = demo.read(
                regional_root_path(), "grant_parcel_links.parquet", [("parcel_ref14", "==", ref)]
            )
            expected_grants = expected_grants[expected_grants.geographic_municipality_code.eq(code)]
            self.assertFalse(expected_energy.empty)
            self.assertFalse(expected_grants.empty)
            app = AppTest.from_string(
                """from madrid_rehab.municipal_fiche import render_fiche
render_fiche("28005", "Alcalá de Henares", "0015301VK7801N")
""",
                default_timeout=120,
            ).run()

            def check_evidence():
                energy = next(
                    d.value for d in app.dataframe if "Ámbito declarado" in d.value.columns
                )
                grants = next(d.value for d in app.dataframe if "Expediente" in d.value.columns)
                self.assertEqual(
                    len(energy),
                    len(
                        expected_energy.drop_duplicates(
                            ["certificate_id", "link_level", "link_reason"]
                        )
                    ),
                )
                self.assertEqual(set(grants.Expediente), set(expected_grants.expediente_id))
                self.assertFalse(grants.Expediente.duplicated().any())
                return energy.copy(), grants.copy()

            before = check_evidence()
            next(b for b in app.button if b.label == "Consultar construcción").click().run()
            self.assertFalse(
                any(
                    "Ámbito declarado" in d.value.columns or "Expediente" in d.value.columns
                    for d in app.dataframe
                )
            )
            next(b for b in app.button if b.label.startswith("Volver al objeto")).click().run()
            after = check_evidence()
            pd.testing.assert_frame_equal(before[0], after[0])
            pd.testing.assert_frame_equal(before[1], after[1])

    def test_missing_enrichment_preserves_identification_and_cp_evidence(self):
        with (
            patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}),
            patch(
                "madrid_rehab.enriched_cadastre.signature",
                side_effect=FileNotFoundError("missing partition"),
            ),
        ):
            app = AppTest.from_string(
                """from madrid_rehab.municipal_fiche import render_fiche
render_fiche("28005", "Alcalá de Henares", "0015301VK7801N")
""",
                default_timeout=120,
            ).run()
            self.assertFalse(app.exception)
            self.assertEqual(tuple(t.label for t in app.tabs), SECTIONS)
            self.assertTrue(any("Geometría utilizable: True" in m.value for m in app.markdown))
            self.assertTrue(app.warning)
            self.assertTrue(any("Ámbito declarado" in d.value.columns for d in app.dataframe))
            self.assertTrue(any("Expediente" in d.value.columns for d in app.dataframe))
