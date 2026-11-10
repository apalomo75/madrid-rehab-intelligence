"""Offline recovery of attributes on already accepted Madrid Building identities.

Never ingests new BuildingParts or changes CP/BU associations.
"""

import argparse
from functools import lru_cache
import json
import os
from pathlib import Path
import zipfile

import pandas as pd

from .cadastre_attributes import encoded, flat_attributes, iter_features, parse_feature
from .ingest import digest

DEFAULT = Path("data/processed/cadastre/session_22_madrid_01")
RAW = Path("data/raw/session_1/edificios_28900.zip")
HISTORICAL = Path("data/processed/session_2/buildings_audited.parquet")
CP = Path("data/processed/session_2/parcels_audited.parquet")
KEYS = ("official_area", "condition", "building_units")
VERSION = "madrid-existing-building-attributes-v1"


def same_documentary_identity(record, old):
    refs = record["documentary_references"]
    return (
        record["source_feature_type"] == "Building"
        and record["building_id"] == old["building_id"]
        and len(refs) == 1
        and refs[0]["reference_state"] == "explicit"
        and refs[0]["cp_reference_original"] == old["parcel_ref14"]
        and record["external_references"] == [old["parcel_ref14"]]
    )


def recover(output=DEFAULT):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    source_meta = json.loads(RAW.with_suffix(".zip.json").read_text())
    city = json.loads(Path("data/processed/session_7_final/manifest.json").read_text())
    inputs = {str(p): digest(p) for p in (RAW, HISTORICAL, CP, RAW.with_suffix(".zip.json"))}
    if (
        inputs[str(RAW)] != source_meta["sha256"]
        or inputs[str(HISTORICAL)] != city["inputs"]["buildings_audited"]
        or inputs[str(CP)] != city["inputs"]["parcels_audited"]
    ):
        raise ValueError("Historical source mismatch")
    old = pd.read_parquet(HISTORICAL, columns=["building_id", "parcel_ref14", "usable_geometry"])
    old = old[old.usable_geometry & ~old.building_id.duplicated(keep=False)]
    cp = pd.read_parquet(CP, columns=["parcel_ref14", "usable_geometry"])
    accepted = set(
        cp.loc[cp.usable_geometry & ~cp.parcel_ref14.duplicated(keep=False), "parcel_ref14"]
    )
    lookup = old.set_index("building_id", drop=False).to_dict("index")
    rows, rejected, seen = [], [], set()
    with zipfile.ZipFile(RAW) as archive:
        member = next(n for n in archive.namelist() if n.endswith(".building.gml"))
        with archive.open(member) as stream:
            for ordinal, node in iter_features(stream):
                record = parse_feature(node)
                bid = record["building_id"]
                if bid in seen:
                    raise ValueError("Duplicate original Building identity")
                seen.add(bid)
                historical = lookup.get(bid)
                if (
                    not historical
                    or historical["parcel_ref14"] not in accepted
                    or not same_documentary_identity(record, historical)
                ):
                    rejected.append(
                        dict(building_id=bid, reason="not_existing_usable_unique_documentary_pair")
                    )
                    continue
                flat = flat_attributes(record)
                rows.append(
                    dict(
                        building_id=bid,
                        parcel_ref14=historical["parcel_ref14"],
                        source_feature_type="Building",
                        source_zip_sha256=inputs[str(RAW)],
                        source_gml_member=member,
                        source_ordinal=ordinal,
                        source_date="2026-08-21T00:00:00Z",
                        captured_at=source_meta["captured_at"],
                        **{
                            k: flat[k]
                            for key in KEYS
                            for k in ("recovered_" + key, "recovered_" + key + "_state")
                        },
                        attributes_json=encoded({k: record["attributes"][k] for k in KEYS}),
                        documentary_references_json=encoded(record["documentary_references"]),
                    )
                )
    result = pd.DataFrame(rows).sort_values(["parcel_ref14", "building_id"])
    if not result.building_id.is_unique:
        raise ValueError("Ambiguous output")
    output.mkdir(parents=True)
    result.to_parquet(output / "building_attributes.parquet", index=False, row_group_size=1024)
    pd.DataFrame(rejected).to_csv(output / "excluded.csv", index=False)
    meta = dict(
        version=VERSION,
        validation_status="validated",
        inputs=inputs,
        outputs={
            name: digest(output / name) for name in ("building_attributes.parquet", "excluded.csv")
        },
        rows=len(result),
        excluded=len(rejected),
        rule="same original Building ID and explicit CP and external reference; accepted historical CP/BU only; no new relations",
        original_buildingparts_activated=0,
        code_sha256=digest(Path(__file__)),
    )
    (output / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def token(root):
    paths = [root / "manifest.json", root / "building_attributes.parquet", CP, HISTORICAL]
    return tuple(
        (str(p), p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
    )


@lru_cache(maxsize=4)
def verify(root, signature):
    root = Path(root)
    meta = json.loads((root / "manifest.json").read_text())
    if meta.get("version") != VERSION or meta.get("validation_status") != "validated":
        raise ValueError("Incompatible recovery contract")
    for p in (CP, HISTORICAL):
        if digest(p) != meta["inputs"][str(p)]:
            raise ValueError("Recovery incompatible with historical identity")
    if (
        digest(root / "building_attributes.parquet")
        != meta["outputs"]["building_attributes.parquet"]
    ):
        raise ValueError("Altered recovered attributes")


@lru_cache(maxsize=64)
def _read(root, signature, ids):
    verify(root, signature)
    result = pd.read_parquet(
        Path(root) / "building_attributes.parquet", filters=[("building_id", "in", list(ids))]
    )
    if not result.building_id.is_unique:
        raise ValueError("Ambiguous recovered identity")
    return result


def supplement(records, root=DEFAULT):
    """Only supplement rows already supplied by the authenticated historical reader."""
    root = Path(root)
    if records.empty or not root.exists():
        return records
    if "building_id" not in records:
        raise ValueError("Missing original Building identity")
    active_city = Path(
        os.environ.get("MADRID_REHAB_SESSION7_DIR", "data/processed/session_7_final")
    )
    active_inputs = json.loads((active_city / "manifest.json").read_text())["inputs"]
    meta = json.loads((root / "manifest.json").read_text())
    if (
        active_inputs["buildings_audited"] != meta["inputs"][str(HISTORICAL)]
        or active_inputs["parcels_audited"] != meta["inputs"][str(CP)]
    ):
        raise ValueError("Recovery incompatible with active municipal snapshot")
    extra = _read(str(root), token(root), tuple(sorted(records.building_id.unique())))
    # A filter by ID never permits silently changing its documentary CP.
    if "parcel_ref14" in records:
        pairs = records[["building_id", "parcel_ref14"]].merge(
            extra[["building_id", "parcel_ref14"]], on="building_id", suffixes=("_old", "_new")
        )
        if not pairs.parcel_ref14_old.eq(pairs.parcel_ref14_new).all():
            raise ValueError("Documentary CP mismatch")
    columns = ["building_id", *[c for c in extra if c.startswith("recovered_")]]
    if "source_feature_type" not in records:
        columns.append("source_feature_type")
    return records.merge(extra[columns], on="building_id", how="left", validate="many_to_one")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(recover(args.output_dir)))
