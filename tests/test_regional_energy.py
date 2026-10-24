"""Contratos conservadores y regresión real de productos energéticos."""

import json
import unittest
from pathlib import Path

import pandas as pd

from madrid_rehab.ingest import digest
from madrid_rehab.normalize import reference
from madrid_rehab.regional_energy import (
    DEFAULT,
    SCOPES,
    combined_summary,
    content_ids,
    identity,
    municipality,
    numeric,
    parcel_links,
    rating,
)


class EnergyContracts(unittest.TestCase):
    def test_complete_municipality_names(self):
        cat = {"MADRID": ["28079"], "LAS ROZAS DE MADRID": ["28127"]}
        self.assertEqual(municipality(" Madrid ", cat)[0], "28079")
        self.assertEqual(municipality("Las Rozas de Madrid", cat)[0], "28127")
        self.assertIsNone(municipality("Rozas Madrid", cat)[0])
        self.assertEqual(municipality("Madrid", cat, "28127")[1], "municipality_conflicting")
        self.assertEqual(municipality("Madrid", cat, "28900")[1], "municipality_conflicting")
        self.assertEqual(municipality("X", {"X": ["1", "2"]})[1], "municipality_ambiguous")

    def test_province_contradiction_prevents_verification(self):
        cat = {"MADRID": ["28079"]}
        self.assertEqual(
            municipality("Madrid", cat, province="Lleida")[1], "municipality_conflicting"
        )
        self.assertIsNone(municipality("Madrid", cat, province="Lleida")[0])
        self.assertEqual(municipality("Madrid", cat, province="Comunidad de Madrid")[0], "28079")

    def test_reference_structure(self):
        self.assertEqual(reference("8238105VK3783G")["reference_kind"], "parcel")
        self.assertEqual(reference("2056324VK2725N0119PW")["parcel_ref14"], "2056324VK2725N")
        self.assertIsNone(reference("2056324")["parcel_ref14"])
        self.assertIsNone(reference("BAD2056324VK2725N0119PW")["parcel_ref14"])

    def test_content_and_registration_identity(self):
        f = pd.DataFrame({"edif_codreg": ["a", "a", "a", ""], "value": ["1", "1", "2", "3"]})
        f["certificate_id"] = content_ids(f)
        result = identity(f)
        self.assertEqual(len(result), 3)
        self.assertEqual(result.occurrence_count.tolist(), [2, 1, 1])
        self.assertEqual(
            result.identity_status.tolist(),
            ["identity_conflicting", "identity_conflicting", "identity_insufficient"],
        )

    def test_scope_never_from_parcel(self):
        self.assertEqual(SCOPES["ViviendaIndividualEnBloque"], "individual_unit")
        self.assertEqual(SCOPES["BloqueDeViviendaCompleto"], "whole_building")
        self.assertNotIn("Vivendas", SCOPES)
        self.assertEqual(SCOPES["LocalUsoTerciario"], "commercial_unit")

    def test_values_and_unknown_units(self):
        self.assertIsNone(rating("H"))
        self.assertEqual(rating("g"), "G")
        self.assertEqual(numeric("0"), (0.0, "observed"))
        self.assertEqual(numeric(""), (None, "missing"))
        self.assertEqual(numeric("99999999,99")[1], "suspect")
        self.assertEqual(numeric("NaN")[1], "non_finite")
        self.assertEqual(numeric("5 kWh/año")[1], "unknown_or_not_numeric")

    def test_parcel_links(self):
        ref = "8238105VK3783G"
        refs = [ref, ref, ref, ref + ",2056324VK2725N", "wrong", ref]
        f = pd.DataFrame(
            {
                "certificate_id": list("abcdef"),
                "edif_refcat": refs,
                "municipality_code": ["28079", "28065", "28007", "28079", "28079", "28127"],
                "municipality_status": ["municipality_verified"] * 6,
            }
        )
        idx = {
            "28079": {"accepted": {ref: 1}, "quarantine": set()},
            "28065": {"accepted": {}, "quarantine": {ref}},
            "28007": {"accepted": {ref: 2}, "quarantine": set()},
        }
        municipal_links = parcel_links(f, idx)
        self.assertEqual(
            municipal_links.groupby("certificate_id").link_level.first().to_dict(),
            dict(zip("abcdef", "ADDDEE")),
        )
        self.assertEqual(municipal_links[municipal_links.certificate_id.eq("d")].shape[0], 2)
        self.assertEqual(
            municipal_links[municipal_links.certificate_id.eq("f")].link_reason.iloc[0],
            "no_integrated_cp_coverage",
        )

    def test_joint_amounts_once_per_case(self):
        e = pd.DataFrame(
            {
                "certificate_id": ["a", "b", "c"],
                "municipality_code": ["1"] * 3,
                "parcel_ref14": ["x", "x", "y"],
                "link_level": ["A"] * 3,
            }
        )
        g = pd.DataFrame(
            {
                "expediente_id": ["G", "G"],
                "geographic_municipality_code": ["1", "1"],
                "parcel_ref14": ["x", "y"],
                "match_status": ["confirmed"] * 2,
            }
        )
        grants = pd.DataFrame(
            {
                "expediente_id": ["G"],
                "programa": ["P1"],
                "importe_centimos": [100],
                "fecha_concesion": [None],
                "fecha_disponible": [None],
            }
        )
        summary, cases = combined_summary(e, g, grants)
        self.assertEqual(summary.certificate_count.sum(), 3)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases.importe_centimos.sum(), 100)
        self.assertNotIn("importe_centimos", summary.columns)


