"""Three product entries; local technical routes require an explicit server setting."""

import os

from .i18n import ui as st

PRIMARY = ("Explorar inmuebles", "Buscar por dirección", "Acerca del proyecto")
TECHNICAL = (
    "Consulta técnica · direcciones",
    "Explorar municipios",
    "Madrid capital",
    "Comunidad de Madrid · Municipios y cobertura",
)


def main_view():
    legacy = st.session_state.get("city_navigation")
    if (
        legacy in TECHNICAL
        and os.environ.get("MADRID_REHAB_DEV") == "1"
        and os.environ.get("MADRID_REHAB_PUBLIC") != "1"
    ):
        st.session_state["technical_navigation"] = legacy
    if st.session_state.get("city_navigation") not in PRIMARY:
        st.session_state["city_navigation"] = PRIMARY[0]

    def remember():
        if st.session_state.get("product_previous_view") != PRIMARY[0]:
            return
        st.session_state["explorer_saved_context"] = {
            k: v
            for k, v in st.session_state.items()
            if k.startswith(("catalog_", "priority_"))
            or k == "commercial_context"
            or (
                k.startswith("municipal_")
                and (k.endswith(("_selected", "_area", "_list_page")) or "_map_page_" in k)
            )
        }

    view = st.sidebar.radio("Navegación", PRIMARY, key="city_navigation", on_change=remember)
    if view == PRIMARY[0] and st.session_state.get("product_previous_view") != view:
        for key, value in st.session_state.get("explorer_saved_context", {}).items():
            st.session_state[key] = value
    st.session_state["product_previous_view"] = view
    if os.environ.get("MADRID_REHAB_DEV") == "1" and os.environ.get("MADRID_REHAB_PUBLIC") != "1":
        with st.sidebar.expander("Herramientas de desarrollo"):
            route = st.selectbox(
                "Consulta técnica", ("Producto", *TECHNICAL), key="technical_navigation"
            )
        if route != "Producto":
            return route
    return view
