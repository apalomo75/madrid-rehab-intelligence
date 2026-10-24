"""Contratos PRTR y regresión sobre la captura real local."""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab.grants import (
    SOURCE,
    aggregate,
    cents,
    normalize,
    reference,
    match_parcels,
    assign_territory,
)
from madrid_rehab.grants_view import filter_grants, parcel_grants, safe_export, exposure_enabled
from madrid_rehab.regional import municipality_config, spatial_municipalities


class GrantContracts(unittest.TestCase):
    def setUp(self):
        self.document = {
            "type": "FeatureCollection",
            "features": [
                dict(
                    type="Feature",
                    properties=dict(
                        expediente="x",
                        pr="pr4",
                        imp_con=3000,
                        catref="9966416VK2696N",
                        refs=["9966416VK2696N"],
                        etapa="APROBACIÓN CONCESIÓN",
                        age=1965,
                        viviendas=1,
                        viviendas_sup=70,
                        sup_vivienda=70,
                    ),
                    geometry=dict(type="Point", coordinates=[-3.82, 40.34]),
                )
            ],
        }

    def test_program_and_award_never_payment(self):
        f, _, _ = normalize(self.document)
        self.assertEqual(f.programa.tolist(), ["P4"])
        self.assertEqual(f.fase.tolist(), ["award"])
        self.assertTrue(f.fecha_pago.isna().all())
        self.assertTrue(f.fecha_concesion.isna().all())

    def test_original_unchanged(self):
        before = copy.deepcopy(self.document)
        normalize(self.document)
        self.assertEqual(before, self.document)

    def test_reproducibility(self):
        for a, b in zip(normalize(self.document), normalize(self.document)):
            pd.testing.assert_frame_equal(a, b)

    def test_multiparcel_no_double_amount(self):
        self.document["features"][0]["properties"]["refs"] += ["1427912VK4812G", "1427912VK4812G"]
        f, links, _ = normalize(self.document)
        self.assertEqual(len(links), 2)
        self.assertTrue(f.multiparcela.all())
        self.assertNotIn("importe_concedido", links)
        self.assertEqual(aggregate(f, ["programa"]).importe_centimos.sum(), 300000)

    def test_invalid_reference_preserved_raw(self):
        self.document["features"][0]["properties"]["refs"] += ["8KK"]
        f, links, issues = normalize(self.document)
        self.assertIn("8KK", f.raw_json.iloc[0])
        self.assertEqual(len(links), 1)
        self.assertIn("invalid_reference", set(issues.issue))

    def test_invalid_points_retained(self):
        for geometry in [
            None,
            {"type": "Polygon", "coordinates": []},
            {"type": "Point", "coordinates": [999, 40]},
        ]:
            self.document["features"][0]["geometry"] = geometry
            f, _, q = normalize(self.document)
            self.assertEqual(len(f), 1)
            self.assertFalse(f.geometry_valid.iloc[0])
            self.assertIn("invalid_point", set(q.issue))

    def test_unknown_phase_program(self):
        self.document["features"][0]["properties"].update(pr="other", etapa="DESCONOCIDA")
        f, _, q = normalize(self.document)
        self.assertEqual(f.fase.iloc[0], "unknown")
        self.assertIn("unknown_program", set(q.issue))

    def test_missing_values(self):
        self.document["features"][0]["properties"] = {"expediente": "x"}
        f, _, _ = normalize(self.document)
        self.assertTrue(f.importe_concedido.isna().all())
        self.assertTrue(f.fecha_disponible.isna().all())

    def test_duplicate_identity_quarantined(self):
        self.document["features"] *= 2
        f, _, q = normalize(self.document)
        self.assertEqual(len(f), 2)
        self.assertTrue(f.identity_conflict.all())
        self.assertTrue(aggregate(f, ["programa"]).empty)
        self.assertIn("identity_conflict", set(q.issue))

    def test_amounts(self):
        self.assertEqual(cents("12.34"), 1234)
        self.assertIsNone(cents("nan"))
        self.assertIsNone(cents("bad"))
        self.document["features"][0]["properties"]["imp_con"] = -2
        _, _, q = normalize(self.document)
        self.assertIn("invalid_amount", set(q.issue))

    def test_reference_format(self):
        self.assertEqual(reference("9966416VK2696N"), "9966416VK2696N")
        self.assertIsNone(reference("ABCDEFGHIJKLMN"))
        self.assertEqual(reference("02129E1VK4801A"), "02129E1VK4801A")

    def test_outside_cp_not_lost(self):
        f, links, _ = normalize(self.document)
        cp = pd.DataFrame(columns=["parcel_ref14", "district_code"])
        matched = match_parcels(f, links, cp)
        self.assertEqual(matched.match_status.iloc[0], "regional_cp_pending")
        self.assertEqual(
            assign_territory(f, matched).territorial_quality.iloc[0], "territorial_candidate"
        )

    def test_contradiction_not_madrid_confirmed(self):
        f, links, _ = normalize(self.document)
        cp = pd.DataFrame(
            [
                dict(
                    parcel_ref14="9966416VK2696N",
                    district_code="07",
                    geometry_crs="EPSG:25830",
                    usable_geometry=True,
                    geometry_wkt="POLYGON ((400000 4500000,400010 4500000,400010 4500010,400000 4500010,400000 4500000))",
                )
            ]
        )
        matched = match_parcels(f, links, cp)
        self.assertEqual(matched.match_status.iloc[0], "contradictory")
        self.assertEqual(assign_territory(f, matched).territorial_quality.iloc[0], "contradictory")

    def test_regional_config_no_fictitious_processing(self):
        config = municipality_config("28005", "Alcalá de Henares")
        self.assertFalse(config["sources"]["cp"]["available"])
        self.assertFalse(config["sources"]["cp"]["processed"])
        with self.assertRaises(ValueError):
            municipality_config("bogus", "x")

    def test_spatial_boundary_ambiguity(self):
        f, _, _ = normalize(self.document)
        from pyproj import Transformer

        x, y = Transformer.from_crs(4326, 25830, always_xy=True).transform(-3.82, 40.34)
        polygon = f"POLYGON (({x - 10} {y - 10},{x + 10} {y - 10},{x + 10} {y + 10},{x - 10} {y + 10},{x - 10} {y - 10}))"
        regions = pd.DataFrame([dict(municipality_code="28005", geometry_wkt=polygon)])
        self.assertEqual(spatial_municipalities(f, regions).municipality_code.iloc[0], "28005")
        self.assertEqual(
            spatial_municipalities(f, pd.concat([regions, regions])).territorial_quality.iloc[0],
            "contradictory",
        )

    def test_export_allowlist_and_formula(self):
        frame = pd.DataFrame(
            [{"expediente_id": "=1+1", "raw_json": "secret", "direccion": "private"}]
        )
        csv = safe_export(frame)
        text = csv.decode("utf-8-sig") if isinstance(csv, bytes) else csv
        self.assertNotIn("secret", text)
        self.assertNotIn("private", text)
        self.assertIn("'=1+1", text)

    def test_public_disabled(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            self.assertFalse(exposure_enabled())


class RealGrants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f, cls.links, cls.q = normalize(json.loads(SOURCE.read_text()))

    def test_7532_unique(self):
        self.assertEqual(len(self.f), 7532)
        self.assertEqual(self.f.expediente_id.nunique(), 7532)

    def test_program_counts(self):
        self.assertEqual(
            self.f.programa.value_counts().to_dict(), {"P4": 4889, "P3": 1380, "P5": 899, "P1": 364}
        )

    def test_points_and_amounts(self):
        self.assertTrue(self.f.geometry_valid.all())
        self.assertTrue(self.f.importe_centimos.gt(0).all())

    def test_multiple_literal_vs_valid_refs(self):
        self.assertEqual(self.f.multiparcela.sum(), 12)
        self.assertEqual(
            self.f.referencias_adicionales.map(lambda s: len(json.loads(s)) > 1).sum(), 19
        )

    def test_filters_and_selection(self):
        self.assertEqual(len(filter_grants(self.f, [])), 0)
        self.assertEqual(len(filter_grants(self.f, ["P1"])), 364)
        links = self.links.copy().assign(match_status="confirmed")
        selected = parcel_grants(links.parcel_ref14.iloc[0], self.f, links)
        self.assertTrue(selected.expediente_id.is_unique)

    def test_app_regional_and_empty_filter(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "app.py"
            path.write_text(
                "from madrid_rehab.grants_view import render_grants\nrender_grants(regional=True)\n"
            )
            app = AppTest.from_file(str(path), default_timeout=30).run()
            self.assertFalse(app.exception)
            app.multiselect[0].set_value([]).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value, "0")


if __name__ == "__main__":
    unittest.main()
