"""Offline integrity, evidence reach and incidence report for the enriched snapshot."""

import argparse
from collections import Counter
import json
from pathlib import Path

import pandas as pd
import shapely as sh

from .cadastre_attributes import ATTRIBUTES
from .cadastre_enrichment import (
    ACCEPTED,
    CODES,
    DEFAULT,
    RAW,
    check_resume,
    code_hashes,
    verify_inputs,
)
from .ingest import digest, save_json
from .pilot_grants import CONFIRMED

ENERGY = Path("data/processed/energy/session_13_final_03/energy_parcel_links.parquet")
GRANTS = ACCEPTED / "grant_parcel_links.parquet"


def audit(output, enriched=DEFAULT):
    output, enriched = Path(output), Path(enriched)
    if output.exists():
        raise FileExistsError("New audit report directory required")
    output.mkdir(parents=True)
    collection = json.loads((enriched / "manifest.json").read_text())
    if (
        collection.get("municipality_codes") != list(CODES)
        or collection.get("validation_status") != "validated"
    ):
        raise ValueError("Incomplete collection manifest")
    for code in CODES:
        if collection["outputs"][code + "/manifest.json"] != digest(
            enriched / code / "manifest.json"
        ):
            raise ValueError("Collection partition manifest mismatch")
    energy, grants = pd.read_parquet(ENERGY), pd.read_parquet(GRANTS)
    comparisons, reach, examples, disjoint_rows, issues_summary, summaries = [], [], [], [], [], []
    for code in CODES:
        inputs, _, _ = verify_inputs(code, ACCEPTED, RAW)
        manifest = check_resume(enriched / code, inputs, code_hashes())
        bu = (
            pd.read_parquet(ACCEPTED / code / "bu.parquet")
            .sort_values("building_id")
            .reset_index(drop=True)
        )
        columns = list(bu.columns) + [
            name
            for key in ATTRIBUTES
            for name in ("recovered_" + key, "recovered_" + key + "_state")
        ]
        frame = pd.read_parquet(enriched / code / "buildings_enriched.parquet", columns=columns)
        frame = frame.sort_values("building_id").reset_index(drop=True)
        pd.testing.assert_frame_equal(bu, frame[list(bu.columns)])
        assert frame.building_id.is_unique and frame.municipality_code.eq(code).all()
        links = pd.read_parquet(enriched / code / "cp_bu_documentary_links.parquet")
        assert set(links.building_id) == set(bu.building_id)
        assert not links.spatial_assignment_created.any()
        assert not links.physical_building_confirmed.any()
        assert links.loc[links.link_class.eq("A"), "explicit_documentary_reference"].all()
        assert links.loc[links.link_class.eq("A"), "accepted_cp_count"].eq(1).all()
        for typ, group in frame.groupby("source_feature_type"):
            before_group = bu[bu.source_feature_type.eq(typ)]
            previous = {
                "current_use": "current_use",
                "construction_begin": "construction_begin",
                "construction_end": "construction_end",
                "dwellings": "dwellings_raw",
                "building_units": "building_units_raw",
            }
            for key in ATTRIBUTES:
                field = "recovered_" + key
                count = int(group[field + "_state"].eq("declared").sum())
                before = int(before_group[previous[key]].notna().sum()) if key in previous else 0
                comparisons.append(
                    dict(
                        municipality_code=code,
                        source_feature_type=typ,
                        attribute=key,
                        before_nonempty=before,
                        after_valid_declared=count,
                        denominator=len(group),
                        states=group[field + "_state"].value_counts().to_dict(),
                    )
                )
        # Explicit check that no Building use/year/area was inherited by parts.
        parts = frame[frame.source_feature_type.eq("BuildingPart")]
        for key in (
            "current_use",
            "construction_begin",
            "construction_end",
            "official_area",
            "dwellings",
            "building_units",
        ):
            assert parts["recovered_" + key + "_state"].eq("absent").all()
        cp = pd.read_parquet(ACCEPTED / code / "cp.parquet")
        cp_refs = set(cp.parcel_ref14)
        valid = set(links.loc[links.link_class.eq("A"), "cp_reference_normalized"])
        el = energy[energy.municipality_code.eq(code) & energy.link_level.eq("A")]
        gl = grants[
            grants.geographic_municipality_code.eq(code) & grants.match_status.isin(CONFIRMED)
        ]
        er = set(el.parcel_ref14) & cp_refs
        gr = set(gl.parcel_ref14) & cp_refs
        reach.append(
            dict(
                municipality_code=code,
                accepted_cp=len(cp_refs),
                cp_with_validated_bu=len(valid),
                cp_with_ceee=len(er),
                cp_with_prtr=len(gr),
                cp_ceee_and_validated_bu=len(er & valid),
                cp_prtr_and_validated_bu=len(gr & valid),
                cp_both_and_validated_bu=len(er & gr & valid),
                cp_either_and_validated_bu=len((er | gr) & valid),
                bu_receiving_ceee_or_prtr_attributes=0,
            )
        )
        bu_index = bu.set_index("building_id")
        disjoint = links[links.spatial_status.eq("disjoint")].copy()
        for row in disjoint.to_dict("records"):
            bid = row["building_id"]
            parent = bid.rsplit("_part", 1)[0] if "_part" in bid else None
            row["lexical_parent_present_not_confirmed"] = parent in bu_index.index
            row["part_intersects_lexical_parent"] = None
            if parent in bu_index.index:
                row["part_intersects_lexical_parent"] = bool(
                    sh.intersects(
                        sh.from_wkt(bu_index.loc[bid].geometry_wkt),
                        sh.from_wkt(bu_index.loc[parent].geometry_wkt),
                    )
                )
            disjoint_rows.append(row)
        issue = links[links.link_class.ne("A")]
        issues_summary.append(
            dict(
                municipality_code=code,
                link_classes=links.link_class.value_counts().to_dict(),
                issues=len(issue),
                disjoint=len(disjoint),
                disjoint_types=disjoint.source_feature_type.value_counts().to_dict(),
                disjoint_distance_bands={
                    str(k): int(v)
                    for k, v in pd.cut(
                        disjoint.distance_to_declared_cp_m,
                        [0, 0.01, 1, 10, 100, 1000, float("inf")],
                        include_lowest=True,
                    )
                    .value_counts(sort=False)
                    .items()
                },
                disjoint_valid_geometries=int(disjoint.geometry_valid.sum()),
                disjoint_unchanged_reference=int(
                    disjoint.cp_reference_original.eq(disjoint.cp_reference_normalized).sum()
                ),
                disjoint_bu_multipart=int(disjoint.bu_geometry_multipart.eq(True).sum()),
                disjoint_cp_multipart=int(disjoint.cp_geometry_multipart.eq(True).sum()),
                disjoint_version_dates_differ=int(
                    disjoint.record_version_dates_differ.eq(True).sum()
                ),
                temporal_cause_established=int(issue.temporal_cause_established.sum()),
            )
        )
        municipal_examples = json.loads((enriched / code / "examples.json").read_text())
        example_attributes = pd.read_parquet(
            enriched / code / "buildings_enriched.parquet",
            columns=["building_id", "attributes_json"],
            filters=[("building_id", "in", [e["building_id"] for e in municipal_examples])],
        ).set_index("building_id")
        for example in municipal_examples:
            example["municipality_code"] = code
            selected = example_attributes.loc[example["building_id"]]
            assert json.loads(selected.attributes_json) == example["attributes"]
            examples.append(example)
        summaries.append(manifest["summary"])
        print(code, "validated", len(frame), flush=True)
    # Compare S17 definitions directly: usable accepted BU and raw documentary reference.
    pilot_bu = sum(r["enriched_bu"] for r in summaries)
    parts = sum(r["accepted_types"]["BuildingPart"] for r in summaries)
    resolved = sum(r["resolved_accepted_links"] for r in summaries)
    disjoint = sum(r["resolved_disjoint"] for r in summaries)
    assert (pilot_bu, parts, resolved, disjoint) == (332746, 283926, 324772, 1182)
    assert len(examples) >= 20
    pd.DataFrame(comparisons).to_parquet(output / "completeness.parquet", index=False)
    pd.DataFrame(reach).to_csv(output / "evidence_reach.csv", index=False)
    pd.DataFrame(disjoint_rows).to_parquet(output / "s17_disjoint_review.parquet", index=False)
    pd.DataFrame(disjoint_rows).drop(columns=["source_href"]).to_csv(
        output / "s17_disjoint_review.csv", index=False
    )
    save_json(output / "examples.json", examples)
    save_json(output / "issues_summary.json", issues_summary)
    save_json(
        output / "results.json",
        dict(
            status="validated",
            pilot_bu=pilot_bu,
            parts=parts,
            documentary_to_unique_accepted_cp=resolved,
            s17_disjoint=disjoint,
            link_classes=dict(sum((Counter(r["link_classes"]) for r in summaries), Counter())),
            municipalities=summaries,
            evidence_reach=reach,
            examples=len(examples),
            physical_building_confirmations=0,
            automatic_spatial_assignments=0,
            propagated_evidence_records=0,
        ),
    )
    save_json(
        output / "manifest.json",
        dict(
            inputs={
                str(ENERGY): digest(ENERGY),
                str(GRANTS): digest(GRANTS),
                **{
                    str(enriched / code / "manifest.json"): digest(
                        enriched / code / "manifest.json"
                    )
                    for code in CODES
                },
            },
            outputs={p.name: digest(p) for p in output.iterdir()},
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--enriched-dir", type=Path, default=DEFAULT)
    args = parser.parse_args()
    audit(args.output_dir, args.enriched_dir)


if __name__ == "__main__":
    main()
