"""Regresiones sintéticas de la ingesta masiva; sin acceso a red."""

import json
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

import pandas as pd

from madrid_rehab.ingest import (
    Archive,
    csv_encoding,
    madrid_entry,
    normalize_certificates,
    geometry_quality,
    cadastral_rows,
    digest,
    run,
)
from madrid_rehab.sources import parse_parcels


class IngestionTests(unittest.TestCase):
    def test_scope_history_and_exact_duplicate_identity(self):
        mapping = json.loads(Path("config/sample.json").read_text())["scope_map"]
        base = {
            "edif_muni": " Madrid ",
            "edif_tipo": "BloqueDeViviendaCompleto",
            "edif_refcat": "1234567VK4712A",
            "edif_codreg": "SYNTHETIC",
            "edif_fecha": "01/02/2025",
        }
        frame = pd.DataFrame(
            [
                base,
                base,
                {**base, "edif_fecha": "01/03/2025"},
                {**base, "edif_muni": "Las Rozas de Madrid"},
                {**base, "edif_tipo": "FutureUnknown"},
            ]
        )
        result = normalize_certificates(frame, mapping)
        self.assertEqual(len(result), 4)
        self.assertEqual(result.record_id.nunique(), 3)
        self.assertEqual(result.iloc[0].certificate_scope, "whole_building")
        self.assertEqual(result.iloc[-1].certificate_scope, "unknown")
        self.assertEqual(result.iloc[0].certificate_date.month, 2)
        self.assertEqual(result.iloc[0].parcel_references, ["1234567VK4712A"])

    def test_municipal_atom_code_is_not_ine(self):
        body = b"""<feed xmlns="http://www.w3.org/2005/Atom"><rights>Attribution</rights>
        <entry><title> 28900-MADRID buildings</title><updated>2026-08-21</updated>
        <link rel="enclosure" href="https://www.catastro.hacienda.gob.es/madrid.zip"/></entry>
        <entry><title>28079-OTHER buildings</title></entry></feed>"""
        url, meta = madrid_entry(body)
        self.assertTrue(url.endswith("madrid.zip"))
        self.assertEqual(meta["updated"], "2026-08-21")
        with self.assertRaises(ValueError):
            madrid_entry(body.replace(b"28900-MADRID", b"28079-MADRID"))

    def test_encoding_keeps_original_bytes_and_resets_stream(self):
        for data, encoding in [("año".encode("utf-8"), "utf-8-sig"), (b"a\xf1o\x8d", "latin-1")]:
            stream = io.BytesIO(data)
            self.assertEqual(csv_encoding(stream), encoding)
            self.assertEqual(stream.tell(), 0)

    def test_invalid_topology_preserved_and_flagged(self):
        wkt = "MULTIPOLYGON (((440000 4470000, 440010 4470010, 440010 4470000, 440000 4470010, 440000 4470000)))"
        result = geometry_quality(pd.DataFrame({"geometry_wkt": [wkt, None]}))
        self.assertEqual(result.geometry_valid.tolist(), [False, False])
        self.assertEqual(result.iloc[0].geometry_wkt, wkt)

    def test_archive_flushes_small_body_and_verifies_cache(self):
        class Response(io.BytesIO):
            headers = {"Content-Length": "1"}

            def geturl(self):
                return "https://datos.comunidad.madrid/file"

        with tempfile.TemporaryDirectory() as tmp:
            archive = Archive(tmp)
            with patch("urllib.request.urlopen", return_value=Response(b"x")):
                path, meta = archive.fetch("https://datos.comunidad.madrid/file", "file")
            self.assertEqual(meta["sha256"], digest(path))
            path.write_bytes(b"y")
            with self.assertRaises(ValueError):
                archive.fetch("https://datos.comunidad.madrid/file", "file")

    def test_zip_selects_parcels_and_reports_declared_count_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cp.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "test.cadastralparcel.gml", '<FeatureCollection numberReturned="1"/>'
                )
                archive.writestr("test.cadastralzoning.gml", "<ignored/>")
            self.assertEqual(list(cadastral_rows(path, "parcelas")), [])

    def test_offline_missing_original_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                Archive(tmp, offline=True).fetch("https://datos.comunidad.madrid/file", "file")

    def test_cp_retains_polygon_and_official_crs(self):
        xml = b"""<CadastralParcel xmlns:gml="http://www.opengis.net/gml/3.2" gml:id="SYNTHETIC">
        <nationalCadastralReference>1234567VK4712A</nationalCadastralReference>
        <geometry><gml:Polygon srsName="http://www.opengis.net/def/crs/EPSG/0/25830">
        <gml:exterior><gml:LinearRing><gml:posList>440000 4470000 440010 4470000 440010 4470010 440000 4470000</gml:posList>
        </gml:LinearRing></gml:exterior></gml:Polygon></geometry></CadastralParcel>"""
        result = parse_parcels(xml)[0]
        self.assertEqual(result["parcel_id"], "SYNTHETIC")
        self.assertEqual(result["geometry_crs"], "EPSG:25830")
        self.assertIsNotNone(result["geometry_wkt"])


