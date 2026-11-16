"""Sección REC en la ficha existente; consultas solo tras clic explícito."""

import time

import pandas as pd
from .i18n import ui as st

from .rec_client import Policy, RecError, consult, official_url, validate_ndp

TTL_SECONDS = 300
NOTICE = (
    "Información orientativa procedente del REC municipal; no constituye una certificación oficial"
)


def confirmed_accesses(frame, ref, municipality="28079"):
    if frame is None or frame.empty or municipality != "28079":
        return [], False
    required = {
        "ndp",
        "confirmed_parcel_ref14",
        "link_status",
        "municipality_code",
        "street",
        "kind",
        "number_raw",
        "qualifier_raw",
    }
    if not required.issubset(frame.columns):
        return [], True
    choices, ambiguous = [], False
    for ndp, group in frame.groupby("ndp", dropna=False):
        try:
            validate_ndp(ndp)
        except RecError:
            ambiguous = True
            continue
        good = (
            group.link_status.eq("confirmed_access_parcel").all()
            and group.confirmed_parcel_ref14.eq(ref).all()
            and group.municipality_code.eq(municipality).all()
            and len(group[["street", "kind", "number_raw", "qualifier_raw"]].drop_duplicates()) == 1
        )
        if not good:
            ambiguous = True
            continue
        row = group.iloc[0]
        if any(
            pd.isna(row[c]) or not str(row[c]).strip() for c in ("street", "kind", "number_raw")
        ) or pd.isna(row["qualifier_raw"]):
            ambiguous = True
            continue
        address = " ".join(
            str(row[c]).strip()
            for c in ("kind", "street", "number_raw", "qualifier_raw")
            if str(row[c]).strip()
        )
        choices.append(
            dict(
                ndp=ndp,
                address=address,
                parcel_ref14=ref,
                municipality="Madrid (28079)",
                quality="Vínculo documental CP–NDP confirmado",
            )
        )
    return sorted(choices, key=lambda x: (x["address"], x["ndp"])), ambiguous


def render_results(result):
    st.success(
        "Resultado obtenido correctamente"
        if result["state"] == "success"
        else "Sin inspecciones registradas en la respuesta consultada"
    )
    st.write(f"Dirección: {result['address']} · NDP: {result['ndp']}")
    st.caption(
        f"Fuente: REC del Ayuntamiento de Madrid · Consulta: {result['queried_at']} · Verificación: {result['identity_check']}"
    )
    if result["origin"] != "http":
        st.warning("Captura local histórica de prueba; no es una consulta actual al REC")
    st.caption(
        "Información del acceso y sus expedientes; no acredita el estado físico actual ni se extiende a todos los edificios de la parcela."
    )
    inspection_columns = {
        "case_reference": "Expediente",
        "inspection_type": "Tipo",
        "presentation_date_raw": "Presentación",
        "opinion_raw": "Dictamen",
        "scope_raw": "Alcance",
        "deficiency_raw": "Causa desfavorable",
        "status_raw": "Situación administrativa",
        "department_raw": "Dependencia",
        "followup_case_raw": "Expediente de seguimiento",
    }
    event_columns = {
        "case_reference": "Expediente",
        "event_kind": "Tipo",
        "noncompliance_raw": "Incumplimiento",
        "resolution_date_raw": "Fecha resolución",
        "resolution_raw": "Resolución",
        "status_raw": "Estado",
        "department_raw": "Dependencia",
        "antecedents_raw": "Antecedentes",
        "remediation_raw": "Subsanación literal",
    }
    for title, rows, columns in [
        ("ITE / IEE", result["inspections"], inspection_columns),
        ("Historial administrativo", result["events"], event_columns),
    ]:
        st.markdown(f"**{title}**")
        if rows:
            st.dataframe(
                pd.DataFrame(rows).reindex(columns=columns).fillna("").rename(columns=columns),
                hide_index=True,
            )
        else:
            st.caption("Sin registros en esta respuesta.")
    st.caption(
        "ARCHIVADO o TERMINADO no equivale a SUBSANADO. Se conservan los literales y expedientes independientes."
    )


