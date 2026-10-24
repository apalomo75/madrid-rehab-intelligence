"""GeoPackage oficial y decisiones territoriales PRTR de la sesión 12.1."""

import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import shapely as sh
from pyproj import Transformer
from streamlit.testing.v1 import AppTest

from madrid_rehab.ingest import digest
from madrid_rehab.municipal_boundaries import (
    DEFAULT as BOUNDARIES,
    SOURCE,
    decode_gpkg,
    normalize,
    overlap_report,
    read_entities,
)
from madrid_rehab.regional_grants import territorial_links
from madrid_rehab.territorial_prtr import DEFAULT, run
from test_regional_expansion import (
    BOX,
    X,
    Y,
    synthetic_grant,
    synthetic_previous,
    synthetic_regions,
)


def blob(geom=BOX, envelope=1, little=True, srs=25830):
    endian = "<" if little else ">"
    flags = int(little) | (envelope << 1)
    minx, miny, maxx, maxy = geom.bounds
    values = [minx, maxx, miny, maxy]
    if envelope in (2, 3):
        values += [0, 0]
    elif envelope == 4:
        values += [0, 0, 0, 0]
    if envelope == 0:
        values = []
    return (
        b"GP\x00"
        + bytes([flags])
        + struct.pack(endian + "i", srs)
        + struct.pack(endian + "d" * len(values), *values)
        + sh.to_wkb(geom, byte_order=1 if little else 0)
    )


class GeoPackageTests(unittest.TestCase):
    def test_envelope_variants_and_endianness(self):
        for envelope in range(5):
            for little in (True, False):
                with self.subTest(envelope=envelope, little=little):
                    self.assertTrue(decode_gpkg(blob(envelope=envelope, little=little)).equals(BOX))

    def test_invalid_headers_flags_crs_and_truncation(self):
        original = blob()
        for bad in [
            b"",
            b"XX" + original[2:],
            original[:2] + b"\x01" + original[3:],
            original[:3] + b"\x0b" + original[4:],
            original[:3] + b"\x31" + original[4:],
            original[:3] + b"\x81" + original[4:],
            original[:20],
            blob(srs=4326),
        ]:
            with self.subTest(bad=bad[:8]), self.assertRaises(ValueError):
                decode_gpkg(bad)

    def test_envelope_contradiction_and_nonfinite(self):
        original = blob()
        for value in (float("nan"), float("inf"), 0.0):
            with self.assertRaises(ValueError):
                decode_gpkg(original[:8] + struct.pack("<d", value) + original[16:])

    def test_non_polygon_and_invalid_polygon(self):
        for geom in [
            sh.Point(X, Y),
            sh.Polygon([(X, Y), (X + 10, Y + 10), (X, Y + 10), (X + 10, Y), (X, Y)]),
        ]:
            with self.assertRaises(ValueError):
                decode_gpkg(blob(geom))

    def test_real_194_179_and_special_entities(self):
        entities, meta = read_entities(SOURCE)
        self.assertEqual(len(entities), 194)
        self.assertEqual(entities.CD_INE.nunique(), 179)
        self.assertEqual(meta["geometry_column"]["srs_id"], 25830)
        self.assertEqual(
            entities.entity_kind.value_counts().to_dict(),
            {"municipality": 179, "enclave": 13, "joint_jurisdiction": 2},
        )
        self.assertTrue(entities.area_km2.gt(0).all())
        self.assertEqual(overlap_report(entities), [])

    def test_normalized_enclaves_and_shared_territories(self):
        entities, _ = read_entities(SOURCE)
        municipalities = pd.read_parquet(BOUNDARIES / "municipality_boundaries.parquet").set_index(
            "municipality_code"
        )
        for e in entities.itertuples():
            municipal = sh.from_wkt(municipalities.loc[e.CD_INE].geometry_wkt)
            geom = sh.from_wkt(e.geometry_wkt)
            if e.entity_kind == "joint_jurisdiction":
                self.assertLess(municipal.intersection(geom).area, 0.001)
                self.assertIsNotNone(e.CD_INE_1)
            else:
                self.assertLess(geom.difference(municipal).area, 0.001)
        self.assertEqual(municipalities.loc["28038", "name"], "Cercedilla")
        self.assertEqual(municipalities.loc["28082", "name"], "Manzanares el Real")

    def test_reproducible_normalization_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "out"
            normalize(SOURCE, path)
            for name in [
                "municipality_boundaries",
                "joint_jurisdictions",
                "administrative_entities",
                "cadastre_comparison",
            ]:
                self.assertEqual(
                    digest(path / (name + ".parquet")), digest(BOUNDARIES / (name + ".parquet"))
                )
            with self.assertRaises(FileExistsError):
                normalize(SOURCE, path)


