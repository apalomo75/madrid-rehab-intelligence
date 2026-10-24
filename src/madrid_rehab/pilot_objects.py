"""Adaptación regional optativa: objetos problemáticos conservados y BU/BuildingPart separados."""

import xml.etree.ElementTree as ET
import zipfile

import pandas as pd
import shapely as sh

from .normalize import reference
from .sources import local_name, parse_buildings


def validate_collection_inventory(report):
    """CRC/XML íntegros no acreditan identidades únicas ni cobertura completa."""
    problems = []
    for member in report["members"]:
        if member["root"] != "FeatureCollection":
            continue
        name = member["name"]
        duplicates = sum(member["duplicate_gml_ids"].values())
        if duplicates:
            problems.append(
                f"{name}: {duplicates} gml:id duplicados "
                f"({sum(member['duplicate_feature_ids'].values())} entidades repetidas)"
            )
        observed = member["feature_members"]
        if observed != sum(member["entities"].values()):
            problems.append(f"{name}: miembros y entidades no reconciliados")
        for key in ("numberReturned", "numberOfFeatures"):
            declared = member["header"].get(key)
            if declared is not None and (not declared.isdigit() or int(declared) != observed):
                problems.append(
                    f"{name}: {key} declarado {declared}; observado {observed}; "
                    "integridad de cobertura no demostrada"
                )
        if member["header"].get("next"):
            problems.append(f"{name}: colección paginada pendiente")
    if problems:
        raise ValueError("; ".join(problems))


def validate_readable_objects(frame, kind):
    """No permitir que el modo auditado rebaje errores de identidad o lectura."""
    key = "parcel_id" if kind == "cp" else "building_id"
    if frame.empty or frame[key].isna().any() or not frame[key].is_unique:
        raise ValueError("Colección vacía o identificadores ausentes/duplicados")
    shapes = sh.from_wkt(frame.geometry_wkt.to_numpy(), on_invalid="ignore")
    if sh.is_missing(shapes).any() or sh.is_empty(shapes).any():
        raise ValueError("Geometrías ilegibles o vacías")


def building_rows(path):
    """Lee miembros completos para no perder partes anidadas ni confundir sus atributos."""

    def objects(node, parent=None):
        tag = local_name(node.tag)
        current = parent
        if tag in {"Building", "BuildingPart"}:
            isolated = ET.Element("Building", node.attrib)
            for child in node:
                if not any(local_name(e.tag) in {"Building", "BuildingPart"} for e in child.iter()):
                    isolated.append(child)
            row = parse_buildings(ET.tostring(isolated))[0]
            row["source_feature_type"] = tag
            row["parent_building_id"] = parent
            row["parent_building_href"] = next(
                (
                    e.get("{http://www.w3.org/1999/xlink}href")
                    for e in node
                    if local_name(e.tag) in {"building", "partOf"}
                ),
                None,
            )
            current = row["building_id"]
            yield row
        for child in node:
            yield from objects(child, current)

    with zipfile.ZipFile(path) as archive:
        members = [
            i
            for i in archive.infolist()
            if i.filename.lower().endswith(("building.gml", "buildingpart.gml"))
        ]
        if not members:
            raise ValueError("Faltan capas BU Building/BuildingPart")
        for member in members:
            with archive.open(member) as stream:
                root = None
                count = 0
                for event, element in ET.iterparse(stream, events=("start", "end")):
                    if root is None:
                        root = element
                        if local_name(root.tag) != "FeatureCollection":
                            raise ValueError("BU requiere FeatureCollection")
                        declared = root.get("numberReturned") or root.get("numberOfFeatures")
                    if event == "end" and local_name(element.tag) in {"member", "featureMember"}:
                        count += 1
                        for row in objects(element):
                            yield {**row, "source_gml_member": member.filename}
                        element.clear()
                        root.clear()
                if declared and declared.isdigit() and int(declared) != count:
                    raise ValueError("Recuento de miembros BU no reconciliado")
                if not count:
                    raise ValueError("Capa BU sin miembros: revisar esquema")


