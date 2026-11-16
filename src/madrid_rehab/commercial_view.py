"""Native Streamlit presentation of documentary commercial evidence."""

from collections import Counter

import pandas as pd
from .i18n import ui as st

from .commercial_fiche import Quality


SCOPES = {
    "individual_unit": "Vivienda individual",
    "whole_building": "Edificio completo declarado",
    "commercial_unit": "Local",
    "unknown": "Desconocido",
}
EVENTS = {
    "order": "Órdenes de ejecución históricas",
    "ite_pending": "Obligaciones ITE",
    "iee_pending": "Obligaciones IEE",
    "license": "Licencias",
    "declaration": "Declaraciones responsables",
}


def show_records(records, title):
    if not records:
        return
    with st.expander(title):
        rows = []
        for e in records:
            row = dict(e.value) if isinstance(e.value, dict) else {"Valor": e.value}
            if "Ámbito" in row:
                row["Ámbito"] = SCOPES.get(row["Ámbito"], row["Ámbito"])
            rows.append(
                {
                    "Dato": EVENTS.get(e.label, e.label),
                    **row,
                    "Fuente": e.source,
                    "Entidad de origen": e.entity_id,
                    "Calidad": str(e.quality),
                    "Ámbito del dato": e.scope,
                    "Fecha / periodo": e.period,
                    "Límite de interpretación": e.limitations,
                }
            )
        st.dataframe(
            pd.DataFrame(rows).map(lambda v: "" if v is None else str(v)),
            hide_index=True,
            width="stretch",
        )


