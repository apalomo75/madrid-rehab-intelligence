"""Session 20: normalization contracts, real postal identities and map-free route."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab import address_search as a


class NormalizationTests(unittest.TestCase):
    def test_accents_case_spaces(self):
        self.assertEqual(a.street_key("  calle  BAILÉN "), a.street_key("CALLE bailen"))

    def test_abbreviations(self):
        for short, full in [("CL", "CALLE"), ("AV.", "AVENIDA"), ("PZ", "PLAZA")]:
            self.assertEqual(a.street_key(short + " Mayor"), full + " MAYOR")

    def test_numbers_and_complements_preserved(self):
        self.assertNotEqual(a.parse_query("Bailén", "24"), a.parse_query("Bailén", "26"))
        self.assertEqual(a.parse_query("CL Bailén, 024 B"), ("CALLE BAILEN", "24", "B"))
        self.assertNotEqual(
            a.parse_query("Bailén", "24", "B"), a.parse_query("Bailén", "24", "DUP")
        )
        self.assertEqual(a.parse_query("26 de Abril 2"), ("26 DE ABRIL", "2", ""))
        self.assertEqual(a.parse_query("Mayor 24-26")[1], "")
        with self.assertRaises(ValueError):
            a.parse_query("Mayor 24 B", complement="A")

    def test_distinct_street_names(self):
        self.assertNotEqual(a.street_key("CALLE MAYOR"), a.street_key("PLAZA MAYOR"))
        self.assertNotEqual(a.street_key("DE LA PAZ"), a.street_key("PAZ"))

    def test_multiple_documentary_cp_and_conflicts(self):
        accesses = pd.DataFrame(
            [
                dict(
                    VIA_NOMBRE_ACENTOS="Mayor",
                    VIA_NOMBRE="MAYOR",
                    NUMERO="24",
                    CLASE_APP="NUMERO",
                    COD_NDP="1",
                    access_version_id="v1",
                    access_id="p1",
                    VIA_CLASE="CALLE",
                    VIA_PAR="",
                    CALIFICADOR="B",
                    COD_VIA="2",
                    TIPO_NDP="PORTAL",
                    source_row=2,
                    source_sha256="abc",
                )
            ]
        )
        links = pd.DataFrame(
            [
                dict(
                    ndp="1",
                    confirmed_parcel_ref14=ref,
                    parcel_candidate=ref,
                    link_status="confirmed_access_parcel",
                    link_reason="documentary",
                )
                for ref in ["A", "B"]
            ]
        )
        rows, _ = a.postal_rows(accesses, links)
        self.assertEqual(json.loads(rows.iloc[0].refs), ["A", "B"])
        links.loc[1, "link_status"] = "ambiguous_access_parcel"
        rows, _ = a.postal_rows(accesses, links)
        self.assertEqual(rows.iloc[0].status, "ambiguous")
        self.assertEqual(json.loads(rows.iloc[0].refs), [])


@unittest.skipUnless((a.DEFAULT / "manifest.json").exists(), "Real postal index not materialized")
class RealAddressTests(unittest.TestCase):
    def test_real_exact_accents_and_full_address(self):
        results, count = a.search("28079", "CALLE BAILÉN", "12")
        self.assertGreater(count, 0)
        for variant in ["cl bailen", "calle bailén 12", "BAILEN"]:
            found, n = a.search("28079", variant, "" if variant.endswith("12") else "12")
            self.assertEqual({r["id"] for r in found}, {r["id"] for r in results})
            self.assertEqual(n, count)
        self.assertTrue(any(r["status"] == "confirmed" for r in results))
        self.assertTrue(any("9542204VK3794A" in json.loads(r["refs"]) for r in results))

    def test_missing_number_and_municipal_homonyms(self):
        self.assertEqual(a.search("28079", "CALLE BAILEN", "999999")[1], 0)
        self.assertEqual(a.search("28079", "VIA INEXISTENTE SESION XX")[1], 0)
        for code in set(a.NAMES) - {"28079"}:
            self.assertEqual(a.search(code, "CALLE BAILEN", "12")[1], 0)

    def test_real_all_statuses_and_complements(self):
        with a.connect() as db:
            for status in ["confirmed", "ambiguous", "unlinked"]:
                row = dict(
                    db.execute(
                        "SELECT * FROM addresses WHERE status=? ORDER BY id LIMIT 1", (status,)
                    ).fetchone()
                )
                rows, _ = a.search(
                    row["municipality"],
                    row["kind"] + " " + row["street"],
                    row["number"],
                    row["complement"],
                )
                self.assertIn(row["id"], [r["id"] for r in rows])
                if status != "confirmed":
                    self.assertEqual(json.loads(row["refs"]), [])
            row = dict(
                db.execute(
                    "SELECT * FROM addresses WHERE complement_key != '' ORDER BY id LIMIT 1"
                ).fetchone()
            )
            rows, _ = a.search(
                "28079", row["kind"] + " " + row["street"], row["number"], row["complement"]
            )
            self.assertIn(row["id"], [r["id"] for r in rows])
            self.assertTrue(all(r["complement_key"] == row["complement_key"] for r in rows))
            self.assertGreater(
                db.execute(
                    "SELECT COUNT(*) FROM (SELECT access_id FROM addresses GROUP BY access_id HAVING COUNT(*)>1)"
                ).fetchone()[0],
                0,
            )

    def test_coverage_five_pilots_no_invented_addresses(self):
        coverage = json.loads((a.REPORT / "address_coverage.json").read_text())
        for code in set(a.NAMES) - {"28079"}:
            metric = coverage["municipalities"][code]
            self.assertGreater(metric["bu_with_ad_reference"], 0)
            self.assertEqual(metric["ad_with_postal_literal"], 0)
            self.assertEqual(metric["indexed_addresses"], 0)
            self.assertIsNone(metric["utility_percentages"])

    def test_real_same_postal_text_different_parcels_not_merged(self):
        # Found in the real index, not a fabricated multi-CP portal.
        rows, total = a.search("28079", "A LA ESTACION DE HORTALEZA", "8")
        self.assertGreater(total, 1)
        self.assertGreater(len({ref for r in rows for ref in json.loads(r["refs"])}), 1)
        self.assertEqual(len({r["id"] for r in rows}), len(rows))

    def test_incompatible_snapshot_override_blocks_summary(self):
        with patch.dict(os.environ, {"MADRID_REHAB_ENERGY_DIR": "/tmp/other-energy"}):
            with self.assertRaises(ValueError):
                a.metadata()

    def test_unresolved_results_do_not_open_fiche(self):
        app = self.make_app(technical=True)
        with a.connect() as db:
            examples = [
                dict(
                    db.execute(
                        "SELECT * FROM addresses WHERE status=? ORDER BY id LIMIT 1", (state,)
                    ).fetchone()
                )
                for state in ("ambiguous", "unlinked")
            ]
        for row in examples:
            app.text_input(key="postal_street").set_value(row["kind"] + " " + row["street"])
            app.text_input(key="postal_number").set_value(row["number"])
            app.text_input(key="postal_complement").set_value(row["complement"])
            next(b for b in app.button if b.label == "Buscar").click().run()
            app.selectbox(key="postal_result_choice").set_value(row["id"]).run()
            self.assertFalse(app.exception)
            self.assertTrue(app.warning)
            self.assertFalse(any(b.label == "Abrir ficha del inmueble" for b in app.button))

    def test_multiple_cp_requires_explicit_additional_selection(self):
        row = a.search("28079", "BAILEN", "12")[0][0].copy()
        row["refs"] = json.dumps(["9542204VK3794A", "0010510VK4701A"])
        # Fixture exercises a cardinality absent from the real NDP snapshot.
        with patch.object(a, "search", return_value=([row], 1)):
            app = self.make_app(technical=True)
            app.text_input(key="postal_street").set_value("BAILEN 12")
            next(b for b in app.button if b.label == "Buscar").click().run()
            app.selectbox(key="postal_result_choice").set_value(row["id"]).run()
            choice = next(s for s in app.selectbox if s.label == "Seleccione la parcela vinculada")
            self.assertIsNone(choice.value)
            self.assertTrue(
                next(b for b in app.button if b.label == "Abrir ficha del inmueble").disabled
            )
            choice.set_value("9542204VK3794A").run()
            self.assertFalse(
                next(b for b in app.button if b.label == "Abrir ficha del inmueble").disabled
            )

    def test_read_only_and_manifest_tampering(self):
        with a.connect() as db:
            import sqlite3

            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM addresses")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "manifest.json").write_text(
                json.dumps(dict(policy=a.POLICY, inputs={}, outputs={"addresses.sqlite": "bad"}))
            )
            (root / "addresses.sqlite").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                a.metadata(root)

    def make_app(self, public="0", technical=False):
        self.environment = patch.dict(
            os.environ, {"MADRID_REHAB_DEMO": "0", "MADRID_REHAB_PUBLIC": public}
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        if technical:
            return AppTest.from_string(
                "from madrid_rehab.address_view import render\nrender(technical=True)",
                default_timeout=120,
            ).run()
        app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=120).run()
        return app.radio(key="city_navigation").set_value("Buscar por dirección").run()

    def test_real_map_free_fiche_return_and_municipal_change(self):
        app = self.make_app()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="city_navigation").value, "Buscar por dirección")
        app.text_input(key="postal_street").set_value("CL BAILEN")
        app.text_input(key="postal_number").set_value("12")
        next(b for b in app.button if b.label == "Buscar").click().run()
        result = app.selectbox(key="postal_result_choice")
        self.assertIsNone(result.value)
        uid = a.search("28079", "CL BAILEN", "12")[0][0]["id"]
        result.set_value(uid).run()
        next(b for b in app.button if b.label == "Abrir ficha del inmueble").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["fiche_identity"][1], "cp")
        self.assertTrue(any("BAILÉN" in m.value.upper() for m in app.subheader))
        self.assertEqual(len(app.tabs), 6)
        self.assertFalse(any(e.type == "deck_gl_json_chart" for e in app))
        next(b for b in app.button if b.label == "Volver a los resultados").click().run()
        self.assertEqual(app.text_input(key="postal_street").value, "CL BAILEN")
        self.assertEqual(app.selectbox(key="postal_result_choice").value, uid)
        app.selectbox(key="postal_municipality").set_value("28065").run()
        self.assertFalse(app.exception)
        self.assertNotIn("postal_open", app.session_state)
        self.assertTrue(any("no dispone" in w.value for w in app.warning))

    def test_evidence_summary_preserves_source_and_public_protection(self):
        from madrid_rehab import demo

        with a.connect() as db:
            row = dict(
                db.execute(
                    "SELECT * FROM parcel_facts WHERE certificate_count>0 AND grant_case_count>0 LIMIT 1"
                ).fetchone()
            )
        cert, _, _, _ = demo.evidence("28079", row["parcel_ref14"])
        self.assertEqual(cert.certificate_id.nunique(), row["certificate_count"])
        app = self.make_app(public="1", technical=True)
        app.text_input(key="postal_street").set_value("Bailen 12")
        next(b for b in app.button if b.label == "Buscar").click().run()
        uid = a.search("28079", "Bailen", "12")[0][0]["id"]
        app.selectbox(key="postal_result_choice").set_value(uid).run()
        next(b for b in app.button if b.label == "Abrir ficha del inmueble").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(any("Expediente" in d.value.columns for d in app.dataframe))


if __name__ == "__main__":
    unittest.main()
