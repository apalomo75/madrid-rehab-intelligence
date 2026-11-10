"""Immutable offline Plan Rehabilita import: original DBF/point rows and postal evidence."""

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import struct
from xml.etree import ElementTree as ET
import zipfile

import pandas as pd
from pyproj import CRS

from .address_search import parse_query
from .ingest import digest

ORIGINAL = Path("/mnt/c/Users/apalo/Downloads/PLAN_REHABILITA.zip")
DEFAULT = Path("data/processed/plan_rehabilita/session_23_01")
REPORT = Path("reports/session_23_plan_rehabilita")
POSTAL = Path("data/processed/addresses/session_20_01/addresses.sqlite")
CP = Path("data/processed/session_2/parcels_audited.parquet")
BASELINE = Path("reports/session_22_data_recovery")
VERSION = "municipal-rehabilita-documentary-v1"
COMPONENTS = {
    "AC_SUBV_CO": "Accesibilidad",
    "CN_CIM_SUB": "Conservación",
    "EE_SUBV_CO": "Eficiencia energética",
    "SA_SUBV_CO": "Salubridad",
}
MONEY = ("TOT_PRES_P", "SUB_AYTO_R", *COMPONENTS)
DATES = ("BOAM_C", "BOCM_C", "FECHA_ACTU")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


def dbf(body, encoding):
    """Strict dBase fields with raw strings, physical ordinal and deletion evidence."""
    if len(body) < 33:
        raise ValueError("Truncated DBF header")
    count, header, width = struct.unpack_from("<IHH", body, 4)
    if header > len(body) or header + count * width > len(body):
        raise ValueError("Truncated DBF records")
    fields = []
    for pos in range(32, header - 1, 32):
        desc = body[pos : pos + 32]
        if desc[0] == 13:
            break
        fields.append(
            dict(
                name=desc[:11].split(b"\0")[0].decode("ascii"),
                type=chr(desc[11]),
                width=desc[16],
                decimals=desc[17],
            )
        )
    if (
        len({f["name"] for f in fields}) != len(fields)
        or sum(f["width"] for f in fields) + 1 != width
    ):
        raise ValueError("Inconsistent DBF schema")
    rows = []
    for i in range(count):
        record = body[header + i * width : header + (i + 1) * width]
        if record[:1] not in {b" ", b"*"}:
            raise ValueError("Invalid deletion marker")
        row = dict(
            source_ordinal=i + 1,
            source_deleted=record[:1] == b"*",
            source_record_sha256=hashlib.sha256(record).hexdigest(),
        )
        offset = 1
        for field in fields:
            row[field["name"]] = record[offset : offset + field["width"]].decode(encoding).strip()
            offset += field["width"]
        rows.append(row)
    return pd.DataFrame(rows), fields


def points(body):
    if (
        len(body) < 100
        or struct.unpack_from(">i", body)[0] != 9994
        or struct.unpack_from("<ii", body, 28) != (1000, 1)
    ):
        raise ValueError("Only declared point Shapefiles supported")
    if struct.unpack_from(">i", body, 24)[0] * 2 != len(body):
        raise ValueError("Invalid SHP length")
    result = []
    pos = 100
    while pos < len(body):
        ordinal, size = struct.unpack_from(">ii", body, pos)
        pos += 8
        record = body[pos : pos + size * 2]
        pos += size * 2
        if ordinal != len(result) + 1 or len(record) != size * 2:
            raise ValueError("Invalid SHP record sequence")
        typ = struct.unpack_from("<i", record)[0]
        if typ == 0:
            result.append((None, None))
        elif typ == 1 and len(record) == 20:
            result.append(struct.unpack_from("<dd", record, 4))
        else:
            raise ValueError("Unsupported SHP object")
    return result


def numeric(raw, money=False, integer=False):
    if raw is None or not str(raw).strip():
        return None, "missing"
    try:
        # DBF numeric contract is decimal dot, never locale/grouping repair.
        if not re.fullmatch(r"-?\d+(?:\.\d+)?", str(raw)):
            raise InvalidOperation
        value = Decimal(str(raw))
        if not value.is_finite() or value < 0:
            raise InvalidOperation
        if integer and value != value.to_integral_value():
            raise InvalidOperation
        if money:
            cents = value * 100
            if cents != cents.to_integral_value():
                raise InvalidOperation
            return int(cents), "observed"
        return (int(value) if integer else float(value)), "observed"
    except (InvalidOperation, ValueError, OverflowError):
        return None, "invalid"


