"""Six-city commercial map and gated entry to the existing documentary CP/BU fiche."""

import streamlit as st

from . import commercial_catalog_store as store
from .address_search import NAMES


def render_fiche(code, name, ref, postal=None, objects=None):
    membership = store.parcel(code, ref)
    if membership is None:
        st.info(store.INSUFFICIENT)
        return
    st.caption(
        "Nivel de la parcela de origen: "
        + membership[store.mode() + "_level"]
        + ". Ámbitos documentales; no diagnóstico del edificio."
    )
    from .municipal_fiche import render_fiche as existing

    existing(code, name, ref, objects, postal=postal, public_catalog=store.mode() == "public")


def render():
    st.title("Mapa comercial · inmuebles documentados")
    st.caption(
        "Parcelas con evidencia verificable para investigar. Una parcela no equivale a un edificio o comunidad; no se calcula necesidad de rehabilitación."
    )
    st.caption(
        "Fuentes: Catastro INSPIRE · Dirección General del Catastro; CEEE · Comunidad de Madrid (CC BY 4.0); "
        "conservación y callejero · Ayuntamiento de Madrid; PRTR · visor de rehabilitación de la Comunidad de Madrid alojado en COAM; "
        "Plan Rehabilita · Ayuntamiento de Madrid, captura local facilitada por el usuario. Cada ficha detalla procedencia, fecha, ámbito y vínculo."
    )
    try:
        store.metadata()
    except (OSError, ValueError, KeyError) as exc:
        st.error(
            "Catálogo no disponible o incompatible. La consulta completa se conserva en la capa técnica."
        )
        with st.expander("Detalle del catálogo"):
            st.text(str(exc))
        return
    code = st.selectbox("Municipio", list(NAMES), format_func=NAMES.get, key="catalog_municipality")
    if code != "28079":
        st.caption(
            "Cobertura catastral parcial. Este municipio dispone de mapa de parcelas y navegación CP/BU; no de búsqueda postal fiable."
        )
    from .municipal_navigation import render_explorer

    render_explorer(code, NAMES[code], commercial=True)
