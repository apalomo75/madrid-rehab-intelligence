"""Public v1.04 address and cadastral map regression checks."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
import shapely as sh

from madrid_rehab import commercial_catalog_store as catalog, grant_address_search as grants
from madrid_rehab.address_search import parse_query
from madrid_rehab.commercial_map import PROJECT, parcel_deck
from madrid_rehab.map_pagination import PAGE_SIZE, page_count, page_refs, spatial_order

BUNDLE = Path(
    os.environ.get(
        "MADRID_REHAB_SESSION39_TEST_BUNDLE", "data/deployment/madrid_rehab_v1_04_candidate_01"
    )
)


class MapTests(unittest.TestCase):
    def test_spatial_pages_partition_the_existing_catalogue(self):
        rows = pd.DataFrame(
            [(f"{i:04d}", (i % 2) * 1000, i // 2) for i in range(2 * PAGE_SIZE + 17)],
            columns=["parcel_ref14", "x", "y"],
        )
        ordered = spatial_order(rows)
        pages = [page_refs(ordered, p) for p in range(page_count(len(rows)))]
        self.assertEqual(list(map(len, pages)), [500, 500, 17])
        self.assertEqual(len(set().union(*map(set, pages))), len(rows))
        self.assertEqual(ordered.iloc[:500].x.nunique(), 1)
        self.assertEqual(page_refs(spatial_order(rows.sample(frac=1, random_state=1)), 0), pages[0])

    def test_map_keeps_original_polygons_and_selected_camera(self):
        west = sh.box(440000, 4470000, 440050, 4470050)
        east = sh.box(441000, 4470000, 441050, 4470050)
        rows = pd.DataFrame({"parcel_ref14": ["A", "B"], "geometry_wkt": [west.wkt, east.wkt]})
        overview, selected = parcel_deck(rows), parcel_deck(rows, "B")
        self.assertEqual(
            overview.initial_view_state.to_json(), selected.initial_view_state.to_json()
        )
        features = selected.layers[0].data["features"]
        for feature, polygon in zip(features, (west, east), strict=True):
            expected = sh.transform(polygon, PROJECT.transform, interleaved=False)
            self.assertTrue(sh.geometry.shape(feature["geometry"]).equals_exact(expected, 0))
        self.assertEqual([item["properties"]["selected"] for item in features], [False, True])
        self.assertIn("[235, 193, 81]", selected.layers[0].get_line_color)
        self.assertLess(selected.initial_view_state.longitude, 0)
        self.assertGreater(selected.initial_view_state.latitude, 0)


class AddressTests(unittest.TestCase):
    def test_public_inputs_preserve_qualifiers_and_normalize_prefixes(self):
        self.assertEqual(parse_query("C/Bailen, 024B"), parse_query("Calle Bailén", "24 B"))
        self.assertEqual(parse_query("P.º del Prado 14"), parse_query("Paseo del Prado", "14"))
        self.assertEqual(parse_query("Av. Bélgica 83"), parse_query("AVENIDA BELGICA", "83"))
        self.assertNotEqual(parse_query("Calle Mayor 24-26"), parse_query("Calle Mayor", "24"))

    @unittest.skipUnless((BUNDLE / "manifest.json").is_file(), "Bundle v1.04 unavailable")
    def test_real_queries_across_the_six_municipalities(self):
        with patch.dict(
            os.environ, {"MADRID_REHAB_PUBLIC": "1", "MADRID_REHAB_BUNDLE_DIR": str(BUNDLE)}
        ):
            variants = [
                ("28079", "Calle Bailén 12", "C/Bailen", "12"),
                ("28065", "Avenida Manuel Azaña 13", "Av. Manuel Azana", "13"),
                ("28092", "Calle Joaquín Blume 9", "C/Joaquin Blume", "9"),
                ("28074", "Avenida Bélgica 83", "Avda Belgica", "83"),
                ("28007", "Calle Berlín 16", "Cl Berlin", "16"),
                ("28005", "Calle Santa Mónica 10", "Cl Santa Monica", "10"),
            ]
            for code, full, short, number in variants:
                with self.subTest(code=code):
                    search = catalog.search if code == "28079" else grants.search
                    originals = search(code, full)[0]
                    self.assertEqual(len(originals), 1)
                    self.assertEqual(originals, search(code, short, number)[0])
                    if code != "28079":
                        ref = originals[0]["reference"]
                        self.assertIsNotNone(catalog.parcel(code, ref))
                        self.assertFalse(search(code, short, "999999")[0])
            mostoles = grants.search("28092", "Calle Río Bidasoa 1")[0]
            alcala = grants.search("28005", "C/Rio Bidasoa 1")[0]
            self.assertEqual(len(mostoles), 1)
            self.assertEqual(len(alcala), 1)
            self.assertNotEqual(mostoles[0]["reference"], alcala[0]["reference"])
            self.assertTrue(grants.search("28007", "Calle Madrid 8")[0])
            self.assertFalse(grants.search("28065", "Calle Madrid 8")[0])

    def test_prtr_release_gate(self):
        with patch("madrid_rehab.production_bundle.allowed_prtr", return_value=False):
            self.assertEqual(grants.search("28007", "Calle Madrid 8"), ([], 0))


if __name__ == "__main__":
    unittest.main()
