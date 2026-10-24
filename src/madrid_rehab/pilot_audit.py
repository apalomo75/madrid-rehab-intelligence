"""Informes del piloto real: ausencia de captura no equivale a cero incidencias."""

import argparse
import json
from pathlib import Path

import pandas as pd

from .cadastre_download import MANIFEST, RAW, inspect_zip, load_manifest
from .cadastre_pilot import DEFAULT as CADASTRE
from .ingest import digest, save_json
from .regional_cadastre import verify_partition
from .territorial_prtr import DEFAULT as TERRITORY

REGIONAL = Path("data/processed/grants/regional/session_12_2_final_01")


def run(output, regional=REGIONAL, cadastre=CADASTRE, raw=RAW, download_report=None):
    output, regional, cadastre, raw = map(Path, (output, regional, cadastre, raw))
    if output.exists():
        raise FileExistsError("Usar informe nuevo")
    metadata = json.loads((regional / "manifest.json").read_text())
    for name, sha in metadata["outputs"].items():
        if digest(regional / name) != sha:
            raise ValueError("Producto alterado")
    for name, sha in metadata["inputs"].items():
        if digest(name) != sha:
            raise ValueError("Entrada alterada")
    if digest(regional / "grant_municipality_links.parquet") != digest(
        TERRITORY / "grant_municipality_links.parquet"
    ):
        raise ValueError("Se han modificado decisiones territoriales congeladas")
    plan = load_manifest(MANIFEST)
    resources = []
    for r in plan["resources"]:
        path = raw / r["cadastre_code"] / (r["kind"] + ".zip")
        meta = path.with_suffix(".zip.json")
        verified = False
        if path.exists() and meta.exists():
            detail = json.loads(meta.read_text())
            if digest(path) != detail["sha256"]:
                raise ValueError("Original alterado")
            inspect_zip(path, r["kind"])
            verified = True
        resources.append(
            dict(
                municipality_code=r["municipality_code"],
                kind=r["kind"],
                file_exists=path.exists(),
                verified=verified,
                bytes=path.stat().st_size if path.exists() else None,
                sha256=digest(path) if verified else None,
            )
        )
    summary = pd.read_parquet(regional / "pilot_summary.parquet")
    programs = pd.read_parquet(regional / "municipality_program_summary.parquet")
    links = pd.read_parquet(regional / "grant_parcel_links.parquet")
    if any(c in links for c in ["importe_centimos", "importe_concedido"]):
        raise ValueError("Importe duplicable en relaciones")
    if (
        int(programs.expedientes.sum()) != 7532
        or int(programs.importe_centimos.sum()) != 31552733899
    ):
        raise ValueError("Contabilidad regional no reconciliada")
    details = []
    for code in summary.municipality_code:
        path = cadastre / code
        details.append(
            dict(municipality_code=code, assessment="not_assessable_without_real_data")
            if not (path / "manifest.json").exists()
            else verify_partition(path)
        )
    output.mkdir(parents=True)
    summary.to_csv(output / "municipality_summary.csv", index=False)
    save_json(output / "resource_integrity.json", resources)
    save_json(output / "cp_bu_quality.json", details)
    save_json(
        output / "prtr_cp_quality.json",
        summary[
            [
                "municipality_code",
                "name",
                "prtr",
                "prtr_linked",
                "prtr_pending",
                "ambiguous_relations",
                "candidate_relations",
                "importe_centimos",
                "quality",
            ]
        ].to_dict("records"),
    )
    quality = dict(
        planned_municipalities=5,
        downloaded_municipalities=sum(
            all(r["verified"] for r in resources if r["municipality_code"] == c)
            for c in summary.municipality_code
        ),
        verified_resources=sum(r["verified"] for r in resources),
        cp_integrated_municipalities=int(summary.cp.gt(0).sum()),
        bu_integrated_municipalities=int(summary.bu.gt(0).sum()),
        pilot_prtr=int(summary.prtr.sum()),
        pilot_prtr_linked=int(summary.prtr_linked.sum()),
        pilot_prtr_pending=int(summary.prtr_pending.sum()),
        pilot_amount_cents=int(summary.importe_centimos.sum()),
        regional_grants=7532,
        regional_amount_cents=31552733899,
        territorial_decisions_preserved=True,
        processing_seconds=metadata["seconds"],
        peak_rss_kib=metadata["peak_rss_kib"],
        real_ingestion_performance_assessable=bool(metadata["integrated_municipalities"]),
        previous_cp_bu_municipalities=1,
        previous_cp_bu_municipality="Madrid capital",
        visual_validation="pending_joint_review_not_requested_this_session",
        prtr_public_exposure=False,
        ambiguous_relations_interpretation="Counts of recorded relations only; absent CP cannot demonstrate absence of ambiguity",
    )
    initial = Path("reports/session_12_2/initial_state.json")
    if initial.exists():
        protected = json.loads(initial.read_text())["protected_files"]
        changed = [p for p, sha in protected.items() if digest(p) != sha]
        quality.update(protected_files=len(protected), protected_files_changed=changed)
        if changed:
            raise ValueError("Originales/snapshots alterados")
    inputs = {
        str(regional / "manifest.json"): digest(regional / "manifest.json"),
        str(MANIFEST): digest(MANIFEST),
    }
    if download_report:
        path = Path(download_report) / "downloads.json"
        download_rows = json.loads(path.read_text())
        expected = {(r["municipality_code"], r["kind"], r["url"]) for r in plan["resources"]}
        if {(r["municipality_code"], r["kind"], r["url"]) for r in download_rows} != expected:
            raise ValueError("Informe de otra captura")
        save_json(output / "download_report.json", download_rows)
        inputs[str(path)] = digest(path)
    save_json(output / "quality.json", quality)
    save_json(
        output / "manifest.json",
        dict(
            inputs=inputs,
            outputs={p.name: digest(p) for p in output.iterdir() if p.is_file()},
            code_sha256={
                str(p): digest(p)
                for p in [
                    Path(__file__),
                    Path(__file__).with_name("cadastre_download.py"),
                    Path(__file__).with_name("cadastre_pilot.py"),
                    Path(__file__).with_name("pilot_objects.py"),
                    Path(__file__).with_name("pilot_grants.py"),
                    Path(__file__).with_name("regional_cadastre.py"),
                ]
            },
        ),
    )
    return quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--regional-dir", type=Path, default=REGIONAL)
    parser.add_argument("--cadastre-dir", type=Path, default=CADASTRE)
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--download-report", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.output_dir,
                args.regional_dir,
                args.cadastre_dir,
                args.raw_dir,
                args.download_report,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