class DecisionTests(unittest.TestCase):
    def decision(self, grants=None, regions=None, excluded=None):
        return territorial_links(
            synthetic_grant() if grants is None else grants,
            synthetic_previous("ambiguous_cp"),
            synthetic_regions() if regions is None else regions,
            excluded=excluded,
        ).iloc[0]

    def test_external_spatial_documentary_and_ambiguous_cp_separate(self):
        result = self.decision()
        self.assertEqual(result.municipality_code, "28065")
        self.assertEqual(result.evidence_level, "B")
        self.assertIsNone(result.cp_confirmed_municipality_code)

    def test_spatial_only_without_full_municipal_name(self):
        result = self.decision(synthetic_grant().assign(direccion="CALLE TEST GETA (MADRID)"))
        self.assertEqual(result.evidence_level, "A")
        self.assertEqual(result.municipality_code, "28065")

    def test_border_and_overlap_unassigned(self):
        self.assertIsNone(self.decision(synthetic_grant(x=X + 10)).municipality_code)
        regions = synthetic_regions()
        regions.loc[1, "geometry_wkt"] = BOX.wkt
        result = self.decision(regions=regions)
        self.assertIsNone(result.municipality_code)
        self.assertEqual(result.evidence_level, "C")

    def test_shared_jurisdiction_unassigned_even_single_municipal_code(self):
        result = self.decision(excluded=pd.DataFrame([dict(geometry_wkt=BOX.wkt)]))
        self.assertEqual(result.territorial_status, "shared_jurisdiction")
        self.assertIsNone(result.municipality_code)
        self.assertEqual(result.evidence_level, "C")

    def test_invalid_missing_placeholder_and_axis_order(self):
        for lon, lat in [
            (None, None),
            (float("nan"), 40),
            (0, 0),
            (-200, 40),
            (-3, 100),
            (40.3, -3.7),
        ]:
            with self.subTest(lon=lon, lat=lat):
                result = self.decision(synthetic_grant().assign(longitude=lon, latitude=lat))
                self.assertIsNone(result.municipality_code)
        self.assertIsNone(
            self.decision(synthetic_grant().assign(geometry_valid=False)).municipality_code
        )

    def test_outside_region(self):
        result = self.decision(synthetic_grant(x=X - 1000))
        self.assertEqual(result.territorial_status, "outside_region")
        self.assertIsNone(result.municipality_code)

    def test_reference_alone_never_assigns(self):
        result = self.decision(
            synthetic_grant().assign(geometry_valid=False, referencia_catastral="1234567VK4712A")
        )
        self.assertIsNone(result.municipality_code)

    def test_identity_conflict_stops_assignment(self):
        result = self.decision(synthetic_grant().assign(identity_conflict=True))
        self.assertEqual(result.evidence_level, "C")
        self.assertIsNone(result.municipality_code)

    def test_similar_names_no_madrid_suffix_false_positive(self):
        regions = synthetic_regions()
        regions.loc[0, "name"] = "Las Rozas de Madrid"
        for address, expected in [
            ("CALLE LAS ROZAS DE MADRID (MADRID)", "B"),
            ("CALLE MADRID (MADRID)", "C"),
        ]:
            self.assertEqual(
                self.decision(synthetic_grant().assign(direccion=address), regions).evidence_level,
                expected,
            )
        result = self.decision(synthetic_grant().assign(direccion="CALLE OTROGETAFE (MADRID)"))
        self.assertEqual(result.evidence_level, "A")

    def test_crs_roundtrip_and_known_external(self):
        lon, lat = Transformer.from_crs(25830, 4326, always_xy=True).transform(X + 5, Y + 5)
        x, y = Transformer.from_crs(4326, 25830, always_xy=True).transform(lon, lat)
        self.assertAlmostEqual(x, X + 5, places=6)
        self.assertAlmostEqual(y, Y + 5, places=6)
        self.assertEqual(self.decision().municipality_code, "28065")


