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
    from .commercial_data import grant_records

    details = grant_records(code, ref)
    if details.empty:
        st.info(UNAVAILABLE)
        st.caption(
            "No constan concesiones vinculadas en esta captura; no acredita ausencia real de ayudas."
        )
        return
    details = details[["expediente_id", "match_status", "programa", "importe_concedido"]].copy()
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


def render_fiche(
    code, name, identifier, objects=None, kind="cp", *, postal=None, public_catalog=False
):
    """Open by stable identity; map, grid and PyDeck state are optional callers."""
    from .cadastral_identity import resolve_object

    st.session_state["fiche_identity"] = None
    st.session_state["fiche_sections"] = {}
    if kind == "cp":
        identifier = identifier.strip().upper()
    origin = (code, kind, identifier)
    key = "fiche_route_" + "_".join(origin)
    if st.session_state.get("fiche_route_origin") != origin:
        for old_key in list(st.session_state):
            if old_key.startswith("fiche_route_") and old_key != "fiche_route_origin":
                del st.session_state[old_key]
        st.session_state["fiche_route_origin"] = origin
    target_kind, target_id = st.session_state.get(key, (kind, identifier))

    def navigate(next_kind, next_id):
        st.session_state[key] = (next_kind, next_id)

    if (target_kind, target_id) != (kind, identifier):
        st.button(
            "Volver al objeto de origen · " + identifier,
            key=key + "_back",
            on_click=navigate,
            args=(kind, identifier),
        )
        status, current = resolve_object(code, target_id, target_kind)
    elif objects is None:
        status, current = resolve_object(code, identifier, kind)
    else:
        status, current = "disponible", objects
    if current.empty:
        st.warning(status)
        return
    _render_commercial_and_technical(
        code,
        name,
        target_id,
        current,
        target_kind,
        navigate,
        key,
        postal if (target_kind, target_id) == (kind, identifier) else None,
        public_catalog,
    )


def _render_commercial_and_technical(
    code, name, identifier, objects, kind, navigate, route_key, postal, public_catalog=False
):
    from . import demo
    from .commercial_data import load_fiche
    from .commercial_view import render

    model, tables, errors, timings = load_fiche(
        code, name, identifier, objects, kind, postal, public_catalog=public_catalog
    )
    st.session_state["commercial_fiche_timings"] = timings
    if demo.private() or public_catalog:
        render(model, errors)
    else:
        st.subheader(model.title)
        st.caption("Información adicional protegida en modo público.")
    with st.expander("Detalles técnicos · seis secciones y datos originales", expanded=False):
        _render_fiche(
            code, name, identifier, objects, kind, navigate, route_key, tables, public_catalog
        )


