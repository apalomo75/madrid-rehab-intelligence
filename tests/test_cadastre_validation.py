"""Regresiones de integridad de colecciones: nunca confundir EOF válido con cobertura."""

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from madrid_rehab.cadastre_download import inspect_zip
from madrid_rehab.pilot_objects import validate_collection_inventory, validate_readable_objects
from test_cadastre_pilot import package, xml
from test_regional_expansion import synthetic_objects


class CollectionValidationTests(unittest.TestCase):
    def inspect(self, body, kind="cp"):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "source.zip"
            path.write_bytes(package(kind, body))
            return inspect_zip(path, kind)

    def test_counts_members_entities_and_namespace(self):
        report = self.inspect(xml("cp"))
        member = report["members"][0]
        self.assertEqual(member["feature_members"], 1)
        self.assertEqual(member["entities"], {"CadastralParcel": 1})
        self.assertEqual(member["unique_feature_ids"], 1)
        self.assertIn(("g", "http://www.opengis.net/gml/3.2"), member["namespaces"])
        validate_collection_inventory(report)

    def test_well_formed_short_collection_still_rejected(self):
        report = self.inspect(xml("cp").replace(b'numberReturned="1"', b'numberReturned="2"'))
        with self.assertRaisesRegex(ValueError, "declarado 2; observado 1"):
            validate_collection_inventory(report)

    def test_duplicate_entities_rejected_even_with_matching_header(self):
        body = xml("cp")
        member = body[body.index(b"<member>") : body.index(b"</member>") + len(b"</member>")]
        body = body.replace(b'numberReturned="1"', b'numberReturned="2"')
        report = self.inspect(
            body.replace(b"</FeatureCollection>", member + b"</FeatureCollection>")
        )
        self.assertEqual(report["members"][0]["duplicate_feature_ids"], {"CadastralParcel": 1})
        with self.assertRaisesRegex(ValueError, "gml:id duplicados"):
            validate_collection_inventory(report)

    def test_truncated_xml_rejected(self):
        with self.assertRaises(ET.ParseError):
            self.inspect(xml("cp")[:-20])

    def test_empty_member_rejected(self):
        with self.assertRaisesRegex(ValueError, "vacío"):
            self.inspect(b"<FeatureCollection><member/></FeatureCollection>")

    def test_pagination_rejected(self):
        report = self.inspect(
            xml("cp").replace(b"<FeatureCollection ", b'<FeatureCollection next="page2" ')
        )
        with self.assertRaisesRegex(ValueError, "paginada"):
            validate_collection_inventory(report)

    def test_building_part_separate_and_missing_count_not_invented(self):
        report = self.inspect(xml("bu", part=True).replace(b' numberReturned="1"', b""), "bu")
        self.assertEqual(report["members"][0]["entities"], {"Building": 1})
        validate_collection_inventory(report)

    def test_unreadable_geometry_and_duplicate_rows_block_audited_ingestion(self):
        frame = synthetic_objects()
        with self.assertRaisesRegex(ValueError, "duplicados"):
            validate_readable_objects(pd.concat([frame, frame]), "cp")
        with self.assertRaisesRegex(ValueError, "ilegibles"):
            validate_readable_objects(frame.assign(geometry_wkt="INVALID"), "cp")
        validate_readable_objects(frame, "cp")
