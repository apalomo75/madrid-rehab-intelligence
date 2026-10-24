"""Vista de eventos reales particionada por distrito, con caché e integridad."""

import json
import os
import time
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from .administrative import DEFAULT, VERSION
from .ingest import digest
from .profiles import csv_export

PUBLIC_COLUMNS = [
    "event_id",
    "event_type",
    "original_id",
    "date",
    "origin_date",
    "date_raw",
    "year",
    "query_date",
    "address_raw",
    "address_normalized",
    "district_code",
    "parcel_ref14",
    "match_status",
    "match_level",
    "match_method",
    "administrative_status",
    "category",
    "description",
    "source_file",
    "source_row",
    "page",
    "quality_flags",
    "identity_conflict",
]
LABELS = {
    "order": "Órdenes de conservación",
    "license": "Licencias urbanísticas",
    "declaration": "Declaraciones responsables",
    "ite_pending": "Obligaciones ITE pendientes según consulta oficial",
    "iee_pending": "Obligaciones IEE pendientes según consulta oficial",
}
COLORS = {
    "order": [215, 75, 55, 190],
    "license": [50, 115, 210, 190],
    "declaration": [140, 80, 190, 190],
    "ite_pending": [225, 160, 30, 190],
    "iee_pending": [25, 155, 130, 190],
}
NOTICE = (
    "La vinculación acredita parcela, no edificio físico. Licencias y declaraciones no acreditan obras ejecutadas; "
    "las órdenes no son diagnósticos actuales. Obligaciones pendientes describen una consulta, sin resultado favorable/desfavorable "
    "ni declaración automática de infracción. La ausencia de registros no demuestra ausencia de actuaciones. "
    "Licencia de reutilización de los archivos aportados pendiente de verificación; uso local."
)


def root_path():
    return Path(os.environ.get("MADRID_REHAB_ADMIN_DIR", str(DEFAULT))).resolve()


def token(root, code=None):
    root = Path(root)
    paths = [root / "manifest.json"]
    if code is not None:
        paths.append(root / "districts" / code / "events.parquet")
    return tuple(
        (str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns)
        for p in paths
    )


def read_partition(root, code, signature):
    if code not in {f"{i:02}" for i in range(1, 22)} | {"unknown"}:
        raise ValueError("Distrito no admitido")
    root = Path(root)
    if token(root, code) != signature:
        raise ValueError("Captura cambiada")
    m = json.loads((root / "manifest.json").read_text())
    if m["version"] != VERSION:
        raise ValueError("Versión no soportada")
    path = root / "districts" / code / "events.parquet"
    name = str(path.relative_to(root))
    if digest(path) != m["outputs"][name]:
        raise ValueError("Partición administrativa alterada")
    frame = pd.read_parquet(path, columns=PUBLIC_COLUMNS)
    if token(root, code) != signature:
        raise ValueError("Captura cambió durante lectura")
    return frame


@st.cache_data(show_spinner=False, max_entries=5)
def cached_partition(root, code, signature):
    return read_partition(root, code, signature)


@st.cache_data(show_spinner=False, max_entries=3)
def cached_summary(root, signature):
    root = Path(root)
    m = json.loads((root / "manifest.json").read_text())
    if m["version"] != VERSION:
        raise ValueError("Versión no soportada")
    for name in ["district_summary.parquet", "time_summary.parquet"]:
        if digest(root / name) != m["outputs"][name]:
            raise ValueError("Agregado alterado")
    if token(root) != signature:
        raise ValueError("Captura cambiada")
    return (
        m,
        pd.read_parquet(root / "district_summary.parquet"),
        pd.read_parquet(root / "time_summary.parquet"),
    )


def filter_events(frame, filters):
    out = frame
    for col, values in filters.items():
        out = out[out[col].isin(values)]
    return out


