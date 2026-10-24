"""Auditoría offline de fuentes, productos históricos y relaciones CEEE–PRTR."""

from pathlib import Path
import json
import pandas as pd
from .ingest import digest, save_json
from .regional_energy import DEFAULT


def run(root, report):
    root, report = Path(root), Path(report)
    report.mkdir(parents=True, exist_ok=False)
    if not (root / "manifest.json").exists():
        raise RuntimeError("La ingesta aún no ha finalizado")
    manifest = json.loads((root / "manifest.json").read_text())
    cert = pd.read_parquet(root / "energy_certificates.parquet")
    records = pd.read_parquet(root / "energy_source_records.parquet")
    links = pd.read_parquet(root / "energy_parcel_links.parquet")
    summary = pd.read_parquet(root / "energy_municipality_summary.parquet")
    # Catálogo de productos históricos derivados; no son capturas adicionales.
    products = []
    for p in sorted(Path("data/processed").rglob("*.parquet")):
        if any(t in p.name.lower() for t in ["certific", "ceee"]) and "energy/" not in str(p):
            import pyarrow.parquet as pq

            meta = pq.ParquetFile(p)
            products.append(
                {
                    "path": str(p),
                    "rows": meta.metadata.num_rows,
                    "columns": meta.schema.names,
                    "bytes": p.stat().st_size,
                }
            )
    save_json(report / "historical_energy_products.json", products)
    # Perfil exhaustivo de todas las columnas originales, con muestras no publicables.
    columns = [c for c in records if c not in ["source_id", "source_row", "certificate_id"]]
    profile = {}
    for source, f in records.groupby("source_id"):
        profile[source] = {
            c: {
                "missing": int(f[c].eq("").sum()),
                "distinct": int(f[c].nunique()),
                "categories": f[c].value_counts().head(30).to_dict(),
            }
            for c in columns
        }
    save_json(report / "column_profiles.json", profile)
    source_summary = []
    for source, f in records.groupby("source_id"):
        a = f.merge(
            cert[["certificate_id", "municipality_code", "municipality_status"]],
            on="certificate_id",
        )
        source_summary.append(
            {
                "source_id": source,
                "rows": len(f),
                "madrid": int(a.municipality_code.eq("28079").sum()),
                "other_municipalities": int(
                    a.municipality_code.notna().sum() - a.municipality_code.eq("28079").sum()
                ),
                "unclassified": int(a.municipality_code.isna().sum()),
                "municipalities": int(a.municipality_code.nunique()),
            }
        )
    save_json(report / "source_territory_summary.json", source_summary)
    # Casos anómalos: no corregimos desplazamientos de columnas mediante conjeturas.
    anomalies = cert[
        cert.schema_suspect
        | cert.date_after_capture
        | cert.identity_status.ne("unique_registration_content")
        | cert.observation_date.isna()
    ]
    anomalies.to_parquet(report / "source_anomalies.parquet", index=False)
    save_json(
        report / "anomalies.json",
        {
            "source_alignment_suspects": int(cert.schema_suspect.sum()),
            "future_date_rows": int(cert.date_after_capture.sum()),
            "dates_unparseable": int(cert.observation_date.isna().sum()),
            "numeric_statuses": {
                c: cert[c].value_counts().to_dict()
                for c in ["consumption_status", "emissions_status", "area_status"]
            },
            "unresolved_municipality_top30": cert[cert.municipality_code.isna()]
            .edif_muni.value_counts()
            .head(30)
            .to_dict(),
            "privacy": "Originales con direcciones, referencias de unidades y dos literales de correo en municipio: solo local; no se exportan en modo público.",
        },
    )
    # Reconciliación de parcelas y catastro aceptado: cuarentena nunca confirmada.
    for code in ["28065", "28092", "28074", "28007", "28005"]:
        cp = pd.read_parquet(
            Path("data/processed/cadastre/session_12_2_partial_validated_01") / code / "cp.parquet",
            columns=["parcel_ref14"],
        )
        confirmed = links[links.municipality_code.eq(code) & links.link_level.eq("A")]
        assert set(confirmed.parcel_ref14) <= set(cp.parcel_ref14)
    # Verificación completa de hashes de productos y todas las entradas del pipeline.
    verified = {}
    for rel, sha in manifest["outputs"].items():
        assert digest(root / rel) == sha, rel
    for path, sha in manifest["inputs"].items():
        assert digest(Path(path)) == sha, path
    verified["session13_outputs"] = len(manifest["outputs"])
    verified["session13_inputs"] = len(manifest["inputs"])
    for folder in [
        Path("data/processed/territory/session_12_1_final_01"),
        Path("data/processed/grants/regional/session_12_1_final_02"),
        Path("data/processed/cadastre/session_12_2_partial_validated_01"),
    ]:
        path = folder / "manifest.json"
        m = json.loads(path.read_text())
        checks = {}
        for name, sha in m.get("outputs", {}).items():
            if isinstance(sha, str) and (folder / name).is_file():
                checks[name] = digest(folder / name) == sha
        assert all(checks.values()), str(folder)
        verified[str(folder)] = {"manifest_sha256": digest(path), "verified_outputs": len(checks)}
    save_json(report / "integrity_verification.json", verified)
    # Descriptivos por certificados únicos; nunca se asigna letra a parcela.
    confirmed = links[links.link_level.eq("A")][
        ["certificate_id", "municipality_code", "parcel_ref14"]
    ].drop_duplicates()
    joint = pd.read_parquet(root / "energy_grants_summary.parquet")
    observed = (
        confirmed.merge(
            joint[joint.observation.eq("energy_and_prtr")][["municipality_code", "parcel_ref14"]]
        )
        .drop_duplicates("certificate_id")
        .merge(cert, on="certificate_id", suffixes=("_link", ""))
    )
    observed.groupby(
        ["municipality_code", "scope", "consumption_rating"], dropna=False
    ).size().rename("certificate_count").reset_index().to_parquet(
        report / "prtr_energy_distribution.parquet", index=False
    )
    municipal = summary[
        [
            "municipality_code",
            "name",
            "source_records",
            "canonical_certificates",
            "confirmed_cp_certificates",
            "quarantine_cp_certificates",
            "ambiguous_cp_certificates",
        ]
    ].copy()
    municipal.to_csv(report / "municipal_results.csv", index=False)
    baseline_path = Path("data/processed/session_2/certificates_integrated.parquet")
    baseline = pd.read_parquet(baseline_path, columns=["record_id", "parcel_status"])
    before = set(baseline.loc[baseline.parcel_status.eq("confirmed"), "record_id"])
    after = set(
        links.loc[links.municipality_code.eq("28079") & links.link_level.eq("A"), "certificate_id"]
    )
    changed = links[links.certificate_id.isin(before - after)]
    changed.to_parquet(report / "madrid_regression_changes.parquet", index=False)
    save_json(
        report / "madrid_regression.json",
        {
            "baseline_sha256": digest(baseline_path),
            "old_confirmed": len(before),
            "new_confirmed": len(after),
            "lost_confirmations": len(before - after),
            "new_confirmations": len(after - before),
            "reasons": changed.groupby("link_reason").certificate_id.nunique().to_dict(),
        },
    )
    # Año constructivo literal: no se imputa desde BU a certificados de unidades.
    observed.groupby(["edif_año", "scope", "consumption_rating"], dropna=False).size().rename(
        "certificate_count"
    ).reset_index().to_parquet(report / "prtr_energy_construction_period.parquet", index=False)
    save_json(
        report / "manifest.json",
        {
            "energy_manifest_sha256": digest(root / "manifest.json"),
            "audit_code_sha256": digest(Path(__file__)),
            "outputs": {
                str(p.relative_to(report)): digest(p)
                for p in sorted(report.rglob("*"))
                if p.is_file()
            },
        },
    )
    print(
        json.dumps(
            {
                "sources": source_summary,
                "integrity": verified,
                "prtr_linked_unique_certificates": len(observed),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--energy-dir", type=Path, default=DEFAULT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.energy_dir, args.output_dir)


if __name__ == "__main__":
    main()
