"""Shared offline municipal explorer, with complete spatial paging of accepted CP."""

import math
import os
import re
import logging
from datetime import datetime, timezone

import shapely as sh

import pyarrow.parquet as pq
import pandas as pd
import streamlit as st
from shapely.geometry import box

from . import demo
from .city_maps import unit_selection

PAGE_SIZE = 500
CELL_SIZE = 1000


def covered_municipalities():
    """Discover accepted CP/BU products from the validated manifest, never a code list."""
    manifest = demo.verified_json(demo.CADASTRE, "summary.json")
    del manifest  # Validate the snapshot before interpreting its partition manifests.
    import json

    outputs = json.loads((demo.CADASTRE / "manifest.json").read_text())["outputs"]
    codes = set()
    for relative in outputs:
        if relative.count("/") == 1 and relative.endswith("/manifest.json"):
            metadata = demo.verified_json(demo.CADASTRE, relative)
            quality = metadata.get("quality", {})
            if (
                metadata.get("validation_status") == "partial_validated"
                and quality.get("cp", {}).get("accepted", 0) > 0
                and quality.get("bu", {}).get("accepted", 0) > 0
            ):
                codes.add(quality["municipality_code"])
    # Historical Madrid CP is authenticated against the conservation contract.
    if (
        not demo.read(demo.CITY, "parcels_audited.parquet", columns=["parcel_ref14"]).empty
        and not demo.read(demo.CITY, "buildings_audited.parquet", columns=["building_id"]).empty
    ):
        codes.add("28079")
    return demo.municipalities().loc[lambda frame: frame.municipality_code.isin(codes)]


def object_source(code, kind):
    if kind == "cp":
        return demo.cp_source(code)
    if kind != "bu":
        raise ValueError("Tipo catastral desconocido")
    override = os.environ.get("MADRID_REHAB_CADASTRE_DIR")
    if override and code != "28079":
        return demo.Path(override) / code, "bu.parquet"
    return (
        (demo.CITY, "buildings_audited.parquet")
        if code == "28079"
        else (demo.CADASTRE, f"{code}/bu.parquet")
    )


def parcel_index(code):
    return object_index(code, "cp")


