"""Reproducible offline coverage census, with fixed populations and explicit units."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

import pandas as pd

from .address_search import NAMES
from .ingest import digest

REPORT = Path("reports/session_22_data_recovery")
CITY = Path("data/processed/session_7_final")
ENRICHED = Path("data/processed/cadastre/session_18_enriched_01")
ENERGY = Path("data/processed/energy/session_13_final_03")
CONSERVATION = Path("data/processed/conservation/session_14_final_02")
PARTIAL = Path("data/processed/cadastre/session_12_2_partial_validated_01")
RECOVERY = Path("data/processed/cadastre/session_22_madrid_01")
FIELDS = {
    "use": ["recovered_current_use", "current_use"],
    "year": ["recovered_construction_begin", "construction_oldest_year"],
    "area": ["recovered_official_area"],
    "dwellings": ["recovered_dwellings", "dwellings_raw"],
    "floors": ["recovered_floors_above", "recovered_floors_below"],
    "units": ["recovered_building_units", "building_units_raw"],
    "condition": ["recovered_condition"],
}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


def present(frame, names):
    result = pd.Series(False, index=frame.index)
    for name in names:
        if name in frame:
            result |= frame[name].notna() & frame[name].astype(str).str.strip().ne("")
    return result


def historic_buildings():
    columns = [
        "building_id",
        "parcel_ref14",
        "district_code",
        "current_use",
        "construction_oldest_year",
        "construction_newest_year",
        "dwellings_raw",
        "building_units_raw",
    ]
    frame = pd.concat(
        [
            pd.read_parquet(p, columns=columns)
            for p in sorted(CITY.glob("districts/*/map_buildings.parquet"))
        ],
        ignore_index=True,
    ).drop_duplicates(["building_id", "parcel_ref14", "district_code"])
    cp = pd.read_parquet(
        "data/processed/session_2/parcels_audited.parquet",
        columns=["parcel_ref14", "district_code"],
    )
    cp = cp[~cp.parcel_ref14.duplicated(keep=False)]
    frame = frame.merge(cp, on=["parcel_ref14", "district_code"], validate="many_to_one")
    return frame.drop_duplicates(["building_id", "parcel_ref14"])


def constructions(code, final):
    if code == "28079":
        frame = historic_buildings()
        if final:
            extra = pd.read_parquet(RECOVERY / "building_attributes.parquet")
            frame = frame.merge(
                extra, on=["building_id", "parcel_ref14"], how="left", validate="many_to_one"
            )
        return frame
    links = pd.read_parquet(
        ENRICHED / code / "cp_bu_documentary_links.parquet",
        columns=["building_id", "cp_reference_normalized", "link_class", "relation_validated"],
    )
    links = links[links.link_class.eq("A") & links.relation_validated]
    columns = [
        "building_id",
        "source_feature_type",
        "current_use",
        "dwellings_raw",
        "building_units_raw",
        *sorted({c for fields in FIELDS.values() for c in fields if c.startswith("recovered_")}),
    ]
    bu = pd.read_parquet(ENRICHED / code / "buildings_enriched.parquet", columns=columns)
    return (
        links[["building_id", "cp_reference_normalized"]]
        .drop_duplicates()
        .merge(
            bu.drop(columns="parcel_ref14", errors="ignore"),
            on="building_id",
            validate="one_to_one",
        )
        .rename(columns={"cp_reference_normalized": "parcel_ref14"})
    )


def cp_population(code):
    p = (
        Path("data/processed/session_2/parcels_audited.parquet")
        if code == "28079"
        else PARTIAL / code / "cp.parquet"
    )
    cp = pd.read_parquet(p, columns=["parcel_ref14", "usable_geometry"])
    return sorted(
        cp.loc[
            cp.usable_geometry & ~cp.parcel_ref14.duplicated(keep=False), "parcel_ref14"
        ].dropna()
    )


def facts(code, final, energy, grants, events):
    bu = constructions(code, final)
    result = pd.DataFrame(index=pd.Index(cp_population(code), name="parcel_ref14"))
    result["confirmed_cp"] = True
    result["address"] = False
    for field, names in FIELDS.items():
        refs = bu.loc[present(bu, names), "parcel_ref14"]
        result[field] = (
            result.index.isin(refs) if final or field not in {"units", "condition"} else False
        )
    el = energy[energy.municipality_code.eq(code)]
    result["ceee"] = result.index.isin(el.parcel_ref14)
    result["ceee_quantities"] = (
        result.index.isin(
            el.loc[
                el.consumption_status.eq("observed") | el.emissions_status.eq("observed"),
                "parcel_ref14",
            ]
        )
        if final
        else False
    )
    result["ceee_certified_area"] = (
        result.index.isin(el.loc[el.area_status.eq("observed"), "parcel_ref14"]) if final else False
    )
    gl = grants[grants.municipality_code.eq(code)]
    result["prtr"] = result.index.isin(gl.parcel_ref14)
    result["administrative_context"] = (
        result.index.isin(events.parcel_ref14) if code == "28079" else False
    )
    conserved = events[events.is_conservation_evidence]
    result["conservation"] = result.index.isin(conserved.parcel_ref14) if code == "28079" else False
    outcomes = events[events.inspection_outcome.isin(["favorable", "unfavorable"])]
    result["inspection_result"] = (
        result.index.isin(outcomes.parcel_ref14) if code == "28079" else False
    )
    useful = [
        *FIELDS,
        "ceee",
        "prtr",
        "administrative_context",
        "conservation",
        "inspection_result",
    ]
    result["useful"] = result[useful].any(axis=1)
    result["almost_empty"] = ~result.useful
    return result, bu


def qualify_metric(row):
    """Availability is measurable; missing sources never establish zero events."""
    uncovered = row["municipality_code"] != "28079" and row["field"] in {
        "conservation",
        "inspection_result",
        "administrative_context",
        "address",
    }
    row["source_coverage"] = "not_integrated" if uncovered else "partial_available_capture"
    row["quality"] = "documentary; original object scope"
    row["limitations"] = (
        "source not integrated: no occurrence rate can be inferred"
        if uncovered
        else "availability in frozen capture; no physical diagnosis or currency guarantee"
    )
    if uncovered:
        row["coverage_percent"] = None
    return row


def metrics(frame, code, unit):
    population_hash = hashlib.sha256(
        "\n".join(sorted(frame.index.astype(str))).encode()
    ).hexdigest()
    return [
        qualify_metric(
            dict(
                municipality_code=code,
                municipality=NAMES[code],
                unit=unit,
                field=field,
                numerator=int(frame[field].sum()),
                denominator=len(frame),
                coverage_percent=100 * float(frame[field].mean()) if len(frame) else None,
                population_sha256=population_hash,
                method="exact documentary keys; vectorized any per entity, no attribute sums",
                scope="available capture, not territorial completeness; attributes retain BU/certificate/case scope",
            )
        )
        for field in frame.columns
        if frame[field].dtype == bool
    ]


def run(output, final=False):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    energy_links = pd.read_parquet(ENERGY / "energy_parcel_links.parquet")
    certs = pd.read_parquet(
        ENERGY / "energy_certificates.parquet",
        columns=[
            "certificate_id",
            "identity_status",
            "date_after_capture",
            "consumption_status",
            "emissions_status",
            "area_status",
        ],
    )
    energy = energy_links.merge(certs, on="certificate_id", validate="many_to_one")
    energy = energy[
        energy.link_level.eq("A")
        & energy.identity_status.eq("unique_registration_content")
        & ~energy.date_after_capture
    ]
    grants = pd.read_parquet(PARTIAL / "grant_parcel_links.parquet")
    grants = grants[
        grants.match_status.isin(
            ["confirmed", "confirmed_reference", "confirmed_historical_madrid"]
        )
    ].copy()
    grants["municipality_code"] = grants.geographic_municipality_code
    master = pd.read_parquet(
        "data/processed/grants/session_11_final_03/grants.parquet",
        columns=["expediente_id", "identity_conflict", "territorial_quality"],
    )
    valid = master[~master.identity_conflict & ~master.territorial_quality.eq("contradictory")]
    grants = grants[grants.expediente_id.isin(valid.expediente_id)]
    events = pd.read_parquet(
        CONSERVATION / "conservation_events.parquet",
        columns=[
            "parcel_ref14",
            "match_status",
            "identity_conflict",
            "is_conservation_evidence",
            "inspection_outcome",
        ],
    )
    events = events[events.match_status.eq("confirmed") & ~events.identity_conflict]
    db = sqlite3.connect(
        "file:data/processed/addresses/session_20_01/addresses.sqlite?mode=ro", uri=True
    )
    postal = pd.read_sql_query("SELECT * FROM addresses ORDER BY id", db)
    db.close()
    records, inventory, all_facts = [], {}, {}
    for code in NAMES:
        frame, bu = facts(code, final, energy, grants, events)
        if code == "28079":
            refs = postal[postal.status.eq("confirmed")].refs.map(json.loads).explode()
            frame["address"] = frame.index.isin(refs)
        records += metrics(frame, code, "distinct_cp")
        all_facts[code] = frame
        inventory[code] = dict(
            accepted_distinct_cp=len(frame),
            associated_bu=bu.building_id.nunique(),
            source_feature_types=bu.source_feature_type.value_counts().to_dict()
            if "source_feature_type" in bu
            else {"Building": bu.building_id.nunique()},
        )
    city = all_facts["28079"]
    expanded = postal[["id", "refs", "status"]].copy()
    expanded["parcel_ref14"] = expanded.refs.map(json.loads)
    expanded = expanded.explode("parcel_ref14")
    expanded = expanded[expanded.status.eq("confirmed")]
    matched = expanded.merge(city, on="parcel_ref14", how="inner")
    by_version = matched.groupby("id")[city.columns].any().reindex(postal.id, fill_value=False)
    by_version["address"] = True
    by_version["almost_empty"] = ~by_version.useful
    records += metrics(by_version, "28079", "postal_version")
    by_access = by_version.join(postal.set_index("id").access_id).groupby("access_id").any()
    by_access["almost_empty"] = ~by_access.useful
    records += metrics(by_access, "28079", "distinct_ndp")
    # Broad potential-residential population retains unknown use and unlinked addresses.
    historic = historic_buildings()
    nonres_only = set(historic.loc[historic.current_use.notna(), "parcel_ref14"]) - set(
        historic.loc[historic.current_use.eq("1_residential"), "parcel_ref14"]
    )
    excluded_ids = set(expanded[expanded.parcel_ref14.isin(nonres_only)].id)
    eligible = postal[~postal.id.isin(excluded_ids)].copy()
    eligible["sample_hash"] = eligible.id.map(
        lambda s: hashlib.sha256(("session22:" + s).encode()).hexdigest()
    )
    sample = eligible.sort_values(["sample_hash", "id"]).head(300)
    sample_path = output.with_name(output.stem + "_sample.csv")
    sample.to_csv(sample_path, index=False)
    records += metrics(by_version.loc[sample.id], "28079", "potential_residential_sample")
    data = dict(
        stage="final" if final else "baseline",
        metrics=records,
        inventory=inventory,
        postal_inventory=dict(
            versions=len(postal),
            distinct_ndp=postal.access_id.nunique(),
            statuses=postal.status.value_counts().to_dict(),
            potential_residential_versions=len(eligible),
            sample_method="smallest SHA256(session22:id); unknown use included; excludes addresses with any exclusively nonresidential linked CP; n=300",
        ),
        definitions=dict(
            useful="any constructive attribute or usable CEEE/PRTR or confirmed administrative context",
            almost_empty="no such evidence; identity/address alone excluded",
            availability="at least one value associated to CP; never attributed to portal",
        ),
        inputs={
            str(p): digest(p)
            for p in [
                Path("data/processed/addresses/session_20_01/addresses.sqlite"),
                CITY / "manifest.json",
                ENRICHED / "manifest.json",
                ENERGY / "manifest.json",
                CONSERVATION / "manifest.json",
                PARTIAL / "manifest.json",
            ]
        },
    )
    if final:
        data["recovery_manifest_sha256"] = digest(RECOVERY / "manifest.json")
    save(output, data)
    # Individual masks support honest union-of-improvement counts.
    for code, frame in all_facts.items():
        frame.to_parquet(output.with_name(output.stem + "_" + code + ".parquet"))
    by_version.to_parquet(output.with_name(output.stem + "_postal.parquet"))
    return data


def compare(root):
    before = json.loads((root / "baseline_coverage.json").read_text())
    after = json.loads((root / "final_coverage.json").read_text())
    keys = ["municipality_code", "unit", "field"]
    a, b = pd.DataFrame(before["metrics"]), pd.DataFrame(after["metrics"])
    merged = a.merge(b, on=keys, suffixes=("_initial", "_final"), validate="one_to_one")
    assert merged.denominator_initial.equals(merged.denominator_final)
    assert merged.population_sha256_initial.equals(merged.population_sha256_final)
    merged["difference_pp"] = merged.coverage_percent_final - merged.coverage_percent_initial
    merged["cause"] = merged.apply(
        lambda r: (
            "same-object GML grossFloorArea recovered"
            if r.field == "area"
            else "preserved attribute now exposed by commercial model"
        )
        if r.difference_pp > 0
        else "no availability improvement",
        axis=1,
    )
    merged["evidence"] = (
        "documentary; attributes remain on original BU, no inferred parent or portal"
    )
    merged.to_csv(root / "coverage_comparison.csv", index=False)
    improvements = {}
    for unit in ["postal", *NAMES]:
        x = pd.read_parquet(root / ("baseline_coverage_" + unit + ".parquet"))
        y = pd.read_parquet(root / ("final_coverage_" + unit + ".parquet"))
        assert x.index.equals(y.index)
        fields = [
            *FIELDS,
            "ceee",
            "ceee_quantities",
            "ceee_certified_area",
            "prtr",
            "administrative_context",
            "conservation",
        ]
        improved = (y[fields] & ~x[fields]).any(axis=1)
        lost = (x[fields] & ~y[fields]).any(axis=1)
        improvements[unit] = dict(
            entities_with_new_field=int(improved.sum()),
            entities_losing_field=int(lost.sum()),
            denominator=len(x),
            almost_empty_before=int(x.almost_empty.sum()),
            almost_empty_after=int(y.almost_empty.sum()),
        )
    save(root / "improvements.json", improvements)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    run(args.output, args.final)
    if args.final:
        compare(args.output.parent)
