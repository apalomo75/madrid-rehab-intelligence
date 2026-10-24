"""Catastro municipal particionado; inventario ATOM y checkpoints verificables."""

import argparse
import hashlib
import json
import re
import resource
import tempfile
import time
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import shapely as sh

from .ingest import ATOM, Archive, cadastral_rows, digest, save_json

VERSION = "regional-cadastre-v1"
DEFAULT = Path("data/processed/territory/session_12_final_01")


def atom_resources(path):
    """Los códigos y nombres son catastrales, nunca se convierten implícitamente a INE."""
    path = Path(path)
    meta = json.loads(path.with_suffix(path.suffix + ".json").read_text())
    if digest(path) != meta["sha256"]:
        raise ValueError("Feed alterado")
    root = ET.parse(path).getroot()
    rows = []
    for entry in root.findall(f"{{{ATOM}}}entry"):
        title = (entry.findtext(f"{{{ATOM}}}title") or "").strip()
        match = re.fullmatch(r"(28\d{3})-(.+) (?:Cadastral Parcels|buildings)", title)
        links = [
            e.get("href") for e in entry.findall(f"{{{ATOM}}}link") if e.get("rel") == "enclosure"
        ]
        if not match or len(links) != 1:
            raise ValueError("Entrada ATOM municipal inesperada")
        rows.append(
            dict(
                cadastre_code=match[1],
                cadastre_name=match[2],
                url=links[0],
                source_date=entry.findtext(f"{{{ATOM}}}updated"),
                rights=entry.findtext(f"{{{ATOM}}}rights") or root.findtext(f"{{{ATOM}}}rights"),
                source_url=meta["url"],
                feed_sha256=meta["sha256"],
            )
        )
    frame = pd.DataFrame(rows)
    if frame.empty or not frame.cadastre_code.is_unique:
        raise ValueError("Inventario vacío o códigos duplicados")
    return frame


def inventory(raw=Path("data/raw/session_1")):
    cp = atom_resources(raw / "parcelas_atom.xml")
    bu = atom_resources(raw / "edificios_atom.xml")
    if set(cp.cadastre_code) != set(bu.cadastre_code):
        raise ValueError("Inventarios CP/BU no reconciliados")
    if not cp.set_index("cadastre_code").cadastre_name.equals(
        bu.set_index("cadastre_code").cadastre_name
    ):
        raise ValueError("Nombres CP/BU contradictorios")
    return cp.merge(
        bu, on=["cadastre_code", "cadastre_name"], suffixes=("_cp", "_bu"), validate="one_to_one"
    )


def validate_crosswalk(frame, resources):
    required = {"municipality_code", "cadastre_code", "name", "evidence_url"}
    if not required <= set(frame):
        raise ValueError("Correspondencia INE/Catastro requiere códigos y evidencia revisada")
    if frame[list(required)].isna().any().any() or any(
        frame[c].astype(str).str.strip().eq("").any() for c in required
    ):
        raise ValueError("Correspondencia incompleta")
    for col in ["municipality_code", "cadastre_code"]:
        if not frame[col].is_unique or not frame[col].str.fullmatch(r"28\d{3}").all():
            raise ValueError("Código duplicado o incompatible")
    if not set(frame.cadastre_code) <= set(resources.cadastre_code):
        raise ValueError("Código ausente del feed")
    return frame


def fetch_retry(archive, url, name, attempts=2):
    url = urllib.parse.quote(url, safe=":/?=&%")
    if not 1 <= attempts <= 3:
        raise ValueError("Máximo tres intentos")
    if isinstance(archive, Archive):
        path = archive.root / name
        if path.exists() and not path.with_suffix(path.suffix + ".json").exists():
            raise ValueError("Original sin metadatos: conservar y usar otro directorio de captura")
    for attempt in range(attempts):
        try:
            return archive.fetch(url, name)
        except urllib.error.HTTPError as exc:
            if exc.code not in {408, 429, 500, 502, 503, 504} or attempt + 1 == attempts:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
        time.sleep(1)


