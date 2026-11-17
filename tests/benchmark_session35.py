"""Public candidate geography and bounded map benchmark, without claiming WebGL validation."""

import argparse
import json
from pathlib import Path
import resource
import sqlite3
from time import perf_counter
from unittest.mock import patch
from urllib.parse import unquote, urlparse

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab import commercial_filters as filters, neighborhoods as geo
from madrid_rehab import production_bundle as bundle
from madrid_rehab.map_pagination import page_count


def run(output):
    if output.exists():
        raise FileExistsError("New report required")
    start = perf_counter()
    meta = bundle.metadata()
    assert meta.get("geography") and bundle.allowed_prtr()
    root = bundle.root()
    accesses = set()
    original_read, original_connect = pd.read_parquet, sqlite3.connect

    def guard(path):
        raw = str(path)
        candidate = Path(unquote(urlparse(raw).path) if raw.startswith("file:") else raw).resolve()
        assert candidate.is_relative_to(root), str(candidate)
        accesses.add(candidate.relative_to(root).as_posix())

    def read(path, *args, **kwargs):
        guard(path)
        return original_read(path, *args, **kwargs)

    def connect(path, *args, **kwargs):
        guard(path)
        return original_connect(path, *args, **kwargs)

    stages = []

    def record(name, app):
        assert not app.exception, [e.message for e in app.exception]
        assert not app.error, [e.value for e in app.error]
        charts = app.get("deck_gl_json_chart")
        features = (
            json.loads(charts[0].proto.json)["layers"][0]["data"]["features"] if charts else []
        )
        assert len(features) <= 500
        stages.append(
            {
                "stage": name,
                "seconds_since_start": perf_counter() - start,
                "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                "map_features": len(features),
                "count": app.metric[0].value,
            }
        )

    with (
        patch("pandas.read_parquet", side_effect=read),
        patch("sqlite3.connect", side_effect=connect),
    ):
        app = AppTest.from_string(
            "from madrid_rehab.i18n import language_selector\nlanguage_selector()\nfrom madrid_rehab.commercial_catalog_view import render\nrender()",
            default_timeout=180,
        ).run()
        record("initial_madrid", app)
        prefix = "municipal_28079__cp_catalog_public_OR_"
        app.button(key=prefix + "_map_next").click().run()
        record("map_middle", app)
        pages = page_count(int(app.metric[0].value.replace(",", "")))
        app.session_state[prefix + "_map_page_all"] = pages - 1
        app.run()
        assert app.button(key=prefix + "_map_next").disabled
        record("map_last", app)
        for district, neighborhood, name in [
            ("17", "174", "los_rosales"),
            ("07", "071", "gaztambide"),
        ]:
            app.selectbox(key="catalog_district").set_value(district).run()
            app.selectbox(key="catalog_neighborhood").set_value(neighborhood).run()
            record(name, app)
        app.checkbox(key="priority_28079_energy").check().run()
        app.checkbox(key="priority_28079_prtr").check().run()
        record("gaztambide_ceee_prtr_or", app)
        app.radio(key="priority_logic_28079").set_value("AND").run()
        record("gaztambide_ceee_prtr_and", app)
        app.radio(key="language_selector").set_value("EN").run()
        record("english", app)
        full = filters.query("28079")
        assignments = geo.read("assignments.parquet")
        admitted = full[["parcel_ref14"]].merge(
            assignments, on="parcel_ref14", validate="one_to_one", how="left"
        )
        counts = (
            admitted[admitted.status.eq("assigned")]
            .groupby("neighborhood_code")
            .size()
            .rename("commercial_parcels")
            .reset_index()
        )
        counts = (
            geo.read("neighborhoods.parquet")
            .merge(counts, on="neighborhood_code", how="left")
            .fillna({"commercial_parcels": 0})
        )
        assert counts.commercial_parcels.sum() == admitted.status.eq("assigned").sum()
    report = {
        "passed": True,
        "candidate": str(root),
        "new_geography_bytes": sum(
            meta["files"]["geography/" + n]["bytes"]
            for n in ("neighborhoods.parquet", "assignments.parquet")
        ),
        "source": meta["geography"]["source"],
        "spatial_build": meta["geography"]["summary"],
        "commercial_madrid_parcels": len(full),
        "commercial_assigned": int(admitted.status.eq("assigned").sum()),
        "commercial_unassigned": int(admitted.status.ne("assigned").sum()),
        "commercial_unassigned_reasons": admitted.loc[admitted.status.ne("assigned"), "status"]
        .fillna("missing_assignment")
        .value_counts()
        .to_dict(),
        "by_neighborhood": counts.to_dict("records"),
        "stages": stages,
        "accessed_files": sorted(accesses),
        "total_seconds": perf_counter() - start,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "webgl_validated": False,
        "mobile_visual_validated": False,
        "cloud_memory_measured": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in {"by_neighborhood", "accessed_files", "source"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
