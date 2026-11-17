"""Documentary certificate scope, independent of parcel/building multiplicity."""

from functools import lru_cache

from .regional_energy import SCOPES

OPTIONS = ("all", "any", "whole_building", "individual_unit", "other", "unknown")


def classify(original):
    return SCOPES.get(original, "unknown")


def usable(rows):
    return rows[
        rows.identity_status.eq("unique_registration_content") & ~rows.date_after_capture
    ].drop_duplicates("certificate_id")


def memberships(certificates, links):
    certificates = usable(certificates).copy()
    certificates["scope_group"] = certificates.edif_tipo.map(classify)
    return (
        links[links.link_level.eq("A")][["parcel_ref14", "certificate_id"]]
        .merge(certificates[["certificate_id", "scope_group"]], validate="many_to_one")
        .drop_duplicates(["parcel_ref14", "certificate_id"])
    )


@lru_cache(maxsize=6)
def _memberships(code, root, token):
    from . import energy_view

    base = f"municipalities/{code}/"
    certificates = energy_view.read(
        base + "certificates.parquet",
        columns=["certificate_id", "edif_tipo", "identity_status", "date_after_capture"],
    )
    links = energy_view.read(
        base + "links.parquet", columns=["certificate_id", "parcel_ref14", "link_level"]
    )
    rows = memberships(certificates, links)
    return {group: frozenset(frame.parcel_ref14) for group, frame in rows.groupby("scope_group")}


def restrict(index, code, scope):
    if scope not in OPTIONS:
        raise ValueError("Invalid certificate scope")
    if scope in {"all", "any"}:
        return index
    from . import energy_view, production_bundle as bundle

    root = energy_view.root_path()
    if bundle.active():
        bundle.metadata()
        token = bundle.signature()
    else:
        paths = [root / "manifest.json"] + [
            root / f"municipalities/{code}/{name}.parquet" for name in ("certificates", "links")
        ]
        token = tuple((p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths)
    groups = _memberships(code, str(root), token)
    refs = (
        groups.get("commercial_unit", frozenset())
        if scope == "other"
        else groups.get(scope, frozenset())
    )
    return index[index.parcel_ref14.isin(refs)].reset_index(drop=True)
