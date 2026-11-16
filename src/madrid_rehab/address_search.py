"""Offline postal identity index. No geometry matching, downloads or BU inheritance."""

import argparse
from contextlib import contextmanager
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import unicodedata

import pandas as pd

from . import demo
from .ingest import digest

DEFAULT = Path("data/processed/addresses/session_20_01")
REPORT = Path("reports/session_20_address_search")
NAMES = {
    "28079": "Madrid",
    "28065": "Getafe",
    "28092": "Móstoles",
    "28074": "Leganés",
    "28007": "Alcorcón",
    "28005": "Alcalá de Henares",
}
POLICY = "postal-documentary-v1"
KINDS = {
    "CL": "CALLE",
    "C": "CALLE",
    "AV": "AVENIDA",
    "AVDA": "AVENIDA",
    "PZ": "PLAZA",
    "PL": "PLAZA",
    "PZA": "PLAZA",
    "PS": "PASEO",
    "Pº": "PASEO",
}


def text(value):
    return "" if value is None or pd.isna(value) else str(value).strip()


def normalize(value):
    """Accent/case/space folding only; preserve name particles and punctuation."""
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFD", text(value).upper())
            if unicodedata.category(c) != "Mn"
        ).split()
    )


def street_key(value):
    value = normalize(value)
    match = re.match(r"^(\w+)[./]?\s+(.+)$", value)
    if match:
        kind, rest = match.groups()
        value = KINDS.get(kind, kind) + " " + rest
    return value


def number_key(value):
    value = normalize(value)
    return str(int(value)) if re.fullmatch(r"\d+", value) else value


def parse_query(street, number="", complement=""):
    """Only parse an anchored final integer (+ single letter/BIS); never ranges."""
    street = text(street)
    if not text(number):
        match = re.fullmatch(r"(.+?)[,\s]+(\d+)\s*([A-Za-z]|BIS)?", street, re.I)
        if match:
            street, number, suffix = match.groups()
            if suffix and complement and normalize(suffix) != normalize(complement):
                raise ValueError("Complementos contradictorios")
            complement = complement or suffix or ""
    return street_key(street), number_key(number), normalize(complement)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_source(root, relative, inputs, columns=None):
    frame = demo.read(root, relative, columns=columns)
    manifest = (demo.CONSERVATION if root == demo.CITY else root) / "manifest.json"
    for path in (manifest, root / relative):
        inputs[str(path)] = digest(path)
    return frame


def postal_rows(accesses, links):
    """Retain each official version. Any conflicting bridge version blocks opening."""
    associations = {}
    for ndp, group in links.groupby("ndp", sort=False):
        refs = sorted(set(group.confirmed_parcel_ref14.dropna()) - {""})
        candidates = sorted(set(group.parcel_candidate.dropna()) - {""})
        statuses = set(group.link_status)
        confirmed = statuses == {"confirmed_access_parcel"} and bool(refs)
        ambiguous = any("ambiguous" in s for s in statuses) or (bool(refs) and not confirmed)
        associations[str(ndp)] = (
            refs if confirmed else [],
            candidates,
            "confirmed" if confirmed else "ambiguous" if ambiguous else "unlinked",
            ";".join(sorted(set(group.link_reason))),
        )
    rows, aliases = [], []
    for r in accesses.itertuples(index=False):
        street, number = text(r.VIA_NOMBRE_ACENTOS), text(r.NUMERO)
        # Kilometres are not house numbers. Retain them in coverage, not portal search.
        if not street or not number or text(r.CLASE_APP) != "NUMERO":
            continue
        ref, candidates, status, reason = associations.get(
            str(r.COD_NDP), ([], [], "unlinked", "no_bridge")
        )
        uid = r.access_version_id
        kind, particle = text(r.VIA_CLASE), text(r.VIA_PAR)
        original = " ".join(v for v in [kind, particle, street, number, text(r.CALIFICADOR)] if v)
        rows.append(
            dict(
                id=uid,
                access_id=r.access_id,
                municipality="28079",
                original=original,
                street=street,
                kind=kind,
                number=number,
                complement=text(r.CALIFICADOR),
                number_key=number_key(number),
                complement_key=normalize(r.CALIFICADOR),
                via_code=text(r.COD_VIA),
                access_type=text(r.TIPO_NDP),
                status=status,
                refs=json.dumps(ref),
                candidates=json.dumps(candidates),
                reason=reason,
                source_row=int(r.source_row),
                source_sha256=r.source_sha256,
            )
        )
        # Both spellings are explicit fields of the same official street record.
        for name in {street, text(r.VIA_NOMBRE), " ".join(v for v in [particle, street] if v)}:
            for alias in {street_key(name), street_key(kind + " " + name)}:
                if alias:
                    aliases.append((uid, "28079", alias))
    return pd.DataFrame(rows), pd.DataFrame(
        aliases, columns=["id", "municipality", "alias"]
    ).drop_duplicates()


