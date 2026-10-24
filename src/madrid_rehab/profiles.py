"""Perfiles descriptivos, filtros y comparaciones; ningún diagnóstico de rehabilitación."""

import numpy as np
import pandas as pd

PERIODS = ["Hasta 1940", "1941–1960", "1961–1980", "1981–2000", "2001–2026", "Sin fecha"]
ENERGY_PROFILES = [
    "Sin registros vinculados",
    "Sin letra interpretable",
    "Muestra escasa (1–2)",
    "E/F/G en ≥75% observado",
    "Otras distribuciones observadas",
]


def add_profiles(frame):
    out = frame.copy()
    years = out.construction_oldest_year
    period = pd.cut(years, [999, 1940, 1960, 1980, 2000, 2026], labels=PERIODS[:-1])
    out["construction_period"] = period.astype("string").fillna("Sin fecha")
    out["energy_profile"] = np.select(
        [
            out.ceee_records_observed.eq(0),
            out.ceee_valid_grade_count.eq(0),
            out.ceee_valid_grade_count.lt(3),
            out.ceee_efg_share_observed.ge(0.75),
        ],
        ENERGY_PROFILES[:-1],
        default=ENERGY_PROFILES[-1],
    )
    out["information_profile"] = out.observed_dimensions.map(
        {0: "Sin ambas dimensiones", 1: "Una dimensión disponible", 2: "Construcción y energía"}
    )
    if out.empty:
        out["review_flags"] = pd.Series(dtype="string", index=out.index)
        return out
    out["review_flags"] = out.apply(
        lambda r: "; ".join(
            flag
            for condition, flag in [
                (r.cp_rows > 1, "identidad CP ambigua"),
                (r.bu_count > 1, "varios BU"),
                (
                    r.ceee_records_observed > 0 and r.ceee_valid_grade_count < 3,
                    "pocas letras observadas",
                ),
                (r.ceee_scope_count > 1, "ámbitos heterogéneos"),
                (r.ceee_records_observed > r.ceee_valid_grade_count, "letras desconocidas"),
                (not r.construction_available, "periodo desconocido"),
                (
                    getattr(r, "construction_invalid_bu_count", 0) > 0,
                    "intervalo constructivo inválido",
                ),
            ]
            if condition
        ),
        axis=1,
    )
    return out


def filter_parcels(
    frame,
    availability="Todas",
    query="",
    periods=None,
    energy_profiles=None,
    residential_only=False,
    minimum_records=0,
    unique_cp=False,
    sort_by="parcel_ref14",
    ascending=True,
):
    if minimum_records < 0:
        raise ValueError("Mínimo de registros negativo")
    if sort_by not in frame.columns:
        raise ValueError("Columna de ordenación desconocida")
    mask = pd.Series(True, index=frame.index)
    if availability == "Con evidencia energética":
        mask &= frame.energy_available
    elif availability == "Sin evidencia energética":
        mask &= ~frame.energy_available
    elif availability != "Todas":
        raise ValueError("Filtro de cobertura desconocido")
    if query.strip():
        mask &= frame.parcel_ref14.str.contains(query.strip(), regex=False, case=False, na=False)
    if periods is not None:
        mask &= frame.construction_period.isin(periods)
    if energy_profiles is not None:
        mask &= frame.energy_profile.isin(energy_profiles)
    if residential_only:
        mask &= frame.residential_bu_count.gt(0)
    if unique_cp:
        mask &= frame.cp_rows.eq(1)
    mask &= frame.ceee_records_observed.ge(minimum_records)
    order = list(dict.fromkeys([sort_by, "parcel_ref14"]))
    return frame.loc[mask].sort_values(
        order, ascending=ascending, na_position="last", kind="stable"
    )


