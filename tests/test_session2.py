"""Contratos de sesión 2: casos sintéticos; ninguna fila se usa en el mapa real."""

import json
import base64
import tempfile
import unittest

import pandas as pd
import shapely as sh
from shapely.geometry import Polygon, Point

from madrid_rehab.districts import assign
from madrid_rehab.session2 import (
    normalize_reference,
    geometry_audit,
    link,
    combine_status,
    compare_districts,
    map_objects,
    run,
)
from madrid_rehab.map_view import filtered_view, features_for_map, deck

P = "1234567VK4712A"
Q = "7654321VK4712A"
WKT = "MULTIPOLYGON (((440000 4470000, 440010 4470000, 440010 4470010, 440000 4470010, 440000 4470000)))"


def certificate(cid="CERT1", reference=P + "0001AB", scope="dwelling", **kwargs):
    return {
        "record_id": cid,
        "edif_refcat": reference,
        "edif_codreg": cid,
        "certificate_scope": scope,
        "cal_norenovglobal": "E",
        **kwargs,
    }


def parcel(rid="PARCEL1", ref=P, **kwargs):
    return {
        "record_id": rid,
        "parcel_ref14": ref,
        "reference_key": ref,
        "district_code": "07",
        "usable_geometry": True,
        "geometry_wkt": WKT,
        "geometry_crs": "EPSG:25830",
        **kwargs,
    }


def building(bid="BU1", ref=P, **kwargs):
    return {
        "record_id": bid,
        "building_id": bid,
        "parcel_ref14": ref,
        "reference_key": ref,
        "district_code": "07",
        "usable_geometry": True,
        "geometry_wkt": WKT,
        "geometry_crs": "EPSG:25830",
        "current_use": "1_residential",
        "construction_begin": "1900-01-01T00:00:00",
        "construction_end": "2000-01-01T00:00:00",
        "crosses_district_boundary": False,
        **kwargs,
    }


class ReferenceTests(unittest.TestCase):
    def test_urban_and_rural_keep_property_level(self):
        for value in [P, P + "0001AB", "28079A00100001", "28079A001000010001AB"]:
            result = normalize_reference(" " + value.lower() + " ")
            self.assertTrue(result["format_valid"])
            self.assertEqual(result["parcel_ref14"], value[:14])
        self.assertEqual(normalize_reference(P + "0001AB")["checksum_status"], "not_checked")

    def test_no_repair_of_invalid_characters(self):
        for raw in ["", None, "bad", P + "-0001AB", "1234567VÉ4712A", P + "0O01AB"]:
            self.assertFalse(normalize_reference(raw)["format_valid"])

    def test_aggregate_partial_and_ambiguous(self):
        self.assertEqual(combine_status(["confirmed", "unmatched"]), "candidate")
        self.assertEqual(combine_status(["confirmed", "ambiguous"]), "ambiguous")
        self.assertEqual(combine_status(["unmatched"]), "unmatched")