def validate_objects(frame, kind, boundary=None):
    key = "parcel_id" if kind == "cp" else "building_id"
    if frame.empty or key not in frame or frame[key].isna().any() or not frame[key].is_unique:
        raise ValueError("Colección vacía o identificadores ausentes/duplicados")
    if not frame.geometry_crs.eq("EPSG:25830").all():
        raise ValueError("CRS no soportado")
    shapes = sh.from_wkt(frame.geometry_wkt.to_numpy(), on_invalid="ignore")
    valid = sh.is_valid(shapes) & ~sh.is_empty(shapes) & (sh.area(shapes) > 0)
    if not valid.all():
        raise ValueError("Geometrías inválidas o vacías")
    box = sh.bounds(shapes)
    if not (
        (box[:, 0] > 300000) & (box[:, 2] < 520000) & (box[:, 1] > 4400000) & (box[:, 3] < 4600000)
    ).all():
        raise ValueError("Geometrías fuera del sobre regional; no acredita municipio")
    frame = frame.copy()
    frame["geometry_valid"] = valid
    frame["usable_geometry"] = valid
    for idx, name in enumerate(["minx", "miny", "maxx", "maxy"]):
        frame[name] = box[:, idx]
    if boundary is not None:
        frame["municipal_overlap_ratio"] = sh.area(sh.intersection(shapes, boundary)) / sh.area(
            shapes
        )
        if frame.municipal_overlap_ratio.lt(0.95).any():
            raise ValueError("Objetos con menos del 95% de área dentro del municipio: revisar")
    return frame


def cp_bu_relations(cp, bu):
    """Relación por referencia más contraste geométrico; no identifica edificios físicos."""
    records = []
    grouped = cp.groupby("parcel_ref14")
    for row in bu.itertuples():
        count, distance = 0, None
        if row.parcel_ref14 in grouped.groups:
            candidates = grouped.get_group(row.parcel_ref14)
            count = len(candidates)
            distance = float(
                sh.distance(
                    sh.from_wkt(row.geometry_wkt),
                    sh.union_all(sh.from_wkt(candidates.geometry_wkt.to_numpy())),
                )
            )
        records.append(
            dict(
                building_id=row.building_id,
                parcel_ref14=row.parcel_ref14,
                cp_rows=count,
                distance_m=distance,
                relation_quality="confirmed_reference_geometry"
                if count == 1 and distance <= 1
                else "ambiguous_reference"
                if count > 1
                else "contradictory_geometry"
                if count
                else "not_found",
            )
        )
    return pd.DataFrame(records)


