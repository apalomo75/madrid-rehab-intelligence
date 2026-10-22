"""Pruebas offline con datos explícitamente sintéticos; no miden cobertura real."""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

import pandas as pd

from madrid_rehab.http import Client, DownloadError
from madrid_rehab.integrate import integrate, quality
from madrid_rehab.normalize import address_key, certification_scope, reference, split_references
from madrid_rehab.pipeline import capture, run
from madrid_rehab.sources import energy_sample, parse_buildings, parse_parcels, parse_properties


PARCEL = "1234567VK4712A"
UNIT = PARCEL + "0001AB"
OTHER = "7654321VK4712A"
RESOURCE = "synthetic-resource"


def config():
    result = json.loads(Path("config/sample.json").read_text())
    result["interval_seconds"] = 0
    result["resource_id"] = RESOURCE
    return result


def row(**changes):
    return {"_id": 1, "edif_codreg": "TEST-1", "edif_refcat": UNIT,
            "edif_tipo": "Vivienda individual", "edif_direc": "C/ Prueba, 1, 2 B",
            "edif_muni": "Madrid", "cal_norenovglobal": "G", **changes}


def point():
    return {"parcel_ref14": PARCEL, "x": 440000, "y": 4470000,
            "coordinate_crs": "EPSG:25830", "coordinate_scope": "parcel_reference_point"}


class Response(io.BytesIO):
    def __init__(self, body, headers=None, status=200):
        super().__init__(body)
        self.headers = headers or {}
        self.status = status

    def geturl(self):
        return "https://datos.comunidad.madrid/api/3/action/datastore_search"


class NormalizationTests(unittest.TestCase):
    def test_reference_preserves_property_and_parcel(self):
        ref = reference(" 1234567vk4712a 0001ab ")
        self.assertEqual(ref["property_ref20"], UNIT)
        self.assertEqual(ref["parcel_ref14"], PARCEL)
        self.assertEqual(ref["checksum_status"], "not_checked")

    def test_does_not_repair_punctuation_or_rural(self):
        for raw in ["garbage", "", PARCEL + "-0001AB", "28079A00100001"]:
            self.assertFalse(reference(raw)["reference_format_valid"])

    def test_multiple_and_empty_references(self):
        self.assertEqual(split_references(UNIT + "; " + OTHER), [UNIT, OTHER])
        self.assertEqual(split_references(None), [""])

    def test_address_preserves_unit_information(self):
        self.assertEqual(address_key("C/ Prúeba, 1, 2º B"), "CALLE PRUEBA 1 2O B")
        self.assertNotEqual(address_key("C/ Prueba 1 2 B"), address_key("C/ Prueba 1 3 B"))

    def test_scope_without_review_is_unknown(self):
        self.assertEqual(certification_scope("Vivienda individual"), "unknown")
        self.assertEqual(certification_scope("7"), "unknown")
        self.assertEqual(certification_scope("Vivienda individual", {"Vivienda individual": "dwelling"}), "dwelling")


class IntegrationTests(unittest.TestCase):
    def build(self, records=None, parcels=None, buildings=None, properties=None):
        return integrate(records or [row()], parcels or [], buildings or [], properties or [],
                         RESOURCE, {"Vivienda individual": "dwelling", "Edificio completo": "whole_building"})

    def test_unit_without_authority_is_not_confirmed_by_parcel(self):
        result = self.build(parcels=[point()])
        self.assertTrue(result.iloc[0].parcel_exists)
        self.assertEqual(result.iloc[0].match_status, "pending_validation")
        self.assertTrue(pd.isna(result.iloc[0].x))

    def test_authority_confirmed_unit_keeps_scope_and_parcel_location(self):
        result = self.build(parcels=[point()], properties=[{"property_ref20": UNIT, "authority_confirmed": True}],
                            buildings=[{"parcel_ref14": PARCEL, "building_id": "SYNTHETIC.BU.1"}])
        first = result.iloc[0]
        self.assertEqual(first.match_status, "matched")
        self.assertEqual(first.certificate_scope, "dwelling")
        self.assertEqual(first.energy_grade_raw, "G")
        self.assertEqual(first.coordinate_scope, "parcel_reference_point")
        self.assertTrue(pd.isna(first.building_id))

    def test_whole_building_not_mapped_just_because_single_bu(self):
        result = self.build(records=[row(edif_tipo="Edificio completo", edif_refcat=PARCEL)],
                            parcels=[point()], buildings=[{"parcel_ref14": PARCEL, "building_id": "ONLY"}])
        self.assertEqual(result.iloc[0].certificate_scope, "whole_building")
        self.assertTrue(pd.isna(result.iloc[0].building_id))

    def test_multireference_and_no_reference_rows_preserved(self):
        result = self.build(records=[row(edif_refcat=PARCEL + ", " + OTHER), row(_id=2, edif_refcat=None)],
                            parcels=[point()])
        self.assertEqual(len(result), 3)
        metrics = quality(result, [row(), row(_id=2)], [])
        self.assertEqual(metrics["reference_match_percent"], 33.33)
        self.assertEqual(metrics["source_row_match_percent"], 0)

    def test_ambiguous_parcel_does_not_match(self):
        result = self.build(records=[row(edif_refcat=PARCEL)], parcels=[point(), point()])
        self.assertEqual(result.iloc[0].pending_reason, "ambiguous_parcel_response")

    def test_invalid_crs_and_coordinate_not_geolocated(self):
        for changes in [{"coordinate_crs": "EPSG:4326"}, {"x": float("inf")}, {"x": -3.7}]:
            result = self.build(records=[row(edif_refcat=PARCEL)], parcels=[{**point(), **changes}])
            self.assertEqual(result.iloc[0].match_status, "matched")
            self.assertTrue(pd.isna(result.iloc[0].x))

    def test_stable_ids_and_no_grade_in_building_entity(self):
        a = self.build(records=[row(), row(_id=2)])
        b = self.build(records=[row(_id=2), row()])
        self.assertEqual(set(a.certificate_row_id), set(b.certificate_row_id))


