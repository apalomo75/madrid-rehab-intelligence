"""Offline, streaming INSPIRE BU extraction; attributes always stay on their own object."""

import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urlsplit

from .sources import local_name

GML = "{http://www.opengis.net/gml/3.2}"
XLINK = "{http://www.w3.org/1999/xlink}href"
XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
BU_NS = {"http://inspire.jrc.ec.europa.eu/schemas/bu-ext2d/2.0"}
TYPES = {"Building", "BuildingPart", "OtherConstruction"}
RULE = "catastre-attributes-v1"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class SafeStream:
    """Reject declarations even when split across incremental reads; never fetch entities."""

    def __init__(self, source):
        self.source = source
        self.tail = b""

    def read(self, size=-1):
        block = self.source.read(65536 if size < 0 else min(size, 65536))
        scan = (self.tail + block).upper()
        if b"<!DOCTYPE" in scan or b"<!ENTITY" in scan:
            raise ValueError("DTD/entities forbidden")
        self.tail = scan[-16:]
        return block


def iter_features(stream):
    """Yield one feature at a time, releasing the root member after consumption."""
    depth, ordinal, root = 0, 0, None
    for event, node in ET.iterparse(SafeStream(stream), events=("start", "end")):
        if event == "start":
            depth += 1
            if depth == 1:
                root = node
                if node.tag != GML + "FeatureCollection":
                    raise ValueError("Expected GML 3.2 FeatureCollection")
        else:
            if depth == 2:
                if node.tag != GML + "featureMember" or len(node) != 1:
                    raise ValueError("Unexpected top-level feature member")
                feature = node[0]
                if (
                    local_name(feature.tag) not in TYPES
                    or feature.tag.rsplit("}", 1)[0].lstrip("{") not in BU_NS
                ):
                    raise ValueError("Unexpected BU feature type or namespace")
                ordinal += 1
                yield ordinal, feature
                root.remove(node)
            depth -= 1


@dataclass(frozen=True)
class Attribute:
    path: str
    kind: str = "text"
    unit: str | None = None
    known: tuple = ()


ATTRIBUTES = {
    "inspire_local_id": Attribute("inspireId/Identifier/localId"),
    "inspire_namespace": Attribute("inspireId/Identifier/namespace"),
    "inspire_version": Attribute("inspireId/Identifier/versionId"),
    "current_use": Attribute(
        "currentUse",
        known=(
            "1_residential",
            "2_agriculture",
            "3_industrial",
            "4_1_office",
            "4_2_retail",
            "4_3_publicServices",
        ),
    ),
    "construction_begin": Attribute("dateOfConstruction/DateOfEvent/beginning", "date"),
    "construction_end": Attribute("dateOfConstruction/DateOfEvent/end", "date"),
    "dwellings": Attribute("numberOfDwellings", "count"),
    "building_units": Attribute("numberOfBuildingUnits", "count"),
    "floors_above": Attribute("numberOfFloorsAboveGround", "count"),
    "floors_below": Attribute("numberOfFloorsBelowGround", "count"),
    "height_below": Attribute("heightBelowGround", "measure", "m"),
    "height_above": Attribute("heightAboveGround", "measure", "m"),
    "official_area": Attribute("officialArea/OfficialArea/value", "measure", "m2"),
    "official_area_definition": Attribute(
        "officialArea/OfficialArea/officialAreaReference", known=("grossFloorArea",)
    ),
    "condition": Attribute("conditionOfConstruction", known=("functional", "declined", "ruin")),
    "lifespan_begin": Attribute("beginLifespanVersion", "date"),
    "lifespan_end": Attribute("endLifespanVersion", "date"),
    "geometry_accuracy": Attribute(
        "geometry/BuildingGeometry/horizontalGeometryEstimatedAccuracy", "measure", "m"
    ),
    "geometry_reference": Attribute(
        "geometry/BuildingGeometry/horizontalGeometryReference", known=("footPrint",)
    ),
    "reference_geometry": Attribute(
        "geometry/BuildingGeometry/referenceGeometry", known=("true", "false")
    ),
}


def elements(node, path):
    return node.findall("/".join("{*}" + part for part in path.split("/")))


