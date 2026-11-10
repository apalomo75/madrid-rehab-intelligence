"""Navegación regional por cobertura real, con lectura municipal diferida."""

import json
import os
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds
import pydeck as pdk
import shapely as sh
import streamlit as st
from pyproj import Transformer
from shapely.ops import transform

from .grants_view import NOTICE, read_view, safe_export
from .ingest import digest
from .regional_cadastre import DEFAULT, verify_partition as verify_legacy_partition
from .municipal_boundaries import DEFAULT as OFFICIAL_BOUNDARIES
from .territorial_prtr import DEFAULT as TERRITORIAL_PRTR


def money(value):
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def token(root):
    root = Path(root)
    paths = [root / "manifest.json", *sorted(root.glob("*.parquet"))]
    if (
        root.name in {"28065", "28092", "28074", "28007", "28005"}
        and (root.parent / "manifest.json").exists()
    ):
        paths.append(root.parent / "manifest.json")
    return tuple(
        (str(p), p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
    )


@st.cache_data(max_entries=2, show_spinner=False)
def load_inventory(root, signature):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    for name, sha in manifest["outputs"].items():
        if digest(root / name) != sha:
            raise ValueError("Inventario alterado")
    if token(root) != signature:
        raise ValueError("Captura cambiada")
    return pd.read_parquet(root / "cadastre_resources.parquet")


@st.cache_data(max_entries=2, show_spinner=False)
def load_territory(root, signature):
    from .regional import load_official_boundaries

    root = Path(root)
    result = load_official_boundaries(
        root / "municipality_boundaries.parquet", root / "manifest.json"
    )
    if token(root) != signature:
        raise ValueError("Captura cambiada")
    return result


@st.cache_data(max_entries=2, show_spinner=False)
def load_decisions(root, signature, source_manifest_sha256=None):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if (
        source_manifest_sha256 is not None
        and manifest.get(
            "source_manifest_sha256",
            manifest.get("inputs", {}).get(
                "data/processed/grants/session_11_final_03/grant_source_manifest.json"
            ),
        )
        != source_manifest_sha256
    ):
        raise ValueError("Decisión territorial de otra captura PRTR")
    for name, sha in manifest["outputs"].items():
        if digest(root / name) != sha:
            raise ValueError("Asignación regional alterada")
    if token(root) != signature:
        raise ValueError("Captura cambiada")
    return pd.read_parquet(root / "grant_municipality_links.parquet")


def partition_path(code):
    return (
        Path(
            os.environ.get(
                "MADRID_REHAB_CADASTRE_DIR",
                "data/processed/cadastre/session_12_2_partial_validated_01",
            )
        )
        / code
    )


def verify_partition(root):
    """Explicit adapter for accepted partial products; legacy validation stays strict."""
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("version") != "partial-cadastre-v1":
        return verify_legacy_partition(root)
    if (
        manifest.get("validation_status") != "partial_validated"
        or manifest["quality"]["municipality_code"] != root.name
        or not manifest.get("independent_bu")
        or manifest.get("cp_bu_relations_created") is not False
    ):
        raise ValueError("Contrato parcial incompatible")
    parent = json.loads((root.parent / "manifest.json").read_text())
    if digest(root / "manifest.json") != parent["outputs"][root.name + "/manifest.json"]:
        raise ValueError("Manifiesto municipal alterado")
    for name, sha in manifest["outputs"].items():
        if digest(root / name) != sha:
            raise ValueError("Producto parcial alterado")
    for path, sha in manifest["inputs"].items():
        if digest(path) != sha:
            raise ValueError("Original parcial alterado")
    counts = {}
    for kind in ("cp", "bu"):
        frame = pd.read_parquet(
            root / f"{kind}.parquet",
            columns=["selection_status", "municipality_code", "usable_geometry"],
        )
        if not (
            frame.selection_status.eq("accepted")
            & frame.municipality_code.eq(root.name)
            & frame.usable_geometry
        ).all():
            raise ValueError("Vista aceptada contiene objetos no utilizables")
        counts[kind] = len(frame)
        if len(frame) != manifest["quality"][kind]["accepted"]:
            raise ValueError("Recuento parcial incompatible")
    return {
        **manifest,
        "cp_rows": counts["cp"],
        "bu_objects": counts["bu"],
        "cp_usable": counts["cp"],
        "bu_usable": counts["bu"],
    }


def integrated_codes():
    from .municipal_navigation import covered_municipalities

    return set(covered_municipalities().municipality_code)


def regional_root_path():
    override = os.environ.get("MADRID_REHAB_REGIONAL_GRANTS_DIR")
    if override:
        return Path(override)
    pointer = partition_path("unused").parent / "active_prtr.json"
    if pointer.exists():
        record = json.loads(pointer.read_text())
        root = Path(record["path"])
        if digest(root / "manifest.json") != record["manifest_sha256"]:
            raise ValueError("Captura PRTR activa alterada")
        return root
    partial = partition_path("unused").parent
    if (partial / "manifest.json").exists():
        meta = json.loads((partial / "manifest.json").read_text())
        if meta.get("version") == "partial-cadastre-v1":
            return partial
    return TERRITORIAL_PRTR


@st.cache_data(max_entries=2, show_spinner=False)
def parcel_index(root, signature):
    verify_partition(root)
    if token(root) != signature:
        raise ValueError("Partición cambiada")
    path = Path(root) / "cp.parquet"
    filters = (
        [("usable_geometry", "==", True)]
        if "usable_geometry" in ds.dataset(path).schema.names
        else None
    )
    return pd.read_parquet(path, columns=["parcel_ref14"], filters=filters).dropna()


@st.cache_data(max_entries=6, show_spinner=False)
def partition_info(root, signature):
    result = verify_partition(root)
    if token(root) != signature:
        raise ValueError("Partición cambiada")
    return result


@st.cache_data(max_entries=4, show_spinner=False)
def parcel_objects(root, signature, ref, kind):
    if kind not in {"cp", "bu"}:
        raise ValueError("Tipo catastral no admitido")
    if token(root) != signature:
        raise ValueError("Partición cambiada")
    return pd.read_parquet(Path(root) / f"{kind}.parquet", filters=[("parcel_ref14", "==", ref)])


def municipality_changed(state, key):
    if state.get("regional_previous_municipality") != key:
        for name in ["regional_parcel", "regional-map"]:
            state.pop(name, None)
        state["regional_previous_municipality"] = key


def parcel_map_changed():
    event = st.session_state.get("regional-map", {})
    objects = event.get("selection", {}).get("objects", {})
    for rows in objects.values():
        if rows:
            ref = rows[0].get("properties", {}).get("id")
            if ref:
                st.session_state["regional_parcel"] = ref
                return


@st.cache_data(max_entries=3, show_spinner=False)
def map_parcels(root, signature, x, y, zoom):
    if token(root) != signature or not 10 <= zoom <= 19:
        raise ValueError("Captura o zoom incompatible")
    radius = min(15000, 200 * 2 ** (17 - zoom))
    dataset = ds.dataset(Path(root) / "cp.parquet", format="parquet")
    selected = (
        (ds.field("maxx") >= x - radius)
        & (ds.field("minx") <= x + radius)
        & (ds.field("maxy") >= y - radius)
        & (ds.field("miny") <= y + radius)
    )
    if "usable_geometry" in dataset.schema.names:
        selected = selected & (ds.field("usable_geometry") == True)  # noqa: E712
    frame = dataset.head(
        1501, columns=["parcel_ref14", "geometry_wkt"], filter=selected
    ).to_pandas()
    return frame.iloc[:1500], len(frame) > 1500


def geometry_deck(frame, id_column, zoom=8, selected="", *, preserve_geometry=False):
    project = Transformer.from_crs(25830, 4326, always_xy=True).transform
    features = []
    for row in frame.itertuples():
        geom = transform(
            project,
            sh.from_wkt(row.geometry_wkt)
            if preserve_geometry
            else sh.from_wkt(row.geometry_wkt).simplify(
                5 if zoom < 12 else 0.2, preserve_topology=True
            ),
        )
        features.append(
            dict(
                type="Feature",
                geometry=sh.geometry.mapping(geom),
                properties={
                    "id": str(getattr(row, id_column)),
                    "unit_id": str(getattr(row, id_column)),
                    "name": getattr(row, "name", str(getattr(row, id_column))),
                    "selected": str(getattr(row, id_column)) == selected,
                    "color": [35, 130, 155, 100]
                    if id_column != "municipality_code"
                    or not getattr(row, "cp_ready", row.municipality_code == "28079")
                    else [200, 130, 35, 140],
                },
            )
        )
    if "catalog_color" in frame:
        for feature, color in zip(features, frame.catalog_color):
            feature["properties"]["color"] = color
    center = sh.union_all(sh.from_wkt(frame.geometry_wkt.to_numpy())).representative_point()
    lon, lat = project(center.x, center.y)
    return pdk.Deck(
        layers=[
            pdk.Layer(
                "GeoJsonLayer",
                {"type": "FeatureCollection", "features": features},
                id="regional-geometries",
                pickable=True,
                get_fill_color="properties.color",
                get_line_color="properties.selected ? [20, 80, 255] : [25, 70, 90]",
                get_line_width="properties.selected ? 4 : 1",
                line_width_units="pixels",
                line_width_min_pixels=1,
            )
        ],
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom),
        map_style=None,
        tooltip={"text": "{name} · {id}"},
    )