class LinkTests(unittest.TestCase):
    def execute(self, cs=None, ps=None, bs=None):
        return link(
            pd.DataFrame(cs or [certificate()]),
            pd.DataFrame(ps or [parcel()]),
            pd.DataFrame(bs or [building()]),
        )

    def test_dwelling_confirms_parcel_not_property_or_physical_building(self):
        links, summary = self.execute()
        r = summary.iloc[0]
        self.assertEqual(r.parcel_status, "confirmed")
        self.assertEqual(r.property_status, "candidate")
        self.assertEqual(r.physical_status, "candidate")
        self.assertIsNone(r.confirmed_physical_building_id)
        self.assertEqual(r.certificate_scope, "dwelling")
        self.assertEqual(links.iloc[0].physical_reason, "individual_scope_does_not_cover_bu")

    def test_whole_building_alone_is_not_physical_evidence(self):
        for scope in ["whole_building", "unknown", "building_part"]:
            with self.subTest(scope=scope):
                links, summary = self.execute(cs=[certificate(scope=scope)])
                self.assertEqual(summary.iloc[0].physical_status, "candidate")
                self.assertIsNone(summary.iloc[0].confirmed_physical_building_id)

    def test_multiple_bu_on_parcel_keeps_ambiguity(self):
        links, summary = self.execute(bs=[building(), building("BU2")])
        self.assertEqual(summary.iloc[0].parcel_status, "confirmed")
        self.assertEqual(summary.iloc[0].physical_status, "ambiguous")
        self.assertEqual(links.iloc[0].candidate_building_ids, ["BU1", "BU2"])

    def test_duplicate_parcels_not_silently_resolved(self):
        links, summary = self.execute(ps=[parcel(), parcel("PARCEL2")])
        self.assertEqual(summary.iloc[0].parcel_status, "ambiguous")
        self.assertEqual(summary.iloc[0].physical_status, "ambiguous")
        self.assertEqual(summary.iloc[0].district_location_quality, "candidate")
        self.assertEqual(len(links.iloc[0].parcel_record_ids), 2)

    def test_duplicate_parcels_different_districts_cannot_localize(self):
        _, summary = self.execute(ps=[parcel(), parcel("PARCEL2", district_code="11")])
        self.assertIsNone(summary.iloc[0].district_code)

    def test_partial_multi_reference_not_promoted_to_confirmed(self):
        links, summary = self.execute(cs=[certificate(reference=P + ";bad")])
        self.assertEqual(len(links), 2)
        self.assertFalse(summary.iloc[0].all_references_format_valid)
        self.assertEqual(summary.iloc[0].parcel_status, "candidate")
        self.assertIsNone(summary.iloc[0].district_code)

    def test_multiple_references_resolving_to_multiple_bu(self):
        _, summary = self.execute(
            cs=[certificate(reference=P + ";" + Q, scope="whole_building")],
            ps=[parcel(), parcel("P2", Q)],
            bs=[building(), building("B2", Q)],
        )
        self.assertEqual(summary.iloc[0].parcel_status, "confirmed")
        self.assertEqual(summary.iloc[0].physical_status, "ambiguous")

    def test_invalid_bu_kept_as_candidate_excluded_from_map(self):
        links, summary = self.execute(bs=[building(usable_geometry=False)])
        self.assertEqual(links.iloc[0].physical_reason, "invalid_bu_geometry")
        self.assertEqual(summary.iloc[0].physical_status, "candidate")
        self.assertTrue(map_objects(pd.DataFrame([building(usable_geometry=False)]), "07").empty)

    def test_unmatched_reference_preserved(self):
        links, summary = self.execute(cs=[certificate(reference=Q)])
        self.assertEqual(summary.iloc[0].parcel_status, "unmatched")
        self.assertEqual(summary.iloc[0].physical_status, "unmatched")
        self.assertEqual(links.iloc[0].reference_raw, Q)

    def test_shared_code_conflicting_reference_is_ambiguous(self):
        _, summary = self.execute(
            cs=[certificate(), certificate("CERT2", reference=Q, edif_codreg="CERT1")],
            ps=[parcel(), parcel("P2", Q)],
        )
        self.assertTrue(summary.parcel_status.eq("ambiguous").all())

    def test_order_does_not_change_links_or_traceability(self):
        cs = pd.DataFrame([certificate(), certificate("CERT2")])
        ps, bs = pd.DataFrame([parcel()]), pd.DataFrame([building()])
        a, sa = link(cs, ps, bs)
        b, sb = link(cs.iloc[::-1], ps, bs)
        pd.testing.assert_frame_equal(a, b)
        pd.testing.assert_frame_equal(sa, sb)

    def test_reordered_source_indices_keep_same_targets(self):
        cs = pd.DataFrame([certificate(), certificate("C2", reference=Q)])
        ps = pd.DataFrame([parcel(), parcel("P2", ref=Q)])
        bs = pd.DataFrame([building(), building("B2", ref=Q)])
        a, sa = link(cs, ps, bs)
        b, sb = link(cs.iloc[::-1], ps.iloc[::-1], bs.iloc[::-1])
        pd.testing.assert_frame_equal(a, b)
        pd.testing.assert_frame_equal(sa, sb)

    def test_output_cannot_overwrite_session_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run(tmp, tmp, tmp)


