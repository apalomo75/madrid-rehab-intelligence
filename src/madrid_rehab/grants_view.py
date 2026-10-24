"""Vistas PRTR locales; proyección explícita sin microdatos territoriales ni raw_json."""

import json
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from .grants import DEFAULT, VERSION
from .ingest import digest
from .profiles import csv_export

COLUMNS = [
    "expediente_id",
    "programa",
    "subprograma",
    "importe_concedido",
    "fase",
    "etapa_administrativa",
    "fecha_concesion",
    "municipality_code",
    "territorial_quality",
    "district_code",
    "tipo_edificio",
    "ano_construccion",
    "numero_viviendas",
    "superficie",
    "actuacion",
    "datos_energeticos",
    "multiparcela",
    "calidad",
    "origen",
    "fecha_actualizacion",
    "fecha_captura",
    "version",
]
NOTICE = (
    "Concesión registrada: no acredita pago ni ejecución. P4 corresponde a viviendas y no se extiende al edificio. "
    "La parcela no identifica edificio físico. Las viviendas y superficies declaradas pueden repetirse entre expedientes. "
    "La ausencia de registro no demuestra ausencia de ayudas. Reutilización pendiente de verificar: uso local."
)
LABELS = {
    "district_code": "Distrito",
    "expediente_id": "Expediente",
    "importe_concedido": "Ayuda concedida (€)",
    "importe": "Ayuda concedida (€)",
    "programa": "Programa",
    "subprograma": "Modalidad",
    "municipality_code": "Código INE",
    "territorial_quality": "Calidad territorial",
    "expedientes": "Expedientes",
    "match_status": "Calidad de vinculación",
    "parcel_ref14": "Referencia de parcela",
    "distance_m": "Distancia a parcela (m)",
}
QUALITY_LABELS = {
    "madrid_confirmed": "Vinculación confirmada en Madrid",
    "territorial_candidate": "Pendiente de asignación municipal",
    "contradictory": "Contradicción pendiente de revisión",
    "unassigned": "Sin asignación",
    "confirmed": "Confirmada",
    "regional_cp_pending": "Cobertura CP pendiente",
    "ambiguous_cp": "Referencia CP ambigua",
}


def euros(value):
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def readable(frame):
    result = frame.copy()
    for field in ["territorial_quality", "match_status"]:
        if field in result:
            result[field] = result[field].replace(QUALITY_LABELS)
    for field in ["importe_concedido", "importe"]:
        if field in result:
            result[field] = result[field].map(lambda v: euros(v) if pd.notna(v) else "Sin dato")
    return result.rename(columns=LABELS)


def grant_table(frame):
    fields = [
        "expediente_id",
        "programa",
        "importe_concedido",
        "district_code",
        "territorial_quality",
    ]
    st.dataframe(readable(frame.reindex(columns=fields)), hide_index=True, width="stretch")
    with st.expander("Análisis técnico · campos originales disponibles"):
        st.dataframe(frame.reindex(columns=COLUMNS), hide_index=True, width="stretch")


def root_path():
    return Path(os.environ.get("MADRID_REHAB_GRANTS_DIR", str(DEFAULT))).resolve()


def exposure_enabled():
    return os.environ.get("MADRID_REHAB_PUBLIC", "0") != "1"


