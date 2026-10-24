"""Selección y presentación sin trasladar calificaciones individuales a geometrías BU."""

import json
import base64

import pandas as pd
import pydeck as pdk
from shapely.geometry import shape

SCOPE_LABELS = {
    "dwelling": "Vivienda",
    "whole_building": "Edificio completo declarado",
    "building_part": "Local / parte de edificio",
    "unknown": "Desconocido",
}
STATE_LABELS = {
    "confirmed": "Confirmado al nivel elegido",
    "candidate": "Candidato",
    "ambiguous": "Ambiguo",
    "unmatched": "Sin correspondencia",
}
COLORS = {
    "confirmed": [21, 128, 131, 185],
    "uncertain": [220, 135, 30, 185],
    "none": [145, 153, 165, 135],
}


def filter_certificates(
    certificates, scope="all", grade="all", status="all", level="parcel_status", year="all"
):
    selected = certificates.copy()
    if scope != "all":
        selected = selected[selected.certificate_scope.eq(scope)]
    if grade != "all":
        selected = selected[selected.cal_norenovglobal.eq("" if grade == "missing" else grade)]
    if year != "all":
        dates = pd.to_datetime(selected.certificate_date, errors="coerce")
        selected = selected[dates.isna() if year == "missing" else dates.dt.year.eq(int(year))]
    if status != "all":
        selected = selected[selected[level].eq(status)]
    return selected


def filtered_view(
    buildings,
    certificates,
    contexts,
    scope="all",
    grade="all",
    status="all",
    level="parcel_status",
    include_unlinked=True,
    residential=True,
    year="all",
):
    objects = buildings.copy()
    if residential:
        objects = objects[objects.current_use.eq("1_residential")]
    # Para el mapa un par certificado-BU se cuenta una sola vez aunque haya varias referencias.
    relations = contexts[["certificate_id", "building_id"]].drop_duplicates()
    full_related = relations.merge(
        certificates, left_on="certificate_id", right_on="record_id", validate="many_to_one"
    )
    selected = filter_certificates(certificates, scope, grade, status, level, year)
    related = relations.merge(
        selected, left_on="certificate_id", right_on="record_id", validate="many_to_one"
    )
    all_ids = set(full_related.building_id)
    selected_ids = set(related.building_id)
    keep = objects.building_id.isin(selected_ids)
    if include_unlinked:
        keep |= ~objects.building_id.isin(all_ids)
    objects = objects[keep].copy()
    counts = related.groupby("building_id").record_id.nunique()
    confirmed = related[related[level].eq("confirmed")].groupby("building_id").record_id.nunique()
    objects["certificate_count"] = objects.building_id.map(counts).fillna(0).astype(int)
    objects["confirmed_count"] = objects.building_id.map(confirmed).fillna(0).astype(int)
    objects["information_state"] = objects.apply(
        lambda r: "confirmed"
        if r.confirmed_count
        else "uncertain"
        if r.certificate_count
        else "none",
        axis=1,
    )
    objects["map_color"] = objects.information_state.map(COLORS)
    visible_certificates = related[related.building_id.isin(objects.building_id)].drop_duplicates(
        "record_id"
    )
    return objects, visible_certificates, related[related.building_id.isin(objects.building_id)]


