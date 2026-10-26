"""Focused offline parser, documentary classification and immutable replay controls."""

from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd
import shapely as sh

from madrid_rehab.cadastre_attributes import (
    extract_attribute,
    ATTRIBUTES,
    iter_features,
    parse_feature,
)
from madrid_rehab.cadastre_enrichment import (
    classify_link,
    enrich_municipality,
    relation_records,
    resolve_links,
    validate_partition_frames,
)
from madrid_rehab.ingest import digest, save_json
from madrid_rehab.partial_cadastre import encoded, normalized_tree, checksum

NS = (
    'xmlns:gml="http://www.opengis.net/gml/3.2" '
    'xmlns:b="http://inspire.jrc.ec.europa.eu/schemas/bu-ext2d/2.0" '
    'xmlns:c="http://inspire.jrc.ec.europa.eu/schemas/bu-core2d/2.0" '
    'xmlns:xlink="http://www.w3.org/1999/xlink" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
)
REF = "0015101VK7801N"
REF2 = "0015102VK7801N"
HREF = "http://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?STOREDQUERIE_ID=GetParcel&amp;refcat="
POLYGON = "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"


def feature(typ="Building", bid="b1", body=None):
    if body is None:
        body = (
            "<b:currentUse>1_residential</b:currentUse>"
            "<b:numberOfDwellings>0</b:numberOfDwellings>"
            "<b:officialArea><b:OfficialArea><b:officialAreaReference>grossFloorArea</b:officialAreaReference>"
            '<b:value uom="m2">12.5</b:value></b:OfficialArea></b:officialArea>'
            f'<c:cadastralParcels xlink:href="{HREF}{REF}"/>'
        )
    return f'<b:{typ} {NS} gml:id="{bid}">{body}</b:{typ}>'


def collection(items):
    return (
        f"<gml:FeatureCollection {NS}>"
        + "".join(f"<gml:featureMember>{item}</gml:featureMember>" for item in items)
        + "</gml:FeatureCollection>"
    ).encode()


def frames():
    bu = pd.DataFrame(
        [
            dict(
                building_id="b1",
                source_feature_type="Building",
                geometry_wkt=POLYGON,
                geometry_crs="EPSG:25830",
                municipality_code="28005",
                selection_status="accepted",
                usable_geometry=True,
            )
        ]
    )
    cp = pd.DataFrame(
        [
            dict(
                parcel_ref14=REF,
                parcel_id="p1",
                reference_original=REF,
                geometry_wkt=POLYGON,
                geometry_crs="EPSG:25830",
                municipality_code="28005",
                source_municipality_code="28005",
                selection_status="accepted",
                usable_geometry=True,
                selection_reason="",
                source_zip_sha256="cp",
                lifespan_begin=None,
            )
        ]
    )
    return bu, cp


class AttributeTests(unittest.TestCase):
    def test_values_units_scope_and_raw_provenance(self):
        record = parse_feature(ET.fromstring(feature()))
        self.assertEqual(record["attributes"]["dwellings"]["value"], "0")
        area = record["attributes"]["official_area"]
        self.assertEqual(area["value"], "12.5")
        self.assertEqual(area["evidence"][0]["xml_attributes"], {"uom": "m2"})
        self.assertEqual(record["documentary_references"][0]["cp_reference_original"], REF)
        part = parse_feature(
            ET.fromstring(
                feature(
                    "BuildingPart",
                    "part1",
                    "<b:numberOfFloorsAboveGround>2</b:numberOfFloorsAboveGround>",
                )
            )
        )
        self.assertEqual(part["attributes"]["current_use"]["state"], "absent")
        self.assertIsNone(part["attributes"]["official_area"]["value"])
        self.assertEqual(part["source_feature_type"], "BuildingPart")

    def test_missing_empty_invalid_pending_and_zero(self):
        for body, state, value in [
            ("", "absent", None),
            ('<b:numberOfDwellings xsi:nil="true" nilReason="unknown"/>', "present_empty", None),
            ("<b:numberOfDwellings> </b:numberOfDwellings>", "present_empty", None),
            ("<b:numberOfDwellings>-1</b:numberOfDwellings>", "invalid", None),
            ("<b:numberOfDwellings>0.5</b:numberOfDwellings>", "invalid", None),
            ("<b:numberOfDwellings>0</b:numberOfDwellings>", "declared", "0"),
        ]:
            with self.subTest(body=body):
                a = extract_attribute(ET.fromstring(feature(body=body)), ATTRIBUTES["dwellings"])
                self.assertEqual((a["state"], a["value"]), (state, value))
        for raw in ["--01-01T00:00:00", "2020-02-30T00:00:00", "988-01-01T00:00:00"]:
            body = f"<c:dateOfConstruction><c:DateOfEvent><c:beginning>{raw}</c:beginning></c:DateOfEvent></c:dateOfConstruction>"
            self.assertEqual(
                parse_feature(ET.fromstring(feature(body=body)))["attributes"][
                    "construction_begin"
                ]["state"],
                "invalid",
            )
        body = '<b:heightBelowGround uom="ft">2</b:heightBelowGround><c:conditionOfConstruction>-</c:conditionOfConstruction>'
        r = parse_feature(ET.fromstring(feature(body=body)))
        self.assertEqual(r["attributes"]["height_below"]["state"], "pending_interpretation")
        self.assertEqual(r["attributes"]["condition"]["state"], "pending_interpretation")

    def test_streaming_types_security_and_no_nested_inheritance(self):
        data = collection(
            [feature(), feature("BuildingPart", "part"), feature("OtherConstruction", "other")]
        )
        self.assertEqual(
            [parse_feature(n)["source_feature_type"] for _, n in iter_features(BytesIO(data))],
            ["Building", "BuildingPart", "OtherConstruction"],
        )
        with self.assertRaises(ValueError):
            list(iter_features(BytesIO(b'<!DOCTYPE foo [<!ENTITY x "x">]>' + data)))
        with self.assertRaises(ValueError):
            parse_feature(ET.fromstring(feature(body=feature("BuildingPart", "nested"))))


