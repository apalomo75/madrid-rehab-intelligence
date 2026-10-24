"""Visor de distrito: un producto local y una celda por interacción."""

import hashlib
import json
import os

import pandas as pd
import streamlit as st

from .analysis_view import render_analysis
from .app import detail
from .city_maps import (
    MAX_MAP_UNITS,
    cap_units,
    detailed_deck,
    unit_selection,
    district_deck,
    zone_records,
    zone_selection,
)
from .city_store import load_district, signature
from .map_view import (
    SCOPE_LABELS,
    STATE_LABELS,
    display_certificate_table,
    filter_certificates,
    filtered_view,
)
from .profiles import csv_export


@st.cache_data(show_spinner=False, max_entries=3)
def cached_district(root, code, token):
    return load_district(root, code, token)


def clear_city_selection():
    st.session_state.city_selected_unit = None
    st.session_state.city_map_epoch = st.session_state.get("city_map_epoch", 0) + 1


def select_unit(key, visible, code):
    if st.session_state.get("city_active_district") != code:
        return
    unit = unit_selection(st.session_state.get(key), visible)
    if unit:
        st.session_state.city_selected_unit = unit


def choose_zone(key, available, code):
    if st.session_state.get("city_active_district") != code:
        return
    zone = zone_selection(st.session_state.get(key), available)
    if zone:
        jump_to_unit(None, zone, code)


def district_home(code):
    jump_to_unit(None, None, code)


def reset_filters(code):
    defaults = {
        "residential": True,
        "scope": "all",
        "grade": "all",
        "level": "parcel_status",
        "status": "all",
        "year": "all",
        "unlinked": True,
        "show_bu": True,
        "show_cp": True,
    }
    for key, value in defaults.items():
        st.session_state[key + "_" + code] = value
    clear_city_selection()


def jump_to_unit(unit, zone, code):
    st.session_state["city_zone_" + code] = zone
    st.session_state.city_selected_unit = unit
    st.session_state.city_map_epoch = st.session_state.get("city_map_epoch", 0) + 1


def parcel_objects(
    parcels, certificates, links, selected, level, include_unlinked, residential_refs=None
):
    objects = parcels.copy()
    if residential_refs is not None:
        objects = objects[objects.parcel_ref14.isin(residential_refs)]
    relation = links[["certificate_id", "parcel_ref14"]].drop_duplicates()
    full = relation[relation.certificate_id.isin(certificates.record_id)]
    selected_links = relation.merge(
        selected[["record_id", level]],
        left_on="certificate_id",
        right_on="record_id",
        validate="many_to_one",
    )
    available = set(full.parcel_ref14)
    matches = set(selected_links.parcel_ref14)
    keep = objects.parcel_ref14.isin(matches)
    if include_unlinked:
        keep |= ~objects.parcel_ref14.isin(available)
    objects = objects[keep].copy()
    counts = selected_links.groupby("parcel_ref14").record_id.nunique()
    objects["certificate_count"] = objects.parcel_ref14.map(counts).fillna(0).astype(int)
    return objects


def parcel_detail(row, certificates, links):
    st.subheader("Ficha de parcela catastral")
    st.markdown("**A. Identificación · parcela CP**")
    st.write(
        f"**RC14:** {row.parcel_ref14} · Distrito: {getattr(row, 'district_code', 'No disponible')}"
    )
    st.markdown("**B. Características constructivas**")
    st.caption(
        "No declaradas en la tabla CP. Selecciona un BU para consultar uso, periodo y unidades de los registros disponibles."
    )
    st.markdown("**C. Información energética**")
    st.caption(f"Fila CP: {row.record_id}. La referencia puede tener varias filas en la captura.")
    if getattr(row, "cp_rows", 1) > 1:
        st.warning(
            f"Esta RC tiene {int(row.cp_rows)} filas CP en la captura municipal; identidad ambigua."
        )
    st.write(f"Cruza límite distrital: {'Sí' if row.crosses_district_boundary else 'No'}")
    ids = links.loc[links.parcel_ref14.eq(row.parcel_ref14), "certificate_id"]
    full = certificates[certificates.record_id.isin(ids)].drop_duplicates("record_id")
    st.warning(
        "Los certificados se localizan en parcela y conservan sus estados. No califican el edificio físico ni todas sus viviendas."
    )
    st.write(
        f"{len(full):,} registros CEEE disponibles en la parcela, sin aplicar filtros del mapa."
    )
    if full.empty:
        st.info("Sin registros vinculados en esta captura; no demuestra ausencia real.")
    else:
        st.dataframe(display_certificate_table(full), hide_index=True, width="stretch")
    st.markdown("**D. Calidad y limitaciones**")
    st.caption(f"Captura CP: {row.captured_at}; fuente: {row.source_date}")
    st.link_button("Fuente oficial CP", row.source_url)
    st.button("Limpiar selección", on_click=clear_city_selection, width="stretch")