def object_index(code, kind):
    root, relative = object_source(code, kind)
    paths = [root / relative, (demo.CONSERVATION if root == demo.CITY else root) / "manifest.json"]
    if root == demo.CITY:
        paths.append(demo.Path("data/processed/session_7_final/manifest.json"))
    signature = tuple(
        (str(p), p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
    )
    return _object_index(code, kind, signature)


@st.cache_data(max_entries=12, show_spinner=False)
def _object_index(code, kind, signature):
    root, relative = object_source(code, kind)
    identifier = "parcel_ref14" if kind == "cp" else "building_id"
    columns = [identifier, "usable_geometry"]
    has_reference_point = {"x", "y"}.issubset(pq.read_schema(root / relative).names)
    if kind == "cp" and has_reference_point:
        columns += ["x", "y"]
    elif code == "28079":
        columns += ["geometry_wkt"]
    else:
        columns += ["minx", "miny", "maxx", "maxy"]
    frame = demo.read(root, relative, columns=columns)
    frame = frame[~frame[identifier].duplicated(keep=False) & frame.usable_geometry].copy()
    if kind == "bu" or not has_reference_point:
        if code == "28079":
            bounds = sh.bounds(sh.from_wkt(frame.geometry_wkt.to_numpy()))
            frame["x"] = (bounds[:, 0] + bounds[:, 2]) / 2
            frame["y"] = (bounds[:, 1] + bounds[:, 3]) / 2
            frame = frame.drop(columns="geometry_wkt")
        else:
            frame["x"] = (frame.minx + frame.maxx) / 2
            frame["y"] = (frame.miny + frame.maxy) / 2
        if kind == "bu":
            frame = frame.rename(columns={identifier: "parcel_ref14"})
    frame = frame.dropna(subset=["parcel_ref14", "x", "y"])
    frame["zone"] = (
        (frame.x // CELL_SIZE).astype(int).astype(str)
        + ":"
        + (frame.y // CELL_SIZE).astype(int).astype(str)
    )
    return frame.sort_values("parcel_ref14").reset_index(drop=True)


def resolve_object(code, identifier, kind):
    """Resolve a municipal domain identity without collapsing ambiguity."""
    empty = pd.DataFrame()
    if kind not in {"cp", "bu"} or not isinstance(identifier, str) or not identifier:
        return "identificador inválido", empty
    if kind == "cp":
        identifier = identifier.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{14}", identifier):
            return "identificador inválido", empty
    try:
        root, relative = object_source(code, kind)
        field = "parcel_ref14" if kind == "cp" else "building_id"
        result = demo.read(root, relative, [(field, "==", identifier)])
        if result.empty:
            return "objeto no disponible", empty
        if len(result) != 1:
            return "referencia ambigua", empty
        row = result.iloc[0]
        if "municipality_code" in result and str(row.municipality_code) != code:
            return "incompatibilidad municipal", empty
        if not bool(row.usable_geometry) or (
            "selection_status" in result and row.selection_status != "accepted"
        ):
            return "objeto no utilizable", empty
        return "CP encontrada y aceptada" if kind == "cp" else "BU encontrado y utilizable", result
    except Exception:
        logging.getLogger(__name__).exception("Cadastral read failed: %s %s", code, kind)
        return "error de lectura", empty


def selected_object(code, identifier, kind):
    return resolve_object(code, identifier, kind)[1]


def zone_page(index, zone, page):
    refs = index[index.zone.eq(zone)].parcel_ref14.sort_values()
    if page < 0 or page >= max(1, math.ceil(len(refs) / PAGE_SIZE)):
        raise ValueError("Página fuera de la zona")
    return refs.iloc[page * PAGE_SIZE : (page + 1) * PAGE_SIZE].tolist()


def zone_frame(index):
    rows = []
    for zone, count in index.groupby("zone").size().items():
        x, y = (int(value) * CELL_SIZE for value in zone.split(":"))
        rows.append(
            dict(
                unit_id=zone,
                name=f"Zona {zone} · {count} objetos",
                geometry_wkt=box(x, y, x + CELL_SIZE, y + CELL_SIZE).wkt,
            )
        )
    return pd.DataFrame(rows)


def picked(event, allowed):
    """Use Madrid's identity allowlist selection parser for both layers."""
    return unit_selection(event, set(allowed))


def apply_map_event(state, event, allowed, code, prefix, zone):
    """Apply a chart event only to its active municipal context and visible identities."""
    if state.get("municipal_active_context") != (code, prefix):
        return
    value = picked(event, allowed)
    emitted = [
        item.get("unit_id", item.get("properties", {}).get("unit_id"))
        for items in (event or {}).get("selection", {}).get("objects", {}).values()
        for item in items
    ]
    state["selection_event_id"] = [v for v in emitted if isinstance(v, str)]
    if not value:
        return
    state["selection_last_change"] = datetime.now(timezone.utc).isoformat()
    if zone == "Vista general":
        state[prefix + "_zone"] = value
        state[prefix + "_ref"] = ""
        state[prefix + "_selected"] = ""
    else:
        state[prefix + "_ref"] = value
        state[prefix + "_selected"] = value
    state[prefix + "_map_epoch"] = state.get(prefix + "_map_epoch", 0) + 1


def render_territories(selector_key):
    """One clickable entry map; a territorial click updates the existing selector."""
    from .regional_view import geometry_deck

    towns = covered_municipalities()
    frame = demo.read(demo.TERRITORY, "municipality_boundaries.parquet")
    frame = frame[frame.municipality_code.isin(towns.municipality_code)].copy()
    frame["unit_id"] = frame.municipality_code
    key = "municipal-territories-" + selector_key

    def choose():
        code = picked(st.session_state.get(key), frame.municipality_code)
        if code:
            st.session_state[selector_key] = code
            st.session_state["municipal_show_territories"] = False
            st.session_state.pop("municipal_active_context", None)

    st.pydeck_chart(
        geometry_deck(frame, "unit_id", 8),
        key=key,
        on_select=choose,
        selection_mode="single-object",
        height=600,
    )


def render_explorer(code, name, initial_ref=""):
    from .regional_view import geometry_deck

    mode = st.radio(
        "Objetos catastrales",
        ["Parcelas", "Objetos BU independientes"],
        horizontal=True,
        key="municipal_kind_" + code,
    )
    kind = "cp" if mode == "Parcelas" else "bu"
    index = object_index(code, kind)
    if index.empty:
        st.info("No disponible en las fuentes integradas")
        st.caption("No hay objetos con identidad única y geometría utilizable en esta captura.")
        return
    prefix = "municipal_" + code + "__" + kind
    context = (code, prefix)
    if st.session_state.get("municipal_active_context") != context:
        for key in list(st.session_state):
            if key.startswith("municipal_") and key not in {
                "municipal_show_territories",
                "municipal_active_context",
            }:
                if key != "municipal_kind_" + code:
                    del st.session_state[key]
        st.session_state["municipal_active_context"] = context
        st.session_state["selection_event_id"] = None
        st.session_state["selection_last_change"] = datetime.now(timezone.utc).isoformat()
    selection_key = prefix + "_ref"
    if selection_key not in st.session_state:
        st.session_state[selection_key] = st.session_state.get(
            prefix + "_selected", initial_ref if kind == "cp" else ""
        )
    if initial_ref and kind == "cp" and st.session_state.get(prefix + "_initial") != initial_ref:
        st.session_state[selection_key] = initial_ref
        st.session_state[prefix + "_initial"] = initial_ref
        st.session_state[prefix + "_selected"] = initial_ref
    if prefix + "_selected" not in st.session_state:
        st.session_state[prefix + "_selected"] = st.session_state[selection_key]
    if code != "28079":
        st.caption(
            "Cobertura catastral parcial. Solo parcelas aceptadas; cuarentena excluida. BU independiente, sin relación BU–CP acreditada."
        )

    def clear_object():
        st.session_state[selection_key] = ""
        st.session_state[prefix + "_selected"] = ""
        st.session_state[prefix + "_last_ref"] = ""
        st.session_state["selection_last_change"] = datetime.now(timezone.utc).isoformat()
        st.session_state["selection_event_id"] = None
        st.session_state[prefix + "_map_epoch"] = st.session_state.get(prefix + "_map_epoch", 0) + 1

    def back_to_zones():
        clear_object()
        st.session_state[prefix + "_zone"] = "Vista general"

    st.button("Volver a cuadrículas", key=prefix + "_back", on_click=back_to_zones)
    search, clear = st.columns([4, 1])

    def search_changed():
        value = st.session_state[selection_key].strip()
        st.session_state["selection_last_change"] = datetime.now(timezone.utc).isoformat()
        st.session_state["selection_event_id"] = None
        st.session_state[prefix + "_selected"] = value.upper() if kind == "cp" else value
        st.session_state[prefix + "_map_epoch"] = st.session_state.get(prefix + "_map_epoch", 0) + 1

    with search:
        st.text_input(
            "Referencia catastral de parcela (14 caracteres)"
            if kind == "cp"
            else "Identificador del objeto catastral BU",
            key=selection_key,
            on_change=search_changed,
        )
    with clear:
        st.button("Limpiar selección", key=prefix + "_clear", on_click=clear_object)
    ref = st.session_state[prefix + "_selected"]
    zones = sorted(index.zone.unique())
    st.session_state["fiche_identity"] = None
    st.session_state["fiche_sections"] = {}
    reader_status, cp = (
        resolve_object(code, ref, kind) if ref else ("sin selección", pd.DataFrame())
    )
    selected_zone = index.loc[index.parcel_ref14.eq(ref), "zone"]
    zone_key = prefix + "_zone"
    if not selected_zone.empty and st.session_state.get(prefix + "_last_ref") != ref:
        st.session_state[zone_key] = selected_zone.iloc[0]
        st.session_state[prefix + "_last_ref"] = ref
        selected_refs = index[index.zone.eq(selected_zone.iloc[0])].parcel_ref14.tolist()
        st.session_state[prefix + "_page_" + selected_zone.iloc[0]] = (
            selected_refs.index(ref) // PAGE_SIZE
        )
    zone = st.selectbox(
        "Zona de exploración",
        ["Vista general", *zones],
        key=zone_key,
        on_change=clear_object,
        format_func=lambda value: value
        if value == "Vista general"
        else f"Zona {value} · {int(index.zone.eq(value).sum()):,} objetos",
    )
    map_col, fiche_col = st.columns([3, 2], gap="medium")
    with map_col:
        if zone == "Vista general":
            all_zones = zone_frame(index)
            overview_page = st.selectbox(
                "Página de zonas",
                range(math.ceil(len(all_zones) / PAGE_SIZE)),
                format_func=lambda value: str(value + 1),
                key=prefix + "_overview_page",
            )
            frame = all_zones.iloc[overview_page * PAGE_SIZE : (overview_page + 1) * PAGE_SIZE]
            st.caption(f"{len(frame)} de {len(all_zones)} zonas · máximo {PAGE_SIZE} por carga.")
            id_column = "unit_id"
            zoom = 11
            st.caption(
                "Selecciona una celda en el mapa o en Zona de exploración. Las celdas son una cuadrícula de navegación, no barrios oficiales."
            )
        else:
            total = int(index.zone.eq(zone).sum())
            page = st.selectbox(
                "Página de objetos",
                range(math.ceil(total / PAGE_SIZE)),
                format_func=lambda value: str(value + 1),
                key=prefix + "_page_" + zone,
                on_change=clear_object,
            )
            refs = zone_page(index, zone, page)
            root, relative = object_source(code, kind)
            field = "parcel_ref14" if kind == "cp" else "building_id"
            frame = demo.read(root, relative, [(field, "in", refs)])
            frame = frame[frame.usable_geometry & frame[field].isin(refs)].copy()
            frame["unit_id"] = frame[field]
            id_column = "unit_id"
            zoom = 15
            st.caption(
                f"{len(frame):,} de {total:,} objetos de esta zona · límite {PAGE_SIZE} por carga. Todas accesibles mediante páginas; {len(index):,} en la captura municipal."
            )
        map_key = prefix + "_map_" + zone + (str(page) if zone != "Vista general" else "")

        map_key += "_" + str(st.session_state.get(prefix + "_map_epoch", 0))

        def select_map():
            apply_map_event(
                st.session_state,
                st.session_state.get(map_key),
                frame[id_column],
                code,
                prefix,
                zone,
            )

        st.pydeck_chart(
            geometry_deck(frame, id_column, zoom, selected=ref),
            key=map_key,
            on_select=select_map,
            selection_mode="single-object",
            height=600,
        )
    with fiche_col:
        if cp.empty:
            st.info("Selecciona un objeto en el mapa o busca su identificador catastral.")
            if ref:
                st.error(f"{reader_status}: {code} · {kind} · {ref}. No se confirma este objeto.")
        else:
            with st.container(height=650):
                from .municipal_fiche import render_fiche

                render_fiche(code, name, ref, cp, kind)

    if os.environ.get("MADRID_REHAB_DEBUG_SELECTION") == "1":
        with st.expander("Diagnóstico técnico de selección"):
            st.json(
                {
                    "municipio": code,
                    "nivel": "cuadrículas" if zone == "Vista general" else "objetos",
                    "cuadricula": zone,
                    "pagina": page if zone != "Vista general" else overview_page,
                    "tipo": kind,
                    "id_evento": st.session_state.get("selection_event_id"),
                    "id_persistente": (code, kind, ref),
                    "lector": reader_status,
                    "identidad_renderizada": st.session_state.get("fiche_identity"),
                    "apartados": st.session_state.get("fiche_sections"),
                    "ultimo_cambio": st.session_state.get("selection_last_change"),
                }
            )


def construction_records(code, cp):
    """Expose existing Madrid BU attributes without creating pilot BU/CP relations."""
    if code != "28079":
        return pd.DataFrame()
    from pathlib import Path
    from .city_store import partition_manifest
    from .municipal_fiche import construction_table

    DEFAULT = Path(__file__).resolve().parents[2] / "data/processed/session_7_final"

    district = cp.iloc[0].get("district_code")
    if not isinstance(district, str) or len(district) != 2:
        return pd.DataFrame()
    root = Path(os.environ.get("MADRID_REHAB_SESSION7_DIR", str(DEFAULT)))
    metadata = partition_manifest(root, district)
    path = root / "districts" / district / "map_buildings.parquet"
    if demo.digest(path) != metadata["outputs"][path.name]:
        raise ValueError("Registros constructivos alterados")
    records = pd.read_parquet(path, filters=[("parcel_ref14", "==", cp.iloc[0].parcel_ref14)])
    return construction_table(records)
