"""Cruce CP del piloto sin modificar las decisiones municipales de sesión 12.1."""

import math

import pandas as pd
import shapely as sh
from pyproj import Transformer

CONFIRMED = {"confirmed", "confirmed_reference", "confirmed_historical_madrid"}


def match_municipality(grants, references, cp, code):
    """Referencia exacta primero. Posición sola siempre candidata y en tabla distinta."""
    if not grants.expediente_id.is_unique:
        raise ValueError("Expedientes duplicados")
    if "municipality_code" in grants and not grants.municipality_code.eq(code).all():
        raise ValueError("Expedientes de otro municipio: conservar decisión de sesión 12.1")
    if "source_municipality_code" in cp and not cp.source_municipality_code.eq(code).all():
        raise ValueError("Partición CP de otro municipio")
    cp = cp.copy().reset_index(drop=True)
    if "usable_geometry" not in cp:
        raise ValueError("CP requiere validación explícita")
    by_ref = {
        ref: group for ref, group in cp.dropna(subset=["parcel_ref14"]).groupby("parcel_ref14")
    }
    valid_cp = cp[cp.usable_geometry].copy()
    shapes = sh.from_wkt(valid_cp.geometry_wkt.to_numpy())
    tree = sh.STRtree(shapes)
    project = Transformer.from_crs(4326, 25830, always_xy=True)
    refs = references.groupby("expediente_id").parcel_ref14.agg(list).to_dict()
    links, candidates = [], []
    for g in grants.itertuples():
        point = None
        if (
            g.geometry_valid
            and all(
                isinstance(v, (int, float)) and math.isfinite(v) for v in [g.longitude, g.latitude]
            )
            and -180 <= g.longitude <= 180
            and -90 <= g.latitude <= 90
            and (g.longitude, g.latitude) != (0, 0)
        ):
            point = sh.Point(*project.transform(g.longitude, g.latitude))
        any_confirmed = False
        for ref in dict.fromkeys(refs.get(g.expediente_id, [])):
            group = by_ref.get(ref)
            distance = None
            parcel_id = None
            level = "D"
            if getattr(g, "identity_conflict", False):
                status = "contradictory"
            elif group is None:
                status = "not_found"
            elif len(group) > 1:
                status = "ambiguous"
            elif not group.usable_geometry.iloc[0]:
                status = "unusable_cp"
            else:
                parcel_id = group.parcel_id.iloc[0]
                if point is None:
                    status, level = "confirmed_reference", "A"
                else:
                    distance = float(point.distance(sh.from_wkt(group.geometry_wkt.iloc[0])))
                    status, level = (
                        ("confirmed", "B") if distance <= 100 else ("contradictory", "D")
                    )
            confirmed = status in CONFIRMED
            any_confirmed |= confirmed
            links.append(
                dict(
                    expediente_id=g.expediente_id,
                    parcel_ref14=ref,
                    parcel_id=parcel_id,
                    municipality_code=code if confirmed else None,
                    geographic_municipality_code=code,
                    match_status=status,
                    match_evidence=level,
                    distance_m=distance,
                    territorial_conflict=False,
                )
            )
        if not any_confirmed and point is not None and not getattr(g, "identity_conflict", False):
            hits = tree.query(point, predicate="intersects")
            for hit in hits[:20]:
                candidate = valid_cp.iloc[hit]
                candidates.append(
                    dict(
                        expediente_id=g.expediente_id,
                        parcel_ref14=candidate.parcel_ref14,
                        parcel_id=candidate.parcel_id,
                        geographic_municipality_code=code,
                        match_status="spatial_candidate" if len(hits) == 1 else "ambiguous_spatial",
                        match_evidence="C",
                        candidate_count=len(hits),
                        candidates_truncated=len(hits) > 20,
                    )
                )
    return pd.DataFrame(
        links,
        columns=[
            "expediente_id",
            "parcel_ref14",
            "parcel_id",
            "municipality_code",
            "geographic_municipality_code",
            "match_status",
            "match_evidence",
            "distance_m",
            "territorial_conflict",
        ],
    ), pd.DataFrame(
        candidates,
        columns=[
            "expediente_id",
            "parcel_ref14",
            "parcel_id",
            "geographic_municipality_code",
            "match_status",
            "match_evidence",
            "candidate_count",
            "candidates_truncated",
        ],
    )
