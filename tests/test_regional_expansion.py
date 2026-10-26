"""Sesión 12: fixtures sintéticas explícitas; productos reales solo en RealSnapshots."""

import io
import os
import tempfile
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import shapely as sh
from pyproj import Transformer
from streamlit.testing.v1 import AppTest

from madrid_rehab.ingest import Archive, cadastral_rows, digest, save_json
from madrid_rehab.regional import load_official_boundaries
from madrid_rehab.regional_cadastre import (
    atom_resources,
    cp_bu_relations,
    fetch_retry,
    inventory,
    process_municipality,
    validate_crosswalk,
    validate_objects,
    verify_partition,
)
from madrid_rehab.regional_grants import regional_matches, run, territorial_links
from madrid_rehab.regional_territory import normalize_boundaries, validate_catalogue
from madrid_rehab.regional_view import municipality_changed, money, geometry_deck
from madrid_rehab.grants_view import readable, safe_export


REF = "1234567VK4712A"
X, Y = 440000, 4470000
BOX = sh.box(X, Y, X + 10, Y + 10)


def synthetic_grant(x=X + 5, y=Y + 5, **values):
    lon, lat = Transformer.from_crs(25830, 4326, always_xy=True).transform(x, y)
    return pd.DataFrame(
        [
            dict(
                expediente_id="SYNTHETIC",
                longitude=lon,
                latitude=lat,
                geometry_valid=True,
                direccion="CALLE TEST GETAFE (MADRID)",
                identity_conflict=False,
                **values,
            )
        ]
    )


def synthetic_regions():
    return pd.DataFrame(
        [
            dict(municipality_code="28065", name="Getafe", geometry_wkt=BOX.wkt),
            dict(
                municipality_code="28079",
                name="Madrid",
                geometry_wkt=sh.box(X + 10, Y, X + 20, Y + 10).wkt,
            ),
        ]
    )


def synthetic_previous(status="confirmed"):
    return pd.DataFrame(
        [dict(expediente_id="SYNTHETIC", parcel_ref14=REF, match_status=status, distance_m=0)]
    )


def synthetic_objects(kind="cp"):
    return pd.DataFrame(
        [
            {
                ("parcel_id" if kind == "cp" else "building_id"): "SYNTHETIC",
                "parcel_ref14": REF,
                "geometry_crs": "EPSG:25830",
                "geometry_wkt": BOX.wkt,
            }
        ]
    )


def synthetic_catalogue():
    return pd.DataFrame(
        [
            dict(
                municipality_code=f"28{i:03}",
                name=f"SYNTHETIC {i}",
                boundary_source_id=f"source-{i}",
            )
            for i in range(1, 180)
        ]
    )


