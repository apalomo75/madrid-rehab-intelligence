"""Adaptadores de preparación. No son registros adquiridos ni autorizan su publicación."""

import pandas as pd

from .events import normalize_events
from .features import require_columns
from .official_sources import SOURCES
from .territory import CODES

# Diccionario público: Agencia de Actividades, CSV 2019 (no extrapolar al XLSX 2026).
URBAN_COLUMNS = [
    "No orden",
    "Tipo de Via",
    "Calle",
    "Distrito",
    "Codigo Distrito",
    "Materia objeto de la inspeccion",
    "Mes",
    "Ano",
]
EVENT_TYPES = {
    "ite_iee": "inspection",
    "urban_inspection": "inspection",
    "grant_call": "grant",
    "grant_award": "grant",
    "grant_phase": "grant",
}


def normalize_reviewed_events(frame, event_type, capture_id, version):
    """Extiende el contrato previo con tipo separado y procedencia de captura.

    No vincula coordenadas/direcciones ni confirma edificio. Esquema canónico
    revisado, no parser universal de expedientes oficiales aún no adquiridos.
    """
    if event_type not in EVENT_TYPES or not capture_id.strip() or not version.strip():
        raise ValueError("Tipo, captura y versión obligatorios")
    kind = EVENT_TYPES[event_type]
    if event_type == "ite_iee" and not frame.empty:
        require_columns(frame, ["inspection_type"], event_type)
        if not frame.inspection_type.isin(["ITE", "IEE"]).all():
            raise ValueError("ITE/IEE requiere tipo explícito")
    if event_type == "urban_inspection" and not frame.empty:
        require_columns(frame, ["inspection_type"], event_type)
        if frame.inspection_type.fillna("").str.upper().isin(["ITE", "IEE"]).any():
            raise ValueError("No mezclar inspección urbanística con ITE/IEE")
    out = normalize_events(frame, kind)
    expected = {"grant_call": "call", "grant_award": "award"}.get(event_type)
    if expected and not out.phase.eq(expected).all():
        raise ValueError("Fase incompatible con tipo de evento")
    if event_type == "grant_phase" and out.phase.isin(["call", "award"]).any():
        raise ValueError("Convocatorias y concesiones tienen contratos separados")
    out["event_type"] = event_type
    out["capture_id"] = capture_id
    out["source_version"] = version
    out["validation_status"] = "normalized_requires_review"
    out["spatial_precision"] = "unverified"
    return out


def normalize_urban_2019(frame, capture_id, extracted_at=None):
    """Contrato derivado de columnas públicas, sin inmuebles confirmados.

    Se omiten nombres de vías del producto: calle sin portal no identifica parcela.
    La clave original solo es única dentro de esta captura; no es expediente persistente.
    """
    require_columns(frame, URBAN_COLUMNS, "urban_2019")
    if not capture_id.strip():
        raise ValueError("Captura obligatoria")
    out = frame[URBAN_COLUMNS].copy().drop_duplicates()
    if out["No orden"].isna().any() or out["No orden"].astype(str).str.strip().eq("").any():
        raise ValueError("Identificador de fila ausente")
    out["No orden"] = out["No orden"].astype(str).str.strip()
    if out["No orden"].duplicated().any():
        raise ValueError("Identificador repetido con contenido contradictorio")
    district = out["Codigo Distrito"].astype("string").str.strip().str.zfill(2)
    month = pd.to_numeric(out.Mes, errors="coerce")
    year = pd.to_numeric(out.Ano, errors="coerce")
    valid_date = month.between(1, 12) & month.mod(1).eq(0) & year.eq(2019)
    return pd.DataFrame(
        {
            "event_id": out["No orden"],
            "capture_id": capture_id,
            "source_url": SOURCES["urban_2019"]["url"],
            "source_version": "2019",
            "extracted_at": extracted_at,
            "district_code_raw": out["Codigo Distrito"],
            "month_raw": out["Mes"],
            "year_raw": out["Ano"],
            "event_type": "urban_inspection",
            "municipality_code": "28079",
            "district_code": district.where(district.isin(CODES)),
            "category_raw": out["Materia objeto de la inspeccion"],
            "year": year.where(valid_date),
            "month": month.where(valid_date),
            "date_invalid": ~valid_date,
            "temporal_precision": "month",
            "spatial_precision": district.isin(CODES).map({True: "district", False: "unlocated"}),
            "parcel_ref14": None,
            "validation_status": "normalized_requires_review",
        }
    ).reset_index(drop=True)