def day(raw):
    if not raw or raw == "00000000":
        return None, "missing"
    try:
        if not re.fullmatch(r"\d{8}", raw):
            raise ValueError("Malformed DBF date")
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8])).isoformat(), "observed"
    except (ValueError, TypeError):
        return None, "invalid"


def load_layers(path):
    layers = {}
    inventory = {}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names) or any(
            i.file_size > 32 * 1024**2 for i in archive.infolist()
        ):
            raise ValueError("Duplicate or excessive ZIP member")
        for name in sorted(n[:-4] for n in names if n.endswith(".dbf")):
            encoding = archive.read(name + ".cpg").decode("ascii").strip()
            if encoding not in {"UTF-8", "UTF8"}:
                raise ValueError("Unsupported declared encoding")
            frame, fields = dbf(archive.read(name + ".dbf"), "utf-8")
            xy = points(archive.read(name + ".shp"))
            if len(frame) != len(xy):
                raise ValueError("DBF and SHP counts differ")
            crs = CRS.from_wkt(archive.read(name + ".prj").decode())
            if crs.to_epsg() != 25830:
                raise ValueError("Unexpected CRS")
            frame["point_x"] = [p[0] for p in xy]
            frame["point_y"] = [p[1] for p in xy]
            frame["source_layer"] = name
            meta = archive.read(name + ".shp.xml")
            if b"<!DOCTYPE" in meta.upper() or b"<!ENTITY" in meta.upper():
                raise ValueError("Unsafe metadata")
            tree = ET.fromstring(meta)
            frame["raw_json"] = frame[[f["name"] for f in fields]].apply(
                lambda r: encoded(r.to_dict()), axis=1
            )
            layers[name] = frame
            inventory[name] = dict(
                rows=len(frame),
                fields=fields,
                encoding=encoding,
                crs="EPSG:25830",
                source_metadata_xml=meta.decode("utf-8"),
                metadata_created=tree.findtext(".//CreaDate"),
                deleted_rows=int(frame.source_deleted.sum()),
            )
        members = [
            dict(name=i.filename, bytes=i.file_size, crc32=i.CRC) for i in archive.infolist()
        ]
    if "SUB_TOTAL_XY" not in layers:
        raise ValueError("Missing primary layer")
    return layers, inventory, members


def postal_candidates(address, postal, aliases):
    street, number, complement = parse_query(address)
    if not number:
        return postal.iloc[:0], "unparsed_address"
    ids = aliases.get(street, set())
    found = postal[
        postal.id.isin(ids) & postal.number_key.eq(number) & postal.complement_key.eq(complement)
    ]
    return found, "exact_official_alias_number_qualifier"


def consistent_case_locations(rows):
    """All documentary directions remain source rows; disagreements cannot become A."""
    return rows.DIRECCION.nunique(dropna=False) == 1 and rows.DISTRITO.nunique(dropna=False) == 1


def classify(found, source_district, cp_district):
    if found.empty:
        return "C", "no_exact_postal_correspondence", None
    refs = set()
    for value in found.refs:
        refs.update(json.loads(value))
    if set(found.status) != {"confirmed"} or found.access_id.nunique() != 1 or len(refs) != 1:
        return "B", "multiple_or_ambiguous_postal_identity", None
    ref = next(iter(refs))
    if ref not in cp_district:
        return "B", "cp_not_unique_accepted", None
    if source_district != cp_district[ref]:
        return "B", "district_disagreement", None
    return "A", "exact_official_address_unique_access_and_accepted_cp", ref


