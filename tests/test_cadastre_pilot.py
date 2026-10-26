"""Piloto 12.2: fixtures sintéticas para fallos; datos reales ausentes se omiten explícitamente."""

import io
import json
import os
import socket
import tempfile
import unittest
import urllib.error
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import shapely as sh
from pyproj import Transformer
from streamlit.testing.v1 import AppTest

from madrid_rehab.cadastre_download import (
    MANIFEST,
    RAW,
    download,
    fetch,
    inspect_zip,
    load_manifest,
    sha256,
)
from madrid_rehab.cadastre_pilot import integrate
from madrid_rehab.ingest import digest
from madrid_rehab.pilot_grants import match_municipality
from madrid_rehab.pilot_objects import audit_objects, building_rows, audited_cp_bu_relations
from madrid_rehab.regional_cadastre import process_municipality, verify_partition
from madrid_rehab.regional_view import map_parcels, parcel_index, token
from madrid_rehab.territorial_prtr import DEFAULT as TERRITORY
from test_regional_expansion import BOX, X, Y, REF, synthetic_objects, synthetic_grant

REGIONAL = Path("data/processed/grants/regional/session_12_2_pilot_02")


def geometry():
    return f'<geometry><Polygon xmlns="http://www.opengis.net/gml/3.2" srsName="urn:ogc:def:crs:EPSG::25830"><exterior><LinearRing><posList>{X} {Y} {X + 10} {Y} {X + 10} {Y + 10} {X} {Y + 10} {X} {Y}</posList></LinearRing></exterior></Polygon></geometry>'


def xml(kind, part=False):
    obj = (
        f'<CadastralParcel g:id="CP1"><nationalCadastralReference>{REF}</nationalCadastralReference>{geometry()}</CadastralParcel>'
        if kind == "cp"
        else f'<Building g:id="BU1"><externalReference><reference>{REF}</reference></externalReference>{geometry()}'
        + (f'<parts><BuildingPart g:id="PART1">{geometry()}</BuildingPart></parts>' if part else "")
        + "</Building>"
    )
    return f'<FeatureCollection xmlns:g="http://www.opengis.net/gml/3.2" numberReturned="1"><member>{obj}</member></FeatureCollection>'.encode()


def package(kind="cp", body=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr(
            "SYNTHETIC." + ("cadastralparcel.gml" if kind == "cp" else "building.gml"),
            body if body is not None else xml(kind),
        )
    return stream.getvalue()


class Response(io.BytesIO):
    status = 200

    def __init__(self, data, **headers):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data)), **headers}

    def geturl(self):
        return "https://www.catastro.hacienda.gob.es/INSPIRE/test.zip"