def validate_cp_snapshot(metadata):
    city = Path(
        os.environ.get(
            "MADRID_REHAB_SESSION7_DIR",
            str(Path(__file__).resolve().parents[2] / "data/processed/session_7_final"),
        )
    )
    declared = json.loads((city / "manifest.json").read_text())
    if metadata["cp_sha256"] != declared["inputs"]["parcels_audited"]:
        raise ValueError("La captura administrativa corresponde a otro Catastro CP")


def parcel_events(ref, district=None):
    root = root_path()
    if not (root / "manifest.json").exists():
        return None
    metadata, _, _ = cached_summary(str(root), token(root))
    validate_cp_snapshot(metadata)
    # RC que no tiene distrito único no se presenta como localizada por uno declarado.
    if district not in {f"{i:02}" for i in range(1, 22)}:
        return pd.DataFrame(columns=PUBLIC_COLUMNS)
    frame = cached_partition(str(root), district, token(root, district))
    return frame[frame.parcel_ref14.eq(ref) & frame.match_status.eq("confirmed")]


def render_parcel_events(ref, district=None):
    st.markdown("**Eventos administrativos asociados**")
    try:
        frame = parcel_events(ref, district)
    except (OSError, ValueError, KeyError) as exc:
        st.warning(f"No se puede verificar la captura administrativa: {exc}")
        return
    if frame is None:
        st.caption("Captura administrativa no disponible.")
        return
    if frame.empty:
        st.info("No se han localizado eventos en las fuentes integradas")
    else:
        st.dataframe(frame, hide_index=True, width="stretch")
    st.caption(NOTICE)


