"""Selective retrieval using existing authenticated readers; no new data products."""

import json
from functools import lru_cache
from pathlib import Path
from time import perf_counter

import pandas as pd

from .commercial_fiche import Quality, build_model


@lru_cache(maxsize=4)
def verify_grants(root, token, city_manifest, city_token):
    from .grants import VERSION
    from .ingest import digest

    root = Path(root)
    meta = json.loads((root / "grant_source_manifest.json").read_text())
    city = json.loads(Path(city_manifest).read_text())
    if meta["version"] != VERSION or meta["cp_sha256"] != city["inputs"]["parcels_audited"]:
        raise ValueError("PRTR incompatible con CP")
    if digest(root / "grants.parquet") != meta["outputs"]["grants.parquet"]:
        raise ValueError("PRTR alterado")


@lru_cache(maxsize=48)
def _grant_rows(root, token, ids):
    return pd.read_parquet(
        Path(root) / "grants.parquet",
        filters=[("expediente_id", "in", list(ids))],
        columns=[
            "expediente_id",
            "programa",
            "importe_concedido",
            "fecha_concesion",
            "fecha_actualizacion",
            "identity_conflict",
            "territorial_quality",
        ],
    )


def grant_records(code, ref):
    import os
    from . import demo, grants_view
    from .regional_view import regional_root_path

    root = regional_root_path()
    links = demo.read(root, "grant_parcel_links.parquet", [("parcel_ref14", "==", ref)])
    candidates = root / "grant_spatial_candidates.parquet"
    if candidates.exists():
        links = pd.concat(
            [links, demo.read(root, candidates.name, [("parcel_ref14", "==", ref)])],
            ignore_index=True,
        )
    scope = (
        "geographic_municipality_code"
        if "geographic_municipality_code" in links
        else "municipality_code"
    )
    links = links[links[scope].eq(code)].drop_duplicates(["expediente_id", "match_status"])
    if links.empty:
        return pd.DataFrame()
    source = grants_view.root_path()
    city = (
        Path(os.environ.get("MADRID_REHAB_SESSION7_DIR", "data/processed/session_7_final"))
        / "manifest.json"
    )
    verify_grants(
        str(source),
        grants_view.signature(source),
        str(city),
        (city.stat().st_size, city.stat().st_mtime_ns, city.stat().st_ctime_ns),
    )
    records = _grant_rows(
        str(source), grants_view.signature(source), tuple(sorted(links.expediente_id.unique()))
    ).copy()
    if records.expediente_id.duplicated().any() or records.identity_conflict.any():
        raise ValueError("Identidad de expediente PRTR ambigua")
    result = links.merge(records, on="expediente_id", validate="many_to_one")
    result.loc[result.territorial_quality.eq("contradictory"), "match_status"] = "contradictory"
    return result.drop_duplicates(["expediente_id", "match_status"])


def load_fiche(code, name, identifier, objects, kind="cp", postal=None, public_catalog=False):
    from . import demo, enriched_cadastre as ec
    from .cadastral_identity import construction_records
    from . import energy_view, conservation_view

    started = perf_counter()
    tables = {
        k: pd.DataFrame()
        for k in ("construction", "accesses", "energy", "grants", "events", "municipal_grants")
    }
    states, errors, timings = {}, {}, {}

    def retrieve(key, query):
        begin = perf_counter()
        try:
            result = query()
            if result is None:
                states[key] = Quality.UNAVAILABLE
            else:
                if key == "construction" and code == "28079":
                    from .madrid_recovery import supplement

                    result = supplement(result)
                tables[key] = result
                states[key] = Quality.PARTIAL
        except (OSError, ValueError, KeyError) as exc:
            states[key] = Quality.UNAVAILABLE
            errors[key] = type(exc).__name__ + ": " + str(exc)
        timings[key + "_ms"] = (perf_counter() - begin) * 1000

    if demo.private() or public_catalog:
        retrieve(
            "construction",
            lambda: (
                ec.parcel_buildings(code, identifier)[0]
                if code != "28079" and kind == "cp"
                else ec.building(code, identifier)
                if code != "28079"
                else construction_records(
                    code,
                    objects,
                    columns=[
                        "building_id",
                        "parcel_ref14",
                        "current_use",
                        "construction_oldest_year",
                        "construction_newest_year",
                        "dwellings_raw",
                        "building_units_raw",
                        "source_date",
                        "source_url",
                        "captured_at",
                    ],
                )
                if kind == "cp"
                else objects
            ),
        )
        if kind == "cp":
            if code == "28079":
                retrieve(
                    "accesses",
                    lambda: conservation_view.parcel_evidence(
                        identifier, "accesses", code, public_catalog=public_catalog
                    ),
                )
                retrieve(
                    "events",
                    lambda: conservation_view.parcel_evidence(
                        identifier, "events", code, public_catalog=public_catalog
                    ),
                )
            else:
                states["events"] = Quality.UNCOVERED
                states["accesses"] = Quality.UNCOVERED

            def energy():
                path = f"municipalities/{code}/links.parquet"
                if not (energy_view.root_path() / path).exists():
                    states["energy"] = Quality.UNCOVERED
                    return pd.DataFrame()
                links = energy_view.read(path, identifier)
                if links.empty:
                    return pd.DataFrame()
                certs = energy_view.read(
                    f"municipalities/{code}/certificates.parquet",
                    ids=tuple(links.certificate_id.unique()),
                    columns=[
                        "certificate_id",
                        "observation_date",
                        "scope",
                        "source_id",
                        "consumption_rating",
                        "emissions_rating",
                        "consumption_value",
                        "emissions_value",
                        "consumption_unit",
                        "emissions_unit",
                        "area_value",
                        "area_unit",
                        "consumption_status",
                        "emissions_status",
                        "area_status",
                        "edif_codreg",
                        "edif_direc",
                        "edif_tipo",
                        "identity_status",
                        "date_after_capture",
                    ],
                )
                return certs.merge(
                    links[["certificate_id", "link_level", "link_reason"]].drop_duplicates(),
                    on="certificate_id",
                    validate="one_to_many",
                )

            retrieve("energy", energy)
            if not (energy_view.root_path() / f"municipalities/{code}/links.parquet").exists():
                states["energy"] = Quality.UNCOVERED
            retrieve("grants", lambda: grant_records(code, identifier))
            from .plan_rehabilita_store import parcel_records

            retrieve(
                "municipal_grants",
                lambda: parcel_records(code, identifier, kind, public_catalog=public_catalog),
            )
        else:
            for key in ("accesses", "events", "energy", "grants", "municipal_grants"):
                states[key] = Quality.UNAVAILABLE
    else:
        states = dict.fromkeys(tables, Quality.UNAVAILABLE)
    retrieved = perf_counter()
    model = build_model(
        code, name, identifier, kind, objects, **tables, postal=postal, states=states
    )
    timings["retrieval_ms"] = (retrieved - started) * 1000
    timings["model_ms"] = (perf_counter() - retrieved) * 1000
    timings["total_ms"] = (perf_counter() - started) * 1000
    return model, tables, errors, timings
