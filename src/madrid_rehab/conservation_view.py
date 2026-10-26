"""Consulta selectiva de evidencia administrativa; licencia pública cerrada por defecto."""

import json
import logging
import os
import re
import time
import tracemalloc
from pathlib import Path

import pandas as pd
import streamlit as st

from .conservation import DEFAULT, POLICY
from .ingest import digest

NOTICE = (
    "Fuente municipal histórica: obligaciones de presentación y órdenes, no actas ITE/IEE. "
    "Una orden antigua o una multa no acreditan deficiencias actuales. Archivo y terminación "
    "no acreditan subsanación. Parcela, acceso y edificio son entidades distintas. "
    "Cobertura parcial; la ausencia de registros no acredita ausencia de incidencias. Uso local."
)
LABELS = {
    "order": "Orden de ejecución histórica",
    "ite_pending": "Obligación de presentación ITE",
    "iee_pending": "Obligación de presentación IEE",
    "license": "Licencia concedida",
    "declaration": "Declaración responsable presentada",
}
DISPLAY = {
    "event_type": "Tipo de actuación",
    "address_raw": "Acceso/dirección de origen",
    "date": "Fecha administrativa",
    "date_semantics": "Naturaleza de la fecha",
    "query_date": "Fecha de consulta original",
    "description": "Motivo original",
    "administrative_status": "Situación administrativa original",
    "source_file": "Fuente",
    "source_row": "Fila original",
    "source_sha256": "SHA-256 original",
    "match_method": "Método de vínculo CP",
    "match_status": "Calidad de vínculo CP",
    "indirect_unfavorable_mention": "Mención indirecta desfavorable en motivo de orden",
}


def enabled():
    return os.environ.get("MADRID_REHAB_PUBLIC", "0") != "1"


def root_path():
    return Path(os.environ.get("MADRID_REHAB_CONSERVATION_DIR", str(DEFAULT)))


def signature(root, relative):
    return tuple(
        (p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns)
        for p in [root / "manifest.json", root / relative]
    )


@st.cache_data(max_entries=24, show_spinner=False)
def read_verified(root, relative, token, ref, columns=None):
    root = Path(root)
    if signature(root, relative) != token:
        raise ValueError("Captura de conservación cambiada")
    m = json.loads((root / "manifest.json").read_text())
    if m["policy"] != POLICY or digest(root / relative) != m["outputs"][relative]:
        raise ValueError("Producto de conservación alterado o incompatible")
    city = Path(os.environ.get("MADRID_REHAB_SESSION7_DIR", "data/processed/session_7_final"))
    if (
        m["cp_sha256"]
        != json.loads((city / "manifest.json").read_text())["inputs"]["parcels_audited"]
    ):
        raise ValueError("Captura de conservación con Catastro incompatible")
    filters = [("parcel_ref14", "==", ref)]
    if relative == "conservation_parcel_links.parquet":
        filters = [
            [(field, "==", ref)]
            for field in ("parcel_ref14", "confirmed_parcel_ref14", "parcel_candidate")
        ]
    frame = pd.read_parquet(root / relative, filters=filters, columns=columns)
    if signature(root, relative) != token:
        raise ValueError("Captura cambió durante lectura")
    return frame


def parcel_evidence(ref, product="events", municipality="28079"):
    if not enabled():
        return None
    if municipality != "28079":
        return None
    if not re.fullmatch(r"[0-9]{7}[A-Z]{2}[0-9]{4}[A-Z]", ref):
        raise ValueError("Referencia CP no válida")
    if product not in {"events", "profiles", "accesses", "rec_accesses"}:
        raise ValueError("Producto no permitido")
    root = root_path()
    if not (root / "manifest.json").exists():
        return None
    metadata = json.loads((root / "manifest.json").read_text())
    if metadata["policy"] != POLICY:
        raise ValueError("Política de conservación incompatible")
    city = Path(os.environ.get("MADRID_REHAB_SESSION7_DIR", "data/processed/session_7_final"))
    if (
        metadata["cp_sha256"]
        != json.loads((city / "manifest.json").read_text())["inputs"]["parcels_audited"]
    ):
        raise ValueError("Catastro incompatible con conservación")
    relative = (
        "conservation_parcel_links.parquet"
        if product == "rec_accesses"
        else f"parcels/{ref[:2]}/{product}.parquet"
    )
    if not (root / relative).exists():
        return pd.DataFrame()
    return read_verified(str(root), relative, signature(root, relative), ref)


def display_events(frame):
    result = frame.copy()
    result["event_type"] = result.event_type.map(LABELS).fillna(result.event_type)
    return result[list(DISPLAY)].rename(columns=DISPLAY)


