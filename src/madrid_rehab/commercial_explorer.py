"""Commercial geography and evidence over a bounded parcel map."""

from .i18n import t, translate, ui as st

from . import (
    commercial_catalog_store as catalog,
    commercial_filters as filters,
    demo,
    production_bundle as bundle,
)
from .commercial_geography import district_names, restrict
from . import energy_scope, neighborhoods
from .commercial_map import GEOMETRY_COLUMNS, parcel_deck
from .map_pagination import PAGE_SIZE, page_count, page_refs, spatial_order
from .municipal_navigation import object_source, picked


def render(code, name, initial_ref=""):
    with st.expander(t("map.filters")):
        district = "all"
        neighborhood = "all"

        def change_district():
            st.session_state["catalog_neighborhood"] = "all"

        if code == "28079":
            names = district_names()
            district = st.selectbox(
                "Distrito",
                ["all", *names],
                key="catalog_district",
                on_change=change_district,
                format_func=lambda c: "Todos los distritos" if c == "all" else names[c],
            )
            if neighborhoods.available():
                neighborhood_names = neighborhoods.names(district)
                if st.session_state.get("catalog_neighborhood", "all") not in {
                    "all",
                    *neighborhood_names,
                }:
                    st.session_state["catalog_neighborhood"] = "all"
                neighborhood = st.selectbox(
                    t("geo.neighborhood"),
                    ["all", *neighborhood_names],
                    key="catalog_neighborhood",
                    disabled=district == "all",
                    format_func=lambda value: t("geo.all_neighborhoods")
                    if value == "all"
                    else neighborhood_names[value],
                    help=t("geo.select_district"),
                )
        scope_key = "energy_scope_" + code
        energy_key = "priority_" + code + "_energy"
        st.session_state.setdefault(scope_key, "any")
        if st.session_state[scope_key] == "all":
            st.session_state[scope_key] = "any"

        def toggle_energy():
            if not st.session_state[energy_key]:
                st.session_state[scope_key] = "any"

        def select_scope():
            if st.session_state[scope_key] != "any":
                st.session_state[energy_key] = True

        selected = []
        help_keys = {"prtr": "filters.prtr_help", "p5": "filters.p5_help"}
        blocked = filters.restricted() if catalog.mode() == "public" else set()
        with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
            for key, label in filters.LABELS.items():
                if st.checkbox(
                    label,
                    key="priority_" + code + "_" + key,
                    on_change=toggle_energy if key == "energy" else None,
                    help=t(help_keys[key]) if key in help_keys else None,
                    disabled=key in blocked,
                ):
                    selected.append(key)
                if key == "energy":
                    with st.popover(t("scope.settings")):
                        st.selectbox(
                            t("scope.settings"),
                            [v for v in energy_scope.OPTIONS if v != "all"],
                            format_func=lambda value: t("scope." + value),
                            key=scope_key,
                            on_change=select_scope,
                        )
        scope = st.session_state[scope_key] if "energy" in selected else "any"
        prtr_program = "any"
        if "prtr" in filters.effective_filters(selected) and catalog.mode() != "public":
            prtr_program = st.selectbox(
                t("prtr.programme"),
                ["any", "P1", "P3", "P4", "P5"],
                format_func=lambda value: t("prtr." + value),
                key="prtr_program_" + code,
            )
        if filters.PRTR_FILTERS.issubset(selected):
            st.caption(t("filters.p5_with_prtr"))
        logic = st.radio(
            "Combinar evidencias",
            ["OR", "AND"],
            horizontal=True,
            format_func=lambda x: "Al menos una (OR)" if x == "OR" else "Todas (AND)",
            key="priority_logic_" + code,
        )

        def reset():
            for key in filters.LABELS:
                st.session_state["priority_" + code + "_" + key] = False
            st.session_state["priority_logic_" + code] = "OR"
            st.session_state["energy_scope_" + code] = "any"
            st.session_state["prtr_program_" + code] = "any"

        st.button("Limpiar filtros", on_click=reset)
    index = restrict(
        filters.query(code, selected, logic, scope=scope, prtr_program=prtr_program), district
    )
    index = neighborhoods.restrict(index, district, neighborhood)
    prefix = (
        "municipal_"
        + code
        + "__cp_catalog_"
        + catalog.mode()
        + "_"
        + filters.context_key(selected, logic)
    )
    context = (code, prefix, district, scope, prtr_program, neighborhood)
    if st.session_state.get("commercial_context") != context:
        previous_context = st.session_state.get("commercial_context")
        previous_prefix = previous_context[1] if previous_context else prefix
        previous_ref = st.session_state.get(previous_prefix + "_selected", "")
        for key in list(st.session_state):
            if key.startswith(prefix + "_"):
                del st.session_state[key]
        if (
            previous_ref
            and previous_context
            and previous_context[0] == code
            and index.parcel_ref14.eq(previous_ref).any()
        ):
            st.session_state[prefix + "_selected"] = previous_ref
        st.session_state["commercial_context"] = context
        st.session_state.pop("fiche_route_origin", None)
    refkey = prefix + "_selected"
    if initial_ref and st.session_state.get(prefix + "_initial") != initial_ref:
        st.session_state[refkey] = initial_ref
        st.session_state[prefix + "_initial"] = initial_ref
    ref = st.session_state.get(refkey, "")
    if ref and not index.parcel_ref14.eq(ref).any():
        st.session_state[refkey] = ref = ""
    st.session_state["fiche_identity"] = None
    st.session_state["fiche_sections"] = {}

    st.metric(t("map.parcel_count"), f"{len(index):,}")
    if selected:
        st.caption(" · ".join(translate(filters.LABELS[key]) for key in selected))
    if index.empty:
        st.info(
            "No hay resultados disponibles para esta combinación. Una fuente no integrada o restringida no acredita ausencia de antecedentes."
        )
        return
    index = spatial_order(index[["parcel_ref14", "x", "y"]])
    page_key = prefix + "_map_page_all"
    pages = page_count(len(index))
    map_page = min(st.session_state.get(page_key, 0), pages - 1)
    if ref:
        positions = index.index[index.parcel_ref14.eq(ref)]
        map_page = int(positions[0]) // PAGE_SIZE
    st.session_state[page_key] = map_page
    refs = page_refs(index, map_page)

    def close_fiche():
        st.session_state[refkey] = ""
        st.session_state.pop("fiche_route_origin", None)

    def move_page(delta):
        st.session_state[page_key] = max(0, min(pages - 1, map_page + delta))
        close_fiche()

    root, relative = object_source(code, "cp")
    frame = demo.read(root, relative, [("parcel_ref14", "in", refs)], columns=GEOMETRY_COLUMNS)
    frame = frame[frame.usable_geometry & frame.parcel_ref14.isin(refs)]
    mapkey = (
        prefix
        + "_map_"
        + district
        + "_"
        + neighborhood
        + "_"
        + scope
        + "_"
        + prtr_program
        + "_"
        + str(map_page)
    )

    def select_map():
        value = picked(st.session_state.get(mapkey), frame.parcel_ref14)
        if value:
            st.session_state[refkey] = value
            st.session_state.pop("fiche_route_origin", None)

    st.html("""<style>
    .st-key-commercial_results [data-testid="stDeckGlJsonChart"] {
        touch-action: none;
        user-select: none;
        -webkit-touch-callout: none;
    }
    @media (max-width: 800px) {
        .st-key-commercial_results :has(> [data-testid="stColumn"]) {
            flex-direction: column;
        }
        .st-key-commercial_results [data-testid="stColumn"] {
            width: 100%; flex: 1 1 auto; min-width: 0;
        }
        .st-key-commercial_pagination button { padding-inline: 0.5rem; }
        .st-key-commercial_map_help { padding-inline-end: 2.25rem; }

    }
    </style>""")
    with st.container(key="commercial_results"):
        if ref:
            map_panel, fiche_panel = st.columns([0.68, 0.32], gap="medium")
        else:
            map_panel = st.container()
        with map_panel:
            if frame.empty:
                st.info(t("ux.no_geometry"))
            else:
                with st.container(key="commercial_map_help"):
                    st.caption(t("map.select_parcel"))
                st.pydeck_chart(
                    parcel_deck(frame, ref),
                    key=mapkey,
                    on_select=select_map,
                    selection_mode="single-object",
                    height=460,
                )
            if pages > 1:
                with st.container(
                    key="commercial_pagination",
                    horizontal=True,
                    horizontal_alignment="center",
                    vertical_alignment="center",
                    gap="small",
                ):
                    st.button(
                        t("map.previous"),
                        key=prefix + "_map_previous",
                        on_click=move_page,
                        args=(-1,),
                        disabled=map_page == 0,
                    )
                    st.markdown(t("map.page", page=map_page + 1, pages=pages), width="content")
                    st.button(
                        t("map.next"),
                        key=prefix + "_map_next",
                        on_click=move_page,
                        args=(1,),
                        disabled=map_page == pages - 1,
                    )
                st.caption(t("map.spatial_pages"))
        if ref:
            with fiche_panel:
                st.subheader("Ficha del inmueble")
                st.button(t("map.close_fiche"), on_click=close_fiche)
                from .commercial_catalog_view import render_fiche

                render_fiche(code, name, ref)
    if catalog.mode() == "public":
        if bundle.active():
            st.caption(t("prtr.bundle_scope" if bundle.allowed_prtr() else "bundle.scope"))
        else:
            st.warning(filters.PUBLIC_BLOCK)
    if "ite" in selected:
        st.info(
            "Obligaciones ITE/IEE y menciones documentadas; no son resultados de inspección ni un diagnóstico del estado actual."
        )
    if code == "28079" and neighborhoods.available():
        st.caption(t("geo.attribution"))
    if code == "28079" and not bundle.active():
        with st.expander("Ver expedientes de Plan Rehabilita"):
            if catalog.mode() == "public":
                st.info("Consulta bloqueada: licencia y redistribución pendientes de verificar.")
            elif st.checkbox("Mostrar consulta de expedientes", key="show_rehabilita_cases"):
                from .plan_rehabilita_view import render as render_cases

                render_cases(show_map=False)