def normalize(raw, spec):
    """A declaration is not automatically a valid or interpreted value."""
    value = raw.strip()
    if not value or value == "-":
        return None, "pending_interpretation"
    if spec.kind == "date":
        if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:Z|[+-]\d\d:\d\d)?", value):
            return None, "invalid"
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None, "invalid"
    if spec.kind in {"count", "measure"}:
        try:
            number = Decimal(value)
            if not number.is_finite() or number < 0:
                return None, "invalid"
            if spec.kind == "count" and number != number.to_integral_value():
                return None, "invalid"
            value = str(int(number)) if spec.kind == "count" else format(number, "f")
        except (InvalidOperation, ValueError, OverflowError):
            return None, "invalid"
    if spec.known and value not in spec.known:
        return None, "pending_interpretation"
    return value, "declared"


def extract_attribute(node, spec):
    found = elements(node, spec.path)
    evidence = []
    for element in found:
        evidence.append(
            dict(
                element_path=spec.path,
                element_qname=element.tag,
                raw_text=element.text,
                xml_attributes=dict(sorted(element.attrib.items())),
            )
        )
    state, value = "absent", None
    if found:
        element = found[0]
        raw = element.text
        if len(found) > 1:
            state = "pending_interpretation"
        elif element.get(XSI_NIL, "false") in {"true", "1"}:
            state = "invalid" if raw and raw.strip() else "present_empty"
        elif raw is None or not raw.strip():
            state = "present_empty"
        else:
            value, state = normalize(raw, spec)
            if state == "declared" and spec.unit and element.get("uom") != spec.unit:
                value, state = None, "pending_interpretation"
    return dict(value=value, state=state, evidence=evidence, rule=RULE)


def parse_feature(node):
    typ = local_name(node.tag)
    if typ not in TYPES:
        raise ValueError("Not a supported BU object")
    if any(local_name(child.tag) in TYPES for c in node for child in c.iter()):
        raise ValueError("Nested BU objects: refuse attribute inheritance")
    attrs = {key: extract_attribute(node, spec) for key, spec in ATTRIBUTES.items()}
    if (
        attrs["official_area"]["state"] == "declared"
        and attrs["official_area_definition"]["value"] != "grossFloorArea"
    ):
        attrs["official_area"].update(value=None, state="pending_interpretation")
    addresses = [
        dict(href=e.get(XLINK), raw_text=e.text, xml_attributes=dict(e.attrib))
        for e in elements(node, "addresses")
    ]
    references = []
    for element in elements(node, "cadastralParcels"):
        href = element.get(XLINK)
        row = dict(
            source_element="cadastralParcels/@xlink:href",
            source_qname=element.tag,
            source_href=href,
            cp_reference_original=None,
            reference_state="unusable",
        )
        if href:
            url = urlsplit(href)
            params = {key.lower(): value for key, value in parse_qs(url.query).items()}
            values = params.get("refcat", [])
            if (
                url.hostname in {"ovc.catastro.meh.es", "www1.sedecatastro.gob.es"}
                and url.path.lower().endswith("/wfscp.aspx")
                and params.get("storedquerie_id") == ["GetParcel"]
                and len(values) == 1
            ):
                row.update(cp_reference_original=values[0], reference_state="explicit")
        references.append(row)
    external = [
        e.text for e in elements(node, "externalReference/ExternalReference/reference") if e.text
    ]
    result = dict(
        building_id=node.get(GML + "id"),
        source_feature_type=typ,
        attributes=attrs,
        documentary_references=references,
        address_references=addresses,
        external_references=external,
    )
    # Retain other nongeometry declarations and attributes without interpreting them.
    extras = []
    for element in node.iter():
        if len(element) == 0 and local_name(element.tag) not in {
            "posList",
            "lowerCorner",
            "upperCorner",
        }:
            extras.append(
                dict(qname=element.tag, raw_text=element.text, xml_attributes=dict(element.attrib))
            )
    result["source_declarations"] = extras
    return result


def flat_attributes(record):
    row = {}
    for key, attr in record["attributes"].items():
        row["recovered_" + key] = attr["value"]
        row["recovered_" + key + "_state"] = attr["state"]
    for key in (
        "attributes",
        "documentary_references",
        "address_references",
        "external_references",
        "source_declarations",
    ):
        row[key + "_json"] = encoded(record[key])
    return row


def finite_ratio(value):
    return float(value) if math.isfinite(value) else None
