"""One commercial search route, independent of spatial navigation."""

import json

from .i18n import t, ui as st

from . import address_search as postal

LABELS = {
    "confirmed": "Vínculo documental confirmado a parcela",
    "ambiguous": "Relación ambigua · requiere revisión",
    "unlinked": "Sin parcela confirmada en las fuentes integradas",
}


def clear():
    for key in list(st.session_state):
        if key.startswith("postal_") and key != "postal_municipality":
            del st.session_state[key]


def render(*, technical=False):
    st.title("Buscar un inmueble por dirección")
    if technical:
        st.caption("Consulta técnica completa: incluye registros excluidos del catálogo comercial.")
    st.caption(t("ux.search_help"))
    try:
        meta = postal.metadata()
    except Exception as exc:
        st.error(
            "Índice postal no disponible o incompatible. Regenere el índice según la documentación."
        )
        if postal.demo.private():
            st.caption(str(exc))
        return
    code = st.selectbox(
        "Municipio",
        list(postal.NAMES),
        format_func=postal.NAMES.get,
        key="postal_municipality",
        on_change=clear,
    )
    coverage = meta["municipalities"][code]
    from . import grant_address_search as grant_addresses

    case_search = (
        not technical and not coverage["indexed_addresses"] and bool(grant_addresses.index(code))
    )
    if case_search:
        st.info(t("postal.case_coverage"))
    elif not coverage["indexed_addresses"]:
        st.warning(
            "Este municipio no dispone de calles y números recuperables en las fuentes locales integradas. "
            "Se necesita una fuente postal oficial adicional. Puede seguir explorando sus parcelas y construcciones desde Explorar municipios."
        )
    with st.form("postal_search_form"):
        st.text_input(
            "Calle o dirección", key="postal_street", placeholder="Por ejemplo: Calle Bailén 12"
        )
        st.text_input("Número", key="postal_number")
        if technical:
            st.text_input("Complemento (opcional)", key="postal_complement")
        submitted = st.form_submit_button("Buscar", type="primary")
    st.button("Limpiar búsqueda", on_click=clear)
    if submitted:
        st.session_state["postal_query"] = (
            code,
            st.session_state.postal_street,
            st.session_state.postal_number,
            st.session_state.get("postal_complement", "") if technical else "",
        )
        st.session_state["postal_page"] = 0
        st.session_state.pop("postal_open", None)
        st.session_state.pop("postal_result_choice", None)
        st.session_state.pop("postal_dismissed", None)
    query = st.session_state.get("postal_query")
    if not query or query[0] != code:
        return
    try:
        page = st.session_state.get("postal_page", 0)
        if technical:
            rows, total = postal.search(*query, offset=page * 100)
            located = total > 0
        elif case_search:
            rows, total = grant_addresses.search(*query, offset=page * 100)
            located = total > 0
        else:
            from . import commercial_catalog_store as catalog

            rows, total, located = catalog.search(*query, offset=page * 100)
    except (OSError, KeyError, ValueError) as exc:
        st.warning(str(exc))
        return
    if not total:
        if case_search:
            st.info(t("postal.case_no_result"))
            return
        if located and not technical:
            st.info(catalog.INSUFFICIENT)
            return
        st.info("No hemos encontrado esta dirección en las fuentes integradas.")
        suggestions = (
            postal.suggest(code, query[1]) if technical else catalog.suggest(code, query[1])
        )
        if suggestions:
            st.write("Vías documentadas que comienzan así: " + " · ".join(suggestions))
        return
    st.write(
        t(
            "postal.one_match" if total == 1 else "postal.matches",
            total=total,
            page=page + 1,
            pages=(total + 99) // 100,
        )
    )
    if total > 100:

        def change_page(delta):
            st.session_state["postal_page"] += delta
            st.session_state.pop("postal_result_choice", None)
            st.session_state.pop("postal_open", None)

        left, right = st.columns(2)
        left.button("Resultados anteriores", disabled=page == 0, on_click=change_page, args=(-1,))
        right.button(
            "Más resultados", disabled=(page + 1) * 100 >= total, on_click=change_page, args=(1,)
        )
    lookup = {r["id"]: r for r in rows}

    def label(uid):
        r = lookup[uid]
        return r["original"] if case_search else f"{r['original']} · {postal.NAMES[code]}"

    choice = st.selectbox(
        "Seleccione la dirección correcta",
        list(lookup),
        index=None,
        format_func=label,
        key="postal_result_choice",
    )
    if choice is None:
        st.caption(
            "Seleccione expresamente una coincidencia; no se abre la primera automáticamente."
        )
        return
    row = lookup[choice]
    if case_search:
        render_result(code, choice, row["reference"], technical=False)
        return
    if technical:
        render_postal_details(row)
    if row["status"] != "confirmed":
        st.warning(
            LABELS[row["status"]] + ". No se puede abrir una ficha con identidad confirmada."
        )
        with st.expander("Procedencia y motivo de revisión"):
            st.write(row["reason"])
            st.write("Fuente SHA-256: " + row["source_sha256"])
            st.write("Referencias candidatas (sin confirmar): " + row["candidates"])
        return
    refs = json.loads(row["refs"])
    ref = (
        refs[0]
        if len(refs) == 1
        else st.selectbox(
            "Seleccione la parcela vinculada", refs, index=None, key="postal_cp_" + choice
        )
    )
    if len(refs) > 1:
        st.warning(
            "Este acceso tiene varias parcelas vinculadas. Sus atributos y expedientes se consultan por separado."
        )
    render_result(code, choice, ref, row=row, technical=technical)


def render_postal_details(row):
    with st.expander(t("ux.postal_details")):
        st.json(
            {
                key: row.get(key)
                for key in (
                    "id",
                    "access_id",
                    "access_type",
                    "source_row",
                    "source_sha256",
                    "original",
                    "refs",
                    "status",
                )
            }
        )


def render_result(code, choice, ref, *, row=None, technical=False):
    if st.button("Abrir ficha del inmueble", disabled=ref is None, type="primary"):
        st.session_state["postal_open"] = (choice, ref)
        st.session_state["fiche_route_" + "_".join((code, "cp", ref))] = ("cp", ref)
    opened = st.session_state.get("postal_open")
    if (
        not technical
        and row is not None
        and ref is not None
        and st.session_state.get("postal_dismissed") != (choice, ref)
    ):
        opened = (choice, ref)
    if opened != (choice, ref):
        return
    if st.button("Volver a los resultados"):
        st.session_state["postal_dismissed"] = (choice, ref)
        st.session_state.pop("postal_open", None)
        st.rerun()
    if technical:
        from .municipal_fiche import render_fiche
    else:
        from .commercial_catalog_view import render_fiche

    if not technical:
        from .commercial_map import render as render_map

        render_map(code, ref, "postal_map_" + ref)
    render_fiche(code, postal.NAMES[code], ref, postal=row)
