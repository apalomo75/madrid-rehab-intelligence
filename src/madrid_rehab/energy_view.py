"""Consulta energética selectiva; no publica datos mientras la licencia esté pendiente."""

import json
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from .ingest import digest
from .regional_energy import DEFAULT

LABELS = {
    "observation_date": "Fecha declarada en la fuente",
    "consumption_rating": "Letra de consumo",
    "emissions_rating": "Letra de emisiones",
    "consumption_value": "Consumo · unidad sin verificar",
    "emissions_value": "Emisiones · unidad sin verificar",
    "scope": "Ámbito declarado",
    "source_id": "Captura",
    "link_level": "Nivel del vínculo",
    "link_reason": "Evidencia del vínculo",
}
SCOPE_LABELS = {
    "individual_unit": "Vivienda individual",
    "whole_building": "Edificio completo declarado",
    "commercial_unit": "Local",
    "unknown": "Desconocido",
}


def enabled():
    return os.environ.get("MADRID_REHAB_PUBLIC", "0") != "1"


def root_path():
    return Path(os.environ.get("MADRID_REHAB_ENERGY_DIR", str(DEFAULT)))


@st.cache_data(max_entries=24, show_spinner=False)
def read_verified(root, relative, signature, ref=None, ids=None, columns=None):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    path = root / relative
    if digest(path) != manifest["outputs"][relative]:
        raise ValueError("Producto energético alterado")
    filters = [("parcel_ref14", "==", ref)] if ref is not None else None
    if ids is not None:
        filters = [("certificate_id", "in", list(ids))]
    result = pd.read_parquet(path, filters=filters, columns=columns)
    if (root / "manifest.json").stat().st_mtime_ns != signature[0]:
        raise ValueError("Captura energética cambiada")
    return result


def read(relative, ref=None, ids=None, columns=None):
    root = root_path()
    info = (root / relative).stat()
    signature = (
        (root / "manifest.json").stat().st_mtime_ns,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )
    return read_verified(str(root), relative, signature, ref, ids, columns)


def render_energy_region(code=None):
    if not enabled() or not (root_path() / "manifest.json").exists():
        return
    st.markdown("**Evidencia energética regional · fuentes integradas**")
    frame = read("energy_municipality_summary.parquet")
    if code is not None:
        frame = frame[frame.municipality_code.eq(code)]
    st.dataframe(
        frame[
            [
                "name",
                "canonical_certificates",
                "confirmed_cp_certificates",
                "date_min",
                "date_max",
                "cp_integrated",
            ]
        ].rename(
            columns={
                "name": "Municipio",
                "canonical_certificates": "Observaciones canónicas",
                "confirmed_cp_certificates": "Con parcela confirmada",
                "date_min": "Primera fecha declarada",
                "date_max": "Última fecha declarada",
                "cp_integrated": "Catastro integrado (cobertura parcial)",
            }
        ),
        hide_index=True,
    )
    st.caption(
        "Capturas disponibles, sin exhaustividad. Las fechas no acreditan vigencia. Una letra de vivienda no califica el edificio. Licencia energética pendiente: consulta local."
    )

    if code is None:
        choices = frame[frame.canonical_certificates.gt(0)].set_index("municipality_code")
        code = st.selectbox(
            "Consultar energía de un municipio",
            choices.index,
            format_func=lambda v: choices.loc[v, "name"],
            key="energy_municipality",
        )
    detail = frame[frame.municipality_code.eq(code)]
    if not detail.empty:
        row = detail.iloc[0]
        distribution = pd.DataFrame(
            {
                "Letra": list("ABCDEFG"),
                "Consumo": [int(row["consumption_" + r]) for r in "ABCDEFG"],
                "Emisiones": [int(row["emissions_" + r]) for r in "ABCDEFG"],
            }
        )
        st.dataframe(distribution, hide_index=True)
        valid_pct = (
            100 * row.valid_reference_certificates / row.canonical_certificates
            if row.canonical_certificates
            else 0
        )
        st.caption(
            f"Referencia con estructura válida: {valid_pct:.1f}%. Edificio completo declarado: {row.whole_building_count:,}; vivienda individual: {row.individual_unit_count:,}; ámbito desconocido: {row.unknown_count:,}. Estructura válida no prueba existencia catastral."
        )
    if not detail.empty and not bool(detail.iloc[0].cp_integrated):
        st.info(
            "Sin parcelario integrado para este municipio: no se puede calcular la coexistencia CEEE–PRTR por parcela. Los certificados municipales se conservan; no implica ausencia de ayudas."
        )
        return
    joint = read("energy_grants_summary.parquet")
    joint = joint[joint.municipality_code.eq(code)]
    labels = {
        "energy_only_in_sources": "Parcelas solo con CEEE vinculado en estas fuentes",
        "energy_and_prtr": "Parcelas con CEEE y concesión PRTR",
        "prtr_only_in_sources": "Parcelas solo con concesión PRTR vinculada",
    }
    st.dataframe(
        joint.observation.value_counts()
        .rename_axis("Relación")
        .rename("Parcelas")
        .reset_index()
        .replace({"Relación": labels}),
        hide_index=True,
    )
    part = f"municipalities/{code}/links.parquet"
    if (root_path() / part).exists():
        links = read(part, columns=["parcel_ref14", "link_level"])
        refs = sorted(links.loc[links.link_level.eq("A"), "parcel_ref14"].dropna().unique())
        if refs:
            ref = st.selectbox(
                "Consultar certificados de una parcela aceptada", refs, key="energy_parcel_" + code
            )
            render_energy_parcel(code, ref)


