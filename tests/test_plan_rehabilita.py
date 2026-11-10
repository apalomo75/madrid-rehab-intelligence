"""Municipal aid identity, financial scope, immutable real sources and client parsing."""

import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab import plan_rehabilita as pr
from madrid_rehab.cadastral_service_probe import parse_response
from madrid_rehab.commercial_fiche import Quality, build_model
from madrid_rehab.ingest import digest


class ParserTests(unittest.TestCase):
    def test_money_null_invalid_and_no_locale_guess(self):
        self.assertEqual(pr.numeric("105008.85000000", money=True), (10500885, "observed"))
        self.assertEqual(pr.numeric("", money=True), (None, "missing"))
        for raw in ["1.234,56", "1,234.56", "NaN", "-12", "2.001"]:
            self.assertEqual(pr.numeric(raw, money=True), (None, "invalid"))
        self.assertEqual(pr.numeric("0", money=True), (0, "observed"))
        self.assertEqual(pr.numeric("14.5", integer=True), (None, "invalid"))
        self.assertEqual(pr.day("20260230"), (None, "invalid"))

    def test_dbf_structural_and_deleted_evidence(self):
        header = bytearray(65)
        struct.pack_into("<IHH", header, 4, 2, 65, 5)
        header[32:36] = b"NAME"
        header[43] = ord("C")
        header[48] = 4
        header[64] = 13
        frame, fields = pr.dbf(bytes(header) + b" abc " + b"*xyz ", "utf-8")
        self.assertEqual(frame.NAME.tolist(), ["abc", "xyz"])
        self.assertEqual(frame.source_deleted.tolist(), [False, True])
        self.assertEqual(fields[0]["name"], "NAME")
        with self.assertRaisesRegex(ValueError, "Truncated"):
            pr.dbf(bytes(header), "utf-8")

    def test_exact_one_access_one_cp_and_ambiguity(self):
        base = dict(
            id="v1",
            access_id="ndp1",
            status="confirmed",
            refs='["CP1"]',
            number_key="14",
            complement_key="",
        )
        postal = pd.DataFrame([base])
        found, method = pr.postal_candidates("AV MONCLOA 14", postal, {"AVENIDA MONCLOA": {"v1"}})
        self.assertEqual(pr.classify(found, "09", {"CP1": "09"})[0], "A")
        self.assertIn("official", method)
        for altered in [
            pd.DataFrame([base, {**base, "id": "v2", "access_id": "ndp2"}]),
            pd.DataFrame([{**base, "status": "ambiguous"}]),
            pd.DataFrame([{**base, "refs": '["CP1","CP2"]'}]),
        ]:
            self.assertEqual(pr.classify(altered, "09", {"CP1": "09", "CP2": "09"})[0], "B")
        self.assertEqual(pr.classify(found, "10", {"CP1": "09"})[0], "B")
        self.assertEqual(pr.classify(found.iloc[:0], "09", {})[0], "C")

    def test_multiple_documentary_addresses_never_confirmed(self):
        rows = pd.DataFrame(
            [
                dict(DIRECCION="CALLE A 1", DISTRITO="01-Centro"),
                dict(DIRECCION="CALLE A 3", DISTRITO="01-Centro"),
            ]
        )
        self.assertFalse(pr.consistent_case_locations(rows))
        self.assertTrue(pr.consistent_case_locations(rows.iloc[:1]))

    def test_property_detail_to_rc14_is_not_building(self):
        body = b"""<consulta_dnp><bico><bi><idbi><rc><pc1>8781605</pc1><pc2>VK4788B</pc2><car>0000</car><cc1>A</cc1><cc2>B</cc2></rc></idbi><debi><luso>Suelo</luso><sfc>0</sfc></debi></bi></bico></consulta_dnp>"""
        detail = parse_response(body, "8781605VK4788B")["detail"]
        self.assertEqual(detail["property_ref20"], "8781605VK4788B0000AB")
        self.assertEqual(detail["area"], "0")
        self.assertIsNone(detail["declared_age"])
        self.assertIn("not_BU", detail["scope"])
        with self.assertRaises(ValueError):
            parse_response(body, "9377401VK3797G")
        with self.assertRaises(ValueError):
            parse_response(b"<!DOCTYPE foo><x/>", "8781605VK4788B")

    def test_municipal_program_not_prtr_or_building_scope(self):
        frame = pd.DataFrame(
            [
                dict(
                    case_id="municipal1",
                    link_class="A",
                    original_address="AV MONCLOA 14",
                    source_sha256="sha",
                    call="REHABILITA 2021",
                    SUB_AYTO_R_cents=123456,
                    TOT_PRES_P_cents=None,
                    dwellings=14,
                    FECHA_ACTU="2026-08-30",
                )
            ]
            * 2
        )
        model = build_model(
            "28079",
            "Madrid",
            "CP",
            "cp",
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            municipal_grants=frame,
        )
        self.assertEqual(len(model.municipal_grants), 1)
        self.assertFalse(model.grants)
        self.assertEqual(
            model.municipal_grants[0].value["Subvención revisada del expediente (€)"], 1234.56
        )
        self.assertIsNone(
            model.municipal_grants[0].value["Presupuesto protegible del expediente (€)"]
        )
        self.assertEqual(model.municipal_grants[0].quality, Quality.PARCEL)
        frame.loc[:, "link_class"] = "B"
        pending = build_model(
            "28079",
            "Madrid",
            "CP",
            "cp",
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            municipal_grants=frame,
        )
        self.assertFalse(pending.municipal_grants)


