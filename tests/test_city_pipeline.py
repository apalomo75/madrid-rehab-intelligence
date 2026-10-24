"""Contratos de expansión; fixtures sintéticos solo en tests."""

import unittest

import pandas as pd
from shapely.geometry import box

import test_sessions456 as fixtures
from madrid_rehab import districts
from madrid_rehab.city_audit import district_summary, quality_links, reconcile
from madrid_rehab.city_pipeline import analytic_audit, display_geometries
from madrid_rehab.features import parcel_features
from madrid_rehab.profiles import add_profiles
from madrid_rehab.territory import (
    CODES,
    add_grid,
    parcel_territories,
    resolve_district,
    validate_districts,
)


def boundaries():
    return pd.DataFrame(
        {
            "district_code": list(CODES),
            "district_name": [f"Distrito {code}" for code in CODES],
            "geometry_crs": ["EPSG:25830"] * 21,
            "geometry_wkt": [
                box(400000 + n * 1000, 4470000, 400900 + n * 1000, 4470900).wkt for n in range(21)
            ],
        }
    )


class TerritoryTests(unittest.TestCase):
    def test_exact_21_codes(self):
        self.assertEqual(len(validate_districts(boundaries())), 21)
        with self.assertRaises(ValueError):
            validate_districts(boundaries().iloc[:-1])
        bad = boundaries()
        bad.loc[0, "district_code"] = "99"
        with self.assertRaises(ValueError):
            validate_districts(bad)

    def test_invalid_crs_geometry_overlap(self):
        for mutate in ["crs", "geometry", "overlap"]:
            bad = boundaries()
            if mutate == "crs":
                bad.loc[0, "geometry_crs"] = "EPSG:4326"
            elif mutate == "geometry":
                bad.loc[0, "geometry_wkt"] = "POLYGON EMPTY"
            else:
                bad.loc[0, "geometry_wkt"] = bad.loc[1, "geometry_wkt"]
            with self.assertRaises(ValueError):
                validate_districts(bad)

    def test_resolve_name_accent_code_all(self):
        frame = boundaries()
        frame.loc[6, "district_name"] = "Chamberí"
        self.assertEqual(resolve_district("chamberi", frame), "07")
        self.assertEqual(resolve_district("7", frame), "07")
        self.assertEqual(resolve_district("ALL", frame), "all")
        with self.assertRaises(ValueError):
            resolve_district("../raw", frame)

    def test_cross_district_rc_not_first_row_assignment(self):
        cp = pd.DataFrame(
            {"parcel_ref14": ["a", "a", "b", "c"], "district_code": ["01", "02", "01", None]}
        )
        owner = parcel_territories(cp).set_index("parcel_ref14")
        self.assertTrue(pd.isna(owner.loc["a", "district_code"]))
        self.assertEqual(owner.loc["a", "district_assignment"], "ambiguous_reference_district")
        self.assertEqual(owner.loc["a", "cp_rows"], 2)
        self.assertEqual(owner.loc["b", "district_code"], "01")
        pd.testing.assert_frame_equal(parcel_territories(cp), parcel_territories(cp.iloc[::-1]))

    def test_same_district_duplicate_cp_keeps_ambiguity_count(self):
        cp = pd.DataFrame({"parcel_ref14": ["a", "a"], "district_code": ["01", "01"]})
        row = parcel_territories(cp).iloc[0]
        self.assertEqual(row.district_code, "01")
        self.assertEqual(row.cp_rows, 2)

    def test_null_district_on_one_cp_prevents_assignment(self):
        cp = pd.DataFrame({"parcel_ref14": ["a", "a"], "district_code": ["01", None]})
        self.assertTrue(pd.isna(parcel_territories(cp).iloc[0].district_code))

    def test_border_crossing_and_invalid_geometry(self):
        frame = pd.DataFrame(
            {
                "district_code": ["01", "02"],
                "geometry_wkt": [box(0, 0, 10, 10).wkt, box(10, 0, 20, 10).wkt],
            }
        )
        result = districts.assign([box(8, 1, 11, 2), box(9, 1, 11, 2), None], frame)
        self.assertTrue(result.iloc[0].crosses_district_boundary)
        self.assertEqual(result.iloc[1].district_assignment, "boundary_ambiguous")
        self.assertTrue(pd.isna(result.iloc[2].district_code))

    def test_grid_requires_unique_cp_and_metric_crs(self):
        cp = pd.DataFrame(
            {
                "parcel_ref14": ["a", "a", "b", "c"],
                "x": [440000] * 4,
                "y": [4470000] * 4,
                "coordinate_crs": ["EPSG:25830"] * 3 + ["EPSG:4326"],
            }
        )
        result = add_grid(pd.DataFrame({"parcel_ref14": ["a", "b", "c"]}), cp)
        self.assertTrue(pd.isna(result.iloc[0].analysis_zone))
        self.assertEqual(result.iloc[1].analysis_zone, "E440000_N4470000")
        self.assertTrue(pd.isna(result.iloc[2].analysis_zone))