def audit_objects(frame, kind, boundary):
    """No elimina filas ni repara geometrías. Los flags determinan su uso en cruce/mapa."""
    key = "parcel_id" if kind == "cp" else "building_id"
    required = {key, "parcel_ref14", "geometry_wkt", "geometry_crs"}
    if frame.empty or not required <= set(frame):
        raise ValueError("Colección vacía o esquema no reconocido")
    frame = frame.copy().reset_index(drop=True)
    frame["source_row"] = frame.index + 1
    frame["reference_raw"] = frame.parcel_ref14
    frame["parcel_ref14"] = frame.reference_raw.map(lambda v: reference(v)["parcel_ref14"])
    frame["source_id_conflict"] = (
        frame[key].isna()
        | frame[key].astype("string").str.strip().eq("").fillna(True)
        | frame[key].duplicated(keep=False)
    )
    shapes = sh.from_wkt(frame.geometry_wkt.to_numpy(), on_invalid="ignore")
    valid = (
        sh.is_valid(shapes)
        & ~sh.is_empty(shapes)
        & (sh.area(shapes) > 0)
        & pd.Series(sh.get_type_id(shapes)).isin([3, 6]).to_numpy()
    )
    boxes = sh.bounds(shapes)
    position = (
        (boxes[:, 0] > 300000)
        & (boxes[:, 2] < 520000)
        & (boxes[:, 1] > 4400000)
        & (boxes[:, 3] < 4600000)
    )
    valid = valid & frame.geometry_crs.eq("EPSG:25830").to_numpy() & position
    frame["geometry_valid"] = valid
    frame["geometry_validity_reason"] = sh.is_valid_reason(shapes)
    for i, col in enumerate(["minx", "miny", "maxx", "maxy"]):
        frame[col] = boxes[:, i]
    ratios = pd.Series(float("nan"), index=frame.index)
    for i in frame.index[valid]:
        ratios.loc[i] = sh.intersection(shapes[i], boundary).area / shapes[i].area
    frame["municipal_overlap_ratio"] = ratios
    frame["boundary_status"] = ratios.map(
        lambda r: "unassessable"
        if pd.isna(r)
        else "inside"
        if r >= 1 - 1e-8
        else "crosses_boundary"
        if r > 0
        else "outside"
    )
    # Objetos que cruzan incluso parcialmente el límite quedan en revisión, sin municipio forzado.
    frame["usable_geometry"] = (
        valid & ~frame.source_id_conflict & frame.boundary_status.eq("inside")
    )
    frame["municipality_assignment_verified"] = frame.usable_geometry
    frame["source_feature_type"] = frame.get(
        "source_feature_type", "CadastralParcel" if kind == "cp" else "Building"
    )
    issues = []
    for row in frame.itertuples():
        flags = []
        if row.source_id_conflict:
            flags.append("source_identity_missing_or_duplicate")
        if row.parcel_ref14 is None:
            flags.append("reference_invalid_or_missing")
        if not row.geometry_valid:
            flags.append("geometry_unusable")
        if row.boundary_status != "inside":
            flags.append("municipal_" + row.boundary_status)
        if flags:
            issues.append(
                dict(source_row=row.source_row, source_id=getattr(row, key), issues=";".join(flags))
            )
    return frame, pd.DataFrame(issues, columns=["source_row", "source_id", "issues"])


def audited_cp_bu_relations(cp, bu):
    from .regional_cadastre import cp_bu_relations

    # Reutilizar el contraste de referencia/geometría existente solo para objetos utilizables.
    eligible_cp = cp[cp.usable_geometry & cp.parcel_ref14.notna()]
    eligible_bu = bu[bu.usable_geometry & bu.parcel_ref14.notna()]
    links = cp_bu_relations(eligible_cp, eligible_bu) if not eligible_bu.empty else pd.DataFrame()
    links = links.to_dict("records")
    counts = cp.dropna(subset=["parcel_ref14"]).groupby("parcel_ref14").size()
    for link in links:
        total = int(counts.get(link["parcel_ref14"], 0))
        if total > 1:
            link.update(cp_rows=total, relation_quality="ambiguous_reference")
        elif total == 1 and link["cp_rows"] == 0:
            link.update(cp_rows=total, relation_quality="unusable_cp")
    represented = set(eligible_bu.source_row)
    for row in bu.itertuples():
        if row.source_row not in represented:
            links.append(
                dict(
                    building_id=row.building_id,
                    parcel_ref14=row.parcel_ref14,
                    cp_rows=0,
                    distance_m=None,
                    relation_quality="unusable_bu"
                    if not row.usable_geometry
                    else "missing_reference",
                )
            )
    return pd.DataFrame(links)
