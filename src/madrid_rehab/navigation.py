"""Welcome and product navigation; local technical routes require an explicit server setting."""

import os

from .i18n import ui as st

HOME = "Inicio"
PRIMARY = ("Explorar inmuebles", "Buscar por dirección", "Acerca del proyecto")
ROUTES = (HOME, *PRIMARY)
POSTAL_WIDGETS = {
    "postal_municipality",
    "postal_street",
    "postal_number",
    "postal_complement",
    "postal_result_choice",
}
TECHNICAL = (
    "Consulta técnica · direcciones",
    "Explorar municipios",
    "Madrid capital",
    "Comunidad de Madrid · Municipios y cobertura",
)


def remember_product_context():
    st.session_state["technical_navigation"] = "Producto"
    previous = st.session_state.get("product_previous_view")
    if previous == PRIMARY[0]:
        st.session_state["explorer_saved_context"] = {
            k: v
            for k, v in st.session_state.items()
            if k.startswith(("catalog_", "priority_", "energy_scope_", "prtr_program_"))
            or k == "commercial_context"
            or (
                k.startswith("municipal_")
                and (k.endswith(("_selected", "_area", "_list_page")) or "_map_page_" in k)
            )
        }
    elif previous == PRIMARY[1]:
        st.session_state["address_saved_widgets"] = {
            k: v
            for k, v in st.session_state.items()
            if k in POSTAL_WIDGETS or k.startswith("postal_cp_")
        }


def open_product(view):
    remember_product_context()
    st.session_state["city_navigation"] = view


def main_view():
    legacy = st.session_state.get("city_navigation")
    if (
        legacy in TECHNICAL
        and os.environ.get("MADRID_REHAB_DEV") == "1"
        and os.environ.get("MADRID_REHAB_PUBLIC") != "1"
    ):
        st.session_state["technical_navigation"] = legacy
    if st.session_state.get("city_navigation") not in ROUTES:
        st.session_state["city_navigation"] = HOME

    view = st.sidebar.radio(
        "Navegación", ROUTES, key="city_navigation", on_change=remember_product_context
    )
    saved = {PRIMARY[0]: "explorer_saved_context", PRIMARY[1]: "address_saved_widgets"}
    if view in saved and st.session_state.get("product_previous_view") != view:
        for key, value in st.session_state.get(saved[view], {}).items():
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
