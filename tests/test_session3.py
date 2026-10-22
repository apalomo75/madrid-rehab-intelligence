"""Contratos de selección por identidad, filtros temporales y presentación cartográfica."""

import base64
import json
import unittest

import pandas as pd

from madrid_rehab.map_view import (
    deck,
    map_style,
    polygon_records,
    selected_building,
    filtered_view,
)
import test_session2


class SelectionTests(unittest.TestCase):
    def test_event_uses_identity_and_rejects_filtered_or_stale_object(self):
        event = {
            "selection": {
                "objects": {"buildings": [{"building_id": "BU2"}]},
                "indices": {"buildings": [0]},
            }
        }
        self.assertEqual(selected_building(event, {"BU1", "BU2"}), "BU2")
        self.assertIsNone(selected_building(event, {"BU1"}))
        self.assertIsNone(selected_building({}, {"BU1"}))

    def test_multipolygon_members_keep_id_and_holes(self):
        rings = [[[0, 0], [4, 0], [4, 4], [0, 0]], [[1, 1], [2, 1], [2, 2], [1, 1]]]
        objects = pd.DataFrame(
            [
                dict(
                    building_id="BU1",
                    parcel_ref14="P",
                    certificate_count=2,
                    confirmed_count=2,
                    map_color=[21, 128, 131, 185],
                    geometry_geojson=json.dumps(
                        {"type": "MultiPolygon", "coordinates": [rings, [rings[0]]]}
                    ),
                )
            ]
        )
        records = polygon_records(objects, "BU1")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["polygon"], rings)
        self.assertEqual({r["building_id"] for r in records}, {"BU1"})
        self.assertTrue(all(r["line_width"] == 4 for r in records))
        self.assertNotIn("energy_grade", records[0])

    def test_styles_are_explicit_and_offline_has_no_remote_resources(self):
        def decode(urban):
            return json.loads(base64.b64decode(map_style(urban).split(",", 1)[1]))

        local, urban = decode(False), decode(True)
        self.assertEqual(local["sources"], {})
        self.assertNotIn("http", json.dumps(local))
        self.assertIn("OpenStreetMap", urban["sources"]["osm"]["attribution"])
        self.assertEqual(urban["sources"]["osm"]["maxzoom"], 19)

    def test_year_filters_use_certificate_date_and_preserve_true_absence(self):
        b, c, links = test_session2.MapViewTests().inputs()
        c["certificate_date"] = pd.to_datetime(["2025-02-03"])
        objects, visible, _ = filtered_view(b, c, links, year="2026")
        self.assertEqual(objects.building_id.tolist(), ["BU2"])
        self.assertTrue(visible.empty)
        self.assertEqual(len(filtered_view(b, c, links, year="2025")[1]), 1)
        c["certificate_date"] = pd.NaT
        self.assertEqual(len(filtered_view(b, c, links, year="missing")[1]), 1)

    def test_several_bu_and_several_letters_do_not_multiply_records(self):
        b, c, links = test_session2.MapViewTests().inputs()
        b.loc[1, "parcel_ref14"] = b.loc[0, "parcel_ref14"]
        c = pd.concat(
            [
                c,
                c.assign(
                    record_id="CERT2", cal_norenovglobal="A", certificate_scope="whole_building"
                ),
            ],
            ignore_index=True,
        )
        links = pd.DataFrame(
            [
                {"certificate_id": cid, "building_id": bid}
                for cid in c.record_id
                for bid in b.building_id
            ]
        )
        objects, visible, related = filtered_view(b, c, links)
        self.assertEqual(objects.certificate_count.tolist(), [2, 2])
        self.assertEqual(len(visible), 2)
        self.assertEqual(len(related), 4)
        self.assertEqual(set(visible.certificate_scope), {"dwelling", "whole_building"})
        self.assertFalse(visible.physical_status.eq("confirmed").any())

    def test_camera_and_layer_ids_do_not_change_on_selection(self):
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-3.71, 40.43], [-3.70, 40.43], [-3.70, 40.44], [-3.71, 40.43]]],
            },
        }
        a = json.loads(deck(pd.DataFrame(), feature, None).to_json())
        b = json.loads(deck(pd.DataFrame(), feature, None, selected="BU1").to_json())
        self.assertEqual(a["initialViewState"], b["initialViewState"])
        self.assertEqual(a["layers"][1]["id"], "buildings")
        self.assertEqual(a["layers"][1]["@@type"], "PolygonLayer")
