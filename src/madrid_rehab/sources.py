"""Adaptadores de muestras CKAN y servicios catastrales documentados."""

import json
import math
import xml.etree.ElementTree as ET

from .http import DownloadError


ETRS89_UTM30_CRS = {
    "EPSG:25830", "EPSG::25830", "urn:ogc:def:crs:EPSG::25830",
    "http://www.opengis.net/def/crs/EPSG/0/25830",
}


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def xml_root(body):
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise ValueError("DTD/entidades no permitidas")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError("XML inválido") from exc
    errors = [e for e in root.iter() if local_name(e.tag) in {"ExceptionText", "ServiceException"}]
    if errors:
        raise ValueError("Excepción OGC: " + "; ".join(e.text or "" for e in errors))
    return root


def first_text(element, name):
    return next((e.text for e in element.iter() if local_name(e.tag) == name and e.text), None)


def energy_sample(client, config):
    limit = config["sample_limit"]
    if not 1 <= limit <= 30:
        raise ValueError("La muestra debe contener entre 1 y 30 filas")
    body = client.get(config["ckan_base"] + "/datastore_search", {
        "resource_id": config["resource_id"], "limit": limit, "offset": 0,
        "sort": "_id asc", "filters": json.dumps(config.get("filters", {})),
    })
    payload = json.loads(body)
    if payload.get("success") is not True:
        raise DownloadError(f"CKAN no confirma success=true: {payload.get('error')}")
    result = payload["result"]
    records = result["records"]
    if not isinstance(records, list) or len(records) > limit:
        raise ValueError("CKAN ignoró el límite o cambió el formato")
    required = {"_id", "edif_refcat", "edif_tipo", "edif_direc", "edif_muni"}
    if any(not required <= row.keys() for row in records):
        raise ValueError("Faltan columnas obligatorias de identidad/ámbito")
    ids = [row["_id"] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("_id repetido en la muestra de origen")
    if ids != sorted(ids):
        raise ValueError("Orden _id no respetado; no usar muestra no determinista")
    return result


def _wfs_params(**extra):
    return {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "srsName": "EPSG::25830", **extra}


def parcel_sample(client, config, ref14):
    return client.get(config["wfs_cp"], _wfs_params(
        STOREDQUERIE_ID="GetParcel", refcat=ref14,
    ))


def building_sample(client, config, ref14):
    return client.get(config["wfs_bu"], _wfs_params(
        STOREDQUERIE_ID="GetBuildingByParcel", refcat=ref14,
    ))


def property_sample(client, config, ref20):
    return client.get(config["dnp_base"], {
        "Provincia": "", "Municipio": "", "RC": ref20,
    })


def parse_parcels(body):
    root = xml_root(body)
    rows = []
    for element in root.iter():
        if local_name(element.tag) != "CadastralParcel":
            continue
        ref = first_text(element, "nationalCadastralReference")
        point = next((e for e in element.iter() if local_name(e.tag) == "referencePoint"), None)
        x = y = crs = None
        if point is not None:
            pos = first_text(point, "pos")
            crs = next((e.attrib["srsName"] for e in point.iter() if "srsName" in e.attrib), None)
            if pos:
                coords = [float(v) for v in pos.split()]
                if len(coords) == 2:
                    x, y = coords
        if crs not in ETRS89_UTM30_CRS:
            x = y = None
        rows.append({"parcel_ref14": ref, "x": x, "y": y,
                     "parcel_id": element.attrib.get("{http://www.opengis.net/gml/3.2}id"),
                     **_building_wkt(element),
                     "coordinate_crs": "EPSG:25830" if x is not None else None,
                     "coordinate_scope": "parcel_reference_point" if x is not None else None})
    # Un HTML de error no debe parecer una respuesta vacía válida.
    if local_name(root.tag) not in {"FeatureCollection", "CadastralParcel"}:
        raise ValueError("La respuesta CP no es una colección GML")
    return rows


def parse_buildings(body):
    root = xml_root(body)
    rows = []
    for element in root.iter():
        if local_name(element.tag) != "Building":
            continue
        ref = first_text(element, "reference")
        local_id = first_text(element, "localId")
        geometry = _building_wkt(element)
        rows.append({
            "building_id": element.attrib.get("{http://www.opengis.net/gml/3.2}id", local_id),
            "parcel_ref14": ref,
            "construction_begin": first_text(element, "beginning"),
            "construction_end": first_text(element, "end"),
            "current_use": first_text(element, "currentUse"),
            "dwellings_raw": first_text(element, "numberOfDwellings"),
            "building_units_raw": first_text(element, "numberOfBuildingUnits"),
            **geometry,
        })
    if local_name(root.tag) not in {"FeatureCollection", "Building"}:
        raise ValueError("La respuesta BU no es una colección GML")
    return rows


def _building_wkt(element):
    """GML 2D Polygon/Surface/MultiSurface; otras geometrías quedan pendientes."""
    unavailable = {"geometry_wkt": None, "geometry_crs": None,
                   "building_geometry_status": "pending_validation"}
    wrapper = next((e for e in element if local_name(e.tag) == "geometry"), None)
    if wrapper is None:
        return unavailable
    crss = {e.attrib["srsName"] for e in wrapper.iter() if "srsName" in e.attrib}
    if not crss or not crss <= ETRS89_UTM30_CRS:
        return unavailable
    if any(e.attrib.get("srsDimension", "2") != "2" for e in wrapper.iter()):
        return unavailable
    patches = [e for e in wrapper.iter() if local_name(e.tag) in {"PolygonPatch", "Polygon"}]
    polygons = []
    for patch in patches:
        if sum(local_name(e.tag) == "exterior" for e in patch) != 1:
            return unavailable
        rings = []
        for kind in ("exterior", "interior"):
            for edge in patch:
                if local_name(edge.tag) != kind:
                    continue
                pos_list = next((e for e in edge.iter() if local_name(e.tag) == "posList"), None)
                if pos_list is None or pos_list.attrib.get("srsDimension", "2") != "2":
                    return unavailable
                try:
                    numbers = [float(n) for n in (pos_list.text or "").split()]
                except ValueError:
                    return unavailable
                if len(numbers) < 8 or len(numbers) % 2 or not all(map(math.isfinite, numbers)):
                    return unavailable
                points = list(zip(numbers[::2], numbers[1::2]))
                if points[0] != points[-1]:
                    return unavailable
                rings.append("(" + ", ".join(f"{x} {y}" for x, y in points) + ")")
        if not rings:
            return unavailable
        polygons.append("(" + ", ".join(rings) + ")")
    if not polygons:
        return unavailable
    return {"geometry_wkt": "MULTIPOLYGON (" + ", ".join(polygons) + ")",
            "geometry_crs": "EPSG:25830", "building_geometry_status": "structural_only"}


def parse_properties(body):
    """Confirma solo una identidad RC20 devuelta explícitamente por DNPRC."""
    root = xml_root(body)
    if local_name(root.tag) != "consulta_dnp":
        raise ValueError("La respuesta no tiene raíz consulta_dnp")
    rows = []
    for element in root.iter():
        if local_name(element.tag) != "rc":
            continue
        parts = [first_text(element, key) for key in ("pc1", "pc2", "car", "cc1", "cc2")]
        if all(parts):
            rows.append({"property_ref20": "".join(parts).upper(), "authority_confirmed": True})
    return rows
