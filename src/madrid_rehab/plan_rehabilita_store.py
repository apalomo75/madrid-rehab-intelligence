"""Authenticated selective Plan Rehabilita reader, private CP scope only."""

from functools import lru_cache
import json
import os
from pathlib import Path

import pandas as pd

from . import address_search, demo
from .ingest import digest
from .plan_rehabilita import CP, DEFAULT, VERSION


def root_path():
    return Path(os.environ.get("MADRID_REHAB_REHABILITA_DIR", str(DEFAULT)))


def signature(root):
    paths = [
        CP,
        root / "manifest.json",
        *sorted(root.glob("*.parquet")),
        address_search.root_path() / "addresses.sqlite",
        Path(os.environ.get("MADRID_REHAB_SESSION7_DIR", "data/processed/session_7_final"))
        / "manifest.json",
    ]
    return tuple(
        (str(p), p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
    )


@lru_cache(maxsize=4)
def verify(root, token):
    root = Path(root)
    meta = json.loads((root / "manifest.json").read_text())
    if meta.get("version") != VERSION or meta.get("validation_status") != "validated":
        raise ValueError("Incompatible Plan Rehabilita contract")
    city = Path(os.environ.get("MADRID_REHAB_SESSION7_DIR", "data/processed/session_7_final"))
    cp_sha = json.loads((city / "manifest.json").read_text())["inputs"]["parcels_audited"]
    if (
        meta["cp_sha256"] != cp_sha
        or digest(address_search.root_path() / "addresses.sqlite") != meta["postal_sha256"]
    ):
        raise ValueError("Plan Rehabilita incompatible with current CP/postal snapshot")
    if digest(CP) != meta["cp_sha256"]:
        raise ValueError("Plan Rehabilita CP source altered")
    for name, sha in meta["outputs"].items():
        if digest(root / name) != sha:
            raise ValueError("Altered Plan Rehabilita product: " + name)
    return meta


@lru_cache(maxsize=32)
def _query(root, token, ref):
    verify(root, token)
    root = Path(root)
    locations = pd.read_parquet(
        root / "locations.parquet", filters=[("parcel_ref14", "==", ref), ("link_class", "==", "A")]
    )
    if locations.empty:
        return pd.DataFrame()
    cases = pd.read_parquet(
        root / "cases.parquet", filters=[("case_id", "in", locations.case_id.tolist())]
    )
    if cases.case_id.duplicated().any() or not cases.identity_usable.all():
        raise ValueError("Ambiguous municipal case identity")
    result = locations.merge(cases, on="case_id", validate="one_to_one", suffixes=("_link", ""))
    actions = pd.read_parquet(
        root / "actions.parquet", filters=[("case_id", "in", locations.case_id.tolist())]
    )
    grouped = actions.groupby("case_id").category.agg(lambda s: " · ".join(sorted(set(s))))
    result["categories"] = result.case_id.map(grouped).fillna("No determinada")
    return result


def parcel_records(code, ref, kind="cp", *, public_catalog=False):
    if (not demo.private() and not public_catalog) or code != "28079" or kind != "cp":
        return pd.DataFrame()
    root = root_path()
    address_search.metadata(address_search.root_path())
    if not root.exists():
        return None
    return _query(str(root), signature(root), ref).copy(deep=True)


def catalogue():
    address_search.metadata(address_search.root_path())
    root = root_path()
    verify(str(root), signature(root))
    cases = pd.read_parquet(root / "cases.parquet")
    links = pd.read_parquet(root / "locations.parquet")
    actions = pd.read_parquet(root / "actions.parquet")
    return cases, links, actions
