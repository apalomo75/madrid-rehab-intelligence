"""Selective PRTR runtime product, candidate and explicitly authorized release."""

import argparse
from functools import lru_cache
import json
from pathlib import Path
import shutil
import sqlite3

import pandas as pd

from .ingest import digest

PROGRAMS = ("any", "P1", "P3", "P4", "P5")
CONFIRMED = ("confirmed", "confirmed_historical_madrid")
PRODUCT = "prtr/confirmed.parquet"
SOURCE_URL = "https://visorrehabilitaprtrmadrid.coam.org/"
API_URL = SOURCE_URL + "api/main.cgi?method=resum&pr=all"
ORIGINAL_SHA256 = "03b6273b8a9c2f53e2fdc211c44fe495176d44aaa4727f7714ac43d4623adc36"
GRANTS = Path("data/processed/grants/session_11_final_03")
LINKS = Path("data/processed/cadastre/session_12_2_partial_validated_01")
CATALOG = Path("data/processed/commercial_catalog/session_24_public_02")


def validate_release(meta):
    proof = meta.get("prtr_authorization", {})
    required = {"derived_records", "locations", "amounts", "cadastral_links", "public_web"}
    if (
        meta.get("release_status") != "authorized"
        or not required.issubset(proof.get("scope", []))
        or not proof.get("attribution")
        or proof.get("dataset_sha256") != ORIGINAL_SHA256
        or proof.get("source_url") != API_URL
        or not proof.get("decision_date")
        or not proof.get("terms")
        or PRODUCT not in meta["files"]
    ):
        raise ValueError("PRTR redistribution authorization is pending")
    if proof.get("status") == "owner_confirmed":
        if (
            proof.get("basis") != "project_owner_communication"
            or proof.get("documentary_verified") is not False
            or not proof.get("statement")
            or proof.get("evidence_file")
        ):
            raise ValueError("Invalid owner-reported PRTR authorization")
    elif (
        proof.get("status") != "verified"
        or not proof.get("rights_holder")
        or not proof.get("evidence_file")
        or proof["evidence_file"] not in meta["files"]
    ):
        raise ValueError("PRTR redistribution authorization is pending")


@lru_cache(maxsize=6)
def _programme_refs(code, program, token):
    from . import production_bundle as bundle

    rows = bundle.read(
        PRODUCT, [("municipality_code", "==", code)], ["parcel_ref14", "programa", "match_status"]
    )
    rows = rows[rows.match_status.isin(CONFIRMED)]
    if program != "any":
        rows = rows[rows.programa.eq(program)]
    return frozenset(rows.parcel_ref14)


def program_refs(code, program):
    if program not in PROGRAMS:
        raise ValueError("Invalid PRTR programme")
    from . import production_bundle as bundle

    if bundle.active():
        return (
            _programme_refs(code, program, bundle.signature())
            if bundle.allowed_prtr()
            else frozenset()
        )
    rows = pd.read_parquet(LINKS / "grant_parcel_links.parquet")
    grants = pd.read_parquet(
        GRANTS / "grants.parquet", columns=["expediente_id", "programa", "identity_conflict"]
    )
    rows = select(rows, grants)
    rows = rows[rows.municipality_code.eq(code)]
    return frozenset(
        rows[rows.programa.eq(program)].parcel_ref14 if program != "any" else rows.parcel_ref14
    )


def records(code, ref):
    from . import production_bundle as bundle

    if not bundle.allowed_prtr():
        return pd.DataFrame()
    rows = bundle.read(PRODUCT, [("municipality_code", "==", code), ("parcel_ref14", "==", ref)])
    return rows[rows.match_status.isin(CONFIRMED)].drop_duplicates("expediente_id")


def select(links, grants):
    links = links[links.match_status.isin(CONFIRMED) & ~links.territorial_conflict].copy()
    links["municipality_code"] = links.geographic_municipality_code
    result = links.merge(
        grants, on="expediente_id", suffixes=("", "_source"), validate="many_to_one"
    )
    return result[~result.identity_conflict].drop_duplicates(
        ["municipality_code", "parcel_ref14", "expediente_id"]
    )