def build(output=DEFAULT, report=REPORT):
    """New output directories only. Products authenticated against existing manifests."""
    output, report = Path(output), Path(report)
    if output.exists() or report.exists():
        raise FileExistsError("Use directorios nuevos para índice e informe")
    inputs = {}
    accesses = read_source(demo.CONSERVATION, "conservation_accesses.parquet", inputs)
    links = read_source(demo.CONSERVATION, "conservation_parcel_links.parquet", inputs)
    rows, aliases = postal_rows(accesses, links)
    cp = read_source(
        demo.CITY, "parcels_audited.parquet", inputs, ["parcel_ref14", "usable_geometry"]
    )
    good = set(cp.loc[~cp.parcel_ref14.duplicated(keep=False) & cp.usable_geometry, "parcel_ref14"])
    for i, row in rows[rows.status.eq("confirmed")].iterrows():
        if not set(json.loads(row.refs)) <= good:
            rows.loc[i, ["status", "refs", "reason"]] = ["ambiguous", "[]", "cp_not_unique_usable"]
    # Lightweight evidence facts used for summary and denominators; no geometries.
    admin = Path("data/processed/administrative_events/session_10_final_01")
    profiles = read_source(
        admin,
        "parcel_profiles.parquet",
        inputs,
        [
            "parcel_ref14",
            "construction_available",
            "construction_oldest_year",
            "construction_newest_year",
            "administrative_events_observed",
        ],
    )
    profiles["municipality"] = "28079"
    conservation = read_source(
        demo.CONSERVATION,
        "conservation_evidence_profile.parquet",
        inputs,
        ["parcel_ref14", "conservation_event_count"],
    )
    profiles = profiles.merge(conservation, on="parcel_ref14", how="left", validate="one_to_one")
    energy = read_source(
        demo.ENERGY,
        "energy_grants_summary.parquet",
        inputs,
        ["municipality_code", "parcel_ref14", "certificate_count", "grant_case_count"],
    )
    # Grant facts must follow the same active snapshot as the fiche.
    from .regional_view import regional_root_path

    grant_root = regional_root_path()
    grants = read_source(grant_root, "grant_parcel_links.parquet", inputs)
    scope = (
        "geographic_municipality_code"
        if "geographic_municipality_code" in grants
        else "municipality_code"
    )
    grants = grants[
        grants.match_status.isin(
            ["confirmed", "confirmed_reference", "confirmed_historical_madrid"]
        )
    ]
    grant_counts = grants.groupby([scope, "parcel_ref14"]).expediente_id.nunique()
    profiles = profiles.merge(
        energy[energy.municipality_code.eq("28079")].drop(columns="municipality_code"),
        on="parcel_ref14",
        how="left",
        validate="one_to_one",
    )
    profiles["grant_case_count"] = [
        int(grant_counts.get(("28079", ref), 0)) for ref in profiles.parcel_ref14
    ]
    profiles = profiles.drop_duplicates("parcel_ref14", keep=False)
    profiles = profiles[profiles.parcel_ref14.isin(good)].fillna(0)
    profiles["construction_available"] = profiles.construction_available.astype(int)
    pilot_metrics = {}
    from . import enriched_cadastre as enriched

    for code in NAMES:
        if code == "28079":
            continue
        enriched.metadata(code)
        root = enriched.ROOT / code
        ad = read_source(
            root,
            "buildings_enriched.parquet",
            inputs,
            ["building_id", "address_references_json", "source_feature_type"],
        )
        declarations = [json.loads(value) for value in ad.address_references_json]
        literals = [v for values in declarations for v in values if text(v.get("raw_text"))]
        if literals:
            raise ValueError("Nueva evidencia postal piloto: revisar parser antes de indexar")
        cp_root, cp_relative = demo.cp_source(code)
        pilot_cp = read_source(cp_root, cp_relative, inputs, ["parcel_ref14"])
        pilot_metrics[code] = dict(
            name=NAMES[code],
            coverage="partial_cadastral_capture_without_postal_literals",
            accepted_cp=len(pilot_cp),
            accepted_bu=len(ad),
            bu_with_ad_reference=sum(bool(v) for v in declarations),
            ad_declarations=sum(len(v) for v in declarations),
            ad_with_postal_literal=len(literals),
            indexed_addresses=0,
            confirmed_addresses=0,
            ambiguous_addresses=0,
            unlinked_addresses=0,
            distinct_accesses=0,
            distinct_portals=0,
            accessible_parcels=0,
            cp_without_recoverable_postal_address=len(pilot_cp),
            utility_percentages=None,
            missing="Official AD literals, address IDs, street/number/complement and explicit CP/BU links",
        )
    output.mkdir(parents=True)
    report.mkdir(parents=True)
    with sqlite3.connect(output / "addresses.sqlite") as db:
        rows.to_sql("addresses", db, index=False)
        aliases.to_sql("aliases", db, index=False)
        profiles.to_sql("parcel_facts", db, index=False)
        db.executescript(
            "CREATE UNIQUE INDEX address_id ON addresses(id);"
            "CREATE INDEX street_lookup ON aliases(municipality, alias);"
            "CREATE INDEX alias_id ON aliases(id);"
            "CREATE INDEX postal_lookup ON addresses(municipality, number_key, complement_key);"
            "CREATE UNIQUE INDEX facts_lookup ON parcel_facts(municipality, parcel_ref14);"
        )
    db.close()
    refs = {
        ref for value in rows.loc[rows.status.eq("confirmed"), "refs"] for ref in json.loads(value)
    }
    linked = rows[rows.status.eq("confirmed")]
    parcel_counts = pd.Series(
        [ref for value in linked.refs for ref in json.loads(value)]
    ).value_counts()
    facts = profiles[profiles.parcel_ref14.isin(refs)]
    utility = {}
    for label, field in [
        ("construction", "construction_available"),
        ("ceee", "certificate_count"),
        ("prtr", "grant_case_count"),
        ("administrative", "administrative_events_observed"),
        ("conservation", "conservation_event_count"),
    ]:
        count = int(facts[field].gt(0).sum())
        utility[label] = dict(
            numerator=count,
            denominator=len(refs),
            unit="distinct_accessible_parcels",
            percent=100 * count / len(refs) if refs else None,
        )
    madrid = dict(
        name="Madrid",
        coverage="integrated_official_snapshot_not_city_completeness",
        source_access_versions=len(accesses),
        source_distinct_accesses=int(accesses.COD_NDP.nunique()),
        source_with_street_number=int(
            (
                accesses.VIA_NOMBRE_ACENTOS.str.strip().ne("") & accesses.NUMERO.str.strip().ne("")
            ).sum()
        ),
        excluded_non_house_number_versions=int(accesses.CLASE_APP.ne("NUMERO").sum()),
        indexed_addresses=len(rows),
        distinct_accesses=int(rows.access_id.nunique()),
        distinct_portals=int(rows.loc[rows.access_type.eq("PORTAL"), "access_id"].nunique()),
        confirmed_addresses=int(rows.status.eq("confirmed").sum()),
        confirmed_accesses=int(linked.access_id.nunique()),
        ambiguous_addresses=int(rows.status.eq("ambiguous").sum()),
        unlinked_addresses=int(rows.status.eq("unlinked").sum()),
        accesses_multiple_versions=int((rows.groupby("access_id").size() > 1).sum()),
        bridge_accesses_multiple_associations=int((links.groupby("ndp").size() > 1).sum()),
        bridge_accesses_multiple_cp=int(
            (links.groupby("ndp").parcel_candidate.nunique() > 1).sum()
        ),
        accessible_parcels=len(refs),
        parcels_multiple_address_versions=int(parcel_counts.gt(1).sum()),
        confirmed_address_memberships_on_shared_parcels=int(
            parcel_counts[parcel_counts.gt(1)].sum()
        ),
        maximum_confirmed_addresses_per_parcel=int(parcel_counts.max())
        if len(parcel_counts)
        else 0,
        distinct_street_codes=int(rows.via_code.nunique()),
        address_keys_multiple_cp=int(
            (
                links[links.address_key.ne("")].groupby("address_key").parcel_candidate.nunique()
                > 1
            ).sum()
        ),
        utility_percentages=utility,
    )
    coverage = dict(
        policy=POLICY,
        units="Addresses = official postal versions with house number; access != portal != CP != physical building",
        independent_address_verification=False,
        municipalities={"28079": madrid, **pilot_metrics},
    )
    write_json(report / "address_coverage.json", coverage)
    manifest = dict(
        policy=POLICY,
        inputs=inputs,
        outputs={"addresses.sqlite": digest(output / "addresses.sqlite")},
        municipalities={
            c: dict(name=v["name"], indexed_addresses=v["indexed_addresses"])
            for c, v in coverage["municipalities"].items()
        },
        grant_root=str(grant_root),
        cp_source=str(demo.CITY),
        pilot_cp_source=str(demo.cp_source("28065")[0]),
    )
    write_json(output / "manifest.json", manifest)
    return coverage


