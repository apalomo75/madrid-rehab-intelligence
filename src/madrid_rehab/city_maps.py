"""Capas escalonadas: 21 distritos o una celda detallada, con selección por identidad."""

import json
import math

import pydeck as pdk
import pandas as pd
from pyproj import Transformer
from shapely.geometry import shape

from .territory import grid_code

from .map_view import map_style, polygon_records
from .territory import CODES

MAX_MAP_UNITS = 2500


def district_selection(event):
    for items in (event or {}).get("selection", {}).get("objects", {}).values():
        for item in items:
            code = item.get("district_code", item.get("properties", {}).get("district_code"))
            if isinstance(code, str) and code in CODES:
                return code
    return None


def unit_selection(event, visible_ids):
    for items in (event or {}).get("selection", {}).get("objects", {}).values():
        for item in items:
            value = item.get("unit_id", item.get("properties", {}).get("unit_id"))
            if isinstance(value, str) and value in visible_ids:
                return value
    return None


def change_district(state, code):
    if code != "all" and code not in CODES:
        raise ValueError("Distrito desconocido")
    if state.get("city_active_district") != code:
        state["city_selected_unit"] = None
        state["city_zone_" + code] = None
        state["city_map_epoch"] = state.get("city_map_epoch", 0) + 1
    state["city_active_district"] = code


def overview_records(boundaries, summary):
    stats = summary.set_index("district_code")
    records = []
    for row in boundaries.itertuples():
        geometry = json.loads(row.geometry_geojson)
        polygons = (
            [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        )
        value = stats.loc[row.district_code]
        coverage = (
            None
            if pd.isna(value.observed_energy_coverage)
            else float(value.observed_energy_coverage)
        )
        for polygon in polygons:
            records.append(
                {
                    "district_code": row.district_code,
                    "district_name": row.district_name,
                    "polygon": polygon,
                    "parcels": int(value.parcels),
                    "energy_parcels": int(value.get("parcels_with_energy", 0)),
                    "bu": int(value.bu_spatial),
                    "records": int(value.ceee_confirmed_records),
                    "coverage_text": "Desconocida" if coverage is None else f"{coverage:.1%}",
                    "color": [145, 153, 165, 135]
                    if coverage is None
                    else [30, int(110 + 100 * coverage), 145, 180],
                }
            )
    return records


def overview_deck(boundaries, summary, urban=False):
    layer = pdk.Layer(
        "PolygonLayer",
        id="city-districts",
        data=overview_records(boundaries, summary),
        get_polygon="polygon",
        get_fill_color="color",
        get_line_color=[255, 255, 255, 255],
        line_width_min_pixels=1.5,
        pickable=True,
        auto_highlight=True,
    )
    return pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(longitude=-3.69, latitude=40.47, zoom=10.3),
        map_provider="carto",
        map_style=map_style(urban),
        height=620,
        tooltip={
            "text": "{district_code} · {district_name}\nParcelas: {parcels}\nBU: {bu}\nCEEE confirmados: {records}\nParcelas con evidencia: {energy_parcels} / {parcels}\nCobertura observada: {coverage_text}"
        },
    )


def cap_units(buildings, parcels, selected=None, maximum=MAX_MAP_UNITS):
    """Límite determinista y explícito; una unidad seleccionada se mantiene si es visible."""
    if maximum < 1:
        raise ValueError("Límite de unidades inválido")
    b = buildings.sort_values("building_id")
    p = parcels.sort_values("record_id")
    candidates = [("bu:" + str(v), "bu", v) for v in b.building_id] + [
        ("cp:" + str(v), "cp", v) for v in p.record_id
    ]
    if selected:
        candidates.sort(key=lambda item: (item[0] != selected, item[0]))
    else:
        candidates.sort(key=lambda item: item[0])
    chosen = candidates[:maximum]
    bids, pids = (
        {v for _, kind, v in chosen if kind == "bu"},
        {v for _, kind, v in chosen if kind == "cp"},
    )
    return b[b.building_id.isin(bids)], p[p.record_id.isin(pids)], len(candidates) > maximum


