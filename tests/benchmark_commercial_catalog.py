"""Real record review and catalogue search latency; no web or source mutation."""

import argparse
import json
from pathlib import Path
import re
import time

import pandas as pd

from madrid_rehab import commercial_catalog as cc, commercial_catalog_store as store
from madrid_rehab.cadastral_identity import resolve_object
from madrid_rehab.commercial_data import load_fiche
from madrid_rehab.commercial_fiche import Quality


def positive(v):
    try:
        return pd.notna(v) and float(v) > 0
    except (ValueError, TypeError):
        return False


def residential(row):
    if row.get("recovered_current_use", row.get("current_use")) != "1_residential":
        return False
    year = row.get("recovered_construction_begin", row.get("construction_oldest_year"))
    match = re.match(r"^(\d{4})(?:-|(?:\.0)?$)", str(year))
    known_year = bool(match and 1000 <= int(match[1]) <= 2026)
    attributes = [
        known_year,
        positive(row.get("recovered_official_area")),
        positive(row.get("recovered_dwellings", row.get("dwellings_raw"))),
        positive(row.get("recovered_floors_above")),
    ]
    return sum(attributes) >= 2


def run():
    started = time.perf_counter()
    store.metadata()
    verification_ms = (time.perf_counter() - started) * 1000
    samples = json.loads(
        Path("reports/session_24_commercial_catalog/review_sample.json").read_text()
    )
    reviewed = []
    for row in samples:
        code, ref = row["code"], row["parcel_ref14"]
        _, cp = resolve_object(code, ref, "cp")
        assert not cp.empty
        model, tables, errors, timing = load_fiche(code, cc.NAMES[code], ref, cp)
        if row["local_visible"]:
            assert not errors, (code, ref, errors)
        expected_construction = any(
            residential(r) for r in tables["construction"].to_dict("records")
        )
        energy = any(e.quality == Quality.PARCEL for e in model.energy)
        admin = any(
            e.quality == Quality.PARCEL
            and e.label in {"order", "ite_pending", "iee_pending"}
            and e.value["Fecha"]
            for e in model.conservation
        )
        prtr = any(e.quality == Quality.PARCEL for e in model.grants)
        rehab = bool(model.municipal_grants)
        actual = [expected_construction, energy, admin, prtr, rehab]
        expected = [bool(row[k]) for k in cc.SOURCES]
        assert actual == expected, (code, ref, actual, expected)
        assert bool(row["local_visible"]) == any(actual)
        reviewed.append(
            dict(
                code=code,
                ref=ref,
                stratum=row["stratum"],
                sources=dict(zip(cc.SOURCES, actual)),
                level=row["local_level"],
                construction_objects=len(tables["construction"]),
                energy_ids=[e.entity_id for e in model.energy if e.quality == Quality.PARCEL],
                grant_ids=[e.entity_id for e in model.grants if e.quality == Quality.PARCEL],
                source_read_errors=errors,
                model_ms=timing["total_ms"],
                review="no divergence from independent selected-record check",
            )
        )
    timings = []
    for query in [
        ("AVENIDA DE AMERICA", "113", "A"),
        ("AVENIDA DE LA MONCLOA", "14", ""),
        ("CALLE BAILEN", "", ""),
    ]:
        trials = []
        for _ in range(3):
            begin = time.perf_counter()
            records, total, located = store.search("28079", *query)
            trials.append((time.perf_counter() - begin) * 1000)
        timings.append(dict(query=query, milliseconds=trials, results=total, located=located))
    return dict(
        verification_ms=verification_ms,
        reviewed_records=reviewed,
        false_positive_divergences=0,
        false_negative_divergences=0,
        selection="3 smallest SHA256 per municipality/stratum where present; not a statistical error-rate estimate",
        search_timings=timings,
        browser_visual_validation=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(run(), ensure_ascii=False, indent=2, default=str) + "\n")
