"""Offline real-product integrity, samples and measured selective-query costs."""

import json
import resource
import time
from pathlib import Path

import pandas as pd

from madrid_rehab import demo, enriched_cadastre as ec


def run():
    results = []
    for code in json.loads((ec.ROOT / "manifest.json").read_text())["municipality_codes"]:
        start = time.perf_counter()
        meta = ec.metadata(code)
        verification = time.perf_counter() - start
        directory = ec.ROOT / code
        old = demo.read(
            demo.CADASTRE,
            code + "/bu.parquet",
            columns=["building_id", "source_feature_type", "geometry_wkt"],
        )
        new = pd.read_parquet(directory / "buildings_enriched.parquet", columns=list(old.columns))
        pd.testing.assert_frame_equal(
            old.sort_values("building_id").reset_index(drop=True),
            new.sort_values("building_id").reset_index(drop=True),
        )
        relations = pd.read_parquet(directory / "cp_bu_documentary_links.parquet")
        assert relations.link_class.value_counts().to_dict() == meta["summary"]["link_classes"]
        assert set(relations.building_id) == set(new.building_id)
        a = relations[relations.link_class.eq("A")]
        counts = a.groupby("cp_reference_normalized").size().sort_values(ascending=False)
        ref = counts.index[0]
        start = time.perf_counter()
        records, issues = ec.parcel_buildings(code, ref)
        cp_seconds = time.perf_counter() - start
        assert len(records) == counts.iloc[0]
        samples = []
        for cls, kind in [
            ("A", "Building"),
            ("A", "BuildingPart"),
            ("B", "BuildingPart"),
            ("C", "Building"),
        ]:
            relation = relations[
                relations.link_class.eq(cls) & relations.source_feature_type.eq(kind)
            ].iloc[0]
            start = time.perf_counter()
            frame = ec.building(code, relation.building_id)
            elapsed = time.perf_counter() - start
            original = pd.read_parquet(
                directory / "buildings_enriched.parquet",
                filters=[("building_id", "==", relation.building_id)],
            )
            pd.testing.assert_frame_equal(frame, original)
            assert ec.links(code, relation.building_id, "bu").link_class.iloc[0] == cls
            samples.append(
                dict(
                    id=relation.building_id,
                    type=kind,
                    link_class=cls,
                    cp=relation.cp_reference_normalized
                    if pd.notna(relation.cp_reference_normalized)
                    else None,
                    seconds=elapsed,
                    attributes=ec.attribute_table(frame.iloc[0])
                    .drop(columns="Original y procedencia XML")
                    .to_dict("records"),
                )
            )
        cp_source = demo.read(demo.CADASTRE, code + "/cp.parquet", columns=["parcel_ref14"])
        no_bu = cp_source[
            ~cp_source.parcel_ref14.isin(a.cp_reference_normalized)
        ].parcel_ref14.iloc[0]
        assert ec.parcel_buildings(code, no_bu)[0].empty
        start = time.perf_counter()
        ec.parcel_buildings(code, ref)
        warm_seconds = time.perf_counter() - start
        results.append(
            dict(
                code=code,
                rows=len(new),
                classes=meta["summary"]["link_classes"],
                identity_geometry_differences=0,
                schemas=ec.schemas(code),
                verification_seconds=verification,
                largest_cp=ref,
                largest_cp_bu=len(records),
                cp_seconds=cp_seconds,
                cp_cached_seconds=warm_seconds,
                cp_dataframe_bytes=int(records.memory_usage(deep=True).sum()),
                issue_count=len(issues),
                cp_without_A=no_bu,
                samples=samples,
            )
        )
    output = dict(
        municipalities=results,
        peak_rss_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        cache=ec._query.cache_info()._asdict(),
        metadata_cache=ec._verify.cache_info()._asdict(),
    )
    Path("reports/session_19_integration/real_validation.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str)
    )


if __name__ == "__main__":
    run()
