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

from .grants_view import NOTICE, exposure_enabled, read_view, safe_export
from .ingest import digest
from .regional_cadastre import DEFAULT, verify_partition
from .municipal_boundaries import DEFAULT as OFFICIAL_BOUNDARIES
from .territorial_prtr import DEFAULT as TERRITORIAL_PRTR


def money(value):
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def token(root):
    root = Path(root)
    paths = [root / "manifest.json", *sorted(root.glob("*.parquet"))]
    return tuple(
        (p.name, p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
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
        and manifest["source_manifest_sha256"] != source_manifest_sha256
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
                "MADRID_REHAB_CADASTRE_DIR", "data/processed/cadastre/session_12_2_pilot_01"
            )
        )
        / code
    )


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


def geometry_deck(frame, id_column, zoom=8):
    project = Transformer.from_crs(25830, 4326, always_xy=True).transform
    features = []
    for row in frame.itertuples():
        geom = transform(
            project,
            sh.from_wkt(row.geometry_wkt).simplify(5 if zoom < 12 else 0.2, preserve_topology=True),
        )
        features.append(
            dict(
                type="Feature",
                geometry=sh.geometry.mapping(geom),
                properties={
                    "id": str(getattr(row, id_column)),
                    "name": getattr(row, "name", str(getattr(row, id_column))),
                    "color": [35, 130, 155, 100]
                    if id_column != "municipality_code"
                    or not getattr(row, "cp_ready", row.municipality_code == "28079")
                    else [200, 130, 35, 140],
                },
            )
        )
    center = sh.union_all(sh.from_wkt(frame.geometry_wkt.to_numpy())).representative_point()
    lon, lat = project(center.x, center.y)
    return pdk.Deck(
        layers=[
            pdk.Layer(
                "GeoJsonLayer",
                {"type": "FeatureCollection", "features": features},
                pickable=True,
                get_fill_color="properties.color",
                get_line_color=[25, 70, 90],
                line_width_min_pixels=1,
            )
        ],
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom),
        map_style=None,
        tooltip={"text": "{name} · {id}"},
    )


