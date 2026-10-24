"""Decisión territorial auditable y matching municipal PRTR sin reparto de importes."""

import argparse
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from numbers import Real

import pandas as pd
import shapely as sh
from pyproj import Transformer

from .grants import DEFAULT as GRANTS
from .ingest import digest, save_json
from .normalize import text_key
from .regional import load_official_boundaries

DEFAULT = Path("data/processed/grants/regional/session_12_final_01")


def territorial_links(grants, previous_links, municipalities=None, border_m=1, excluded=None):
    """Espacial y catastral son evidencias distintas; conflictos no revocan CP histórico."""
    if border_m < 0:
        raise ValueError("Tolerancia negativa")
    shapes = (
        sh.from_wkt(municipalities.geometry_wkt.to_numpy()) if municipalities is not None else []
    )
    tree = sh.STRtree(shapes)
    excluded_shapes = sh.from_wkt(excluded.geometry_wkt.to_numpy()) if excluded is not None else []
    excluded_tree = sh.STRtree(excluded_shapes)
    transform = Transformer.from_crs(4326, 25830, always_xy=True)
    cp_ids = set(previous_links.loc[previous_links.match_status.eq("confirmed"), "expediente_id"])
    rows = []
    for g in grants.itertuples():
        prior = "28079" if g.expediente_id in cp_ids else None
        code, candidates, distance, conflict = None, [], None, False
        address_evidence = "unavailable"
        declared_code = None
        status = "boundaries_unavailable"
        if municipalities is not None:
            if (
                not g.geometry_valid
                or not all(
                    isinstance(v, Real) and math.isfinite(v) for v in [g.longitude, g.latitude]
                )
                or not (-180 <= g.longitude <= 180 and -90 <= g.latitude <= 90)
                or (g.longitude == 0 and g.latitude == 0)
            ):
                status = "invalid_or_missing_geometry"
            else:
                point = sh.Point(*transform.transform(g.longitude, g.latitude))
                hits = tree.query(point, predicate="intersects")
                candidates = municipalities.iloc[hits].municipality_code.tolist()
                nearby = (
                    tree.query(point.buffer(border_m), predicate="intersects") if border_m else hits
                )
                if len(hits) > 1:
                    status = "borderline"
                elif len(hits) == 0:
                    status = "borderline" if len(nearby) else "outside_region"
                else:
                    code = candidates[0]
                    distance = float(point.distance(shapes[hits[0]].boundary))
                    status = "borderline" if distance <= border_m else "spatial_unambiguous"
                    literal = text_key(getattr(g, "direccion", "") or "")
                    # Solo una declaración municipal explícita permite afirmar contradicción textual.
                    declared = [
                        (len(text_key(r.name)), r.municipality_code)
                        for r in municipalities.itertuples()
                        if literal == text_key(r.name) + " (MADRID)"
                        or literal.endswith(" " + text_key(r.name) + " (MADRID)")
                    ]
                    # «Las Rozas de Madrid» también termina en «Madrid»: priorizar
                    # el nombre completo reconocido evita una falsa concordancia.
                    declared_code = max(declared)[1] if declared else None
                    address_evidence = (
                        "agrees"
                        if declared_code == code
                        else "contradicts"
                        if declared_code is not None
                        else "unrecognized"
                    )
                    conflict = (
                        prior is not None and prior != code
                    ) or address_evidence == "contradicts"
                    if conflict:
                        status = "contradictory"
                if len(
                    excluded_tree.query(
                        point.buffer(border_m) if border_m else point, predicate="intersects"
                    )
                ):
                    code = None
                    status = "shared_jurisdiction"
                if getattr(g, "identity_conflict", False):
                    status = "contradictory"
        assigned = (
            code
            if status == "spatial_unambiguous"
            else prior
            if status == "boundaries_unavailable"
            else None
        )
        rows.append(
            dict(
                expediente_id=g.expediente_id,
                municipality_code=assigned,
                spatial_municipality_code=code,
                spatial_candidates=json.dumps(candidates),
                territorial_status=status,
                address_evidence=address_evidence,
                declared_municipality_code=declared_code,
                cp_confirmed_municipality_code=prior,
                cp_spatial_conflict=bool(conflict and prior),
                boundary_distance_m=distance,
                evidence_level=(
                    "historical_cp_only"
                    if status == "boundaries_unavailable" and assigned
                    else "B"
                    if assigned and (address_evidence == "agrees" or prior == assigned)
                    else "A"
                    if assigned
                    else "C"
                    if status in {"contradictory", "borderline", "shared_jurisdiction"}
                    else "unassigned"
                ),
                historical_municipality_code=getattr(g, "municipality_code", prior),
                historical_territorial_quality=getattr(g, "territorial_quality", None),
                assignment_method=(
                    "official_polygon_point_and_documentary_agreement"
                    if assigned and address_evidence == "agrees"
                    else "official_polygon_point_and_historical_cp"
                    if assigned and status == "spatial_unambiguous" and prior == assigned
                    else "official_polygon_point"
                    if assigned and status == "spatial_unambiguous"
                    else "historical_cp_without_boundaries"
                    if assigned
                    else "not_assigned"
                ),
            )
        )
    return pd.DataFrame(rows)