class CompleteIngestionTests(unittest.TestCase):
    def test_offline_three_table_roundtrip_with_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir()
            catalog = {
                "success": True,
                "result": {
                    "license_title": "test",
                    "resources": [
                        {
                            "name": f"Registro CEEE {year}",
                            "url": f"https://datos.comunidad.madrid/{year}.csv",
                            "id": str(year),
                        }
                        for year in (2025, 2026)
                    ],
                },
            }
            bodies = {"catalog.json": json.dumps(catalog).encode()}
            csv = "edif_muni;edif_tipo;edif_codreg;edif_fecha;edif_refcat\nMadrid;BloqueDeViviendaCompleto;SYNTHETIC;01/02/2025;1234567VK4712A\n"
            bodies.update({f"certificados_{year}.csv": csv.encode() for year in (2025, 2026)})
            ring = "440000 4470000 440010 4470000 440010 4470010 440000 4470000"
            geometry = f'<geometry><gml:Polygon srsName="EPSG:25830"><gml:exterior><gml:LinearRing><gml:posList>{ring}</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></geometry>'
            for kind in ("edificios", "parcelas"):
                feed = f'<feed xmlns="http://www.w3.org/2005/Atom"><rights>test</rights><entry><title>28900-MADRID test</title><updated>2026-08-21</updated><link rel="enclosure" href="https://www.catastro.hacienda.gob.es/{kind}.zip"/></entry></feed>'
                bodies[f"{kind}_atom.xml"] = feed.encode()
                tag = "Building" if kind == "edificios" else "CadastralParcel"
                ref = (
                    "<externalReference><reference>1234567VK4712A</reference></externalReference>"
                    if kind == "edificios"
                    else '<nationalCadastralReference>1234567VK4712A</nationalCadastralReference><referencePoint><gml:Point srsName="EPSG:25830"><gml:pos>440000 4470000</gml:pos></gml:Point></referencePoint>'
                )
                gml = f'<FeatureCollection xmlns:gml="http://www.opengis.net/gml/3.2" numberReturned="1"><{tag} gml:id="TEST.{kind}">{ref}{geometry}</{tag}></FeatureCollection>'
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as archive:
                    archive.writestr(
                        "test."
                        + ("building.gml" if kind == "edificios" else "cadastralparcel.gml"),
                        gml,
                    )
                bodies[f"{kind}_28900.zip"] = buffer.getvalue()

            def fetch(self, url, name):
                path = raw / name
                path.write_bytes(bodies[name])
                return path, {
                    "url": url,
                    "sha256": digest(path),
                    "captured_at": "2026-10-22",
                    "bytes": len(bodies[name]),
                    "headers": {},
                }

            with patch.object(Archive, "fetch", fetch):
                run(raw, root / "out", offline=True)
            cert = pd.read_parquet(root / "out/certificados_madrid.parquet")
            self.assertEqual(len(cert), 1)
            self.assertEqual(cert.iloc[0].source_occurrences, 2)
            self.assertEqual(cert.iloc[0].parcel_link_quality, "authority_parcel_reference")
            self.assertEqual(cert.iloc[0].building_link_quality, "unresolved_physical_building")
            for kind in ("parcelas", "edificios"):
                frame = pd.read_parquet(root / f"out/{kind}_madrid.parquet")
                self.assertEqual(len(frame), 1)
                self.assertTrue(frame.geometry_valid.all())
                self.assertEqual(frame.iloc[0].link_quality, "authority_parcel_reference")
            self.assertTrue((root / "out/informe_ingesta.md").exists())