def render_municipality(code, name):
    from .energy_view import render_energy_region

    render_energy_region(code)
    st.markdown(f"**{name} · Parcelas y objetos BU**")
    if code == "28079":
        st.info(
            "Catastro, CEEE y eventos disponibles en «Madrid capital», con sus 21 distritos y fichas completas."
        )
        return
    root = partition_path(code)
    if not (root / "manifest.json").exists():
        st.info("CP/BU sin procesar. No hay ficha catastral disponible para este municipio.")
        return
    try:
        sig = token(root)
        refs = parcel_index(str(root), sig).parcel_ref14.drop_duplicates().sort_values().tolist()
        if not refs:
            st.warning("No hay parcelas con referencia y geometría utilizables en esta captura.")
            return
        metadata = partition_info(str(root), sig)
        if metadata.get("quality_status") == "review_required":
            st.warning(
                f"Objetos con incidencias conservadas: {metadata.get('cp_issues', 0)} CP y {metadata.get('bu_issues', 0)} BU. Los no utilizables se excluyen del cruce y del mapa."
            )
        ref = st.selectbox("Parcela catastral · RC14", refs, key="regional_parcel")
        from .energy_view import render_energy_parcel

        render_energy_parcel(code, ref)
        cp = parcel_objects(str(root), sig, ref, "cp")
        bu = parcel_objects(str(root), sig, ref, "bu")
        zoom = st.slider("Detalle del mapa municipal", 10, 19, 17)
        usable_cp = cp[cp.usable_geometry] if "usable_geometry" in cp else cp
        if usable_cp.empty:
            st.warning("La selección no tiene geometría utilizable; consultar las incidencias.")
            return
        center = sh.from_wkt(usable_cp.geometry_wkt.iloc[0]).representative_point()
        nearby, truncated = map_parcels(str(root), sig, center.x, center.y, zoom)
        st.pydeck_chart(geometry_deck(nearby, "parcel_ref14", zoom), key="regional-map")
        if truncated:
            st.caption(
                "Límite de 1.500 parcelas visibles; aumenta el detalle o selecciona otra RC14."
            )
        usable_bu = bu[bu.usable_geometry] if "usable_geometry" in bu else bu
        if st.checkbox("Mostrar objetos BU de la parcela") and not usable_bu.empty:
            st.pydeck_chart(geometry_deck(usable_bu, "building_id", 18))
        st.write(
            f"{len(cp)} objetos CP · {len(bu)} objetos BU. No equivalen a edificios físicos o viviendas."
        )
        with st.expander("Información catastral de la selección"):
            st.dataframe(cp.drop(columns=["geometry_wkt"]), hide_index=True)
            st.dataframe(bu.drop(columns=["geometry_wkt"]), hide_index=True)
        if exposure_enabled():
            regional = regional_root_path()
            if (regional / "manifest.json").exists():
                manifest = json.loads((regional / "manifest.json").read_text())
                path = regional / "grant_parcel_links.parquet"
                if digest(path) != manifest["outputs"][path.name]:
                    raise ValueError("Relaciones PRTR alteradas")
                scope = (
                    "geographic_municipality_code"
                    if "geographic_municipality_code" in ds.dataset(path).schema.names
                    else "municipality_code"
                )
                linked = pd.read_parquet(
                    path, filters=[("parcel_ref14", "==", ref), (scope, "==", code)]
                )
                confirmed = linked[
                    linked.match_status.isin(
                        ["confirmed", "confirmed_reference", "confirmed_historical_madrid"]
                    )
                ]
                st.write(
                    f"{confirmed.expediente_id.nunique()} expedientes PRTR con relación catastral confirmada."
                )
                candidate_path = regional / "grant_spatial_candidates.parquet"
                if candidate_path.exists():
                    if digest(candidate_path) != manifest["outputs"][candidate_path.name]:
                        raise ValueError("Candidatos PRTR alterados")
                    candidates = pd.read_parquet(
                        candidate_path,
                        filters=[
                            ("parcel_ref14", "==", ref),
                            ("geographic_municipality_code", "==", code),
                        ],
                    )
                    linked = pd.concat([linked, candidates], ignore_index=True)
                if not linked.empty:
                    data = read_view()
                    if data is not None:
                        details = linked[["expediente_id", "match_status"]].merge(
                            data[1][["expediente_id", "programa", "importe_concedido"]],
                            on="expediente_id",
                            validate="many_to_one",
                        )
                        details["match_status"] = details.match_status.replace(
                            {
                                "confirmed": "Referencia y geometría concordantes",
                                "confirmed_reference": "Referencia exacta; sin contraste espacial",
                                "confirmed_historical_madrid": "Confirmación histórica Madrid",
                                "spatial_candidate": "Posible por posición; sin confirmación documental",
                                "ambiguous_spatial": "Posición ambigua",
                                "ambiguous": "Referencia ambigua",
                                "contradictory": "Contradicción",
                                "not_found": "Referencia no encontrada",
                                "unusable_cp": "Parcela en revisión",
                            }
                        )
                        st.dataframe(
                            details.rename(
                                columns={
                                    "expediente_id": "Expediente",
                                    "match_status": "Evidencia",
                                    "programa": "Programa",
                                    "importe_concedido": "Concesión del expediente (€)",
                                }
                            ),
                            hide_index=True,
                        )
                        st.caption(
                            "Importe del expediente, sin reparto entre parcelas. Esta tabla no debe sumarse entre fichas."
                        )
    except (OSError, KeyError, ValueError) as exc:
        st.error(f"Partición no verificable: {exc}")


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
        cp_codes = {"28079"}
        for pilot in ["28065", "28092", "28074", "28007", "28005"]:
            path = partition_path(pilot)
            if (path / "manifest.json").exists():
                info = partition_info(str(path), token(path))
                if (
                    info.get("cp_usable", info["cp_rows"]) > 0
                    and info.get("bu_usable", info["bu_objects"]) > 0
                ):
                    cp_codes.add(pilot)
        c.metric("Municipios con CP/BU integrado", len(cp_codes))
        if municipalities is None:
            st.warning(
                "Inventario Catastro de 179 municipios. Catálogo INE completo y límites pendientes de descarga; no hay clasificación espacial regional validada."
            )
            names = resources.set_index("cadastre_code").cadastre_name.to_dict()
            selected = st.selectbox(
                "Municipio · identificador Catastro, INE pendiente",
                ["all"] + sorted(names, key=names.get),
                format_func=lambda key: "Comunidad de Madrid · toda la captura"
                if key == "all"
                else f"{names[key]} · Catastro {key}",
                key="regional_municipality",
            )
            code = "28079" if selected == "28900" else None
            name = names.get(selected, "Comunidad de Madrid")
        else:
            municipalities = municipalities.copy()
            municipalities["cp_ready"] = municipalities.municipality_code.isin(cp_codes)
            names = municipalities.set_index("municipality_code")["name"].to_dict()
            selected = st.selectbox(
                "Municipio · código INE",
                ["all"] + sorted(names, key=names.get),
                format_func=lambda key: "Comunidad de Madrid"
                if key == "all"
                else f"{names[key]} · {key}",
                key="regional_municipality",
            )
            code, name = (
                (None if selected == "all" else selected),
                names.get(selected, "Comunidad de Madrid"),
            )
            st.pydeck_chart(
                geometry_deck(
                    municipalities
                    if code is None
                    else municipalities[municipalities.municipality_code.eq(code)],
                    "municipality_code",
                )
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