def regional_matches(
    grants, references, territory, partitions, previous_links, madrid_cp_path=None
):
    """No CP y referencia ausente son estados diferentes; importes nunca en relaciones."""
    from .regional_cadastre import verify_partition

    by_id = grants.set_index("expediente_id")
    territory = territory.set_index("expediente_id")
    historical = previous_links.set_index(["expediente_id", "parcel_ref14"])
    transform = Transformer.from_crs(4326, 25830, always_xy=True)
    rows = []
    # Solo se carga una partición municipal por iteración.
    scoped = references.merge(
        territory[["municipality_code"]],
        left_on="expediente_id",
        right_index=True,
        validate="many_to_one",
    )
    for code, group in scoped.groupby("municipality_code", dropna=False):
        cp = None
        if code == "28079" and madrid_cp_path is not None:
            cp = pd.read_parquet(madrid_cp_path, columns=["parcel_ref14", "geometry_wkt"])
        elif pd.notna(code) and code in partitions:
            partition_manifest = verify_partition(partitions[code])
            if partition_manifest["config"]["municipality_code"] != code:
                raise ValueError("Partición catastral de otro municipio")
            cp = pd.read_parquet(
                Path(partitions[code]) / "cp.parquet", columns=["parcel_ref14", "geometry_wkt"]
            )
        for r in group.itertuples():
            key = (r.expediente_id, r.parcel_ref14)
            distance, quality = None, "no_cp_coverage"
            confirmed_code = None
            if key in historical.index and historical.loc[key].match_status == "confirmed":
                quality, confirmed_code = "confirmed_historical_madrid", "28079"
                distance = float(historical.loc[key].distance_m)
            elif key in historical.index and historical.loc[key].match_status == "ambiguous_cp":
                quality = "ambiguous_historical_madrid"
            elif cp is not None:
                candidates = cp[cp.parcel_ref14.eq(r.parcel_ref14)]
                quality = (
                    "not_found"
                    if candidates.empty
                    else "ambiguous"
                    if len(candidates) > 1
                    else "candidate"
                )
                if len(candidates) == 1:
                    g = by_id.loc[r.expediente_id]
                    if g.geometry_valid and not g.identity_conflict:
                        point = sh.Point(*transform.transform(g.longitude, g.latitude))
                        distance = float(
                            point.distance(sh.from_wkt(candidates.geometry_wkt.iloc[0]))
                        )
                        quality = "confirmed" if distance <= 100 else "contradictory"
                        confirmed_code = code if quality == "confirmed" else None
            conflict = territory.loc[r.expediente_id].territorial_status == "contradictory"
            rows.append(
                dict(
                    expediente_id=r.expediente_id,
                    parcel_ref14=r.parcel_ref14,
                    municipality_code=confirmed_code,
                    match_status=quality,
                    distance_m=distance,
                    territorial_conflict=conflict,
                )
            )
        del cp
    return pd.DataFrame(rows)


