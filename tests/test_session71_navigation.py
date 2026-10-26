"""Regresiones de navegación con datos reales; AppTest no sustituye clic WebGL."""

import base64
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

import pandas as pd
from pyproj import Transformer
from streamlit.testing.v1 import AppTest

from madrid_rehab.city_maps import (
    district_deck,
    geographic_zone,
    zone_records,
    zone_selection,
)
from madrid_rehab.profiles import csv_export

ROOT = Path("data/processed/session_7_final")


class GridTests(unittest.TestCase):
    def test_known_madrid_coordinate(self):
        # Puerta del Sol: control independiente de orden de ejes y CRS.
        self.assertEqual(
            geographic_zone(-3.7038, 40.4168, {"E440000_N4474000"}), "E440000_N4474000"
        )
        self.assertIsNone(geographic_zone(40.4168, -3.7038, {"E440000_N4474000"}))

    def test_roundtrip_cell_centres_and_edges(self):
        convert = Transformer.from_crs(25830, 4326, always_xy=True)
        zones = {"E440000_N4479500", "E440500_N4479500"}
        for x, expected in [
            (440250, "E440000_N4479500"),
            (440499.99, "E440000_N4479500"),
            (440500.01, "E440500_N4479500"),
            (440750, "E440500_N4479500"),
        ]:
            lon, lat = convert.transform(x, 4479750)
            self.assertEqual(geographic_zone(lon, lat, zones), expected)

    def test_invalid_and_unavailable_coordinates(self):
        for lon, lat in [(None, 40.4), (float("nan"), 40.4), (-3.7, float("inf")), (0, 0)]:
            self.assertIsNone(geographic_zone(lon, lat, set()))
        self.assertIsNone(geographic_zone(-3.7038, 40.4168, set()))

    def test_identity_not_untrusted_click_coordinates(self):
        event = {"selection": {"objects": {"district-zones": [{"zone_id": "valid"}]}}}
        self.assertEqual(zone_selection(event, {"valid"}), "valid")
        self.assertIsNone(zone_selection(event, {"other"}))
        self.assertIsNone(
            zone_selection({"selection": {"objects": {"layer": [{"zone_id": []}]}}}, set())
        )

    def test_grid_geometry_and_offline(self):
        b = pd.DataFrame({"map_zone": ["E440500_N4479500"] * 2})
        p = pd.DataFrame({"map_zone": ["E440500_N4479500"]})
        records = zone_records(b, p)
        self.assertEqual((records[0]["bu_count"], records[0]["cp_count"]), (2, 1))
        centre = Transformer.from_crs(25830, 4326, always_xy=True).transform(440750, 4479750)
        self.assertEqual(geographic_zone(*centre, {records[0]["zone_id"]}), records[0]["zone_id"])
        geometry = {"type": "Polygon", "coordinates": [records[0]["polygon"]]}
        for urban in [False, True]:
            deck = district_deck(geometry, records, urban)
            serialized = json.loads(deck.to_json())
            self.assertEqual(serialized["layers"][1]["id"], "district-zones")
            style = base64.b64decode(serialized["mapStyle"].split(",", 1)[1]).decode()
            self.assertEqual("tile.openstreetmap.org" in style, urban)
        self.assertEqual(zone_records(b.iloc[:0], p.iloc[:0]), [])

    def test_cell_callback_and_obsolete_district(self):
        from madrid_rehab.district_view import choose_zone, district_home

        state = {
            "city_active_district": "07",
            "city_selected_unit": "bu:old",
            "grid": {
                "selection": {"objects": {"district-zones": [{"zone_id": "E440500_N4479500"}]}}
            },
        }

        class State(dict):
            def __getattr__(self, key):
                return self[key]

            def __setattr__(self, key, value):
                self[key] = value

        state = State(state)
        with patch("madrid_rehab.district_view.st", SimpleNamespace(session_state=state)):
            choose_zone("grid", {"E440500_N4479500"}, "06")
            self.assertEqual(state.city_selected_unit, "bu:old")
            choose_zone("grid", {"E440500_N4479500"}, "07")
            self.assertEqual(state["city_zone_07"], "E440500_N4479500")
            self.assertIsNone(state.city_selected_unit)
            district_home("07")
            self.assertIsNone(state["city_zone_07"])

    def test_safe_export(self):
        output = csv_export(
            pd.DataFrame({"value": ["=1+1", "@SUM(A1)", "normal"], "amount": [1, 2, 3]})
        )
        text = output.decode("utf-8-sig") if isinstance(output, bytes) else output
        self.assertIn("'=1+1", text)
        self.assertIn("'@SUM(A1)", text)


@unittest.skipUnless((ROOT / "manifest.json").exists(), "Requiere sesión 7")
class NavigationAppTests(unittest.TestCase):
    def test_district_zone_return_and_filters(self):
        app = (
            AppTest.from_file("src/madrid_rehab/app.py", default_timeout=60)
            .run()
            .radio(key="city_navigation")
            .set_value("Madrid capital")
            .run()
        )
        totals = [m.value for m in app.metric]
        for code in ["07", "06", "19"]:
            app.selectbox(key="city_district").set_value(code).run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Elige una zona" in i.value for i in app.info))
            b = pd.read_parquet(ROOT / "districts" / code / "map_buildings.parquet")
            zone = b.map_zone.value_counts().index[0]
            app.selectbox(key="city_zone_" + code).set_value(zone).run()
            self.assertFalse(app.exception)
            # Búsqueda sin resultados y filtro avanzado vacío no conservan ficha.
            app.text_input(key="search_" + code).set_value("NO_EXISTE_OBJETO").run()
            self.assertTrue(any("Sin coincidencias" in i.value for i in app.info))
            app.selectbox(key="level_" + code).set_value("physical_status").run()
            app.selectbox(key="status_" + code).set_value("confirmed").run()
            app.checkbox(key="unlinked_" + code).uncheck().run()
            self.assertEqual(app.metric[0].value, "0")
            self.assertIsNone(app.session_state["city_selected_unit"])
            next(w for w in app.button if w.label == "Restablecer filtros").click().run()
            self.assertEqual(app.session_state["level_" + code], "parcel_status")
            next(w for w in app.button if w.label == "Ver distrito completo").click().run()
            self.assertIsNone(app.session_state["city_zone_" + code])
            next(w for w in app.button if w.label == "Volver a Madrid capital").click().run()
            self.assertEqual([m.value for m in app.metric], totals)
