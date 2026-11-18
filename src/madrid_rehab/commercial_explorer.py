"""Commercial geography, evidence, bounded map and list over one parcel set."""

import math

from .i18n import t, ui as st

from . import commercial_catalog_store as catalog, commercial_filters as filters, demo
from .commercial_geography import district_names, restrict
from . import energy_scope, neighborhoods
from .map_pagination import page_count, page_refs
from .municipal_navigation import PAGE_SIZE, object_source, picked


def render(code, name, initial_ref="", *, district_panel=None, neighborhood_panel=None):
    from .regional_view import geometry_deck

    district = "all"
    neighborhood = "all"

    def change_district():
        st.session_state["catalog_neighborhood"] = "all"

    if code == "28079":
        names = district_names()
        district = (district_panel or st).selectbox(
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
            neighborhood = (neighborhood_panel or st).selectbox(
                t("geo.neighborhood"),
                ["all", *neighborhood_names],
                key="catalog_neighborhood",
                disabled=district == "all",
                format_func=lambda value: t("geo.all_neighborhoods")
                if value == "all"
                else neighborhood_names[value],
                help=t("geo.select_district"),
            )
            st.caption(t("geo.attribution"))
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

    # Visually hide only the settings button's text; its accessible name stays intact.
    st.html("""<style>
    .st-key-ceee_settings button[data-testid="stPopoverButton"] p {
        position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
        overflow: hidden; clip-path: inset(50%); white-space: nowrap; border: 0;
    }
    </style>""")
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
                with st.container(key="ceee_settings", width=42):
                    with st.popover(
                        t("scope.settings"),
                        icon=":material/tune:",
                        use_container_width=False,
                        help=t("scope.settings"),
                    ):
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
        if previous_ref and index.parcel_ref14.iloc[:PAGE_SIZE].eq(previous_ref).any():
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
    st.caption(
        "Se cuentan parcelas catastrales distintas, no necesariamente edificios únicos. Mapa y lista muestran páginas del mismo conjunto."
    )
    if catalog.mode() == "public":
        from . import production_bundle as bundle

        if bundle.active():
            st.caption(t("prtr.bundle_scope" if bundle.allowed_prtr() else "bundle.scope"))
        else:
            st.warning(filters.PUBLIC_BLOCK)
    if "ite" in selected:
        st.info(
            "Obligaciones ITE/IEE y menciones documentadas; no son resultados de inspección ni un diagnóstico del estado actual."
        )
    if index.empty:
        st.metric("Inmuebles encontrados", "0")
        st.info(
            "No hay resultados disponibles para esta combinación. Una fuente no integrada o restringida no acredita ausencia de antecedentes."
        )
        return
    map_panel, fiche_panel = st.columns([0.65, 0.35], gap="medium")
    zone = "all"
    page_key = prefix + "_map_page_" + zone
    pages = page_count(len(index))
    map_page = min(st.session_state.get(page_key, 0), pages - 1)
    if ref:
        # Opening a side-list result moves to its actual map page, without replacing a row.
        positions = index.parcel_ref14.reset_index(drop=True).eq(ref)
        map_page = int(positions[positions].index[0]) // PAGE_SIZE
    st.session_state[page_key] = map_page
    refs = page_refs(index, map_page)

    def move_page(delta):
        target = max(0, min(pages - 1, st.session_state[page_key] + delta))
        st.session_state[page_key] = target
        if st.session_state.get(refkey) not in page_refs(index, target):
            st.session_state[refkey] = ""
            st.session_state.pop("fiche_route_origin", None)

    root, relative = object_source(code, "cp")
    frame = demo.read(root, relative, [("parcel_ref14", "in", refs)])
    frame = frame[frame.usable_geometry & frame.parcel_ref14.isin(refs)].copy()
    frame["unit_id"] = frame.parcel_ref14
    mapkey = prefix + "_map_" + district + "_" + neighborhood + "_" + zone + "_" + str(map_page)

    def select_map():
        value = picked(st.session_state.get(mapkey), frame.unit_id)
        if value:
            st.session_state[refkey] = value
            st.session_state.pop("fiche_route_origin", None)

    with map_panel:
        from .commercial_map import selected_deck

        deck = (
            selected_deck(frame, ref)
            if ref and frame.parcel_ref14.eq(ref).any()
            else geometry_deck(
                frame, "unit_id", 12 if code == "28079" else 13, preserve_geometry=True
            )
            if not frame.empty
            else None
        )
        if deck is None:
            st.info(t("ux.no_geometry"))
        else:
            st.pydeck_chart(
                deck,
                key=mapkey,
                on_select=select_map,
                selection_mode="single-object",
                height=480,
            )
        # Controls belong to the map column and follow the chart immediately.
        with st.container(
            horizontal=True, horizontal_alignment="center", vertical_alignment="center", gap="small"
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
        st.markdown(
            "<p style='text-align:center;font-size:0.85rem'>" + t("map.limit") + "</p>",
            unsafe_allow_html=True,
        )
    with fiche_panel:
        with st.container(height=680, border=False):
            st.metric("Inmuebles encontrados", f"{len(index):,}")
            if not ref or not index.parcel_ref14.eq(ref).any():
                st.subheader("Lista de inmuebles")
                st.session_state.setdefault(
                    prefix + "_list_page", st.session_state.get(prefix + "_saved_page", 0)
                )
                page = st.selectbox(
                    "Página de inmuebles",
                    range(math.ceil(len(index) / 10)),
                    format_func=lambda n: str(n + 1),
                    key=prefix + "_list_page",
                )
                st.session_state[prefix + "_saved_page"] = page
                rows = index.iloc[page * 10 : (page + 1) * 10]
                details = filters.list_details(code, rows.parcel_ref14)

                def open_fiche(identifier):
                    st.session_state[refkey] = identifier
                    st.session_state.pop("fiche_route_origin", None)

                for _, row in rows.iterrows():
                    st.write(
                        filters.result_label(row.parcel_ref14, details[row.parcel_ref14], name)
                    )
                    st.caption(row.parcel_ref14 + " · " + " · ".join(filters.evidence_labels(row)))
                    st.button(
                        "Abrir ficha",
                        key=prefix + "_open_" + row.parcel_ref14,
                        on_click=open_fiche,
                        args=(row.parcel_ref14,),
                    )
            st.session_state["fiche_identity"] = None
            if ref and index.parcel_ref14.eq(ref).any():
                st.subheader("Ficha del inmueble")

                def back():
                    st.session_state[refkey] = ""
                    st.session_state.pop("fiche_route_origin", None)

                st.button("Volver a la lista", on_click=back)
                from .commercial_catalog_view import render_fiche

                render_fiche(code, name, ref)
    from . import production_bundle as bundle

    if code == "28079" and not bundle.active():
        with st.expander("Ver expedientes de Plan Rehabilita"):
            if catalog.mode() == "public":
                st.info("Consulta bloqueada: licencia y redistribución pendientes de verificar.")
            elif st.checkbox("Mostrar consulta de expedientes", key="show_rehabilita_cases"):
                from .plan_rehabilita_view import render as render_cases

                render_cases(show_map=False)
