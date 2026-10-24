"""Exploración de productos analíticos materializados, con caché e integridad."""

from pathlib import Path

import streamlit as st

from .analysis_charts import (
    construction_distribution,
    coverage_chart,
    evidence_scatter,
    grade_distribution,
    observation_years,
    sensitivity_chart,
)
from .analysis_store import load_snapshot, snapshot_signature
from .profiles import (
    explain_profile,
    ENERGY_PROFILES,
    PERIODS,
    csv_export,
    filter_parcels,
    group_comparison,
)


# API previa conservada para consumidores y tests de sesión 6 v1.
def filter_profile(frame, availability="Todas", query=""):
    return filter_parcels(frame, availability=availability, query=query)


@st.cache_data(show_spinner=False, max_entries=4)
def cached_snapshot(root, signature):
    return load_snapshot(root, signature)


def render_analysis(root, key_prefix=None):
    def widget_key(name):
        return f"{key_prefix}:{name}" if key_prefix else None

    st.subheader("Perfil de rehabilitación por parcela")
    st.caption("Universo completo del distrito; los filtros del mapa BU no afectan esta tabla.")
    root = Path(root)
    if not (root / "manifest.json").exists():
        st.info("Genera el perfil con: PYTHONPATH=src .venv/bin/python -m madrid_rehab.analytics")
        return
    try:
        snapshot = cached_snapshot(str(root.resolve()), snapshot_signature(root))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.error(f"No se puede leer el perfil verificable: {exc}")
        return
    frame, report = snapshot["parcel_features.parquet"], snapshot["coverage.json"]
    for prefix, title in [("inspection", "ITE/IEE"), ("grant", "Ayudas")]:
        states = frame[prefix + "_source_status"].unique()
        st.caption(
            f"{title}: {'captura revisada integrada' if 'snapshot_reviewed' in states else 'registros no integrados'}. "
            "Sin información no significa ausencia real del fenómeno."
        )
    a, b, c = st.columns(3)
    a.metric("Parcelas del distrito", report["parcels"])
    b.metric("Con evidencia energética", report["energy_available"])
    c.metric("Con periodo constructivo", report["construction_available"])
    st.warning(
        "Sin IPR global. Certificados de viviendas o partes no califican el edificio. "
        "Los perfiles describen evidencia disponible, no necesidad ni urgencia de obras."
    )
    left, right = st.columns(2)
    with left:
        availability = st.selectbox(
            "Cobertura del perfil",
            ["Todas", "Con evidencia energética", "Sin evidencia energética"],
            key=widget_key("coverage"),
        )
        periods = st.multiselect(
            "Periodo constructivo", PERIODS, default=PERIODS, key=widget_key("period")
        )
        residential = st.checkbox(
            "Parcelas con algún BU residencial declarado", key=widget_key("residential")
        )
    with right:
        query = st.text_input("Buscar parcela en el perfil", key=widget_key("query"))
        profiles = st.multiselect(
            "Perfil de evidencia energética",
            ENERGY_PROFILES,
            default=ENERGY_PROFILES,
            key=widget_key("profile"),
        )
        minimum = st.number_input(
            "Mínimo de registros CEEE vinculados",
            min_value=0,
            value=0,
            step=1,
            key=widget_key("minimum"),
        )
    unique = st.checkbox("Solo identidad CP única", value=False, key=widget_key("unique"))
    order_labels = {
        "Referencia": "parcel_ref14",
        "Registros CEEE": "ceee_records_observed",
        "Año más antiguo": "construction_oldest_year",
        "Proporción observada E/F/G": "ceee_efg_share_observed",
    }
    order = st.selectbox("Ordenar parcelas por", list(order_labels), key=widget_key("order"))
    descending = st.checkbox("Orden descendente", value=False, key=widget_key("descending"))
    result = filter_parcels(
        frame,
        availability,
        query,
        periods,
        profiles,
        residential,
        minimum,
        unique,
        order_labels[order],
        not descending,
    )
    st.write(f"**{len(result):,} / {len(frame):,} parcelas cumplen todos los filtros.**")
    st.caption(
        "CEEE son versiones de registro únicas; el historial no se fuerza a un certificado vigente. "
        "E/F/G usa solo letras A–G observadas. Cero enlaces no prueba ausencia real. "
        "El periodo del agregado BU no es fecha de reforma. Los filtros se combinan con AND."
    )
    columns = [
        "parcel_ref14",
        "construction_period",
        "bu_count",
        "residential_bu_count",
        "ceee_records_observed",
        "ceee_valid_grade_count",
        "ceee_efg_share_observed",
        "energy_profile",
        "information_profile",
        "review_flags",
    ]
    columns += [
        name
        for name in [
            "inspection_records_observed",
            "inspection_last_historical_result",
            "inspection_last_observed_date",
            "grant_awards_observed",
            "grant_known_eur_awarded",
        ]
        if name in result
    ]
    st.dataframe(
        result[columns],
        hide_index=True,
        width="stretch",
        column_config={
            "parcel_ref14": "Referencia de parcela",
            "construction_period": "Periodo constructivo",
            "bu_count": "Objetos BU",
            "residential_bu_count": "BU residenciales",
            "ceee_records_observed": "Registros CEEE",
            "ceee_valid_grade_count": "Con letra A–G",
            "energy_profile": "Perfil de evidencia",
            "information_profile": "Disponibilidad",
            "review_flags": "Avisos de revisión",
            "ceee_efg_share_observed": st.column_config.NumberColumn(
                "Proporción E/F/G observada", format="%.3f"
            ),
        },
    )
    st.download_button(
        "Exportar perfil filtrado",
        csv_export(result),
        file_name="perfil_parcelas.csv",
        mime="text/csv",
    )
    if result.empty:
        st.info("No hay parcelas con esta combinación. Amplía los filtros para ver distribuciones.")
        return
    with st.expander("Explicación individual de los indicadores"):
        ref = st.selectbox(
            "Explicar una parcela",
            [""] + result.parcel_ref14.tolist(),
            format_func=lambda value: value or "Selecciona una referencia",
            key=widget_key("explain"),
        )
        if ref:
            row = result[result.parcel_ref14.eq(ref)].iloc[0]
            for label, explanation in explain_profile(row).items():
                st.write(f"**{label}:** {explanation}")
    context, energy, comparisons, methodology = st.tabs(
        [
            "Contexto y cobertura",
            "Distribución energética",
            "Comparaciones",
            "Perfiles y sensibilidad",
        ]
    )
    with context:
        st.altair_chart(construction_distribution(result), use_container_width=True)
        st.bar_chart(result.information_profile.value_counts().rename("Parcelas"))
        st.caption(
            "Construcción y energía son dos dimensiones informativas. Las fuentes administrativas se indican arriba."
        )
    with energy:
        observations = snapshot.get("energy_observations.parquet")
        if observations is None:
            st.info(
                "Esta captura v1 no incluye observaciones por ámbito. Genera una nueva salida v2."
            )
        else:
            observations = observations[observations.parcel_ref14.isin(result.parcel_ref14)]
            scopes = sorted(observations.certificate_scope.fillna("unknown").unique())
            chosen = st.multiselect(
                "Ámbitos para los gráficos energéticos",
                scopes,
                default=scopes,
                key=widget_key("scopes"),
            )
            observations = observations[
                observations.certificate_scope.fillna("unknown").isin(chosen)
            ]
            st.caption(
                "Este filtro de ámbito afecta únicamente a los gráficos energéticos. "
                "Haz clic en la leyenda para resaltar ámbitos; las cantidades no se recalculan por el resaltado."
            )
            if observations.empty:
                st.info("Sin registros energéticos en las parcelas y ámbitos seleccionados.")
            else:
                st.altair_chart(grade_distribution(observations), use_container_width=True)
                st.altair_chart(observation_years(observations), use_container_width=True)
                st.caption(
                    "Año de fecha del certificado, distinto de recursos de extracción 2025–2026. "
                    "Recuentos deduplicados por registro dentro de la selección; no son edificios."
                )
        if result.construction_available.any() and result.ceee_valid_grade_count.gt(0).any():
            st.altair_chart(evidence_scatter(result), use_container_width=True)
            st.caption(
                "Rueda/arrastre para explorar. Hasta 5.000 observaciones, cada punto es parcela; "
                "por encima, se agrupa en periodos de 10–20 años y bandas E/F/G de 5–10%, con número de parcelas en tooltip. "
                "consultar número de registros y avisos en tooltip. No implica causalidad."
            )
    with comparisons:
        groups = ["construction_period"] + (["analysis_zone"] if "analysis_zone" in result else [])
        group = st.selectbox(
            "Comparar por",
            groups,
            key=widget_key("comparison"),
            format_func=lambda v: "Periodo constructivo"
            if v == "construction_period"
            else "Malla métrica de 500 m (no barrios)",
        )
        comparison = group_comparison(
            result, group, observations=snapshot.get("energy_observations.parquet")
        )
        st.altair_chart(coverage_chart(comparison, group), use_container_width=True)
        st.dataframe(comparison, hide_index=True, width="stretch")
        st.caption(
            "Cobertura = parcelas con registros / parcelas seleccionadas de cada grupo. "
            "Mediana E/F/G entre parcelas con letras válidas, sin ponderar por número de registros. "
            "Solo se muestra con ≥20 parcelas y ≥5 con letras: mínimo operativo, no inferencia estadística. "
            "La proporción agrupada usa registros únicos por grupo en v2; pooled_unit indica la unidad. "
            "Un certificado que abarca grupos distintos puede figurar una vez en cada uno; no se suman como censo. "
            "La malla usa coordenadas CP EPSG:25830; no son barrios oficiales y hay celdas de borde parciales."
        )
    with methodology:
        st.write(
            "**Perfiles interpretables:** sin registros; sin letra interpretable; muestra escasa (1–2 letras); "
            "E/F/G en al menos 75% de ≥3 registros; otras distribuciones observadas. "
            "Son etiquetas descriptivas con umbrales explícitos, no diagnósticos."
        )
        st.write(
            "**Avisos de revisión:** identidad CP ambigua, varios BU, pocas letras, ámbitos mezclados "
            "y periodo desconocido. Una etiqueta no compensa otra dimensión ausente."
        )
        summary = snapshot.get("sensitivity_summary.parquet")
        if summary is not None:
            st.altair_chart(sensitivity_chart(summary), use_container_width=True)
            st.dataframe(summary, hide_index=True, width="stretch")
            st.caption(
                "Auditoría del distrito completo, independiente de los filtros. Comparador B: "
                "peso × antigüedad acotada + (1−peso) × proporción E/F/G. "
                "Se varían pesos 0–1 y mínimos 1/3/5/10. Diferencias y correlación de rangos "
                "contra peso 0,5/mínimo 3 sobre parcelas comunes. No es IPR ni ranking recomendado."
            )
        with st.expander("Auditoría y denominadores"):
            st.json(snapshot.get("audit.json", report))
