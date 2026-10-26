"""One ordered fiche for municipal parcels and independent cadastral objects."""

import re
import logging
from contextlib import contextmanager

import pandas as pd
import streamlit as st
import shapely as sh

SECTIONS = (
    "Identificación",
    "Características constructivas",
    "Certificados CEEE",
    "Conservación e ITE/IEE",
    "Subvenciones PRTR",
    "Calidad, limitaciones y procedencia",
)
UNAVAILABLE = "No disponible en las fuentes integradas"
CONSTRUCTION_LABELS = {
    "building_id": "Objeto catastral BU",
    "source_feature_type": "Tipo de objeto en origen",
    "current_use": "Uso declarado",
    "construction_begin": "Inicio constructivo declarado",
    "construction_end": "Fin constructivo declarado",
    "construction_oldest_year": "Año inicial declarado",
    "construction_newest_year": "Año final declarado",
    "dwellings_raw": "Viviendas declaradas",
    "building_units_raw": "Unidades declaradas",
}


LOGGER = logging.getLogger(__name__)


@contextmanager
def panel(label, statuses):
    """An auxiliary failure must never abort the remaining cadastral fiche."""
    statuses[label] = "consulta iniciada"
    try:
        yield
        if statuses[label] == "consulta iniciada":
            statuses[label] = "renderizado; disponibilidad indicada en el apartado"
    except Exception as exc:
        LOGGER.exception("Fiche panel failed: %s", label)
        statuses[label] = "error de consulta: " + type(exc).__name__
        st.warning(
            f"{label}: consulta fallida ({type(exc).__name__}). "
            "No se puede determinar la disponibilidad; identificación conservada."
        )


def construction_table(records):
    return records[[c for c in CONSTRUCTION_LABELS if c in records]].rename(
        columns=CONSTRUCTION_LABELS
    )


def render_prtr(code, ref):
    """Reuse the regional authenticated links and case reader, preserving match levels."""
    from . import demo
    from .grants_view import read_view
    from .regional_view import regional_root_path

    root = regional_root_path()
    links = demo.read(root, "grant_parcel_links.parquet", [("parcel_ref14", "==", ref)])
    candidates_path = root / "grant_spatial_candidates.parquet"
    if candidates_path.exists():
        candidates = demo.read(root, candidates_path.name, [("parcel_ref14", "==", ref)])
        links = pd.concat([links, candidates], ignore_index=True)
    scope = (
        "geographic_municipality_code"
        if "geographic_municipality_code" in links
        else "municipality_code"
    )
    links = links[links[scope].eq(code)]
    if links.empty:
        st.info(UNAVAILABLE)
        st.caption(
            "No constan concesiones vinculadas en esta captura; no acredita ausencia real de ayudas."
        )
        return
    data = read_view()
    if data is None:
        st.info(UNAVAILABLE)
        return
    details = (
        links[["expediente_id", "match_status"]]
        .drop_duplicates()
        .merge(
            data[1][["expediente_id", "programa", "importe_concedido"]],
            on="expediente_id",
            validate="many_to_one",
        )
    )
    details["match_status"] = details.match_status.replace(
        {
            "confirmed": "Referencia y geometría concordantes",
            "confirmed_reference": "Referencia documental exacta",
            "confirmed_historical_madrid": "Vínculo histórico Madrid",
            "spatial_candidate": "Candidato espacial sin confirmación",
            "ambiguous": "Referencia ambigua",
            "ambiguous_spatial": "Posición ambigua",
            "contradictory": "Contradicción",
            "unusable_cp": "Parcela en revisión",
            "not_found": "Referencia no localizada",
        }
    )
    st.dataframe(
        details.rename(
            columns={
                "expediente_id": "Expediente",
                "match_status": "Evidencia del vínculo",
                "programa": "Programa",
                "importe_concedido": "Concesión del expediente (€)",
            }
        ),
        hide_index=True,
    )
    st.caption(
        "Concesiones administrativas; no acreditan pago ni obras. El importe pertenece al expediente único y no debe sumarse entre parcelas. La coincidencia con CEEE no acredita causalidad."
    )