def render_details(model, errors):
    st.subheader(model.title)
    if any(e.label == "Dirección seleccionada" for e in model.identity):
        st.caption(
            "Dirección vinculada documentalmente a una parcela catastral. No acredita un edificio físico único."
        )
    else:
        st.caption(
            "Consulta documental de parcela u objeto catastral; dirección seleccionada no disponible."
        )
    st.caption(
        f"{model.name} · {'Parcela vinculada' if model.kind == 'cp' else 'Objeto BU independiente'} · {model.identifier}"
    )
    for e in model.identity:
        if e.label == "Referencia de consulta":
            st.caption(f"Corte catastral: {e.period} · {e.source}")
        elif e.label in {"Accesos documentales de la parcela", "Parcelas vinculadas al acceso"}:
            st.write(f"{e.label}: {e.value}")
        elif e.label == "Objetos constructivos documentados":
            st.caption(
                "Objetos constructivos documentados: "
                + " · ".join(f"{k}: {v}" for k, v in e.value.items())
                + ". No es un recuento de edificios físicos."
            )
        elif e.quality == Quality.UNCOVERED:
            st.caption(f"{e.label}: {e.quality}")
    st.markdown("### Características principales")
    labels = list(dict.fromkeys(e.label for e in model.characteristics))
    for offset in range(0, len(labels), 2):
        cols = st.columns(2)
        for col, label in zip(cols, labels[offset : offset + 2]):
            evidence = [
                e for e in model.characteristics if e.label == label and e.value is not None
            ]
            values = sorted({str(e.value) for e in evidence})
            with col:
                st.markdown("**" + label + "**")
                st.write(
                    " · ".join(values[:8])
                    + (f" · {len(values)} valores distintos" if len(values) > 8 else "")
                    if values
                    else "No disponible"
                )
                if evidence:
                    st.caption(
                        (
                            "Información asociada a parcela · "
                            if model.kind == "cp"
                            else "Dato propio del objeto · "
                        )
                        + (
                            "Varios valores declarados; sin suma."
                            if len(values) > 1
                            else "Declaración por objeto; sin suma."
                        )
                    )
    st.caption(
        "Fuente: Catastro INSPIRE. Los años y usos pertenecen a objetos constructivos asociados; no son características verificadas del portal. BuildingPart es una parte catastral, no un edificio físico independiente."
    )
    show_records(
        [e for e in model.characteristics if e.value is not None],
        "Consultar valores constructivos y procedencia por objeto",
    )
    st.markdown("### Información energética")
    documented = [e for e in model.energy if e.quality == Quality.PARCEL]
    state = model.states.get("energy")
    if state in {Quality.UNAVAILABLE, Quality.UNCOVERED}:
        st.write(str(state) + ". No se puede determinar la disponibilidad de certificados.")
    elif documented:
        st.write(
            f"{len({e.entity_id for e in documented})} contenidos CEEE vinculados documentalmente a parcela."
        )
        for field in ("Consumo", "Emisiones"):
            counts = Counter(e.value[field] or "Sin letra" for e in documented)
            st.write(field + ": " + " · ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
        scopes = Counter(SCOPES.get(e.scope, e.scope) for e in documented)
        st.write("Ámbitos: " + " · ".join(f"{k}: {v}" for k, v in sorted(scopes.items())))
        dates = sorted(
            {e.value["Fecha declarada"] for e in documented if e.value["Fecha declarada"]}
        )
        st.caption(
            "Fechas declaradas: " + (f"{dates[0]} a {dates[-1]}" if dates else "No disponibles")
        )
    else:
        st.write("Sin certificados energéticos asociados en las fuentes integradas.")
    if len(documented) != len(model.energy):
        st.caption(
            f"{len(model.energy) - len(documented)} relaciones ambiguas o contenidos con incidencias, excluidos del recuento documental utilizable."
        )
    st.caption(
        "Cada certificado conserva su ámbito. Una vivienda no califica todo el edificio; no se acredita vigencia ni cobertura física."
    )
    show_records(model.energy, "Consultar certificados, fechas y fuentes")
    from .grants import PROGRAMS

    st.markdown("### Ayudas y subvenciones")
    st.markdown("**PRTR · Comunidad de Madrid**")
    documented = [e for e in model.grants if e.quality == Quality.PARCEL]
    if model.states.get("grants") == Quality.UNAVAILABLE:
        st.write("Información no disponible; consulta de ayudas no verificable.")
    elif documented:
        st.write(
            f"{len(documented)} expedientes PRTR con concesión asociada documentalmente a parcela."
        )
        for e in documented:
            amount = e.value["Concesión del expediente (€)"]
            st.write(
                f"{e.value['Programa']} · {PROGRAMS.get(e.value['Programa'], 'Programa sin descripción')} · Importe del expediente: "
                + (f"{amount:,.2f} €" if amount is not None else "No disponible")
            )
            st.caption(f"{e.entity_id} · {e.period} · Fuente: {e.source}")
            if e.value["Programa"] == "P4":
                st.caption("P4 corresponde a vivienda; no se extiende al conjunto del edificio.")
    else:
        st.write(
            "Sin expedientes PRTR confirmados en esta captura; no acredita ausencia real de ayudas."
        )
    if len(model.grants) != len(documented):
        st.caption(
            "Existen relaciones con incidencias; consultar detalles sin atribuir concesiones confirmadas."
        )
    st.caption(
        "Concesión no acredita pago, obra iniciada ni terminada. Importe por expediente, sin suma entre parcelas."
    )
    show_records(model.grants, "Consultar expedientes y procedencia")
    st.markdown("**Plan Rehabilita · Ayuntamiento de Madrid**")
    if model.states.get("municipal_grants") == Quality.UNAVAILABLE:
        st.write("Fuente municipal no disponible o no verificable en esta consulta.")
    elif model.municipal_grants:
        st.write(
            f"{len(model.municipal_grants)} expedientes municipales con relación documental confirmada a la parcela."
        )
    elif model.kind == "cp" and model.code == "28079":
        st.write(
            "Sin expediente municipal confirmado en esta captura; no acredita ausencia real de ayudas."
        )
    else:
        st.caption("Consulta municipal disponible exclusivamente en parcelas de Madrid.")
    st.caption(
        "Importes por expediente, sin suma entre capas ni parcelas. Subvención revisada no acredita pago ni obra ejecutada."
    )
    for evidence in model.municipal_grants:
        from .i18n import translate

        for label, value in evidence.value.items():
            st.write(translate(label) + ":", value if value is not None else "—")
        st.caption(evidence.source + " · " + evidence.period)
    show_records(model.municipal_grants, "Consultar Plan Rehabilita y procedencia")
    st.markdown("### Conservación e inspecciones")
    if model.states.get("events") in {Quality.UNCOVERED, Quality.UNAVAILABLE}:
        st.write(str(model.states["events"]))
    else:
        counts = Counter(e.label for e in model.conservation if e.quality == Quality.PARCEL)
        if counts:
            for key, count in sorted(counts.items()):
                st.write(f"{EVENTS.get(key, key)}: {count}")
        else:
            st.write("Sin antecedentes administrativos confirmados en la captura integrada.")
        if any(e.quality == Quality.AMBIGUOUS for e in model.conservation):
            st.caption(
                "Vinculación ambigua: existen antecedentes con incidencias; no se cuentan como confirmados."
            )
    st.caption(
        "Resultados actuales de inspección: no acreditados por estos antecedentes. REC: sin consulta automática; las consultas expresas y sus resultados se mantienen en detalles técnicos. Obligaciones y órdenes históricas no son diagnósticos actuales."
    )
    show_records(model.conservation, "Consultar antecedentes, fechas y fuentes")
    st.markdown("### Antes de preparar una propuesta")
    if model.recommendations:
        for recommendation in model.recommendations:
            st.write("• " + recommendation)
    else:
        st.caption("No hay comprobaciones adicionales derivadas de las evidencias disponibles.")
    for key, error in errors.items():
        label = {
            "construction": "Características",
            "events": "Conservación",
            "accesses": "Accesos",
            "energy": "Energía",
            "grants": "Ayudas",
            "municipal_grants": "Plan Rehabilita",
        }.get(key, key)
        st.warning(
            f"{label}: consulta no verificable. No se interpreta como ausencia de registros."
        )
        with st.expander("Detalle de consulta · " + label):
            st.text(error)


def render(model, errors):
    """Compact presentation; all original evidence remains in expanded details."""
    from .i18n import t, translate
    from .rec_client import official_url

    st.subheader(model.title)
    location = model.name
    if model.code == "28079" and model.kind == "cp":
        from .commercial_geography import district_index, district_names

        districts = district_index()
        match = districts[
            districts.parcel_ref14.eq(model.identifier)
            & districts.district_assignment.eq("assigned")
        ]
        if not match.empty:
            location += " · " + district_names().get(match.iloc[0].district_code, "")
    st.caption(location + " · " + model.identifier)
    values = {}
    for evidence in model.characteristics:
        if evidence.value is not None:
            values.setdefault(evidence.label, set()).add(str(evidence.value))
    st.write(
        translate("Uso declarado") + ": " + " · ".join(sorted(values.get("Uso declarado", {"—"})))
    )
    labels = [
        "Años constructivos declarados",
        "Viviendas declaradas por objeto",
        "Superficie bruta de plantas (m²)",
    ]
    for col, label in zip(st.columns(3), labels):
        entries = sorted(values.get(label, set()))
        col.metric(
            label,
            (" · ".join(entries) or "—")
            if len(entries) <= 2
            else t("ux.multiple", count=len(entries)),
        )
    st.caption(t("ux.scope"))
    st.markdown("**CEEE**")
    certificates = {e.entity_id: e for e in model.energy if e.quality == Quality.PARCEL}
    if certificates:
        st.write(t("ux.certificates", count=len(certificates)))
        for field in ("Consumo", "Emisiones"):
            counts = Counter(e.value.get(field) or "—" for e in certificates.values())
            st.write(
                translate(field)
                + ": "
                + " · ".join(f"{k} ({v})" for k, v in sorted(counts.items()))
            )
        scopes = Counter(translate(SCOPES.get(e.scope, e.scope)) for e in certificates.values())
        st.write(" · ".join(f"{k} ({v})" for k, v in scopes.items()))
        dates = sorted(
            {
                e.value.get("Fecha declarada")
                for e in certificates.values()
                if e.value.get("Fecha declarada")
            }
        )
        if dates:
            st.caption(dates[0] if len(dates) == 1 else dates[0] + " — " + dates[-1])
        st.caption(t("ux.energy_scope"))
    else:
        st.write(
            t("ux.energy_unknown")
            if model.states.get("energy") in {Quality.UNAVAILABLE, Quality.UNCOVERED}
            else t("ux.no_energy")
        )
    show_records(model.energy, "Consultar certificados, fechas y fuentes")
    if model.grants:
        st.markdown("**PRTR**")
        for evidence in model.grants:
            if evidence.quality == Quality.PARCEL:
                st.write(evidence.entity_id + " · " + str(evidence.value.get("Programa") or "—"))
                st.write(
                    translate("Concesión del expediente (€)")
                    + ": "
                    + str(evidence.value.get("Concesión del expediente (€)"))
                )
        st.caption(t("ux.grant_scope"))
    st.markdown("**Plan Rehabilita**")
    cases = {e.entity_id: e for e in model.municipal_grants}
    if not cases:
        st.write(t("ux.no_plan"))

    def show_case(e):
        data = e.value
        st.write(str(data.get("Convocatoria") or "—") + " · " + e.entity_id)
        st.write(data.get("Actuaciones por componente fuente") or "—")
        amount = data.get("Subvención revisada del expediente (€)")
        st.write(
            translate("Subvención revisada del expediente (€)")
            + ": "
            + (f"{amount:,.2f} €" if amount is not None else "—")
        )
        st.caption(t("ux.plan_source") + " · " + translate(e.period))

    if len(cases) > 1:
        st.write(t("ux.plan_cases", count=len(cases)))
        with st.expander(t("ux.plan_relation")):
            for evidence in cases.values():
                show_case(evidence)
    else:
        for evidence in cases.values():
            show_case(evidence)
    if cases:
        st.caption(t("ux.plan_scope"))
    st.markdown("**" + t("ux.inspections") + "**")
    st.write(t("ux.no_results"))
    counts = Counter(e.label for e in model.conservation if e.quality == Quality.PARCEL)
    for label, count in counts.items():
        st.write(translate(EVENTS.get(label, label)) + ": " + str(count))
    st.caption(t("ux.orders_scope"))
    if model.code == "28079":
        st.link_button(t("ux.official"), official_url())
        st.caption(t("ux.external"))
        if not model.title.startswith("Consulta catastral"):
            st.code(model.title.split(" — ")[0], language=None)
    if errors:
        st.warning(t("ux.errors"))
    with st.expander(t("ux.full")):
        render_details(model, errors)
