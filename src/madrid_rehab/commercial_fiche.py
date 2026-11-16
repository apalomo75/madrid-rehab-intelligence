"""Documentary commercial model and deterministic rules, independent of Streamlit."""

from dataclasses import dataclass, field
from enum import StrEnum

import pandas as pd


class Quality(StrEnum):
    DOCUMENTED = "Información documentada"
    PARCEL = "Información asociada a parcela"
    PARTIAL = "Información parcial"
    AMBIGUOUS = "Vinculación ambigua"
    UNAVAILABLE = "Información no disponible"
    UNCOVERED = "Fuente no cubierta para ese municipio"


@dataclass(frozen=True)
class Evidence:
    label: str
    value: object
    source: str
    entity_id: str
    quality: Quality
    scope: str
    period: str = "Fecha no documentada"
    limitations: str = ""


@dataclass
class CommercialFiche:
    code: str
    name: str
    identifier: str
    kind: str
    title: str
    identity: list[Evidence] = field(default_factory=list)
    characteristics: list[Evidence] = field(default_factory=list)
    energy: list[Evidence] = field(default_factory=list)
    grants: list[Evidence] = field(default_factory=list)
    conservation: list[Evidence] = field(default_factory=list)
    municipal_grants: list[Evidence] = field(default_factory=list)
    states: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


USES = {
    "1_residential": "Residencial",
    "2_agriculture": "Agrícola",
    "3_industrial": "Industrial",
    "4_2_retail": "Comercio",
    "4_1_office": "Oficinas",
    "4_3_publicServices": "Servicios públicos",
}
CONFIRMED_GRANTS = {"confirmed", "confirmed_reference", "confirmed_historical_madrid"}


def clean(value):
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip() or None
    return value.item() if hasattr(value, "item") else value


