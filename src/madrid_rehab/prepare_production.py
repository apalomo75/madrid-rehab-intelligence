"""Package existing audited products; no acquisition, matching or source ETL."""

import argparse
from collections import Counter
from contextlib import closing
import csv
import json
from pathlib import Path
import sqlite3

import pandas as pd

from . import commercial_catalog_store as catalog, demo, enriched_cadastre
from .commercial_filters import inspection_rows
from .data_recovery_audit import CITY, CONSERVATION, ENERGY, RECOVERY
from .ingest import digest
from .production_bundle import VERSION

CODES = ("28079", "28065", "28092", "28074", "28007", "28005")
PLAN = Path("data/processed/plan_rehabilita/session_23_01")
PLAN_URL = "https://geoportal.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=00000009-b145-11ea-a01e-ecb1d753f6e8"
PLAN_HASH = "5c9ba32bb5871e5c0af2f7b15148373a694d635c8ca633a7e7d05e4bcaedd66b"


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def build(output, report, evidence):
    output, report = Path(output), Path(report)
    if output.exists() or report.exists():
        raise FileExistsError("New output and report directories required")
    proof = json.loads(Path(evidence).read_text())
    if (
        not proof.get("exact_match")
        or proof.get("sha256") != PLAN_HASH
        or proof.get("status") != 200
    ):
        raise ValueError("Official Plan Rehabilita identity is not accredited")
    if not proof.get("url", "").startswith("https://geoportal.madrid.es/fsdescargas/"):
        raise ValueError("Unofficial Plan Rehabilita source")
    # Authenticate existing inputs using the readers used in S28, before packaging.
    original = catalog.metadata()
    from . import address_search

    postal = address_search.metadata()
    for code in CODES[1:]:
        enriched_cadastre.metadata(code)
    inventory = list(
        csv.DictReader(Path("reports/session_28_deployment/inventory_final/files.csv").open())
    )
    source_hashes = {r["path"]: r["sha256"] for r in inventory}
    plan_meta = json.loads((PLAN / "manifest.json").read_text())
    for name, sha in plan_meta["outputs"].items():
        source_hashes[str(PLAN / name)] = sha
    output.mkdir(parents=True)
    report.mkdir(parents=True)
    files, inputs = {}, {}

    def source(path):
        path = Path(path)
        sha = digest(path)
        if source_hashes.get(path.as_posix()) != sha:
            raise ValueError("Unauthenticated source: " + str(path))
        inputs[path.as_posix()] = sha
        return path

    def parquet(path, frame=None, family="cadastre"):
        path = source(path)
        if frame is None:
            frame = pd.read_parquet(path)
        # Raw ETL serialization is never rendered; typed columns and provenance hashes remain.
        dropped = [c for c in frame if c == "raw_json"]
        frame = frame.drop(columns=dropped)
        sort = next(
            (c for c in ("parcel_ref14", "building_id", "certificate_id", "case_id") if c in frame),
            None,
        )
        if sort:
            frame = frame.sort_values(sort, kind="stable")
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(target, index=False, compression="zstd", row_group_size=1024)
        files[path.as_posix()] = dict(
            bytes=target.stat().st_size,
            sha256=digest(target),
            source=path.as_posix(),
            source_sha256=inputs[path.as_posix()],
            family=family,
            rows=len(frame),
            dropped_columns=dropped,
            transformation="sorted lossless typed rows; zstd; small row groups",
        )

    for filename in ("parcels_audited.parquet", "buildings_audited.parquet"):
        parquet(demo.CITY / filename)
    parquet(CITY / "districts.parquet")
    for path in sorted((CITY / "districts").glob("*/map_buildings.parquet")):
        parquet(path)
    parquet(RECOVERY / "building_attributes.parquet")
    for code in CODES[1:]:
        for name in ("cp.parquet", "bu.parquet"):
            parquet(demo.CADASTRE / code / name)
        for name in ("buildings_enriched.parquet", "cp_bu_documentary_links.parquet"):
            parquet(enriched_cadastre.ROOT / code / name)
    for code in CODES:
        for name in ("links.parquet", "certificates.parquet"):
            parquet(ENERGY / "municipalities" / code / name, family="ceee_cc_by_4")
    # Only 300377 rows have source-specific reuse evidence; do not smuggle PDF obligations.
    events = pd.read_parquet(source(CONSERVATION / "conservation_events.parquet"))
    authorized = events.event_type.eq("order") & events.source_file.str.startswith("300377-")
    allowed_events = events[authorized].copy()
    admin = (
        allowed_events[
            allowed_events.match_status.eq("confirmed")
            & ~allowed_events.identity_conflict
            & allowed_events.is_conservation_evidence
            & pd.to_datetime(allowed_events.date, format="mixed", errors="coerce").notna()
        ]
        .groupby("parcel_ref14")
        .size()
        .to_dict()
    )
    ite = sorted(set(inspection_rows(allowed_events).parcel_ref14.dropna()))
    for path in sorted((CONSERVATION / "parcels").glob("*/events.parquet")):
        frame = pd.read_parquet(source(path))
        frame = frame[frame.event_type.eq("order") & frame.source_file.str.startswith("300377-")]
        if not frame.empty:
            parquet(path, frame, family="municipal_orders_cc_by_4")
    for path in sorted((CONSERVATION / "parcels").glob("*/accesses.parquet")):
        parquet(path, family="municipal_street_register_cc_by_4")
    locations = pd.read_parquet(source(PLAN / "locations.parquet"))
    locations = locations[locations.link_class.eq("A")].copy()
    cases = pd.read_parquet(source(PLAN / "cases.parquet"))
    if not cases.case_id.is_unique:
        raise ValueError("Nonunique Plan Rehabilita case")
    cases = cases[cases.identity_usable & cases.case_id.isin(locations.case_id)].copy()
    cases["official_source_url"] = PLAN_URL
    cases["official_last_modified"] = proof.get("headers", {}).get("Last-Modified", "")
    locations = locations[locations.case_id.isin(cases.case_id)]
    actions = pd.read_parquet(source(PLAN / "actions.parquet"))
    actions = actions[actions.case_id.isin(cases.case_id)]
    parquet(PLAN / "locations.parquet", locations, "plan_rehabilita_municipal_terms")
    parquet(PLAN / "cases.parquet", cases, "plan_rehabilita_municipal_terms")
    parquet(PLAN / "actions.parquet", actions, "plan_rehabilita_municipal_terms")
    plan_refs = locations.groupby("parcel_ref14").case_id.nunique().to_dict()
    db_path = output / "catalogue/catalogue.sqlite"
    db_path.parent.mkdir()
    source_db = source(catalog.root_path() / "catalogue.sqlite")
    with (
        closing(sqlite3.connect(source_db.resolve().as_uri() + "?mode=ro", uri=True)) as src,
        closing(sqlite3.connect(db_path)) as dst,
    ):
        parcels = pd.read_sql_query("SELECT * FROM parcels", src)
        old_count = int(parcels.public_visible.sum())
        parcels["prtr"] = 0
        parcels["prtr_count"] = 0
        parcels["administrative_count"] = parcels.parcel_ref14.map(admin).fillna(0).astype(int)
        parcels["administrative"] = (parcels.administrative_count > 0).astype(int)
        parcels["rehabilita_count"] = parcels.parcel_ref14.map(plan_refs).fillna(0).astype(int)
        parcels["rehabilita"] = (parcels.rehabilita_count > 0).astype(int)
        families = (
            parcels[["construction", "energy", "administrative", "rehabilita"]]
            .astype(bool)
            .sum(axis=1)
        )
        for mode in ("local", "public"):
            parcels[mode + "_visible"] = (families > 0).astype(int)
            parcels[mode + "_families"] = families
            parcels[mode + "_level"] = [
                "Ficha documentada"
                if a or n >= 2
                else "Ficha parcial con evidencia"
                if n
                else "Registro técnico excluido"
                for a, n in zip(parcels.construction, families)
            ]
            parcels[mode + "_reasons"] = [
                " · ".join(
                    k for k in ("construction", "energy", "administrative", "rehabilita") if row[k]
                )
                for _, row in parcels.iterrows()
            ]
        parcels.to_sql("parcels", dst, index=False)
        dst.execute(
            "CREATE UNIQUE INDEX parcel_identity ON parcels(municipality_code,parcel_ref14)"
        )
        dst.execute("CREATE INDEX parcel_zone ON parcels(municipality_code,zone)")
        admitted = set(parcels.loc[parcels.public_visible.eq(1), "parcel_ref14"])
        # One postal table instead of S20 plus a second full S24 database.
        addresses = pd.read_sql_query("SELECT * FROM addresses", src)
        for mode in ("local", "public"):
            addresses[mode + "_refs"] = addresses.refs.map(
                lambda s: json.dumps(
                    [r for r in json.loads(s) if r in admitted], separators=(",", ":")
                )
            )
            addresses[mode + "_visible"] = (addresses[mode + "_refs"] != "[]").astype(int)
        # Keep all original versions (including excluded) to retain located/insufficient behavior.
        addresses.to_sql("addresses", dst, index=False)
        dst.execute("CREATE UNIQUE INDEX address_id ON addresses(id)")
        dst.execute(
            "CREATE TABLE aliases(id TEXT,municipality TEXT,alias TEXT,PRIMARY KEY(municipality,alias,id)) WITHOUT ROWID"
        )
        for chunk in pd.read_sql_query(
            "SELECT DISTINCT id,municipality,alias FROM aliases", src, chunksize=50000
        ):
            dst.executemany(
                "INSERT INTO aliases VALUES(?,?,?)", chunk.itertuples(index=False, name=None)
            )
        dst.execute(
            "CREATE TABLE postal_labels(parcel_ref14 TEXT PRIMARY KEY,address TEXT,district TEXT) WITHOUT ROWID"
        )
        district_names = (
            pd.read_parquet(CITY / "districts.parquet")
            .set_index("district_code")
            .district_name.to_dict()
        )
        assignments = (
            pd.read_parquet(
                demo.CITY / "parcels_audited.parquet", columns=["parcel_ref14", "district_code"]
            )
            .drop_duplicates("parcel_ref14")
            .set_index("parcel_ref14")
            .district_code.to_dict()
        )
        labels = {}
        for row in addresses.sort_values("original").itertuples():
            for ref in json.loads(row.public_refs):
                labels.setdefault(ref, (row.original, district_names.get(assignments.get(ref), "")))
        dst.executemany(
            "INSERT INTO postal_labels VALUES(?,?,?)",
            ((ref, *value) for ref, value in sorted(labels.items())),
        )
        dst.commit()
        dst.execute("VACUUM")
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite corruption")
        counts = parcels.groupby("municipality_code").public_visible.sum().astype(int).to_dict()
        new_count = int(parcels.public_visible.sum())
        postal_count = int(addresses.public_visible.sum())
    files["catalogue/catalogue.sqlite"] = dict(
        bytes=db_path.stat().st_size,
        sha256=digest(db_path),
        source=str(source_db),
        source_sha256=inputs[str(source_db)],
        family="authorized_commercial_catalogue",
        transformation="existing thresholds; authorized evidence only; deduplicated alias index",
    )
    save(
        output / "attribution.json",
        dict(
            catastro="Dirección General del Catastro · INSPIRE; independent derived integration, non-official, no physical certification",
            ceee="Comunidad de Madrid · CC BY 4.0",
            municipal="Ayuntamiento de Madrid · street datasets 213605/200075 and orders 300377, CC BY 4.0",
            rehabilita=dict(
                url=PLAN_URL,
                zip_sha256=PLAN_HASH,
                terms="https://datos.madrid.es/pages/condiciones-generales-ayuntamiento-de-madrid",
                last_modified=proof.get("headers", {}).get("Last-Modified"),
            ),
        ),
    )
    files["attribution.json"] = dict(
        bytes=(output / "attribution.json").stat().st_size,
        sha256=digest(output / "attribution.json"),
        family="source_attribution",
    )
    meta = dict(
        version=VERSION,
        catalogue_version=original["version"],
        policy=dict(
            construction=True,
            energy=True,
            administrative="orders_300377_only",
            rehabilita=True,
            prtr=False,
            ite_iee_pdfs=False,
        ),
        files=files,
        inputs=inputs,
        postal=postal,
        inspection_refs=ite,
        counts=counts,
        postal_versions=postal_count,
        plan_cases=len(cases),
        plan_confirmed_parcels=len(plan_refs),
        catalogue_source_sha256=inputs[str(source_db)],
        build_code_sha256=digest(Path(__file__)),
    )
    # Postal metadata only needs coverage and names in address_view; remove historical input paths.
    meta["postal"] = {k: v for k, v in postal.items() if k in ("municipalities", "version")}
    save(output / "manifest.json", meta)
    hashes = Counter(row["sha256"] for row in inventory)
    total = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
    save(
        report / "comparison.json",
        dict(
            before_bytes=1242181124,
            after_bytes=total,
            reduction_bytes=1242181124 - total,
            reduction_percent=100 * (1 - total / 1242181124),
            files=len(files) + 1,
            before_public_cp=old_count,
            after_public_cp=new_count,
            postal_versions=postal_count,
            counts=counts,
            plan_confirmed_parcels=len(plan_refs),
            plan_cases=len(cases),
            source_duplicate_hashes={k: v for k, v in hashes.items() if v > 1},
            exclusions=[
                "PRTR records and membership contributions",
                "ITE/IEE PDF obligations pending reuse",
                "build-only inputs and historical manifests",
                "S20 duplicate database",
                "unused catalogue geometry copies",
                "unused ETL raw_json columns",
            ],
            no_originals_modified=True,
        ),
    )
    save(report / "preparation_manifest.json", meta)
    print(json.dumps(dict(bytes=total, parcels=new_count, counts=counts), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--plan-evidence", type=Path, required=True)
    args = parser.parse_args()
    build(args.output_dir, args.report_dir, args.plan_evidence)


if __name__ == "__main__":
    main()