def render_district(root, code, overview):
    metadata = overview["manifest"]
    if code not in metadata["available_districts"]:
        st.info(
            "Este distrito no se generó en esta ejecución. Ejecuta la CLI con --district all en otra salida."
        )
        return
    try:
        data = cached_district(str(root), code, signature(root, code))
    except (ValueError, OSError, KeyError) as exc:
        st.error(f"No se puede leer el distrito: {exc}")
        return
    buildings, parcels, certificates, contexts, links = (
        data[name]
        for name in [
            "map_buildings.parquet",
            "map_parcels.parquet",
            "certificates.parquet",
            "contexts.parquet",
            "links.parquet",
        ]
    )
    name = data["manifest"]["district_name"]
    st.subheader(f"Distrito {code} · {name}")
    map_tab, analysis_tab = st.tabs(["Mapa y ficha", "Análisis del distrito"])
    with st.sidebar:
        st.header("Ubicación")
        st.button("Ver distrito completo", on_click=district_home, args=(code,))
        urban = st.toggle(
            "Mapa urbano · requiere internet",
            value=os.environ.get("MADRID_REHAB_OFFLINE") != "1",
            key="urban_" + code,
        )
        st.subheader("Filtros principales")
        st.button("Restablecer filtros", on_click=reset_filters, args=(code,))
        residential = st.checkbox(
            "Solo BU de uso residencial declarado", value=True, key="residential_" + code
        )
        st.subheader("Filtros energéticos")
        scopes = st.selectbox(
            "Ámbito energético",
            ["all"] + list(SCOPE_LABELS),
            format_func=lambda x: SCOPE_LABELS.get(x, "Todos"),
            key="scope_" + code,
        )
        grade = st.selectbox(
            "Calificación energética del certificado",
            ["all"] + list("ABCDEFG") + ["missing"],
            key="grade_" + code,
            format_func=lambda x: {"all": "Todos", "missing": "Sin letra"}.get(x, x),
        )
        with st.expander("Opciones avanzadas · correspondencia"):
            level = st.selectbox(
                "Nivel de vinculación",
                ["parcel_status", "property_status", "physical_status"],
                key="level_" + code,
                format_func=lambda x: {
                    "parcel_status": "Parcela · localización",
                    "property_status": "Inmueble RC20 · identidad",
                    "physical_status": "Edificio físico · cobertura",
                }[x],
            )
            status = st.selectbox(
                "Estado de vinculación",
                ["all"] + list(STATE_LABELS),
                key="status_" + code,
                format_func=lambda x: STATE_LABELS.get(x, "Todos"),
            )
        years = sorted(
            pd.to_datetime(certificates.certificate_date, errors="coerce")
            .dt.year.dropna()
            .astype(int)
            .unique()
        )
        year = st.selectbox(
            "Año de la fecha del certificado",
            ["all"] + [str(y) for y in years] + ["missing"],
            key="year_" + code,
            format_func=lambda x: {"all": "Todos", "missing": "Sin fecha"}.get(x, x),
        )
        include_unlinked = st.checkbox(
            "Incluir unidades sin CEEE vinculados", value=True, key="unlinked_" + code
        )
        show_bu = st.checkbox("Mostrar objetos BU", value=True, key="show_bu_" + code)
        show_cp = st.checkbox("Mostrar parcelas CP", value=True, key="show_cp_" + code)
        zones = sorted(set(buildings.map_zone) | set(parcels.map_zone))
        # La vista inicial abarca todo el distrito. El selector técnico queda como alternativa.
        unit = st.session_state.get("city_selected_unit")
        if unit and not st.session_state.get("city_zone_" + code):
            matches = (
                buildings[buildings.building_id.eq(unit[3:])]
                if unit.startswith("bu:")
                else parcels[parcels.record_id.eq(unit[3:])]
            )
            if not matches.empty:
                st.session_state["city_zone_" + code] = matches.iloc[0].map_zone
        with st.expander("Opciones avanzadas · celda técnica"):
            zone = st.selectbox(
                "Detalle por malla de 500 m (no barrios)",
                [None] + zones,
                format_func=lambda x: x or "Distrito completo · elegir zona en el mapa",
                key="city_zone_" + code,
            )
        query = st.text_input("Buscar referencia o BU en todo el distrito", key="search_" + code)
        if query.strip():
            found_b = buildings[
                buildings.building_id.str.contains(query.strip(), regex=False, case=False)
                | buildings.parcel_ref14.str.contains(query.strip(), regex=False, case=False)
            ]
            found_p = parcels[
                parcels.parcel_ref14.str.contains(query.strip(), regex=False, case=False)
            ]
            if found_b.empty and found_p.empty:
                st.info("Sin coincidencias en este distrito.")
            for row in found_b.head(5).itertuples():
                st.button(
                    "BU " + row.building_id,
                    key="found_b_" + row.record_id,
                    on_click=jump_to_unit,
                    args=("bu:" + row.building_id, row.map_zone, code),
                )
            for row in found_p.head(5).itertuples():
                st.button(
                    "CP " + row.parcel_ref14,
                    key="found_p_" + row.record_id,
                    on_click=jump_to_unit,
                    args=("cp:" + row.record_id, row.map_zone, code),
                )
    active = sum(
        [
            residential,
            scopes != "all",
            grade != "all",
            status != "all",
            level != "parcel_status",
            year != "all",
            not include_unlinked,
        ]
    )
    st.sidebar.caption(
        f"{active} filtros activos · combinación AND" if active else "Sin filtros activos"
    )
    selected = filter_certificates(certificates, scopes, grade, status, level, year)
    filtered_b, visible_certificates, related = filtered_view(
        buildings,
        certificates,
        contexts,
        scopes,
        grade,
        status,
        level,
        include_unlinked,
        residential,
        year,
    )
    residential_refs = (
        set(buildings.loc[buildings.current_use.eq("1_residential"), "parcel_ref14"])
        if residential
        else None
    )
    filtered_p = parcel_objects(
        parcels, certificates, links, selected, level, include_unlinked, residential_refs
    )
    zone_b, zone_p = (
        filtered_b[filtered_b.map_zone.eq(zone)],
        filtered_p[filtered_p.map_zone.eq(zone)],
    )
    if not show_bu:
        zone_b = zone_b.iloc[:0]
    if not show_cp:
        zone_p = zone_p.iloc[:0]
    zone_b, zone_p, capped = cap_units(zone_b, zone_p, st.session_state.get("city_selected_unit"))
    visible = {"bu:" + v for v in zone_b.building_id} | {"cp:" + v for v in zone_p.record_id}
    if st.session_state.get("city_selected_unit") not in visible:
        st.session_state.city_selected_unit = None
    with map_tab:
        a, b, c = st.columns(3)
        a.metric("BU del distrito tras filtros", len(filtered_b))
        b.metric("Parcelas CP tras filtros", len(filtered_p))
        c.metric("Unidades dibujadas en celda", len(zone_b) + len(zone_p))
        st.caption(
            f"Detalle de una celda de 500 m, no todo el distrito. Tope {MAX_MAP_UNITS:,} unidades. "
            "Usa «Ver distrito completo» para elegir otra zona o busca una referencia. CP y BU son unidades distintas."
        )
        if zone is not None and zone_b.empty and zone_p.empty:
            st.info("No hay unidades visibles en esta zona con los filtros actuales.")
        if capped:
            st.info(
                "La celda supera el límite de dibujo. Se muestra un subconjunto determinista; los indicadores de distrito conservan todo el filtro."
            )
        boundary = overview["districts.parquet"].set_index("district_code").loc[code]
        geometry = json.loads(boundary.geometry_geojson)
        key = (
            "district-map-"
            + hashlib.sha256(
                repr(
                    (
                        code,
                        zone,
                        scopes,
                        grade,
                        status,
                        level,
                        year,
                        residential,
                        show_bu,
                        show_cp,
                        include_unlinked,
                        st.session_state.get("city_map_epoch", 0),
                    )
                ).encode()
            ).hexdigest()[:20]
        )
        if zone is None:
            st.info(
                "Elige una zona de 500 m en el mapa para cargar sus parcelas y objetos BU. Las zonas no son barrios oficiales."
            )
            zone_key = f"district-zones-{code}-{st.session_state.get('city_map_epoch', 0)}"
            records = zone_records(buildings, parcels)
            st.pydeck_chart(
                district_deck(geometry, records, urban),
                key=zone_key,
                on_select=lambda: choose_zone(zone_key, zones, code),
                selection_mode="single-object",
            )
            st.caption(
                "Zonas disponibles en la captura, antes de filtros. CP y BU se cuentan por separado. "
                "© OpenStreetMap contributors · ODbL si está activado."
            )
        map_col, panel = st.columns([2, 1])
        if zone is not None:
            with map_col:
                st.pydeck_chart(
                    detailed_deck(
                        zone_b,
                        zone_p,
                        geometry,
                        zone,
                        st.session_state.get("city_selected_unit"),
                        urban,
                    ),
                    key=key,
                    on_select=lambda: select_unit(key, visible, code),
                    selection_mode="single-object",
                )
                st.caption(
                    "CP: contornos azules; BU: relleno de disponibilidad, nunca letra energética del edificio. "
                    "© OpenStreetMap contributors · ODbL si está activado. Catastro: DGC. Límites: Ayuntamiento de Madrid · CC BY 4.0."
                )
        with panel:
            unit = st.session_state.get("city_selected_unit")
            if unit and unit.startswith("bu:"):
                detail(
                    buildings[buildings.building_id.eq(unit[3:])].iloc[0],
                    buildings,
                    certificates,
                    contexts,
                    related,
                    district_name=name,
                    clear_callback=clear_city_selection,
                )
            elif unit and unit.startswith("cp:"):
                parcel_detail(parcels[parcels.record_id.eq(unit[3:])].iloc[0], certificates, links)
            elif zone is not None:
                st.info(
                    "Selecciona una parcela CP u objeto BU en la celda. Desactiva BU para acceder a los contornos CP que cubre."
                )
        st.sidebar.subheader("Exportación")
        st.sidebar.download_button(
            "Exportar CEEE tras filtros del distrito",
            csv_export(selected),
            file_name=f"ceee_{code}.csv",
            mime="text/csv",
        )
    with analysis_tab:
        render_analysis(root / "districts" / code, key_prefix="district-" + code)
