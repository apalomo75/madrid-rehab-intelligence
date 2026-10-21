"""Normalización conservadora: formato no significa existencia catastral."""

import re
import unicodedata


def text_key(value):
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value)).upper()
    return "".join(c for c in text if not unicodedata.combining(c))


def address_key(value):
    """Clave auxiliar; nunca se utiliza por sí sola para confirmar coincidencias."""
    text = text_key(value)
    text = re.sub(r"^\s*(?:C/|CL\.?\s+|CALLE\s+)", "CALLE ", text)
    text = re.sub(r"^\s*(?:AVDA\.?\s+|AVENIDA\s+)", "AVENIDA ", text)
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", text)).strip()


def split_references(value):
    if value is None or str(value).strip().lower() in {"", "nan", "none", "null"}:
        return [""]
    # Comas, punto y coma y saltos separan referencias; espacios internos no.
    return [part.strip() for part in re.split(r"[,;\n]+", str(value)) if part.strip()] or [""]


def reference(value):
    normalized = re.sub(r"\s+", "", text_key(value))
    base = r"[0-9]{7}[A-Z]{2}[0-9]{4}[A-Z]"
    if re.fullmatch(base, normalized):
        kind = "parcel"
    elif re.fullmatch(base + r"[0-9]{4}[A-Z]{2}", normalized):
        kind = "property"
    else:
        kind = "invalid_or_unsupported"
    return {
        "reference_raw": str(value) if value is not None else "",
        "reference_normalized": normalized,
        "reference_kind": kind,
        "reference_format_valid": kind != "invalid_or_unsupported",
        "parcel_ref14": normalized[:14] if kind != "invalid_or_unsupported" else None,
        "property_ref20": normalized if kind == "property" else None,
        "checksum_status": "not_checked" if kind == "property" else "not_applicable",
    }


def certification_scope(value, reviewed_mapping=None):
    """Sin catálogo contrastado, el ámbito es desconocido y se conserva el original."""
    mapping = {text_key(k).strip(): v for k, v in (reviewed_mapping or {}).items()}
    result = mapping.get(text_key(value).strip(), "unknown")
    if result not in {"dwelling", "building_part", "whole_building", "unknown"}:
        raise ValueError(f"Ámbito no soportado: {result}")
    return result