class RealProductsTests(unittest.TestCase):
    def test_exact_accounting_programs_and_no_multi_relation_amounts(self):
        grants = pd.read_parquet("data/processed/grants/session_11_final_03/grants.parquet")
        decisions = pd.read_parquet(DEFAULT / "grant_municipality_links.parquet")
        summary = pd.read_parquet(DEFAULT / "municipality_program_summary.parquet")
        links = pd.read_parquet(DEFAULT / "grant_parcel_links.parquet")
        self.assertTrue(decisions.expediente_id.is_unique)
        self.assertEqual(set(grants.expediente_id), set(decisions.expediente_id))
        self.assertEqual(len(decisions), 7532)
        self.assertEqual(int(summary.importe_centimos.sum()), 31552733899)
        self.assertEqual(int(summary.expedientes.sum()), 7532)
        pd.testing.assert_series_equal(
            grants.groupby("programa").importe_centimos.sum(),
            summary.groupby("programa").importe_centimos.sum(),
        )
        self.assertNotIn("importe_centimos", links)
        self.assertGreater(len(links), 7532)
        self.assertEqual(decisions.municipality_code.eq("28079").sum(), 3808)
        old = decisions[decisions.historical_municipality_code.eq("28079")]
        self.assertEqual(len(old), 3805)
        self.assertTrue(old.municipality_code.eq("28079").all())

    def test_coverage_179_and_only_madrid_cp_bu(self):
        products = pd.read_parquet(DEFAULT / "municipal_products.parquet")
        self.assertEqual(len(products), 179)
        self.assertEqual(int(products.expedientes.sum()), 7532)
        self.assertEqual(int(products.importe_centimos.sum()), 31552733899)
        self.assertEqual(products.cp_available.sum(), 1)
        self.assertEqual(products.bu_available.sum(), 1)
        self.assertEqual(
            products.loc[products.cp_available, "municipality_code"].tolist(), ["28079"]
        )

    def test_replay_exact_decisions_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "out"
            audit = run(out)
            self.assertEqual(audit["total"], 7532)
            for name in [
                "grant_municipality_links",
                "municipality_program_summary",
                "municipal_products",
                "session12_comparison",
            ]:
                self.assertEqual(
                    digest(out / (name + ".parquet")), digest(DEFAULT / (name + ".parquet"))
                )
            with self.assertRaises(FileExistsError):
                run(out)
        initial = json.loads(Path("reports/session_12_1/initial_state.json").read_text())
        for path, sha in initial["protected_files"].items():
            self.assertEqual(digest(path), sha, path)

    def test_real_source_coordinates_and_no_repeated_placeholder_evidence(self):
        grants = pd.read_parquet("data/processed/grants/session_11_final_03/grants.parquet")
        self.assertTrue(grants.longitude.between(-4.6, -3).all())
        self.assertTrue(grants.latitude.between(39.8, 41.2).all())
        # Mismo punto puede representar varias concesiones de una parcela; no se deduplica.
        self.assertGreater(grants.duplicated(["longitude", "latitude"]).sum(), 0)
        decisions = pd.read_parquet(DEFAULT / "grant_municipality_links.parquet")
        repeated = grants.merge(
            decisions[["expediente_id", "municipality_code"]],
            on="expediente_id",
            suffixes=("_old", ""),
        )
        self.assertEqual(
            repeated.groupby(["longitude", "latitude"]).municipality_code.nunique().max(), 1
        )

    def test_21_districts_preserved(self):
        districts = pd.read_parquet("data/processed/session_7_final/district_summary.parquet")
        self.assertEqual(districts.district_code.nunique(), 21)

    def test_real_regional_view_selection_and_public_protection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "app.py"
            path.write_text(
                "from madrid_rehab.regional_view import render_regional\nrender_regional()"
            )
            app = AppTest.from_file(str(path), default_timeout=60).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.selectbox[0].options), 180)
            app.selectbox[0].set_value("28065").run()
            self.assertFalse(app.exception)
            self.assertTrue(any("sin procesar" in item.value for item in app.info))
            self.assertTrue(any(" / 7532" in item.value for item in app.metric))
            with (
                patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}),
                patch(
                    "madrid_rehab.regional_view.load_decisions",
                    side_effect=AssertionError("Public must not load PRTR decisions"),
                ),
            ):
                public = AppTest.from_file(str(path), default_timeout=60).run()
                self.assertFalse(public.exception)
                self.assertEqual(len(public.multiselect), 0)
                self.assertEqual(len(public.get("download_button")), 0)


if __name__ == "__main__":
    unittest.main()
