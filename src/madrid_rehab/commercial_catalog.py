"""Offline six-municipality catalogue; documentary alternatives, no physical diagnosis."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import shapely as sh

from . import demo, enriched_cadastre
from .address_search import NAMES
from .data_recovery_audit import (
    CITY,
    CONSERVATION,
    ENERGY,
    PARTIAL,
    RECOVERY,
    historic_buildings,
)
from .ingest import digest
from .plan_rehabilita import DEFAULT as REHABILITA

DEFAULT = Path("data/processed/commercial_catalog/session_24_public_02")
REPORT = Path("reports/session_24_public_catalog_02")
VERSION = "commercial-catalog-six-v2"
SOURCES = ("construction", "energy", "administrative", "prtr", "rehabilita")
# Catalogue membership follows the owner's explicit request for local/public parity.
# Evidence retains its original attribution, scope and source-level limitations.
PUBLIC_SOURCES = dict.fromkeys(SOURCES, True)
PUBLIC_REASONS = {
    "construction": "Owner-approved catalogue exposure; original object scope and Catastro attribution retained",
    "energy": "Owner-approved catalogue exposure; CC BY 4.0 attribution and certificate scope retained",
    "administrative": "Owner-approved catalogue exposure; source attribution and historical/obligation scope retained",
    "prtr": "Owner-approved catalogue exposure; COAM-hosted PRTR viewer attributed; reuse licence remains unverified",
    "rehabilita": "Owner-approved catalogue exposure; user-provided Ayuntamiento dataset attributed; original licence remains unverified",
}
FIELDS = ["year", "area", "dwellings", "floors"]
DOCUMENTED = "Ficha documentada"
PARTIAL_LEVEL = "Ficha parcial con evidencia"
EXCLUDED = "Registro técnico excluido"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


def number(frame, choices):
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    for field in choices:
        if field in frame:
            result = result.fillna(pd.to_numeric(frame[field], errors="coerce"))
    return result


def construction_flags(frame):
    """Require all qualifying attributes on the SAME residential object, never CP union."""
    use = frame.get("recovered_current_use", pd.Series(index=frame.index, dtype=object))
    if "current_use" in frame:
        use = use.fillna(frame.current_use)
    years = number(frame, ["construction_oldest_year"])
    if "recovered_construction_begin" in frame:
        raw = frame.recovered_construction_begin.astype("string")
        parsed = pd.to_numeric(
            raw.str.extract(r"^(\d{4})-\d{2}-\d{2}T", expand=False), errors="coerce"
        )
        years = years.fillna(parsed)
    flags = pd.DataFrame(index=frame.index)
    flags["year"] = years.between(1000, 2026)
    flags["area"] = number(frame, ["recovered_official_area"]).gt(0)
    flags["dwellings"] = number(frame, ["recovered_dwellings", "dwellings_raw"]).gt(0)
    # Zero below-ground floors alone cannot turn an empty object into useful construction.
    flags["floors"] = number(frame, ["recovered_floors_above"]).gt(0)
    flags["residential"] = use.eq("1_residential").fillna(False)
    flags["construction"] = flags.residential & flags[FIELDS].sum(axis=1).ge(2)
    return flags


def assign_levels(frame, source_policy):
    selected = pd.DataFrame({key: frame[key] & bool(source_policy[key]) for key in SOURCES})
    # Two aid programmes are one evidence family, not complementary physical evidence.
    families = pd.DataFrame(
        dict(
            construction=selected.construction,
            energy=selected.energy,
            administrative=selected.administrative,
            aid=selected.prtr | selected.rehabilita,
        )
    )
    visible = families.any(axis=1)
    documented = selected.construction | families.sum(axis=1).ge(2)
    levels = pd.Series(EXCLUDED, index=frame.index)
    levels.loc[visible] = PARTIAL_LEVEL
    levels.loc[visible & documented] = DOCUMENTED
    reasons = selected.apply(
        lambda r: json.dumps([k for k in SOURCES if r[k]], ensure_ascii=False), axis=1
    )
    return visible, levels, reasons, families.sum(axis=1)


def build(output=DEFAULT, report=REPORT):
    output, report = Path(output), Path(report)
    if output.exists() or (report / "metrics.json").exists():
        raise FileExistsError("New catalogue and report outputs required")
    report.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True)
    inputs = {}

    def track(path):
        path = Path(path)
        inputs[str(path)] = digest(path)
        return path

    for root in [CITY, ENERGY, CONSERVATION, PARTIAL, enriched_cadastre.ROOT, RECOVERY, REHABILITA]:
        track(root / "manifest.json")
    from . import address_search

    address_search.metadata()
    track(address_search.DEFAULT / "manifest.json")
    postal_path = track(address_search.DEFAULT / "addresses.sqlite")
    certificates = pd.read_parquet(
        track(ENERGY / "energy_certificates.parquet"),
        columns=[
            "certificate_id",
            "identity_status",
            "date_after_capture",
            "scope",
            "schema_suspect",
        ],
    )
    el = pd.read_parquet(track(ENERGY / "energy_parcel_links.parquet"))
    el = el.merge(certificates, on="certificate_id", validate="many_to_one")
    el = el[
        el.link_level.eq("A")
        & el.identity_status.eq("unique_registration_content")
        & ~el.date_after_capture
        & ~el.schema_suspect
    ]
    events = pd.read_parquet(
        track(CONSERVATION / "conservation_events.parquet"),
        columns=[
            "event_id",
            "parcel_ref14",
            "event_type",
            "date",
            "match_status",
            "identity_conflict",
            "is_conservation_evidence",
            "inspection_outcome",
        ],
    )
    valid_dates = events.date.fillna("").str.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?")
    valid_dates &= pd.to_datetime(events.date, format="mixed", errors="coerce").notna()
    admin = events[
        events.match_status.eq("confirmed")
        & ~events.identity_conflict
        & events.is_conservation_evidence
        & valid_dates
        & events.event_type.isin(["order", "ite_pending", "iee_pending"])
    ]
    grant_master = pd.read_parquet(
        track(Path("data/processed/grants/session_11_final_03/grants.parquet")),
        columns=["expediente_id", "identity_conflict", "territorial_quality"],
    )
    good_grants = grant_master[
        ~grant_master.identity_conflict & ~grant_master.territorial_quality.eq("contradictory")
    ]
    gl = pd.read_parquet(track(PARTIAL / "grant_parcel_links.parquet"))
    gl = gl[
        gl.match_status.isin(["confirmed", "confirmed_reference", "confirmed_historical_madrid"])
        & gl.expediente_id.isin(good_grants.expediente_id)
    ]
    rehab = pd.read_parquet(track(REHABILITA / "locations.parquet"))
    rehab = rehab[rehab.link_class.eq("A")]
    # Authenticate selected immutable sources against their historical manifests before use.
    for root in [ENERGY, CONSERVATION, REHABILITA]:
        meta = json.loads((root / "manifest.json").read_text())
        for name, sha in meta["outputs"].items():
            path = root / name
            if str(path) in inputs and inputs[str(path)] != sha:
                raise ValueError("Altered source " + str(path))
    for name, sha in json.loads((RECOVERY / "manifest.json").read_text())["outputs"].items():
        if digest(RECOVERY / name) != sha:
            raise ValueError("Altered Madrid recovery")
    rows = []
    metrics = []
    samples = []
    object_metrics = []
    for code, name in NAMES.items():
        root, relative = demo.cp_source(code)
        path = track(root / relative)
        cp = demo.read(root, relative)
        observed = len(cp)
        cp = cp[cp.usable_geometry & ~cp.parcel_ref14.duplicated(keep=False)].copy()
        if code == "28079":
            for p in sorted(CITY.glob("districts/*/map_buildings.parquet")):
                m = p.parent / "manifest.json"
                track(m)
                expected = json.loads(m.read_text())["outputs"][p.name]
                if digest(p) != expected:
                    raise ValueError("Altered municipal construction partition")
                track(p)
            track(demo.CITY / "buildings_audited.parquet")
            bu = historic_buildings()
            extra = pd.read_parquet(
                track(RECOVERY / "building_attributes.parquet"),
                columns=["building_id", "parcel_ref14", "recovered_official_area"],
            )
            bu = bu.merge(
                extra, on=["building_id", "parcel_ref14"], how="left", validate="one_to_one"
            )
            bu["source_feature_type"] = "Building"
        else:
            enriched_cadastre.metadata(code)
            track(enriched_cadastre.ROOT / code / "manifest.json")
            links = pd.read_parquet(
                track(enriched_cadastre.ROOT / code / "cp_bu_documentary_links.parquet"),
                columns=[
                    "building_id",
                    "cp_reference_normalized",
                    "link_class",
                    "relation_validated",
                ],
            )
            links = links[links.link_class.eq("A") & links.relation_validated]
            bu = pd.read_parquet(
                track(enriched_cadastre.ROOT / code / "buildings_enriched.parquet"),
                columns=[
                    "building_id",
                    "source_feature_type",
                    "recovered_current_use",
                    "recovered_construction_begin",
                    "recovered_official_area",
                    "recovered_dwellings",
                    "recovered_floors_above",
                ],
            )
            bu = (
                links[["building_id", "cp_reference_normalized"]]
                .merge(bu, on="building_id", validate="one_to_one")
                .rename(columns={"cp_reference_normalized": "parcel_ref14"})
            )
        flags = construction_flags(bu)
        counts = bu.groupby("parcel_ref14").building_id.nunique()
        qualifying = bu.loc[flags.construction]
        refindex = pd.Index(cp.parcel_ref14, name="parcel_ref14")
        facts = pd.DataFrame(index=refindex)
        facts["has_construction"] = facts.index.isin(counts.index)
        facts["construction"] = facts.index.isin(qualifying.parcel_ref14)
        for f in FIELDS:
            facts[f] = facts.index.isin(bu.loc[flags[f] & flags.residential, "parcel_ref14"])
        facts["residential"] = facts.index.isin(bu.loc[flags.residential, "parcel_ref14"])
        energy = el[el.municipality_code.eq(code) & el.parcel_ref14.isin(refindex)]
        for label, sel in [
            ("certificate_count", energy),
            ("individual_certificates", energy[energy.scope.eq("individual_unit")]),
            ("whole_building_certificates", energy[energy.scope.eq("whole_building")]),
            (
                "other_certificates",
                energy[~energy.scope.isin(["individual_unit", "whole_building"])],
            ),
        ]:
            mapping = sel.groupby("parcel_ref14").certificate_id.nunique()
            facts[label] = facts.index.to_series().map(mapping).fillna(0).astype(int)
        facts["energy"] = facts.certificate_count.gt(0)
        admin_counts = (
            admin.groupby("parcel_ref14").event_id.nunique()
            if code == "28079"
            else pd.Series(dtype=int)
        )
        facts["administrative_count"] = (
            facts.index.to_series().map(admin_counts).fillna(0).astype(int)
        )
        facts["administrative"] = facts.administrative_count.gt(0)
        code_grants = gl[gl.geographic_municipality_code.eq(code)]
        grant_counts = code_grants.groupby("parcel_ref14").expediente_id.nunique()
        facts["prtr_count"] = facts.index.to_series().map(grant_counts).fillna(0).astype(int)
        facts["prtr"] = facts.prtr_count.gt(0)
        rehab_counts = (
            rehab.groupby("parcel_ref14").case_id.nunique()
            if code == "28079"
            else pd.Series(dtype=int)
        )
        facts["rehabilita_count"] = facts.index.to_series().map(rehab_counts).fillna(0).astype(int)
        facts["rehabilita"] = facts.rehabilita_count.gt(0)
        for mode, policy in [("local", dict.fromkeys(SOURCES, True)), ("public", PUBLIC_SOURCES)]:
            (
                facts[mode + "_visible"],
                facts[mode + "_level"],
                facts[mode + "_reasons"],
                facts[mode + "_families"],
            ) = assign_levels(facts, policy)
        facts["municipality_code"] = code
        facts["construction_object_count"] = (
            facts.index.to_series().map(counts).fillna(0).astype(int)
        )
        if {"x", "y"}.issubset(cp.columns):
            xy = cp.set_index("parcel_ref14")[["x", "y"]].reindex(refindex)
        else:
            bounds = sh.bounds(sh.from_wkt(cp.geometry_wkt.to_numpy()))
            xy = pd.DataFrame(
                dict(x=(bounds[:, 0] + bounds[:, 2]) / 2, y=(bounds[:, 1] + bounds[:, 3]) / 2),
                index=refindex,
            )
        facts[["x", "y"]] = xy
        facts["zone"] = (
            (facts.x // 1000).astype(int).astype(str)
            + ":"
            + (facts.y // 1000).astype(int).astype(str)
        )
        # Source WKT is copied unchanged, one unique CP per row; display projection only.
        facts["geometry_wkt"] = cp.set_index("parcel_ref14").geometry_wkt.reindex(refindex)
        facts["geometry_sha256"] = facts.geometry_wkt.map(
            lambda s: hashlib.sha256(s.encode()).hexdigest()
        )
        facts = facts.reset_index()
        facts.to_parquet(output / (code + ".parquet"), index=False, row_group_size=1024)
        rows.append(facts.drop(columns="geometry_wkt"))
        for mode in ["local", "public"]:
            admitted = facts[facts[mode + "_visible"]]
            metrics.append(
                dict(
                    municipality_code=code,
                    municipality=name,
                    mode=mode,
                    unit="accepted_distinct_cp",
                    source_rows=observed,
                    denominator=len(facts),
                    included=len(admitted),
                    excluded=len(facts) - len(admitted),
                    levels=facts[mode + "_level"].value_counts().to_dict(),
                    sources={
                        s: int((admitted[s] & (mode == "local" or PUBLIC_SOURCES[s])).sum())
                        for s in SOURCES
                    },
                    without_construction=int((~admitted.has_construction).sum()),
                    administrative_only=int(
                        (
                            admitted.administrative
                            & ~admitted.construction
                            & ~admitted.energy
                            & ~admitted.prtr
                            & ~admitted.rehabilita
                        ).sum()
                    )
                    if mode == "local"
                    else 0,
                    with_individual_ceee=int(admitted.individual_certificates.gt(0).sum())
                    if mode == "local"
                    else 0,
                    only_individual_ceee=int(
                        (
                            admitted.individual_certificates.gt(0)
                            & admitted.whole_building_certificates.eq(0)
                            & admitted.other_certificates.eq(0)
                        ).sum()
                    )
                    if mode == "local"
                    else 0,
                    multiple_evidence_families=int(admitted[mode + "_families"].ge(2).sum()),
                    administrative_source_coverage="partial_historical"
                    if code == "28079"
                    else "not_integrated",
                    postal_source_coverage="session20" if code == "28079" else "not_integrated",
                    population_sha256=hashlib.sha256(
                        "\n".join(sorted(facts.parcel_ref14)).encode()
                    ).hexdigest(),
                )
            )
        object_metrics.append(
            dict(
                code=code,
                associated_objects=len(bu),
                types=bu.source_feature_type.value_counts().to_dict(),
                residential_qualifying_objects=int(flags.construction.sum()),
            )
        )
        for label, mask in [
            ("included_residential", facts.construction),
            (
                "energy_only",
                facts.energy
                & ~facts.construction
                & ~facts.administrative
                & ~facts.prtr
                & ~facts.rehabilita,
            ),
            ("admin_only", facts.administrative & facts.local_families.eq(1)),
            ("aid_only", (facts.prtr | facts.rehabilita) & facts.local_families.eq(1)),
            ("excluded_with_construction", ~facts.local_visible & facts.has_construction),
            ("excluded_without_construction", ~facts.local_visible & ~facts.has_construction),
        ]:
            sample = facts[mask].copy()
            sample["sample_hash"] = sample.parcel_ref14.map(
                lambda r: hashlib.sha256(("catalog24:" + r).encode()).hexdigest()
            )
            for row in (
                sample.sort_values(["sample_hash", "parcel_ref14"]).head(3).to_dict("records")
            ):
                samples.append(
                    dict(
                        code=code,
                        stratum=label,
                        **{k: v for k, v in row.items() if k != "geometry_wkt"},
                    )
                )
    allcp = pd.concat(rows, ignore_index=True)
    with sqlite3.connect("file:" + str(postal_path) + "?mode=ro", uri=True) as old:
        postal = pd.read_sql_query("SELECT * FROM addresses", old)
    for mode in ["local", "public"]:
        allowed = set(
            allcp.loc[
                allcp.municipality_code.eq("28079") & allcp[mode + "_visible"], "parcel_ref14"
            ]
        )
        postal[mode + "_refs"] = postal.apply(
            lambda r: json.dumps([v for v in json.loads(r.refs) if v in allowed])
            if r.status == "confirmed"
            else "[]",
            axis=1,
        )
        postal[mode + "_visible"] = postal[mode + "_refs"].ne("[]")
    postal_metrics = []
    for mode in ["local", "public"]:
        included = postal[postal[mode + "_visible"]]
        postal_metrics.append(
            dict(
                municipality_code="28079",
                mode=mode,
                versions_total=len(postal),
                versions_included=len(included),
                versions_excluded=len(postal) - len(included),
                ndp_total=postal.access_id.nunique(),
                ndp_included=included.access_id.nunique(),
                address_literals_included=included.original.nunique(),
                index_sha256=digest(postal_path),
            )
        )
    with sqlite3.connect(output / "catalogue.sqlite") as db:
        allcp.drop(columns=["geometry_sha256"]).to_sql("parcels", db, index=False)
        postal.to_sql("addresses", db, index=False)
        db.execute("ATTACH DATABASE ? AS original", (str(postal_path.resolve()),))
        db.execute("CREATE TABLE aliases AS SELECT * FROM original.aliases")
        for sql in [
            "CREATE UNIQUE INDEX parcel_identity ON parcels(municipality_code,parcel_ref14)",
            "CREATE INDEX parcel_zone ON parcels(municipality_code,zone,local_visible,public_visible)",
            "CREATE UNIQUE INDEX address_id ON addresses(id)",
            "CREATE INDEX street_lookup ON aliases(municipality,alias,id)",
        ]:
            db.execute(sql)
        db.commit()
    for path, sha in inputs.items():
        if digest(Path(path)) != sha:
            raise ValueError("Source changed during catalogue build: " + path)
    outputs = {p.name: digest(p) for p in output.iterdir() if p.is_file()}
    policy = dict(
        version=VERSION,
        publication_sources=PUBLIC_SOURCES,
        publication_reasons=PUBLIC_REASONS,
        source_attribution={
            "construction": {
                "publisher": "Dirección General del Catastro",
                "source": "Catastro INSPIRE; productos catastrales derivados de las capturas documentadas",
                "url": "https://www.catastro.hacienda.gob.es/webinspire/",
                "terms": "Aplicar la licencia de acceso y uso correspondiente al producto fuente; no usar datos protegidos.",
            },
            "energy": {
                "publisher": "Comunidad de Madrid",
                "source": "Registro de Certificados de Eficiencia Energética de Edificios",
                "url": "https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica",
                "terms": "CC BY 4.0; conservar atribución, ámbito y fecha disponibles.",
            },
            "administrative": {
                "publisher": "Ayuntamiento de Madrid",
                "source": "Órdenes de conservación 300377, obligaciones ITE/IEE y callejero; cobertura parcial.",
                "url": "https://datos.madrid.es/dataset/300377-0-conservacion-rehabilitacion",
                "terms": "Conservar fuente y fecha. Los resultados ITE/IEE no están integrados.",
            },
            "prtr": {
                "publisher": "Visor de rehabilitación PRTR de la Comunidad de Madrid, alojado en COAM",
                "source": "API resum/all; captura 24/10/2026, actualización indicada 20/07/2026.",
                "url": "https://visorrehabilitaprtrmadrid.coam.org/",
                "terms": "Licencia específica no verificada; publicación conforme a instrucción del propietario, pendiente de autorización documental.",
            },
            "rehabilita": {
                "publisher": "Ayuntamiento de Madrid (atribución de origen declarada; fichero facilitado por el usuario)",
                "source": "PLAN_REHABILITA.zip; SHA-256 5c9ba32bb5871e5c0af2f7b15148373a694d635c8ca633a7e7d05e4bcaedd66b.",
                "url": None,
                "terms": "Procedencia oficial y licencia original no verificadas; publicación conforme a instrucción del propietario, pendiente de autorización documental.",
            },
        },
        year_range=[1000, 2026],
        positive_counts_required=True,
        same_object_requirement=True,
        administrative_types=["order", "ite_pending", "iee_pending"],
        licences_and_declarations_qualify=False,
        diagnosis_or_ranking=False,
    )
    manifest = dict(
        version=VERSION,
        validation_status="validated",
        municipalities=list(NAMES),
        inputs=inputs,
        outputs=outputs,
        policy=policy,
        code_sha256=digest(Path(__file__)),
    )
    save(output / "manifest.json", manifest)
    save(
        report / "metrics.json",
        dict(
            parcels=metrics,
            postal=postal_metrics,
            objects=object_metrics,
            public_policy=policy,
            technical_sources_untouched=True,
        ),
    )
    save(report / "review_sample.json", samples)
    pd.json_normalize(metrics).to_csv(report / "coverage_by_municipality.csv", index=False)
    pd.DataFrame(postal_metrics).to_csv(report / "postal_coverage.csv", index=False)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--report-dir", type=Path, default=REPORT)
    args = parser.parse_args()
    build(args.output_dir, args.report_dir)
