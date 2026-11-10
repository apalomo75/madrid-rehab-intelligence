"""Six-city catalogue threshold, privacy, exact search and map navigation regressions."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab import commercial_catalog as cc, commercial_catalog_store as store
from madrid_rehab import address_search as postal
from madrid_rehab.ingest import digest


class RuleTests(unittest.TestCase):
    def test_same_residential_object_two_positive_attributes(self):
        data = pd.DataFrame(
            [
                dict(
                    current_use="1_residential",
                    construction_oldest_year=1978,
                    recovered_official_area="5346",
                    dwellings_raw="14",
                ),
                dict(current_use="1_residential", construction_oldest_year=1978),
                dict(current_use="1_residential", recovered_official_area="200"),
                dict(
                    current_use="3_industrial",
                    construction_oldest_year=1978,
                    recovered_official_area="200",
                ),
                dict(
                    current_use="1_residential",
                    construction_oldest_year=999,
                    recovered_official_area="0",
                    dwellings_raw="0",
                ),
            ]
        )
        f = cc.construction_flags(data)
        self.assertEqual(f.construction.tolist(), [True, False, False, False, False])
        # Rows 1/2 are not combined into a qualifying residential object.

    def test_alternatives_levels_and_two_aids_not_two_families(self):
        data = (
            pd.DataFrame(
                [
                    dict(construction=True),
                    dict(energy=True),
                    dict(administrative=True),
                    dict(prtr=True),
                    dict(rehabilita=True),
                    dict(prtr=True, rehabilita=True),
                    dict(energy=True, administrative=True),
                    {},
                ]
            )
            .reindex(columns=cc.SOURCES)
            .astype("boolean")
            .fillna(False)
            .astype(bool)
        )
        visible, levels, reasons, families = cc.assign_levels(data, dict.fromkeys(cc.SOURCES, True))
        self.assertEqual(visible.tolist(), [True] * 7 + [False])
        self.assertEqual(levels.iloc[0], cc.DOCUMENTED)
        self.assertEqual(levels.iloc[5], cc.PARTIAL_LEVEL)
        self.assertEqual(families.iloc[5], 1)
        self.assertEqual(levels.iloc[6], cc.DOCUMENTED)
        public = cc.assign_levels(data, cc.PUBLIC_SOURCES)
        self.assertEqual(public[0].tolist(), visible.tolist())
        self.assertEqual(public[1].tolist(), levels.tolist())
        self.assertEqual(public[2].tolist(), reasons.tolist())


@unittest.skipUnless((cc.DEFAULT / "manifest.json").exists(), "Catalogue product absent")
class RealCatalogTests(unittest.TestCase):
    def test_integrity_six_cities_and_geometry_unchanged(self):
        meta = store.metadata()
        self.assertEqual(set(meta["municipalities"]), set(postal.NAMES))
        for name, expected in meta["outputs"].items():
            self.assertEqual(digest(cc.DEFAULT / name), expected)
        from madrid_rehab.cadastral_identity import resolve_object

        for code in postal.NAMES:
            frame = pd.read_parquet(cc.DEFAULT / (code + ".parquet"))
            self.assertTrue(frame.parcel_ref14.is_unique)
            sample = frame[frame.local_visible].iloc[0]
            _, cp = resolve_object(code, sample.parcel_ref14, "cp")
            self.assertEqual(cp.iloc[0].geometry_wkt, sample.geometry_wkt)
            self.assertEqual(frame.public_visible.tolist(), frame.local_visible.tolist())

    def test_real_inclusion_metrics_and_no_forced_ambiguity(self):
        d = json.loads(Path("reports/session_24_public_catalog_02/metrics.json").read_text())
        local = [r for r in d["parcels"] if r["mode"] == "local"]
        public = [r for r in d["parcels"] if r["mode"] == "public"]
        self.assertEqual(sum(r["included"] for r in local), 153929)
        self.assertEqual(sum(r["included"] for r in public), sum(r["included"] for r in local))
        self.assertEqual(sum(r["excluded"] for r in local), 40891)
        self.assertEqual(sum(r["denominator"] for r in local), 194820)
        madrid = next(r for r in local if r["municipality_code"] == "28079")
        self.assertEqual(madrid["sources"]["administrative"], 9036)
        self.assertEqual(madrid["sources"]["energy"], 51842)
        self.assertEqual(d["postal"][0]["versions_total"], 214083)

    def test_america_excluded_moncloa_included_and_technical_preserved(self):
        self.assertIsNone(store.parcel("28079", "8781605VK4788B"))
        row = store.parcel("28079", "9377401VK3797G")
        self.assertTrue(row["construction"])
        self.assertEqual(row["local_level"], cc.DOCUMENTED)
        from madrid_rehab.cadastral_identity import resolve_object

        self.assertFalse(resolve_object("28079", "8781605VK4788B", "cp")[1].empty)
        all_rows, total = postal.search("28079", "AVENIDA DE AMERICA", "113", "A")
        self.assertGreater(total, 0)
        rows, total, located = store.search("28079", "AVENIDA DE AMERICA", "113", "A")
        self.assertFalse(rows)
        self.assertEqual(total, 0)
        self.assertTrue(located)
        rows, total, located = store.search("28079", "AVENIDA DE LA MONCLOA", "14")
        self.assertTrue(located)
        self.assertGreater(total, 0)
        self.assertTrue(all(r["status"] == "confirmed" for r in rows))
        self.assertEqual(set(json.loads(rows[0]["refs"])), {"9377401VK3797G"})

    def test_confirmed_aids_only_ambiguity_never_counts(self):
        from madrid_rehab.data_recovery_audit import PARTIAL

        links = pd.read_parquet(PARTIAL / "grant_parcel_links.parquet")
        grants = pd.read_parquet(
            "data/processed/grants/session_11_final_03/grants.parquet",
            columns=["expediente_id", "identity_conflict", "territorial_quality"],
        )
        valid = set(
            grants.loc[
                ~grants.identity_conflict & ~grants.territorial_quality.eq("contradictory"),
                "expediente_id",
            ]
        )
        good = links[
            links.match_status.isin(
                ["confirmed", "confirmed_reference", "confirmed_historical_madrid"]
            )
            & links.expediente_id.isin(valid)
        ]
        self.assertTrue(links.match_status.astype(str).str.contains("ambiguous").any())
        for code in postal.NAMES:
            frame = pd.read_parquet(cc.DEFAULT / (code + ".parquet"))
            refs = set(good.loc[good.geographic_municipality_code.eq(code), "parcel_ref14"])
            self.assertEqual(
                set(frame.loc[frame.prtr, "parcel_ref14"]), refs & set(frame.parcel_ref14)
            )

    def test_commercial_postal_positive_and_no_duplicate_results(self):
        rows, total, located = store.search("28079", "CALLE BAILEN")
        self.assertTrue(located)
        self.assertEqual(len(rows), len({r["id"] for r in rows}))
        self.assertTrue(
            all(store.parcel("28079", ref) for r in rows for ref in json.loads(r["refs"]))
        )
        at = AppTest.from_string(
            "from madrid_rehab.address_view import render\nrender()\n", default_timeout=90
        ).run()
        at.text_input(key="postal_street").set_value("AVENIDA DE LA MONCLOA 14")
        next(b for b in at.button if b.label == "Buscar").click().run()
        choice = at.selectbox(key="postal_result_choice")
        uid = store.search("28079", "AVENIDA DE LA MONCLOA", "14")[0][0]["id"]
        choice.set_value(uid).run()
        next(b for b in at.button if b.label == "Abrir ficha del inmueble").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["fiche_identity"], ("28079", "cp", "9377401VK3797G"))
        next(b for b in at.button if b.label == "Volver a los resultados").click().run()
        self.assertEqual(at.selectbox(key="postal_result_choice").value, uid)

    def test_geometry_display_does_not_simplify_source(self):
        from madrid_rehab.regional_view import geometry_deck

        frame = pd.read_parquet(cc.DEFAULT / "28065.parquet")
        frame = frame[frame.local_visible].head(1).copy()
        frame["unit_id"] = frame.parcel_ref14
        frame["catalog_color"] = [[35, 130, 155, 130]]
        result = json.loads(geometry_deck(frame, "unit_id", 15, preserve_geometry=True).to_json())
        feature = result["layers"][0]["data"]["features"][0]
        self.assertEqual(feature["properties"]["unit_id"], frame.iloc[0].parcel_ref14)
        self.assertEqual(feature["properties"]["color"], [35, 130, 155, 130])
        import shapely as sh
        from shapely.ops import transform
        from pyproj import Transformer

        original = sh.from_wkt(frame.iloc[0].geometry_wkt)
        projected = transform(Transformer.from_crs(25830, 4326, always_xy=True).transform, original)
        self.assertTrue(sh.geometry.shape(feature["geometry"]).equals_exact(projected, 1e-12))

    def test_unknown_and_excluded_different_no_pilot_postal_invention(self):
        self.assertFalse(store.search("28079", "CALLE QUE NO EXISTE XYZ", "999")[2])
        for code in set(postal.NAMES) - {"28079"}:
            self.assertEqual(store.search(code, "CALLE A", "1"), ([], 0, False))

    def test_public_catalog_matches_local_membership(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            public_memberships = {}
            for code in postal.NAMES:
                public_memberships[code] = store.parcel_index(code).parcel_ref14.tolist()
                self.assertTrue(public_memberships[code])
            self.assertIsNotNone(store.parcel("28079", "9377401VK3797G"))
            self.assertEqual(store.search("28079", "AVENIDA DE LA MONCLOA", "14")[1], 1)
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}):
            for code, refs in public_memberships.items():
                self.assertEqual(store.parcel_index(code).parcel_ref14.tolist(), refs)

    def test_sources_masks_and_single_individual_certificate(self):
        for code in postal.NAMES:
            f = pd.read_parquet(cc.DEFAULT / (code + ".parquet"))
            self.assertTrue(
                (
                    f.local_visible
                    == (f.construction | f.energy | f.administrative | f.prtr | f.rehabilita)
                ).all()
            )
            self.assertTrue(
                f.loc[f.local_visible, "local_level"].isin([cc.DOCUMENTED, cc.PARTIAL_LEVEL]).all()
            )
            only = f[
                f.energy
                & ~f.construction
                & ~f.administrative
                & ~f.prtr
                & ~f.rehabilita
                & f.individual_certificates.eq(1)
                & f.whole_building_certificates.eq(0)
                & f.other_certificates.eq(0)
            ]
            if not only.empty:
                self.assertTrue(only.local_level.eq(cc.PARTIAL_LEVEL).all())
            self.assertTrue(f.loc[~f.local_visible, "local_level"].eq(cc.EXCLUDED).all())

    def test_excluded_search_never_opens_empty_fiche(self):
        at = AppTest.from_string(
            "from madrid_rehab.address_view import render\nrender()\n", default_timeout=90
        ).run()
        at.text_input(key="postal_street").set_value("AVENIDA DE AMERICA")
        at.text_input(key="postal_number").set_value("113")
        at.text_input(key="postal_complement").set_value("A")
        next(b for b in at.button if b.label == "Buscar").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any(store.INSUFFICIENT == i.value for i in at.info))
        self.assertFalse(any(b.label == "Abrir ficha del inmueble" for b in at.button))
        self.assertFalse(at.subheader)

    def test_map_six_cities_only_admitted_and_original_cp_bu_route(self):
        from madrid_rehab.municipal_navigation import zone_page, picked

        for code in postal.NAMES:
            index = store.parcel_index(code)
            self.assertFalse(index.empty)
            self.assertTrue(index.parcel_ref14.is_unique)
            zone = index.iloc[0].zone
            refs = zone_page(index, zone, 0)
            self.assertLessEqual(len(refs), 500)
            self.assertTrue(all(store.parcel(code, r) for r in refs[:2]))
            self.assertIsNone(
                picked({"selection": {"objects": {"x": [{"unit_id": "EXCLUDED"}]}}}, refs)
            )
        # Directly enter a documented pilot CP, then the existing technical navigation remains available.
        code = "28065"
        ref = store.parcel_index(code).loc[lambda f: f.construction.eq(1)].iloc[0].parcel_ref14
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            at = AppTest.from_string(
                "from madrid_rehab.municipal_navigation import render_explorer\n"
                f"render_explorer({code!r},'Getafe',{ref!r},commercial=True)\n",
                default_timeout=90,
            ).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["fiche_identity"], (code, "cp", ref))
        button = next(b for b in at.button if b.label == "Consultar construcción")
        selected = next(s for s in at.selectbox if s.label == "Construcción relacionada").value
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            button.click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["fiche_identity"], (code, "bu", selected))
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            next(
                b for b in at.button if b.label.startswith("Volver al objeto de origen")
            ).click().run()
        self.assertEqual(at.session_state["fiche_identity"], (code, "cp", ref))

    def test_public_map_uses_same_valid_catalogue_and_provides_attribution(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            at = AppTest.from_string(
                "from madrid_rehab.commercial_catalog_view import render\nrender()\n",
                default_timeout=90,
            ).run()
            self.assertFalse(at.exception)
            self.assertTrue(any("Catastro INSPIRE" in c.value for c in at.caption))
            self.assertEqual(len(store.parcel_index("28079")), 114706)
            with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}):
                local = store.parcel_index("28079").parcel_ref14.tolist()
            public = store.parcel_index("28079").parcel_ref14.tolist()
            self.assertEqual(public, local)

    def test_public_catalog_fiche_loads_attributed_evidence(self):
        from madrid_rehab.cadastral_identity import resolve_object
        from madrid_rehab.commercial_data import load_fiche

        objects = resolve_object("28079", "9377401VK3797G", "cp")[1]
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            model, tables, errors, _ = load_fiche(
                "28079",
                "Madrid",
                "9377401VK3797G",
                objects,
                public_catalog=True,
            )
        self.assertTrue(tables["energy"].shape[0] >= 1)
        self.assertTrue(any("Comunidad de Madrid" in item.source for item in model.energy))
        self.assertFalse(errors)


if __name__ == "__main__":
    unittest.main()
