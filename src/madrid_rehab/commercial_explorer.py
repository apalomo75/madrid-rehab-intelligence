"""Commercial geography, evidence, bounded map and list over one parcel set."""

import math

from .i18n import t, ui as st

from . import commercial_catalog_store as catalog, commercial_filters as filters, demo
from .commercial_geography import district_names, restrict
from .municipal_navigation import PAGE_SIZE, object_source, picked


def render(code, name, initial_ref=""):
    from .regional_view import geometry_deck

    district = "all"
    if code == "28079":
        names = district_names()
        district = st.selectbox(
            "Distrito",
            ["all", *names],
            key="catalog_district",
            format_func=lambda c: "Todos los distritos" if c == "all" else names[c],
        )
    selected = []
    for col, (key, label) in zip(st.columns(4), filters.LABELS.items()):
        if col.checkbox(
            label,
            key="priority_" + code + "_" + key,
            help=t("filters.prtr_help") if key == "prtr" else None,
            disabled=catalog.mode() == "public" and key in filters.restricted(),
        ):
            selected.append(key)
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

    st.button("Limpiar filtros", on_click=reset)
    index = restrict(filters.query(code, selected, logic), district)
    prefix = (
        "municipal_"
        + code
        + "__cp_catalog_"
        + catalog.mode()
        + "_"
        + filters.context_key(selected, logic)
    )
    context = (code, prefix, district)
    if st.session_state.get("commercial_context") != context:
        for key in list(st.session_state):
            if key.startswith(prefix + "_"):
                del st.session_state[key]
        st.session_state["commercial_context"] = context
        st.session_state.pop("fiche_route_origin", None)
    refkey = prefix + "_selected"
    if initial_ref and st.session_state.get(prefix + "_initial") != initial_ref:
        st.session_state[refkey] = initial_ref
        st.session_state[prefix + "_initial"] = initial_ref
    ref = st.session_state.get(refkey, "")
    st.session_state["fiche_identity"] = None
    st.session_state["fiche_sections"] = {}
    st.caption(
        "Se cuentan parcelas catastrales distintas, no necesariamente edificios únicos. Mapa y lista muestran páginas del mismo conjunto."
    )
    if catalog.mode() == "public":
        from . import production_bundle as bundle

        if bundle.active():
            st.caption(t("bundle.scope"))
        else:
            st.warning(filters.PUBLIC_BLOCK)
    if "ite" in selected:
        st.info(
            "Obligaciones ITE/IEE y menciones documentadas; no son resultados de inspección ni un diagnóstico del estado actual."
        )
    if index.empty:
        st.info(
            "No hay resultados disponibles para esta combinación. Una fuente no integrada o restringida no acredita ausencia de antecedentes."
        )
        return
    map_panel, fiche_panel = st.columns([0.65, 0.35], gap="medium")
    with map_panel:
        zone = "all"
        with st.expander("Explorar una zona del mapa"):
            zone = st.selectbox(
                "Explorar área",
                ["all", *sorted(index.zone.unique())],
                format_func=lambda z: t("explore.overview")
                if z == "all"
                else t("explore.area_label", area=z),
                key=prefix + "_area",
            )
            st.caption("Áreas de navegación para acotar el mapa; no son barrios oficiales.")
        visible_index = index if zone == "all" else index[index.zone.eq(zone)]
        map_page = st.selectbox(
            "Página del mapa",
            range(math.ceil(len(visible_index) / PAGE_SIZE)),
            format_func=lambda n: str(n + 1),
            key=prefix + "_map_page_" + zone,
        )
    refs = visible_index.parcel_ref14.iloc[
        map_page * PAGE_SIZE : (map_page + 1) * PAGE_SIZE
    ].tolist()
    root, relative = object_source(code, "cp")
    frame = demo.read(root, relative, [("parcel_ref14", "in", refs)])
    frame = frame[frame.usable_geometry & frame.parcel_ref14.isin(refs)].copy()
    frame["unit_id"] = frame.parcel_ref14
    mapkey = prefix + "_map_" + district + "_" + zone + "_" + str(map_page)

    def select_map():
        value = picked(st.session_state.get(mapkey), frame.unit_id)
        if value:
            st.session_state[refkey] = value
            st.session_state.pop("fiche_route_origin", None)

    if ref and ref not in refs and index.parcel_ref14.eq(ref).any():
        extra = demo.read(root, relative, [("parcel_ref14", "==", ref)])
        extra = extra[extra.usable_geometry].copy()
        extra["unit_id"] = extra.parcel_ref14
        import pandas as pd

        frame = pd.concat([frame.iloc[: PAGE_SIZE - 1], extra.iloc[:1]], ignore_index=True)
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
        st.caption(
            f"{len(frame):,} parcelas en esta página del mapa; máximo 500 por carga. La lista permite recorrer todo el conjunto filtrado."
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
                        details[row.parcel_ref14].get("address", "Parcela documentada en " + name)
                    )
                    st.caption(" · ".join(filters.evidence_labels(row)))
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
