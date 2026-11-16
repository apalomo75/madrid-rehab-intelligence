"""Priority evidence filters over authenticated, admitted parcel identities."""

from functools import lru_cache

import pandas as pd

from . import commercial_catalog_store as store
from .data_recovery_audit import CONSERVATION

LABELS = {
    "energy": "Solo CEEE",
    "ite": "Solo ITE/IEE",
    "rehabilita": "Solo Plan Rehabilita",
    "prtr": "Solo ayudas PRTR",
}
RESTRICTED = {"rehabilita", "prtr"}
PUBLIC_BLOCK = (
    "Publicación externa bloqueada: licencia/procedencia de PRTR y Plan Rehabilita "
    "pendientes. Sus filtros y evidencias están deshabilitados en modo público. "
    "La membresía pública del catálogo no autoriza la redistribución."
)


def inspection_rows(events):
    """Only dated, confirmed obligations or explicitly attributed indirect mentions."""
    date = pd.to_datetime(events.date, format="mixed", errors="coerce").notna()
    specific = events.event_type.isin(["ite_pending", "iee_pending"]) | (
        events.event_type.eq("order")
        & events.indirect_unfavorable_mention.fillna(False)
        & events.description.fillna("").str.contains(r"\b(?:ITE|IEE)\b", case=False, regex=True)
    )
    return events[
        date
        & specific
        & events.match_status.eq("confirmed")
        & ~events.identity_conflict
        & events.is_conservation_evidence
    ]


@lru_cache(maxsize=4)
def _inspection_refs(token):
    events = pd.read_parquet(
        CONSERVATION / "conservation_events.parquet",
        columns=[
            "parcel_ref14",
            "date",
            "event_type",
            "match_status",
            "identity_conflict",
            "is_conservation_evidence",
            "indirect_unfavorable_mention",
            "description",
        ],
    )
    return frozenset(inspection_rows(events).parcel_ref14)


def inspection_refs():
    store.metadata()  # Its manifest authenticates this exact event product.
    return _inspection_refs(store.signature(store.root_path()))


def combine(index, selected=(), logic="OR", public=False, ite_refs=()):
    if logic not in {"OR", "AND"} or set(selected) - LABELS.keys():
        raise ValueError("Filtros inválidos")
    result = index.copy()
    result["ite"] = result.parcel_ref14.isin(ite_refs)
    if public:
        for key in RESTRICTED:
            result[key] = False
    if selected:
        masks = result[list(selected)].astype(bool)
        result = result[masks.all(axis=1) if logic == "AND" else masks.any(axis=1)]
    return result.drop_duplicates("parcel_ref14").reset_index(drop=True)


def query(code, selected=(), logic="OR"):
    return combine(
        store.parcel_index(code),
        selected,
        logic,
        store.mode() == "public",
        inspection_refs() if code == "28079" else (),
    )


def list_details(code, refs):
    """Bounded postal lookup; never instantiate a fiche to label a result."""
    refs = tuple(refs)
    result = {ref: {} for ref in refs}
    if code != "28079" or not refs:
        return result
    from . import demo

    rows = demo.read(
        demo.CITY,
        "parcels_audited.parquet",
        [("parcel_ref14", "in", list(refs))],
        columns=["parcel_ref14", "district_code"],
    )
    from .commercial_geography import district_names

    names = district_names()
    for _, row in rows.iterrows():
        if row.district_code in names:
            result[row.parcel_ref14]["district"] = names[row.district_code]
    lookup = _postal_labels(store.signature(store.root_path()), store.mode())
    for ref in refs:
        if ref in lookup:
            result[ref]["address"] = lookup[ref]
    return result


@lru_cache(maxsize=4)
def _postal_labels(token, active_mode):
    import json

    with store.connect() as db:
        rows = db.execute(
            "SELECT original,"
            + active_mode
            + "_refs FROM addresses WHERE "
            + active_mode
            + "_visible=1 ORDER BY original"
        ).fetchall()
    labels = {}
    for address, refs in rows:
        for ref in json.loads(refs):
            labels.setdefault(ref, address)
    return labels


def evidence_labels(row):
    labels = [label.removeprefix("Solo ") for key, label in LABELS.items() if row[key]]
    if row.get("construction", False):
        labels.append("Datos constructivos documentados")
    if row.get("administrative", False) and not row["ite"]:
        labels.append("Antecedente administrativo confirmado")
    return labels


def context_key(selected, logic):
    return logic + "_" + "_".join(sorted(selected))
