"""Aplicación local. Lee exclusivamente resultados de la sesión 2, nunca consulta Catastro."""

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


def main():
    st.set_page_config(page_title="Madrid Rehab Intelligence", page_icon="🏘️", layout="wide")
    root = Path(os.environ.get("MADRID_REHAB_SESSION2_DIR", str(DEFAULT)))
    st.title("Madrid Rehab Intelligence")
    st.caption(
        "Exploración local de Catastro y certificados energéticos · Datos públicos oficiales"
    )
    if not (root / "quality_metrics.json").exists():
        st.error("Faltan los resultados de la sesión 2. Ejecuta el pipeline indicado en README.md.")
        st.code("PYTHONPATH=src .venv/bin/python -m madrid_rehab.session2")
        return
    try:
        frames, metadata = load_data(str(root), digest(root / "quality_metrics.json"))
    except (ValueError, OSError, KeyError) as exc:
        st.error(f"No se pueden leer resultados verificables: {exc}")
        return
    pilot = metadata["pilot"]
    buildings = frames["pilot_buildings"]
    certificates = frames["pilot_certificates"]
    contexts = frames["building_certificate_contexts"]
    st.subheader(f"Distrito piloto · {pilot['district_name'].title()}")
    st.info(
        "Los certificados se localizan en parcelas. La letra de una vivienda o local no califica todo el edificio. Los colores muestran disponibilidad y calidad del vínculo, no eficiencia del BU."
    )
    with st.sidebar:
        st.header("Explorar datos")
        residential = st.checkbox("Solo BU de uso residencial declarado", value=True)
        scope = st.selectbox(
            "Ámbito energético",
            ["all"] + list(SCOPE_LABELS),
            format_func=lambda x: "Todos los ámbitos" if x == "all" else SCOPE_LABELS[x],
        )
        grade = st.selectbox(
            "Calificación energética del certificado",
            ["all"] + list("ABCDEFG") + ["missing"],
            format_func=lambda x: "Todas las letras"
            if x == "all"
            else "Sin letra"
            if x == "missing"
            else x,
        )
        level = st.selectbox(
            "Nivel de vinculación",
            ["parcel_status", "property_status", "physical_status"],
            format_func=lambda x: {
                "parcel_status": "Parcela · localización",
                "property_status": "Inmueble RC20 · identidad",
                "physical_status": "Edificio físico · cobertura",
            }[x],
        )
        status = st.selectbox(
            "Estado de vinculación",
            ["all"] + list(STATE_LABELS),
            format_func=lambda x: "Todos los estados" if x == "all" else STATE_LABELS[x],
        )
        include_unlinked = st.checkbox(
            "Incluir elementos sin CEEE vinculados en esta captura", value=True
        )
        st.caption(
            "Los filtros se aplican a certificados. Los elementos sin información se incluyen aparte; su ausencia en el registro no prueba que carezcan de certificado."
        )
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
    )
    denominator = len(objects)
    with_data = int(objects.certificate_count.gt(0).sum())
    cols = st.columns(5)
    cols[0].metric("Objetos BU representados", f"{len(objects):,}")
    cols[1].metric("CEEE en parcelas mostradas", f"{len(visible):,}")
    cols[2].metric(
        "CEEE confirmados · nivel elegido", f"{int(visible[level].eq('confirmed').sum()):,}"
    )
    cols[3].metric(
        "CEEE ambiguos · nivel elegido", f"{int(visible[level].eq('ambiguous').sum()):,}"
    )
    cols[4].metric(
        "BU con contexto CEEE en parcela",
        f"{100 * with_data / denominator:.1f}%" if denominator else "—",
    )
    st.caption(
        f"Cobertura de contexto: {with_data:,} de {denominator:,} BU representados tienen certificados en su parcela tras los filtros. No es cobertura energética del edificio físico. Certificados contados por registro único, sin multiplicar referencias."
    )
    st.markdown(
        '<span style="color:#158083">●</span> Confirmado al nivel elegido · '
        '<span style="color:#dc871e">●</span> Información sin confirmación al nivel elegido · '
        '<span style="color:#9199a5">●</span> Sin CEEE vinculados en esta captura',
        unsafe_allow_html=True,
    )
    district = frames["districts"][frames["districts"].district_code.eq(pilot["district_code"])]
    geometry = sh.from_wkt(district.iloc[0].geometry_wkt)
    transformer = Transformer.from_crs(25830, 4326, always_xy=True)
    geo = transform(transformer.transform, geometry.simplify(1, preserve_topology=True))
    district_feature = {"type": "Feature", "properties": {}, "geometry": sh.geometry.mapping(geo)}
    center = transformer.transform(
        geometry.representative_point().x, geometry.representative_point().y
    )
    st.pydeck_chart(
        deck(objects, district_feature, center),
        key=f"map-{scope}-{grade}-{level}-{status}-{include_unlinked}-{residential}",
        on_select="ignore",
        selection_mode="single-object",
    )
    st.caption(
        "Geometrías reales · Simplificación de visualización: 0,25 m, conservando topología · Sin mapa base ni consultas externas. Usa el ratón para navegar y el selector inferior para abrir una ficha verificable."
    )
    ids = objects.building_id.tolist()
    if st.session_state.get("object_selector", "") not in [""] + ids:
        st.session_state["object_selector"] = ""
    selected = st.selectbox(
        "Consultar ficha por identificador catastral",
        [""] + ids,
        format_func=lambda v: v or "Selecciona un identificador público para abrir su ficha",
        key="object_selector",
    )
    if selected in ids:
        row = objects[objects.building_id.eq(selected)].iloc[0]
        st.subheader("Ficha del objeto catastral")
        st.write(
            f"**Identificador público:** {row.building_id} · **Parcela declarada:** {row.parcel_ref14}"
        )
        st.write(f"**Uso BU declarado:** {row.current_use or 'No disponible'}")
        oldest = (
            "No disponible"
            if pd.isna(row.construction_oldest_year)
            else str(int(row.construction_oldest_year))
        )
        newest = (
            "No disponible"
            if pd.isna(row.construction_newest_year)
            else str(int(row.construction_newest_year))
        )
        st.write(
            f"**Construcción:** año más antiguo {oldest}; más reciente {newest}. El intervalo agrega las unidades constructivas del BU; no acredita una reforma ni una fecha única del bloque."
        )
        st.write(
            f"**Viviendas declaradas en BU:** {row.dwellings_raw} · **Unidades de edificio declaradas:** {row.building_units_raw}"
        )
        st.caption(
            "BuildingUnit no equivale necesariamente a vivienda. El BU puede reunir varios cuerpos construidos de la parcela."
        )
        st.write(
            f"**Calidad geométrica:** válida para la visualización · **Cruza límites distritales:** {'Sí' if row.crosses_district_boundary else 'No'}"
        )
        st.write(
            f"**Fuente:** Dirección General del Catastro · **Fecha ATOM:** {row.source_date} · **Captura:** {row.captured_at}"
        )
        st.link_button("Consultar fuente oficial BU (archivo municipal)", row.source_url)
        selected_certs = related[related.building_id.eq(selected)].drop_duplicates("record_id")
        st.markdown("**Información energética de la parcela**")
        if selected_certs.empty:
            st.write(
                "No hay certificados vinculados a este objeto en la captura y filtros actuales. No equivale a ausencia de certificado administrativo."
            )
        else:
            st.dataframe(
                display_certificate_table(selected_certs), hide_index=True, width="stretch"
            )
            st.caption(
                "confirmed en parcela solo confirma localización por referencia. candidate en edificio físico no acredita que el certificado cubra esta geometría."
            )
            st.write(
                "Fuentes CEEE:",
                sorted({url for values in selected_certs.source_urls for url in values}),
            )
            st.write("Fechas de captura CEEE:", sorted(set(selected_certs.captured_at)))
    with st.expander("Calidad, comparación distrital y límites de uso"):
        st.dataframe(pd.DataFrame(metadata["districts"]), hide_index=True, width="stretch")
        st.write(pilot["method"])
        st.write(
            "Madrid: confirmaciones de edificio físico:",
            metadata["certificates"]["physical_states"]["confirmed"],
        )
        st.write("Geometrías excluidas y otras incidencias:", metadata["geometry"])
        st.caption(
            "Distritos: Ayuntamiento de Madrid, Departamento de Cartografía, CC BY 4.0. CEEE: Comunidad de Madrid. Catastro: Dirección General del Catastro, Ministerio de Hacienda. Los registros son versiones históricas; no se elige automáticamente un certificado vigente."
        )
        st.download_button(
            "Descargar informe de calidad",
            (root / "informe_calidad.md").read_text(),
            file_name="informe_calidad_sesion_2.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