class TerritoryTests(unittest.TestCase):
    def test_catalogue_179_unique_required(self):
        frame = synthetic_catalogue()
        self.assertEqual(len(validate_catalogue(frame)), 179)
        for bad in [frame.iloc[:-1], pd.concat([frame.iloc[:-1], frame.iloc[:1]])]:
            with self.assertRaises(ValueError):
                validate_catalogue(bad)

    def test_catalogue_empty_names_and_wrong_province(self):
        for field, value in [
            ("name", ""),
            ("municipality_code", "08001"),
            ("boundary_source_id", ""),
        ]:
            frame = synthetic_catalogue()
            frame.loc[0, field] = value
            with self.assertRaises(ValueError):
                validate_catalogue(frame)

    def test_boundary_original_geometry_and_crs(self):
        catalogue = synthetic_catalogue()
        features = [
            dict(
                type="Feature",
                properties={"source": r.boundary_source_id},
                geometry=sh.geometry.mapping(sh.box(X + i * 20, Y, X + i * 20 + 10, Y + 10)),
            )
            for i, r in enumerate(catalogue.itertuples())
        ]
        result = normalize_boundaries(
            dict(type="FeatureCollection", features=features), catalogue, "source", "EPSG:25830"
        )
        self.assertTrue(result.geometry_crs.eq("EPSG:25830").all())
        self.assertEqual(sh.from_wkt(result.geometry_wkt.iloc[0]).area, 100)
        with self.assertRaises(ValueError):
            normalize_boundaries(
                dict(type="FeatureCollection", features=features[:-1]),
                catalogue,
                "source",
                "EPSG:25830",
            )
        with self.assertRaises(ValueError):
            normalize_boundaries(
                dict(type="FeatureCollection", features=features), catalogue, "source", "EPSG:3857"
            )

    def test_pagination_rejected(self):
        with self.assertRaises(ValueError):
            normalize_boundaries(
                dict(type="FeatureCollection", links=[dict(rel="next")]),
                synthetic_catalogue(),
                "source",
                "EPSG:25830",
            )

    def test_unique_spatial_assignment(self):
        result = territorial_links(
            synthetic_grant(), synthetic_previous("regional_cp_pending"), synthetic_regions()
        )
        self.assertEqual(result.municipality_code.iloc[0], "28065")
        self.assertEqual(result.territorial_status.iloc[0], "spatial_unambiguous")

    def test_borderline_not_allocated(self):
        for x in [X + 10, X + 9.9]:
            result = territorial_links(
                synthetic_grant(x=x), synthetic_previous("regional_cp_pending"), synthetic_regions()
            )
            self.assertEqual(result.territorial_status.iloc[0], "borderline")
            self.assertIsNone(result.municipality_code.iloc[0])

    def test_cp_conflict_preserves_historical_evidence(self):
        result = territorial_links(synthetic_grant(), synthetic_previous(), synthetic_regions())
        self.assertEqual(result.territorial_status.iloc[0], "contradictory")
        self.assertEqual(result.cp_confirmed_municipality_code.iloc[0], "28079")
        self.assertIsNone(result.municipality_code.iloc[0])
        self.assertTrue(result.cp_spatial_conflict.iloc[0])

    def test_unknown_address_not_silently_contradiction(self):
        grants = synthetic_grant()
        grants["direccion"] = "UNRECOGNIZED VARIANT"
        self.assertEqual(
            territorial_links(
                grants, synthetic_previous("pending"), synthetic_regions()
            ).territorial_status.iloc[0],
            "spatial_unambiguous",
        )

    def test_explicit_address_contradiction(self):
        grants = synthetic_grant()
        grants["direccion"] = "CALLE TEST MADRID (MADRID)"
        result = territorial_links(grants, synthetic_previous("pending"), synthetic_regions())
        self.assertEqual(result.territorial_status.iloc[0], "contradictory")
        regions = pd.concat(
            [
                synthetic_regions(),
                pd.DataFrame(
                    [
                        dict(
                            municipality_code="28127",
                            name="Las Rozas de Madrid",
                            geometry_wkt=sh.box(X + 30, Y, X + 40, Y + 10).wkt,
                        )
                    ]
                ),
            ],
            ignore_index=True,
        )
        grants = synthetic_grant(x=X + 15)
        grants["direccion"] = "CALLE TEST LAS ROZAS DE MADRID (MADRID)"
        result = territorial_links(grants, synthetic_previous("pending"), regions)
        self.assertEqual(result.territorial_status.iloc[0], "contradictory")

    def test_invalid_and_outside(self):
        grants = synthetic_grant()
        grants["geometry_valid"] = False
        self.assertEqual(
            territorial_links(
                grants, synthetic_previous("pending"), synthetic_regions()
            ).territorial_status.iloc[0],
            "invalid_or_missing_geometry",
        )
        grants = synthetic_grant(x=X - 100)
        self.assertEqual(
            territorial_links(
                grants, synthetic_previous("pending"), synthetic_regions()
            ).territorial_status.iloc[0],
            "outside_region",
        )

    def test_boundaries_unavailable_not_outside_region(self):
        result = territorial_links(synthetic_grant(), synthetic_previous())
        self.assertEqual(result.territorial_status.iloc[0], "boundaries_unavailable")
        self.assertEqual(result.municipality_code.iloc[0], "28079")

    def test_municipal_validation_overlap_and_envelope(self):
        frame = synthetic_catalogue().drop(columns="boundary_source_id")
        frame["geometry_crs"] = "EPSG:25830"
        frame["geometry_wkt"] = [
            sh.box(X + i * 20, Y, X + i * 20 + 10, Y + 10).wkt for i in range(179)
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "frame.parquet"
            meta = Path(temp) / "manifest.json"

            def write():
                frame.to_parquet(path, index=False)
                save_json(
                    meta,
                    dict(
                        source_url="https://www.ign.es",
                        publisher="SYNTHETIC",
                        license="SYNTHETIC",
                        source_date="2026-01-01",
                        sha256=digest(path),
                    ),
                )

            write()
            self.assertEqual(len(load_official_boundaries(path, meta)), 179)
            frame.loc[1, "geometry_wkt"] = frame.geometry_wkt.iloc[0]
            write()
            with self.assertRaises(ValueError):
                load_official_boundaries(path, meta)
            frame.loc[1, "geometry_wkt"] = sh.box(0, 0, 1, 1).wkt
            write()
            with self.assertRaises(ValueError):
                load_official_boundaries(path, meta)


class CadastreTests(unittest.TestCase):
    def test_crosswalk_not_identity_assumed(self):
        resources = pd.DataFrame([dict(cadastre_code="28900")])
        frame = pd.DataFrame(
            [
                dict(
                    municipality_code="28079",
                    cadastre_code="28900",
                    name="Madrid",
                    evidence_url="reviewed",
                )
            ]
        )
        self.assertEqual(validate_crosswalk(frame, resources).municipality_code.iloc[0], "28079")
        with self.assertRaises(ValueError):
            validate_crosswalk(frame.drop(columns="evidence_url"), resources)
        with self.assertRaises(ValueError):
            validate_crosswalk(pd.concat([frame, frame]), resources)

    def test_http_retry_bounded(self):
        archive = Mock()
        archive.fetch.side_effect = urllib.error.URLError("synthetic DNS")
        with (
            patch("madrid_rehab.regional_cadastre.time.sleep"),
            self.assertRaises(urllib.error.URLError),
        ):
            fetch_retry(archive, "https://www.catastro.hacienda.gob.es/x", "x", 2)
        self.assertEqual(archive.fetch.call_count, 2)

    def test_http_404_no_retry(self):
        archive = Mock()
        archive.fetch.side_effect = urllib.error.HTTPError("test", 404, "missing", {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            fetch_retry(archive, "https://www.catastro.hacienda.gob.es/x", "x", 3)
        self.assertEqual(archive.fetch.call_count, 1)

    def test_space_in_feed_url_encoded(self):
        archive = Mock()
        fetch_retry(archive, "https://www.catastro.hacienda.gob.es/ALCALA DE HENARES/x", "x")
        self.assertIn("ALCALA%20DE%20HENARES", archive.fetch.call_args.args[0])

    def test_bad_retry_limit(self):
        with self.assertRaises(ValueError):
            fetch_retry(Mock(), "x", "x", 4)

    def test_cp_bu_geometry_relationship(self):
        result = cp_bu_relations(synthetic_objects(), synthetic_objects("bu"))
        self.assertEqual(result.relation_quality.iloc[0], "confirmed_reference_geometry")
        bu = synthetic_objects("bu")
        bu["geometry_wkt"] = sh.box(X + 200, Y, X + 210, Y + 10).wkt
        self.assertEqual(
            cp_bu_relations(synthetic_objects(), bu).relation_quality.iloc[0],
            "contradictory_geometry",
        )

    def test_cp_bu_ambiguous_and_missing(self):
        cp = synthetic_objects()
        bu = synthetic_objects("bu")
        self.assertEqual(
            cp_bu_relations(pd.concat([cp, cp]), bu).relation_quality.iloc[0], "ambiguous_reference"
        )
        bu["parcel_ref14"] = "MISSING"
        self.assertEqual(cp_bu_relations(cp, bu).relation_quality.iloc[0], "not_found")

    def test_invalid_crs_id_and_boundary(self):
        for field, value in [
            ("geometry_crs", "EPSG:4326"),
            ("parcel_id", None),
            ("geometry_wkt", "POLYGON EMPTY"),
        ]:
            frame = synthetic_objects()
            frame[field] = value
            with self.assertRaises(ValueError):
                validate_objects(frame, "cp", BOX)
        with self.assertRaises(ValueError):
            validate_objects(synthetic_objects(), "cp", sh.box(X + 100, Y, X + 110, Y + 10))

    def test_corrupt_zip_missing_and_wrong_members(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "x.zip"
            p.write_bytes(b"invalid")
            with self.assertRaises(zipfile.BadZipFile):
                list(cadastral_rows(p, "parcelas"))
            with self.assertRaises(FileNotFoundError):
                list(cadastral_rows(Path(temp) / "absent.zip", "edificios"))
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("x.txt", "test")
            with self.assertRaises(ValueError):
                list(cadastral_rows(p, "edificios"))

    def test_incomplete_collection_rejected_for_new_pipeline(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cp.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "test.cadastralparcel.gml", '<FeatureCollection numberReturned="1"/>'
                )
            with self.assertRaises(ValueError):
                list(cadastral_rows(path, "parcelas", strict_count=True))

    def test_regional_matching_covered_missing_ambiguous_and_contradictory(self):
        previous = synthetic_previous("regional_cp_pending")
        territory = territorial_links(synthetic_grant(), previous, synthetic_regions())
        references = previous[["expediente_id", "parcel_ref14"]]
        cp = synthetic_objects()
        with (
            patch(
                "madrid_rehab.regional_cadastre.verify_partition",
                return_value={"config": {"municipality_code": "28065"}},
            ),
            patch("madrid_rehab.regional_grants.pd.read_parquet", return_value=cp),
        ):
            result = regional_matches(
                synthetic_grant(), references, territory, {"28065": "SYNTHETIC"}, previous
            )
        self.assertEqual(result.match_status.iloc[0], "confirmed")
        for candidate, expected in [
            (cp.assign(parcel_ref14="MISSING"), "not_found"),
            (pd.concat([cp, cp]), "ambiguous"),
            (cp.assign(geometry_wkt=sh.box(X + 200, Y, X + 210, Y + 10).wkt), "contradictory"),
        ]:
            with (
                patch(
                    "madrid_rehab.regional_cadastre.verify_partition",
                    return_value={"config": {"municipality_code": "28065"}},
                ),
                patch("madrid_rehab.regional_grants.pd.read_parquet", return_value=candidate),
            ):
                result = regional_matches(
                    synthetic_grant(), references, territory, {"28065": "SYNTHETIC"}, previous
                )
            self.assertEqual(result.match_status.iloc[0], expected)
        territory["municipality_code"] = "28079"
        with patch(
            "madrid_rehab.regional_grants.pd.read_parquet",
            return_value=cp.assign(parcel_ref14="MISSING"),
        ):
            result = regional_matches(
                synthetic_grant(),
                references,
                territory,
                {},
                previous,
                madrid_cp_path="SYNTHETIC_MADRID",
            )
        self.assertEqual(result.match_status.iloc[0], "not_found")

    def test_processed_municipality_apptest_and_selective_map(self):
        from madrid_rehab.regional_view import map_parcels, token

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            original = base / "original"
            original.write_bytes(b"SYNTHETIC")
            config = dict(
                municipality_code="28065",
                cadastre_code="28065",
                url_cp="https://www.catastro.hacienda.gob.es/cp",
                url_bu="https://www.catastro.hacienda.gob.es/bu",
            )
            with (
                patch(
                    "madrid_rehab.regional_cadastre.fetch_retry",
                    return_value=(original, dict(sha256=digest(original))),
                ),
                patch(
                    "madrid_rehab.regional_cadastre.cadastral_rows",
                    side_effect=[
                        synthetic_objects().to_dict("records"),
                        synthetic_objects("bu").to_dict("records"),
                    ],
                ),
            ):
                process_municipality(config, base / "raw", base / "out", BOX)
            partition = base / "out" / "28065"
            frame, truncated = map_parcels(str(partition), token(partition), X + 5, Y + 5, 17)
            self.assertEqual(len(frame), 1)
            self.assertFalse(truncated)
            frame, _ = map_parcels(str(partition), token(partition), X + 10000, Y + 10000, 17)
            self.assertTrue(frame.empty)
            path = base / "app.py"
            path.write_text(
                "from madrid_rehab.regional_view import render_municipality\nrender_municipality('28065','SYNTHETIC GETAFE')"
            )
            with patch.dict(os.environ, {"MADRID_REHAB_CADASTRE_DIR": str(base / "out")}):
                app = AppTest.from_file(str(path), default_timeout=30).run()
                self.assertFalse(app.exception)
                next(x for x in app.radio if x.label == "Objetos catastrales").set_value(
                    "Objetos BU independientes"
                ).run()
                self.assertFalse(app.exception)

    def test_cached_download_cp_bu_no_network(self):
        class Response(io.BytesIO):
            headers = {"Content-Length": "4"}

            def geturl(self):
                return "https://www.catastro.hacienda.gob.es/x"

        with tempfile.TemporaryDirectory() as temp:
            for kind in ["cp", "bu"]:
                archive = Archive(Path(temp) / kind)
                with patch("urllib.request.urlopen", return_value=Response(b"test")) as network:
                    path, _ = fetch_retry(
                        archive, "https://www.catastro.hacienda.gob.es/x", kind + ".zip"
                    )
                    fetch_retry(archive, "https://www.catastro.hacienda.gob.es/x", kind + ".zip")
                    self.assertEqual(network.call_count, 1)
                path.write_bytes(b"corrupt")
                with self.assertRaises(ValueError):
                    fetch_retry(archive, "https://www.catastro.hacienda.gob.es/x", kind + ".zip")
            orphan = Path(temp) / "orphan.zip"
            orphan.write_bytes(b"SYNTHETIC ORIGINAL WITHOUT METADATA")
            with (
                self.assertRaises(ValueError),
                patch(
                    "urllib.request.urlopen", side_effect=AssertionError("must preserve original")
                ),
            ):
                fetch_retry(Archive(temp), "https://www.catastro.hacienda.gob.es/x", "orphan.zip")
            self.assertEqual(orphan.read_bytes(), b"SYNTHETIC ORIGINAL WITHOUT METADATA")

    def test_process_checkpoint_and_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            raw = temp / "raw"
            output = temp / "out"
            original = temp / "original.zip"
            original.write_bytes(b"SYNTHETIC")
            config = dict(
                municipality_code="28065",
                cadastre_code="28065",
                url_cp="https://www.catastro.hacienda.gob.es/cp",
                url_bu="https://www.catastro.hacienda.gob.es/bu",
            )
            with (
                patch(
                    "madrid_rehab.regional_cadastre.fetch_retry",
                    return_value=(original, dict(sha256=digest(original))),
                ),
                patch(
                    "madrid_rehab.regional_cadastre.cadastral_rows",
                    side_effect=[
                        synthetic_objects().to_dict("records"),
                        synthetic_objects("bu").to_dict("records"),
                    ],
                ),
            ):
                first = process_municipality(config, raw, output, BOX)
            with patch("urllib.request.urlopen", side_effect=AssertionError("no network")):
                second = process_municipality(config, raw, output, BOX, offline=True)
            self.assertEqual(first, second)
            self.assertEqual(verify_partition(output / "28065")["cp_rows"], 1)
            (output / "28065" / "cp.parquet").write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                process_municipality(config, raw, output, BOX)

    def test_matching_missing_cp_and_historical_ambiguity(self):
        previous = synthetic_previous("ambiguous_cp")
        territory = territorial_links(synthetic_grant(), previous)
        result = regional_matches(
            synthetic_grant(), previous[["expediente_id", "parcel_ref14"]], territory, {}, previous
        )
        self.assertEqual(result.match_status.iloc[0], "ambiguous_historical_madrid")
        previous = synthetic_previous("regional_cp_pending")
        result = regional_matches(
            synthetic_grant(), previous[["expediente_id", "parcel_ref14"]], territory, {}, previous
        )
        self.assertEqual(result.match_status.iloc[0], "no_cp_coverage")


class RegionalViewTests(unittest.TestCase):
    def test_change_municipality_clears_parcel(self):
        state = {
            "regional_parcel": REF,
            "regional-map": {},
            "regional_previous_municipality": "28065",
            "city_district": "07",
        }
        municipality_changed(state, "28092")
        self.assertNotIn("regional_parcel", state)
        self.assertEqual(state["city_district"], "07")

    def test_money_and_labels(self):
        self.assertEqual(money(315527338.99), "315.527.338,99")
        frame = readable(
            pd.DataFrame(
                [
                    dict(
                        expediente_id="SYNTHETIC",
                        district_code="07",
                        importe_concedido=1000.5,
                        territorial_quality="madrid_confirmed",
                    )
                ]
            )
        )
        self.assertEqual(frame["Ayuda concedida (€)"].iloc[0], "1.000,50")
        self.assertEqual(frame["Calidad territorial"].iloc[0], "Vinculación confirmada en Madrid")

    def test_map_no_mutation(self):
        frame = synthetic_regions()
        before = frame.copy(deep=True)
        deck = geometry_deck(frame, "municipality_code")
        self.assertIn("GeoJsonLayer", deck.to_json())
        pd.testing.assert_frame_equal(frame, before)

    def test_safe_export_excludes_new_sensitive_fields(self):
        data = safe_export(
            pd.DataFrame(
                [
                    dict(
                        expediente_id="=SYNTHETIC",
                        direccion="PRIVATE",
                        raw_json="SECRET",
                        spatial_candidates="HIDDEN",
                    )
                ]
            )
        )
        data = data.decode("utf-8-sig") if isinstance(data, bytes) else data
        for text in ["PRIVATE", "SECRET", "HIDDEN"]:
            self.assertNotIn(text, data)
        self.assertIn("'=SYNTHETIC", data)


class RealSnapshots(unittest.TestCase):
    def test_real_official_atom_179_resources_not_ine(self):
        frame = inventory()
        self.assertEqual(len(frame), 179)
        self.assertTrue(frame.cadastre_code.is_unique)
        self.assertIn("28900", set(frame.cadastre_code))
        self.assertNotIn("municipality_code", frame)
        self.assertTrue(frame.url_cp.str.startswith("https://www.catastro.hacienda.gob.es/").all())

    def test_tampered_feed_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "atom.xml"
            path.write_bytes(b"corrupt")
            save_json(path.with_suffix(".xml.json"), dict(sha256="invalid"))
            with self.assertRaises(ValueError):
                atom_resources(path)

    def test_real_grants_reconciled_and_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "first"
            again = Path(temp) / "replay"
            a = run(out)
            b = run(again)
            self.assertEqual(a["grants"], 7532)
            self.assertEqual(a["amount_cents"], 31552733899)
            self.assertEqual(a["assigned"], 3805)
            self.assertEqual(a["matching"]["confirmed_historical_madrid"], 3809)
            self.assertEqual(a["matching"]["ambiguous_historical_madrid"], 3)
            self.assertEqual(a["outputs"], b["outputs"])
            with self.assertRaises(FileExistsError):
                run(out)

    def test_app_179_selection_no_fictitious_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "app.py"
            path.write_text(
                "from madrid_rehab.regional_view import render_regional\nrender_regional()"
            )
            # Conservar la regresión de navegación del snapshot histórico sin límites.
            with patch.dict(
                os.environ,
                {
                    "MADRID_REHAB_TERRITORY_DIR": str(Path(temp) / "no_boundaries"),
                    "MADRID_REHAB_REGIONAL_GRANTS_DIR": "data/processed/grants/regional/session_12_final_01",
                },
            ):
                app = AppTest.from_file(str(path), default_timeout=30).run()
                self.assertFalse(app.exception)
                self.assertEqual(len(app.selectbox[0].options), 6)
                app.selectbox[0].set_value("28065").run()
                self.assertFalse(app.exception)
                self.assertTrue(any(x.label == "Zona de exploración" for x in app.selectbox))
                app.selectbox[0].set_value("28079").run()
                self.assertFalse(app.exception)

    def test_app_filters_and_public_no_prtr(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "app.py"
            path.write_text(
                "from madrid_rehab.regional_view import render_regional\nrender_regional()"
            )
            app = AppTest.from_file(str(path), default_timeout=30).run()
            app.multiselect[0].set_value([]).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[-2].value, "0 / 7532")
            with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
                app = AppTest.from_file(str(path), default_timeout=30).run()
                self.assertFalse(app.exception)
                self.assertEqual(len(app.get("download_button")), 0)
                self.assertEqual(len(app.multiselect), 0)


if __name__ == "__main__":
    unittest.main()
