"""Gráficos interactivos con unidades y denominadores explícitos."""

import altair as alt

from .profiles import PERIODS

SCOPE_NAMES = {
    "dwelling": "Vivienda",
    "building_part": "Parte/local",
    "whole_building": "Edificio completo declarado",
    "unknown": "Desconocido",
}


def grade_distribution(observations):
    data = observations.drop_duplicates("record_id").copy()
    data["grade"] = data.cal_norenovglobal.where(
        data.cal_norenovglobal.isin(list("ABCDEFG")), "Sin letra"
    )
    data["scope"] = data.certificate_scope.map(SCOPE_NAMES).fillna("Desconocido")
    counts = data.groupby(["grade", "scope"]).size().rename("records").reset_index()
    select = alt.selection_point(fields=["scope"], bind="legend")
    return (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            x=alt.X(
                "grade:N", sort=list("ABCDEFG") + ["Sin letra"], title="Letra del registro CEEE"
            ),
            y=alt.Y("records:Q", title="Registros únicos observados"),
            color=alt.Color("scope:N", title="Ámbito declarado"),
            opacity=alt.condition(select, alt.value(1), alt.value(0.2)),
            tooltip=[
                alt.Tooltip("grade:N", title="Letra"),
                alt.Tooltip("scope:N", title="Ámbito"),
                alt.Tooltip("records:Q", title="Registros"),
            ],
        )
        .add_params(select)
    )


def construction_distribution(frame):
    counts = frame.groupby("construction_period").size().rename("parcels").reset_index()
    return (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            x=alt.X("construction_period:N", sort=PERIODS, title="Año más antiguo del agregado BU"),
            y=alt.Y("parcels:Q", title="Parcelas"),
            tooltip=["construction_period:N", "parcels:Q"],
        )
    )


def evidence_scatter(frame):
    fields = [
        "parcel_ref14",
        "construction_oldest_year",
        "ceee_efg_share_observed",
        "ceee_valid_grade_count",
        "energy_profile",
        "review_flags",
    ]
    data = frame.loc[frame.ceee_valid_grade_count.gt(0), fields].copy()
    if len(data) > 5000:
        data["decade"] = (data.construction_oldest_year // 10) * 10
        data["efg_band_lower"] = (
            (data.ceee_efg_share_observed * 20).clip(upper=19.999999) // 1
        ) / 20
        counts = (
            data.groupby(["decade", "efg_band_lower", "energy_profile"])
            .size()
            .rename("parcels")
            .reset_index()
        )
        width = 0.05
        if len(counts) > 5000:
            data["decade"] = (data.construction_oldest_year // 20) * 20
            data["efg_band_lower"] = (
                (data.ceee_efg_share_observed * 10).clip(upper=9.999999) // 1
            ) / 10
            counts = (
                data.groupby(["decade", "efg_band_lower", "energy_profile"])
                .size()
                .rename("parcels")
                .reset_index()
            )
            width = 0.1
        counts["efg_band_upper"] = counts.efg_band_lower + width
        return (
            alt.Chart(counts)
            .mark_circle(opacity=0.65)
            .encode(
                x=alt.X(
                    "decade:Q",
                    title="Periodo más antiguo del agregado BU (10–20 años)",
                    scale=alt.Scale(zero=False),
                ),
                y=alt.Y(
                    "efg_band_lower:Q",
                    title="Límite inferior de banda E/F/G (ancho 5–10%)",
                    scale=alt.Scale(domain=[0, 1]),
                ),
                size=alt.Size("parcels:Q", title="Parcelas por grupo"),
                color=alt.Color("energy_profile:N", title="Perfil de observación"),
                tooltip=[
                    "decade:Q",
                    "efg_band_lower:Q",
                    "efg_band_upper:Q",
                    "parcels:Q",
                    "energy_profile:N",
                ],
            )
            .interactive()
        )
    return (
        alt.Chart(data)
        .mark_circle(size=48, opacity=0.5)
        .encode(
            x=alt.X(
                "construction_oldest_year:Q",
                title="Año más antiguo del agregado BU",
                scale=alt.Scale(zero=False),
            ),
            y=alt.Y(
                "ceee_efg_share_observed:Q",
                title="Proporción E/F/G observada",
                scale=alt.Scale(domain=[0, 1]),
            ),
            color=alt.Color("energy_profile:N", title="Perfil de observación"),
            tooltip=[
                "parcel_ref14:N",
                "construction_oldest_year:Q",
                alt.Tooltip("ceee_efg_share_observed:Q", format=".1%"),
                "ceee_valid_grade_count:Q",
                "review_flags:N",
            ],
        )
        .interactive()
    )


def coverage_chart(comparison, group):
    data = comparison.copy()
    data[group] = data[group].fillna("Sin localización")
    return (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(
                "observed_energy_coverage:Q",
                title="Parcelas con CEEE / parcelas del grupo",
                axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 1]),
            ),
            y=alt.Y(
                f"{group}:N",
                title="Periodo" if group == "construction_period" else "Celda de malla 500 m",
            ),
            color=alt.Color("comparison_eligible:N", title="Mínimo para comparar distribución"),
            tooltip=[
                f"{group}:N",
                "parcels:Q",
                "with_energy:Q",
                "parcels_with_valid_grades:Q",
                alt.Tooltip("observed_energy_coverage:Q", format=".1%"),
            ],
        )
    )


def sensitivity_chart(summary):
    return (
        alt.Chart(summary)
        .mark_line(point=True)
        .encode(
            x=alt.X("age_weight:Q", title="Peso del contexto constructivo"),
            y=alt.Y(
                "median_absolute_change:Q",
                title="Cambio absoluto mediano frente al escenario base (puntos)",
            ),
            color=alt.Color("minimum_records:N", title="Mínimo de registros con letra"),
            tooltip=[
                "age_weight:Q",
                "minimum_records:N",
                "eligible_parcels:Q",
                "median_absolute_change:Q",
                "rank_correlation:Q",
            ],
        )
    )


def observation_years(observations):
    data = observations.drop_duplicates("record_id")
    counts = data.groupby("year").size().rename("records").reset_index()
    counts["year"] = counts.year.astype(int).astype(str)
    return (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            x=alt.X("year:O", title="Año de fecha declarada"),
            y=alt.Y("records:Q", title="Registros únicos"),
            tooltip=["year:O", "records:Q"],
        )
    )