def build(path=ORIGINAL, output=DEFAULT, report=REPORT):
    path, output, report = Path(path), Path(output), Path(report)
    if output.exists():
        raise FileExistsError(output)
    if (report / "source_inventory.json").exists():
        raise FileExistsError(report / "source_inventory.json")
    report.mkdir(parents=True, exist_ok=True)
    source_sha = digest(path)
    raw = Path("data/raw/plan_rehabilita") / source_sha / path.name
    raw.parent.mkdir(parents=True, exist_ok=True)
    if raw.exists():
        if digest(raw) != source_sha:
            raise ValueError("Altered preserved original")
    else:
        shutil.copyfile(path, raw)
    layers, inventory, members = load_layers(raw)
    main = layers["SUB_TOTAL_XY"]
    allrows = pd.concat(layers.values(), ignore_index=True)
    identity_issues = set(
        main.loc[main.NUMERO_EXP.duplicated(keep=False) | main.NUMERO_EXP.eq(""), "NUMERO_EXP"]
    )
    cases = []
    issues = []
    for row in main.to_dict("records"):
        case_id = row["NUMERO_EXP"]
        item = dict(
            case_id=case_id,
            original_address=row["DIRECCION"],
            district_code=row["DISTRITO"].split("-")[0].zfill(2),
            district_original=row["DISTRITO"],
            call=row["CONVOCATOR"],
            zone=row["ZONA"],
            point_x=row["point_x"],
            point_y=row["point_y"],
            raw_json=row["raw_json"],
            source_layer="SUB_TOTAL_XY",
            source_ordinal=row["source_ordinal"],
            source_record_sha256=row["source_record_sha256"],
            source_sha256=source_sha,
            source_snapshot="FECHA_ACTU: " + row["FECHA_ACTU"],
            administrative_stage="not_individually_verified",
            source_financial_semantics="SUB_AYTO_R: sub_ayto_revisada; not payment",
            identity_usable=case_id not in identity_issues and not row["source_deleted"],
        )
        for key in MONEY:
            item[key + "_cents"], item[key + "_state"] = numeric(row[key], money=True)
        item["dwellings"], item["dwellings_state"] = numeric(row["NUM_VIVIEN"], integer=True)
        for key in DATES:
            item[key], item[key + "_state"] = day(row[key])
        case_issues = [k for k in MONEY + DATES if item[k + "_state"] == "invalid"]
        if not item["identity_usable"]:
            case_issues.append("unusable_case_identity")
        if case_issues:
            issues.append(
                dict(case_id=case_id, reason=";".join(case_issues), raw_json=row["raw_json"])
            )
        cases.append(item)
    cases = pd.DataFrame(cases)
    if cases.case_id.duplicated().any():
        # Preserve every original in source_rows/quarantine; catalogue identity only.
        cases = cases.drop_duplicates("case_id", keep="first").copy()
        for key in MONEY:
            cases.loc[~cases.identity_usable, key + "_cents"] = None
            cases.loc[~cases.identity_usable, key + "_state"] = "ambiguous_identity"
    with sqlite3.connect("file:" + str(POSTAL) + "?mode=ro", uri=True) as db:
        postal = pd.read_sql_query("SELECT * FROM addresses", db)
        alias = pd.read_sql_query("SELECT id,alias FROM aliases", db)
    aliases = alias.groupby("alias").id.agg(set).to_dict()
    cp = pd.read_parquet(CP, columns=["parcel_ref14", "district_code", "usable_geometry"])
    cp = cp[cp.usable_geometry & ~cp.parcel_ref14.duplicated(keep=False)]
    cp_district = dict(zip(cp.parcel_ref14, cp.district_code))
    locations = []
    for row in cases.itertuples():
        found, method = postal_candidates(row.original_address, postal, aliases)
        status, reason, ref = classify(found, row.district_code, cp_district)
        # Other layers cannot silently override or broaden the primary address.
        secondary = allrows[allrows.NUMERO_EXP.eq(row.case_id)]
        if not consistent_case_locations(secondary) or not row.identity_usable:
            status, reason, ref = "B", "cross_layer_identity_or_address_conflict", None
        locations.append(
            dict(
                case_id=row.case_id,
                address_original=row.original_address,
                link_class=status,
                link_reason=reason,
                parcel_ref14=ref,
                matching_method=method,
                postal_version_ids=encoded(sorted(found.id)),
                access_ids=encoded(sorted(set(found.access_id))),
                candidate_refs=encoded(sorted({v for s in found.refs for v in json.loads(s)})),
                source_layer=row.source_layer,
                source_ordinal=row.source_ordinal,
            )
        )
    locations = pd.DataFrame(locations)
    # Categories retain primary source component amounts; never add them to revised total.
    actions = []
    for row in main.to_dict("records"):
        for field, label in COMPONENTS.items():
            value, state = numeric(row[field], money=True)
            if value is not None and value > 0:
                actions.append(
                    dict(
                        case_id=row["NUMERO_EXP"],
                        category=label,
                        source_field=field,
                        component_amount_cents=value,
                        interpretation="source_component_not_reconciled_to_revised_total",
                    )
                )
    actions = pd.DataFrame(actions)
    quality = dict(
        primary_rows=len(main),
        unique_cases=main.NUMERO_EXP.nunique(),
        all_layer_rows=len(allrows),
        deleted_rows=int(allrows.source_deleted.sum()),
        primary_duplicate_id_rows=int(main.NUMERO_EXP.duplicated(keep=False).sum()),
        secondary_ids_absent_primary=sorted(set(allrows.NUMERO_EXP) - set(main.NUMERO_EXP)),
        cross_layer_multi_address_cases=int(
            (allrows.groupby("NUMERO_EXP").DIRECCION.nunique() > 1).sum()
        ),
        calls=main.CONVOCATOR.value_counts().to_dict(),
        districts=main.DISTRITO.value_counts().to_dict(),
        monetary_states={k: cases[k + "_state"].value_counts().to_dict() for k in MONEY},
        revised_subsidy_cents=int(cases.SUB_AYTO_R_cents.dropna().sum()),
        component_total_disagreement_cases=sum(
            numeric(r["SUB_AYTO_R"], money=True)[0]
            != sum(numeric(r[k], money=True)[0] or 0 for k in COMPONENTS)
            for r in main.to_dict("records")
        ),
        dates={
            k: dict(
                states=cases[k + "_state"].value_counts().to_dict(),
                min=cases[k].min(),
                max=cases[k].max(),
            )
            for k in DATES
        },
        point_vs_declared_xy_disagreements=int(
            (
                (pd.to_numeric(main.X) - main.point_x).abs().gt(0.001)
                | (pd.to_numeric(main.Y) - main.point_y).abs().gt(0.001)
            ).sum()
        ),
        layer_counts={
            k: dict(
                rows=len(v),
                cases=v.NUMERO_EXP.nunique(),
                nonprimary_repeats=int(v.NUMERO_EXP.isin(main.NUMERO_EXP).sum()),
            )
            for k, v in layers.items()
        },
        raw_rows_preserved=True,
        public_exposure=False,
        license="not_verified",
    )
    quality["cross_layer_field_disagreements"] = {
        field: int((allrows.groupby("NUMERO_EXP")[field].nunique() > 1).sum())
        for field in [
            "DIRECCION",
            "DISTRITO",
            "NUM_VIVIEN",
            "CONVOCATOR",
            "BOAM_C",
            "BOCM_C",
            "FECHA_ACTU",
        ]
    }
    output.mkdir(parents=True)
    products = dict(
        cases=cases,
        source_rows=allrows,
        locations=locations,
        actions=actions,
        finance=cases[["case_id", *[k + "_cents" for k in MONEY], *[k + "_state" for k in MONEY]]],
        quarantine=pd.DataFrame(issues, columns=["case_id", "reason", "raw_json"]),
    )
    for name, frame in products.items():
        frame.to_parquet(output / (name + ".parquet"), index=False)
    inputs = {
        str(p): digest(p)
        for p in [
            raw,
            POSTAL,
            CP,
            BASELINE / "final_coverage.json",
            BASELINE / "final_coverage_postal.parquet",
        ]
    }
    manifest = dict(
        version=VERSION,
        validation_status="validated",
        inputs=inputs,
        source_original_path=str(path),
        preserved_original=str(raw),
        source_sha256=source_sha,
        source_capture_date="not_verified; user-provided local file",
        public_exposure=False,
        license="not_verified",
        cp_sha256=digest(CP),
        postal_sha256=digest(POSTAL),
        outputs={name + ".parquet": digest(output / (name + ".parquet")) for name in products},
        code_sha256=digest(Path(__file__)),
    )
    save(output / "manifest.json", manifest)
    save(
        report / "source_inventory.json",
        dict(
            path=str(path),
            name=path.name,
            bytes=path.stat().st_size,
            sha256=source_sha,
            preserved_original=str(raw),
            members=members,
            layers=inventory,
            license="not_verified",
            provenance="user-provided ZIP; official origin of individual fields not independently attested",
        ),
    )
    save(report / "source_quality.json", quality)
    mq = dict(
        total_cases=len(cases),
        case_link_classes=locations.link_class.value_counts().to_dict(),
        confirmed_cases=locations.loc[locations.link_class.eq("A"), "case_id"].nunique(),
        unique_confirmed_cp=locations.loc[locations.link_class.eq("A"), "parcel_ref14"].nunique(),
        matching_rule="exact official postal alias + number + qualifier; all versions confirmed; one NDP and one accepted CP; same district; cross-layer address consistency",
        coordinate_only_confirmations=0,
    )
    save(report / "matching_quality.json", mq)
    coverage(output, report, postal)
    if digest(path) != source_sha:
        raise ValueError("Original changed during import")
    return manifest