def render_fiche(code, name, identifier, objects, kind="cp"):
    from . import demo
    from .municipal_navigation import construction_records

    statuses = {}
    st.session_state["fiche_sections"] = statuses
    st.session_state["fiche_identity"] = (code, kind, identifier)
    row = objects.iloc[0]
    ref = identifier if kind == "cp" else None
    # BU remains independent: a parcel field alone does not document a BU–CP relation.
    conservation_ref = ref if ref and re.fullmatch(r"[0-9]{7}[A-Z]{2}[0-9]{4}[A-Z]", ref) else None
    st.subheader(f"Ficha de {'parcela' if kind == 'cp' else 'objeto BU'} · {identifier}")
    tabs = st.tabs(SECTIONS)
    with tabs[0], panel(SECTIONS[0], statuses):
        st.write(
            f"{name} · {'Parcela catastral CP' if kind == 'cp' else 'Objeto catastral BU independiente'}"
        )
        st.caption(
            "Identificación documental en captura. Parcela, objeto BU, portal y edificio físico son entidades diferentes."
        )
        if kind == "bu":
            st.write(
                f"Referencia de parcela acreditada: {ref}"
                if ref
                else "Relación BU–CP: " + UNAVAILABLE
            )
        st.write(f"Municipio: {code} · Identidad: {identifier}")
        st.caption("Fuente: Dirección General del Catastro · INSPIRE")
        st.write(
            f"Geometría utilizable: {bool(row.get('usable_geometry', False))} · "
            f"Validación: {row.get('selection_status', 'captura histórica auditada')}"
        )
        geometry = row.get("geometry_wkt")
        if isinstance(geometry, str):
            point = sh.from_wkt(geometry).representative_point()
            st.caption(f"Ubicación EPSG:25830: {point.x:.2f}, {point.y:.2f}")
        else:
            st.caption("Ubicación: " + UNAVAILABLE)
        if kind == "bu" and not ref:
            st.caption(
                "Objeto constructivo consultado de forma independiente; no consta una "
                "relación documental confirmada con una parcela de las fuentes integradas"
            )
        if demo.private() and conservation_ref:
            from .conservation_view import parcel_evidence

            accesses = parcel_evidence(ref, "accesses", code)
            if accesses is not None and not accesses.empty:
                labels = {
                    "ndp": "Identificador de portal",
                    "street": "Calle",
                    "number_raw": "Número",
                    "qualifier_raw": "Complemento",
                    "link_status": "Calidad del vínculo",
                }
                st.dataframe(accesses[list(labels)].rename(columns=labels), hide_index=True)
            else:
                st.caption("Accesos y dirección: " + UNAVAILABLE)
        else:
            st.caption("Accesos y dirección: " + UNAVAILABLE)
    with tabs[1], panel(SECTIONS[1], statuses):
        construction = (
            construction_table(objects) if kind == "bu" else construction_records(code, objects)
        )
        if construction.empty:
            st.info(UNAVAILABLE)
            st.caption(
                "Los BU independientes pueden consultarse desde el selector de objetos. No se atribuyen a esta parcela sin relación acreditada."
            )
        else:
            st.dataframe(construction, hide_index=True)
            st.caption(
                "Atributos declarados del registro catastral; no confirman estado físico actual ni identidad de un edificio físico."
            )
    with tabs[2], panel(SECTIONS[2], statuses):
        if demo.private() and ref:
            from .energy_view import render_energy_parcel

            render_energy_parcel(code, ref)
            st.caption(
                "Evidencias de parcela; no se trasladan al objeto BU ni a todas sus viviendas."
            )
        else:
            st.info(UNAVAILABLE)
            st.caption(
                "Información protegida en modo público."
                if not demo.private()
                else "Sin relación BU–CP acreditada para vincular certificados."
            )
    with tabs[3], panel(SECTIONS[3], statuses):
        if demo.private() and conservation_ref:
            from .conservation_view import render_conservation_parcel

            result = render_conservation_parcel(ref, code)
            if result:
                statuses[SECTIONS[3]] = result
        else:
            st.info(UNAVAILABLE)
        st.caption(
            "Las obligaciones ITE/IEE no son resultados. Archivar, terminar o multar no acredita subsanación ni estado físico."
        )
    with tabs[4], panel(SECTIONS[4], statuses):
        if demo.private() and ref:
            render_prtr(code, ref)
        else:
            st.info(UNAVAILABLE)
            st.caption(
                "PRTR protegido: reutilización sin acreditar."
                if not demo.private()
                else "Sin relación BU–CP acreditada para vincular ayudas."
            )
    with tabs[5], panel(SECTIONS[5], statuses):
        st.caption(demo.NOTICE)
        st.write(
            "Cobertura parcial de objetos observados; cuarentena excluida."
            if code != "28079"
            else "Captura municipal histórica de Madrid; no es un censo actualizado de edificios físicos."
        )
        labels = {
            "source_date": "Fecha de fuente",
            "captured_at": "Fecha de captura",
            "source_url": "Fuente catastral",
            "source_zip_sha256": "SHA-256 del archivo original",
            "source_sha256": "SHA-256 de fuente",
            "source_xml_sha256": "SHA-256 del registro original",
            "source_record_id": "Registro original",
            "usable_geometry": "Geometría utilizable",
            "selection_status": "Estado de aceptación",
        }
        st.dataframe(
            pd.DataFrame(
                [
                    {"Dato": label, "Valor": str(row.get(field, UNAVAILABLE))}
                    for field, label in labels.items()
                ]
            ),
            hide_index=True,
        )
        st.caption(
            "Catastro: INSPIRE. CEEE y PRTR: Comunidad de Madrid. Conservación y NDP: Ayuntamiento de Madrid, únicamente donde existe soporte. Cada fuente conserva fechas, ámbito y nivel de vínculo independientes."
        )
        if kind == "cp":
            st.download_button(
                "Exportar ficha HTML · identificación y limitaciones",
                demo.export_html(code, name, identifier, objects),
                file_name=f"ficha_{code}_{identifier}.html",
                mime="text/html",
            )
            st.caption(
                "La exportación excluye evidencias pendientes de revisión de redistribución."
            )