def group_comparison(frame, group="construction_period", minimum_parcels=20, observations=None):
    """No inventa zonas: solo periodos o malla métrica derivada de coordenadas CP."""
    if group not in {"construction_period", "analysis_zone"} or minimum_parcels < 1:
        raise ValueError("Agrupación o mínimo inválido")
    if group not in frame:
        return pd.DataFrame()
    data = frame.copy()
    data["efg_records"] = data[[f"ceee_grade_{g}" for g in "EFG"]].sum(axis=1)
    result = data.groupby(group, dropna=False).agg(
        parcels=("parcel_ref14", "nunique"),
        with_energy=("energy_available", "sum"),
        valid_grade_records=("ceee_valid_grade_count", "sum"),
        efg_records=("efg_records", "sum"),
        median_parcel_efg_share=("ceee_efg_share_observed", "median"),
        parcels_with_valid_grades=("ceee_valid_grade_count", lambda s: s.gt(0).sum()),
    )
    result["pooled_grade_denominator"] = result.valid_grade_records
    result["pooled_efg_numerator"] = result.efg_records
    result["pooled_unit"] = "record_parcel_pairs"
    if observations is not None:
        # Un certificado multiparcela cuenta una vez dentro de cada grupo seleccionado.
        observed = observations.merge(
            frame[["parcel_ref14", group]], on="parcel_ref14", how="inner", validate="many_to_one"
        )
        observed = observed.drop_duplicates(["record_id", group]).copy()
        observed["valid_grade"] = observed.cal_norenovglobal.isin(list("ABCDEFG"))
        observed["efg"] = observed.cal_norenovglobal.isin(list("EFG"))
        grouped = observed.groupby(group, dropna=False)
        result["pooled_grade_denominator"] = grouped.valid_grade.sum().reindex(
            result.index, fill_value=0
        )
        result["pooled_efg_numerator"] = grouped.efg.sum().reindex(result.index, fill_value=0)
        result["pooled_unit"] = "unique_records_per_group"
    result["pooled_efg_share"] = (
        result.pooled_efg_numerator / result.pooled_grade_denominator.replace(0, float("nan"))
    )
    result["observed_energy_coverage"] = result.with_energy / result.parcels
    result["comparison_eligible"] = result.parcels.ge(
        minimum_parcels
    ) & result.parcels_with_valid_grades.ge(5)
    if group == "analysis_zone":
        result["comparison_eligible"] &= result.index.notna()
    # Se conservan tamaños y cobertura de grupos pequeños, sin mostrar su mediana.
    result.loc[~result.comparison_eligible, ["median_parcel_efg_share", "pooled_efg_share"]] = (
        float("nan")
    )
    return result.reset_index()


def sensitivity_analysis(frame, scorer):
    rows = []
    reference = scorer(frame, 0.5, 3)
    for minimum in [1, 3, 5, 10]:
        for weight in [0, 0.25, 0.5, 0.75, 1]:
            score = scorer(frame, weight, minimum)
            comparable = score.notna() & reference.notna()
            a, b = score[comparable], reference[comparable]
            rank_corr = None
            if len(a) > 1 and a.nunique() > 1 and b.nunique() > 1:
                rank_corr = float(a.rank().corr(b.rank()))
            delta = (a - b).abs()
            rows.append(
                {
                    "minimum_records": minimum,
                    "age_weight": weight,
                    "eligible_parcels": int(score.notna().sum()),
                    "eligible_share": float(score.notna().mean()) if len(score) else None,
                    "comparable_with_baseline": int(comparable.sum()),
                    "median_absolute_change": float(delta.median()) if len(delta) else None,
                    "max_absolute_change": float(delta.max()) if len(delta) else None,
                    "rank_correlation": rank_corr,
                }
            )
    return pd.DataFrame(rows)


def csv_export(frame):
    """Neutraliza fórmulas de hojas de cálculo en cadenas; conserva números y nulos."""
    out = frame.copy()
    for col in out.select_dtypes(include=["object", "string"]).columns:
        out[col] = out[col].map(
            lambda value: "'" + value
            if isinstance(value, str)
            and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n"))
            else value
        )
    return out.to_csv(index=False).encode("utf-8-sig")


def explain_profile(row):
    """Explicación individual sin trasladar atributos de vivienda al edificio."""
    count, valid = int(row.ceee_records_observed), int(row.ceee_valid_grade_count)
    share = (
        "desconocida"
        if pd.isna(row.ceee_efg_share_observed)
        else f"{100 * row.ceee_efg_share_observed:.1f}%"
    )
    construction = (
        "Periodo no disponible."
        if not row.construction_available
        else f"Año más antiguo {int(row.construction_oldest_year)} del agregado BU; no es fecha de reforma."
    )
    return {
        "Contexto constructivo": construction,
        "Evidencia energética": f"{count} registros vinculados; {valid} con letra A–G. Proporción E/F/G observada: {share}.",
        "Perfil descriptivo": row.energy_profile,
        "Revisión de evidencia": row.review_flags
        or "Sin avisos adicionales en los campos disponibles.",
        "Límite": "Localización en parcela; no confirma cobertura energética del edificio físico.",
    }