class RelationTests(unittest.TestCase):
    def test_threshold_classes_and_no_spatial_reference_creation(self):
        base = dict(
            explicit_documentary_reference=True,
            cp_reference_normalized=REF,
            accepted_cp_count=1,
            cp_all_count=1,
            geometry_valid=True,
            intersection_ratio=1,
            other_cp_material_overlap_count=0,
        )
        self.assertEqual(classify_link(base)[0], "A")
        for changes, state in [
            ({"explicit_documentary_reference": False}, "D"),
            ({"accepted_cp_count": 0}, "C"),
            ({"cp_reference_normalized": None}, "C"),
            ({"cp_all_count": 2}, "B"),
            ({"geometry_valid": False}, "B"),
            ({"intersection_ratio": 0.94}, "B"),
            ({"other_cp_material_overlap_count": 1}, "B"),
        ]:
            self.assertEqual(classify_link({**base, **changes})[0], state)

    def test_documentary_cardinality_and_spatial_discordance(self):
        bu, cp = frames()
        body = "".join(f'<c:cadastralParcels xlink:href="{HREF}{ref}"/>' for ref in [REF, REF2])
        record = parse_feature(ET.fromstring(feature(body=body)))
        links = relation_records(record, {})
        self.assertEqual(len(links), 2)
        self.assertTrue(
            all(
                link["reference_integrity_issue"] == "multiple_documentary_cp_references"
                for link in links
            )
        )
        r = resolve_links(links, bu, cp, cp, "28005")
        self.assertTrue(r.link_class.eq("B").all())
        direct = relation_records(parse_feature(ET.fromstring(feature())), {})
        bu.loc[0, "geometry_wkt"] = "POLYGON ((20 20, 21 20, 21 21, 20 21, 20 20))"
        r = resolve_links(direct, bu, cp, cp, "28005")
        self.assertEqual(r.iloc[0].link_class, "B")
        self.assertEqual(r.iloc[0].spatial_status, "disjoint")
        self.assertEqual(r.iloc[0].parcel_id, "p1")
        self.assertFalse(r.spatial_assignment_created.any())
        # Spatial containment alone without a documentary reference remains D.
        bu.loc[0, "geometry_wkt"] = POLYGON
        no_ref = relation_records(parse_feature(ET.fromstring(feature(body=""))), {})
        self.assertEqual(resolve_links(no_ref, bu, cp, cp, "28005").iloc[0].link_class, "D")

    def test_geometries_duplicates_and_municipal_isolation(self):
        bu, cp = frames()
        direct = relation_records(parse_feature(ET.fromstring(feature())), {})
        all_cp = pd.concat([cp, cp], ignore_index=True)
        self.assertEqual(resolve_links(direct, bu, cp, all_cp, "28005").iloc[0].link_class, "B")
        bu.loc[0, "geometry_wkt"] = "POLYGON ((0 0, 10 10, 0 10, 10 0, 0 0))"
        self.assertFalse(sh.is_valid(sh.from_wkt(bu.geometry_wkt.iloc[0])))
        self.assertEqual(resolve_links(direct, bu, cp, cp, "28005").iloc[0].link_class, "B")
        cp.loc[0, "municipality_code"] = "28065"
        with self.assertRaises(ValueError):
            validate_partition_frames(bu, cp, cp, "28005")


