"""Sesión 12.1: clasificación offline, reconciliación exacta y productos regionales."""

import argparse
import json
from pathlib import Path

import pandas as pd

from .grants import DEFAULT as SOURCE_GRANTS
from .ingest import digest, save_json
from .municipal_boundaries import DEFAULT as BOUNDARIES
from .regional import load_official_boundaries
from .regional_grants import DEFAULT as HISTORICAL, run as classify

DEFAULT = Path("data/processed/grants/regional/session_12_1_final_02")


def run(output=DEFAULT, boundaries=BOUNDARIES, grants_root=SOURCE_GRANTS):
    output, boundaries, grants_root = map(Path, (output, boundaries, grants_root))
    if output.exists():
        raise FileExistsError("Usar salida nueva")
    boundary_manifest = json.loads((boundaries / "manifest.json").read_text())
    for name, sha in boundary_manifest["outputs"].items():
        if digest(boundaries / name) != sha:
            raise ValueError("Producto territorial alterado")
    municipalities = load_official_boundaries(
        boundaries / "municipality_boundaries.parquet", boundaries / "manifest.json"
    )
    shared = pd.read_parquet(boundaries / "joint_jurisdictions.parquet")
    source_manifest = json.loads((grants_root / "grant_source_manifest.json").read_text())
    original = Path(source_manifest["source_file"])
    if digest(original) != source_manifest["source_sha256"]:
        raise ValueError("Original PRTR alterado")
    document = json.loads(original.read_text())
    if document.get("crs", {}).get("properties", {}).get("name") != "urn:ogc:def:crs:OGC:1.3:CRS84":
        raise ValueError("Revisar ejes CRS de captura original")
    grants = pd.read_parquet(grants_root / "grants.parquet")
    # Verificar geometrías procesadas frente al original, sin regenerar la captura.
    for g in grants.itertuples():
        feature = document["features"][g.source_row - 1]
        xy = (feature.get("geometry") or {}).get("coordinates")
        if feature["properties"]["expediente"] != g.expediente_id or (
            g.geometry_valid and xy != [g.longitude, g.latitude]
        ):
            raise ValueError("Geometría/identidad procesada difiere del original")
    if len(grants) != 7532 or int(grants.importe_centimos.sum()) != 31552733899:
        raise ValueError("Captura de referencia incompatible")
    manifest = classify(
        output,
        grants_root=grants_root,
        municipalities=municipalities,
        excluded=shared,
        boundary_paths=[
            boundaries / "manifest.json",
            boundaries / "municipality_boundaries.parquet",
            boundaries / "joint_jurisdictions.parquet",
        ],
    )
    decisions = pd.read_parquet(output / "grant_municipality_links.parquet")
    old_path = HISTORICAL / "grant_municipality_links.parquet"
    historical = pd.read_parquet(old_path)[["expediente_id", "municipality_code"]].rename(
        columns={"municipality_code": "session12_municipality_code"}
    )
    comparison = decisions.merge(historical, on="expediente_id", validate="one_to_one")
    comparison["changed"] = comparison.municipality_code.fillna("").ne(
        comparison.session12_municipality_code.fillna("")
    )
    facts = grants[["expediente_id", "programa", "importe_centimos", "district_code"]].merge(
        decisions, on="expediente_id", validate="one_to_one"
    )
    summary = pd.read_parquet(output / "municipality_program_summary.parquet")
    expected = (
        grants.groupby("programa")
        .agg(expedientes=("expediente_id", "size"), importe_centimos=("importe_centimos", "sum"))
        .sort_index()
    )
    actual = summary.groupby("programa")[["expedientes", "importe_centimos"]].sum().sort_index()
    pd.testing.assert_frame_equal(expected, actual)
    links = pd.read_parquet(output / "grant_parcel_links.parquet")
    if "importe_centimos" in links:
        raise ValueError("Importe presente en relación multiparcela")
    confirmed_ids = set(
        links.loc[
            links.match_status.isin(["confirmed", "confirmed_historical_madrid"]), "expediente_id"
        ]
    )
    facts["cp_linked"] = facts.expediente_id.isin(confirmed_ids)
    counts = (
        facts.groupby("municipality_code", dropna=False)
        .agg(
            expedientes=("expediente_id", "size"),
            importe_centimos=("importe_centimos", "sum"),
            cp_linked=("cp_linked", "sum"),
        )
        .reset_index()
    )
    counts["cp_linked_percent"] = 100 * counts.cp_linked / counts.expedientes
    products = municipalities.drop(columns="geometry_wkt").merge(
        counts, on="municipality_code", how="left", validate="one_to_one"
    )
    for col in ["expedientes", "importe_centimos", "cp_linked"]:
        products[col] = products[col].fillna(0).astype("int64")
    products["cp_linked_percent"] = products.cp_linked_percent.fillna(0)
    products["prtr_coverage"] = "capture_spatially_assessed_not_exhaustive"
    products["cp_available"] = products.municipality_code.eq("28079")
    products["bu_available"] = products.cp_available
    products["ceee_coverage"] = products.municipality_code.map(
        lambda c: "historical_madrid" if c == "28079" else "not_integrated"
    )
    for program in ["P1", "P3", "P4", "P5"]:
        group = summary[summary.programa.eq(program)].set_index("municipality_code")
        for field in ["expedientes", "importe_centimos"]:
            products[program + "_" + field] = (
                products.municipality_code.map(group[field]).fillna(0).astype("int64")
            )
    quality_counts = pd.crosstab(facts.municipality_code, facts.evidence_level)
    for level in ["A", "B", "C"]:
        products["evidence_" + level] = (
            products.municipality_code.map(quality_counts[level] if level in quality_counts else {})
            .fillna(0)
            .astype("int64")
        )
    conflicts = facts[facts.evidence_level.eq("C")].copy()
    conflicts = conflicts.merge(
        grants[["expediente_id", "direccion", "referencia_catastral", "longitude", "latitude"]],
        on="expediente_id",
        validate="one_to_one",
    )
    changes = comparison[comparison.changed]
    historical_changes = changes[changes.session12_municipality_code.notna()]
    masks = {
        "madrid": facts.municipality_code.eq("28079"),
        "external": facts.municipality_code.notna() & facts.municipality_code.ne("28079"),
        "unassigned": facts.municipality_code.isna(),
    }
    audit = dict(
        total=len(facts),
        amount_cents=int(facts.importe_centimos.sum()),
        municipalities=179,
        validated_municipalities=179,
        ambiguous=int(facts.evidence_level.eq("C").sum()),
        statuses=facts.territorial_status.value_counts().to_dict(),
        evidence=facts.evidence_level.value_counts().to_dict(),
        historical_madrid=3805,
        historical_changes=len(historical_changes),
        new_assignments=int(
            (
                comparison.changed
                & comparison.session12_municipality_code.isna()
                & comparison.municipality_code.notna()
            ).sum()
        ),
        external_municipalities=int(facts.loc[masks["external"], "municipality_code"].nunique()),
        cp_bu_integrated_municipalities=1,
        programs=expected.reset_index().to_dict("records"),
        source_crs="OGC:CRS84 longitude/latitude",
        target_crs="EPSG:25830 always_xy=True",
        border_tolerance_m=1,
        redistribution="unverified_local_only",
        pending=[
            "License of boundaries and PRTR redistribution unverified",
            "Independent regional completeness comparison unavailable",
            "Cadastre identity crosswalk not authorized by name comparison",
            "External CP/BU and CEEE not integrated",
            "Browser visual acceptance pending",
        ],
    )
    for key, mask in masks.items():
        audit[key + "_grants"] = int(mask.sum())
        audit[key + "_amount_cents"] = int(facts.loc[mask, "importe_centimos"].sum())
    if (
        sum(audit[k + "_grants"] for k in masks) != 7532
        or sum(audit[k + "_amount_cents"] for k in masks) != 31552733899
    ):
        raise ValueError("Reconciliación contable fallida")
    tables = {
        "municipal_products": products,
        "territorial_conflicts": conflicts,
        "session12_comparison": comparison,
        "historical_changes": historical_changes,
    }
    for name, frame in tables.items():
        frame.to_parquet(output / (name + ".parquet"), index=False)
    save_json(output / "quality.json", audit)
    manifest.update(
        version="regional-grants-v12.1",
        inputs=manifest["inputs"]
        | {str(original): digest(original), str(old_path): digest(old_path)},
        outputs={
            p.name: digest(p) for p in output.iterdir() if p.is_file() and p.name != "manifest.json"
        },
        quality=audit,
    )
    save_json(output / "manifest.json", manifest)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--boundaries-dir", type=Path, default=BOUNDARIES)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir, args.boundaries_dir), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