def features_for_map(frame):
    features = []
    for row in frame.itertuples():
        properties = {
            "building_id": row.building_id,
            "parcel_reference": row.parcel_ref14,
            "certificate_count": row.certificate_count,
            "confirmed_count": row.confirmed_count,
            "color": row.map_color,
            "information": "CEEE en parcela; cobertura del edificio no acreditada"
            if row.certificate_count
            else "Sin CEEE vinculados en esta captura",
        }
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(row.geometry_geojson),
                "properties": properties,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def polygon_records(objects, selected=""):
    """Cada miembro conserva el ID del BU; los anillos interiores siguen siendo huecos.

    PolygonLayer evita identificar subcapas de GeoJsonLayer por índice. El ID público
    viaja en el objeto seleccionado, incluso en agregados con varios polígonos.
    """
    records = []
    for feature in features_for_map(objects)["features"]:
        geometry = feature["geometry"]
        polygons = (
            [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        )
        for polygon in polygons:
            properties = feature["properties"]
            records.append(
                {
                    **properties,
                    "polygon": polygon,
                    "line_color": [14, 50, 105, 255]
                    if properties["building_id"] == selected
                    else [65, 75, 88, 190],
                    "line_width": 4 if properties["building_id"] == selected else 0.6,
                }
            )
    return records


def selected_building(event, visible_ids):
    """Valida identidad del evento contra el conjunto visible, nunca usa un índice."""
    for items in (event or {}).get("selection", {}).get("objects", {}).values():
        for item in items:
            identifier = item.get("building_id", item.get("properties", {}).get("building_id"))
            if identifier in visible_ids:
                return identifier
    return None


def map_style(urban=False):
    style = {
        "version": 8,
        "sources": {},
        "layers": [
            {"id": "background", "type": "background", "paint": {"background-color": "#f4f6f9"}}
        ],
    }
    if urban:
        style["sources"]["osm"] = {
            "type": "raster",
            "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            "tileSize": 256,
            "maxzoom": 19,
            "attribution": '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
        }
        style["layers"].append({"id": "streets", "type": "raster", "source": "osm"})
    return "data:application/json;base64," + base64.b64encode(json.dumps(style).encode()).decode()


def deck(objects, district_feature, center, urban=False, selected=""):
    layer = pdk.Layer(
        "PolygonLayer",
        id="buildings",
        data=polygon_records(objects, selected),
        get_polygon="polygon",
        filled=True,
        stroked=True,
        pickable=True,
        auto_highlight=True,
        get_fill_color="color",
        get_line_color="line_color",
        get_line_width="line_width",
        line_width_units="pixels",
        line_width_min_pixels=0.6,
    )
    border = pdk.Layer(
        "GeoJsonLayer",
        id="district",
        data=district_feature,
        filled=False,
        stroked=True,
        pickable=False,
        get_line_color=[30, 55, 95, 240],
        line_width_min_pixels=3,
    )
    west, south, east, north = shape(district_feature["geometry"]).bounds
    # Vista inicial fija: no depende del tamaño del conjunto filtrado ni de la selección.
    view = pdk.ViewState(
        longitude=(west + east) / 2, latitude=(south + north) / 2, zoom=13.8, pitch=0, bearing=0
    )
    return pdk.Deck(
        layers=[border, layer],
        initial_view_state=view,
        map_provider="carto",
        map_style=map_style(urban),
        height=650,
        tooltip={
            "text": "{building_id}\nParcela: {parcel_reference}\nCEEE en parcela: {certificate_count}\n{information}"
        },
    )


def display_certificate_table(frame):
    columns = [
        "record_id",
        "edif_codreg",
        "edif_refcat",
        "edif_tipo",
        "edif_fecha",
        "cal_norenovglobal",
        "cal_co2global",
        "parcel_status",
        "property_status",
        "physical_status",
        "source_years",
        "edif_superf_numeric",
        "norenov_global_numeric",
        "norenov_co2global_numeric",
    ]
    result = frame[[c for c in columns if c in frame]].copy()
    for column in ["parcel_status", "property_status", "physical_status"]:
        if column in result:
            result[column] = result[column].map(STATE_LABELS)
    return result.rename(
        columns={
            "record_id": "Identificador del registro original",
            "edif_superf_numeric": "Superficie habitable declarada (m²)",
            "norenov_global_numeric": "Consumo no renovable (kWh/m²·año)",
            "norenov_co2global_numeric": "Emisiones (kg CO₂/m²·año)",
            "edif_codreg": "Código de certificado",
            "edif_refcat": "Referencia declarada",
            "edif_tipo": "Ámbito original",
            "edif_fecha": "Fecha declarada",
            "cal_norenovglobal": "Letra energética del certificado",
            "cal_co2global": "Letra emisiones del certificado",
            "parcel_status": "Vínculo de parcela",
            "property_status": "Identidad RC20",
            "physical_status": "Cobertura de edificio físico",
            "source_years": "Recursos de origen",
        }
    )
