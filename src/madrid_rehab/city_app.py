"""Aplicación municipal: 21 distritos agregados y detalle selectivo con datos locales."""

import os
from pathlib import Path

import altair as alt
import streamlit as st

from madrid_rehab.grants_view import render_grants
from madrid_rehab.administrative_view import render_activity
from madrid_rehab.city_maps import change_district, district_selection, overview_deck
from madrid_rehab.city_store import load_overview, signature
from madrid_rehab.district_view import render_district
from madrid_rehab.profiles import csv_export

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "data/processed/session_7_final"


@st.cache_data(show_spinner=False, max_entries=3)
def cached_overview(root, token):
    return load_overview(root, token)


def selected_district(key):
    code = district_selection(st.session_state.get(key))
    if code:
        st.session_state.city_district = code
        change_district(st.session_state, code)


def go_home():
    st.session_state.city_district = "all"
    change_district(st.session_state, "all")


def compare_districts(summary):
    st.subheader("Comparación de distritos")
    summary = summary.copy()
    summary["ceee_grade_unknown"] = summary.ceee_confirmed_records - summary[
        [f"ceee_grade_{g}" for g in "ABCDEFG"]
    ].sum(axis=1)
    codes = summary.district_code.tolist()
    names = summary.set_index("district_code").district_name.to_dict()
    chosen = st.multiselect(
        "Distritos a comparar (dos o más para contraste)",
        codes,
        default=codes,
        format_func=lambda code: f"{code} · {names[code]}",
    )
    minimum = st.number_input(
        "Mínimo de parcelas con CEEE para comparar", min_value=0, value=0, step=1
    )
    filtered = summary[summary.district_code.isin(chosen) & summary.parcels_with_energy.ge(minimum)]
    order = st.selectbox(
        "Ordenar comparación por",
        [
            "district_code",
            "parcels",
            "bu_spatial",
            "observed_energy_coverage",
            "median_oldest_year",
        ],
    )
    descending = st.checkbox("Comparación en orden descendente")
    filtered = filtered.sort_values(
        [order] + ([] if order == "district_code" else ["district_code"]),
        ascending=not descending,
        na_position="last",
    )
    st.caption(
        "Parcelas = referencias asignadas de forma única a distrito; CP espaciales = filas geométricas. "
        "BU se asigna por punto interior propio. Cobertura = parcelas con CEEE confirmado / parcelas del distrito. "
        "Los registros únicos por distrito pueden repetirse entre distritos; no se suman como certificados municipales."
    )
    st.dataframe(filtered, hide_index=True, width="stretch")
    st.download_button(
        "Exportar comparación de distritos",
        csv_export(filtered),
        file_name="comparacion_distritos.csv",
        mime="text/csv",
    )
    if filtered.empty:
        st.info("No hay distritos con esta combinación de filtros.")
        return
    st.altair_chart(
        alt.Chart(filtered)
        .mark_bar()
        .encode(
            x=alt.X(
                "observed_energy_coverage:Q",
                title="Cobertura energética observada por parcela",
                axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 1]),
            ),
            y=alt.Y("district_name:N", title="Distrito", sort=None),
            tooltip=[
                "district_name:N",
                "parcels:Q",
                "parcels_with_energy:Q",
                "valid_grade_records:Q",
            ],
        ),
        use_container_width=True,
    )
    distribution = st.radio("Distribución de registros observados", ["Letras", "Ámbitos"])
    if distribution == "Letras":
        columns = [f"ceee_grade_{g}" for g in "ABCDEFG"] + ["ceee_grade_unknown"]
    else:
        columns = [
            f"ceee_scope_{scope}"
            for scope in ["dwelling", "building_part", "whole_building", "unknown"]
        ]
    if set(columns).issubset(filtered.columns):
        distribution_table = filtered.melt(
            id_vars=["district_code", "district_name"],
            value_vars=columns,
            var_name="category",
            value_name="records",
        )
        distribution_table["category"] = distribution_table.category.str.replace(
            "ceee_grade_", "", regex=False
        ).str.replace("ceee_scope_", "", regex=False)
        if distribution == "Letras":
            distribution_table["category"] = distribution_table.category.replace(
                {"unknown": "Sin letra A–G"}
            )
        else:
            labels = {
                "dwelling": "Vivienda",
                "building_part": "Parte/local",
                "whole_building": "Edificio completo declarado",
                "unknown": "Ámbito desconocido",
            }
            distribution_table["category"] = distribution_table.category.map(labels)
        st.altair_chart(
            alt.Chart(distribution_table)
            .mark_bar()
            .encode(
                x=alt.X("district_name:N", title="Distrito"),
                y=alt.Y("records:Q", title="Registros CEEE únicos dentro del distrito"),
                color=alt.Color(
                    "category:N", title="Letra" if distribution == "Letras" else "Ámbito declarado"
                ),
                tooltip=["district_name:N", "category:N", "records:Q"],
            ),
            use_container_width=True,
        )
    st.caption(
        "Distribución de registros observados, no calificación del parque. Las diferencias de cobertura y ámbito impiden interpretar esto como ranking de necesidad."
    )