def render_energy_parcel(code, ref):
    if not enabled() or not (root_path() / "manifest.json").exists():
        return
    st.markdown("**Información energética regional**")
    path = f"municipalities/{code}/links.parquet"
    if not (root_path() / path).exists():
        st.info("No constan certificados vinculados en las fuentes integradas")
        return
    links = read(path, ref)
    if links.empty:
        st.info("No constan certificados vinculados en las fuentes integradas")
        return
    columns = [
        "certificate_id",
        "observation_date",
        "consumption_rating",
        "emissions_rating",
        "consumption_value",
        "emissions_value",
        "scope",
        "source_id",
        "date_after_capture",
        "identity_status",
    ]
    cert = read(
        f"municipalities/{code}/certificates.parquet",
        ids=tuple(links.certificate_id.unique()),
        columns=columns,
    )
    selected = cert.merge(
        links[["certificate_id", "link_level", "link_reason"]].drop_duplicates(),
        on="certificate_id",
    )
    if (
        selected.date_after_capture.any()
        or selected.identity_status.ne("unique_registration_content").any()
    ):
        st.warning(
            "Hay fechas posteriores a la captura o identidades de inscripción conflictivas. Consultar la auditoría antes de interpretar estas observaciones."
        )
    selected["link_reason"] = selected.link_reason.map(
        {
            "documentary_reference_and_municipality": "Referencia documental y municipio concordantes",
            "multiple_or_mixed_references": "Varias parcelas o referencias de distinta calidad",
            "quarantined_cp": "Parcela en cuarentena",
            "multiple_cp_rows": "Varias filas catastrales para la referencia",
            "suspect_source_column_alignment": "Posible desplazamiento de columnas en origen",
            "no_integrated_cp_coverage": "Sin parcelario integrado",
            "municipality_not_verified": "Municipio sin verificar",
            "no_documentary_identity": "Identificación documental insuficiente",
        }
    ).fillna("Consultar auditoría")
    selected["scope"] = selected.scope.map(SCOPE_LABELS)
    st.dataframe(selected[list(LABELS)].rename(columns=LABELS), hide_index=True)
    st.caption(
        "A: relación documental con parcela aceptada; D: ambigua o en cuarentena. No se ha confirmado ningún objeto BU. Consumo y emisiones conservan valores originales con unidades sin verificar; no se comparan entre unidades distintas."
    )
    coexistence = read("energy_grants_summary.parquet", ref=ref)
    coexistence = coexistence[coexistence.municipality_code.eq(code)]
    grants_count = int(coexistence.grant_case_count.max()) if not coexistence.empty else 0
    if grants_count:
        st.info(
            f"En esta parcela constan {grants_count} expedientes PRTR con vínculo confirmado en las fuentes integradas. Son concesiones administrativas; no se dispone de fecha de concesión individual contrastada. Los importes pertenecen al expediente y no se suman por parcela."
        )
    else:
        st.caption(
            "No constan expedientes PRTR con vínculo confirmado a esta parcela en las fuentes integradas; no acredita ausencia de otras ayudas."
        )
    st.caption(
        "La coincidencia de CEEE y concesión PRTR en una parcela no acredita causalidad, pago ni obras ejecutadas. No se atribuye una calificación a la parcela."
    )


def benchmark():
    start = time.perf_counter()
    summary = read("energy_municipality_summary.parquet")
    regional = time.perf_counter() - start
    start = time.perf_counter()
    links = read("municipalities/28065/links.parquet")
    cert = read("municipalities/28065/certificates.parquet")
    municipal = time.perf_counter() - start
    return {
        "regional_read_seconds": regional,
        "getafe_read_seconds": municipal,
        "regional_rows": len(summary),
        "getafe_certificates": len(cert),
        "getafe_links": len(links),
        "measurement": "Python selective data access, excludes browser rendering",
    }
