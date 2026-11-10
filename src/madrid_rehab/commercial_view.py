"""Native Streamlit presentation of documentary commercial evidence."""

from collections import Counter

import pandas as pd
import streamlit as st

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


def render(model, errors):
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