@unittest.skipUnless((pr.DEFAULT / "manifest.json").exists(), "Real municipal product absent")
class RealPlanTests(unittest.TestCase):
    def test_original_and_every_source_row_preserved(self):
        meta = json.loads((pr.DEFAULT / "manifest.json").read_text())
        self.assertEqual(digest(Path(meta["source_original_path"])), meta["source_sha256"])
        self.assertEqual(digest(Path(meta["preserved_original"])), meta["source_sha256"])
        for name, sha in meta["outputs"].items():
            self.assertEqual(digest(pr.DEFAULT / name), sha)
        rows = pd.read_parquet(pr.DEFAULT / "source_rows.parquet")
        cases = pd.read_parquet(pr.DEFAULT / "cases.parquet")
        self.assertEqual(len(rows), 7990)
        self.assertEqual(len(cases), 2085)
        self.assertTrue(cases.case_id.is_unique)
        self.assertEqual(int(cases.SUB_AYTO_R_cents.sum()), 23304513610)
        self.assertTrue(rows.NUMERO_EXP.duplicated().any())
        with self.assertRaises(FileExistsError):
            pr.build(output=pr.DEFAULT)

    def test_reader_unique_cases_no_bu_public_or_other_municipality(self):
        from madrid_rehab.plan_rehabilita_store import parcel_records

        links = pd.read_parquet(pr.DEFAULT / "locations.parquet")
        ref = links[links.link_class.eq("A")].parcel_ref14.value_counts().index[0]
        got = parcel_records("28079", ref)
        expected = links[links.link_class.eq("A") & links.parcel_ref14.eq(ref)]
        self.assertEqual(set(got.case_id), set(expected.case_id))
        self.assertTrue(got.case_id.is_unique)
        self.assertGreater(len(got), 1)
        self.assertTrue(parcel_records("28079", ref, kind="bu").empty)
        self.assertTrue(parcel_records("28065", ref).empty)
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            self.assertTrue(parcel_records("28079", ref).empty)

    def test_coverage_same_population_and_no_false_rescue(self):
        report = Path("reports/session_23_plan_rehabilita")
        d = json.loads((report / "coverage_summary.json").read_text())
        self.assertEqual(d["reference_population"], 214083)
        self.assertEqual(d["almost_empty_before"], 18691)
        self.assertEqual(d["new_municipal_evidence_versions"], 3194)
        self.assertEqual(d["previously_almost_empty_rescued"], 0)
        a = pd.read_parquet(pr.BASELINE / "final_coverage_postal.parquet")
        b = pd.read_parquet(report / "coverage_masks.parquet")
        self.assertTrue(a.index.equals(b.index))
        self.assertTrue(a.almost_empty.equals(b.almost_empty))

    def test_priority_cases_keep_session22_attributes(self):
        from madrid_rehab.cadastral_identity import resolve_object
        from madrid_rehab.commercial_data import load_fiche

        for ref in ["8781605VK4788B", "9377401VK3797G"]:
            _, cp = resolve_object("28079", ref, "cp")
            model, tables, errors, _ = load_fiche("28079", "Madrid", ref, cp)
            self.assertFalse(errors)
            if ref.startswith("878"):
                self.assertTrue(tables["construction"].empty)
                self.assertFalse(model.municipal_grants)
            else:
                self.assertEqual(
                    {
                        e.value
                        for e in model.characteristics
                        if e.label.startswith("Superficie bruta")
                    },
                    {"5346"},
                )
                self.assertEqual(len(model.energy), 2)
                self.assertFalse(model.municipal_grants)

    def test_confirmed_plan_visible_in_real_commercial_fiche(self):
        links = pd.read_parquet(pr.DEFAULT / "locations.parquet")
        ref = links.loc[links.link_class.eq("A"), "parcel_ref14"].value_counts().index[0]
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "app.py"
            app.write_text(
                "from madrid_rehab.municipal_fiche import render_fiche\n"
                f"render_fiche('28079','Madrid',{ref!r})\n"
            )
            at = AppTest.from_file(str(app), default_timeout=30).run()
            self.assertFalse(at.exception)
            rendered = " ".join(str(v.value) for v in at.markdown)
            self.assertIn("Plan Rehabilita", rendered)
            self.assertTrue(any("Consultar Plan Rehabilita" in str(e.label) for e in at.expander))

    def test_private_catalogue_filters_and_public_block(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "app.py"
            app.write_text("from madrid_rehab.plan_rehabilita_view import render\nrender()\n")
            at = AppTest.from_file(str(app), default_timeout=30).run()
            self.assertFalse(at.exception)
            self.assertEqual(len(at.multiselect), 3)
            at.multiselect[1].set_value(["REHABILITA 2025"]).run()
            self.assertFalse(at.exception)
            self.assertIn("143", [m.value for m in at.metric])
            with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
                public = AppTest.from_file(str(app)).run()
                self.assertFalse(public.exception)
                self.assertTrue(any("deshabilitada" in str(v.value) for v in public.info))
                self.assertFalse(public.dataframe)


if __name__ == "__main__":
    unittest.main()