def render_conservation_parcel(ref, municipality="28079"):
    from .rec_view import render_rec_parcel

    render_rec_parcel(ref, municipality)
    if not enabled():
        return
    st.markdown("**Conservación e inspecciones**")
    st.caption("Captura histórica de conservación independiente de la consulta REC bajo demanda.")
    try:
        frame = parcel_evidence(ref, municipality=municipality)
        if frame is None:
            st.info("No disponible en las fuentes integradas")
            return
        frame = frame[frame.is_conservation_evidence] if not frame.empty else frame
        if not frame.empty:
            st.dataframe(display_events(frame), hide_index=True)
        else:
            st.caption("No constan órdenes ni obligaciones vinculadas en las fuentes integradas.")
        accesses = parcel_evidence(ref, "accesses", municipality)
        if accesses is not None and not accesses.empty:
            st.caption(
                "Accesos municipales con relación documental a esta parcela; no identifican edificio físico."
            )
            st.dataframe(
                accesses[["ndp", "street", "number_raw", "qualifier_raw", "link_status"]].rename(
                    columns={
                        "ndp": "Identificador de portal",
                        "street": "Calle",
                        "number_raw": "Número",
                        "qualifier_raw": "Complemento",
                        "link_status": "Calidad del vínculo",
                    }
                ),
                hide_index=True,
            )
        profile = parcel_evidence(ref, "profiles", municipality)
        if profile is not None and not profile.empty:
            st.caption(
                "Perfil explicable de evidencias vinculadas; sin diagnóstico ni puntuación de riesgo."
            )
            columns = {
                "historical_order_count": "Órdenes históricas",
                "pending_ite_obligation_count": "Obligaciones ITE observadas",
                "pending_iee_obligation_count": "Obligaciones IEE observadas",
                "latest_administrative_date": "Última fecha administrativa (puede ser plazo)",
                "latest_source_observation": "Última consulta de obligaciones",
                "certificate_count": "Contenidos CEEE vinculados",
                "grant_case_count": "Expedientes PRTR vinculados",
                "energy_observed_scope": "Ámbitos de certificados observados",
                "whole_building_certificate_count": "Certificados declarados de edificio completo",
            }
            st.dataframe(profile[list(columns)].rename(columns=columns), hide_index=True)
            st.caption(
                "CEEE y PRTR son evidencias independientes. Su coexistencia no acredita financiación de una orden, obras realizadas ni una calificación energética de la parcela."
            )
        st.caption(NOTICE)
    except (OSError, ValueError, KeyError) as exc:
        logging.getLogger(__name__).exception("Conservation panel read failed")
        st.warning(f"No se puede verificar la evidencia de conservación: {type(exc).__name__}")
        return "error de consulta de conservación"


def render_conservation_activity(frame, key_prefix):
    """Recibe únicamente la partición distrital que ya está cargada por el visor."""
    if not enabled():
        return
    from .conservation import CONSERVATION_TYPES

    frame = frame[frame.event_type.isin(CONSERVATION_TYPES)]
    if frame.empty:
        return
    with st.expander("Conservación · fuentes municipales integradas"):
        st.caption(NOTICE)
        chosen = frame
        for column, title in [
            ("event_type", "Tipo de conservación"),
            ("year", "Año administrativo"),
            ("administrative_status", "Situación de origen"),
            ("match_status", "Calidad del vínculo"),
            ("source_file", "Fuente de conservación"),
        ]:
            values = sorted(frame[column].fillna("").unique())
            selected = st.multiselect(
                title,
                values,
                default=values,
                key=key_prefix + "conservation_" + column,
                format_func=lambda v: LABELS.get(v, v),
            )
            chosen = chosen[chosen[column].isin(selected)]
        st.dataframe(
            chosen[
                [
                    "event_type",
                    "date",
                    "address_raw",
                    "description",
                    "administrative_status",
                    "match_status",
                ]
            ].assign(event_type=lambda d: d.event_type.map(LABELS)),
            hide_index=True,
        )
        st.caption("No hay filtros de dictamen ni deficiencias: no se han integrado actas reales.")


def benchmark(ref="8238105VK3783G"):
    tracemalloc.start()
    started = time.perf_counter()
    frame = parcel_evidence(ref)
    cold = time.perf_counter() - started
    started = time.perf_counter()
    parcel_evidence(ref)
    warm = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return dict(
        parcel_ref14=ref,
        rows=0 if frame is None else len(frame),
        verified_query_s=cold,
        cached_query_s=warm,
        python_peak_mib=peak / 1024**2,
        dataframe_mib=0 if frame is None else frame.memory_usage(deep=True).sum() / 1024**2,
        memory_scope="tracemalloc Python allocations; excludes native Arrow buffers",
    )
