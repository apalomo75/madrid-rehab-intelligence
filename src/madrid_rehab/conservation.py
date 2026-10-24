"""Productos offline de conservación a partir de evidencia municipal preservada.

No obtiene fichas REC, no crea dictámenes desde obligaciones y no confirma BU.
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from .administrative import DEFAULT as ADMIN, json_write, key
from .ingest import digest

DEFAULT = Path("data/processed/conservation/session_14_final_02")
ENERGY = Path("data/processed/energy/session_13_final_03")
CP = Path("data/processed/session_2/parcels_audited.parquet")
POLICY = "conservation-evidence-v1"
CONSERVATION_TYPES = {"order", "ite_pending", "iee_pending"}


def verify_product(root, relative, inputs):
    root = Path(root)
    manifest_path = root / "manifest.json"
    m = json.loads(manifest_path.read_text())
    p = root / relative
    h = digest(p)
    if h != m["outputs"][relative]:
        raise ValueError(f"Producto alterado: {p}")
    inputs[str(manifest_path)] = digest(manifest_path)
    inputs[str(p)] = h
    return p


def access_links(bridge, cp):
    """Puente documental previo + CP única y utilizable. Sin vecinos próximos.

    Conserva todos los candidatos; las contradicciones son ambiguas. Todas las
    ocurrencias de una clave CP duplicada/no utilizable quedan excluidas.
    """
    b = bridge.copy()
    cp = cp.copy()
    unusable = cp.parcel_ref14.duplicated(keep=False)
    for col in ["usable_geometry", "topology_valid"]:
        if col in cp:
            unusable |= ~cp[col].fillna(False)
    if "quality_status" in cp:
        unusable |= cp.quality_status.ne("accepted")
    if "quarantined" in cp:
        unusable |= cp.quarantined.fillna(True)
    invalid_refs = set(cp.loc[unusable, "parcel_ref14"])
    good = set(cp.parcel_ref14) - invalid_refs
    b["access_id"] = "28079:ndp:" + b.ndp.fillna("")
    b["link_status"] = b.match_status.map(
        {
            "confirmed": "confirmed_access_parcel",
            "candidate": "candidate_access_parcel",
            "ambiguous": "ambiguous_access_parcel",
            "contradictory": "ambiguous_access_parcel",
            "multiparcel": "ambiguous_access_parcel",
            "unmatched": "unmatched_access",
        }
    ).fillna("unmatched_access")
    b["link_reason"] = "inherited_audited_documentary_bridge"
    bad = b.match_status.eq("confirmed") & ~b.parcel_ref14.isin(good)
    b.loc[bad, "link_status"] = "ambiguous_access_parcel"
    b.loc[bad, "link_reason"] = "cp_missing_unusable_or_quarantined"
    # No aceptar una versión de NDP si otra versión tiene un vínculo distinto.
    for _, group in b[b.ndp.duplicated(keep=False)].groupby("ndp", sort=False):
        if (
            group.link_status.ne("confirmed_access_parcel").any()
            or group.parcel_ref14.nunique() != 1
        ):
            b.loc[group.index, "link_status"] = "ambiguous_access_parcel"
            b.loc[group.index, "link_reason"] = "conflicting_access_versions"
    b["confirmed_parcel_ref14"] = b.parcel_ref14.where(
        b.link_status.eq("confirmed_access_parcel"), ""
    )
    b["municipality_code"] = "28079"
    b["physical_building_link"] = False
    return b


def municipal_evidence(events):
    """Mantiene todas las identidades anteriores, con semántica adicional explícita."""
    e = events.copy()
    e["is_conservation_evidence"] = e.event_type.isin(CONSERVATION_TYPES)
    e["evidence_kind"] = e.event_type.map(
        {
            "order": "historical_execution_order",
            "ite_pending": "ite_presentation_obligation",
            "iee_pending": "iee_presentation_obligation",
            "license": "license_granted",
            "declaration": "declaration_presented",
        }
    ).fillna("other_administrative_action")
    e["inspection_outcome"] = "unknown"
    # Motivo de una orden, no acta de inspección: preservado como señal indirecta.
    normalized = e.description.map(key)
    e["indirect_unfavorable_mention"] = e.event_type.eq("order") & normalized.str.contains(
        "DESFAVORABLE|DESAFAVORABLE", regex=True
    )
    e["current_physical_condition"] = "not_evaluable"
    e["remediation_status"] = "unknown"
    e["municipality_code"] = "28079"
    e["rec_individual_coverage"] = "no_individual_coverage"
    e["date_semantics"] = e.event_type.map(
        {
            "order": "resolution_month",
            "ite_pending": "obligation_deadline",
            "iee_pending": "obligation_deadline",
            "license": "grant_resolution_date",
            "declaration": "registration_date",
        }
    )
    e["public_exposure"] = False
    return e


def relation_level(rec, municipal):
    """A/B/C/D para investigación; no fusiona identidades ni ordinales de órdenes."""
    r, m = rec.get("case_reference", ""), municipal.get("original_id", "")
    import re

    valid = bool(re.fullmatch(r"\d{3}/\d{4}/\d+", r)) and r == m
    same_authority = rec.get("authority") == municipal.get("authority") and bool(
        rec.get("authority")
    )
    r_ndp, m_ndp = rec.get("ndp", ""), municipal.get("ndp", "")
    if valid and same_authority:
        if r_ndp and m_ndp and r_ndp != m_ndp:
            return "D_contradiction"
        return "B_exact_case_and_access" if r_ndp and r_ndp == m_ndp else "A_exact_case"
    if r_ndp and r_ndp == m_ndp:
        return "C_possible_administrative_relation"
    if rec.get("address_normalized") and rec.get("address_normalized") == municipal.get(
        "address_normalized"
    ):
        return "C_possible_administrative_relation"
    return "unrelated"


def investigation_signal(state, historical=False):
    if state == "contradictory":
        return "review_conflict"
    if state == "unfavorable_remediation_evidenced":
        return "resolved_evidence"
    if state == "unfavorable_explicitly_pending":
        return "pending_at_source_observation"
    if state == "favorable":
        return "favorable_at_observation"
    return "historical_evidence_current_state_unknown" if historical else "unknown"


def evidence_profiles(events, context):
    e = events[events.match_status.eq("confirmed") & events.parcel_ref14.ne("")].drop_duplicates(
        "event_id"
    )
    groups = []
    for ref, g in e.groupby("parcel_ref14", sort=True):
        conservation = g[g.is_conservation_evidence]
        if conservation.empty:
            continue
        orders = conservation[conservation.event_type.eq("order")]
        obligations = conservation[conservation.event_type.isin(["ite_pending", "iee_pending"])]
        dates = conservation.date.fillna("")
        groups.append(
            dict(
                municipality_code="28079",
                parcel_ref14=ref,
                conservation_event_count=len(conservation),
                historical_order_count=len(orders),
                pending_ite_obligation_count=int(conservation.event_type.eq("ite_pending").sum()),
                pending_iee_obligation_count=int(conservation.event_type.eq("iee_pending").sum()),
                indirect_unfavorable_mention_count=int(orders.indirect_unfavorable_mention.sum()),
                license_context_count=int(g.event_type.eq("license").sum()),
                declaration_context_count=int(g.event_type.eq("declaration").sum()),
                latest_administrative_date=max(dates[dates.ne("")], default=""),
                latest_source_observation=max(obligations.query_date.fillna(""), default=""),
                inspection_count=0,
                remediation_status="unknown",
                rec_coverage="no_individual_coverage",
                investigation_signal="historical_evidence_current_state_unknown"
                if len(orders)
                else "presentation_obligation_at_source_observation",
                event_ids="|".join(sorted(conservation.event_id.unique())),
                source="municipal_administrative_snapshot_session10",
                link_quality="confirmed_parcel_not_building",
                physical_condition="not_evaluable",
                public_exposure=False,
            )
        )
    p = pd.DataFrame(groups)
    if p.empty:
        return p
    c = context[context.municipality_code.eq("28079")]
    if c.duplicated(["municipality_code", "parcel_ref14"]).any():
        raise ValueError("Contexto energético/PRTR duplicado por parcela")
    p = p.merge(
        c[["municipality_code", "parcel_ref14", "certificate_count", "grant_case_count"]],
        how="left",
        on=["municipality_code", "parcel_ref14"],
        validate="one_to_one",
    )
    # Contexto no tiene cobertura exhaustiva; cero significa ninguno vinculado en snapshot.
    p[["certificate_count", "grant_case_count"]] = (
        p[["certificate_count", "grant_case_count"]].fillna(0).astype(int)
    )
    p["context_semantics"] = "linked_observations_only_no_causality_no_parcel_energy_rating"
    return p


def build(output=DEFAULT, admin=ADMIN, energy=ENERGY, cp_path=CP):
    started = time.perf_counter()
    output, admin, energy, cp_path = map(Path, [output, admin, energy, cp_path])
    if output.exists():
        raise FileExistsError("Usa un directorio nuevo; snapshots inmutables")
    inputs = {}
    events_path = verify_product(admin, "events.parquet", inputs)
    bridge_path = verify_product(admin, "ndp_bridge.parquet", inputs)
    ndp_path = verify_product(admin, "213605-4-callejero-oficial-madrid-csv.csv.parquet", inputs)
    context_path = verify_product(energy, "energy_grants_summary.parquet", inputs)
    metadata = json.loads((admin / "manifest.json").read_text())
    if digest(cp_path) != metadata["cp_sha256"]:
        raise ValueError("Catastro CP no corresponde al puente administrativo")
    inputs[str(cp_path)] = digest(cp_path)
    # Verificar originales preservados, sin inventar fecha de descarga.
    original_manifest = admin / "input_manifest.json"
    if digest(original_manifest) != metadata["input_manifest_sha256"]:
        raise ValueError("Inventario original alterado")
    inputs[str(original_manifest)] = digest(original_manifest)
    originals = json.loads(original_manifest.read_text())
    for row in originals:
        raw = Path("data/raw/administrative") / row["sha256"] / row["name"]
        if digest(raw) != row["sha256"]:
            raise ValueError(f"Original alterado: {raw}")
        inputs[str(raw)] = row["sha256"]
    source_config = Path("config/conservation_sources.json")
    sources = json.loads(source_config.read_text())
    inputs[str(source_config)] = digest(source_config)
    # Revalidar manifests externos e integridad de sus outputs, sin reprocesarlos.
    verified = {}
    for root in [
        energy,
        Path("data/processed/cadastre/session_12_2_partial_validated_01"),
        Path("data/processed/grants/session_11_final_03"),
        Path("data/processed/grants/regional/session_12_1_final_02"),
        Path("data/processed/territory/session_12_1_final_01"),
    ]:
        manifest_name = (
            "grant_source_manifest.json" if root.name == "session_11_final_03" else "manifest.json"
        )
        dependency_manifest = root / manifest_name
        m = json.loads(dependency_manifest.read_text())
        for name, expected in m["outputs"].items():
            if digest(root / name) != expected:
                raise ValueError(f"Snapshot dependiente alterado: {root / name}")
        inputs[str(dependency_manifest)] = digest(dependency_manifest)
        verified[str(root)] = len(m["outputs"])
    cp = pd.read_parquet(cp_path, columns=["parcel_ref14", "usable_geometry", "topology_valid"])
    b = access_links(pd.read_parquet(bridge_path), cp)
    ndp = pd.read_parquet(ndp_path)
    ndp["identity_quality"] = ndp.COD_NDP.duplicated(keep=False).map(
        {True: "multiple_observed_address_versions", False: "single_observed_address"}
    )
    ndp["source_row"] = range(2, len(ndp) + 2)
    events = municipal_evidence(pd.read_parquet(events_path))
    # Conservar vínculo confirmado previo solo si CP aceptada y única.
    good = set(
        cp.loc[
            cp.usable_geometry & cp.topology_valid & ~cp.parcel_ref14.duplicated(keep=False),
            "parcel_ref14",
        ]
    )
    bad = events.match_status.eq("confirmed") & ~events.parcel_ref14.isin(good)
    events.loc[bad, "match_status"] = "ambiguous"
    events.loc[bad, "parcel_ref14"] = ""
    profiles = evidence_profiles(events, pd.read_parquet(context_path))
    energy_links_path = verify_product(energy, "municipalities/28079/links.parquet", inputs)
    energy_cert_path = verify_product(energy, "municipalities/28079/certificates.parquet", inputs)
    el = pd.read_parquet(energy_links_path)
    el = el[el.link_level.eq("A") & el.parcel_ref14.isin(profiles.parcel_ref14)].drop_duplicates(
        ["certificate_id", "parcel_ref14"]
    )
    cert = pd.read_parquet(
        energy_cert_path,
        columns=[
            "certificate_id",
            "scope",
            "consumption_rating",
            "emissions_rating",
            "observation_date",
            "identity_status",
            "source_id",
        ],
    )
    energy_evidence = el.merge(cert, on="certificate_id", validate="many_to_one")
    for column in ["scope", "consumption_rating", "emissions_rating", "observation_date"]:
        series = energy_evidence.groupby("parcel_ref14")[column].agg(
            lambda x: "|".join(sorted(set(x.dropna().astype(str)) - {""}))
        )
        profiles["energy_observed_" + column] = profiles.parcel_ref14.map(series).fillna("")
    profiles["whole_building_certificate_count"] = (
        profiles.parcel_ref14.map(
            energy_evidence[energy_evidence.scope.eq("whole_building")]
            .groupby("parcel_ref14")
            .certificate_id.nunique()
        )
        .fillna(0)
        .astype(int)
    )
    profiles["energy_source_snapshot"] = str(energy)
    profiles["energy_context_quality"] = "scope_of_each_certificate_not_of_parcel"
    partial = Path("data/processed/cadastre/session_12_2_partial_validated_01")
    grant_links_path = verify_product(partial, "grant_parcel_links.parquet", inputs)
    gl = pd.read_parquet(grant_links_path)
    gl = gl[
        gl.match_status.isin(["confirmed", "confirmed_historical_madrid"])
        & gl.geographic_municipality_code.eq("28079")
        & gl.parcel_ref14.isin(profiles.parcel_ref14)
    ]
    grant_evidence = gl.drop_duplicates(["expediente_id", "parcel_ref14"]).copy()
    grants_path = Path("data/processed/grants/session_11_final_03/grants.parquet")
    inputs[str(grants_path)] = digest(grants_path)
    grants = pd.read_parquet(grants_path)
    grant_cases = grants[grants.expediente_id.isin(grant_evidence.expediente_id)][
        ["expediente_id", "programa", "importe_centimos", "fecha_concesion", "fecha_disponible"]
    ].drop_duplicates()
    if grant_cases.expediente_id.duplicated().any():
        raise ValueError("Concesiones con identidad conflictiva")
    profiles["grant_source_snapshot"] = str(partial)
    # Cobertura explícita para los 179 municipios, sin exportar NDP fuera de Madrid.
    municipalities_path = verify_product(energy, "energy_municipality_summary.parquet", inputs)
    coverage = pd.read_parquet(municipalities_path, columns=["municipality_code", "name"])
    coverage["individual_inspection_coverage"] = "no_individual_coverage"
    coverage["administrative_coverage"] = coverage.municipality_code.map(
        {"28079": "partial_historical_sources"}
    ).fillna("not_evaluable")
    coverage["municipal_source_discovered"] = coverage.municipality_code.map(
        {
            "28079": "REC",
            "28005": "municipal_ITE_obligation_lists",
            "28065": "padrón_documented_not_acquired",
            "28092": "IEE_lists_link_documented",
            "28007": "municipal_IEE_obligation_list_documented",
            "28014": "municipal_open_dataset_not_acquired",
        }
    ).fillna("not_verified_in_this_session")
    events["source_sha256"] = events.source_file.map({r["name"]: r["sha256"] for r in originals})
    events["source_record_ref"] = "session10:" + events.event_version_id
    if events.source_sha256.isna().any():
        raise ValueError("Evento sin procedencia original")
    events["product_generated_at"] = "not_source_capture_date"
    ndp["municipality_code"] = "28079"
    ndp["access_id"] = "28079:ndp:" + ndp.COD_NDP
    ndp["access_version_id"] = ndp.access_id + ":row:" + ndp.source_row.astype(str)
    ndp["source_sha256"] = next(
        r["sha256"] for r in originals if r["name"] == ndp_path.name.removesuffix(".parquet")
    )
    ndp["source_capture_date"] = None
    ndp["source_snapshot_date"] = None
    ndp["physical_building_identity"] = "not_confirmed"
    for frame in [ndp, b]:
        frame["source_snapshot"] = str(admin)
        frame["source_manifest_sha256"] = digest(admin / "manifest.json")
        frame["capture_date"] = None
        frame["schema_version"] = POLICY
    quality = pd.DataFrame(
        [
            {"metric": "rec_individual_coverage", "value": "none"},
            {"metric": "ite_iee_real_inspections", "value": "0"},
            {"metric": "rec_municipal_overlap", "value": "not_evaluable_no_rec_records"},
            {"metric": "rec_batch_permission", "value": "not_verified"},
            {"metric": "regional_individual_coverage", "value": "not_evaluable"},
            {"metric": "ndp_11140360", "value": "address_matches_user_observation_cp_unmatched"},
        ]
    )
    # Separar procedencia ligera de eventos, sin duplicar los bytes de cada original.
    source_records = events[
        [
            "event_id",
            "event_version_id",
            "source_record_ref",
            "source_file",
            "source_row",
            "page",
            "source_sha256",
            "capture_date",
            "query_date",
        ]
    ].copy()
    output.mkdir(parents=True)
    products = {
        "conservation_accesses": ndp,
        "conservation_parcel_links": b,
        "conservation_events": events,
        "conservation_evidence_profile": profiles,
        "conservation_source_records": source_records,
        "conservation_quality": quality,
        "conservation_sources": pd.DataFrame(sources),
        "conservation_energy_links": energy_evidence,
        "conservation_grant_links": grant_evidence,
        "conservation_grant_cases": grant_cases,
        "conservation_regional_coverage": coverage,
    }
    for name, frame in products.items():
        frame.to_parquet(output / (name + ".parquet"), index=False)
    # Buckets CP permiten filtros de fila sin cargar distritos completos en una ficha.
    confirmed = events[events.match_status.eq("confirmed") & events.parcel_ref14.ne("")]
    for bucket, frame in confirmed.groupby(confirmed.parcel_ref14.str[:2], sort=True):
        folder = output / "parcels" / bucket
        folder.mkdir(parents=True)
        frame.sort_values(["parcel_ref14", "date", "event_id"]).to_parquet(
            folder / "events.parquet", index=False, row_group_size=128
        )
        profiles[profiles.parcel_ref14.str.startswith(bucket)].sort_values(
            "parcel_ref14"
        ).to_parquet(folder / "profiles.parquet", index=False, row_group_size=128)
    access_confirmed = b[b.link_status.eq("confirmed_access_parcel")].copy()
    access_confirmed["parcel_ref14"] = access_confirmed.confirmed_parcel_ref14
    for bucket, frame in access_confirmed.groupby(access_confirmed.parcel_ref14.str[:2], sort=True):
        folder = output / "parcels" / bucket
        folder.mkdir(parents=True, exist_ok=True)
        frame.sort_values(["parcel_ref14", "ndp"]).to_parquet(
            folder / "accesses.parquet", index=False, row_group_size=128
        )
    counts = {
        "sources_investigated": len(sources),
        "official_download_sources": sum(r["official_download"] for r in sources),
        "sources_reused": sum(r["incorporated"] for r in sources),
        "new_rec_sources": 0,
        "ndp_contrasted_against_user_observation": 1,
        "official_accesses": int(ndp.COD_NDP.nunique()),
        "official_access_versions": len(ndp),
        "ndp_with_multiple_versions": int(
            ndp.loc[ndp.COD_NDP.duplicated(keep=False), "COD_NDP"].nunique()
        ),
        "confirmed_accesses": int(
            b.loc[b.link_status.eq("confirmed_access_parcel"), "ndp"].nunique()
        ),
        "ambiguous_accesses": int(
            b.loc[b.link_status.eq("ambiguous_access_parcel"), "ndp"].nunique()
        ),
        "real_inspections": 0,
        "ite_favorable": 0,
        "ite_unfavorable": 0,
        "iee_favorable": 0,
        "iee_unfavorable": 0,
        "explicit_pending_remediation": 0,
        "evidenced_remediation": 0,
        "execution_orders": int(events.event_type.eq("order").sum()),
        "coercive_fines": 0,
        "municipal_events_reused": int(events.event_id.nunique()),
        "conservation_events": int(events.is_conservation_evidence.sum()),
        "conservation_parcels": len(profiles),
        "indirect_unfavorable_order_mentions": int(events.indirect_unfavorable_mention.sum()),
        "events_with_exact_case_reference": int(
            events.original_id.str.fullmatch(r"\d{3}/\d{4}/\d+").sum()
        ),
        "source_identity_duplicates": int(events.event_id.duplicated().sum()),
    }
    json_write(output / "summary.json", counts)
    manifest = dict(
        policy=POLICY,
        inputs=inputs,
        counts=counts,
        cp_sha256=metadata["cp_sha256"],
        verified_dependency_outputs=verified,
        rec_access_status="public_individual_reuse_unverified",
        rec_batch_access="not_verified",
        public_exposure=False,
        historical_coverage="partial_unknown_completeness",
        inspection_coverage="no_individual_coverage",
        no_physical_building_links=True,
        outputs={
            str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()
        },
        code_sha256={
            p.name: digest(p) for p in [Path(__file__), Path(__file__).with_name("rec.py")]
        },
    )
    json_write(output / "manifest.json", manifest)
    return dict(counts=counts, duration_s=time.perf_counter() - started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--administrative-dir", type=Path, default=ADMIN)
    parser.add_argument("--energy-dir", type=Path, default=ENERGY)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir, args.administrative_dir, args.energy_dir), indent=2))


if __name__ == "__main__":
    main()