def signature(root):
    paths = [
        Path(root) / n
        for n in ["grant_source_manifest.json", "grants.parquet", "grant_parcel_links.parquet"]
    ]
    return tuple(
        (p.name, p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
    )


@st.cache_data(show_spinner=False, max_entries=3)
def load(root, token):
    root = Path(root)
    if signature(root) != token:
        raise ValueError("Captura cambiada")
    metadata = json.loads((root / "grant_source_manifest.json").read_text())
    if metadata["version"] != VERSION:
        raise ValueError("Versión PRTR no soportada")
    city = Path(os.environ.get("MADRID_REHAB_SESSION7_DIR", "data/processed/session_7_final"))
    if (
        json.loads((city / "manifest.json").read_text())["inputs"]["parcels_audited"]
        != metadata["cp_sha256"]
    ):
        raise ValueError("Captura PRTR corresponde a otro CP municipal")
    for name in ["grants.parquet", "grant_parcel_links.parquet"]:
        if digest(root / name) != metadata["outputs"][name]:
            raise ValueError("Producto PRTR alterado")
    frame = pd.read_parquet(
        root / "grants.parquet",
        columns=COLUMNS + ["geometry_valid", "longitude", "latitude", "identity_conflict"],
    )
    links = pd.read_parquet(root / "grant_parcel_links.parquet")
    if signature(root) != token:
        raise ValueError("Captura cambió durante lectura")
    return metadata, frame, links


def filter_grants(frame, programs=None, minimum=None, maximum=None, years=None, quality=None):
    result = frame
    if programs is not None:
        result = result[result.programa.isin(programs)]
    if minimum is not None:
        result = result[result.importe_concedido.ge(minimum)]
    if maximum is not None:
        result = result[result.importe_concedido.le(maximum)]
    if years is not None:
        result = result[result.ano_construccion.between(*years)]
    if quality is not None:
        result = result[result.territorial_quality.isin(quality)]
    return result


def parcel_grants(ref, frame, links):
    ids = links.loc[
        links.parcel_ref14.eq(ref) & links.match_status.eq("confirmed"), "expediente_id"
    ]
    selected = frame[frame.expediente_id.isin(ids)]
    if "territorial_quality" in selected:
        selected = selected[~selected.territorial_quality.eq("contradictory")]
    return selected.drop_duplicates("expediente_id")


def safe_export(frame):
    return csv_export(frame.reindex(columns=COLUMNS))


def read_view():
    root = root_path()
    if not exposure_enabled():
        st.info("Exposición PRTR desactivada en modo público: licencia sin verificar.")
        return None
    if not (root / "grant_source_manifest.json").exists():
        st.info("Captura PRTR no disponible. Ejecuta python -m madrid_rehab.grants.")
        return None
    try:
        return load(str(root), signature(root))
    except (OSError, KeyError, ValueError) as exc:
        st.error(f"Captura PRTR no verificable: {exc}")
        return None


def render_parcel_grants(ref):
    data = read_view()
    if data is None:
        return
    _, frame, links = data
    selected = parcel_grants(ref, frame, links)
    st.markdown("**Subvenciones PRTR confirmadas en esta parcela**")
    st.caption(NOTICE)
    if selected.empty:
        st.info("Sin concesiones localizadas en esta captura.")
    else:
        st.write(
            f"{len(selected)} expedientes distintos asociados; no son necesariamente obras distintas."
        )
        grant_table(selected)
        st.dataframe(
            links[links.parcel_ref14.eq(ref) & links.match_status.eq("confirmed")], hide_index=True
        )


def render_grants(regional=False, district=None):
    st.subheader(
        "Comunidad de Madrid — Subvenciones" if regional else "Subvenciones PRTR · Madrid capital"
    )
    st.caption(NOTICE)
    data = read_view()
    if data is None:
        return
    metadata, frame, links = data
    if regional:
        st.warning(
            "Sin límites municipales oficiales descargados: clasificación regional incompleta. No se dispone de CP/BU regional fuera de Madrid capital."
        )
        st.dataframe(
            frame.groupby(["territorial_quality", "programa"])
            .agg(expedientes=("expediente_id", "nunique"), importe=("importe_concedido", "sum"))
            .reset_index(),
            hide_index=True,
        )
        st.markdown("**Municipios confirmados en la captura integrada**")
        confirmed = frame[frame.municipality_code.notna()]
        st.dataframe(
            confirmed.groupby("municipality_code")
            .agg(expedientes=("expediente_id", "nunique"), importe=("importe_concedido", "sum"))
            .reset_index(),
            hide_index=True,
        )
        scope = st.selectbox(
            "Territorio PRTR",
            ["Toda la captura regional", "Madrid confirmado", "Pendiente o contradictorio"],
        )
        if scope == "Madrid confirmado":
            frame = frame[frame.territorial_quality.eq("madrid_confirmed")]
        elif scope == "Pendiente o contradictorio":
            frame = frame[~frame.territorial_quality.eq("madrid_confirmed")]
    else:
        frame = frame[frame.territorial_quality.eq("madrid_confirmed")]
        if district is not None:
            frame = frame[frame.district_code.eq(district)]
    prefix = "regional_prtr" if regional else f"city_prtr_{district}"
    programs = st.multiselect(
        "Programa PRTR",
        ["P1", "P3", "P4", "P5"],
        default=["P1", "P3", "P4", "P5"],
        key=prefix + "program",
    )
    minimum = st.number_input(
        "Importe mínimo concedido (€)", min_value=0.0, value=0.0, key=prefix + "min"
    )
    maximum = st.number_input(
        "Importe máximo concedido (€)",
        min_value=0.0,
        value=float(frame.importe_concedido.max()) if not frame.empty else 0.0,
        key=prefix + "max",
    )
    qualities = st.multiselect(
        "Calidad territorial PRTR",
        sorted(frame.territorial_quality.unique()),
        default=sorted(frame.territorial_quality.unique()),
        format_func=lambda value: QUALITY_LABELS.get(value, value),
        key=prefix + "quality",
    )
    st.caption(
        "Tipología de inmueble y medidas energéticas individuales no disponibles en el GeoJSON; no se infieren del programa ni de variables censales."
    )
    year_filter = st.checkbox("Filtrar año constructivo declarado válido", key=prefix + "use_year")
    years = (
        st.slider("Año constructivo PRTR", 1600, 2026, (1600, 2026), key=prefix + "years")
        if year_filter
        else None
    )
    selected = filter_grants(frame, programs, minimum, maximum, years, qualities)
    a, b, c = st.columns(3)
    a.metric("Expedientes únicos", selected.expediente_id.nunique())
    b.metric("Importe concedido (€)", euros(selected.importe_concedido.sum()))
    c.metric(
        "Mediana por expediente (€)",
        euros(selected.importe_concedido.median()) if not selected.empty else "Sin datos",
    )
    st.bar_chart(selected.groupby("programa").importe_concedido.sum())
    if not regional:
        st.dataframe(
            readable(
                selected.groupby(["district_code", "programa"], dropna=False)
                .agg(expedientes=("expediente_id", "nunique"), importe=("importe_concedido", "sum"))
                .reset_index()
            ),
            hide_index=True,
        )
    grant_table(selected)
    st.download_button(
        "CSV PRTR seguro · selección local",
        safe_export(selected),
        "prtr_seleccion.csv",
        "text/csv",
        key=prefix + "csv",
    )
    st.caption(
        f"Fuente {metadata['source_url']} · actualización indicada {metadata['source_update']} · captura {metadata['capture_date']}. Importes contados por expediente, sin reparto multiparcela."
    )


def benchmark_views(root=DEFAULT):
    start = time.perf_counter()
    _, frame, links = load(str(root), signature(root))
    loaded = time.perf_counter()
    district = frame[frame.district_code.eq("07")]
    detailed = time.perf_counter()
    filter_grants(frame, ["P3"], 0, 1_000_000)
    end = time.perf_counter()
    return dict(
        regional_load_s=loaded - start,
        district_select_s=detailed - loaded,
        filter_s=end - detailed,
        dataframe_mib=(frame.memory_usage(deep=True).sum() + links.memory_usage(deep=True).sum())
        / 1024**2,
        chamberi_expedientes=len(district),
    )