def detailed_deck(buildings, parcels, district_geometry, zone, selected=None, urban=False):
    records = []
    for item in (
        polygon_records(buildings, selected[3:] if selected and selected.startswith("bu:") else "")
        if not buildings.empty
        else []
    ):
        records.append(
            {
                **item,
                "unit_id": "bu:" + item["building_id"],
                "unit_label": "BU " + item["building_id"],
            }
        )
    for row in parcels.itertuples():
        geometry = json.loads(row.geometry_geojson)
        polygons = (
            [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        )
        for polygon in polygons:
            records.append(
                {
                    "unit_id": "cp:" + row.record_id,
                    "unit_label": "Parcela " + row.parcel_ref14,
                    "polygon": polygon,
                    "color": [70, 120, 200, 25],
                    "certificate_count": row.certificate_count,
                    "line_color": [15, 50, 105, 255]
                    if selected == "cp:" + row.record_id
                    else [80, 110, 150, 180],
                    "line_width": 4 if selected == "cp:" + row.record_id else 1,
                }
            )
    # CP primero, BU después, para permitir seleccionar cuerpos BU sobre sus parcelas.
    records.sort(key=lambda r: r["unit_id"].startswith("bu:"))
    layer = pdk.Layer(
        "PolygonLayer",
        id="city-units",
        data=records,
        get_polygon="polygon",
        get_fill_color="color",
        get_line_color="line_color",
        get_line_width="line_width",
        line_width_units="pixels",
        line_width_min_pixels=0.6,
        pickable=True,
        auto_highlight=True,
    )
    border = pdk.Layer(
        "GeoJsonLayer",
        id="city-district-border",
        data=district_geometry,
        filled=False,
        get_line_color=[30, 55, 95, 200],
        line_width_min_pixels=2,
    )
    if zone:
        x, y = [int(value[1:]) + 250 for value in zone.split("_")]
        lon, lat = Transformer.from_crs(25830, 4326, always_xy=True).transform(x, y)
        view = pdk.ViewState(longitude=lon, latitude=lat, zoom=15.3)
    else:
        west, south, east, north = shape(district_geometry).bounds
        extent = max((east - west) * math.cos(math.radians((south + north) / 2)), north - south)
        view = pdk.ViewState(
            longitude=(west + east) / 2,
            latitude=(south + north) / 2,
            zoom=max(9, min(14, math.log2(360 / max(extent, 0.001)) - 1)),
        )
    return pdk.Deck(
        layers=[border, layer],
        initial_view_state=view,
        map_provider="carto",
        map_style=map_style(urban),
        height=650,
        tooltip={"text": "{unit_label}\nRegistros CEEE en parcela: {certificate_count}"},
    )


TO_WGS84 = Transformer.from_crs(25830, 4326, always_xy=True)
TO_METRIC = Transformer.from_crs(4326, 25830, always_xy=True)


def geographic_zone(longitude, latitude, available):
    """WGS84 lon/lat → ETRS89 UTM30; solo celdas de la partición activa."""
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in [longitude, latitude]):
        return None
    if not (-4.0 <= longitude <= -3.2 and 40.1 <= latitude <= 40.9):
        return None
    x, y = TO_METRIC.transform(longitude, latitude)
    code = grid_code(x, y)
    return code if code in available else None


def zone_records(buildings, parcels):
    """Solo celdas disponibles; recuentos CP/BU separados, no barrios oficiales."""
    b = buildings.groupby("map_zone").size()
    p = parcels.groupby("map_zone").size()
    records = []
    for index, zone in enumerate(sorted(set(b.index) | set(p.index)), 1):
        x, y = [int(v[1:]) for v in zone.split("_")]
        if x % 500 or y % 500:
            raise ValueError("Celda fuera de la malla de 500 m")
        polygon = [
            TO_WGS84.transform(a, c)
            for a, c in [(x, y), (x + 500, y), (x + 500, y + 500), (x, y + 500), (x, y)]
        ]
        records.append(
            {
                "zone_id": zone,
                "zone_label": f"Zona {index}",
                "polygon": polygon,
                "bu_count": int(b.get(zone, 0)),
                "cp_count": int(p.get(zone, 0)),
            }
        )
    return records


def zone_selection(event, available):
    # La identidad devuelta por PolygonLayer evita inferir coordenadas del clic.
    for items in (event or {}).get("selection", {}).get("objects", {}).values():
        for item in items:
            zone = item.get("zone_id")
            if isinstance(zone, str) and zone in available:
                return zone
    return None


def district_deck(geometry, records, urban=False):
    deck = detailed_deck(pd.DataFrame(), pd.DataFrame(), geometry, None, urban=urban)
    deck.layers = [
        deck.layers[0],
        pdk.Layer(
            "PolygonLayer",
            id="district-zones",
            data=records,
            get_polygon="polygon",
            get_fill_color=[30, 145, 150, 65],
            get_line_color=[30, 75, 95, 220],
            line_width_min_pixels=1,
            pickable=True,
            auto_highlight=True,
        ),
    ]
    deck.tooltip = {
        "text": "{zone_label} · 500 m\nCP disponibles: {cp_count}\nBU disponibles: {bu_count}\nHaz clic para explorar"
    }
    return deck
