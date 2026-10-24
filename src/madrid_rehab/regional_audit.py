"""Auditoría reproducible de cobertura regional sin publicar detalle PRTR."""

import argparse
import json
import resource
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from .ingest import digest, save_json
from .regional_cadastre import DEFAULT, inventory
from .regional_grants import DEFAULT as GRANTS


def network_audit():
    resources = inventory().set_index("cadastre_code")
    urls = [
        (
            "INE catalogue",
            "https://www.madrid.org/iestadis/fijas/clasificaciones/descarga/mcmva26.xlsx",
        ),
        (
            "IDEM capabilities",
            "https://idem.comunidad.madrid/geoidem/UnidadesAdministrativas/wfs?REQUEST=GetCapabilities&Service=WFS&VERSION=1.1.0",
        ),
        ("IGN collection", "https://api-features.ign.es/collections/administrativeunit?f=json"),
    ]
    for code in ["28065", "28092", "28007", "28074", "28005"]:
        for kind in ["cp", "bu"]:
            urls.append((f"pilot {code} {kind}", resources.loc[code, f"url_{kind}"]))
    rows = []
    for label, url in urls:
        started = time.perf_counter()
        url = urllib.parse.quote(url, safe=":/?=&%")
        row = dict(label=label, url=url, processed=False)
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, method="HEAD"), timeout=10
            ) as response:
                row.update(status=response.status, headers=dict(response.headers))
        except OSError as exc:
            row.update(status="blocked", error=str(exc))
        row["seconds"] = time.perf_counter() - started
        rows.append(row)
        time.sleep(0.2)
    return rows


def run(output, initial_state, check_network=False):
    output = Path(output)
    if output.exists():
        raise FileExistsError("Usar informe nuevo")
    start = time.perf_counter()
    initial = json.loads(Path(initial_state).read_text())
    changed = [
        p
        for p, sha in initial["protected_files"].items()
        if not Path(p).exists() or digest(p) != sha
    ]
    inventory_manifest = json.loads((DEFAULT / "manifest.json").read_text())
    grants_manifest = json.loads((GRANTS / "manifest.json").read_text())
    for base, manifest in [(DEFAULT, inventory_manifest), (GRANTS, grants_manifest)]:
        for name, sha in manifest["outputs"].items():
            if digest(base / name) != sha:
                raise ValueError("Producto regional alterado")
        for name, sha in manifest["inputs"].items():
            if digest(name) != sha:
                raise ValueError("Entrada regional alterada")
    coverage = pd.read_parquet(DEFAULT / "coverage.parquet")
    territory = pd.read_parquet(GRANTS / "grant_municipality_links.parquet")
    links = pd.read_parquet(GRANTS / "grant_parcel_links.parquet")
    summary = pd.read_parquet(GRANTS / "municipality_program_summary.parquet")
    confirmed = links[links.match_status.isin(["confirmed", "confirmed_historical_madrid"])]
    result = dict(
        version="session-12-audit-v1",
        status="partial_network_blocked",
        initial_changed_paths=initial["changed_paths"],
        protected_files=len(initial["protected_files"]),
        protected_files_changed=changed,
        cadastre_resource_municipalities=len(coverage),
        validated_ine_catalogue_municipalities=int(coverage.municipality_code.notna().sum()),
        official_municipal_boundaries_imported=0,
        municipalities_cp_processed=int(coverage.cp_processed.sum()),
        municipalities_bu_processed=int(coverage.bu_processed.sum()),
        new_cp_rows=0,
        new_bu_objects=0,
        grants=grants_manifest["grants"],
        amount_cents=grants_manifest["amount_cents"],
        assigned=int(territory.municipality_code.notna().sum()),
        unassigned=int(territory.municipality_code.isna().sum()),
        spatial_assignments=int(territory.territorial_status.eq("spatial_unambiguous").sum()),
        contradictions=int(territory.territorial_status.eq("contradictory").sum()),
        contradictions_assessable=False,
        borders_assessable=False,
        confirmed_parcel_relations=len(confirmed),
        confirmed_grants=int(confirmed.expediente_id.nunique()),
        confirmed_parcels=int(confirmed.parcel_ref14.nunique()),
        matching=links.match_status.value_counts().to_dict(),
        amount_reconciled=int(summary.importe_centimos.sum()) == grants_manifest["amount_cents"],
        grant_counts_reconciled=int(summary.expedientes.sum()) == grants_manifest["grants"],
        pilot_status="not_executed_access_blocked",
        scaling_status="stopped_before_pilot",
        prtr_redistribution_license="unverified_local_only",
        memory_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        seconds=time.perf_counter() - start,
    )
    output.mkdir(parents=True)
    save_json(output / "quality.json", result)
    summary.to_csv(output / "municipality_program_summary.csv", index=False)
    if check_network:
        save_json(output / "network_audit.json", network_audit())
    save_json(
        output / "manifest.json",
        dict(
            inputs={
                str(DEFAULT / "manifest.json"): digest(DEFAULT / "manifest.json"),
                str(GRANTS / "manifest.json"): digest(GRANTS / "manifest.json"),
                str(initial_state): digest(initial_state),
            },
            outputs={p.name: digest(p) for p in output.iterdir() if p.is_file()},
        ),
    )
    if changed:
        raise ValueError("Productos anteriores alterados: ver quality.json")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--initial-state", type=Path, default=Path("reports/session_12/initial_state.json")
    )
    parser.add_argument("--check-network", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir, args.initial_state, args.check_network), indent=2))


if __name__ == "__main__":
    main()
