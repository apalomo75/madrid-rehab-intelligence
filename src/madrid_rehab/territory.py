"""Unidades territoriales deterministas; el residuo no asignado forma parte del universo."""

import re

import pandas as pd
import shapely as sh

from .normalize import text_key

CODES = tuple(f"{code:02d}" for code in range(1, 22))


def validate_districts(frame):
    if len(frame) != 21 or set(frame.district_code) != set(CODES):
        raise ValueError("Se requieren exactamente los códigos oficiales 01–21")
    if frame.district_name.isna().any() or not frame.district_name.is_unique:
        raise ValueError("Nombres distritales vacíos o duplicados")
    if not frame.geometry_crs.eq("EPSG:25830").all():
        raise ValueError("CRS distrital incompatible")
    geometries = sh.from_wkt(frame.geometry_wkt.to_numpy(), on_invalid="ignore")
    if not (
        sh.is_valid(geometries)
        & ~sh.is_empty(geometries)
        & pd.Series(sh.get_type_id(geometries)).isin([3, 6]).to_numpy()
    ).all():
        raise ValueError("Geometría de distrito inválida")
    for i, geom in enumerate(geometries):
        if any(geom.intersection(other).area > 0.01 for other in geometries[i + 1 :]):
            raise ValueError("Distritos solapados")
    return frame.sort_values("district_code").reset_index(drop=True)


def resolve_district(value, districts):
    key = re.sub(r"[^A-Z0-9]", "", text_key(value))
    if key == "ALL":
        return "all"
    if key.isdigit() and key.zfill(2) in set(districts.district_code):
        return key.zfill(2)
    lookup = {
        re.sub(r"[^A-Z0-9]", "", text_key(row.district_name)): row.district_code
        for row in districts.itertuples()
    }
    if key not in lookup:
        raise ValueError(f"Distrito desconocido: {value}")
    return lookup[key]


def parcel_territories(parcels):
    """Una RC no se asigna por primera fila: todas las CP deben concordar territorialmente."""
    if (
        parcels.parcel_ref14.isna().any()
        or parcels.parcel_ref14.astype(str).str.strip().eq("").any()
    ):
        raise ValueError("Referencia CP vacía")
    grouped = parcels.groupby("parcel_ref14", sort=True).district_code.agg(
        ["size", "count", "nunique", "first"]
    )
    owner = grouped["first"].where(grouped["nunique"].eq(1) & grouped["count"].eq(grouped["size"]))
    result = pd.DataFrame(
        {
            "parcel_ref14": grouped.index,
            "district_code": owner.to_numpy(),
            "cp_rows": grouped["size"].to_numpy(),
        }
    )
    result["district_assignment"] = [
        "assigned" if pd.notna(code) else "ambiguous_reference_district" if n > 1 else "unassigned"
        for code, n in zip(owner, grouped["nunique"])
    ]
    return result


def add_grid(features, parcels):
    out = features.copy()
    out["analysis_zone"] = None
    if not {"x", "y", "coordinate_crs"}.issubset(parcels.columns):
        return out
    counts = parcels.groupby("parcel_ref14").size()
    spatial = parcels[parcels.parcel_ref14.map(counts).eq(1)].copy()
    x, y = pd.to_numeric(spatial.x, errors="coerce"), pd.to_numeric(spatial.y, errors="coerce")
    valid = (
        spatial.coordinate_crs.eq("EPSG:25830")
        & x.between(350000, 500000)
        & y.between(4400000, 4550000)
    )
    spatial["analysis_zone"] = None
    spatial.loc[valid, "analysis_zone"] = [grid_code(a, b) for a, b in zip(x[valid], y[valid])]
    out["analysis_zone"] = out.parcel_ref14.map(spatial.set_index("parcel_ref14").analysis_zone)
    return out


def grid_code(x, y):
    return f"E{int(x // 500) * 500}_N{int(y // 500) * 500}"


def event_territories(events, parcels, municipality_code="28079"):
    """Evidencia territorial separada del literal declarado y de la identidad del evento."""
    out = events.copy()
    scoped_parcels = parcels if "district_code" in parcels else parcels.assign(district_code=None)
    owners = parcel_territories(scoped_parcels).set_index("parcel_ref14")
    known = (
        out.parcel_ref14.map(owners.cp_rows).eq(1)
        & out.match_status.eq("confirmed")
        & out.match_level.eq("parcel")
    )
    if "municipality_code" in parcels:
        valid_refs = set(
            parcels.loc[parcels.municipality_code.eq(municipality_code), "parcel_ref14"]
        )
        known &= out.parcel_ref14.isin(valid_refs)
    out["verified_municipality_code"] = None
    out["verified_district_code"] = None
    out.loc[known, "verified_municipality_code"] = municipality_code
    out.loc[known, "verified_district_code"] = out.loc[known, "parcel_ref14"].map(
        owners.district_code
    )
    out["territory_level"] = "unlocated"
    out.loc[known, "territory_level"] = "parcel"
    out["territory_reason"] = "insufficient_territorial_evidence"
    out.loc[known, "territory_reason"] = "confirmed_reference_in_municipal_cp_snapshot"
    if "municipality_code" in out:
        declared_city = ~known & out.municipality_code.eq(municipality_code)
        out.loc[declared_city, ["territory_level", "territory_reason"]] = [
            "municipality",
            "declared_municipality_not_parcel",
        ]
        if "district_code" in out:
            declared_district = declared_city & out.district_code.isin(CODES)
            out.loc[declared_district, ["territory_level", "territory_reason"]] = [
                "district",
                "declared_district_not_parcel",
            ]
    return out