class CityAggregationTests(unittest.TestCase):
    def setUp(self):
        case = fixtures.AnalyticsTests()
        case.setUp()
        self.cp, self.bu, self.cert, self.links = (
            case.parcels.copy(),
            case.bu.copy(),
            case.cert.copy(),
            case.links.copy(),
        )
        self.cp["crosses_district_boundary"] = False
        (
            self.bu["district_code"],
            self.bu["crosses_district_boundary"],
            self.bu["usable_geometry"],
        ) = "07", False, True

    def test_all_preserves_residual_universe_and_district_selection(self):
        self.cp.loc[1, "district_code"] = None
        city = parcel_features(self.cp, self.bu, self.cert, self.links, "all")
        self.assertEqual(len(city), 2)
        self.assertEqual(city.district_code.isna().sum(), 1)
        old = parcel_features(self.cp, self.bu, self.cert, self.links)
        self.assertEqual(len(old), 1)
        self.assertEqual(old.ceee_records_observed.sum(), city.ceee_records_observed.sum())

    def test_multiparcel_cross_district_records_are_not_additive(self):
        self.cp.loc[1, "district_code"] = "08"
        self.links = pd.concat([self.links, self.links.iloc[:1].assign(parcel_ref14="other")])
        q, energy = quality_links(self.cp, self.cert, self.links)
        features = add_profiles(parcel_features(self.cp, self.bu, self.cert, self.links, "all"))
        summary = district_summary(features, self.bu, self.cp, energy, q, boundaries())
        report = reconcile(features, self.bu, self.cp, energy, summary)
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["municipal_unique_certificates"], 1)
        self.assertEqual(report["district_certificate_memberships"], 2)
        self.assertEqual(report["municipal_record_parcel_pairs"], 2)

    def test_candidate_never_promoted(self):
        self.cert.loc[0, "parcel_status"] = "candidate"
        q, energy = quality_links(self.cp, self.cert, self.links)
        self.assertTrue(energy.empty)
        self.assertEqual(q.iloc[0].analytic_status, "candidate")

    def test_duplicate_cp_confirmed_input_rejected_analytically(self):
        self.cp = pd.concat([self.cp, self.cp.iloc[:1]])
        q, energy = quality_links(self.cp, self.cert, self.links)
        self.assertTrue(energy.empty)
        self.assertTrue(q.analytic_status.eq("rejected").all())

    def test_analytic_audit_detects_corruption(self):
        _, energy = quality_links(self.cp, self.cert, self.links)
        f = parcel_features(self.cp, self.bu, self.cert, self.links, "all")
        self.assertTrue(all(analytic_audit(f, energy)["checks"].values()))
        f.loc[0, "ceee_valid_grade_count"] = 999
        with self.assertRaises(ValueError):
            analytic_audit(f, energy)

    def test_display_geometries_do_not_include_invalid_rows(self):
        frame = pd.DataFrame(
            {
                "record_id": ["a", "b"],
                "parcel_ref14": ["p", "q"],
                "usable_geometry": [True, False],
                "geometry_wkt": [box(440000, 4470000, 440010, 4470010).wkt, "POLYGON EMPTY"],
            }
        )
        result = display_geometries(frame, "cp")
        self.assertEqual(result.record_id.tolist(), ["a"])
        self.assertIn("geometry_geojson", result)
        self.assertNotIn("geometry_wkt", result)


class LargeChartTests(unittest.TestCase):
    def test_many_records_use_real_aggregate_counts_under_altair_limit(self):
        import numpy as np
        from madrid_rehab.analysis_charts import evidence_scatter

        n = 6000
        index = np.arange(n)
        data = pd.DataFrame(
            {
                "parcel_ref14": [f"p{i}" for i in index],
                "construction_oldest_year": 1000 + (index // 100) * 10,
                "ceee_valid_grade_count": 3,
                "ceee_efg_share_observed": (index % 20) / 20,
                "energy_profile": (index // 20 % 5).astype(str),
                "review_flags": "",
            }
        )
        chart = evidence_scatter(data).to_dict()
        values = next(iter(chart["datasets"].values()))
        self.assertLessEqual(len(values), 5000)
        self.assertEqual(sum(row["parcels"] for row in values), n)
