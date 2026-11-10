"""Reproducible internal documentary samples; not independent accuracy validation."""

import argparse
import json
from pathlib import Path
import time

from madrid_rehab import address_search as a
from madrid_rehab.cadastral_identity import resolve_object, construction_records


def measured(call):
    start = time.perf_counter()
    value = call()
    return value, (time.perf_counter() - start) * 1000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=a.REPORT / "search_benchmark.json")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    _, cold = measured(a.metadata)
    cases = []
    with a.connect() as db:
        # Deterministic spread through the complete ID order, plus each outcome.
        rows = [dict(r) for r in db.execute("SELECT * FROM addresses ORDER BY id")]
        selected = rows[:: max(1, len(rows) // 18)]
        selected += [
            dict(
                db.execute(
                    "SELECT * FROM addresses WHERE status=? ORDER BY id LIMIT 1", (s,)
                ).fetchone()
            )
            for s in ("confirmed", "ambiguous", "unlinked")
        ]
    for row in {r["id"]: r for r in selected}.values():
        query = (
            row["municipality"],
            row["kind"] + " " + row["street"],
            row["number"],
            row["complement"],
        )
        (_, street_count), street_ms = measured(lambda: a.search(query[0], query[1]))
        (found, total), portal_ms = measured(lambda: a.search(*query))
        (_, _), cached_ms = measured(lambda: a.search(*query))
        item = dict(
            input=query,
            source_id=row["id"],
            result_count=total,
            status=row["status"],
            recovered_expected_version=row["id"] in [r["id"] for r in found],
            street_results=street_count,
            street_ms=street_ms,
            portal_ms=portal_ms,
            second_query_ms=cached_ms,
            fiche_available=False,
        )
        if row["status"] == "confirmed":
            ref = json.loads(row["refs"])[0]
            (status, cp), fiche_ms = measured(lambda: resolve_object(query[0], ref, "cp"))
            (_, _), second_fiche_ms = measured(lambda: resolve_object(query[0], ref, "cp"))
            records, construction_ms = measured(lambda: construction_records(query[0], cp))
            facts = a.parcel_facts(query[0], ref)
            item.update(
                cp=ref,
                fiche_status=status,
                fiche_available=not cp.empty,
                fiche_identity_ms=fiche_ms,
                second_fiche_identity_ms=second_fiche_ms,
                construction_ms=construction_ms,
                construction_records=len(records),
                certificate_count=facts.get("certificate_count"),
                grant_case_count=facts.get("grant_case_count"),
                conservation_count=facts.get("conservation_event_count"),
            )
        cases.append(item)
    for code in set(a.NAMES) - {"28079"}:
        (_, total), ms = measured(lambda: a.search(code, "CALLE MAYOR", "24"))
        cases.append(
            dict(
                municipality=code,
                input="CALLE MAYOR 24",
                result_count=total,
                portal_ms=ms,
                status="no_postal_source",
                fiche_available=False,
                real_positive_sample=None,
                reason="No local postal literals; this query tests isolation only",
            )
        )
    a.write_json(
        args.output,
        dict(
            validation="internal_documentary_replay_not_independent_accuracy",
            cold_integrity_ms=cold,
            cases=cases,
        ),
    )


if __name__ == "__main__":
    main()
