"""Local demonstration using immutable, verified snapshots; no network access."""

import html
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from .ingest import digest

ENERGY = Path("data/processed/energy/session_13_final_03")
CONSERVATION = Path("data/processed/conservation/session_14_final_02")
CADASTRE = Path("data/processed/cadastre/session_12_2_partial_validated_01")
TERRITORY = Path("data/processed/territory/session_12_1_final_01")
CITY = Path("data/processed/session_2")
CASES = {
    "Madrid · energía y órdenes históricas": ("28079", "0010510VK4701A"),
    "Alcalá de Henares · energía y ayuda": ("28005", "0015301VK7801N"),
    "Getafe · energía y Catastro parcial": ("28065", "0036104VK4603N"),
}
NOTICE = (
    "Información orientativa basada en fuentes públicas, no certificación oficial. "
    "Una parcela no equivale a un edificio. Ausencia de evidencia no significa estado favorable. "
    "Las observaciones individuales no califican el edificio. Sin diagnóstico ni score financiero."
)
REC = "https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons"


def private():
    return os.environ.get("MADRID_REHAB_PUBLIC", "0") != "1"


@st.cache_data(max_entries=48, show_spinner=False)
def _read(root, relative, token, filters, columns):
    root = Path(root)
    manifest = json.loads(((CONSERVATION if root == CITY else root) / "manifest.json").read_text())
    expected = manifest.get("outputs", {}).get(relative)
    if expected is None and root == CITY and relative == "parcels_audited.parquet":
        expected = json.loads((CONSERVATION / "manifest.json").read_text())["cp_sha256"]
    if root == CITY and relative == "buildings_audited.parquet":
        metadata = json.loads(
            (Path("data/processed/session_7_final") / "manifest.json").read_text()
        )
        expected = metadata["inputs"]["buildings_audited"]
    if not expected or digest(root / relative) != expected:
        raise ValueError("Fuente alterada o sin hash acreditado: " + relative)
    return pd.read_parquet(root / relative, filters=filters, columns=columns)


