"""Aplicación local. Lee exclusivamente resultados de la sesión 2, nunca consulta Catastro."""

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import shapely as sh
import streamlit as st
from pyproj import Transformer
from shapely.ops import transform

from madrid_rehab.ingest import digest
from madrid_rehab.map_view import (
    SCOPE_LABELS,
    STATE_LABELS,
    deck,
    display_certificate_table,
    filtered_view,
    selected_building,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "data/processed/session_2"


@st.cache_data(show_spinner="Leyendo el distrito piloto…")
def load_data(root, manifest_hash):
    root = Path(root)
    metadata = json.loads((root / "quality_metrics.json").read_text())
    files = ["pilot_buildings", "pilot_certificates", "building_certificate_contexts", "districts"]
    frames = {}
    for name in files:
        path = root / f"{name}.parquet"
        if digest(path) != metadata["outputs"][path.name]["sha256"]:
            raise ValueError(f"El archivo {name} no coincide con el manifiesto de integración")
        frames[name] = pd.read_parquet(path)
    return frames, metadata


def selection_changed(key, ids):
    identifier = selected_building(st.session_state.get(key), ids)
    # Clic en fondo o deselección nativa no borra la ficha: el usuario tiene un botón explícito.
    if identifier:
        st.session_state.selected_bu = identifier


def clear_selection():
    st.session_state.selected_bu = None
    st.session_state.map_epoch = st.session_state.get("map_epoch", 0) + 1


def detail(row, buildings, certificates, contexts, related):
    st.subheader("Ficha del objeto catastral")
    st.write(f"**Identificador público:** {row.building_id}")
    st.write(f"**Referencia de parcela:** {row.parcel_ref14}")
    st.caption("Chamberí · Madrid · Dirección postal: no disponible en estas tablas BU.")
    st.write(
        f"**Uso declarado:** {'Residencial' if row.current_use == '1_residential' else row.current_use or 'No disponible'}"
    )
    siblings = buildings[buildings.parcel_ref14.eq(row.parcel_ref14)]
    st.write(
        f"**Objetos BU relacionados con la parcela en el piloto:** {siblings.building_id.nunique()}"
    )
    if len(siblings) > 1:
        st.warning(
            "Varios BU comparten parcela. No es posible asignar los certificados a uno de ellos con certeza."
        )
        st.write(", ".join(siblings.building_id))

    def year(value):
        return "No disponible" if pd.isna(value) else str(int(value))

    st.write(
        f"**Periodo constructivo:** {year(row.construction_oldest_year)} – {year(row.construction_newest_year)}"
    )
    st.caption(
        "Años de las unidades más antigua y reciente del agregado BU. No indican reforma ni un año único del bloque."
    )
    st.write(
        f"**Viviendas declaradas:** {row.dwellings_raw or 'No disponible'} · **Unidades declaradas:** {row.building_units_raw or 'No disponible'}"
    )
    st.caption(
        "Una unidad BU no equivale necesariamente a una vivienda. El agregado puede reunir varios cuerpos construidos."
    )
    ids = contexts.loc[contexts.building_id.eq(row.building_id), "certificate_id"]
    full = certificates[certificates.record_id.isin(ids)].drop_duplicates("record_id")
    matching = related[related.building_id.eq(row.building_id)].record_id.nunique()
    st.markdown("**Información energética de la parcela**")
    st.warning(
        "Localización en parcela; correspondencia con el edificio físico no confirmada. Una vivienda o local no califica todo el edificio. Incluso el ámbito «edificio completo» es una declaración del certificado, no una cobertura física verificada."
    )
    st.write(
        f"**{len(full)} registros CEEE disponibles · {matching} cumplen los filtros actuales.**"
    )
    if full.empty:
        st.info(
            "No hay certificados vinculados en esta captura. Esto no demuestra ausencia de certificación energética."
        )
    else:
        counts = full.cal_norenovglobal.value_counts().reindex(list("ABCDEFG"), fill_value=0)
        st.bar_chart(
            counts.rename_axis("Letra del certificado").rename("Registros CEEE"),
            color="#158083",
            height=180,
        )
        missing = (~full.cal_norenovglobal.isin(list("ABCDEFG"))).sum()
        st.caption(
            f"Distribución de todos los registros de la parcela. Sin letra A–G: {missing}. Se conserva el historial; no se elige un certificado vigente."
        )
        st.dataframe(display_certificate_table(full), hide_index=True, width="stretch")
        st.caption(
            "Confirmado en parcela indica coincidencia de referencia oficial; candidato o ambiguo no confirma identidad RC20 ni cobertura física. No se asigna un porcentaje de confianza sin evidencia."
        )
        with st.expander("Procedencia de certificados"):
            for url in sorted({u for values in full.source_urls for u in values}):
                st.link_button("Recurso oficial CEEE", url)
            st.write("Capturas:", sorted(set(full.captured_at)))
    with st.expander("Procedencia catastral y geometría"):
        st.write(
            f"Geometría válida · Cruza límite distrital: {'Sí' if row.crosses_district_boundary else 'No'}"
        )
        st.write(f"Fecha ATOM: {row.source_date} · Captura: {row.captured_at}")
        st.link_button("Fuente oficial BU · archivo municipal", row.source_url)
    st.button("Limpiar selección", on_click=clear_selection, width="stretch")


def main():
    st.set_page_config(page_title="Madrid Rehab Intelligence", page_icon="🏘️", layout="wide")
    st.markdown(
        """<style>
    .block-container {padding-top:2rem; padding-bottom:2rem;}
    [data-testid="stMetricValue"] {font-size:1.65rem;}
    [data-testid="stMetricLabel"] {white-space:normal;}
    [data-testid="stSidebar"] {min-width:320px;}
    </style>""",
        unsafe_allow_html=True,
    )
    st.title("Madrid Rehab Intelligence")
    st.caption("Catastro y energía · Fuentes públicas oficiales · Exploración local")
    root = Path(os.environ.get("MADRID_REHAB_SESSION2_DIR", str(DEFAULT)))
    if not (root / "quality_metrics.json").exists():
        st.error(
            "Faltan los resultados de la sesión 2. Consulta README.md para generarlos en una ruta nueva."
        )
        return
    try:
        frames, metadata = load_data(str(root), digest(root / "quality_metrics.json"))
    except (ValueError, OSError, KeyError) as exc:
        st.error(f"No se pueden leer resultados verificables: {exc}")
        return
    pilot = metadata["pilot"]
    buildings, certificates, contexts = (
        frames[n]
        for n in ["pilot_buildings", "pilot_certificates", "building_certificate_contexts"]
    )
    st.subheader(f"Distrito piloto · {pilot['district_name'].title()}")
    with st.sidebar:
        st.header("Explorar Chamberí")
        mode = st.radio(
            "Modo del mapa", ["Disponibilidad de información", "Exploración energética"]
        )
        urban = st.toggle(
            "Mapa urbano · requiere internet",
            value=os.environ.get("MADRID_REHAB_OFFLINE") != "1",
        )
        st.caption(
            "Desactívalo para explorar sin cartografía externa. Solo se solicitan las teselas de la vista actual."
        )
        residential = st.checkbox("Solo BU de uso residencial declarado", value=True)
        energy = mode == "Exploración energética"
        scope = st.selectbox(
            "Ámbito energético",
            ["all"] + list(SCOPE_LABELS),
            format_func=lambda x: "Todos los ámbitos" if x == "all" else SCOPE_LABELS[x],
            disabled=not energy,
        )
        grade = st.selectbox(
            "Calificación energética del certificado",
            ["all"] + list("ABCDEFG") + ["missing"],
            format_func=lambda x: "Todas las letras"
            if x == "all"
            else "Sin letra"
            if x == "missing"
            else x,
            disabled=not energy,
        )
        years = sorted(
            pd.to_datetime(certificates.certificate_date, errors="coerce")
            .dt.year.dropna()
            .astype(int)
            .unique()
            .tolist()
        )
        year = st.selectbox(
            "Año de la fecha del certificado",
            ["all"] + [str(y) for y in years] + ["missing"],
            format_func=lambda x: "Todos los años"
            if x == "all"
            else "Sin fecha"
            if x == "missing"
            else x,
            disabled=not energy,
        )
        level = st.selectbox(
            "Nivel de vinculación",
            ["parcel_status", "property_status", "physical_status"],
            format_func=lambda x: {
                "parcel_status": "Parcela · localización",
                "property_status": "Inmueble RC20 · identidad",
                "physical_status": "Edificio físico · cobertura",
            }[x],
            disabled=not energy,
        )
        status = st.selectbox(
            "Estado de vinculación",
            ["all"] + list(STATE_LABELS),
            format_func=lambda x: "Todos los estados" if x == "all" else STATE_LABELS[x],
            disabled=not energy,
        )
        include_unlinked = st.checkbox(
            "Incluir elementos sin CEEE vinculados en esta captura", value=True
        )
        st.caption(
            "BU: agregado catastral que puede reunir varios cuerpos construidos. Los colores nunca representan una letra energética del edificio."
        )
    if not energy:
        scope, grade, year, status, level = "all", "all", "all", "all", "parcel_status"
    objects, visible, related = filtered_view(
        buildings,
        certificates,
        contexts,
        scope,
        grade,
        status,
        level,
        include_unlinked,
        residential,
        year,
    )
    ids = set(objects.building_id)
    if st.session_state.get("selected_bu") and st.session_state.selected_bu not in ids:
        clear_selection()
        st.info("La selección se ha limpiado porque el elemento queda fuera de los filtros.")
    explore, analysis, quality = st.tabs(
        ["Explorar mapa", "Análisis energético", "Calidad y metodología"]
    )
    with explore:
        cols = st.columns(3)
        cols[0].metric("Objetos BU representados", f"{len(objects):,}")
        cols[1].metric("CEEE en parcelas mostradas", f"{len(visible):,}")
        cols[2].metric(
            "CEEE confirmados · nivel elegido", f"{int(visible[level].eq('confirmed').sum()):,}"
        )
        st.caption(
            "Registros CEEE únicos, sin multiplicarlos por BU. La captura 2025–2026 no es un censo completo del parque inmobiliario."
        )
        if energy:
            st.caption(
                f"Filtros: letra {'Todas' if grade == 'all' else 'Sin letra' if grade == 'missing' else grade} · ámbito {SCOPE_LABELS.get(scope, 'Todos')} · año {'Todos' if year == 'all' else 'Sin fecha' if year == 'missing' else year} · estado {STATE_LABELS.get(status, 'Todos')}. Los polígonos indican certificados que cumplen estos filtros en su parcela."
            )
        st.markdown(
            "🟢 Confirmados al nivel elegido · 🟠 Información sin confirmación al nivel elegido · ⚪ Sin CEEE vinculados en esta captura · **Contorno azul: selección**"
        )
        if objects.empty:
            st.info(
                "No hay elementos con estos filtros. Prueba otros ámbitos, letras o años, o incluye elementos sin información."
            )
        district = frames["districts"][frames["districts"].district_code.eq(pilot["district_code"])]
        geometry = sh.from_wkt(district.iloc[0].geometry_wkt)
        transformer = Transformer.from_crs(25830, 4326, always_xy=True)
        geo = transform(transformer.transform, geometry.simplify(1, preserve_topology=True))
        district_feature = {
            "type": "Feature",
            "properties": {},
            "geometry": sh.geometry.mapping(geo),
        }
        # Cambiar filtros renueva eventos/índices. Selección propia conserva identidad si sigue visible.
        signature = (
            scope,
            grade,
            year,
            status,
            level,
            include_unlinked,
            residential,
            urban,
            st.session_state.get("map_epoch", 0),
        )
        key = "pilot-map-" + hashlib.sha256(repr(signature).encode()).hexdigest()[:16]
        map_col, panel = st.columns([1.9, 1], gap="large")
        with map_col:
            st.pydeck_chart(
                deck(
                    objects, district_feature, None, urban, st.session_state.get("selected_bu", "")
                ),
                key=key,
                on_select=lambda: selection_changed(key, ids),
                selection_mode="single-object",
            )
            if urban:
                st.caption(
                    "Mapa base: © OpenStreetMap contributors · ODbL. Servicio externo sin garantía de disponibilidad; si no carga, desactiva el mapa urbano."
                )
                st.link_button(
                    "Atribución y licencia OpenStreetMap", "https://www.openstreetmap.org/copyright"
                )
            else:
                st.caption(
                    "Modo sin conexión · Sin teselas, estilos ni fuentes remotas. Navega con arrastre y rueda del ratón."
                )
            st.caption(
                "Contorno del distrito: Ayuntamiento de Madrid · CC BY 4.0. Polígonos: Dirección General del Catastro. Copia visual simplificada a 0,25 m; originales intactos."
            )
            with st.expander("Buscar por identificador público"):
                query = st.text_input("Referencia de parcela o identificador BU")
                matches = (
                    objects[
                        objects.building_id.str.contains(query.strip(), case=False, regex=False)
                        | objects.parcel_ref14.str.contains(query.strip(), case=False, regex=False)
                    ]
                    if query.strip()
                    else objects.iloc[:0]
                )
                if query.strip() and matches.empty:
                    st.info("Sin resultados entre los elementos visibles.")
                for identifier in matches.building_id.head(15):
                    if st.button(identifier, key="search-" + identifier):
                        st.session_state.selected_bu = identifier
                        st.rerun()
        with panel:
            selected = st.session_state.get("selected_bu")
            if selected in ids:
                detail(
                    objects[objects.building_id.eq(selected)].iloc[0],
                    buildings,
                    certificates,
                    contexts,
                    related,
                )
            else:
                st.subheader("Consulta una parcela")
                st.write(
                    "Haz clic sobre un polígono para consultar sus datos y los certificados localizados en su parcela."
                )
                st.info(
                    "La letra de una vivienda o local no califica todo el edificio. Ninguna vinculación al edificio físico está confirmada."
                )
    with analysis:
        st.subheader("Certificados disponibles en Chamberí")
        st.caption(
            "Toda la captura piloto, sin los filtros del mapa. Una fila es una versión de registro CEEE, no un edificio ni necesariamente un certificado administrativo distinto."
        )
        st.metric("Registros CEEE del piloto", f"{len(certificates):,}")
        left, right = st.columns(2)
        with left:
            st.write("**Calificación del certificado · consumo no renovable**")
            counts = certificates.cal_norenovglobal.value_counts().reindex(
                list("ABCDEFG"), fill_value=0
            )
            st.bar_chart(counts.rename("Registros CEEE"), color="#158083")
            st.caption(
                f"Sin letra A–G: {(~certificates.cal_norenovglobal.isin(list('ABCDEFG'))).sum()}"
            )
        with right:
            st.write("**Ámbito declarado**")
            st.bar_chart(
                certificates.certificate_scope.map(SCOPE_LABELS)
                .fillna("Desconocido")
                .value_counts()
                .rename("Registros CEEE")
            )
        dates = pd.to_datetime(certificates.certificate_date, errors="coerce")
        st.write("**Evolución por mes de la fecha declarada**")
        st.bar_chart(
            dates.dropna()
            .dt.to_period("M")
            .astype(str)
            .value_counts()
            .sort_index()
            .rename("Registros CEEE")
        )
        st.caption(
            f"Fechas no disponibles: {dates.isna().sum()}. Evolución de registros disponibles, sin inferir renovaciones o variaciones del parque."
        )
        confirmed = int(certificates.parcel_status.eq("confirmed").sum())
        st.write(
            f"Localización confirmada en parcela: {confirmed:,} / {len(certificates):,} registros del piloto."
        )
        st.caption(
            "Este denominador ya está condicionado por la localización del piloto. La cobertura municipal, incluidos los no localizados, se presenta en metodología."
        )
    with quality:
        st.subheader("Fuentes y límites de interpretación")
        st.write(
            "CEEE: Comunidad de Madrid, recursos 2025 y 2026. Catastro: Dirección General del Catastro. Distritos: Ayuntamiento de Madrid, CC BY 4.0."
        )
        st.write(
            "Tres niveles distintos: parcela (localización), inmueble RC20 (identidad), edificio físico (cobertura). Un BU único por parcela tampoco prueba cobertura física."
        )
        st.write(
            "Se conservan referencias múltiples, duplicidades de origen, versiones históricas, ámbitos desconocidos y geometrías inválidas en las tablas de auditoría. Las geometrías no utilizables se excluyen del mapa."
        )
        st.write("Comparación distrital · recuentos de registros, no edificios certificados")
        st.dataframe(pd.DataFrame(metadata["districts"]), hide_index=True, width="stretch")
        st.write(pilot["method"])
        st.write("Capturas catastrales del piloto:", sorted(set(buildings.captured_at)))
        st.markdown((root / "informe_calidad.md").read_text().split("## Selección")[0])
        with st.expander("Detalle técnico del manifiesto"):
            st.json(metadata)
        st.download_button(
            "Descargar informe de calidad",
            (root / "informe_calidad.md").read_text(),
            file_name="informe_calidad_sesion_2.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
