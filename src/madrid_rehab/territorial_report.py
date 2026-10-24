"""Informes locales agregados de sesión 12.1; detalle sensible en el producto ignorado."""

import argparse
import json
from pathlib import Path

import pandas as pd

from .ingest import digest, save_json
from .municipal_boundaries import DEFAULT as BOUNDARIES
from .normalize import text_key
from .territorial_prtr import DEFAULT


def run(output, classification=DEFAULT, boundaries=BOUNDARIES):
    output, classification, boundaries = map(Path, (output, classification, boundaries))
    if output.exists():
        raise FileExistsError("Usar informe nuevo")
    manifests = {}
    for root in (classification, boundaries):
        manifest = json.loads((root / "manifest.json").read_text())
        for name, sha in manifest["outputs"].items():
            if digest(root / name) != sha:
                raise ValueError("Producto alterado")
        manifests[str(root / "manifest.json")] = digest(root / "manifest.json")
    products = pd.read_parquet(classification / "municipal_products.parquet")
    summary = pd.read_parquet(classification / "municipality_program_summary.parquet")
    decisions = pd.read_parquet(classification / "grant_municipality_links.parquet")
    quality = json.loads((classification / "quality.json").read_text())
    output.mkdir(parents=True)
    products.to_csv(output / "municipal_products.csv", index=False)
    summary.merge(
        products[["municipality_code", "name"]],
        on="municipality_code",
        how="left",
        validate="many_to_one",
    ).to_csv(output / "municipality_program_summary.csv", index=False)
    save_json(output / "quality.json", quality)
    save_json(
        output / "conflicts.json",
        dict(
            conflicting_or_ambiguous=quality["ambiguous"],
            unassigned=quality["unassigned_grants"],
            status_counts=quality["statuses"],
            minimum_border_distance_m=float(decisions.boundary_distance_m.min()),
            within_10m=int(decisions.boundary_distance_m.le(10).sum()),
            within_25m=int(decisions.boundary_distance_m.le(25).sum()),
            detail_path=str(classification / "territorial_conflicts.parquet"),
            interpretation="No detected conflicts in this capture under 1m operational tolerance; not proof of legal/geocoding accuracy",
        ),
    )
    resources = pd.read_parquet(
        "data/processed/territory/session_12_final_01/cadastre_resources.parquet"
    )
    pilots = []
    for name in ["Getafe", "Móstoles", "Alcorcón", "Leganés", "Alcalá de Henares"]:
        municipality = products[products.name.map(text_key).eq(text_key(name))].iloc[0]
        matches = resources[resources.cadastre_name.map(text_key).eq(text_key(name))]
        for row in matches.itertuples():
            pilots.append(
                dict(
                    name=name,
                    ine_code=municipality.municipality_code,
                    cadastre_code=row.cadastre_code,
                    url_cp=row.url_cp,
                    url_bu=row.url_bu,
                    recognition="URLs present in preserved official CP/BU feeds; no new download or HTTP validation",
                    identity_status="exact full name comparison; not an authorized import crosswalk",
                )
            )
    save_json(output / "pilot_url_recognition.json", pilots)
    initial = Path("reports/session_12_1/initial_state.json")
    if initial.exists():
        protected = json.loads(initial.read_text())["protected_files"]
        changed = [name for name, sha in protected.items() if digest(name) != sha]
        save_json(
            output / "preservation.json", dict(protected_files=len(protected), changed=changed)
        )
        if changed:
            raise ValueError("Snapshot histórico alterado")
        manifests[str(initial)] = digest(initial)
    save_json(
        output / "manifest.json",
        dict(
            inputs=manifests,
            outputs={p.name: digest(p) for p in output.iterdir() if p.is_file()},
            code_sha256={
                str(p): digest(p)
                for p in [
                    Path(__file__),
                    Path(__file__).with_name("municipal_boundaries.py"),
                    Path(__file__).with_name("territorial_prtr.py"),
                    Path(__file__).with_name("regional_grants.py"),
                ]
            },
        ),
    )
    return quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--classification-dir", type=Path, default=DEFAULT)
    parser.add_argument("--boundaries-dir", type=Path, default=BOUNDARIES)
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.output_dir, args.classification_dir, args.boundaries_dir),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
