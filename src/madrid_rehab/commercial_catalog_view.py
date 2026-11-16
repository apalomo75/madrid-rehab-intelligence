"""Six-city commercial map and gated entry to the existing documentary CP/BU fiche."""

from .i18n import ui as st

from . import commercial_catalog_store as store
from .address_search import NAMES


def render_fiche(code, name, ref, postal=None, objects=None):
    membership = store.parcel(code, ref)
    if membership is None:
        st.info(store.INSUFFICIENT)
        return
    from .municipal_fiche import render_fiche as existing

    existing(code, name, ref, objects, postal=postal, public_catalog=store.mode() == "public")


def render():
    st.title("Explorar inmuebles")
    st.caption(
        "Conoce las características y la información pública disponible sobre los inmuebles de seis municipios."
    )
    try:
        store.metadata()
    except (OSError, ValueError, KeyError) as exc:
        st.error(
            "Catálogo no disponible o incompatible. La consulta completa se conserva en la capa técnica."
        )
        if store.demo.private():
            with st.expander("Detalle del catálogo"):
                st.text(str(exc))
        return
    code = st.selectbox("Municipio", list(NAMES), format_func=NAMES.get, key="catalog_municipality")
    if code != "28079":
        st.caption(
            "Cobertura catastral parcial. Este municipio dispone de mapa de parcelas y sus fichas; no de búsqueda postal fiable."
        )
    from .municipal_navigation import render_explorer

    render_explorer(code, NAMES[code], commercial=True)
    from . import production_bundle as bundle

    if bundle.active():
        from .i18n import t

        st.caption(t("bundle.attribution"))
        st.markdown(t("bundle.licenses"))
        return
    with st.expander("Fuentes y alcance"):
        st.caption(
            "Catastro INSPIRE · Dirección General del Catastro; CEEE · Comunidad de Madrid (CC BY 4.0); "
            "conservación y callejero · Ayuntamiento de Madrid; PRTR · visor de rehabilitación de la Comunidad de Madrid alojado en COAM; "
            "Plan Rehabilita · Ayuntamiento de Madrid, captura local facilitada por el usuario. "
            "Cada ficha detalla procedencia, fecha, ámbito y vínculo. PRTR y Plan Rehabilita: reutilización pendiente de verificar; bloqueados en público."
        )
    if code == "28079" and "city_navigation" in st.session_state:

        def postal_search():
            st.session_state["city_navigation"] = "Buscar por dirección"

        st.button("Buscar por dirección en Madrid", on_click=postal_search)
