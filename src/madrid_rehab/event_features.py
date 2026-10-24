"""Extensión opcional de eventos canónicos revisados; no descarga ni confirma edificios."""

import pandas as pd
import json
from pathlib import Path
from .ingest import digest

from .events import grant_summary
from .features import require_columns


def aggregate_event_features(features, inspections=None, grants=None):
    """None = no integrado; tabla vacía = captura revisada sin enlaces, no ausencia real.

    El llamante debe normalizar, hacer matching y revisar procedencia/licencia antes.
    No se usan candidatos, ambiguos, importes de otras fases ni registros territoriales.
    """
    if features.parcel_ref14.duplicated().any():
        raise ValueError("El universo de parcelas debe ser único")
    out = features.copy().set_index("parcel_ref14")
    for kind, events in [("inspection", inspections), ("grant", grants)]:
        if events is None:
            continue
        fields = ["authority", "event_id", "parcel_ref14", "match_status", "match_level"]
        require_columns(events, fields, kind)
        # Clave de identidad compuesta sin concatenaciones que puedan colisionar.
        duplicate = events.duplicated(["authority", "event_id"], keep=False)
        if duplicate.any():
            raise ValueError(f"{kind}: eventos repetidos; normalizar antes de agregar")
        confirmed = events[
            events.match_status.eq("confirmed")
            & events.match_level.eq("parcel")
            & events.parcel_ref14.isin(out.index)
        ].copy()
        # CP ambigua en el universo nunca acepta un evento confirmado por otra captura.
        confirmed = confirmed[confirmed.parcel_ref14.map(out.cp_rows).eq(1)]
        out[kind + "_source_status"] = "snapshot_reviewed"
        if kind == "inspection":
            require_columns(
                confirmed,
                ["inspection_date_parsed", "result_normalized", "remediation_date_parsed"],
                kind,
            )
            grouped = confirmed.groupby("parcel_ref14")
            out["inspection_records_observed"] = grouped.size().reindex(out.index, fill_value=0)
            date = pd.to_datetime(confirmed.inspection_date_parsed, utc=True, errors="coerce")
            confirmed["date"] = date
            out["inspection_last_observed_date"] = confirmed.groupby("parcel_ref14").date.max()
            confirmed["documented_remediation"] = confirmed.remediation_date_parsed.notna()
            # Nulo si no hay evidencia explícita; False no significa ausencia de subsanación.
            documented = confirmed.groupby("parcel_ref14").documented_remediation.any()
            out["inspection_remediation_documented"] = documented.reindex(out.index).map(
                lambda v: True if pd.notna(v) and v else None
            )
            # No elegir por orden: dos resultados en la misma última fecha quedan ambiguos.
            result = {}
            for ref, group in confirmed.groupby("parcel_ref14"):
                if group.date.notna().any():
                    values = group.loc[
                        group.date.eq(group.date.max()), "result_normalized"
                    ].drop_duplicates()
                    result[ref] = values.iloc[0] if len(values) == 1 else "ambiguous_history"
            out["inspection_last_historical_result"] = pd.Series(result, dtype="string")
        else:
            require_columns(
                confirmed,
                [
                    "phase",
                    "case_id",
                    "program",
                    "amount",
                    "currency",
                    "location_role",
                    "resolution_date_parsed",
                ],
                kind,
            )
            confirmed = confirmed[confirmed.location_role.eq("subsidized_property")]
            # Conciliar globalmente antes de repartir; un expediente con dos parcelas no se duplica.
            all_awards = events[events.phase.eq("award")].copy()
            valid_cases = []
            keys = ["authority", "program", "case_id"]
            for key, group in all_awards.groupby(keys, dropna=False):
                summary = grant_summary(group)
                if summary["unique_consistent_awards"] == 1:
                    valid_cases.append(key)
            eligible = confirmed[confirmed.phase.eq("award")].copy()
            key_series = pd.Series(
                list(eligible[keys].itertuples(index=False, name=None)),
                index=eligible.index,
                dtype=object,
            )
            eligible = eligible[key_series.isin(valid_cases)].drop_duplicates(keys)
            grouped = eligible.groupby("parcel_ref14")
            out["grant_awards_observed"] = grouped.size().reindex(out.index, fill_value=0)
            euros = eligible[eligible.currency.eq("EUR")]
            out["grant_known_eur_awarded"] = euros.groupby("parcel_ref14").amount.sum(min_count=1)
            out["grant_known_eur_amount_count"] = (
                euros.groupby("parcel_ref14").amount.count().reindex(out.index, fill_value=0)
            )
            out["grant_last_award_date"] = grouped.resolution_date_parsed.max()
    return out.reset_index()


def load_event_snapshot(root, kind, cp_hash):
    """Acepta solo la captura canónica íntegra cruzada contra la misma versión CP."""
    root = Path(root)
    metadata_hash = digest(root / "manifest.json")
    metadata = json.loads((root / "manifest.json").read_text())
    if metadata["kind"] != kind or metadata["parcels_sha256"] != cp_hash:
        raise ValueError("Eventos de otro tipo o de una captura CP diferente")
    path = root / "events.parquet"
    if digest(path) != metadata["output_sha256"]:
        raise ValueError("Eventos no coinciden con su manifiesto")
    data = pd.read_parquet(path)
    if len(data) != metadata["rows"]:
        raise ValueError("Número de eventos no coincide con manifiesto")
    if digest(root / "manifest.json") != metadata_hash or digest(path) != metadata["output_sha256"]:
        raise ValueError("Eventos modificados durante la lectura")
    return data, {"manifest_sha256": metadata_hash, "events_sha256": metadata["output_sha256"]}
