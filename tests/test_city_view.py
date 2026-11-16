"""Lectura selectiva, navegación e integridad del visor municipal."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from navigation_support import technical_app

import test_sessions456 as fixtures
from madrid_rehab.city_maps import (
    cap_units,
    change_district,
    district_selection,
    unit_selection,
    MAX_MAP_UNITS,
)
from madrid_rehab.city_store import load_overview, signature, partition_manifest
from madrid_rehab.city_app import cached_overview
from madrid_rehab.district_view import cached_district, parcel_objects
from madrid_rehab.territory import event_territories

REAL = Path("data/processed/session_7_final")


class SelectionTests(unittest.TestCase):
    def test_identity_and_obsolete_events(self):
        self.assertEqual(
            district_selection({"selection": {"objects": {"layer": [{"district_code": "07"}]}}}),
            "07",
        )
        self.assertIsNone(
            district_selection({"selection": {"objects": {"layer": [{"district_code": "99"}]}}})
        )
        event = {"selection": {"objects": {"layer": [{"unit_id": "bu:one"}]}}}
        self.assertEqual(unit_selection(event, {"bu:one"}), "bu:one")
        self.assertIsNone(unit_selection(event, {"bu:other"}))
        self.assertIsNone(
            unit_selection({"selection": {"objects": {"layer": [{"unit_id": []}]}}}, set())
        )

    def test_changing_district_clears_selection(self):
        state = {"city_active_district": "07", "city_selected_unit": "bu:x", "city_map_epoch": 3}
        change_district(state, "08")
        self.assertIsNone(state["city_selected_unit"])
        self.assertEqual(state["city_map_epoch"], 4)
        state["city_selected_unit"] = "bu:new"
        change_district(state, "08")
        self.assertEqual(state["city_selected_unit"], "bu:new")
        change_district(state, "all")
        self.assertIsNone(state["city_selected_unit"])
        with self.assertRaises(ValueError):
            change_district(state, "../raw")

    def test_map_limit_and_selected_unit_preserved(self):
        b = pd.DataFrame({"building_id": [f"b{i:05d}" for i in range(3000)]})
        p = pd.DataFrame({"record_id": [f"p{i:05d}" for i in range(3000)]})
        shown_b, shown_p, truncated = cap_units(b, p, "cp:p02999")
        self.assertTrue(truncated)
        self.assertEqual(len(shown_b) + len(shown_p), MAX_MAP_UNITS)
        self.assertIn("p02999", shown_p.record_id.tolist())
        empty_b, empty_p, truncated = cap_units(b.iloc[:0], p.iloc[:0])
        self.assertTrue(empty_b.empty and empty_p.empty)
        self.assertFalse(truncated)

    def test_cp_filter_does_not_relabel_filtered_information_absent(self):
        p = pd.DataFrame({"record_id": ["p", "q"], "parcel_ref14": ["a", "b"]})
        c = pd.DataFrame({"record_id": ["c"], "parcel_status": ["confirmed"]})
        links = pd.DataFrame({"certificate_id": ["c"], "parcel_ref14": ["a"]})
        result = parcel_objects(p, c, links, c.iloc[:0], "parcel_status", True)
        self.assertEqual(result.parcel_ref14.tolist(), ["b"])
        self.assertEqual(result.certificate_count.sum(), 0)

    def test_future_event_territories_require_evidence(self):
        case = fixtures.AnalyticsTests()
        case.setUp()
        events = pd.DataFrame(
            {
                "parcel_ref14": [fixtures.RC, fixtures.RC, None, None],
                "match_status": ["confirmed", "candidate", "unmatched", "unmatched"],
                "match_level": ["parcel", "none", "none", "none"],
                "municipality_code": [None, None, "28079", "28079"],
                "district_code": [None, None, "08", None],
            }
        )
        result = event_territories(events, case.parcels)
        self.assertEqual(
            result.territory_level.tolist(), ["parcel", "unlocated", "district", "municipality"]
        )
        self.assertEqual(result.iloc[0].verified_district_code, "07")
        self.assertTrue(pd.isna(result.iloc[2].verified_district_code))


@unittest.skipUnless((REAL / "manifest.json").exists(), "Generar sesión 7 municipal")
class RealCityDataTests(unittest.TestCase):
    def test_overview_reads_no_detailed_geometry(self):
        with patch("madrid_rehab.city_store.pd.read_parquet", wraps=pd.read_parquet) as read:
            result = load_overview(REAL, signature(REAL))
            self.assertEqual(len(result["districts.parquet"]), 21)
            self.assertEqual(
                {Path(call.args[0]).name for call in read.call_args_list},
                {"districts.parquet", "district_summary.parquet"},
            )
        self.assertEqual(result["manifest"]["municipal"]["parcel_references"], 140595)

    def test_cold_warm_cache_no_reloads_and_copy_isolation(self):
        cached_overview.clear()
        with patch("madrid_rehab.city_store.pd.read_parquet", wraps=pd.read_parquet) as read:
            first = cached_overview(str(REAL), signature(REAL))
            first["district_summary.parquet"].loc[0, "parcels"] = -100
            other = cached_overview(str(REAL), signature(REAL))
            self.assertEqual(read.call_count, 2)
            self.assertGreater(other["district_summary.parquet"].iloc[0].parcels, 0)

    def test_district_loader_reads_only_chosen_partition(self):
        cached_district.clear()
        with patch("madrid_rehab.city_store.pd.read_parquet", wraps=pd.read_parquet) as read:
            result = cached_district(str(REAL), "07", signature(REAL, "07"))
            self.assertTrue(
                all(Path(call.args[0]).parent.name == "07" for call in read.call_args_list)
            )
            self.assertEqual(len(result["map_buildings.parquet"]), 3761)
            again = cached_district(str(REAL), "07", signature(REAL, "07"))
            self.assertEqual(read.call_count, 5)
            self.assertEqual(len(again["map_buildings.parquet"]), 3761)
        with self.assertRaises(ValueError):
            partition_manifest(REAL, "../raw")

    def test_chamberi_and_additive_reconciliation(self):
        overview = load_overview(REAL, signature(REAL))
        report = overview["reconciliation.json"]
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["chamberi_regression"]["status"], "passed")
        self.assertEqual(report["chamberi_regression"]["parcels"], 3790)
        self.assertEqual(report["chamberi_regression"]["unique_certificates"], 5105)
        self.assertEqual(
            overview["district_summary.parquet"].parcels.sum()
            + report["residual_parcel_references"],
            140595,
        )

    def test_tampered_overview_invalidates_signature_and_fails_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in [
                "manifest.json",
                "district_summary.parquet",
                "districts.parquet",
                "source_coverage.json",
                "reconciliation.json",
            ]:
                (root / name).write_bytes((REAL / name).read_bytes())
            old = signature(root)
            (root / "source_coverage.json").write_text('{"tampered":true}')
            self.assertNotEqual(old, signature(root))
            with self.assertRaises(ValueError):
                load_overview(root, signature(root))

    def test_tampered_district_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "districts" / "07").mkdir(parents=True)
            (root / "manifest.json").write_bytes((REAL / "manifest.json").read_bytes())
            (root / "districts" / "07" / "manifest.json").write_text("{}")
            with self.assertRaises(ValueError):
                partition_manifest(root, "07")


@unittest.skipUnless((REAL / "manifest.json").exists(), "Generar sesión 7 municipal")
class CityAppTests(unittest.TestCase):
    def app(self):
        return technical_app("Madrid capital", timeout=120)

    def test_default_21_districts_and_comparison_filters(self):
        app = self.app()
        self.assertFalse(app.exception)
        selector = next(w for w in app.selectbox if w.label == "Ámbito territorial")
        self.assertEqual(len(selector.options), 22)
        next(w for w in app.multiselect if w.label.startswith("Distritos a comparar")).set_value(
            ["07", "11"]
        ).run()
        table = next(d.value for d in app.dataframe if "district_code" in d.value)
        self.assertEqual(set(table.district_code), {"07", "11"})
        next(w for w in app.multiselect if w.label.startswith("Distritos a comparar")).set_value(
            []
        ).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("No hay distritos" in w.value for w in app.info))

    def test_switch_district_home_and_clear_selection(self):
        app = self.app()
        next(w for w in app.selectbox if w.label == "Ámbito territorial").set_value("07").run()
        self.assertFalse(app.exception)
        self.assertIn("Distrito 07 · Chamberí", [w.value for w in app.subheader])
        app.session_state["city_selected_unit"] = "bu:obsolete"
        next(w for w in app.selectbox if w.label == "Ámbito territorial").set_value("11").run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state["city_selected_unit"])
        self.assertIn("Distrito 11 · Carabanchel", [w.value for w in app.subheader])
        next(w for w in app.button if w.label == "Volver a Madrid capital").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["city_active_district"], "all")

    def test_positive_bu_and_parcel_detail_in_default_zone(self):
        app = self.app()
        next(w for w in app.selectbox if w.label == "Ámbito territorial").set_value("07").run()
        b = pd.read_parquet(REAL / "districts/07/map_buildings.parquet")
        p = pd.read_parquet(REAL / "districts/07/map_parcels.parquet")
        zone = b.map_zone.value_counts().index[0]
        chosen = b[b.map_zone.eq(zone) & b.current_use.eq("1_residential")].iloc[0]
        app.session_state["city_selected_unit"] = "bu:" + chosen.building_id
        app.run()
        self.assertFalse(app.exception)
        self.assertIn("Ficha del objeto catastral", [w.value for w in app.subheader])
        cp = p[p.parcel_ref14.eq(chosen.parcel_ref14) & p.map_zone.eq(zone)].iloc[0]
        app.session_state["city_selected_unit"] = "cp:" + cp.record_id
        app.run()
        self.assertFalse(app.exception)
        self.assertIn("Ficha de parcela catastral", [w.value for w in app.subheader])
        next(w for w in app.button if w.label == "Limpiar selección").click().run()
        self.assertIsNone(app.session_state["city_selected_unit"])

    def test_all_21_districts_render_real_partitions(self):
        app = self.app()
        for code in [f"{i:02d}" for i in range(1, 22)]:
            next(w for w in app.selectbox if w.label == "Ámbito territorial").set_value(code).run()
            self.assertFalse(app.exception, f"Distrito {code}: {[e.value for e in app.exception]}")
            self.assertTrue(any(w.value.startswith(f"Distrito {code} ·") for w in app.subheader))
            self.assertLessEqual(int(app.metric[2].value.replace(",", "")), MAX_MAP_UNITS)

    def test_district_filters_empty_and_csv_preserved(self):
        app = self.app()
        next(w for w in app.selectbox if w.label == "Ámbito territorial").set_value("07").run()
        next(w for w in app.selectbox if w.label == "Nivel de vinculación").set_value(
            "physical_status"
        ).run()
        next(w for w in app.selectbox if w.label == "Estado de vinculación").set_value(
            "confirmed"
        ).run()
        self.assertFalse(app.exception)
        next(
            w for w in app.checkbox if w.label == "Incluir unidades sin CEEE vinculados"
        ).uncheck().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0")
        next(w for w in app.multiselect if w.label == "Periodo constructivo").set_value([]).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.get("download_button"))


class MissingOverviewTests(unittest.TestCase):
    def test_missing_coverage_not_reported_as_zero(self):
        from madrid_rehab.city_maps import overview_records

        districts = pd.DataFrame(
            {
                "district_code": ["01"],
                "district_name": ["TEST"],
                "geometry_geojson": [
                    '{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}'
                ],
            }
        )
        summary = pd.DataFrame(
            {
                "district_code": ["01"],
                "parcels": [0],
                "bu_spatial": [0],
                "ceee_confirmed_records": [0],
                "observed_energy_coverage": [None],
            }
        )
        result = overview_records(districts, summary)
        self.assertEqual(result[0]["coverage_text"], "Desconocida")
        self.assertEqual(result[0]["color"], [145, 153, 165, 135])