def coverage(output, report, postal=None):
    if postal is None:
        with sqlite3.connect("file:" + str(POSTAL) + "?mode=ro", uri=True) as db:
            postal = pd.read_sql_query("SELECT * FROM addresses", db)
    before = pd.read_parquet(BASELINE / "final_coverage_postal.parquet")
    links = pd.read_parquet(output / "locations.parquet")
    confirmed = set(links.loc[links.link_class.eq("A"), "parcel_ref14"].dropna())
    refs = postal.refs.map(json.loads)
    has = refs.map(lambda r: bool(set(r) & confirmed)) & postal.status.eq("confirmed")
    has = pd.Series(has.to_numpy(), index=postal.id).reindex(before.index)
    assert len(before) == 214083 and not has.isna().any()
    useful = before.useful | has
    rows = []
    for field, a, b in [
        ("plan_rehabilita", pd.Series(False, index=before.index), has),
        ("useful", before.useful, useful),
        ("almost_empty", before.almost_empty, ~useful),
    ]:
        rows.append(
            dict(
                field=field,
                unit="postal_version",
                numerator_before=int(a.sum()),
                numerator_after=int(b.sum()),
                denominator=len(before),
                percent_before=float(a.mean() * 100),
                percent_after=float(b.mean() * 100),
                difference_pp=float((b.mean() - a.mean()) * 100),
                population_sha256=hashlib.sha256(
                    "\n".join(sorted(before.index)).encode()
                ).hexdigest(),
            )
        )
    for field in [
        "use",
        "year",
        "area",
        "dwellings",
        "floors",
        "ceee",
        "prtr",
        "conservation",
        "inspection_result",
    ]:
        n = int(before[field].sum())
        rows.append(
            dict(
                field=field,
                unit="postal_version",
                numerator_before=n,
                numerator_after=n,
                denominator=len(before),
                percent_before=n / len(before) * 100,
                percent_after=n / len(before) * 100,
                difference_pp=0,
                population_sha256=hashlib.sha256(
                    "\n".join(sorted(before.index)).encode()
                ).hexdigest(),
            )
        )
    pd.DataFrame(rows).to_csv(report / "coverage_before_after.csv", index=False)
    effect = dict(
        reference_population=len(before),
        new_municipal_evidence_versions=int(has.sum()),
        previously_almost_empty_rescued=int((has & before.almost_empty).sum()),
        useful_before=int(before.useful.sum()),
        useful_after=int(useful.sum()),
        almost_empty_before=int(before.almost_empty.sum()),
        almost_empty_after=int((~useful).sum()),
        cadastral_attribute_recovery_cp=0,
        cadastral_integration="probe_only_no_production",
        postal_index_sha256=digest(POSTAL),
    )
    save(report / "coverage_summary.json", effect)
    pd.DataFrame(dict(plan_rehabilita=has, useful=useful, almost_empty=~useful)).to_parquet(
        report / "coverage_masks.parquet"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ORIGINAL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--report-dir", type=Path, default=REPORT)
    args = parser.parse_args()
    build(args.input, args.output_dir, args.report_dir)