def run(
    output=DEFAULT,
    grants_root=GRANTS,
    municipalities=None,
    partitions=None,
    boundary_paths=None,
    excluded=None,
):
    output, grants_root = Path(output), Path(grants_root)
    if output.exists():
        raise FileExistsError("Usar salida nueva")
    if municipalities is not None and not boundary_paths:
        raise ValueError("Registrar límites y manifiesto oficiales en la procedencia")
    start = time.perf_counter()
    meta = json.loads((grants_root / "grant_source_manifest.json").read_text())
    for name in ["grants.parquet", "grant_parcel_links.parquet"]:
        if digest(grants_root / name) != meta["outputs"][name]:
            raise ValueError("Captura PRTR alterada")
    grants = pd.read_parquet(grants_root / "grants.parquet")
    previous = pd.read_parquet(grants_root / "grant_parcel_links.parquet")
    if not grants.expediente_id.is_unique:
        raise ValueError("Identidades PRTR duplicadas")
    territory = territorial_links(grants, previous, municipalities, excluded=excluded)
    madrid_cp_path = (
        Path("data/processed/session_2/parcels_audited.parquet")
        if municipalities is not None
        else None
    )
    if madrid_cp_path is not None and digest(madrid_cp_path) != meta["cp_sha256"]:
        raise ValueError("CP histórico Madrid incompatible con la captura PRTR")
    links = regional_matches(
        grants,
        previous[["expediente_id", "parcel_ref14"]],
        territory,
        partitions or {},
        previous,
        madrid_cp_path,
    )
    facts = grants[["expediente_id", "programa", "importe_centimos"]].merge(
        territory, on="expediente_id", validate="one_to_one"
    )
    summary = (
        facts.groupby(["municipality_code", "programa"], dropna=False)
        .agg(expedientes=("expediente_id", "size"), importe_centimos=("importe_centimos", "sum"))
        .reset_index()
    )
    if int(summary.importe_centimos.sum()) != int(grants.importe_centimos.sum()) or int(
        summary.expedientes.sum()
    ) != len(grants):
        raise ValueError("Reconciliación territorial fallida")
    output.mkdir(parents=True)
    tables = {
        "grant_municipality_links": territory,
        "grant_parcel_links": links,
        "municipality_program_summary": summary,
        "grant_match_summary": links.groupby("expediente_id")
        .agg(
            parcel_relations=("parcel_ref14", "size"),
            confirmed_relations=(
                "match_status",
                lambda s: int(s.isin(["confirmed", "confirmed_historical_madrid"]).sum()),
            ),
            ambiguous_relations=(
                "match_status",
                lambda s: int(s.isin(["ambiguous", "ambiguous_historical_madrid"]).sum()),
            ),
            without_cp_coverage=("match_status", lambda s: int(s.eq("no_cp_coverage").sum())),
        )
        .reset_index(),
    }
    for name, frame in tables.items():
        frame.to_parquet(output / f"{name}.parquet", index=False)
    manifest = dict(
        version="regional-grants-v1",
        source_manifest_sha256=digest(grants_root / "grant_source_manifest.json"),
        inputs={
            str(grants_root / n): digest(grants_root / n)
            for n in ["grants.parquet", "grant_parcel_links.parquet"]
        }
        | {str(p): digest(p) for p in (boundary_paths or [])}
        | ({str(madrid_cp_path): digest(madrid_cp_path)} if madrid_cp_path is not None else {})
        | {
            str(Path(p) / "manifest.json"): digest(Path(p) / "manifest.json")
            for p in (partitions or {}).values()
        },
        outputs={p.name: digest(p) for p in output.glob("*.parquet")},
        grants=len(grants),
        amount_cents=int(grants.importe_centimos.sum()),
        boundaries_available=municipalities is not None,
        boundary_identity_sha256=hashlib.sha256(
            municipalities[["municipality_code", "geometry_wkt"]].to_json().encode()
        ).hexdigest()
        if municipalities is not None
        else None,
        created_at=datetime.now(timezone.utc).isoformat(),
        territorial_status=territory.territorial_status.value_counts().to_dict(),
        matching=links.match_status.value_counts().to_dict(),
        assigned=int(territory.municipality_code.notna().sum()),
        seconds=time.perf_counter() - start,
    )
    save_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--boundaries", type=Path)
    parser.add_argument("--boundaries-manifest", type=Path)
    parser.add_argument("--cadastre-dir", type=Path)
    args = parser.parse_args()
    municipalities = (
        load_official_boundaries(args.boundaries, args.boundaries_manifest)
        if args.boundaries and args.boundaries_manifest
        else None
    )
    if bool(args.boundaries) != bool(args.boundaries_manifest):
        parser.error("Límite y manifiesto son inseparables")
    partitions = (
        {p.parent.name: p.parent for p in args.cadastre_dir.glob("*/manifest.json")}
        if args.cadastre_dir
        else {}
    )
    print(
        json.dumps(
            run(
                args.output_dir,
                municipalities=municipalities,
                partitions=partitions,
                boundary_paths=[args.boundaries, args.boundaries_manifest]
                if municipalities is not None
                else None,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