@unittest.skipUnless((DEFAULT / "manifest.json").exists(), "Producto real no disponible")
class RealEnergyProducts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((DEFAULT / "manifest.json").read_text())
        cls.quality = json.loads((DEFAULT / "energy_quality.json").read_text())

    def test_historical_inputs_and_outputs_intact(self):
        for path, sha in self.manifest["inputs"].items():
            self.assertEqual(digest(Path(path)), sha, path)
        for path, sha in self.manifest["outputs"].items():
            self.assertEqual(digest(DEFAULT / path), sha, path)

    def test_source_reconciliation(self):
        q = self.quality
        self.assertEqual(q["source_records"], 236173)
        self.assertEqual(
            q["canonical_certificates"] + q["exact_duplicate_occurrences"], q["source_records"]
        )

    def test_madrid_and_five_pilots(self):
        summary = pd.read_parquet(DEFAULT / "energy_municipality_summary.parquet").set_index(
            "municipality_code"
        )
        for code in ["28079", "28065", "28092", "28074", "28007", "28005"]:
            self.assertGreater(summary.loc[code, "canonical_certificates"], 0)
            self.assertGreater(summary.loc[code, "confirmed_cp_certificates"], 0)
        self.assertEqual(len(summary), 179)
        self.assertEqual(summary.cp_integrated.sum(), 6)

    def test_no_invented_bu_or_time_series(self):
        self.assertEqual(self.quality["confirmed_bu"], 0)
        self.assertEqual(self.quality["confirmed_temporal_pairs"], 0)
        self.assertFalse((DEFAULT / "energy_building_links.parquet").exists())

    def test_public_exposure_disabled(self):
        self.assertFalse(self.manifest["public_exposure"])

    def test_selective_partition_reconciliation(self):
        f = pd.read_parquet(DEFAULT / "energy_certificates.parquet")
        for code in ["28079", "28065", "28092", "28074", "28007", "28005"]:
            p = pd.read_parquet(DEFAULT / "municipalities" / code / "certificates.parquet")
            self.assertEqual(
                set(p.certificate_id), set(f.loc[f.municipality_code.eq(code), "certificate_id"])
            )
        self.assertTrue(f.consumption_unit.eq("not_verified_in_local_schema").all())


if __name__ == "__main__":
    unittest.main()


class EnergyViewer(unittest.TestCase):
    def test_public_mode_reads_no_energy(self):
        from unittest.mock import patch
        from madrid_rehab.energy_view import render_energy_region, render_energy_parcel

        with patch.dict("os.environ", {"MADRID_REHAB_PUBLIC": "1"}):
            with patch("madrid_rehab.energy_view.read") as reader:
                render_energy_region()
                render_energy_parcel("28079", "8238105VK3783G")
                reader.assert_not_called()

    @unittest.skipUnless((DEFAULT / "manifest.json").exists(), "Producto real no disponible")
    def test_real_streamlit_energy_navigation(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_string(
            "from madrid_rehab.energy_view import render_energy_region\nrender_energy_region()"
        )
        app.run(timeout=40)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.selectbox[0].options), 179)
        app.selectbox[0].select("28065").run(timeout=40)
        self.assertEqual(len(app.exception), 0)
        self.assertGreater(len(app.dataframe), 2)

    def test_dates_do_not_order_identity_versions(self):
        f = pd.DataFrame({"edif_codreg": ["a", "a"], "edif_fecha": ["01/01/2026", "01/01/2025"]})
        f["certificate_id"] = content_ids(f)
        result = identity(f)
        self.assertEqual(len(result), 2)
        self.assertTrue(result.identity_status.eq("identity_conflicting").all())