def _render_fiche(
    code, name, identifier, objects, kind, navigate, route_key, tables, public_catalog=False
):
    from . import demo
    from . import enriched_cadastre as enriched

    statuses = {}
    st.session_state["fiche_sections"] = statuses
    st.session_state["fiche_identity"] = (code, kind, identifier)
    row = objects.iloc[0]
    ref = identifier if kind == "cp" else None
    # BU remains independent: a parcel field alone does not document a BU–CP relation.
    conservation_ref = ref if ref and re.fullmatch(r"[0-9]{7}[A-Z]{2}[0-9]{4}[A-Z]", ref) else None
    st.subheader(f"Ficha de {'parcela' if kind == 'cp' else 'objeto BU'} · {identifier}")
    expose = demo.private() or public_catalog
    enriched_enabled = code != "28079" and expose
    tabs = st.tabs(SECTIONS)
    with tabs[0], panel(SECTIONS[0], statuses):
        st.write(
            f"{name} · {'Parcela catastral CP' if kind == 'cp' else 'Objeto catastral BU independiente'}"
        )
        st.caption(
            "Identificación documental en captura. Parcela, objeto BU, portal y edificio físico son entidades diferentes."
        )
        if kind == "bu" and not enriched_enabled:
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
        if kind == "bu" and not ref and not enriched_enabled:
            st.caption(
                "Objeto constructivo consultado de forma independiente; no consta una "
                "relación documental confirmada con una parcela de las fuentes integradas"
            )
        if expose and conservation_ref:
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
        if kind == "bu" and enriched_enabled:
            relations = enriched.links(code, identifier, "bu")
            st.write("Relaciones documentales CP–BU (A validada; B/C incidencia)")
            st.dataframe(
                relations[["cp_reference_original", "link_class", "validation_reason"]],
                hide_index=True,
            )
            for cp_ref in (
                relations.loc[
                    relations.link_class.eq("A") & relations.relation_validated,
                    "cp_reference_normalized",
                ]
                .dropna()
                .unique()
            ):
                st.button(
                    "Abrir parcela relacionada · " + cp_ref,
                    key=route_key + "_cp_" + cp_ref,
                    on_click=navigate,
                    args=("cp", cp_ref),
                )
    with tabs[1], panel(SECTIONS[1], statuses):
        if enriched_enabled:
            enriched.metadata(code)
            if kind == "cp":
                records = tables["construction"]
                relations = enriched.links(code, identifier)
                issues = relations[~relations.link_class.eq("A")]
                counts = records.source_feature_type.value_counts()
                st.write(
                    f"{len(records)} objetos BU con relación documental A · "
                    f"{counts.get('Building', 0)} Building · {counts.get('BuildingPart', 0)} BuildingPart"
                )
                if not records.empty:
                    labels = {"building_id": "Objeto BU", "source_feature_type": "Tipo"}
                    labels.update({"recovered_" + k: v for k, v in enriched.ATTRIBUTES.items()})
                    st.dataframe(
                        records.drop(columns="municipality_code").rename(columns=labels),
                        hide_index=True,
                    )
                    selected = st.selectbox(
                        "Construcción relacionada",
                        records.building_id.tolist(),
                        key=route_key + "_bu_choice_" + identifier,
                    )
                    st.button(
                        "Consultar construcción",
                        key=route_key + "_open_" + identifier,
                        on_click=navigate,
                        args=("bu", selected),
                    )
                else:
                    st.info(
                        "Sin BU documental A en esta captura; no acredita ausencia de construcciones."
                    )
                st.write(f"{len(issues)} vínculos con incidencias, sin confirmación")
                if not issues.empty:
                    st.dataframe(
                        issues[["building_id", "link_class", "validation_reason"]], hide_index=True
                    )
            else:
                own = enriched.building(code, identifier).iloc[0]
                st.write("Tipo de objeto: " + own.source_feature_type)
                attributes = enriched.attribute_table(own)
                st.dataframe(attributes[["Atributo", "Valor", "Estado"]], hide_index=True)
                with st.expander("Valores originales y procedencia de cada atributo"):
                    st.dataframe(attributes, hide_index=True)
            st.caption(
                "Valores propios del objeto. No se suman superficies de Building y BuildingPart. "
                "BuildingPart no equivale a edificio completo. Nulos y estados se conservan; "
                "la condición catastral no es una inspección actual."
            )
        else:
            construction = (
                construction_table(objects)
                if kind == "bu"
                else construction_table(tables["construction"])
            )
            if construction.empty:
                st.info(UNAVAILABLE)
            else:
                st.dataframe(construction, hide_index=True)
        st.caption("Atributos declarados; no confirman identidad ni estado físico actual.")
    with tabs[2], panel(SECTIONS[2], statuses):
        if expose and ref:
            from .energy_view import render_energy_parcel

            render_energy_parcel(code, ref)
            st.caption(
                "Evidencias de parcela; no se trasladan al objeto BU ni a todas sus viviendas."
            )
        else:
            st.info(UNAVAILABLE)
            st.caption(
                "Información protegida en modo público."
                if not expose
                else "CEEE pertenece a la parcela y a su ámbito certificado; no se atribuye a este BU."
            )
    with tabs[3], panel(SECTIONS[3], statuses):
        if expose and conservation_ref:
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
        if expose and ref:
            render_prtr(code, ref)
        else:
            st.info(UNAVAILABLE)
            st.caption(
                "PRTR protegido: reutilización sin acreditar."
                if not expose
                else "Las ayudas pertenecen al expediente y la parcela; no se atribuyen a este BU."
            )
    with tabs[5], panel(SECTIONS[5], statuses):
        st.caption(demo.NOTICE)
        if enriched_enabled:
            st.write("Snapshot: " + str(enriched.ROOT))
            relations = enriched.links(code, identifier, kind)
            st.write(
                f"Calidad documental: {relations.link_class.value_counts().to_dict()} · "
                f"Incidencias: {int((~relations.link_class.eq('A')).sum())}"
            )
            st.caption(
                "A: declaración y geometría concordantes según regla 95%/5%. "
                "B: incidencia documental o geométrica. C: sin CP aceptada resoluble. "
                "No acredita edificio físico ni atribuye CEEE, conservación o PRTR al BU."
            )
            if kind == "cp":
                st.caption(
                    "Altura sobre rasante: no disponible en esta captura. "
                    "La disponibilidad de uso, fechas, viviendas, plantas y superficie varía "
                    "por objeto; consultar el detalle BU y sus estados, sin heredar valores."
                )
            if kind == "bu":
                own = enriched.building(code, identifier).iloc[0]
                st.write(
                    "Campos no declarados válidos: "
                    + ", ".join(
                        label
                        for k, label in enriched.ATTRIBUTES.items()
                        if own.get("recovered_" + k + "_state") != "declared"
                    )
                )
                st.json(
                    {
                        field: str(own.get(field))
                        for field in (
                            "source_gml_member",
                            "source_ordinal",
                            "source_xml_sha256",
                            "source_zip_sha256",
                            "enrichment_captured_at",
                            "enrichment_rule",
                        )
                    }
                )
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