class SourceTests(unittest.TestCase):
    def test_cp_accepts_official_crs_uri_without_accepting_other_zones(self):
        for code in ("25830", "25831"):
            with self.subTest(code=code):
                xml = f'''<FeatureCollection xmlns:gml="http://www.opengis.net/gml/3.2">
                <CadastralParcel><nationalCadastralReference>{PARCEL}</nationalCadastralReference>
                <referencePoint><gml:Point srsName="http://www.opengis.net/def/crs/EPSG/0/{code}">
                <gml:pos>440000 4470000</gml:pos></gml:Point></referencePoint>
                </CadastralParcel></FeatureCollection>'''
                result = parse_parcels(xml.encode())[0]
                self.assertEqual(result["x"], 440000 if code == "25830" else None)
                self.assertEqual(result["coordinate_crs"], "EPSG:25830" if code == "25830" else None)

    def test_cp_reads_reference_point_with_crs(self):
        xml = f'''<FeatureCollection xmlns:gml="http://www.opengis.net/gml/3.2"><CadastralParcel>
        <nationalCadastralReference>{PARCEL}</nationalCadastralReference><referencePoint>
        <gml:Point srsName="urn:ogc:def:crs:EPSG::25830"><gml:pos>440000 4470000</gml:pos>
        </gml:Point></referencePoint></CadastralParcel></FeatureCollection>'''
        self.assertEqual(parse_parcels(xml.encode())[0]["x"], 440000)

    def test_bu_geometry_does_not_create_unit_identity(self):
        xml = f'''<FeatureCollection xmlns:gml="http://www.opengis.net/gml/3.2"><Building gml:id="TEST.BU.1">
        <externalReference><reference>{PARCEL}</reference></externalReference>
        <geometry><gml:Surface srsName="EPSG:25830"><gml:patches><gml:PolygonPatch>
        <gml:exterior><gml:LinearRing><gml:posList>440000 4470000 440010 4470000 440010 4470010 440000 4470000</gml:posList>
        </gml:LinearRing></gml:exterior></gml:PolygonPatch></gml:patches></gml:Surface></geometry>
        </Building></FeatureCollection>'''
        result = parse_buildings(xml.encode())[0]
        self.assertTrue(result["geometry_wkt"].startswith("MULTIPOLYGON"))
        self.assertEqual(result["building_geometry_status"], "structural_only")
        self.assertNotIn("energy_grade", result)

    def test_property_confirmation_requires_full_rc(self):
        xml = '''<consulta_dnp><bico><bi><idbi><rc><pc1>1234567</pc1><pc2>VK4712A</pc2>
        <car>0001</car><cc1>A</cc1><cc2>B</cc2></rc></idbi></bi></bico></consulta_dnp>'''
        self.assertEqual(parse_properties(xml.encode())[0]["property_ref20"], UNIT)
        self.assertEqual(parse_properties(b"<consulta_dnp><rc><pc1>1234567</pc1></rc></consulta_dnp>"), [])

    def test_xml_rejects_error_html_entities_and_malformed(self):
        for xml in [b"<html>error</html>", b"<ExceptionReport><ExceptionText>bad</ExceptionText></ExceptionReport>",
                    b'<!DOCTYPE x [<!ENTITY a "x">]><x/>', b"<broken"]:
            with self.assertRaises(ValueError):
                parse_parcels(xml)

    def test_ckan_limit_sort_and_required_columns(self):
        class FakeClient:
            def get(self, base, params):
                self.params = params
                return json.dumps({"success": True, "result": {"records": [row()], "fields": []}}).encode()
        client = FakeClient()
        self.assertEqual(len(energy_sample(client, config())["records"]), 1)
        self.assertEqual(client.params["sort"], "_id asc")
        self.assertEqual(client.params["limit"], 30)