class SpatialTests(unittest.TestCase):
    def test_invalid_geometry_and_crs_flagged(self):
        bowtie = "MULTIPOLYGON (((440000 4470000, 440010 4470010, 440010 4470000, 440000 4470010, 440000 4470000)))"
        f, _ = geometry_audit(
            pd.DataFrame(
                [
                    parcel(geometry_wkt=bowtie),
                    parcel("P2", geometry_crs="EPSG:4326"),
                    parcel("P3", geometry_wkt=None),
                ]
            )
        )
        self.assertFalse(f.usable_geometry.any())
        self.assertEqual(f.iloc[0].geometry_wkt, bowtie)

    def test_assignment_boundary_points_and_crossing_polygons(self):
        districts = pd.DataFrame(
            {
                "district_code": ["07", "11"],
                "geometry_wkt": [
                    Polygon([(0, 0), (5, 0), (5, 10), (0, 10)]).wkt,
                    Polygon([(5, 0), (10, 0), (10, 10), (5, 10)]).wkt,
                ],
            }
        )
        result = assign([Point(2, 2), Point(5, 2), Point(15, 2)], districts, polygon=False)
        self.assertEqual(result.district_code.iloc[0], "07")
        self.assertEqual(result.district_assignment.iloc[1], "boundary_ambiguous")
        self.assertIsNone(result.district_code.iloc[2])
        polygon = Polygon([(3, 1), (8, 1), (8, 4), (3, 4)])
        crossing = assign([polygon], districts)
        self.assertTrue(crossing.crosses_district_boundary.iloc[0])
        self.assertEqual(len(crossing), 1)

    def test_pilot_uses_quality_then_smaller_review_volume(self):
        districts = pd.DataFrame(
            {"district_code": ["07", "11", "12"], "district_name": ["A", "B", "C"]}
        )
        cs = pd.DataFrame(
            [
                certificate(
                    f"{d}-{i}",
                    parcel_status="confirmed",
                    physical_status="candidate",
                    district_code=d,
                )
                for d in ["07", "11", "12"]
                for i in range(100)
            ]
        )
        ps = pd.DataFrame(
            [
                parcel(f"P{d}", district_code=d, crosses_district_boundary=False)
                for d in ["07", "11", "12"]
            ]
        )
        bs = pd.DataFrame(
            [
                building("B07a"),
                building("B07b"),
                building("B11a", district_code="11"),
                building("B12a", district_code="12"),
            ]
        )
        comparison, pilot = compare_districts(cs, ps, bs, districts)
        self.assertEqual(pilot["district_code"], "11")
        self.assertEqual(len(comparison), 3)

    def test_display_keeps_original_geometry(self):
        original = pd.DataFrame([building()])
        result = map_objects(original, "07")
        self.assertEqual(original.iloc[0].geometry_wkt, WKT)
        self.assertEqual(result.iloc[0].construction_oldest_year, 1900)
        self.assertTrue(sh.geometry.shape(json.loads(result.iloc[0].geometry_geojson)).is_valid)


class MapViewTests(unittest.TestCase):
    def inputs(self):
        objects = pd.DataFrame([building(), building("BU2", Q)])
        certs = pd.DataFrame(
            [
                certificate(
                    parcel_status="confirmed",
                    property_status="candidate",
                    physical_status="candidate",
                )
            ]
        )
        contexts = pd.DataFrame(
            [
                {"certificate_id": "CERT1", "building_id": "BU1"},
                {"certificate_id": "CERT1", "building_id": "BU1"},
            ]
        )
        return objects, certs, contexts

    def test_counts_do_not_multiply_certificates(self):
        objects, certs, _ = filtered_view(*self.inputs())
        self.assertEqual(len(certs), 1)
        self.assertEqual(objects.certificate_count.sum(), 1)
        self.assertEqual(objects.information_state.tolist(), ["confirmed", "none"])
        self.assertNotIn("energy_grade", objects.columns)

    def test_filtered_existing_information_is_not_marked_absent(self):
        objects, certs, _ = filtered_view(*self.inputs(), grade="A")
        self.assertEqual(objects.building_id.tolist(), ["BU2"])
        self.assertTrue(certs.empty)

    def test_no_false_physical_confirmation(self):
        objects, certs, _ = filtered_view(*self.inputs(), level="physical_status")
        self.assertEqual(objects.information_state.tolist(), ["uncertain", "none"])
        self.assertEqual(int(certs.physical_status.eq("confirmed").sum()), 0)

    def test_no_information_and_empty_filter(self):
        objects, certs, _ = filtered_view(*self.inputs(), grade="A", include_unlinked=False)
        self.assertTrue(objects.empty)
        self.assertTrue(certs.empty)
        self.assertEqual(features_for_map(objects)["features"], [])

    def test_map_style_is_local_url_compatible_with_streamlit(self):
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-3.71, 40.43], [-3.70, 40.43], [-3.70, 40.44], [-3.71, 40.43]]],
            },
        }
        chart = deck(pd.DataFrame(), feature, [-3.7, 40.43])
        style = json.loads(chart.to_json())["mapStyle"]
        self.assertIsInstance(style, str)
        self.assertTrue(style.startswith("data:application/json;base64,"))
        decoded = json.loads(base64.b64decode(style.split(",", 1)[1]))
        self.assertEqual(decoded["sources"], {})
        self.assertNotIn("glyphs", decoded)