def read(root, relative, filters=None, columns=None):
    paths = [(CONSERVATION if root == CITY else root) / "manifest.json", root / relative]
    if root == CITY and relative == "buildings_audited.parquet":
        paths.append(Path("data/processed/session_7_final/manifest.json"))
    token = tuple((p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths)
    return _read(str(root), relative, token, filters, columns)


def municipalities():
    return read(TERRITORY, "municipality_boundaries.parquet", columns=["municipality_code", "name"])


def cp_source(code):
    override = os.environ.get("MADRID_REHAB_CADASTRE_DIR")
    if override and code != "28079":
        return Path(override) / code, "cp.parquet"
    return (
        (CITY, "parcels_audited.parquet") if code == "28079" else (CADASTRE, f"{code}/cp.parquet")
    )


def parcel(code, ref):
    root, relative = cp_source(code)
    if not (root / relative).exists():
        return pd.DataFrame()
    result = read(root, relative, [("parcel_ref14", "==", ref)])
    # Never collapse conflicting identities, even if one row has usable geometry.
    if len(result) != 1 or not bool(result.iloc[0].usable_geometry):
        return pd.DataFrame()
    return result


def evidence(code, ref):
    if not private():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    from . import conservation_view, energy_view

    part = f"municipalities/{code}/links.parquet"
    links = energy_view.read(part, ref=ref)
    links = links[links.link_level.eq("A")]
    cert = pd.DataFrame()
    if not links.empty:
        cert = energy_view.read(
            f"municipalities/{code}/certificates.parquet", ids=tuple(links.certificate_id.unique())
        )
    events = conservation_view.parcel_evidence(ref, municipality=code)
    accesses = conservation_view.parcel_evidence(ref, "accesses", code)
    joint = energy_view.read("energy_grants_summary.parquet", ref=ref)
    joint = joint[joint.municipality_code.eq(code)]
    return (
        cert,
        events if events is not None else pd.DataFrame(),
        accesses if accesses is not None else pd.DataFrame(),
        joint,
    )


def export_html(code, name, ref, cp, cert=None, events=None, grants=None):
    """Allowlisted redistributable identification only, in both public/private modes.

    The optional evidence arguments are deliberately excluded until reuse is reviewed.
    """
    if cp.empty or len(cp) != 1 or not bool(cp.iloc[0].usable_geometry):
        raise ValueError("Identificación catastral no confirmada")

    def esc(value):
        return html.escape(str(value), quote=True)

    return f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>Ficha {esc(ref)}</title>
<style>body{{font:16px system-ui;max-width:850px;margin:3rem auto;line-height:1.6}}h1{{color:#17495b}}</style>
<h1>Madrid Rehab Intelligence</h1><p>Ficha de consulta · {esc(name)} ({esc(code)})</p>
<h2>{esc(ref)}</h2><p>Objeto: parcela catastral. Geometría disponible. Identificación documental en captura local.</p>
<h2>Energía, conservación y ayudas</h2><p>Evidencias excluidas de la exportación: revisión específica de redistribución pendiente. Resultado ITE/IEE no disponible en las fuentes integradas.</p>
<h2>Fuentes y fecha</h2><p>Dirección General del Catastro, servicio INSPIRE. Referencia de captura: {esc(cp_source(code)[0])}. Fecha de generación: {esc(pd.Timestamp.now(tz="UTC").isoformat())}.</p>
<p>Dirección y año de construcción no incluidos. La fecha de generación no es la fecha de actualización de la fuente.</p>
<p>{esc(NOTICE)}</p>{f'<a href="{REC}">Consulta oficial REC (Madrid)</a>' if code == "28079" else ""}</html>"""


def verified_json(root, relative):
    manifest = json.loads((root / "manifest.json").read_text())
    if digest(root / relative) != manifest["outputs"][relative]:
        raise ValueError("Metadatos alterados")
    return json.loads((root / relative).read_text())


def research_refs(code, signal):
    if not private():
        return []
    joint = read(ENERGY, "energy_grants_summary.parquet", [("municipality_code", "==", code)])
    if signal == "CEEE y PRTR":
        result = joint[(joint.certificate_count > 0) & (joint.grant_case_count > 0)]
    elif signal == "Órdenes históricas (Madrid)":
        if code != "28079":
            return []
        result = read(
            CONSERVATION,
            "conservation_evidence_profile.parquet",
            [("historical_order_count", ">", 0)],
            ["parcel_ref14"],
        )
    elif signal == "Letras E/F/G observadas":
        links = read(
            ENERGY,
            f"municipalities/{code}/links.parquet",
            [("link_level", "==", "A")],
            ["certificate_id", "parcel_ref14"],
        )
        cert = read(
            ENERGY,
            f"municipalities/{code}/certificates.parquet",
            columns=["certificate_id", "consumption_rating"],
        )
        result = links.merge(cert[cert.consumption_rating.isin(list("EFG"))], on="certificate_id")
    else:
        result = joint[joint.certificate_count > 0]
    return sorted(result.parcel_ref14.dropna().unique())


def render():
    st.title("Madrid Rehab Intelligence")
    st.caption("Inteligencia territorial para el análisis de rehabilitación de edificios")
    st.write(
        "Integramos información pública de edificios, eficiencia energética, subvenciones y antecedentes administrativos para facilitar la investigación de oportunidades de rehabilitación"
    )
    st.caption(
        "Proyecto personal independiente · Demostración local · No afiliado a una entidad financiera"
    )
    try:
        from .municipal_navigation import covered_municipalities

        towns = covered_municipalities().sort_values("name")
        with st.expander("Cobertura y fuentes de la captura"):
            summary = read(ENERGY, "energy_municipality_summary.parquet") if private() else None
            cols = st.columns(3)
            cols[0].metric("Municipios con límites", len(municipalities()))
            cols[1].metric("Municipios con CP integrada", len(towns))
            cols[2].metric("Cobertura catastral", "Madrid + 5 pilotos parciales")
            st.caption(
                "Corte de demostración: 26/10/2026. 179 municipios con geometría administrativa; no acredita cobertura completa de edificios. Fechas de origen en Fuentes."
            )
            if summary is not None:
                quality = verified_json(ENERGY, "energy_quality.json")
                st.caption(
                    f"Observaciones energéticas vinculadas: {quality['link_counts_distinct_certificates']['A']:,} de {quality['canonical_certificates']:,} contenidos canónicos regionales. Fuente CEEE regional, capturas 2025/2026; no edificios únicos."
                )
                counts = json.loads((CONSERVATION / "manifest.json").read_text())["counts"]
                st.caption(
                    f"Parcelas con antecedentes de conservación: {counts['conservation_parcels']:,} · Madrid capital · obligaciones consultadas 24/10/2026 y órdenes históricas 2018–2026."
                )
                st.caption(
                    "7.532 expedientes PRTR regionales territorializados · captura sesión 12.1 · fecha individual no contrastada. No acredita pago ni obras."
                )
            st.caption(
                "Parcelas: 140.595 referencias distintas en la captura municipal histórica de Madrid y 54.441 CP aceptadas en cinco pilotos parciales. Son denominadores de capturas diferentes, no censo de edificios ni cobertura total regional."
            )
            if not private():
                st.info(
                    "Modo público: energía regional, PRTR y conservación protegidos. Las exportaciones excluyen esas evidencias."
                )
        choice = st.selectbox(
            "Caso real de demostración",
            ["Búsqueda libre", *CASES] if private() else ["Búsqueda libre"],
        )
        chosen_code, chosen_ref = CASES.get(choice, ("28079", ""))
        codes = towns.municipality_code.tolist()
        code = st.selectbox(
            "Municipio",
            codes,
            index=codes.index(chosen_code),
            format_func=lambda v: towns.set_index("municipality_code").loc[v, "name"],
            key="demo_town_" + choice,
            on_change=lambda: st.session_state.update(municipal_show_territories=False),
        )
        name = towns.set_index("municipality_code").loc[code, "name"]
        root, relative = cp_source(code)
        if not (root / relative).exists():
            st.info(
                "Sin Catastro CP integrado para este municipio. No hay parcelas consultables; la ausencia de cobertura no describe el estado de sus edificios."
            )
            return
        st.caption(
            "Búsqueda por referencia catastral urbana RC14. Índice de direcciones regional no disponible; los accesos de Madrid se muestran tras confirmar parcela."
        )
        if private():
            with st.expander("Encontrar candidatos para estudio"):
                signal = st.selectbox(
                    "Evidencias para investigar",
                    [
                        "CEEE y PRTR",
                        "CEEE vinculado",
                        "Letras E/F/G observadas",
                        "Órdenes históricas (Madrid)",
                    ],
                )
                refs = research_refs(code, signal)
                st.caption(
                    f"{len(refs):,} parcelas en estas fuentes; sin ranking ni diagnóstico. Selecciona expresamente una referencia."
                )
                candidate = st.selectbox(
                    "Referencia candidata", refs, index=None, key="demo_candidate_" + code + signal
                )
                if candidate:
                    chosen_ref = candidate
                    chosen_code = code
        from .municipal_navigation import render_explorer

        st.button(
            "Ver municipios en el mapa",
            key="explorer_territories",
            on_click=lambda: st.session_state.update(municipal_show_territories=True),
        )
        if st.session_state.get("municipal_show_territories"):
            from .municipal_navigation import render_territories

            render_territories("demo_town_" + choice)
        else:
            render_explorer(code, name, chosen_ref if code == chosen_code else "")
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"No se puede verificar una fuente local: {exc}")


def render_fiche(code, name, ref, cp):
    from .municipal_fiche import render_fiche as shared_fiche

    shared_fiche(code, name, ref, cp)
