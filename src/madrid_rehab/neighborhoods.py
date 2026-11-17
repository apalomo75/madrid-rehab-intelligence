"""Offline official Madrid neighborhoods, auditable spatial allocation and additive bundle."""

import argparse
from datetime import datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
import resource
import shutil
from time import perf_counter
import urllib.request

import numpy as np
import pandas as pd
from pyproj import Transformer
import shapely as sh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import transform

from .ingest import digest
from .territory import parcel_territories

CATALOG = "https://servpub.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=422fa235-762b-11e9-861d-ecb1d753f6e8"
URL = "https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/LIMITES_ADMINISTRATIVOS/Barrios/TopoJSON/Barrios.json"
SERVICE = (
    "https://sigma.madrid.es/hosted/rest/services/CARTOGRAFIA/LIMITES_ADMINISTRATIVOS/MapServer/25"
)
TERMS = "https://datos.madrid.es/pages/condiciones-generales-ayuntamiento-de-madrid"
DATE = "2026-08-31"
CP = "data/processed/session_2/parcels_audited.parquet"
DEFAULT = Path("data/processed/geography/session_35_01")
RULE = "largest_positive_overlap_m2; ties_within_1e-6_m2_lowest_official_code; require_existing_district_agreement; no_geometry_repair"


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def capture(output):
    """One bounded official capture; save each response before moving to the next."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    meta = {"captured_at": datetime.now(timezone.utc).isoformat(), "files": {}}
    from urllib.parse import urlencode

    query = urlencode(
        {
            "where": "1=1",
            "outFields": "COD_DIS_TX,NOMDIS,COD_BAR,NOMBRE,FCH_ALTA,FCH_BAJA",
            "outSR": "25830",
            "returnGeometry": "true",
            "orderByFields": "COD_BAR",
            "f": "geojson",
        }
    )
    for name, url in (
        ("Barrios.json", URL),
        ("catalogue.html", CATALOG),
        ("layer.json", SERVICE + "?f=json"),
        ("barrios.geojson", SERVICE + "/query?" + query),
    ):
        with urllib.request.urlopen(url, timeout=40) as response:
            if not response.url.startswith("https://"):
                raise ValueError("Insecure redirect")
            data = response.read(20_000_001)
            if len(data) > 20_000_000:
                raise ValueError("Source exceeds capture limit")
            (output / name).write_bytes(data)
            meta["files"][name] = {
                "url": url,
                "sha256": digest(output / name),
                "bytes": len(data),
                "headers": dict(response.headers),
            }
            write_json(output / "capture.json", meta)
    return meta


def decode_topology(payload):
    """Decode polygon arcs, including reverse indices, delta transform and holes."""
    if payload.get("type") != "Topology" or set(payload["objects"]) != {"Barrios"}:
        raise ValueError("Unexpected neighborhood TopoJSON structure")
    scale = payload.get("transform")
    arcs = []
    for raw in payload["arcs"]:
        coords = np.asarray(raw, dtype=float)
        if scale:
            coords = coords.cumsum(axis=0) * scale["scale"] + scale["translate"]
        arcs.append(coords.tolist())

    def ring(indices):
        points = []
        for index in indices:
            arc = arcs[index] if index >= 0 else arcs[~index][::-1]
            if points and points[-1] != arc[0]:
                raise ValueError("Disconnected TopoJSON arcs")
            points.extend(arc if not points else arc[1:])
        if len(points) < 4 or points[0] != points[-1]:
            raise ValueError("Unclosed TopoJSON ring")
        return points

    def polygon(rings):
        return Polygon(ring(rings[0]), [ring(r) for r in rings[1:]])

    transformer = Transformer.from_crs(4326, 25830, always_xy=True)
    rows = []
    for item in payload["objects"]["Barrios"]["geometries"]:
        props = item["properties"]
        if item["type"] == "Polygon":
            geometry = polygon(item["arcs"])
        elif item["type"] == "MultiPolygon":
            geometry = MultiPolygon([polygon(p) for p in item["arcs"]])
        else:
            raise ValueError("Unexpected geometry type")
        # The actual TopoJSON has WGS84 longitude/latitude, unlike the catalogue's SHP CRS.
        minx, miny, maxx, maxy = geometry.bounds
        if not (-4.1 < minx <= maxx < -3.2 and 40 < miny <= maxy < 41):
            raise ValueError("Unexpected source CRS or Madrid envelope")
        geometry = transform(transformer.transform, geometry)
        if not geometry.is_valid or geometry.is_empty:
            raise ValueError("Invalid official polygon; no silent repair")
        code, district = str(props["COD_BAR"]), str(props["CODDIS"]).zfill(2)
        if props["COD_DIS_TX"] != district or props["COD_DISBAR"] != code:
            raise ValueError("Contradictory official codes")
        rows.append(
            {
                "municipality_code": "28079",
                "district_code": district,
                "district_name": props["NOMDIS"],
                "neighborhood_code": code,
                "neighborhood_name": props["NOMBRE"],
                "geometry_wkt": geometry.wkt,
                "geometry_crs": "EPSG:25830",
            }
        )
    frame = pd.DataFrame(rows).sort_values("neighborhood_code").reset_index(drop=True)
    return validate_neighborhoods(frame)


def validate_neighborhoods(frame):
    if (
        len(frame) != 131
        or not frame.neighborhood_code.is_unique
        or set(frame.district_code) != {f"{i:02}" for i in range(1, 22)}
        or frame.groupby("district_code").district_name.nunique().ne(1).any()
        or not frame.neighborhood_code.str[:-1].str.zfill(2).eq(frame.district_code).all()
    ):
        raise ValueError("Expected 131 unique official neighborhoods in 21 districts")
    geoms = sh.from_wkt(frame.geometry_wkt.to_numpy())
    for i, geom in enumerate(geoms):
        if any(geom.intersection(other).area > 0.01 for other in geoms[i + 1 :]):
            raise ValueError("Overlapping official neighborhoods")
    return frame


def assign(parcels, neighborhoods):
    """One result per original reference. Preserve ambiguous rows separately for audit."""
    if parcels.parcel_ref14.isna().any():
        raise ValueError("Empty cadastral identity")
    geography = parcel_territories(parcels)
    geoms = sh.from_wkt(neighborhoods.geometry_wkt.to_numpy())
    tree = sh.STRtree(geoms)
    results, issues = [], []
    grouped = parcels.groupby("parcel_ref14", sort=True)
    for row in geography.itertuples(index=False):
        source = grouped.get_group(row.parcel_ref14)
        result = {
            "municipality_code": "28079",
            "parcel_ref14": row.parcel_ref14,
            "district_code": row.district_code,
            "neighborhood_code": None,
            "status": "unassigned",
            "overlap_count": 0,
            "winner_share": None,
        }
        reason = None
        if len(source) != 1:
            reason = "duplicate_parcel_reference"
        elif row.district_assignment != "assigned":
            reason = "district_unassigned"
        elif not source.iloc[0].usable_geometry or source.iloc[0].geometry_crs != "EPSG:25830":
            reason = "unusable_geometry_or_crs"
        else:
            geom = sh.from_wkt(source.iloc[0].geometry_wkt, on_invalid="ignore")
            if geom is None or geom.is_empty or not geom.is_valid or geom.area <= 0:
                reason = "invalid_parcel_geometry"
            else:
                candidates = []
                for index in tree.query(geom, predicate="intersects"):
                    area = geom.intersection(geoms[index]).area
                    if area > 0:
                        n = neighborhoods.iloc[index]
                        candidates.append((area, n.neighborhood_code, n.district_code))
                result["overlap_count"] = len(candidates)
                if not candidates:
                    reason = "no_positive_overlap"
                else:
                    maximum = max(a for a, _, _ in candidates)
                    ties = sorted((c, d) for a, c, d in candidates if maximum - a <= 1e-6)
                    code, district = ties[0]
                    result["winner_share"] = maximum / geom.area
                    if district != row.district_code:
                        reason = "district_conflict"
                    else:
                        result.update(neighborhood_code=code, status="assigned")
                    if len(candidates) > 1 or reason:
                        issues.append(
                            {
                                "parcel_ref14": row.parcel_ref14,
                                "reason": reason
                                or (
                                    "area_tie" if len(ties) > 1 else "crosses_neighborhood_boundary"
                                ),
                                "selected_code": result["neighborhood_code"],
                                "existing_district": row.district_code,
                                "candidates_json": json.dumps(
                                    sorted(candidates), ensure_ascii=False
                                ),
                                "parcel_area_m2": geom.area,
                            }
                        )
        if reason:
            result["status"] = reason
            if reason != "district_conflict":
                issues.append(
                    {
                        "parcel_ref14": row.parcel_ref14,
                        "reason": reason,
                        "selected_code": None,
                        "existing_district": row.district_code,
                        "candidates_json": "[]",
                        "parcel_area_m2": None,
                    }
                )
        results.append(result)
    assignments = pd.DataFrame(results)
    assert assignments.parcel_ref14.is_unique
    return assignments, pd.DataFrame(
        issues,
        columns=[
            "parcel_ref14",
            "reason",
            "selected_code",
            "existing_district",
            "candidates_json",
            "parcel_area_m2",
        ],
    )


def load_official(raw, capture_meta):
    """Prefer supplied TopoJSON; use the catalogue-linked official service if invalid."""
    for name in ("Barrios.json", "catalogue.html"):
        if digest(raw / name) != capture_meta["files"][name]["sha256"]:
            raise ValueError("Neighborhood source integrity failure")
    payload = json.loads((raw / "Barrios.json").read_bytes())
    try:
        return decode_topology(payload), {"selected": "Barrios.json", "fallback": False}
    except ValueError as exc:
        failure = str(exc)
    # No repair or third-party boundary replacement. Exact official service response required.
    for name in ("layer.json", "barrios.geojson"):
        if digest(raw / name) != capture_meta["files"][name]["sha256"]:
            raise ValueError("Official fallback integrity failure")
    data = json.loads((raw / "barrios.geojson").read_bytes())
    layer = json.loads((raw / "layer.json").read_bytes())
    if (
        layer["extent"]["spatialReference"]["wkid"] != 25830
        or data.get("crs", {}).get("properties", {}).get("name") != "EPSG:25830"
        or data.get("exceededTransferLimit")
        or data.get("type") != "FeatureCollection"
    ):
        raise ValueError("Unexpected official response CRS or coverage")
    rows = []
    for feature in data["features"]:
        props = feature["properties"]
        geom = sh.geometry.shape(feature["geometry"])
        if geom.geom_type not in {"Polygon", "MultiPolygon"} or not geom.is_valid or geom.is_empty:
            raise ValueError("Invalid service geometry")
        rows.append(
            {
                "municipality_code": "28079",
                "district_code": props["COD_DIS_TX"],
                "district_name": props["NOMDIS"],
                "neighborhood_code": props["COD_BAR"],
                "neighborhood_name": props["NOMBRE"],
                "geometry_wkt": geom.wkt,
                "geometry_crs": "EPSG:25830",
            }
        )
    frame = validate_neighborhoods(
        pd.DataFrame(rows).sort_values("neighborhood_code").reset_index(drop=True)
    )
    topo_ids = {
        (g["properties"]["COD_BAR"], g["properties"]["COD_DIS_TX"], g["properties"]["NOMBRE"])
        for g in payload["objects"]["Barrios"]["geometries"]
    }
    if topo_ids != set(
        frame[["neighborhood_code", "district_code", "neighborhood_name"]].itertuples(
            index=False, name=None
        )
    ):
        raise ValueError("TopoJSON and official service neighborhood catalogue differ")
    return frame, {
        "selected": "barrios.geojson",
        "fallback": True,
        "rejected_topojson_reason": failure,
        "topojson_sha256": digest(raw / "Barrios.json"),
        "catalogues_identical": True,
        "geometry_repairs": 0,
    }


def build(raw, base, output):
    """Offline reproducible normalized geography, retaining all CP and allocation issues."""
    raw, base, output = map(Path, (raw, base, output))
    if output.exists():
        raise FileExistsError("New geography output required")
    start = perf_counter()
    meta = json.loads((base / "manifest.json").read_text())
    for name in (CP, "data/processed/session_7_final/districts.parquet"):
        if digest(base / name) != meta["files"][name]["sha256"]:
            raise ValueError("Base geography integrity failure")
    capture_meta = json.loads((raw / "capture.json").read_text())
    neighborhoods, source_audit = load_official(raw, capture_meta)
    districts = pd.read_parquet(base / "data/processed/session_7_final/districts.parquet")
    official = (
        neighborhoods[["district_code", "district_name"]]
        .drop_duplicates()
        .sort_values("district_code")
    )
    expected = districts[["district_code", "district_name"]].sort_values("district_code")
    if (
        official.set_index("district_code").district_name.to_dict()
        != expected.set_index("district_code").district_name.to_dict()
    ):
        raise ValueError("District catalogue differs from active bundle")
    parcels = pd.read_parquet(
        base / CP,
        columns=[
            "parcel_ref14",
            "district_code",
            "usable_geometry",
            "geometry_wkt",
            "geometry_crs",
        ],
    )
    assignments, issues = assign(parcels, neighborhoods)
    output.mkdir(parents=True)
    tables = {
        "neighborhoods.parquet": neighborhoods.drop(columns=["geometry_wkt", "geometry_crs"]),
        "boundaries.parquet": neighborhoods,
        "assignments.parquet": assignments,
        "issues.parquet": issues,
    }
    files = {}
    for name, table in tables.items():
        table.to_parquet(output / name, index=False, compression="zstd")
        files[name] = {
            "sha256": digest(output / name),
            "bytes": (output / name).stat().st_size,
            "rows": len(table),
        }
    summary = {
        "source_rows": len(parcels),
        "unique_parcels": len(assignments),
        "assigned": int(assignments.status.eq("assigned").sum()),
        "unassigned": int(assignments.status.ne("assigned").sum()),
        "statuses": assignments.status.value_counts().to_dict(),
        "crossing_or_issue_rows": len(issues),
        "neighborhoods": 131,
        "districts": 21,
        "seconds": perf_counter() - start,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }
    manifest = {
        "version": "madrid-neighborhoods-v1",
        "municipality_code": "28079",
        "source": {
            "url": capture_meta["files"][source_audit["selected"]]["url"],
            "catalogue_url": CATALOG,
            "date": DATE,
            "sha256": digest(raw / source_audit["selected"]),
            "source_audit": source_audit,
            "terms_url": TERMS,
            "license": "Condiciones generales de reutilización del Ayuntamiento de Madrid",
            "attribution": "Origen de los datos: Ayuntamiento de Madrid · Barrios municipales · 31/08/2026",
            "source_crs": "EPSG:25830" if source_audit["fallback"] else "EPSG:4326",
            "output_crs": "EPSG:25830",
            "captured_at": capture_meta["captured_at"],
        },
        "rule": RULE,
        "cp_sha256": meta["files"][CP]["sha256"],
        "source_cp_sha256": meta["files"][CP].get("source_sha256"),
        "base_manifest_sha256": digest(base / "manifest.json"),
        "files": files,
        "summary": summary,
    }
    write_json(output / "manifest.json", manifest)
    assignments.groupby(["district_code", "neighborhood_code"], dropna=False).size().rename(
        "parcels"
    ).reset_index().to_csv(output / "counts.csv", index=False)
    return manifest


def candidate(base, geography, output):
    """Independent local candidate; exact copies of all parent authorized products."""
    base, geography, output = map(Path, (base, geography, output))
    if output.exists():
        raise FileExistsError("New candidate required")
    meta = json.loads((base / "manifest.json").read_text())
    geo = json.loads((geography / "manifest.json").read_text())
    if geo["cp_sha256"] != meta["files"][CP]["sha256"]:
        raise ValueError("Geography and base CP differ")
    from .public_prtr import validate_release

    validate_release(meta)
    # Validate everything before creating an output; no hardlinks to historical snapshots.
    for name, item in meta["files"].items():
        path = Path(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not (base / path).resolve().is_relative_to(base.resolve())
            or digest(base / path) != item["sha256"]
        ):
            raise ValueError("Invalid base product")
    for name in ("neighborhoods.parquet", "assignments.parquet"):
        if digest(geography / name) != geo["files"][name]["sha256"]:
            raise ValueError("Invalid geographic product")
    output.mkdir(parents=True)
    for name in meta["files"]:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base / name, target)
    for name in ("neighborhoods.parquet", "assignments.parquet"):
        target = output / "geography" / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(geography / name, target)
        meta["files"]["geography/" + name] = {
            **geo["files"][name],
            "family": "official_neighborhood_geography",
        }
    meta.update(
        release_id=output.name,
        candidate_status="local_visual_review_pending",
        parent_manifest_sha256=digest(base / "manifest.json"),
        geography={
            "version": geo["version"],
            "source": geo["source"],
            "rule": geo["rule"],
            "summary": geo["summary"],
            "cp_sha256": geo["cp_sha256"],
            "product_manifest_sha256": digest(geography / "manifest.json"),
        },
    )
    write_json(output / "manifest.json", meta)
    return {
        "candidate": str(output),
        "manifest_sha256": digest(output / "manifest.json"),
        "files": len(meta["files"]),
        "total_bytes": sum(p["bytes"] for p in meta["files"].values()),
        "geography_bytes": sum(
            geo["files"][n]["bytes"] for n in ("neighborhoods.parquet", "assignments.parquet")
        ),
        "parent_preserved": True,
        "public_release_created": False,
    }


def available():
    from . import production_bundle as bundle

    return (
        bool(bundle.metadata().get("geography"))
        if bundle.active()
        else (DEFAULT / "manifest.json").exists()
    )


@lru_cache(maxsize=2)
def _local(directory, token):
    from . import demo

    root = Path(directory)
    meta = json.loads((root / "manifest.json").read_text())
    if digest(demo.CITY / "parcels_audited.parquet") not in {
        meta["cp_sha256"],
        meta["source_cp_sha256"],
    }:
        raise ValueError("Local neighborhood CP contract differs")
    for name, item in meta["files"].items():
        if digest(root / name) != item["sha256"]:
            raise ValueError("Local geographic product changed")
    return {
        name: pd.read_parquet(root / name)
        for name in ("neighborhoods.parquet", "assignments.parquet")
    }


@lru_cache(maxsize=2)
def _bundled(token):
    from . import production_bundle as bundle

    return {
        name: bundle.read("geography/" + name)
        for name in ("neighborhoods.parquet", "assignments.parquet")
    }


def read(name):
    from . import production_bundle as bundle

    if name not in {"neighborhoods.parquet", "assignments.parquet"}:
        raise ValueError("Invalid geographic product")
    if bundle.active():
        meta = bundle.metadata()
        if meta.get("geography", {}).get("cp_sha256") != meta["files"][CP]["sha256"]:
            raise ValueError("Bundled neighborhood CP contract differs")
        return _bundled(bundle.signature())[name]
    paths = [DEFAULT / n for n in ("manifest.json", "neighborhoods.parquet", "assignments.parquet")]
    from . import demo

    paths.append(demo.CITY / "parcels_audited.parquet")
    token = tuple((p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths)
    return _local(str(DEFAULT), token)[name]


def names(district):
    rows = read("neighborhoods.parquet")
    if district == "all":
        return {}
    return (
        rows[rows.district_code.eq(district)]
        .set_index("neighborhood_code")
        .neighborhood_name.to_dict()
    )


def restrict(index, district, neighborhood):
    if neighborhood == "all":
        return index
    if neighborhood not in names(district):
        raise ValueError("Neighborhood outside selected district")
    rows = read("assignments.parquet")
    refs = rows.loc[
        rows.status.eq("assigned")
        & rows.district_code.eq(district)
        & rows.neighborhood_code.eq(neighborhood),
        "parcel_ref14",
    ]
    return index[index.parcel_ref14.isin(refs)].reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["capture", "build", "candidate"])
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--base", type=Path, default=Path("data/deployment/madrid_rehab_v1_03"))
    parser.add_argument("--geography-dir", type=Path, default=DEFAULT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "capture":
        result = capture(args.output_dir)
    elif args.action == "build":
        if not args.raw_dir:
            parser.error("--raw-dir required")
        result = build(args.raw_dir, args.base, args.output_dir)
    else:
        result = candidate(args.base, args.geography_dir, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
