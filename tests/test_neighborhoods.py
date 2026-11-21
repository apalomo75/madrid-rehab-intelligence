"""Official hierarchy, conservative spatial allocation, candidate and map paging."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from shapely.geometry import box
from streamlit.testing.v1 import AppTest


from test_municipal_map_events import pick_first_parcel
from madrid_rehab import neighborhoods as geo
from madrid_rehab import commercial_filters as filters, production_bundle as bundle
from madrid_rehab.ingest import digest
from madrid_rehab.map_pagination import page_count, page_refs

CANDIDATE = Path("data/deployment/madrid_rehab_v1_04_candidate_01")
PRODUCT = Path("data/processed/geography/session_35_01")


class AllocationTests(unittest.TestCase):
    def test_crossings_ties_district_conflicts_duplicates_and_missing(self):
        neighborhoods = pd.DataFrame(
            [
                {
                    "neighborhood_code": "011",
                    "district_code": "01",
                    "geometry_wkt": box(0, 0, 5, 10).wkt,
                },
                {
                    "neighborhood_code": "012",
                    "district_code": "01",
                    "geometry_wkt": box(5, 0, 10, 10).wkt,
                },
                {
                    "neighborhood_code": "021",
                    "district_code": "02",
                    "geometry_wkt": box(10, 0, 15, 10).wkt,
                },
            ]
        )
        cases = [
            ("majority", box(4, 1, 9, 4), "01"),
            ("tie", box(4, 1, 6, 4), "01"),
            ("conflict", box(9, 1, 14, 4), "01"),
            ("outside", box(20, 0, 21, 1), "01"),
            ("duplicate", box(1, 1, 2, 2), "01"),
            ("duplicate", box(1, 1, 2, 2), "01"),
            ("no_district", box(1, 1, 2, 2), None),
        ]
        parcels = pd.DataFrame(
            [
                {
                    "parcel_ref14": ref,
                    "district_code": district,
                    "geometry_wkt": geom.wkt,
                    "usable_geometry": True,
                    "geometry_crs": "EPSG:25830",
                }
                for ref, geom, district in cases
            ]
        )
        rows, issues = geo.assign(parcels, neighborhoods)
        result = rows.set_index("parcel_ref14")
        self.assertTrue(rows.parcel_ref14.is_unique)
        self.assertEqual(len(rows), 6)
        self.assertEqual(result.loc["majority", "neighborhood_code"], "012")
        self.assertEqual(result.loc["tie", "neighborhood_code"], "011")
        self.assertEqual(result.loc["conflict", "status"], "district_conflict")
        self.assertEqual(result.loc["duplicate", "status"], "duplicate_parcel_reference")
        self.assertEqual(result.loc["outside", "status"], "no_positive_overlap")
        self.assertEqual(result.loc["no_district", "status"], "district_unassigned")
        self.assertTrue(
            {"crosses_neighborhood_boundary", "area_tie", "district_conflict"}.issubset(
                set(issues.reason)
            )
        )
        reverse, _ = geo.assign(parcels.iloc[::-1], neighborhoods.iloc[::-1].reset_index(drop=True))
        pd.testing.assert_frame_equal(rows, reverse)

    @unittest.skipUnless(
        Path("data/raw/neighborhoods/session_35_capture_02/capture.json").exists(),
        "Official capture unavailable",
    )
    def test_topojson_rejected_service_valid_and_catalogues_identical(self):
        raw = Path("data/raw/neighborhoods/session_35_capture_02")
        meta = json.loads((raw / "capture.json").read_text())
        with self.assertRaisesRegex(ValueError, "Disconnected"):
            geo.decode_topology(json.loads((raw / "Barrios.json").read_text()))
        frame, audit = geo.load_official(raw, meta)
        self.assertTrue(audit["fallback"])
        self.assertTrue(audit["catalogues_identical"])
        self.assertEqual(audit["geometry_repairs"], 0)
        self.assertEqual(len(frame), 131)

    def test_real_page_slices_are_bounded_disjoint_and_complete(self):
        index = pd.DataFrame({"parcel_ref14": [str(i) for i in range(1001)]})
        self.assertEqual(page_count(1001), 3)
        self.assertEqual([len(page_refs(index, p)) for p in range(3)], [500, 500, 1])
        refs = [ref for p in range(3) for ref in page_refs(index, p)]
        self.assertEqual(refs, index.parcel_ref14.tolist())
        self.assertEqual(page_count(0), 1)
        self.assertEqual(page_count(1000), 2)
        with self.assertRaises(ValueError):
            page_refs(index, 3)
        with self.assertRaises(ValueError):
            page_refs(index, -1)


@unittest.skipUnless((CANDIDATE / "manifest.json").exists(), "New real candidate unavailable")
class OfficialProductTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(
            os.environ,
            {
                "MADRID_REHAB_PUBLIC": "1",
                "MADRID_REHAB_OFFLINE": "1",
                "MADRID_REHAB_BUNDLE_DIR": str(CANDIDATE.resolve()),
                "MADRID_REHAB_DEV": "0",
                "MADRID_REHAB_DEMO": "0",
                "MADRID_REHAB_PILOT": "0",
            },
        )
        env.start()
        self.addCleanup(env.stop)

    def test_131_neighborhoods_parent_hashes_and_assignment_integrity(self):
        parent = json.loads(Path("data/deployment/madrid_rehab_v1_03/manifest.json").read_text())
        meta = bundle.metadata()
        self.assertEqual(meta["policy"], parent["policy"])
        self.assertEqual(meta["prtr_authorization"], parent["prtr_authorization"])
        self.assertEqual(meta["counts"], parent["counts"])
        self.assertEqual(meta["candidate_status"], "local_visual_review_pending")
        for name, item in parent["files"].items():
            self.assertEqual(meta["files"][name], item)
            self.assertEqual(digest(CANDIDATE / name), item["sha256"])
        self.assertEqual(
            set(meta["files"]) - set(parent["files"]),
            {"geography/assignments.parquet", "geography/neighborhoods.parquet"},
        )
        names = geo.read("neighborhoods.parquet")
        self.assertEqual(
            (len(names), names.neighborhood_code.nunique(), names.district_code.nunique()),
            (131, 131, 21),
        )
        self.assertEqual(geo.names("17")["174"], "Los Rosales")
        self.assertEqual(geo.names("07")["071"], "Gaztambide")
        assignments = geo.read("assignments.parquet")
        self.assertTrue(assignments.parcel_ref14.is_unique)
        assigned = assignments[assignments.status.eq("assigned")]
        checked = assigned.merge(
            names,
            on=["municipality_code", "district_code", "neighborhood_code"],
            validate="many_to_one",
        )
        self.assertEqual(len(assigned), len(checked))
        self.assertEqual(len(assignments), 140595)
        self.assertEqual(len(assigned), 140360)
        issues = pd.read_parquet(PRODUCT / "issues.parquet")
        self.assertTrue(issues.reason.eq("district_conflict").any())
        self.assertEqual(assignments.status.ne("assigned").sum(), 235)
        with self.assertRaises(ValueError):
            geo.restrict(filters.query("28079"), "07", "174")

    def test_geography_after_evidence_or_and_and_six_towns(self):
        full = filters.query("28079")
        for district, neighborhood in [("17", "174"), ("07", "071")]:
            selected = set(geo.restrict(full, district, neighborhood).parcel_ref14)
            self.assertTrue(selected)
            energy = set(filters.query("28079", ["energy"]).parcel_ref14)
            prtr = set(filters.query("28079", ["prtr"]).parcel_ref14)
            for logic, expected in [("OR", energy | prtr), ("AND", energy & prtr)]:
                result = geo.restrict(
                    filters.query("28079", ["energy", "prtr"], logic), district, neighborhood
                )
                self.assertEqual(set(result.parcel_ref14), selected & expected)
        self.assertEqual(len(filters.query("28079", ["prtr"])), 3300)
        for code in bundle.metadata()["counts"]:
            rows = filters.query(code)
            self.assertTrue(rows.parcel_ref14.is_unique)
            self.assertEqual(len(rows), bundle.metadata()["counts"][code])

    def app(self):
        return AppTest.from_string(
            "from madrid_rehab.i18n import language_selector\nlanguage_selector()\nfrom madrid_rehab.commercial_catalog_view import render\nrender()",
            default_timeout=180,
        ).run()

    def test_dependent_selectors_fiche_evidence_language_and_towns(self):
        app = self.app()
        self.assertFalse(app.exception)
        self.assertTrue(app.selectbox(key="catalog_neighborhood").disabled)
        self.assertFalse(any(s.label == "Página del mapa" for s in app.selectbox))
        for district, neighborhood in [("17", "174"), ("07", "071")]:
            app.selectbox(key="catalog_district").set_value(district).run()
            self.assertEqual(app.selectbox(key="catalog_neighborhood").value, "all")
            app.selectbox(key="catalog_neighborhood").set_value(neighborhood).run()
            expected = geo.restrict(filters.query("28079"), district, neighborhood)
            self.assertEqual(int(app.metric[0].value.replace(",", "")), len(expected))
            app.checkbox(key="priority_28079_prtr").check().run()
            app.checkbox(key="priority_28079_energy").check().run()
            for logic in ("OR", "AND"):
                app.radio(key="priority_logic_28079").set_value(logic).run()
                count = len(
                    geo.restrict(
                        filters.query("28079", ["energy", "prtr"], logic), district, neighborhood
                    )
                )
                self.assertEqual(int(app.metric[0].value.replace(",", "")), count)
            app.radio(key="priority_logic_28079").set_value("OR").run()
            pick_first_parcel(app)
            self.assertFalse(app.exception)
            identity = app.session_state["fiche_identity"]
            self.assertIn(identity[2], set(expected.parcel_ref14))
            app.radio(key="language_selector").set_value("EN").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key="catalog_neighborhood").label, "Neighborhood")
            self.assertEqual(app.selectbox(key="catalog_neighborhood").value, neighborhood)
            self.assertEqual(app.session_state["fiche_identity"], identity)
            app.radio(key="language_selector").set_value("ES").run()
            next(b for b in app.button if b.label == "Limpiar filtros").click().run()
        for code in ("28005", "28007", "28065", "28074", "28092"):
            app.selectbox(key="catalog_municipality").set_value(code).run()
            self.assertFalse(app.exception)
            self.assertFalse(
                any(s.key in {"catalog_neighborhood", "catalog_district"} for s in app.selectbox)
            )
            self.assertEqual(
                int(app.metric[0].value.replace(",", "")), bundle.metadata()["counts"][code]
            )
        app.selectbox(key="catalog_municipality").set_value("28079").run()
        self.assertEqual(app.selectbox(key="catalog_district").value, "all")
        self.assertEqual(app.selectbox(key="catalog_neighborhood").value, "all")

    def test_map_first_middle_last_reset_and_selection(self):
        app = self.app()
        prefix = "municipal_28079__cp_catalog_public_OR_"
        self.assertTrue(app.button(key=prefix + "_map_previous").disabled)
        self.assertFalse(app.button(key=prefix + "_map_next").disabled)
        first = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
        first_refs = {f["properties"]["unit_id"] for f in first["layers"][0]["data"]["features"]}
        app.button(key=prefix + "_map_next").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state[prefix + "_map_page_all"], 1)
        middle = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
        middle_refs = {f["properties"]["unit_id"] for f in middle["layers"][0]["data"]["features"]}
        self.assertFalse(first_refs & middle_refs)
        self.assertEqual(len(middle_refs), 500)
        # Set the last valid page directly through application state, then test real controls.
        pages = page_count(len(filters.query("28079")))
        app.session_state[prefix + "_map_page_all"] = pages - 1
        app.run()
        self.assertTrue(app.button(key=prefix + "_map_next").disabled)
        last = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
        self.assertEqual(len(last["layers"][0]["data"]["features"]), 50)
        app.button(key=prefix + "_map_previous").click().run()
        self.assertEqual(app.session_state[prefix + "_map_page_all"], pages - 2)
        app.radio(key="language_selector").set_value("EN").run()
        self.assertEqual(app.session_state[prefix + "_map_page_all"], pages - 2)
        self.assertEqual(app.button(key=prefix + "_map_next").label, "Next")
        app.selectbox(key="catalog_district").set_value("17").run()
        self.assertEqual(app.session_state[prefix + "_map_page_all"], 0)
        app.button(key=prefix + "_map_next").click().run()
        app.selectbox(key="catalog_neighborhood").set_value("174").run()
        self.assertEqual(app.session_state[prefix + "_map_page_all"], 0)
        # Changing the page clears the selected parcel.
        pick_first_parcel(app)
        self.assertFalse(app.exception)
        app.button(key=prefix + "_map_next").click().run()
        self.assertIsNone(app.session_state["fiche_identity"])
        app.checkbox(key="priority_28079_energy").check().run()
        new_prefix = "municipal_28079__cp_catalog_public_OR_energy"
        self.assertEqual(app.session_state[new_prefix + "_map_page_all"], 0)


if __name__ == "__main__":
    unittest.main()