def build(base, output, report):
    """Create local candidate only. Never infer authorization or create an archive."""
    from . import production_bundle as bundle

    base, output, report = map(Path, (base, output, report))
    if output.exists() or report.exists():
        raise FileExistsError("New candidate and report directories required")
    original = json.loads((base / "manifest.json").read_text())
    if original["version"] != bundle.VERSION:
        raise ValueError("Incompatible base")
    for name, item in original["files"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or digest(base / path) != item["sha256"]:
            raise ValueError("Base integrity failure")
    if original["policy"]["prtr"]:
        raise ValueError("Expected original PRTR-free base")
    inputs = json.loads((CATALOG / "manifest.json").read_text())["inputs"]
    for path in (GRANTS / "grants.parquet", LINKS / "grant_parcel_links.parquet"):
        if digest(path) != inputs[str(path)]:
            raise ValueError("Unauthenticated PRTR input")
    grant_columns = [
        "expediente_id",
        "programa",
        "importe_concedido",
        "importe_centimos",
        "fecha_concesion",
        "fecha_pago",
        "fecha_actualizacion",
        "etapa_administrativa",
        "direccion",
        "identity_conflict",
        "territorial_quality",
        "source_row",
        "origen",
        "fecha_captura",
        "referencia_catastral",
        "referencias_adicionales",
        "longitude",
        "latitude",
        "fase",
    ]
    grants = pd.read_parquet(GRANTS / "grants.parquet", columns=grant_columns)
    links = pd.read_parquet(LINKS / "grant_parcel_links.parquet")
    rows = select(links, grants)
    rows["source_url"] = SOURCE_URL
    rows["source_sha256"] = json.loads((GRANTS / "grant_source_manifest.json").read_text()).get(
        "source_sha256", "03b6273b8a9c2f53e2fdc211c44fe495176d44aaa4727f7714ac43d4623adc36"
    )
    shutil.copytree(base, output)
    report.mkdir(parents=True)
    target = output / PRODUCT
    target.parent.mkdir()
    rows.sort_values(["municipality_code", "parcel_ref14", "expediente_id"]).to_parquet(
        target, index=False, compression="zstd", row_group_size=512
    )
    counts = rows.groupby(["municipality_code", "parcel_ref14"]).expediente_id.nunique()
    dbpath = output / "catalogue/catalogue.sqlite"
    with sqlite3.connect(dbpath) as db:
        for (code, ref), count in counts.items():
            db.execute(
                "UPDATE parcels SET prtr=1,prtr_count=?,local_visible=1,public_visible=1 WHERE municipality_code=? AND parcel_ref14=?",
                (int(count), code, ref),
            )
        for mode in ("local", "public"):
            db.execute(
                f"UPDATE parcels SET {mode}_families=construction+energy+administrative+CASE WHEN prtr=1 OR rehabilita=1 THEN 1 ELSE 0 END"
            )
        for mode in ("local", "public"):
            db.execute(
                f"UPDATE parcels SET {mode}_reasons=CASE WHEN {mode}_reasons='' THEN 'prtr' ELSE {mode}_reasons || ' · prtr' END WHERE prtr=1"
            )
        # Restore only existing documented postal memberships for admitted identities.
        refs = {r[0] for r in db.execute("SELECT parcel_ref14 FROM parcels WHERE public_visible=1")}
        for rowid, raw in db.execute("SELECT rowid,refs FROM addresses").fetchall():
            allowed = sorted(set(json.loads(raw)) & refs)
            db.execute(
                "UPDATE addresses SET public_refs=?,public_visible=?,local_refs=?,local_visible=? WHERE rowid=?",
                (
                    json.dumps(allowed),
                    int(bool(allowed)),
                    json.dumps(allowed),
                    int(bool(allowed)),
                    rowid,
                ),
            )
        for mode in ("local", "public"):
            db.execute(
                f"UPDATE parcels SET {mode}_level=CASE WHEN construction=1 OR {mode}_families>=2 THEN 'Ficha documentada' WHEN {mode}_families=1 THEN 'Ficha parcial con evidencia' ELSE 'Registro técnico excluido' END"
            )
        counts_by_city = dict(
            db.execute(
                "SELECT municipality_code,SUM(public_visible) FROM parcels GROUP BY municipality_code"
            )
        )
    meta = json.loads((output / "manifest.json").read_text())
    meta.update(
        release_status="authorization_pending",
        prtr_authorization={"status": "pending"},
        counts=counts_by_city,
    )
    meta["policy"]["prtr"] = True
    meta["files"][PRODUCT] = {
        "sha256": digest(target),
        "bytes": target.stat().st_size,
        "family": "prtr_confirmed_only",
        "rows": len(rows),
        "inputs": {
            str(p): digest(p)
            for p in (GRANTS / "grants.parquet", LINKS / "grant_parcel_links.parquet")
        },
    }
    meta["files"]["catalogue/catalogue.sqlite"].update(
        sha256=digest(dbpath),
        bytes=dbpath.stat().st_size,
        transformation="base authorized evidence plus confirmed PRTR; local candidate only",
    )
    (output / "manifest.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    summary = {
        "status": "authorization_pending",
        "distributable": False,
        "original_cases": len(grants),
        "confirmed_cases": rows.expediente_id.nunique(),
        "confirmed_parcels": rows.parcel_ref14.nunique(),
        "confirmed_links": len(rows),
        "product_bytes": target.stat().st_size,
        "by_municipality_program": rows.groupby(["municipality_code", "programa"])
        .agg(cases=("expediente_id", "nunique"), parcels=("parcel_ref14", "nunique"))
        .reset_index()
        .to_dict("records"),
        "base_manifest_sha256": digest(base / "manifest.json"),
    }
    (report / "candidate.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def authorize(candidate, output, evidence, document):
    """New release after an actual written authorization has been reviewed by the owner."""
    candidate, output, evidence, document = map(Path, (candidate, output, evidence, document))
    if output.exists():
        raise FileExistsError("New release directory required")
    proof = json.loads(evidence.read_text())
    if not proof.get("owner_reviewed") or proof.get("document_sha256") != digest(document):
        raise ValueError("Reviewed written authorization and matching document required")
    meta = json.loads((candidate / "manifest.json").read_text())
    if meta.get("release_status") != "authorization_pending":
        raise ValueError("Expected pending candidate")
    for name, item in meta["files"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or digest(candidate / path) != item["sha256"]:
            raise ValueError("Candidate integrity failure")
    proof["evidence_file"] = "prtr/authorization.txt"
    meta["files"][proof["evidence_file"]] = {
        "sha256": digest(document),
        "bytes": document.stat().st_size,
        "family": "prtr_authorization",
    }
    meta.update(release_status="authorized", prtr_authorization=proof)
    validate_release(meta)
    shutil.copytree(candidate, output)
    shutil.copyfile(document, output / proof["evidence_file"])
    (output / "manifest.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")


def release_from_owner(candidate, output, release_id, decision_date):
    """Record the owner's authorization communication without claiming document verification."""
    candidate, output = Path(candidate), Path(output)
    if output.exists():
        raise FileExistsError("New release directory required")
    if not release_id or not decision_date:
        raise ValueError("Release identity and owner communication date required")
    meta = json.loads((candidate / "manifest.json").read_text())
    if meta.get("release_status") != "authorization_pending" or not meta["policy"]["prtr"]:
        raise ValueError("Expected pending PRTR candidate")
    for name, item in meta["files"].items():
        path = Path(name)
        source = candidate / path
        if (
            path.is_absolute()
            or ".." in path.parts
            or not source.resolve().is_relative_to(candidate.resolve())
            or source.is_symlink()
            or digest(source) != item["sha256"]
        ):
            raise ValueError("Candidate integrity failure")
    meta.update(
        release_id=release_id,
        release_status="authorized",
        prtr_authorization={
            "status": "owner_confirmed",
            "basis": "project_owner_communication",
            "documentary_verified": False,
            "decision_date": decision_date,
            "statement": "The project owner confirms possession of PRTR reuse authorization and instructs inclusion in the public production release. No documentary verification performed.",
            "dataset_sha256": ORIGINAL_SHA256,
            "source_url": API_URL,
            "scope": ["derived_records", "locations", "amounts", "cadastral_links", "public_web"],
            "terms": "Public inclusion instructed by project owner; source attribution and original documentary scope preserved.",
            "attribution": "Fuente: Comunidad de Madrid · visor de rehabilitación PRTR alojado en COAM. Actualización indicada: 20/07/2026; captura: 24/10/2026. Relaciones catastrales derivadas por Madrid Rehab Intelligence; concesión no acredita pago ni ejecución.",
        },
    )
    validate_release(meta)
    # Copy only authenticated runtime products, never stray private or personal files.
    output.mkdir(parents=True)
    for name in meta["files"]:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate / name, destination)
    (output / "manifest.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-confirmed", action="store_true")
    parser.add_argument("--release-id")
    parser.add_argument("--decision-date")
    parser.add_argument("--base", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--document", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path)
    args = parser.parse_args()
    if args.owner_confirmed:
        if (
            not (args.candidate and args.release_id and args.decision_date)
            or args.authorization
            or args.document
            or args.base
        ):
            parser.error("Owner-confirmed release requires candidate/release-id/decision-date only")
        meta = release_from_owner(
            args.candidate, args.output_dir, args.release_id, args.decision_date
        )
        print(
            json.dumps(
                {
                    "release_id": meta["release_id"],
                    "authorization": meta["prtr_authorization"]["status"],
                }
            )
        )
    elif args.candidate and args.authorization and args.document:
        authorize(args.candidate, args.output_dir, args.authorization, args.document)
    elif (
        args.base
        and args.report_dir
        and not (args.authorization or args.document or args.candidate)
    ):
        print(json.dumps(build(args.base, args.output_dir, args.report_dir), indent=2))
    else:
        parser.error("Supply base/report-dir or candidate/authorization/document")


if __name__ == "__main__":
    main()