def render_activity(district=None, parcels=None, zone=None):
    root = root_path()
    if not (root / "manifest.json").exists():
        st.info(
            "Genera la captura local: PYTHONPATH=src .venv/bin/python -m madrid_rehab.administrative"
        )
        return
    try:
        m, summary, temporal = cached_summary(str(root), token(root))
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Captura administrativa no verificable: {exc}")
        return
    try:
        validate_cp_snapshot(m)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Capturas incompatibles: {exc}")
        return
    st.subheader("Actividad y rehabilitación")
    st.caption(NOTICE)
    st.caption(
        "Obligaciones ITE/IEE pendientes según consulta oficial · filtros independientes de los energéticos."
    )
    st.info(
        "Subvenciones: disponible una convocatoria BOCM de 2022; no hay concesiones individuales integradas."
    )
    if district is None:
        st.write(
            f"{m['unique_event_ids']:,} identidades administrativas observadas; {m['rows']:,} versiones conservadas."
        )
        st.dataframe(summary, hide_index=True, width="stretch")
        st.bar_chart(temporal.groupby(["year", "event_type"]).events.sum().unstack(fill_value=0))
        st.download_button(
            "Exportar resumen administrativo municipal",
            csv_export(summary),
            "actividad_madrid.csv",
            "text/csv",
        )
        district = st.selectbox(
            "Distrito de actividad administrativa",
            [""] + [f"{i:02}" for i in range(1, 22)] + ["unknown"],
            format_func=lambda v: "Selecciona distrito"
            if not v
            else "Sin distrito"
            if v == "unknown"
            else v,
            key="admin_municipal_district",
        )
        if not district:
            return
    try:
        frame = cached_partition(str(root), district, token(root, district))
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"No se puede leer el distrito administrativo: {exc}")
        return
    prefix = "admin_" + district
    filters = {}
    labels = {
        "source_file": "Fuente",
        "event_type": "Tipo de evento",
        "year": "Periodo (año de registro o de obligación)",
        "category": "Categoría",
        "match_status": "Nivel de vinculación",
        "administrative_status": "Estado administrativo",
    }
    with st.expander("Filtros de actividad administrativa", expanded=False):
        for col, label in labels.items():
            values = sorted(frame[col].fillna("").unique())
            filters[col] = st.multiselect(
                label,
                values,
                default=values,
                key=prefix + col,
                format_func=lambda v: LABELS.get(v, v) or "Sin fecha/categoría",
            )
    chosen = filter_events(frame, filters)
    confirmed = chosen[chosen.match_status.eq("confirmed")]
    a, b, c, d = st.columns(4)
    a.metric("Expedientes/obligaciones observados", chosen.event_id.nunique())
    b.metric("Parcelas vinculadas inequívocamente", confirmed.parcel_ref14.nunique())
    c.metric("Versiones sin vínculo inequívoco", len(chosen) - len(confirmed))
    counts = confirmed.groupby("parcel_ref14").event_id.nunique()
    d.metric("Parcelas con varios eventos", int(counts.gt(1).sum()))
    st.caption(
        "Conteos de la captura filtrada; periodo de obligación y fecha de consulta son distintos. No son tasas del parque ni edificios afectados."
    )
    if chosen.empty:
        st.info("No hay eventos con esta combinación de filtros.")
        return
    st.bar_chart(chosen.groupby(["year", "event_type"]).event_id.nunique().unstack(fill_value=0))
    st.dataframe(chosen, hide_index=True, width="stretch")
    st.download_button(
        "Exportar eventos administrativos filtrados",
        csv_export(chosen),
        "eventos_administrativos.csv",
        "text/csv",
        key=prefix + "download",
    )
    if parcels is not None and zone is not None:
        if st.checkbox("Mostrar eventos confirmados de la celda", key=prefix + "map"):
            # Usa solo CP ya limitadas por el visor, una geometría por RC; no dibuja candidatos.
            selected = parcels[parcels.map_zone.eq(zone)].head(2500)
            event_map = confirmed[["parcel_ref14", "event_type"]].drop_duplicates()
            selected = selected.merge(event_map, on="parcel_ref14", how="inner").head(2500)
            selected = selected.drop_duplicates(["parcel_ref14", "event_type"])
            if selected.empty:
                st.info("Sin eventos confirmados en las parcelas de esta celda.")
            else:
                layers = []
                for typ, g in selected.groupby("event_type"):
                    features = [
                        {
                            "type": "Feature",
                            "geometry": json.loads(r.geometry_geojson),
                            "properties": {
                                "parcel_ref14": r.parcel_ref14,
                                "event_type": LABELS.get(typ, typ),
                            },
                        }
                        for r in g.itertuples()
                    ]
                    layers.append(
                        pdk.Layer(
                            "GeoJsonLayer",
                            {"type": "FeatureCollection", "features": features},
                            id="admin-" + typ,
                            get_fill_color=COLORS.get(typ, [100, 100, 100, 180]),
                            get_line_color=[255, 255, 255],
                            pickable=True,
                        )
                    )
                geom = json.loads(selected.iloc[0].geometry_geojson)
                from shapely.geometry import shape

                center = shape(geom).representative_point()
                st.pydeck_chart(
                    pdk.Deck(
                        layers=layers,
                        initial_view_state=pdk.ViewState(
                            longitude=center.x, latitude=center.y, zoom=15
                        ),
                        map_style=None,
                        tooltip={"text": "{parcel_ref14}\n{event_type}"},
                    )
                )
                st.caption(
                    "Celda seleccionada; máximo 2.500 geometrías. Rojo: órdenes; azul: licencias; violeta: declaraciones; amarillo: ITE; verde: IEE. Parcelas con varios tipos se superponen. Sin atribución a BU."
                )
    else:
        st.caption(
            "Para cartografía de eventos, abre un distrito y selecciona una celda catastral."
        )


def benchmark(root, code="07"):
    t = time.perf_counter()
    frame = read_partition(root, code, token(root, code))
    cold = time.perf_counter() - t
    t = time.perf_counter()
    cached_partition(str(root), code, token(root, code))
    warm = []
    for _ in range(5):
        t = time.perf_counter()
        cached_partition(str(root), code, token(root, code))
        warm.append(time.perf_counter() - t)
    return {
        "district": code,
        "rows": len(frame),
        "verified_partition_s": cold,
        "cached_s": warm,
        "dataframe_mib": frame.memory_usage(deep=True).sum() / 1024**2,
    }