def open_madrid():
    st.session_state["city_navigation"] = "Madrid capital"


def render_municipality(code, name):
    from .municipal_navigation import render_explorer

    st.button(
        "Ver municipios en el mapa",
        key="regional_territories",
        on_click=lambda: st.session_state.update(municipal_show_territories=True),
    )
    if st.session_state.get("municipal_show_territories"):
        from .municipal_navigation import render_territories

        render_territories("regional_municipality")
    else:
        render_explorer(code, name)
    if code == "28079":
        st.button("Abrir fichas de Madrid capital · NDP y REC", on_click=open_madrid)


def render_regional():
    from .energy_view import render_energy_region

    st.title("Comunidad de Madrid · Cobertura municipal")
    root = Path(os.environ.get("MADRID_REHAB_TERRITORY_INVENTORY_DIR", str(DEFAULT)))
    if not (root / "manifest.json").exists():
        st.info(
            "Genera el inventario: python -m madrid_rehab.regional_cadastre --inventory-output data/processed/territory/session_12_01"
        )
        return
    try:
        resources = load_inventory(str(root), token(root))
        boundary_root = Path(os.environ.get("MADRID_REHAB_TERRITORY_DIR", str(OFFICIAL_BOUNDARIES)))
        municipalities = (
            load_territory(str(boundary_root), token(boundary_root))
            if (boundary_root / "manifest.json").exists()
            else None
        )
        a, b, c = st.columns(3)
        a.metric("Municipios en inventario oficial catastral", len(resources))
        b.metric(
            "Municipios con límite oficial validado",
            0 if municipalities is None else len(municipalities),
        )
        cp_codes = integrated_codes()
        c.metric("Municipios con CP/BU integrado", len(cp_codes))
        if municipalities is None:
            st.warning(
                "Inventario Catastro de 179 municipios. Catálogo INE completo y límites pendientes de descarga; no hay clasificación espacial regional validada."
            )
            from .municipal_navigation import covered_municipalities

            names = covered_municipalities().set_index("municipality_code").name.to_dict()
            selected = st.selectbox(
                "Municipio",
                sorted(cp_codes, key=names.get),
                format_func=lambda key: names[key],
                key="regional_municipality",
                on_change=lambda: st.session_state.update(municipal_show_territories=False),
            )
            code, name = selected, names[selected]
        else:
            municipalities = municipalities.copy()
            municipalities["cp_ready"] = municipalities.municipality_code.isin(cp_codes)
            names = municipalities.set_index("municipality_code")["name"].to_dict()
            selected = st.selectbox(
                "Municipio",
                sorted(cp_codes, key=names.get),
                format_func=lambda key: names[key],
                key="regional_municipality",
                on_change=lambda: st.session_state.update(municipal_show_territories=False),
            )
            code, name = (
                (None if selected == "all" else selected),
                names.get(selected, "Comunidad de Madrid"),
            )
            boundary_metadata = json.loads((boundary_root / "manifest.json").read_text())
            st.caption(
                f"Obra derivada de límites oficiales · {boundary_metadata['publisher']} · "
                "Licencia y fecha de actualización de la fuente pendientes de verificar."
            )
            st.caption(
                "Ocre: municipios con CP/BU integrado en esta navegación. CEEE regional en el panel energético. Azul: límite municipal disponible, "
                "sin CP/BU integrado. Los territorios de jurisdicción compartida se conservan "
                "aparte y no se atribuyen a un municipio. Licencia de límites pendiente de verificar."
            )
        municipality_changed(st.session_state, selected)
        if selected == "all":
            render_energy_region()
        if selected != "all":
            cp_ready = code in cp_codes
            st.write(
                f"CP/BU: {'procesados; ver captura municipal' if cp_ready else 'sin procesar'} · CEEE: {'captura regional consultable en el panel energético' if code else 'municipio sin identidad INE validada'} · Eventos urbanísticos: {'Madrid capital' if code == '28079' else 'no integrados'}."
            )
            if code:
                render_municipality(code, name)
            else:
                st.info(
                    "Correspondencia INE pendiente de verificación. No se asignan PRTR por nombre ni por rectángulos ATOM."
                )
        data = read_view()
        if data is None:
            return
        _, grants, _ = data
        regional_root = regional_root_path()
        if (regional_root / "manifest.json").exists():
            from .grants_view import root_path

            decisions = load_decisions(
                str(regional_root),
                token(regional_root),
                digest(root_path() / "grant_source_manifest.json"),
            )
            grants = grants.drop(columns="municipality_code").merge(
                decisions, on="expediente_id", validate="one_to_one"
            )
            match_summary = regional_root / "grant_match_summary.parquet"
            if (
                match_summary.exists()
                and "current_cp_confirmed" in ds.dataset(match_summary).schema.names
            ):
                grants = grants.merge(
                    pd.read_parquet(
                        match_summary, columns=["expediente_id", "current_cp_confirmed"]
                    ),
                    on="expediente_id",
                    validate="one_to_one",
                )
            if "evidence_level" in grants:
                grants["Calidad territorial"] = grants.evidence_level.map(
                    {
                        "A": "A · Espacial verificada",
                        "B": "B · Espacial y documental concordante",
                        "C": "C · Contradicción o ambigüedad",
                        "unassigned": "Sin asignación",
                    }
                )
        elif selected != "all" and code != "28079":
            st.info("Asignación PRTR municipal no disponible; no representa cero ayudas.")
            return
        if selected != "all":
            if code is None:
                st.info(
                    "PRTR conservados regionalmente; asignación a este municipio no disponible."
                )
                return
            grants = grants[grants.municipality_code.eq(code)]
        with st.expander("Filtros PRTR"):
            programs = st.multiselect(
                "Programa PRTR", ["P1", "P3", "P4", "P5"], default=["P1", "P3", "P4", "P5"]
            )
            minimum = st.number_input("Ayuda mínima concedida (€)", min_value=0.0)
            maximum = st.number_input(
                "Ayuda máxima concedida (€)", min_value=0.0, value=5_000_000.0
            )
            coverage = st.selectbox(
                "Cobertura catastral confirmada",
                ["Todos", "Con CP confirmado", "Sin CP confirmado"],
            )
            qualities = (
                st.multiselect(
                    "Calidad de asignación territorial",
                    sorted(grants["Calidad territorial"].dropna().unique()),
                    default=sorted(grants["Calidad territorial"].dropna().unique()),
                )
                if "Calidad territorial" in grants
                else None
            )
        selected_grants = grants[
            grants.programa.isin(programs) & grants.importe_concedido.between(minimum, maximum)
        ]
        if qualities is not None:
            selected_grants = selected_grants[
                selected_grants["Calidad territorial"].isin(qualities)
            ]
        if coverage != "Todos":
            has_cp = (
                selected_grants.current_cp_confirmed
                if "current_cp_confirmed" in selected_grants
                else selected_grants.cp_confirmed_municipality_code.notna()
                if "cp_confirmed_municipality_code" in selected_grants
                else selected_grants.territorial_quality.eq("madrid_confirmed")
            )
            selected_grants = selected_grants[
                has_cp if coverage == "Con CP confirmado" else ~has_cp
            ]
        st.caption(NOTICE)
        st.caption(
            "El municipio geográfico no confirma una parcela. La cobertura PRTR corresponde "
            "a esta captura de concesiones y no acredita exhaustividad, pago ni obras terminadas."
        )
        a, b = st.columns(2)
        a.metric(
            "Expedientes únicos · selección / captura regional", f"{len(selected_grants)} / 7532"
        )
        b.metric("Ayuda concedida (€)", money(selected_grants.importe_concedido.sum()))
        st.bar_chart(selected_grants.groupby("programa").size())
        programs_summary = (
            selected_grants.groupby("programa")
            .agg(
                Expedientes=("expediente_id", "size"),
                **{"Ayuda concedida (€)": ("importe_concedido", "sum")},
            )
            .reindex(["P1", "P3", "P4", "P5"], fill_value=0)
        )
        st.dataframe(programs_summary.rename_axis("Programa").reset_index(), hide_index=True)
        st.dataframe(
            selected_grants[
                ["expediente_id", "programa", "importe_concedido"]
                + (["Calidad territorial"] if "Calidad territorial" in selected_grants else [])
            ].rename(
                columns={
                    "expediente_id": "Expediente",
                    "programa": "Programa",
                    "importe_concedido": "Ayuda concedida (€)",
                }
            ),
            hide_index=True,
            column_config={"Ayuda concedida (€)": st.column_config.NumberColumn(format="%.2f €")},
        )
        st.download_button(
            "CSV PRTR seguro · selección local",
            safe_export(selected_grants),
            "prtr_regional.csv",
            "text/csv",
        )
    except (OSError, KeyError, ValueError) as exc:
        st.error(f"Cobertura regional no verificable: {exc}")