class HttpTests(unittest.TestCase):
    def test_limit_without_content_length_and_no_partial_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {**config(), "max_response_bytes": 10}
            client = Client(tmp, cfg, opener=lambda *a, **k: Response(b"x" * 11))
            with self.assertRaises(DownloadError):
                client.get("https://datos.comunidad.madrid/test")
            self.assertEqual(len(list(Path(tmp).glob("*.body"))), 0)

    def test_content_length_limit_prevents_body_read(self):
        response = Response(b"x" * 100, {"Content-Length": "100"})
        with tempfile.TemporaryDirectory() as tmp:
            client = Client(tmp, {**config(), "max_response_bytes": 10}, opener=lambda *a, **k: response)
            with self.assertRaises(DownloadError):
                client.get("https://datos.comunidad.madrid/test")
            self.assertEqual(client.events[0]["bytes_read"], 0)

    def test_cache_is_reproducible_and_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = Client(tmp, config(), opener=lambda *a, **k: Response(b"{}"))
            url = "https://datos.comunidad.madrid/test"
            self.assertEqual(client.get(url), client.get(url))
            self.assertEqual(client.requests, 1)
            next(Path(tmp).glob("*.body")).write_bytes(b"changed")
            with self.assertRaises(DownloadError):
                client.get(url)

    def test_dns_failure_has_no_http_status(self):
        def failing(*args, **kwargs):
            raise urllib.error.URLError("DNS failure")
        with tempfile.TemporaryDirectory() as tmp:
            client = Client(tmp, config(), opener=failing)
            with self.assertRaises(DownloadError):
                client.get("https://datos.comunidad.madrid/test")
            self.assertIsNone(client.events[0]["http_status"])

    def test_ceiling_and_request_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                Client(tmp, {**config(), "max_total_bytes": 5242881})
            client = Client(tmp, {**config(), "max_requests": 1}, opener=lambda *a, **k: Response(b"{}"))
            client.get("https://datos.comunidad.madrid/one")
            with self.assertRaises(DownloadError):
                client.get("https://datos.comunidad.madrid/two")


class PipelineTests(unittest.TestCase):
    def test_end_to_end_synthetic_snapshot_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = {"resource_id": RESOURCE, "data_kind": "synthetic_test_only",
                        "energy": {"records": [row()], "fields": []}, "parcels": [point()],
                        "properties": [{"property_ref20": UNIT, "authority_confirmed": True}],
                        "buildings": [], "errors": [], "selected_references": [UNIT]}
            source = root / "input.json"
            source.write_text(json.dumps(snapshot))
            result = run(config(), root / "raw", root / "out", root / "report", source)
            parquet = pd.read_parquet(root / "out/certificate_reference_links.parquet")
            self.assertEqual(len(parquet), 1)
            self.assertEqual(result["metrics"]["reference_match_percent"], 100)
            self.assertEqual(result["metrics"]["certificate_buildings_reliably_geolocated"], 0)
            self.assertEqual(parquet.iloc[0].certificate_scope_raw, "Vivienda individual")
            self.assertEqual(parquet.iloc[0].certificate_scope, "unknown")
            self.assertEqual(parquet.iloc[0].energy_grade_raw, "G")
            with self.assertRaises(ValueError):
                run(config(), root / "raw", root / "out", root / "report", source)

    def test_empty_snapshot_reports_undefined_percentage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = {"resource_id": RESOURCE, "data_kind": "synthetic_test_only",
                        "energy": {"records": [], "fields": []}, "parcels": [], "properties": [],
                        "buildings": [], "errors": [{"source": "energy", "error": "test failure"}],
                        "selected_references": []}
            source = root / "input.json"
            source.write_text(json.dumps(snapshot))
            result = run(config(), root / "raw", root / "out", root / "report", source)
            self.assertEqual(result["status"], "blocked")
            self.assertIsNone(result["metrics"]["reference_match_percent"])
            self.assertEqual(len(pd.read_parquet(root / "out/certificate_reference_links.parquet")), 0)

    def test_capture_stops_after_domain_failure(self):
        class FailingClient:
            def __init__(self):
                self.calls = 0
            def get(self, *args, **kwargs):
                self.calls += 1
                raise DownloadError("synthetic DNS failure")
        client = FailingClient()
        snapshot = capture(client, config())
        self.assertEqual(client.calls, 2)
        self.assertEqual(len(snapshot["errors"]), 2)
        self.assertEqual(snapshot["energy"]["records"], [])


if __name__ == "__main__":
    unittest.main()