class ResourceTests(unittest.TestCase):
    def test_ten_official_resources_and_reviewed_identity(self):
        plan = load_manifest(MANIFEST)
        self.assertEqual(len(plan["resources"]), 10)
        for r in plan["resources"]:
            self.assertIn(
                r["name"], ["Getafe", "Móstoles", "Leganés", "Alcorcón", "Alcalá de Henares"]
            )
            self.assertTrue(r["entry_title"].startswith(r["cadastre_code"] + "-"))
            self.assertEqual(r["entry_id"], r["url"])
            self.assertIn("D. G. of the Cadastre", r["rights"])
            self.assertIsNone(r["expected_bytes"])
            self.assertTrue(r["official_source_fids"])
        self.assertEqual(
            {r["municipality_code"] for r in plan["resources"]},
            {"28065", "28092", "28074", "28007", "28005"},
        )

    def test_zip_xml_integrity_rejects_html_truncated_and_wrong_layer(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "cp.zip"
            for data in [
                b"<html>error</html>",
                package(body=b"<FeatureCollection>"),
                package("bu"),
                package(body=b"<html>error</html>"),
                package(body=b'<!DOCTYPE a [<!ENTITY b "x">]><FeatureCollection/>'),
            ]:
                p.write_bytes(data)
                with self.assertRaises((ValueError, zipfile.BadZipFile, ET.ParseError)):
                    inspect_zip(p, "cp")
            p.write_bytes(package())
            self.assertEqual(inspect_zip(p, "cp")["zip_integrity"], "verified")

    def test_download_cache_and_orphan_preservation(self):
        r = load_manifest(MANIFEST)["resources"][0]
        with (
            tempfile.TemporaryDirectory() as temp,
            patch("madrid_rehab.cadastre_download.urllib.request.build_opener") as opener,
        ):
            opener.return_value.open.return_value = Response(package())
            first = fetch(r, temp)
            second = fetch(r, temp)
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(second["status"], "verified_cached")
            self.assertEqual(opener.return_value.open.call_count, 1)
            path = Path(first["path"])
            path.write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                fetch(r, temp)
            path.unlink()
            with self.assertRaises(ValueError):
                fetch(r, temp)

    def test_limited_progressive_retry_and_dns_single_attempt(self):
        r = load_manifest(MANIFEST)["resources"][0]
        with (
            tempfile.TemporaryDirectory() as temp,
            patch("madrid_rehab.cadastre_download.urllib.request.build_opener") as opener,
            patch("madrid_rehab.cadastre_download.time.sleep") as sleep,
        ):
            opener.return_value.open.side_effect = [
                urllib.error.URLError("transient"),
                Response(package()),
            ]
            self.assertEqual(fetch(r, temp)["status"], "verified_downloaded")
            sleep.assert_called_once_with(1)
        with (
            tempfile.TemporaryDirectory() as temp,
            patch("madrid_rehab.cadastre_download.urllib.request.build_opener") as opener,
        ):
            opener.return_value.open.side_effect = urllib.error.URLError(
                socket.gaierror(-3, "DNS fixture")
            )
            self.assertEqual(fetch(r, temp)["attempts"], 1)
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_html_and_truncated_download_never_promoted(self):
        r = load_manifest(MANIFEST)["resources"][0]
        for response in [
            Response(b"<html/>", **{"Content-Type": "text/html"}),
            Response(package(), **{"Content-Length": "999999"}),
        ]:
            with (
                tempfile.TemporaryDirectory() as temp,
                patch("madrid_rehab.cadastre_download.urllib.request.build_opener") as opener,
            ):
                opener.return_value.open.return_value = response
                with self.assertRaises(ValueError):
                    fetch(r, temp)
                self.assertEqual(list(Path(temp).rglob("*.zip")), [])
                self.assertEqual(list(Path(temp).rglob("*.part")), [])

    def test_interrupted_partial_preserved_not_reused(self):
        r = load_manifest(MANIFEST)["resources"][0]
        with (
            tempfile.TemporaryDirectory() as temp,
            patch("madrid_rehab.cadastre_download.urllib.request.build_opener") as opener,
        ):
            d = Path(temp) / r["cadastre_code"]
            d.mkdir()
            (d / "cp.zip.part").write_bytes(b"partial")
            opener.return_value.open.return_value = Response(package())
            self.assertEqual(fetch(r, temp)["status"], "verified_downloaded")
            self.assertEqual(next(d.glob("*.interrupted-*")).read_bytes(), b"partial")

    def test_offline_ten_resources_missing_not_claimed_downloaded(self):
        with tempfile.TemporaryDirectory() as temp:
            results, _ = download(
                root=Path(temp) / "raw", report=Path(temp) / "report", offline=True
            )
            self.assertEqual(len(results), 10)
            self.assertTrue(all(r["status"] == "missing" for r in results))
            from madrid_rehab.cadastre_download import official_url

            for result in results:
                self.assertEqual(result["request_url"], official_url(result["url"]))

    def test_real_ten_resources_integrity(self):
        paths = [
            (RAW / r["cadastre_code"] / (r["kind"] + ".zip"), r)
            for r in load_manifest(MANIFEST)["resources"]
        ]
        if not all(p.exists() for p, r in paths):
            self.skipTest(
                "DNS blocked: real ten-resource validation pending Ubuntu capture; synthetic tests do not replace it"
            )
        for path, r in paths:
            with self.subTest(name=r["name"], kind=r["kind"]):
                meta = json.loads(path.with_suffix(".zip.json").read_text())
                self.assertEqual(digest(path), meta["sha256"])
                inspect_zip(path, r["kind"])


class ObjectTests(unittest.TestCase):
    def test_parse_building_and_nested_part_identity_and_missing_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "bu.zip"
            p.write_bytes(package("bu", xml("bu", part=True)))
            rows = list(building_rows(p))
            self.assertEqual([r["source_feature_type"] for r in rows], ["Building", "BuildingPart"])
            self.assertEqual(rows[1]["parent_building_id"], "BU1")
            self.assertIsNone(rows[1]["parcel_ref14"])
            self.assertEqual(rows[0]["parcel_ref14"], REF)

    def test_invalid_duplicate_cross_boundary_retained(self):
        frame = synthetic_objects()
        frame = pd.concat([frame, frame], ignore_index=True)
        frame.loc[1, "geometry_wkt"] = "INVALID"
        result, issues = audit_objects(frame, "cp", BOX)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(issues), 2)
        self.assertFalse(result.usable_geometry.any())
        result, issues = audit_objects(synthetic_objects(), "cp", sh.box(X + 1, Y, X + 10, Y + 10))
        self.assertEqual(result.boundary_status.iloc[0], "crosses_boundary")
        self.assertFalse(result.usable_geometry.iloc[0])

    def test_multipart_geometry_not_duplicated(self):
        frame = synthetic_objects()
        frame["geometry_wkt"] = sh.MultiPolygon(
            [sh.box(X, Y, X + 2, Y + 2), sh.box(X + 3, Y, X + 4, Y + 1)]
        ).wkt
        result, issues = audit_objects(frame, "cp", BOX)
        self.assertEqual(len(result), 1)
        self.assertTrue(result.usable_geometry.iloc[0])
        self.assertTrue(issues.empty)

    def test_cp_bu_reference_geometry_and_missing_reference_separate(self):
        cp, _ = audit_objects(synthetic_objects(), "cp", BOX)
        bu, _ = audit_objects(synthetic_objects("bu"), "bu", BOX)
        self.assertEqual(
            audited_cp_bu_relations(cp, bu).relation_quality.iloc[0], "confirmed_reference_geometry"
        )
        bu["parcel_ref14"] = None
        self.assertEqual(
            audited_cp_bu_relations(cp, bu).relation_quality.iloc[0], "missing_reference"
        )

    def test_unusable_duplicate_cp_does_not_launder_ambiguity(self):
        cp, _ = audit_objects(synthetic_objects(), "cp", BOX)
        other = cp.copy()
        other["usable_geometry"] = False
        other["geometry_wkt"] = "INVALID"
        bu, _ = audit_objects(synthetic_objects("bu"), "bu", BOX)
        result = audited_cp_bu_relations(pd.concat([cp, other]), bu)
        self.assertEqual(result.relation_quality.iloc[0], "ambiguous_reference")

    def test_ingestion_replay_and_selective_map(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = root / "raw"
            config = dict(
                municipality_code="28065",
                cadastre_code="28065",
                url_cp="https://www.catastro.hacienda.gob.es/INSPIRE/cp.zip",
                url_bu="https://www.catastro.hacienda.gob.es/INSPIRE/bu.zip",
            )
            from madrid_rehab.cadastre_download import write_json

            for kind in ["cp", "bu"]:
                d = raw / "28065"
                d.mkdir(parents=True, exist_ok=True)
                p = d / (kind + ".zip")
                p.write_bytes(package(kind, xml(kind, part=kind == "bu")))
                write_json(
                    p.with_suffix(".zip.json"),
                    dict(url=config["url_" + kind], sha256=sha256(p), bytes=p.stat().st_size),
                )
            a = process_municipality(config, raw, root / "out", BOX, offline=True, audited=True)
            b = process_municipality(config, raw, root / "replay", BOX, offline=True, audited=True)
            self.assertEqual(a["outputs"], b["outputs"])
            self.assertEqual(a["bu_objects"], 2)
            self.assertEqual(a["cp_bu_quality"]["missing_reference"], 1)
            part = root / "out" / "28065"
            verify_partition(part)
            self.assertEqual(len(parcel_index(str(part), token(part))), 1)
            mapped, truncated = map_parcels(str(part), token(part), X + 5, Y + 5, 17)
            self.assertEqual(len(mapped), 1)
            self.assertFalse(truncated)
            far, _ = map_parcels(str(part), token(part), X + 50000, Y + 50000, 17)
            self.assertTrue(far.empty)
            with patch.dict(
                os.environ,
                {"MADRID_REHAB_CADASTRE_DIR": str(root / "out"), "MADRID_REHAB_PUBLIC": "1"},
            ):
                path = root / "app.py"
                path.write_text(
                    "from madrid_rehab.regional_view import render_municipality\nrender_municipality('28065','Getafe')"
                )
                app = AppTest.from_file(str(path), default_timeout=30).run()
                self.assertFalse(app.exception)
                next(x for x in app.radio if x.label == "Objetos catastrales").set_value(
                    "Objetos BU independientes"
                ).run()
                self.assertFalse(app.exception)
                self.assertEqual(len(app.get("download_button")), 0)


class MatchTests(unittest.TestCase):
    def setup_data(self):
        cp, _ = audit_objects(synthetic_objects(), "cp", BOX)
        grants = synthetic_grant()
        refs = pd.DataFrame([dict(expediente_id="SYNTHETIC", parcel_ref14=REF)])
        return cp, grants, refs

    def test_reference_plus_geometry_and_reference_only(self):
        cp, g, r = self.setup_data()
        links, _ = match_municipality(g, r, cp, "28065")
        self.assertEqual(links.match_evidence.iloc[0], "B")
        links, _ = match_municipality(g.assign(geometry_valid=False), r, cp, "28065")
        self.assertEqual(links.match_status.iloc[0], "confirmed_reference")
        self.assertEqual(links.match_evidence.iloc[0], "A")

    def test_spatial_candidate_never_confirmed(self):
        cp, g, r = self.setup_data()
        r["parcel_ref14"] = "7654321VK4712B"
        links, candidates = match_municipality(g, r, cp, "28065")
        self.assertEqual(links.match_status.iloc[0], "not_found")
        self.assertEqual(candidates.match_status.iloc[0], "spatial_candidate")
        self.assertEqual(candidates.match_evidence.iloc[0], "C")

    def test_ambiguous_reference_and_contradictory_location(self):
        cp, g, r = self.setup_data()
        links, _ = match_municipality(g, r, pd.concat([cp, cp]), "28065")
        self.assertEqual(links.match_status.iloc[0], "ambiguous")
        lon, lat = Transformer.from_crs(25830, 4326, always_xy=True).transform(X + 1000, Y)
        links, _ = match_municipality(g.assign(longitude=lon, latitude=lat), r, cp, "28065")
        self.assertEqual(links.match_status.iloc[0], "contradictory")

    def test_multi_parcel_and_accounting_remains_at_grant_level(self):
        cp, g, r = self.setup_data()
        other = cp.copy()
        other["parcel_id"] = "SECOND"
        other["parcel_ref14"] = "7654321VK4712B"
        refs = pd.concat([r, r.assign(parcel_ref14="7654321VK4712B")])
        g["importe_centimos"] = 123456
        links, _ = match_municipality(g, refs, pd.concat([cp, other]), "28065")
        self.assertEqual(len(links), 2)
        self.assertEqual(links.expediente_id.nunique(), 1)
        self.assertNotIn("importe_centimos", links)
        self.assertEqual(g.importe_centimos.sum(), 123456)

    def test_municipality_mismatch_rejected(self):
        cp, g, refs = self.setup_data()
        with self.assertRaises(ValueError):
            match_municipality(g.assign(municipality_code="28079"), refs, cp, "28065")

    def test_synthetic_capture_full_pipeline_keeps_real_territorial_decisions(self):
        # ZIP fabricados solo dentro del test: valida el flujo, no la precisión de Catastro real.
        from madrid_rehab.cadastre_download import official_url, write_json
        from madrid_rehab.grants import DEFAULT as GRANTS

        grants = pd.read_parquet(GRANTS / "grants.parquet")
        decisions = pd.read_parquet(TERRITORY / "grant_municipality_links.parquet")
        previous = pd.read_parquet(TERRITORY / "grant_parcel_links.parquet")
        selected = grants[
            grants.expediente_id.isin(
                decisions.loc[decisions.municipality_code.eq("28065"), "expediente_id"]
            )
        ].iloc[0]
        ref = previous.loc[previous.expediente_id.eq(selected.expediente_id), "parcel_ref14"].iloc[
            0
        ]
        x, y = Transformer.from_crs(4326, 25830, always_xy=True).transform(
            selected.longitude, selected.latitude
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for r in load_manifest(MANIFEST)["resources"]:
                if r["municipality_code"] != "28065":
                    continue
                path = root / "raw" / r["cadastre_code"] / (r["kind"] + ".zip")
                path.parent.mkdir(parents=True, exist_ok=True)
                with patch.dict(globals(), {"X": x - 5, "Y": y - 5, "REF": ref}):
                    path.write_bytes(package(r["kind"], xml(r["kind"])))
                write_json(
                    path.with_suffix(".zip.json"),
                    {
                        "url": official_url(r["url"]),
                        "sha256": sha256(path),
                        "bytes": path.stat().st_size,
                    },
                )
            summary, meta = integrate(root / "raw", root / "cp", root / "prtr")
            self.assertEqual(meta["integrated_municipalities"], ["28065"])
            self.assertGreater(summary.prtr_linked.sum(), 0)
            self.assertEqual(
                digest(root / "prtr" / "grant_municipality_links.parquet"),
                digest(TERRITORY / "grant_municipality_links.parquet"),
            )
            self.assertTrue((root / "cp" / "active_prtr.json").exists())
            self.assertEqual(meta["amount_cents"], 31552733899)

    def test_no_real_input_preserves_assignment_and_reports_no_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            summary, meta = integrate(Path(temp) / "raw", Path(temp) / "cp", Path(temp) / "prtr")
            self.assertEqual(summary.cp.sum(), 0)
            self.assertEqual(summary.bu.sum(), 0)
            self.assertEqual(summary.prtr.sum(), 1245)
            self.assertEqual(summary.prtr_linked.sum(), 0)
            self.assertEqual(summary.prtr_pending.sum(), 1245)
            self.assertEqual(meta["amount_cents"], 31552733899)
            self.assertEqual(
                digest(Path(temp) / "prtr" / "grant_municipality_links.parquet"),
                digest(TERRITORY / "grant_municipality_links.parquet"),
            )
            self.assertEqual(meta["integrated_municipalities"], [])
            self.assertFalse((Path(temp) / "cp" / "active_prtr.json").exists())

    def test_historical_snapshots_unchanged(self):
        initial = json.loads(Path("reports/session_12_2/initial_state.json").read_text())
        for path, sha in initial["protected_files"].items():
            self.assertEqual(digest(path), sha, path)


if __name__ == "__main__":
    unittest.main()
