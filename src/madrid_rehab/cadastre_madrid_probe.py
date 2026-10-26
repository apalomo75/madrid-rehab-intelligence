"""Inventory all original Madrid BuildingParts; extract a bounded research-only sample."""

import argparse
from collections import Counter
import json
from pathlib import Path
import time
import zipfile
from urllib.parse import parse_qs, urlsplit

import pandas as pd
import shapely as sh

from .cadastre_attributes import GML, XLINK, encoded, flat_attributes, iter_features, parse_feature
from .ingest import digest, save_json
from .sources import _building_wkt, local_name

DEFAULT = Path("data/processed/cadastre/session_18_madrid_probe_01")


def probe(output=DEFAULT, limit=2000):
    output = Path(output)
    if output.exists():
        raise FileExistsError("New, isolated research output required")
    if not 1 <= limit <= 10000:
        raise ValueError("Probe limited to 1..10000 objects")
    start = time.perf_counter()
    zip_path = Path("data/raw/session_1/edificios_28900.zip")
    cp_path = Path("data/processed/session_2/parcels_audited.parquet")
    bu_path = Path("data/processed/session_2/buildings_audited.parquet")
    district_path = Path("data/processed/session_2/districts.parquet")
    city_manifest = Path("data/processed/session_7_final/manifest.json")
    inputs = {
        str(p): digest(p)
        for p in (
            zip_path,
            zip_path.with_suffix(".zip.json"),
            cp_path,
            bu_path,
            district_path,
            city_manifest,
        )
    }
    meta = json.loads(zip_path.with_suffix(".zip.json").read_text())
    manifest = json.loads(city_manifest.read_text())
    if (
        inputs[str(zip_path)] != meta["sha256"]
        or inputs[str(cp_path)] != manifest["inputs"]["parcels_audited"]
        or inputs[str(bu_path)] != manifest["inputs"]["buildings_audited"]
        or inputs[str(district_path)] != manifest["inputs"]["districts"]
    ):
        raise ValueError("Historical source integrity mismatch")
    buildings = set(pd.read_parquet(bu_path, columns=["building_id"]).building_id)
    cp = pd.read_parquet(cp_path)
    cp = cp[cp.usable_geometry & ~cp.parcel_ref14.duplicated(keep=False)]
    by_ref = cp.set_index("parcel_ref14").to_dict("index")
    samples, ids, inventory, units, district_counts, attributes = (
        [],
        set(),
        Counter(),
        Counter(),
        Counter(),
        Counter(),
    )
    with zipfile.ZipFile(zip_path) as archive:
        member = next(n for n in archive.namelist() if n.endswith(".buildingpart.gml"))
        with archive.open(member) as stream:
            for ordinal, node in iter_features(stream):
                bid = node.get(GML + "id")
                inventory["BuildingPart"] += 1
                inventory["duplicate_part_id_rows_after_first"] += int(bid in ids)
                inventory["exact_id_overlap_with_existing_building"] += int(bid in buildings)
                ids.add(bid)
                inventory["lexical_parent_building_present_not_confirmed"] += int(
                    bid.rsplit("_part", 1)[0] in buildings
                )
                crss = {e.get("srsName") for e in node.iter() if e.get("srsName")}
                inventory["source_crs_25830"] += int(
                    bool(crss) and crss <= {"urn:ogc:def:crs:EPSG::25830", "EPSG:25830"}
                )
                for element in node.iter():
                    if len(element) == 0 and local_name(element.tag) in {
                        "numberOfFloorsAboveGround",
                        "numberOfFloorsBelowGround",
                        "heightBelowGround",
                    }:
                        attributes[local_name(element.tag) + ":declared"] += int(
                            bool(element.text and element.text.strip())
                        )
                        units[local_name(element.tag) + ":" + str(element.get("uom"))] += 1
                refs = []
                for element in node.findall("{*}cadastralParcels"):
                    href = element.get(XLINK, "")
                    url = urlsplit(href)
                    params = {k.lower(): v for k, v in parse_qs(url.query).items()}
                    if (
                        url.hostname == "ovc.catastro.meh.es"
                        and url.path.lower().endswith("/wfscp.aspx")
                        and params.get("storedquerie_id") == ["GetParcel"]
                    ):
                        refs.extend(params.get("refcat", []))
                inventory["documentary_cp_reference"] += int(bool(refs))
                target = by_ref.get(refs[0]) if len(refs) == 1 else None
                inventory["documentary_cp_unique_accepted"] += int(target is not None)
                if target:
                    district_counts[str(target.get("district_code"))] += 1
                if len(samples) < limit:
                    record = parse_feature(node)
                    geometry = _building_wkt(node)
                    samples.append(
                        dict(
                            building_id=bid,
                            source_feature_type="BuildingPart",
                            municipality_code="28079",
                            source_zip=str(zip_path),
                            source_zip_sha256=meta["sha256"],
                            source_gml_member=member,
                            source_ordinal=ordinal,
                            captured_at=meta.get("captured_at"),
                            source_geometry_wkt=geometry["geometry_wkt"],
                            source_geometry_crs=geometry["geometry_crs"],
                            documentary_cp_reference=refs[0] if len(refs) == 1 else None,
                            cp_accepted_candidate_id=target["parcel_id"] if target else None,
                            **flat_attributes(record),
                        )
                    )
    sample = pd.DataFrame(samples)
    shapes = sh.from_wkt(sample.source_geometry_wkt.to_numpy(), on_invalid="ignore")
    sample["source_geometry_valid"] = sh.is_valid(shapes) & ~sh.is_empty(shapes)
    sample["accepted_in_historical_snapshot"] = False
    sample["physical_building_confirmed"] = False
    districts = pd.read_parquet(district_path)
    hits = sh.STRtree(sh.from_wkt(districts.geometry_wkt.to_numpy())).query(
        shapes, predicate="intersects"
    )
    import numpy as np

    sample["intersecting_district_count"] = np.bincount(hits[0], minlength=len(sample))
    output.mkdir(parents=True)
    sample.to_parquet(
        output / "madrid_buildingparts_probe.parquet", index=False, compression="zstd"
    )
    elapsed = time.perf_counter() - start
    summary = dict(
        original_inventory=dict(inventory),
        original_attribute_declarations=dict(attributes),
        original_units=dict(units),
        district_from_documentary_cp_candidate=dict(district_counts),
        sampled_objects=len(sample),
        sample_selection="first_N_source_order_not_representative",
        sampled_valid_geometry=int(sample.source_geometry_valid.sum()),
        sampled_intersecting_district_counts=sample.intersecting_district_count.value_counts().to_dict(),
        sampled_bytes=(output / "madrid_buildingparts_probe.parquet").stat().st_size,
        inventory_plus_sample_seconds=elapsed,
        geometry_validation_scope="sample_only",
        full_madrid_ingestion_performed=False,
    )
    save_json(output / "summary.json", summary)
    for path, sha in inputs.items():
        if digest(path) != sha:
            raise ValueError("Historical source changed during probe")
    save_json(
        output / "manifest.json",
        dict(
            version="madrid-buildingparts-probe-v1",
            validation_status="research_only_not_accepted",
            inputs=inputs,
            outputs={p.name: digest(p) for p in sorted(output.iterdir())},
            code_sha256={
                str(Path(__file__)): digest(__file__),
                str(Path(__file__).with_name("cadastre_attributes.py")): digest(
                    Path(__file__).with_name("cadastre_attributes.py")
                ),
            },
            limit=limit,
            public_exposure=False,
            activation_pointer_created=False,
        ),
    )
    print(encoded(summary), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()
    probe(args.output_dir, args.limit)


if __name__ == "__main__":
    main()