def root_path():
    return Path(os.environ.get("MADRID_REHAB_ADDRESS_DIR", str(DEFAULT)))


def signature(paths):
    return tuple(
        (str(p), p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
    )


@lru_cache(maxsize=4)
def _validate(root, token):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["policy"] != POLICY:
        raise ValueError("Contrato postal incompatible")
    for path, expected in manifest["inputs"].items():
        if digest(Path(path)) != expected:
            raise ValueError("Índice postal desactualizado: " + path)
    if digest(root / "addresses.sqlite") != manifest["outputs"]["addresses.sqlite"]:
        raise ValueError("Índice postal alterado")
    return manifest


def metadata(root=None):
    from . import production_bundle as bundle

    if bundle.active():
        return bundle.metadata()["postal"]
    root = Path(root or root_path())
    manifest = json.loads((root / "manifest.json").read_text())
    token = signature(
        [root / "manifest.json", root / "addresses.sqlite", *map(Path, manifest["inputs"])]
    )
    result = _validate(str(root), token)
    for variable, expected in (
        ("MADRID_REHAB_ENERGY_DIR", demo.ENERGY),
        ("MADRID_REHAB_CONSERVATION_DIR", demo.CONSERVATION),
        (
            "MADRID_REHAB_ADMIN_DIR",
            Path("data/processed/administrative_events/session_10_final_01"),
        ),
        ("MADRID_REHAB_SESSION7_DIR", Path("data/processed/session_7_final")),
    ):
        active = Path(os.environ.get(variable, str(expected)))
        if active.resolve() != expected.resolve():
            raise ValueError("Captura activa incompatible con el resumen postal: " + variable)
    from .regional_view import regional_root_path

    if (
        regional_root_path().resolve() != Path(result["grant_root"]).resolve()
        or demo.cp_source("28065")[0].resolve() != Path(result["pilot_cp_source"]).resolve()
    ):
        raise ValueError(
            "Captura activa incompatible con el índice postal; regenere en salida nueva"
        )
    return result


@contextmanager
def connect(root=None):
    root = Path(root or root_path())
    metadata(root)
    db = sqlite3.connect((root / "addresses.sqlite").resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()


def search(municipality, street, number="", complement="", root=None, limit=100, offset=0):
    """Bounded explicit submit query. Full spelling or documented alias, exact number."""
    alias, num, extra = parse_query(street, number, complement)
    if not alias:
        return [], 0
    conditions, params = (
        ["s.municipality=?", "s.alias=?", "a.municipality=?"],
        [municipality, alias, municipality],
    )
    if num:
        conditions.append("a.number_key=?")
        params.append(num)
    if extra:
        conditions.append("a.complement_key=?")
        params.append(extra)
    where = " AND ".join(conditions)
    # Begin with the selective street index. SQLite otherwise chooses a full
    # municipal address scan for number-less queries on this real distribution.
    base = (
        " FROM aliases s INDEXED BY street_lookup CROSS JOIN addresses a "
        "INDEXED BY address_id ON a.id=s.id WHERE " + where
    )
    with connect(root) as db:
        total = db.execute("SELECT COUNT(DISTINCT a.id)" + base, params).fetchone()[0]
        found = db.execute(
            "SELECT DISTINCT a.*" + base + " ORDER BY a.original,a.id LIMIT ? OFFSET ?",
            [*params, min(max(limit, 1), 100), max(offset, 0)],
        ).fetchall()
    return [dict(r) for r in found], total


def suggest(municipality, street, root=None):
    key = street_key(street)
    if len(key) < 2:
        return []
    with connect(root) as db:
        return [
            r[0]
            for r in db.execute(
                "SELECT DISTINCT alias FROM aliases WHERE municipality=? AND alias>=? AND alias<? ORDER BY alias LIMIT 20",
                (municipality, key, key + "\uffff"),
            )
        ]


def parcel_facts(municipality, ref, root=None):
    with connect(root) as db:
        row = db.execute(
            "SELECT * FROM parcel_facts WHERE municipality=? AND parcel_ref14=?",
            (municipality, ref),
        ).fetchone()
    return dict(row) if row else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--report-dir", type=Path, default=REPORT)
    args = parser.parse_args()
    start = time.perf_counter()
    coverage = build(args.output_dir, args.report_dir)
    print(
        json.dumps(
            {"municipalities": coverage["municipalities"], "seconds": time.perf_counter() - start},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