def verify_partition(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["version"] != VERSION or manifest["validation_status"] != "validated":
        raise ValueError("Partición no validada")
    for name, sha in manifest["outputs"].items():
        if digest(root / name) != sha:
            raise ValueError("Partición alterada")
    for path, sha in manifest["inputs"].items():
        if digest(path) != sha:
            raise ValueError("Original de partición alterado")
    return manifest


def process_municipality(config, raw_root, output_root, boundary, offline=False, audited=False):
    """Una partición se publica solo tras validar CP, BU y sus relaciones."""
    code = config["municipality_code"]
    if (
        not re.fullmatch(r"28\d{3}", code)
        or not re.fullmatch(r"28\d{3}", config["cadastre_code"])
        or boundary is None
        or not boundary.is_valid
        or boundary.is_empty
        or boundary.geom_type not in {"Polygon", "MultiPolygon"}
    ):
        raise ValueError("Requiere código INE y límite municipal validado")
    target = Path(output_root) / code
    if target.exists():
        old = verify_partition(target)
        if (
            old["config"] != config
            or old["boundary_sha256"] != hashlib.sha256(boundary.wkb).hexdigest()
            or old.get("ingestion_mode", "strict") != ("audited" if audited else "strict")
        ):
            raise ValueError("Checkpoint corresponde a otra configuración/límite")
        return old
    started = time.perf_counter()
    archive = Archive(Path(raw_root) / config["cadastre_code"], offline=offline)
    inputs, frames, issues = {}, {}, {}
    for kind, parser in [("cp", "parcelas"), ("bu", "edificios")]:
        path, meta = fetch_retry(archive, config[f"url_{kind}"], f"{kind}.zip")
        inputs[str(path)] = meta["sha256"]
        if audited:
            from .cadastre_download import inspect_zip
            from .pilot_objects import (
                audit_objects,
                building_rows,
                validate_collection_inventory,
                validate_readable_objects,
            )

            validate_collection_inventory(inspect_zip(path, kind))
            rows = (
                building_rows(path)
                if kind == "bu"
                else cadastral_rows(path, parser, strict_count=True)
            )
            parsed = pd.DataFrame(rows)
            validate_readable_objects(parsed, kind)
            frames[kind], issues[kind] = audit_objects(parsed, kind, boundary)
            frames[kind]["source_municipality_code"] = code
            frames[kind]["municipality_code"] = frames[kind].usable_geometry.map(
                lambda ok: code if ok else None
            )
        else:
            frames[kind] = validate_objects(
                pd.DataFrame(cadastral_rows(path, parser, strict_count=True)), kind, boundary
            )
            frames[kind]["municipality_code"] = code
    if audited:
        from .pilot_objects import audited_cp_bu_relations

        relations = audited_cp_bu_relations(frames["cp"], frames["bu"])
    else:
        relations = cp_bu_relations(frames["cp"], frames["bu"])
    if not audited and not relations.relation_quality.eq("confirmed_reference_geometry").all():
        raise ValueError("Relaciones CP/BU requieren revisión; originales conservados")
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = dict(
        version=VERSION,
        config=config,
        created_at=datetime.now(timezone.utc).isoformat(),
        boundary_sha256=hashlib.sha256(boundary.wkb).hexdigest(),
        validation_status="validated",
        inputs=inputs,
        outputs={},
        cp_rows=len(frames["cp"]),
        cp_references=frames["cp"].parcel_ref14.nunique(),
        bu_objects=len(frames["bu"]),
        seconds=time.perf_counter() - started,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        download_bytes=archive.total,
    )
    if audited:
        manifest.update(
            ingestion_mode="audited",
            cp_usable=int(frames["cp"].usable_geometry.sum()),
            bu_usable=int(frames["bu"].usable_geometry.sum()),
            cp_issues=len(issues["cp"]),
            bu_issues=len(issues["bu"]),
            bu_feature_types=frames["bu"].source_feature_type.value_counts().to_dict(),
            cp_bu_quality=relations.relation_quality.value_counts().to_dict(),
            quality_status="review_required"
            if any(len(f) for f in issues.values())
            or not relations.relation_quality.eq("confirmed_reference_geometry").all()
            else "no_issues_detected",
        )
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=f".{code}-") as temp:
        stage = Path(temp) / "partition"
        stage.mkdir()
        for kind, frame in {
            **frames,
            "cp_bu_links": relations,
            **{k + "_issues": f for k, f in issues.items()},
        }.items():
            if kind in {"cp", "bu"}:
                frame = frame.sort_values(
                    ["parcel_ref14", "parcel_id" if kind == "cp" else "building_id"]
                )
            frame.to_parquet(stage / f"{kind}.parquet", index=False, row_group_size=10000)
        manifest["outputs"] = {p.name: digest(p) for p in stage.glob("*.parquet")}
        save_json(stage / "manifest.json", manifest)
        stage.rename(target)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory-output", type=Path)
    parser.add_argument("--crosswalk", type=Path)
    parser.add_argument("--boundaries", type=Path)
    parser.add_argument("--boundaries-manifest", type=Path)
    parser.add_argument("--municipalities", nargs="+", default=[])
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/cadastre/session_12_01"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/cadastre/session_12_01")
    )
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    resources = inventory()
    if args.inventory_output:
        if args.inventory_output.exists():
            raise FileExistsError("Usar salida nueva")
        args.inventory_output.mkdir(parents=True)
        resources.to_parquet(args.inventory_output / "cadastre_resources.parquet", index=False)
        coverage = resources[["cadastre_code", "cadastre_name"]].copy()
        coverage["municipality_code"] = coverage.cadastre_code.map({"28900": "28079"})
        coverage["ine_identity_status"] = coverage.cadastre_code.map(
            lambda code: "historical_madrid_confirmed"
            if code == "28900"
            else "requires_official_crosswalk"
        )
        coverage["official_boundary"] = False
        coverage["cp_processed"] = coverage.cadastre_code.eq("28900")
        coverage["bu_processed"] = coverage.cadastre_code.eq("28900")
        coverage["ceee_coverage"] = coverage.cadastre_code.map(
            lambda code: "historical_madrid_snapshot" if code == "28900" else "unvalidated"
        )
        coverage["municipal_events"] = coverage.cadastre_code.map(
            lambda code: "madrid_only" if code == "28900" else "not_integrated"
        )
        coverage["prtr_municipal_assignment"] = coverage.cadastre_code.map(
            lambda code: "historical_cp_confirmed_partial"
            if code == "28900"
            else "unavailable_not_zero"
        )
        coverage.to_parquet(args.inventory_output / "coverage.parquet", index=False)
        save_json(
            args.inventory_output / "manifest.json",
            dict(
                version=VERSION,
                created_at=datetime.now(timezone.utc).isoformat(),
                scope="cadastral_resource_inventory_not_INE_catalogue",
                resources=len(resources),
                outputs={p.name: digest(p) for p in args.inventory_output.glob("*.parquet")},
                inputs={str(p): digest(p) for p in Path("data/raw/session_1").glob("*_atom.xml")},
            ),
        )
    if args.municipalities:
        from .regional import load_official_boundaries

        if (
            not args.crosswalk
            or not args.boundaries
            or not args.boundaries_manifest
            or len(args.municipalities) > 5
        ):
            parser.error(
                "Lote máximo 5; requiere crosswalk revisado y límites/manifiesto oficiales"
            )
        crosswalk = validate_crosswalk(pd.read_parquet(args.crosswalk), resources)
        boundaries = load_official_boundaries(args.boundaries, args.boundaries_manifest).set_index(
            "municipality_code"
        )
        configs = crosswalk.merge(resources, on="cadastre_code", validate="one_to_one").set_index(
            "municipality_code"
        )
        checkpoint = []
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for code in args.municipalities:
            try:
                row = configs.loc[code]
                config = {
                    "municipality_code": code,
                    **{
                        k: str(row[k])
                        for k in [
                            "cadastre_code",
                            "name",
                            "evidence_url",
                            "url_cp",
                            "url_bu",
                            "source_date_cp",
                            "source_date_bu",
                        ]
                    },
                }
                result = process_municipality(
                    config,
                    args.raw_dir,
                    args.output_dir,
                    sh.from_wkt(boundaries.loc[code].geometry_wkt),
                    args.offline,
                )
                checkpoint.append(
                    dict(
                        municipality_code=code,
                        status="validated",
                        cp_rows=result["cp_rows"],
                        bu_objects=result["bu_objects"],
                    )
                )
            except (OSError, ValueError, KeyError) as exc:
                checkpoint.append(dict(municipality_code=code, status="blocked", error=str(exc)))
            save_json(args.output_dir / "checkpoint.json", checkpoint)
            if checkpoint[-1]["status"] != "validated":
                break  # No escalar un lote con errores.


if __name__ == "__main__":
    main()
