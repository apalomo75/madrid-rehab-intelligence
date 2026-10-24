"""Selección parcial: preservación exacta, cuarentena por todas las claves y cruces seguros."""

import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from xml.parsers.expat import ExpatError

import pandas as pd
import pyarrow.parquet as pq
import shapely as sh

from madrid_rehab.partial_cadastre import (
    checksum,
    compare_groups,
    feature_fragments,
    ingest_layer,
    normalized_tree,
    parse_object,
    select_objects,
)
from madrid_rehab.pilot_grants import CONFIRMED, match_municipality
from test_cadastre_pilot import geometry
from test_regional_expansion import BOX, REF, X, Y, synthetic_grant


def entity(ident="CP1", ref=REF, local_id=None, typ="CadastralParcel", begin="2020-01-01"):
    local_id = local_id or ident
    ref_tag = "nationalCadastralReference" if typ == "CadastralParcel" else "reference"
    return (
        f'<{typ} g:id="{ident}"><inspireId><Identifier><namespace>TEST</namespace>'
        f"<localId>{local_id}</localId></Identifier></inspireId>"
        f"<{ref_tag}>{ref or ''}</{ref_tag}><beginLifespanVersion>{begin}</beginLifespanVersion>"
        f'<areaValue uom="m2">100</areaValue>{geometry()}</{typ}>'
    )


def collection(*entities):
    return (
        '<FeatureCollection xmlns:g="http://www.opengis.net/gml/3.2">'
        + "".join("<member>" + e + "</member>" for e in entities)
        + "</FeatureCollection>"
    ).encode()


def rows(*entities, kind="cp"):
    result = []
    for ordinal, begin, end, raw, node in feature_fragments(collection(*entities)):
        row = parse_object(node, kind)
        row.update(
            source_record_id=str(ordinal),
            source_ordinal=ordinal,
            source_gml_member="SYNTHETIC.gml",
            source_xml_sha256=checksum(raw),
        )
        result.append(row)
    return pd.DataFrame(result)


