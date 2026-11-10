"""Six real documentary cases, selected from preserved local products; no network."""

import argparse
from dataclasses import asdict
from pathlib import Path
import resource
import time
import tracemalloc

import pandas as pd

from madrid_rehab import address_search as postal, enriched_cadastre as ec
from madrid_rehab.cadastral_identity import resolve_object
from madrid_rehab.commercial_data import load_fiche


def real_cases():
    cases = [("Bailén 16", "28079", "9540103VK3794B")]
    with postal.connect() as db:
        for label, condition in [
            ("Madrid CEEE", "certificate_count>0"),
            ("Madrid conservación", "conservation_event_count>0"),
            ("Madrid PRTR", "grant_case_count>0"),
            (
                "Madrid sin información adicional",
                "certificate_count=0 AND grant_case_count=0 AND administrative_events_observed=0 AND construction_available=0",
            ),
        ]:
            row = db.execute(
                "SELECT parcel_ref14 FROM parcel_facts WHERE "
                + condition
                + " ORDER BY parcel_ref14 LIMIT 1"
            ).fetchone()
            if row is None:
                raise ValueError("No real case found: " + label)
            cases.append((label, "28079", row[0]))
    links = pd.read_parquet(
        ec.ROOT / "28065/cp_bu_documentary_links.parquet",
        columns=["cp_reference_normalized", "link_class", "relation_validated"],
    )
    ref = (
        links.loc[links.link_class.eq("A") & links.relation_validated, "cp_reference_normalized"]
        .value_counts()
        .index[0]
    )
    cases.insert(4, ("Getafe múltiples objetos A", "28065", ref))
    return cases


def run():
    output = []
    for label, code, ref in real_cases():
        begin = time.perf_counter()
        status, objects = resolve_object(code, ref, "cp")
        identity_ms = (time.perf_counter() - begin) * 1000
        if objects.empty:
            raise ValueError(status)
        row = None
        if code == "28079":
            with postal.connect() as db:
                found = db.execute(
                    "SELECT * FROM addresses WHERE status='confirmed' AND refs=? ORDER BY id LIMIT 1",
                    ('["' + ref + '"]',),
                ).fetchone()
                row = dict(found) if found else None
        tracemalloc.start()
        model, tables, errors, cold = load_fiche(code, postal.NAMES[code], ref, objects, postal=row)
        _, _, repeat_errors, warm = load_fiche(code, postal.NAMES[code], ref, objects, postal=row)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        if errors or repeat_errors:
            raise ValueError(errors or repeat_errors)
        output.append(
            dict(
                case=label,
                code=code,
                ref=ref,
                identity_ms=identity_ms,
                cold=cold,
                repeat=warm,
                python_peak_mib=peak / 1024**2,
                selected_rows={k: len(v) for k, v in tables.items()},
                model=asdict(model),
            )
        )
    return dict(
        validation="documentary_replay_not_independent_physical_verification",
        memory_scope="tracemalloc Python excludes native Arrow; process RSS high water includes prior cases",
        process_peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        cases=output,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    postal.write_json(args.output, run())