def render_rec_parcel(ref, municipality="28079", *, loader=None, query=None):
    if municipality != "28079":
        st.info("No disponible en las fuentes integradas")
        st.caption("Consulta REC y accesos NDP de Madrid no aplicables a este municipio.")
        return
    st.markdown("**ITE / IEE — Registro municipal**")
    policy = Policy.from_env()
    frame, load_error = None, None
    if not policy.public and municipality == "28079":
        if loader is None:
            from .conservation_view import parcel_evidence

            loader = parcel_evidence
        try:
            frame = loader(ref, "rec_accesses", municipality)
        except (OSError, ValueError, KeyError) as exc:
            load_error = str(exc)
    choices, ambiguous = confirmed_accesses(frame, ref, municipality)
    selected = None
    if choices:
        selected_ndp = st.selectbox(
            "Seleccionar portal municipal",
            [c["ndp"] for c in choices],
            index=None,
            placeholder="Seleccione expresamente un acceso",
            format_func=lambda n: next(
                f"{c['address']} · NDP {n} · {c['quality']}" for c in choices if c["ndp"] == n
            ),
            key=f"rec_portal_{municipality}_{ref}",
        )
        selected = next((c for c in choices if c["ndp"] == selected_ndp), None)
    else:
        st.info("No se ha identificado un acceso municipal suficientemente verificado")
    if ambiguous:
        st.warning("NDP ambiguo o relación CP–NDP no confirmada; esos accesos no son consultables.")
    if ambiguous and frame is not None and not frame.empty:
        rejected = frame[~frame.ndp.isin([c["ndp"] for c in choices])] if "ndp" in frame else frame
        columns = [
            c
            for c in (
                "ndp",
                "street",
                "number_raw",
                "parcel_candidate",
                "parcel_ref14",
                "link_status",
            )
            if c in rejected
        ]
        if columns and not rejected.empty:
            st.dataframe(
                rejected[columns].rename(
                    columns={
                        "ndp": "Identificador de portal",
                        "street": "Calle",
                        "number_raw": "Número",
                        "parcel_candidate": "Parcela candidata",
                        "parcel_ref14": "Referencia catastral de parcela",
                        "link_status": "Calidad del vínculo",
                    }
                ),
                hide_index=True,
            )
    if load_error:
        st.warning(f"No se puede verificar el puente municipal: {load_error}")
    # Siempre independiente del resultado integrado; link_button abre otra pestaña.
    st.link_button(
        "Abrir ficha oficial del REC", official_url(selected["ndp"] if selected else None)
    )
    if selected:
        st.caption(
            f"{selected['municipality']} · CP {ref} · NDP {selected['ndp']} · {selected['quality']}"
        )
    token = (municipality, ref, selected["ndp"] if selected else None, policy.allowed)
    state_key = "rec_last_query"
    previous = st.session_state.get(state_key)
    if previous and (
        previous["token"] != token or time.monotonic() - previous["at"] >= TTL_SECONDS
    ):
        del st.session_state[state_key]
    if not policy.allowed:
        st.caption("Consulta integrada no habilitada")
    clicked = st.button(
        "Consultar ITE/IEE" if policy.allowed else "Consulta integrada no habilitada",
        disabled=not policy.allowed or selected is None,
        key=f"rec_query_{municipality}_{ref}",
    )
    if clicked and policy.allowed and selected:
        # Eliminar el resultado previo antes de intentar: no fallback silencioso.
        st.session_state.pop(state_key, None)
        try:
            result = (query or consult)(selected["ndp"], selected["address"], policy=policy)
            current = dict(result=result)
        except RecError as exc:
            current = dict(error=str(exc), code=exc.code)
        st.session_state[state_key] = dict(token=token, at=time.monotonic(), **current)
    previous = st.session_state.get(state_key)
    if previous:
        if "error" in previous:
            st.error(f"{previous['error']} ({previous['code']})")
        else:
            render_results(previous["result"])
    st.caption(NOTICE)