class PartialCadastreTests(unittest.TestCase):
    def test_exact_source_bytes_offsets_and_complete_normalization(self):
        body = collection(entity()).replace(
            b'<areaValue uom="m2">100', b'<areaValue uom="m2"> 100 '
        )
        ordinal, begin, end, raw, node = next(feature_fragments(body))
        self.assertEqual(raw, body[begin:end])
        self.assertIn(b"> 100 </areaValue>", raw)
        self.assertEqual(
            normalized_tree(node), normalized_tree(next(feature_fragments(collection(entity())))[4])
        )
        changed = ET.fromstring(ET.tostring(node))
        changed.set("unknownAttribute", "retained")
        self.assertNotEqual(normalized_tree(changed), normalized_tree(node))

    def test_source_xml_encoding_and_prefixes_preserved(self):
        body = (
            '<?xml version="1.0" encoding="ISO-8859-1"?>'
            '<g:FeatureCollection xmlns:g="http://www.opengis.net/gml/3.2">'
            '<g:featureMember><Object g:id="A"><name>Alcorcón</name></Object>'
            "</g:featureMember></g:FeatureCollection>"
        ).encode("latin-1")
        _, start, end, raw, node = next(feature_fragments(body))
        self.assertEqual(raw, body[start:end])
        self.assertEqual(node[0].text, "Alcorcón")

    def test_conflicting_group_all_occurrences_quarantined(self):
        different = entity().replace(">100</areaValue>", ">101</areaValue>")
        frame = select_objects(
            rows(entity(), different, entity("CP2", "7654321VK4712B")), "cp", BOX, "28065"
        )
        self.assertEqual(
            frame.selection_status.tolist(), ["quarantined", "quarantined", "accepted"]
        )
        self.assertFalse(frame.usable_geometry.iloc[:2].any())
        comparison = compare_groups(frame, "cp")[0]
        self.assertFalse(comparison["exact_duplicate_only"])
        self.assertTrue(comparison["field_differences"]["area_value"])

    def test_exact_duplicates_preserved_without_arbitrary_selection(self):
        frame = select_objects(rows(entity(), entity()), "cp", BOX, "28065")
        self.assertTrue(frame.selection_status.eq("quarantined").all())
        self.assertTrue(compare_groups(frame, "cp")[0]["exact_duplicate_only"])

    def test_inspire_collision_with_different_gml_and_reference(self):
        frame = select_objects(
            rows(entity(), entity("CP2", "7654321VK4712B", local_id="CP1")), "cp", BOX, "28065"
        )
        self.assertTrue(frame.selection_reason.str.contains("collision_inspire_key").all())
        self.assertFalse(frame.usable_geometry.any())

    def test_reference_collision_with_other_identity_keys_unique(self):
        frame = select_objects(rows(entity(), entity("CP2")), "cp", BOX, "28065")
        self.assertTrue(frame.selection_reason.str.contains("collision_parcel_ref14").all())

    def test_versions_never_choose_latest(self):
        frame = select_objects(rows(entity(), entity(begin="2025-01-01")), "cp", BOX, "28065")
        self.assertFalse(frame.usable_geometry.any())
        self.assertTrue(compare_groups(frame, "cp")[0]["date_difference"])

    def test_bu_without_parcel_reference_accepted_independently(self):
        frame = select_objects(
            rows(entity("P1", None, typ="BuildingPart"), kind="bu"), "bu", BOX, "28065"
        )
        self.assertTrue(frame.usable_geometry.iloc[0])
        self.assertEqual(frame.source_feature_type.iloc[0], "BuildingPart")
        outside = select_objects(
            rows(entity("B1", typ="Building"), kind="bu"),
            "bu",
            sh.box(X + 20, Y + 20, X + 30, Y + 30),
            "28065",
        )
        self.assertEqual(outside.selection_status.iloc[0], "quarantined")

    def test_quarantined_identity_never_confirmed_even_if_reference_group_unique(self):
        frame = select_objects(
            rows(entity(), entity("CP2", "7654321VK4712B", local_id="CP1")), "cp", BOX, "28065"
        )
        grant = synthetic_grant()
        refs = pd.DataFrame([dict(expediente_id="SYNTHETIC", parcel_ref14=REF)])
        links, candidates = match_municipality(grant, refs, frame, "28065")
        self.assertFalse(links.match_status.isin(CONFIRMED).any())
        self.assertTrue(candidates.empty)
        self.assertEqual(links.match_status.iloc[0], "unusable_cp")

    def test_record_accounting_and_hashes_reconstruct_original_fragments(self):
        data = collection(entity(), entity())
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "cp.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("SYNTHETIC.cadastralparcel.gml", data)
            evidence = dict(
                sha256=checksum(path.read_bytes()),
                members=[
                    dict(name="SYNTHETIC.cadastralparcel.gml", entities={"CadastralParcel": 2})
                ],
            )
            frame, quality = ingest_layer(path, "cp", folder, BOX, "28065", evidence)
            self.assertEqual(quality["observed"], quality["accepted"] + quality["quarantined"])
            self.assertEqual(quality["quarantined"], 2)
            records = pq.read_table(folder / "cp_source_records.parquet").to_pylist()
            self.assertEqual(len(records), 2)
            self.assertNotEqual(records[0]["source_record_id"], records[1]["source_record_id"])
            for record in records:
                raw = record["source_xml"]
                self.assertEqual(raw, data[record["source_byte_start"] : record["source_byte_end"]])
                self.assertEqual(checksum(raw), record["source_xml_sha256"])
            self.assertEqual(set(frame.source_record_id), {r["source_record_id"] for r in records})
            self.assertEqual(
                json.loads((folder / "cp_comparisons.json").read_text())[0]["occurrences"], 2
            )

    def test_last_empty_child_and_empty_feature_have_exact_ranges(self):
        for body in [collection("<Object><empty/></Object>"), collection("<Object/>")]:
            _, begin, end, raw, node = next(feature_fragments(body))
            self.assertEqual(raw, body[begin:end])
            self.assertEqual(node.tag, "Object")
            self.assertNotIn(b"member", raw)

    def test_namespace_scope_does_not_leak_from_child_or_other_member(self):
        body = (
            b'<FeatureCollection><member xmlns:p="urn:a"><p:Object>'
            b'<nested xmlns="urn:child"/></p:Object></member>'
            b'<member xmlns:p="urn:b"><p:Object/></member></FeatureCollection>'
        )
        nodes = [r[4] for r in feature_fragments(body)]
        self.assertEqual([n.tag for n in nodes], ["{urn:a}Object", "{urn:b}Object"])
        self.assertEqual(nodes[0][0].tag, "{urn:child}nested")

    def test_duplicate_geometry_id_quarantines_independent_feature_keys(self):
        a = entity().replace("<Polygon ", '<Polygon g:id="GEOMETRY" ')
        b = entity("CP2", "7654321VK4712B").replace("<Polygon ", '<Polygon g:id="GEOMETRY" ')
        frame = select_objects(rows(a, b), "cp", BOX, "28065")
        self.assertTrue(frame.selection_reason.str.contains("collision_gml_id").all())

    def test_unexpected_truncation_and_dtd_rejected(self):
        with self.assertRaises(ExpatError):
            list(feature_fragments(collection(entity())[:-5]))
        with self.assertRaisesRegex(ValueError, "DTD"):
            list(feature_fragments(b"<!DOCTYPE x><FeatureCollection/>"))
