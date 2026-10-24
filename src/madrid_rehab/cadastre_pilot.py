"""Piloto acotado CP/BU: captura reanudable, ingesta offline y PRTR congelado en sesión 12.1."""

import argparse
import json
import resource
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import shapely as sh

from .cadastre_download import MANIFEST, RAW, download, load_manifest, inspect_zip
from .grants import DEFAULT as GRANTS
from .ingest import digest, save_json
from .municipal_boundaries import DEFAULT as BOUNDARIES
from .pilot_grants import CONFIRMED, match_municipality
from .regional import load_official_boundaries
from .regional_cadastre import process_municipality, verify_partition
from .territorial_prtr import DEFAULT as TERRITORY

DEFAULT = Path("data/processed/cadastre/session_12_2_pilot_01")
REGIONAL = Path("data/processed/grants/regional/session_12_2_pilot_01")


def integrate(raw=RAW, output=DEFAULT, regional=REGIONAL, manifest_path=MANIFEST):
    started = time.perf_counter()
    raw, output, regional = map(Path, (raw, output, regional))
    if regional.exists():
        raise FileExistsError("Usar salida regional nueva")
    plan = load_manifest(manifest_path)
    boundaries = load_official_boundaries(
        BOUNDARIES / "municipality_boundaries.parquet", BOUNDARIES / "manifest.json"
    ).set_index("municipality_code")
    source_meta = json.loads((TERRITORY / "manifest.json").read_text())
    for name, sha in source_meta["outputs"].items():
        if digest(TERRITORY / name) != sha:
            raise ValueError("Clasificación territorial alterada")
    grant_meta = json.loads((GRANTS / "grant_source_manifest.json").read_text())
    if digest(GRANTS / "grants.parquet") != grant_meta["outputs"]["grants.parquet"]:
        raise ValueError("Hechos PRTR alterados")
    grants = (
        pd.read_parquet(GRANTS / "grants.parquet")
        .drop(columns="municipality_code")
        .merge(
            pd.read_parquet(TERRITORY / "grant_municipality_links.parquet")[
                ["expediente_id", "municipality_code"]
            ],
            on="expediente_id",
            validate="one_to_one",
        )
    )
    baseline = pd.read_parquet(TERRITORY / "grant_parcel_links.parquet")
    source_decisions = pd.read_parquet(TERRITORY / "grant_municipality_links.parquet")
    resources = pd.DataFrame(plan["resources"])
    codes = list(resources.municipality_code.drop_duplicates())
    results = []
    partitions = {}
    collection_inventory = []
    output.mkdir(parents=True, exist_ok=True)
    for code in codes:
        group = resources[resources.municipality_code.eq(code)]
        cp_resource = group[group.kind.eq("cp")].iloc[0]
        config = dict(
            municipality_code=code,
            cadastre_code=cp_resource.cadastre_code,
            name=cp_resource["name"],
            evidence_url=cp_resource.feed_url,
            identity_review=cp_resource.identity_review,
            plan_sha256=digest(manifest_path),
        )
        state = "missing"
        error = None
        complete = True
        for r in group.itertuples():
            config["url_" + r.kind] = r.url
            config["source_date_" + r.kind] = r.updated
            path = raw / r.cadastre_code / (r.kind + ".zip")
            meta = path.with_suffix(".zip.json")
            if not path.exists() or not meta.exists():
                complete = False
                continue
            metadata = json.loads(meta.read_text())
            from .cadastre_download import official_url

            if digest(path) != metadata["sha256"] or metadata["url"] != official_url(r.url):
                raise ValueError("Original catastral alterado")
            collection_inventory.append(
                dict(
                    municipality_code=code,
                    kind=r.kind,
                    path=str(path),
                    sha256=metadata["sha256"],
                    **inspect_zip(path, r.kind),
                )
            )
        product = None
        if complete:
            try:
                product = process_municipality(
                    config,
                    raw,
                    output,
                    sh.from_wkt(boundaries.loc[code].geometry_wkt),
                    offline=True,
                    audited=True,
                )
                partitions[code] = output / code
                state = "integrated"
            except (OSError, ValueError, KeyError) as exc:
                state = "ingestion_blocked"
                error = str(exc)
        selected = grants[grants.municipality_code.eq(code)]
        results.append(
            dict(
                municipality_code=code,
                name=config["name"],
                downloaded=complete,
                status=state,
                error=error,
                cp=product["cp_rows"] if product else 0,
                cp_usable=product["cp_usable"] if product else 0,
                bu=product["bu_objects"] if product else 0,
                bu_usable=product["bu_usable"] if product else 0,
                quality=product["quality_status"]
                if product
                else "blocked_source_integrity"
                if state == "ingestion_blocked"
                else "not_assessable_without_real_data",
                prtr=len(selected),
                importe_centimos=int(selected.importe_centimos.sum()),
            )
        )
    # Mantener exactamente todas las decisiones y relaciones históricas fuera del piloto.
    all_links = [
        baseline[
            ~baseline.expediente_id.isin(
                grants[grants.municipality_code.isin(partitions)].expediente_id
            )
        ].copy()
    ]
    candidate_tables = []
    for code, root in partitions.items():
        verify_partition(root)
        selected = grants[grants.municipality_code.eq(code)]
        refs = baseline[baseline.expediente_id.isin(selected.expediente_id)][
            ["expediente_id", "parcel_ref14"]
        ]
        links, candidates = match_municipality(
            selected, refs, pd.read_parquet(root / "cp.parquet"), code
        )
        all_links.append(links)
        candidate_tables.append(candidates)
    links = pd.concat(all_links, ignore_index=True)
    geographic = source_decisions.set_index("expediente_id").municipality_code
    links["geographic_municipality_code"] = links.expediente_id.map(geographic)
    candidates = (
        pd.concat(candidate_tables, ignore_index=True)
        if candidate_tables
        else pd.DataFrame(
            columns=[
                "expediente_id",
                "parcel_ref14",
                "parcel_id",
                "geographic_municipality_code",
                "match_status",
                "match_evidence",
                "candidate_count",
                "candidates_truncated",
            ]
        )
    )
    confirmed = set(links.loc[links.match_status.isin(CONFIRMED), "expediente_id"])
    ambiguous = (
        links[links.match_status.isin(["ambiguous", "ambiguous_historical_madrid"])]
        .groupby("geographic_municipality_code")
        .size()
    )
    for result in results:
        ids = set(
            grants.loc[grants.municipality_code.eq(result["municipality_code"]), "expediente_id"]
        )
        result.update(
            prtr_linked=len(ids & confirmed),
            prtr_pending=len(ids - confirmed),
            ambiguous_relations=int(ambiguous.get(result["municipality_code"], 0)),
            candidate_relations=int(
                candidates.geographic_municipality_code.eq(result["municipality_code"]).sum()
            ),
        )
    summary = pd.DataFrame(results)
    if len(grants) != 7532 or int(grants.importe_centimos.sum()) != 31552733899:
        raise ValueError("Reconciliación regional fallida")
    facts = grants[["expediente_id", "municipality_code", "programa", "importe_centimos"]]
    products = pd.read_parquet(TERRITORY / "municipal_products.parquet")
    for code in partitions:
        products.loc[products.municipality_code.eq(code), ["cp_available", "bu_available"]] = True
    products["cp_linked"] = (
        products.municipality_code.map(
            facts[facts.expediente_id.isin(confirmed)].groupby("municipality_code").size()
        )
        .fillna(0)
        .astype("int64")
    )
    products["cp_linked_percent"] = (
        100 * products.cp_linked / products.expedientes.replace(0, float("nan"))
    ).fillna(0)
    inputs = {
        str(manifest_path): digest(manifest_path),
        str(TERRITORY / "manifest.json"): digest(TERRITORY / "manifest.json"),
        str(GRANTS / "grant_source_manifest.json"): digest(GRANTS / "grant_source_manifest.json"),
    } | {str(p / "manifest.json"): digest(p / "manifest.json") for p in partitions.values()}
    inputs.update({r["path"]: r["sha256"] for r in collection_inventory})
    regional.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=regional.parent, prefix=".pilot-prtr-") as temp:
        stage = Path(temp) / "product"
        stage.mkdir()
        # Copia binaria de la decisión congelada, no nueva asignación municipal.
        (stage / "grant_municipality_links.parquet").write_bytes(
            (TERRITORY / "grant_municipality_links.parquet").read_bytes()
        )
        tables = {
            "grant_parcel_links": links,
            "grant_spatial_candidates": candidates,
            "pilot_summary": summary,
            "municipal_products": products,
            "municipality_program_summary": pd.read_parquet(
                TERRITORY / "municipality_program_summary.parquet"
            ),
            "grant_match_summary": pd.DataFrame(
                {
                    "expediente_id": grants.expediente_id,
                    "current_cp_confirmed": grants.expediente_id.isin(confirmed),
                }
            ),
        }
        for name, frame in tables.items():
            frame.to_parquet(stage / (name + ".parquet"), index=False)
        save_json(stage / "collection_inventory.json", collection_inventory)
        metadata = dict(
            version="regional-grants-pilot-12.2",
            source_manifest_sha256=digest(GRANTS / "grant_source_manifest.json"),
            inputs=inputs,
            outputs={p.name: digest(p) for p in stage.iterdir() if p.is_file()},
            grants=7532,
            amount_cents=31552733899,
            integrated_municipalities=list(partitions),
            seconds=time.perf_counter() - started,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        )
        save_json(stage / "manifest.json", metadata)
        stage.rename(regional)
    if partitions:
        from .cadastre_download import write_json

        write_json(
            output / "active_prtr.json",
            {
                "path": str(regional),
                "manifest_sha256": digest(regional / "manifest.json"),
            },
        )
    return summary, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--regional-output", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.regional_output is None:
        args.regional_output = REGIONAL.parent / (
            "session_12_2_run_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            + "_"
            + uuid.uuid4().hex[:6]
        )
    if not args.offline:
        results, report = download(args.manifest, args.raw_dir)
        print("Informe de descarga:", report)
        if not any(r["status"].startswith("verified_") for r in results):
            print("Red bloqueada: se genera cobertura real sin incorporar cartografía ausente.")
    summary, metadata = integrate(
        args.raw_dir, args.output_dir, args.regional_output, args.manifest
    )
    print("Producto regional:", args.regional_output)
    print("Particiones catastrales:", args.output_dir)
    print(summary.to_string(index=False))
    print(json.dumps(metadata, indent=2))
    raise SystemExit(0 if summary.status.eq("integrated").all() else 2)


if __name__ == "__main__":
    main()
