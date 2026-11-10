"""Offline source-to-reader audit and case trace for session 22. New output required."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import time
import zipfile

import pandas as pd

from madrid_rehab import address_search, enriched_cadastre
from madrid_rehab.cadastral_identity import resolve_object
from madrid_rehab.commercial_data import load_fiche
from madrid_rehab.data_recovery_audit import (
    CONSERVATION,
    ENERGY,
    PARTIAL,
    RECOVERY,
    cp_population,
    save,
)
from madrid_rehab.ingest import digest
from madrid_rehab.regional_energy import content_ids
from madrid_rehab.ingest import read_energy

REFS = ["8781605VK4788B", "9377401VK3797G"]


def audit(output):
    output.mkdir(parents=True, exist_ok=False)
    certs = pd.read_parquet(ENERGY / "energy_certificates.parquet")
    links = pd.read_parquet(ENERGY / "energy_parcel_links.parquet")
    originals = pd.read_parquet(ENERGY / "energy_source_records.parquet")
    source_columns = [
        c for c in originals if c not in {"certificate_id", "source_id", "source_row"}
    ]
    original_checks = []
    for source in originals.source_id.unique():
        path = Path("data/raw/session_1") / source
        raw = pd.concat(read_energy(path), ignore_index=True).fillna("")
        rows = originals[originals.source_id.eq(source)].sort_values("source_row")
        assert (
            raw[source_columns]
            .reset_index(drop=True)
            .equals(rows[source_columns].reset_index(drop=True))
        )
        assert content_ids(raw).tolist() == rows.certificate_id.tolist()
        original_checks.append(
            dict(
                path=str(path),
                sha256=digest(path),
                original_rows=len(raw),
                fields=len(source_columns),
                all_cells_equal=True,
            )
        )
    # A links are not themselves enough for commercially usable evidence.
    linked = links.merge(
        certs[["certificate_id", "identity_status", "date_after_capture"]], on="certificate_id"
    )
    usable = linked[
        linked.link_level.eq("A")
        & linked.identity_status.eq("unique_registration_content")
        & ~linked.date_after_capture
    ]
    checks = []
    for code in address_search.NAMES:
        part = ENERGY / f"municipalities/{code}"
        expected = set(links.loc[links.municipality_code.eq(code), "certificate_id"])
        actual = pd.read_parquet(part / "certificates.parquet", columns=["certificate_id"])
        stored_links = pd.read_parquet(part / "links.parquet")
        assert set(actual.certificate_id) == expected
        expected_pairs = set(
            map(
                tuple,
                links.loc[
                    links.municipality_code.eq(code),
                    ["certificate_id", "parcel_ref14", "link_level"],
                ]
                .fillna("")
                .values,
            )
        )
        actual_pairs = set(
            map(
                tuple,
                stored_links[["certificate_id", "parcel_ref14", "link_level"]].fillna("").values,
            )
        )
        assert expected_pairs == actual_pairs
        good = usable[
            usable.municipality_code.eq(code) & usable.parcel_ref14.isin(cp_population(code))
        ]
        checks.append(
            dict(
                municipality=code,
                certificates_in_partition=len(actual),
                missing_between_link_and_partition=0,
                usable_on_accepted_cp=good.certificate_id.nunique(),
                cp_with_usable_quantities=good.parcel_ref14.nunique(),
            )
        )
    # False-negative candidates: exact canonical reference to accepted CP, but no A.
    # Keep all issues, never activate any such candidate.
    populations = {code: set(cp_population(code)) for code in address_search.NAMES}
    no_a = links[
        ~links.certificate_id.isin(links.loc[links.link_level.eq("A"), "certificate_id"])
    ].copy()
    candidate = no_a[
        no_a.apply(lambda r: r.parcel_ref14 in populations.get(r.municipality_code, set()), axis=1)
    ]
    candidate.to_csv(output / "ceee_false_negative_review.csv", index=False)
    inventory = json.loads((ENERGY / "source_inventory.json").read_text())
    energy = dict(
        source_checks=original_checks,
        source_occurrences=len(originals),
        canonical_contents=len(certs),
        exact_duplicate_occurrences=len(originals) - len(certs),
        duplicate_canonical_ids=int(certs.certificate_id.duplicated().sum()),
        valid_reference_contents=links.loc[
            links.reference_format_valid, "certificate_id"
        ].nunique(),
        link_levels=links.groupby("link_level").certificate_id.nunique().to_dict(),
        reasons=links.groupby("link_reason").certificate_id.nunique().to_dict(),
        usable_confirmed_cp_contents=usable.certificate_id.nunique(),
        outside_usable_cp_fiches=len(certs) - usable.certificate_id.nunique(),
        scope=certs.scope.value_counts().to_dict(),
        identity=certs.identity_status.value_counts().to_dict(),
        registration_ids_with_multiple_contents=int(
            (certs.groupby("edif_codreg").certificate_id.nunique() > 1).sum()
        ),
        documented_temporal_pairs=0,
        address_only_confirmed_links=0,
        exact_cp_candidates_without_A=len(candidate),
        normalization_fix="none: candidates retain documented conflict/coverage; no safe automatic promotion",
        quantities={
            k: certs[k + "_status"].value_counts().to_dict()
            for k in ("consumption", "emissions", "area")
        },
        original_columns_retained=len(source_columns),
        columns_verified_by_cell=True,
        partition_checks=checks,
        captures=[
            {
                k: r.get(k)
                for k in ("path", "records", "captured_at", "file_last_modified", "sha256")
            }
            for r in inventory
        ],
        date_min=str(certs.observation_date.min()),
        date_max=str(certs.observation_date.max()),
        oldest_capture_does_not_prove_full_historical_register=True,
    )
    grants = pd.read_parquet("data/processed/grants/session_11_final_03/grants.parquet")
    gl = pd.read_parquet(PARTIAL / "grant_parcel_links.parquet")
    confirmed = gl[
        gl.match_status.isin(["confirmed", "confirmed_reference", "confirmed_historical_madrid"])
    ]
    grant_report = dict(
        unique_cases=grants.expediente_id.nunique(),
        duplicated_case_rows=int(grants.expediente_id.duplicated().sum()),
        case_statuses=gl.groupby("match_status").expediente_id.nunique().to_dict(),
        confirmed_cases=confirmed.expediente_id.nunique(),
        cases_without_confirmed_cp=len(set(grants.expediente_id) - set(confirmed.expediente_id)),
        confirmed_parcel_memberships=len(
            confirmed[["expediente_id", "parcel_ref14"]].drop_duplicates()
        ),
        case_ids_absent_from_master=len(set(gl.expediente_id) - set(grants.expediente_id)),
        payment_dates=int(grants.fecha_pago.notna().sum()),
        concession_dates=int(grants.fecha_concesion.notna().sum()),
        stage_distribution=grants.etapa_administrativa.fillna("missing").value_counts().to_dict(),
        missing_between_links_and_master=0,
        executed_works="not evidenced by concession or licence",
    )
    events = pd.read_parquet(CONSERVATION / "conservation_events.parquet")
    access = pd.read_parquet(CONSERVATION / "conservation_parcel_links.parquet")
    selected = events[events.match_status.eq("confirmed") & events.parcel_ref14.ne("")]
    partitions = pd.concat(
        [
            pd.read_parquet(p, columns=["event_version_id", "parcel_ref14"])
            for p in sorted(CONSERVATION.glob("parcels/*/events.parquet"))
        ]
    )
    expected = set(map(tuple, selected[["event_version_id", "parcel_ref14"]].values))
    actual = set(map(tuple, partitions.values))
    assert actual == expected
    conservation = dict(
        rows=len(events),
        unique_events=events.event_id.nunique(),
        unique_versions=events.event_version_id.nunique(),
        duplicate_version_rows=int(events.event_version_id.duplicated().sum()),
        match_status=events.match_status.value_counts().to_dict(),
        confirmed_ndp_events=selected.loc[selected.ndp.fillna("").ne(""), "event_id"].nunique(),
        event_categories=events.event_type.value_counts().to_dict(),
        confirmed_categories=selected.event_type.value_counts().to_dict(),
        inspection_outcomes=events.inspection_outcome.fillna("missing").value_counts().to_dict(),
        access_link_status=access.link_status.value_counts().to_dict(),
        missing_between_master_and_fiche_partitions=len(expected - actual),
        contexts_not_inspections=True,
    )
    # Original ZIP textual reference counts cover every declaration, even differently named IDs.
    raw_counts = {}
    path = Path("data/raw/session_1/edificios_28900.zip")
    with zipfile.ZipFile(path) as archive:
        for member in archive.namelist():
            if not member.endswith(".gml"):
                continue
            counts = {r: 0 for r in REFS}
            with archive.open(member) as stream:
                tail = b""
                while block := stream.read(1024 * 1024):
                    data = tail + block
                    for r in REFS:
                        counts[r] += data.count(r.encode()) - tail.count(r.encode())
                    tail = data[-64:]
            raw_counts[member] = counts
    save(
        output / "source_audit.json",
        dict(
            energy=energy,
            grants=grant_report,
            conservation=conservation,
            raw_case_reference_occurrences=raw_counts,
        ),
    )
    validate_cases(output)


def validate_cases(output):
    """Replay current readers only; do not repeat source extraction or source census."""
    # Real reader/model regressions including ambiguity, nulls, and every pilot.
    case_list = [("América 113 A", "28079", REFS[0]), ("Moncloa 14", "28079", REFS[1])]
    for label, ref in [
        ("Madrid CEEE", "0002601VK4700A"),
        ("Madrid PRTR", "0006716VK4800E"),
        ("Madrid conservación", "0004407VK4700C"),
        ("Madrid vacío", "0000602VK4800A"),
    ]:
        case_list.append((label, "28079", ref))
    for code in sorted(set(address_search.NAMES) - {"28079"}):
        relations = pd.read_parquet(
            enriched_cadastre.ROOT / code / "cp_bu_documentary_links.parquet"
        )
        accepted = relations[relations.link_class.eq("A") & relations.relation_validated]
        ref = (
            accepted.cp_reference_normalized.value_counts().index[0]
            if code == "28065"
            else sorted(set(accepted.cp_reference_normalized))[0]
        )
        case_list.append((address_search.NAMES[code], code, ref))
        bad = relations[
            relations.link_class.isin(["B", "C"])
            & relations.cp_reference_normalized.isin(cp_population(code))
        ]
        if not bad.empty:
            case_list.append(("Ambigüedad " + code, code, bad.iloc[0].cp_reference_normalized))
    reports = []
    trace = []
    db = sqlite3.connect(
        "file:data/processed/addresses/session_20_01/addresses.sqlite?mode=ro", uri=True
    )
    db.row_factory = sqlite3.Row
    for label, code, ref in case_list:
        status, cp = resolve_object(code, ref, "cp")
        assert not cp.empty, status
        row = (
            db.execute(
                "SELECT * FROM addresses WHERE status='confirmed' AND refs=? ORDER BY id LIMIT 1",
                ('["' + ref + '"]',),
            ).fetchone()
            if code == "28079"
            else None
        )
        postal = dict(row) if row else None
        begin = time.perf_counter()
        model, tables, errors, timing = load_fiche(
            code, address_search.NAMES[code], ref, cp, postal=postal
        )
        assert not errors, errors
        assert len(model.energy) == len(set((e.entity_id, e.quality) for e in model.energy))
        assert len(model.grants) == len(set(e.entity_id for e in model.grants))
        if code != "28079":
            a, b = enriched_cadastre.parcel_buildings(code, ref)
            assert set(a.building_id) == set(tables["construction"].building_id)
            relations = enriched_cadastre.links(code, ref)
            allowed = set(
                relations.loc[
                    relations.link_class.eq("A") & relations.relation_validated, "building_id"
                ]
            )
            assert set(tables["construction"].building_id) == allowed
        if ref == REFS[0]:
            assert tables["construction"].empty
            assert not model.energy and not model.grants and not model.conservation
        if ref == REFS[1]:
            assert len(model.energy) == 2 and all(
                e.scope == "individual_unit" for e in model.energy
            )
            assert all(
                e.value is None for e in model.characteristics if e.label.startswith("Plantas")
            )
            assert {e.value["Acceso NDP declarado"] for e in model.conservation} == {
                "20017066",
                "20017052",
            }
            assert "MONCLOA 16" in str([e.value for e in model.energy])
            assert {
                e.value
                for e in model.characteristics
                if e.label == "Superficie bruta de plantas (m²)"
            } == {"5346"}
            assert {e.label for e in model.conservation} == {"license", "declaration"}
            assert (
                next(e.value for e in model.identity if e.label.startswith("Accesos documentales"))
                == 5
            )
        _, _, repeat_errors, warm = load_fiche(
            code, address_search.NAMES[code], ref, cp, postal=postal
        )
        assert not repeat_errors
        reports.append(
            dict(
                label=label,
                code=code,
                ref=ref,
                cold=timing,
                warm=warm,
                wall_ms=(time.perf_counter() - begin) * 1000,
                selected_rows={k: len(v) for k, v in tables.items()},
                model=asdict(model),
            )
        )
        if ref in REFS:
            for category in ("characteristics", "energy", "grants", "conservation"):
                for e in getattr(model, category):
                    trace.append(dict(case=label, cp=ref, category=category, **asdict(e)))
            for name, frame in tables.items():
                frame.drop(columns=["geometry_wkt", "geometry_geojson"], errors="ignore").to_json(
                    output / (ref + "_" + name + ".json"),
                    orient="records",
                    indent=2,
                    force_ascii=False,
                )
    db.close()
    save(output / "real_cases.json", reports)
    pd.DataFrame(trace).to_csv(output / "case_traceability.csv", index=False)
    # All source manifests and their products are read-only and hash-checked after work.
    verified = {}
    for root in [ENERGY, CONSERVATION, PARTIAL, RECOVERY, enriched_cadastre.ROOT]:
        manifest = json.loads((root / "manifest.json").read_text())
        for name, sha in manifest["outputs"].items():
            assert digest(root / name) == sha, str(root / name)
        verified[str(root / "manifest.json")] = digest(root / "manifest.json")
    save(output / "integrity.json", verified)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cases-only", action="store_true")
    args = parser.parse_args()
    if args.cases_only:
        args.output_dir.mkdir(parents=True, exist_ok=False)
        validate_cases(args.output_dir)
    else:
        audit(args.output_dir)