class PipelineTests(unittest.TestCase):
    def fixture(self, root):
        raw, accepted = root / "raw", root / "accepted"
        (raw / "28005").mkdir(parents=True)
        (accepted / "28005").mkdir(parents=True)
        items = [
            feature(),
            feature(
                "BuildingPart",
                "part1",
                "<b:numberOfFloorsAboveGround>2</b:numberOfFloorsAboveGround>"
                + f'<c:cadastralParcels xlink:href="{HREF}{REF}"/>',
            ),
            feature("OtherConstruction", "other", ""),
        ]
        zp = raw / "28005/bu.zip"
        # One archive member per original type, as in the real source.
        with zipfile.ZipFile(zp, "w") as z:
            for typ, item in zip(["building", "buildingpart", "otherconstruction"], items):
                z.writestr("fixture." + typ + ".gml", collection([item]))
        sha = digest(zp)
        save_json(zp.with_suffix(".zip.json"), dict(sha256=sha, captured_at="2026-01-01"))
        save_json(raw / "28005/cp.zip.json", dict(captured_at="2026-01-01"))
        bu, cp = frames()
        rows = []
        for typ, item in zip(["building", "buildingpart"], items):
            node = ET.fromstring(item)
            record = parse_feature(node)
            row = bu.iloc[0].to_dict()
            row.update(
                building_id=record["building_id"],
                source_feature_type=record["source_feature_type"],
                source_gml_member="fixture." + typ + ".gml",
                source_ordinal=1,
                source_zip_sha256=sha,
                normalized_sha256=checksum(encoded(normalized_tree(node)).encode()),
                source_record_id=typ,
                current_use="1_residential" if typ == "building" else None,
                construction_begin=None,
                construction_end=None,
                dwellings_raw="0" if typ == "building" else None,
                building_units_raw=None,
            )
            rows.append(row)
        bu = pd.DataFrame(rows)
        bu["source_id_conflict"] = pd.Series([False] * len(bu), dtype="boolean")
        for name, df in [("bu", bu), ("bu_all", bu), ("cp", cp), ("cp_all", cp)]:
            df.to_parquet(accepted / "28005" / f"{name}.parquet", index=False)
        outputs = {p.name: digest(p) for p in (accepted / "28005").glob("*.parquet")}
        save_json(
            accepted / "28005/manifest.json",
            dict(
                version="partial-cadastre-v1",
                quality=dict(municipality_code="28005", bu=dict(observed=2)),
                inputs={str(zp): sha},
                outputs=outputs,
            ),
        )
        save_json(
            accepted / "manifest.json",
            dict(outputs={"28005/manifest.json": digest(accepted / "28005/manifest.json")}),
        )
        return raw, accepted

    def test_complete_deterministic_safe_replay_and_integrity(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            raw, accepted = self.fixture(root)
            before = {
                str(p): digest(p)
                for tree in (raw, accepted)
                for p in tree.rglob("*")
                if p.is_file()
            }
            a = enrich_municipality("28005", root / "out", accepted, raw)
            b = enrich_municipality("28005", root / "replay", accepted, raw)
            self.assertEqual(a["outputs"], b["outputs"])
            self.assertEqual(a["summary"]["enriched_bu"], 2)
            self.assertEqual(a["summary"]["link_classes"], {"A": 2})
            enriched = pd.read_parquet(root / "out/28005/buildings_enriched.parquet")
            self.assertTrue(enriched.building_id.is_unique)
            self.assertIsNone(
                enriched.loc[enriched.building_id.eq("part1"), "recovered_current_use"].iloc[0]
            )
            with self.assertRaises(FileExistsError):
                enrich_municipality("28005", root / "out", accepted, raw)
            self.assertEqual(
                a, enrich_municipality("28005", root / "out", accepted, raw, resume=True)
            )
            self.assertEqual(before, {p: digest(p) for p in before})
            (root / "out/28005/summary.json").write_text("{}")
            with self.assertRaises(ValueError):
                enrich_municipality("28005", root / "out", accepted, raw, resume=True)


if __name__ == "__main__":
    unittest.main()