def main():
    st.set_page_config(
        page_title="Madrid Rehab Intelligence · Madrid", page_icon="🏘️", layout="wide"
    )
    st.markdown(
        """<style>
        .block-container {padding-top:1.5rem; padding-bottom:2rem;}
        [data-testid="stMetricValue"] {font-size:1.65rem;}
        [data-testid="stMetricLabel"] {white-space:normal;}
        </style>""",
        unsafe_allow_html=True,
    )
    view = st.sidebar.radio("Navegación", ["Madrid capital", "Comunidad de Madrid — Subvenciones"])
    if view == "Comunidad de Madrid — Subvenciones":
        from .regional_view import render_regional

        render_regional()
        return
    st.title("Madrid Rehab Intelligence · Madrid capital")
    st.caption("21 distritos oficiales · Parcela, BU y certificado diferenciados · Sin IPR global")
    root = Path(os.environ.get("MADRID_REHAB_SESSION7_DIR", str(DEFAULT))).resolve()
    if not (root / "manifest.json").exists():
        st.error(
            "Faltan productos de sesión 7. Ejecuta: PYTHONPATH=src .venv/bin/python -m madrid_rehab.city_pipeline --district all"
        )
        return
    try:
        overview = cached_overview(str(root), signature(root))
    except (OSError, KeyError, ValueError) as exc:
        st.error(f"No se puede abrir la captura municipal: {exc}")
        return
    summary = overview["district_summary.parquet"]
    names = summary.set_index("district_code").district_name.to_dict()
    with st.sidebar:
        st.header("Ubicación")
        code = st.selectbox(
            "Ámbito territorial",
            ["all"] + summary.district_code.tolist(),
            key="city_district",
            format_func=lambda c: "Madrid capital · 21 distritos"
            if c == "all"
            else f"{c} · {names[c]}",
        )
        st.button("Volver a Madrid capital", on_click=go_home)
    change_district(st.session_state, code)
    if code != "all":
        render_district(root, code, overview)
        return
    municipal = overview["manifest"]["municipal"]
    a, b, c, d = st.columns(4)
    a.metric("Parcelas RC distintas · captura municipal", municipal["parcel_references"])
    b.metric("Objetos BU · captura municipal", municipal["bu_objects"])
    c.metric("Registros CEEE · captura", municipal["ceee_records"])
    d.metric("Parcelas con CEEE confirmado", municipal["parcels_with_energy"])
    st.caption(
        f"{municipal['parcel_rows']:,} filas CP; {municipal['confirmed_certificate_records']:,} registros CEEE confirmados en parcela; "
        f"{municipal['record_parcel_pairs']:,} pares registro/parcela. {municipal['unassigned_parcel_references']} referencias sin distrito único. "
        "Datos observados del paquete municipal: no garantizan cobertura de todos los edificios o certificados existentes."
    )
    map_tab, comparison_tab, quality_tab, activity_tab, grants_tab = st.tabs(
        [
            "Madrid · mapa general",
            "Comparar distritos",
            "Cobertura y calidad",
            "Actividad y rehabilitación",
            "Subvenciones PRTR",
        ]
    )
    with map_tab:
        urban = st.toggle("Mapa urbano municipal · requiere internet", value=False)
        st.pydeck_chart(
            overview_deck(overview["districts.parquet"], summary, urban),
            key="city-overview-map",
            on_select=lambda: selected_district("city-overview-map"),
            selection_mode="single-object",
        )
        st.markdown(
            '<div style="height:12px;background:linear-gradient(to right,rgb(30,110,145),rgb(30,210,145));border:1px solid #667"></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "0% — 100% · Parcelas con certificado localizado y correspondencia confirmada a nivel de parcela / parcelas del distrito. Gris: desconocido."
        )
        st.write(
            "Selecciona un distrito en el mapa o el selector lateral para abrir detalle por celdas."
        )
        st.caption(
            "Color: disponibilidad de evidencia energética, no potencial de rehabilitación. "
            "Límites: Ayuntamiento de Madrid · CC BY 4.0. © OpenStreetMap contributors · ODbL si se activa."
        )
    with comparison_tab:
        compare_districts(summary)
    with quality_tab:
        if not overview["manifest"].get("event_inputs"):
            st.info(
                "La captura energética histórica no incorpora eventos. Consulta las fuentes administrativas locales en «Actividad y rehabilitación»; las concesiones siguen pendientes."
            )
        else:
            st.info(
                "Capturas canónicas revisadas integradas: "
                + ", ".join(overview["manifest"]["event_inputs"])
            )
        st.json(overview["source_coverage.json"])
        st.json(overview["reconciliation.json"])
        st.caption(
            "Punto interior para asignación espacial; cruces de límite conservados. "
            "Una referencia con filas CP en distintos distritos permanece residual. "
            "Mallas de 500 m son subdivisiones métricas exploratorias, no barrios administrativos."
        )

    with activity_tab:
        render_activity()
    with grants_tab:
        render_grants()


if __name__ == "__main__":
    main()