def build_model(
    code,
    name,
    identifier,
    kind,
    cp,
    construction,
    accesses,
    energy,
    grants,
    events,
    postal=None,
    states=None,
    municipal_grants=None,
):
    """Receive selected documentary rows; never infer physical identity or sum BU attributes."""
    model = CommercialFiche(code, name, identifier, kind, f"Consulta catastral · {name}")
    model.states.update(states or {})
    source = "Dirección General del Catastro · INSPIRE"
    scope = "Objetos constructivos asociados a parcela" if kind == "cp" else "Objeto BU consultado"
    if postal:
        model.title = postal["original"] + " — " + name
        model.identity.append(
            Evidence(
                "Dirección seleccionada",
                postal["original"],
                "Ayuntamiento de Madrid · índice S20",
                postal["id"],
                Quality.DOCUMENTED,
                "Versión postal de acceso",
                limitations="Vínculo documental a parcela; no identifica un edificio físico único.",
            )
        )
        import json

        model.identity.append(
            Evidence(
                "Parcelas vinculadas al acceso",
                len(json.loads(postal["refs"])),
                "Índice postal S20",
                postal["access_id"],
                Quality.DOCUMENTED,
                "Acceso seleccionado",
            )
        )
    elif kind == "cp" and code != "28079":
        model.identity.append(
            Evidence(
                "Dirección postal",
                None,
                "Auditoría postal S20",
                identifier,
                Quality.UNCOVERED,
                "Municipio piloto",
            )
        )
    confirmed_accesses = accesses
    if not accesses.empty:
        confirmed_accesses = accesses[accesses.link_status.eq("confirmed_access_parcel")]
        count = confirmed_accesses.access_id.nunique()
        model.identity.append(
            Evidence(
                "Accesos documentales de la parcela",
                count,
                "Ayuntamiento de Madrid · S14",
                identifier,
                Quality.PARCEL,
                "Parcela; no comunidades",
            )
        )
        if not postal and count:
            addresses = sorted(
                {
                    " ".join(
                        str(r[k])
                        for k in ("kind", "street", "number_raw", "qualifier_raw")
                        if clean(r[k]) is not None
                    )
                    for _, r in confirmed_accesses.iterrows()
                }
            )
            model.title = " / ".join(addresses[:2]) + " — " + name
            if len(addresses) > 2:
                model.title += f" · {len(addresses)} accesos"
        if count > 1:
            model.recommendations.append(
                "Comprobar qué portal y comunidad corresponden al interlocutor: la parcela tiene varios accesos documentados."
            )
    if not cp.empty:
        r = cp.iloc[0]
        model.identity.append(
            Evidence(
                "Referencia de consulta",
                identifier,
                source,
                identifier,
                Quality.DOCUMENTED,
                "Parcela CP" if kind == "cp" else "Objeto BU",
                str(clean(r.get("source_date")) or "Fecha de fuente no documentada"),
            )
        )
    if not construction.empty:
        types = construction.get(
            "source_feature_type", pd.Series("BU histórico agregado", index=construction.index)
        ).value_counts()
        model.identity.append(
            Evidence(
                "Objetos constructivos documentados",
                {str(k): int(v) for k, v in types.items()},
                source,
                identifier,
                Quality.PARCEL if kind == "cp" else Quality.DOCUMENTED,
                scope,
                limitations="Recuento de objetos catastrales; no edificios físicos ni comunidades.",
            )
        )
    mapping = [
        ("Uso declarado", ["recovered_current_use", "current_use"]),
        (
            "Años constructivos declarados",
            [
                "recovered_construction_begin",
                "recovered_construction_end",
                "construction_oldest_year",
                "construction_newest_year",
            ],
        ),
        ("Superficie bruta de plantas (m²)", ["recovered_official_area"]),
        ("Viviendas declaradas por objeto", ["recovered_dwellings", "dwellings_raw"]),
        ("Plantas sobre rasante por objeto", ["recovered_floors_above"]),
        ("Plantas bajo rasante por objeto", ["recovered_floors_below"]),
        ("Unidades declaradas por objeto", ["recovered_building_units", "building_units_raw"]),
        ("Condición catastral declarada", ["recovered_condition"]),
    ]
    construction_rows = construction.to_dict("records")
    for label, fields in mapping:
        values = []
        for row in construction_rows:
            for key in fields:
                value = clean(row.get(key))
                if value is None:
                    continue
                if label == "Uso declarado":
                    value = USES.get(value, value)
                if isinstance(value, float) and value.is_integer():
                    value = int(value)
                values.append(
                    Evidence(
                        label,
                        value,
                        source,
                        str(row.get("building_id", identifier)),
                        Quality.PARCEL if kind == "cp" else Quality.DOCUMENTED,
                        scope
                        + " · "
                        + str(row.get("source_feature_type", "BU histórico agregado")),
                        str(clean(row.get("source_date")) or "Fecha de fuente en detalle técnico"),
                        "Valores por objeto, sin suma; no se atribuyen al portal. BuildingPart no equivale a edificio completo.",
                    )
                )
        model.characteristics.extend(
            values or [Evidence(label, None, source, identifier, Quality.UNAVAILABLE, scope)]
        )
    for _, row in (
        energy.drop_duplicates(["certificate_id", "link_level"]).iterrows()
        if not energy.empty
        else []
    ):
        # Link A alone is insufficient for contradictory registration content.
        good = (
            row.link_level == "A"
            and row.identity_status == "unique_registration_content"
            and not bool(row.date_after_capture)
        )
        model.energy.append(
            Evidence(
                "Contenido CEEE",
                {
                    "Consumo": clean(row.consumption_rating),
                    "Emisiones": clean(row.emissions_rating),
                    "Registro declarado": clean(row.get("edif_codreg")),
                    "Dirección certificada": clean(row.get("edif_direc")),
                    "Tipo certificado original": clean(row.get("edif_tipo")),
                    "Estado de magnitudes": " · ".join(
                        str(row.get(k + "_status", "no disponible"))
                        for k in ("consumption", "emissions", "area")
                    ),
                    "Consumo declarado": clean(row.get("consumption_value"))
                    if row.get("consumption_status") == "observed"
                    else None,
                    "Unidad consumo": clean(row.get("consumption_unit")),
                    "Emisiones declaradas": clean(row.get("emissions_value"))
                    if row.get("emissions_status") == "observed"
                    else None,
                    "Unidad emisiones": clean(row.get("emissions_unit")),
                    "Superficie certificada": clean(row.get("area_value"))
                    if row.get("area_status") == "observed"
                    else None,
                    "Unidad superficie": clean(row.get("area_unit")),
                    "Ámbito": clean(row.scope),
                    "Fecha declarada": clean(row.observation_date),
                },
                "Comunidad de Madrid · CEEE · " + str(row.source_id),
                row.certificate_id,
                Quality.PARCEL if good else Quality.AMBIGUOUS,
                str(row.scope),
                str(clean(row.observation_date) or "Fecha no disponible"),
                "Contenido canónico, no inmueble único ni certificado vigente verificado; no califica la parcela o todo el edificio. Magnitudes de la unidad certificada; unidades solo según estado de la fuente, sin suponer kWh/m² o m².",
            )
        )
    grant_groups = grants.groupby("expediente_id", sort=False) if not grants.empty else []
    for _, group in grant_groups:
        row = group.iloc[0]
        documentary = set(group.match_status).issubset(CONFIRMED_GRANTS)
        model.grants.append(
            Evidence(
                "Concesión PRTR",
                {
                    "Programa": clean(row.programa),
                    "Estados documentales": " · ".join(sorted(set(group.match_status))),
                    "Concesión del expediente (€)": clean(row.importe_concedido),
                    "Fecha de concesión declarada": clean(row.get("fecha_concesion")),
                    "Actualización fuente": clean(row.get("fecha_actualizacion")),
                },
                "Comunidad de Madrid · PRTR",
                row.expediente_id,
                Quality.PARCEL if documentary else Quality.AMBIGUOUS,
                "Expediente vinculado a parcela; importe del expediente único",
                str(
                    clean(row.get("fecha_concesion"))
                    or "Fecha individual de concesión no contrastada"
                ),
                "Concesión no acredita pago, inicio ni terminación de obras. No sumar por parcelas."
                + (
                    " P4 corresponde a vivienda y no se extiende al edificio."
                    if row.programa == "P4"
                    else ""
                ),
            )
        )
    if municipal_grants is not None and not municipal_grants.empty:
        for _, row in municipal_grants.drop_duplicates("case_id").iterrows():
            if row.link_class != "A":
                continue
            amount = clean(row.get("SUB_AYTO_R_cents"))
            budget = clean(row.get("TOT_PRES_P_cents"))
            model.municipal_grants.append(
                Evidence(
                    "Plan Rehabilita",
                    {
                        "Programa": "Plan Rehabilita · Ayuntamiento de Madrid",
                        "Convocatoria": clean(row.get("call")),
                        "Expediente": row.case_id,
                        "Dirección original": row.original_address,
                        "Actuaciones por componente fuente": clean(row.get("categories")),
                        "Viviendas declaradas del expediente": clean(row.get("dwellings")),
                        "Presupuesto protegible del expediente (€)": budget / 100
                        if budget is not None
                        else None,
                        "Subvención revisada del expediente (€)": amount / 100
                        if amount is not None
                        else None,
                        "BOAM_C · publicación según campo": clean(row.get("BOAM_C")),
                        "BOCM_C · publicación según campo": clean(row.get("BOCM_C")),
                        "Actualización de fuente": clean(row.get("FECHA_ACTU")),
                        "Estado individual": "No verificado en esta captura",
                        (
                            "Versión oficial verificada"
                            if row.get("official_source_url")
                            else "Captura original"
                        ): clean(row.get("official_last_modified"))
                        or "Fecha no acreditada; ZIP aportado por usuario",
                    },
                    "Ayuntamiento de Madrid · SUB_TOTAL_XY · "
                    + row.source_sha256
                    + (
                        " · " + str(row.official_source_url)
                        if row.get("official_source_url")
                        else ""
                    ),
                    row.case_id,
                    Quality.PARCEL,
                    "Expediente municipal relacionado con acceso y CP; no edificio físico",
                    str(clean(row.get("FECHA_ACTU")) or "Fecha no disponible"),
                    "Importe revisado por expediente único, sin reparto ni suma por CP o capas. "
                    "No acredita pago, obra iniciada/ejecutada, necesidad actual de financiación ni equivalencia con PRTR. "
                    "Viviendas del ámbito del expediente, no del portal. Fechas de publicación no son fecha individual de concesión.",
                )
            )
    for _, row in events.iterrows():
        model.conservation.append(
            Evidence(
                str(row.event_type),
                {
                    "Fecha": clean(row.date),
                    "Significado de fecha": clean(row.date_semantics),
                    "Situación original": clean(row.administrative_status),
                    "Expediente original": clean(row.get("original_id")),
                    "Acceso NDP declarado": clean(row.get("ndp")),
                    "Dirección original del antecedente": clean(row.get("address_raw")),
                    "Calle declarada": clean(row.get("street")),
                    "Número declarado": clean(row.get("number_raw")),
                },
                str(row.source_file),
                str(row.event_id),
                Quality.PARCEL
                if row.match_status == "confirmed" and not bool(row.identity_conflict)
                else Quality.AMBIGUOUS,
                "Antecedente administrativo de parcela",
                str(clean(row.date) or "Fecha no disponible"),
                "Obligación no es resultado; orden histórica no acredita deficiencias actuales ni subsanación.",
            )
        )
    if kind == "cp":
        if model.states.get("energy") not in {Quality.UNAVAILABLE, Quality.UNCOVERED} and not any(
            e.quality == Quality.PARCEL for e in model.energy
        ):
            model.recommendations.append(
                "Solicitar al interlocutor el certificado energético disponible: no consta un CEEE documental utilizable en estas fuentes."
            )
        if any(e.quality == Quality.PARCEL for e in model.grants):
            model.recommendations.append(
                "Comprobar compatibilidad de ayudas y estado real de la actuación; la concesión no acredita pago ni obras."
            )
        if any(e.label in {"order", "ite_pending", "iee_pending"} for e in model.conservation):
            model.recommendations.append(
                "Verificar el resultado vigente de ITE/IEE: los antecedentes disponibles son históricos u obligaciones de presentación."
            )
    uses = {
        e.value for e in model.characteristics if e.label == "Uso declarado" and e.value is not None
    }
    if uses & (set(USES.values()) - {"Residencial"}):
        model.recommendations.append(
            "Revisar el encaje del producto de financiación: constan usos distintos del residencial en los objetos consultados."
        )
    return model
