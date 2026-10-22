"""Selección y presentación sin trasladar calificaciones individuales a geometrías BU."""

import json
import base64

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
):
    objects = buildings.copy()
    if residential:
        objects = objects[objects.current_use.eq("1_residential")]
    # Para el mapa un par certificado-BU se cuenta una sola vez aunque haya varias referencias.
    relations = contexts[["certificate_id", "building_id"]].drop_duplicates()
    full_related = relations.merge(
        certificates, left_on="certificate_id", right_on="record_id", validate="many_to_one"
    )
    selected = certificates.copy()
    if scope != "all":
        selected = selected[selected.certificate_scope.eq(scope)]
    if grade != "all":
        selected = selected[selected.cal_norenovglobal.eq("" if grade == "missing" else grade)]
    if status != "all":
        selected = selected[selected[level].eq(status)]
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


def deck(objects, district_feature, center):
    layer = pdk.Layer(
        "GeoJsonLayer",
        id="buildings",
        data=features_for_map(objects),
        filled=True,
        stroked=True,
        pickable=True,
        auto_highlight=True,
        get_fill_color="properties.color",
        get_line_color=[65, 75, 88, 160],
        line_width_min_pixels=0.5,
    )
    border = pdk.Layer(
        "GeoJsonLayer",
        id="district",
        data=district_feature,
        filled=False,
        stroked=True,
        pickable=False,
        get_line_color=[55, 75, 100],
        line_width_min_pixels=2,
    )
    west, south, east, north = shape(district_feature["geometry"]).bounds
    view = pdk.data_utils.compute_view([[west, south], [east, north]])
    view.zoom = max(0, view.zoom - 0.3)
    return pdk.Deck(
        layers=[border, layer],
        initial_view_state=view,
        map_provider="carto",
        # Streamlit 1.50 espera una URL de estilo, no un dict. Una data URI mantiene el fondo local.
        map_style="data:application/json;base64,"
        + base64.b64encode(
            json.dumps(
                {
                    "version": 8,
                    "sources": {},
                    "layers": [
                        {
                            "id": "background",
                            "type": "background",
                            "paint": {"background-color": "#f4f6f9"},
                        }
                    ],
                }
            ).encode()
        ).decode(),
        height=600,
        tooltip={
            "text": "{building_id}\nParcela: {parcel_reference}\nCEEE en parcela: {certificate_count}\n{information}"
        },
    )


def display_certificate_table(frame):
    columns = [
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
    ]
    result = frame[[c for c in columns if c in frame]].copy()
    return result.rename(
        columns={
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
