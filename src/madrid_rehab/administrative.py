"""Integración local de fuentes administrativas; nunca confirma edificio físico."""

import argparse
import hashlib
import json
import re
import resource
import shutil
import time
from pathlib import Path

import pandas as pd
import shapely as sh
from pyproj import Transformer

from .administrative_io import csv, inventory, xlsx
from .ingest import digest
from .normalize import reference, text_key

VERSION = "administrative-v1"
DEFAULT = Path("data/processed/administrative_events/session_10_final_01")
TYPES = {
    "CL": "CALLE",
    "AV": "AVENIDA",
    "AVDA": "AVENIDA",
    "PZ": "PLAZA",
    "PS": "PASEO",
    "PO": "PASEO",
    "CM": "CAMINO",
    "CT": "CARRETERA",
    "TR": "TRAVESIA",
    "GL": "GLORIETA",
    "CJ": "CALLEJON",
}
MONTHS = dict(
    zip(
        [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ],
        range(1, 13),
    )
)


def key(value):
    return re.sub(r"\s+", " ", text_key(value or "").strip())


def code(value):
    v = str(value or "").strip()
    return str(int(v.split(".")[0])) if re.fullmatch(r"\d+(?:\.0)?", v) else v


def number(value):
    m = re.fullmatch(r"\s*(\d+)\s*([A-Za-z]*)\s*", str(value or ""))
    return (str(int(m[1])), key(m[2])) if m else ("", "")


def address(street, num, qualifier="", kind=""):
    n, q = number(num)
    t = TYPES.get(key(kind), key(kind))
    return "|".join([t, key(street), n, key(qualifier) or q]) if n and key(street) else ""


def convert_coordinates(x, y, source_crs="EPSG:25830", target_crs="EPSG:4326"):
    """Conversión explícita; nunca adivina CRS a partir de valores o cabeceras."""
    return Transformer.from_crs(source_crs, target_crs, always_xy=True).transform(x, y)


def json_write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


def date_parts(row, prefix):
    try:
        y = row.get(prefix + " - Año", "")
        m = MONTHS.get(str(row.get(prefix + " - Mes", "")).lower(), row.get(prefix + " - Mes", ""))
        d = row.get(prefix + " - Día", "")
        return pd.Timestamp(year=int(y), month=int(m), day=int(d)).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def build_bridge(ndp, legacy, cp):
    """Conserva todas las relaciones oficiales; contradicción nunca elige primera RC."""
    b = pd.DataFrame(
        {
            "ndp": ndp.COD_NDP.map(code),
            "via_code": ndp.COD_VIA.map(code),
            "street": ndp.VIA_NOMBRE_ACENTOS,
            "kind": ndp.VIA_CLASE,
            "number_raw": ndp.NUMERO,
            "qualifier_raw": ndp.CALIFICADOR,
            "district_declared": ndp.DISTRITO.map(lambda v: code(v).zfill(2)),
            "x": pd.to_numeric(ndp.UTMX_ETRS.str.replace(",", "."), errors="coerce"),
            "y": pd.to_numeric(ndp.UTMY_ETRS.str.replace(",", "."), errors="coerce"),
            "number_class": ndp.CLASE_APP,
        }
    )
    old = pd.DataFrame(
        {
            "ndp": legacy["Codigo de numero"].map(code),
            "reference_raw": legacy["Parcela catastral del numero"].str.strip(),
            "legacy_via": legacy["Codigo de via"].map(code),
        }
    )
    b = b.merge(old.drop_duplicates(), on="ndp", how="outer")
    b["parcel_candidate"] = b.reference_raw.fillna("").map(lambda v: reference(v)["parcel_ref14"])
    counts = cp.groupby("parcel_ref14").size()
    districts = cp.groupby("parcel_ref14").district_code.agg(
        lambda s: s.iloc[0] if len(s) == 1 else ""
    )
    b["cp_rows"] = b.parcel_candidate.map(counts).fillna(0).astype(int)
    b["cp_district"] = b.parcel_candidate.map(districts).fillna("")
    b["district_code"] = b.cp_district.where(b.cp_district.ne(""), b.district_declared).fillna("")
    b["address_key"] = [
        address(s, n, q, t) if pd.notna(s) else ""
        for s, n, q, t in zip(b.street, b.number_raw, b.qualifier_raw, b.kind)
    ]
    b["reference_count"] = b.ndp.map(b.groupby("ndp").parcel_candidate.nunique())
    b["match_status"] = "unmatched"
    b.loc[b.parcel_candidate.notna(), "match_status"] = "candidate"
    b.loc[b.cp_rows.eq(1), "match_status"] = "confirmed"
    b.loc[b.cp_rows.gt(1), "match_status"] = "ambiguous"
    b.loc[b.reference_count.gt(1), "match_status"] = "multiparcel"
    conflict = (b.via_code.notna() & b.legacy_via.notna() & b.via_code.ne(b.legacy_via)) | (
        b.cp_district.ne("") & b.district_declared.notna() & b.cp_district.ne(b.district_declared)
    )
    # Un mismo NDP con direcciones oficiales diferentes también exige revisión.
    conflicting_ndp = b.groupby("ndp").address_key.nunique().loc[lambda s: s.gt(1)].index
    conflict |= b.ndp.isin(conflicting_ndp)
    b.loc[conflict, "match_status"] = "contradictory"
    b["parcel_ref14"] = b.parcel_candidate.where(b.match_status.eq("confirmed"), "")
    b["distance_to_cp_m"] = float("nan")
    unique_cp = cp[~cp.parcel_ref14.duplicated(keep=False)].set_index("parcel_ref14")
    valid = b.cp_rows.eq(1) & b.x.notna() & b.y.notna()
    geom = sh.from_wkt(
        unique_cp.reindex(b.loc[valid, "parcel_candidate"]).geometry_wkt.to_numpy(),
        on_invalid="ignore",
    )
    b.loc[valid, "distance_to_cp_m"] = sh.distance(
        geom, sh.points(b.loc[valid, "x"], b.loc[valid, "y"])
    )
    # Geografía contradictoria queda fuera de confirmación; nunca aproxima otra RC.
    b.loc[b.distance_to_cp_m.gt(100), ["match_status", "parcel_ref14"]] = ["contradictory", ""]
    return b


def lookup_bridge(bridge, field):
    result = {}
    available = bridge[bridge[field].fillna("").ne("")]
    multiple = available[field].duplicated(keep=False)
    columns = [field, "match_status", "parcel_ref14", "district_code", "parcel_candidate"]
    for ident, status, ref, district, candidate in available.loc[~multiple, columns].itertuples(
        index=False, name=None
    ):
        result[ident] = (
            status,
            ref if status == "confirmed" else "",
            district,
            candidate if pd.notna(candidate) else "",
        )
    for ident, group in available[multiple].groupby(field, sort=False):
        refs = set(group.parcel_ref14.dropna()) - {""}
        statuses = set(group.match_status)
        districts = set(group.district_code.dropna()) - {""}
        status = (
            "confirmed"
            if statuses == {"confirmed"} and len(refs) == 1
            else "multiparcel"
            if len(refs) > 1
            else "contradictory"
            if "contradictory" in statuses
            else "ambiguous"
            if "ambiguous" in statuses or len(group.parcel_candidate.dropna().unique()) > 1
            else "candidate"
            if "candidate" in statuses
            else "unmatched"
        )
        result[ident] = (
            status,
            next(iter(refs)) if status == "confirmed" else "",
            next(iter(districts)) if len(districts) == 1 else "",
            "|".join(sorted(set(group.parcel_candidate.dropna()))),
        )
    return result


def classify(raw):
    """Solo categorías explícitas, nunca uso residencial como rehabilitación."""
    k = key(raw)
    for term, category in [
        ("REHABILIT", "rehabilitación"),
        ("REFORMA", "reforma"),
        ("CONSERVACION", "conservación"),
        ("OBRAS DE REPARACION", "conservación"),
        ("MEDIDAS DE SEGURIDAD", "medidas de seguridad"),
        ("AMPLIACION", "ampliación"),
        ("NUEVA CONSTRUCCION", "nueva construcción"),
        ("DEMOLIC", "demolición"),
        ("PRIMERA OCUPACION", "primera ocupación"),
        ("1A OCUPACION", "primera ocupación"),
        ("ACTIVIDAD", "actividad"),
    ]:
        if term in k:
            return category
    return "no determinada"


def urban_events(frame, kind, source):
    rows = []
    for pos, r in enumerate(frame.to_dict("records"), 2):
        ident = r.get("Nº_EXPEDIENTE", "").strip()
        prefix = "FECHA_ALTA_EXPEDIENTE" if kind == "declaration" else "FECHA_ALTA"
        date = date_parts(r, prefix)
        resolution = date_parts(r, "FECHA_FIRMA_RESOLUCION")
        rows.append(
            {
                "event_type": kind,
                "original_id": ident,
                "date": resolution or date,
                "origin_date": date,
                "date_raw": r.get("FECHA_ALTA", ""),
                "year": (resolution or date)[:4],
                "ndp": code(r.get("NDP", "")),
                "street": r.get("DIRECCION", ""),
                "number_raw": r.get("Nº", ""),
                "kind_raw": r.get("VIA", ""),
                "district_declared": "",
                "address_raw": " ".join(str(r.get(c, "")) for c in ["VIA", "DIRECCION", "Nº"]),
                "description": r.get("TIPO", ""),
                "category": classify(r.get("TIPO", "")),
                "administrative_status": r.get("RESOLUCION", "presentada; ejecución desconocida"),
                "source_file": source,
                "source_row": pos,
                "page": None,
                "quality_flags": "invalid_date" if not date else "",
                "raw_json": json.dumps(r, ensure_ascii=False),
            }
        )
    return rows


def order_events(frame, source):
    rows = []
    for pos, original in enumerate(frame.to_dict("records"), 2):
        r = {key(k): v for k, v in original.items()}
        if not str(r.get("ANO", "")).strip():
            continue
        yr = str(r["ANO"]).strip()
        ident = str(r.get("NUMERO DE ORDEN", "")).strip()
        street = r.get("NOMBRE VIA (EMPLAZAMIENTO PRINCIPAL)", "")
        num = r.get("NO DE VIA", "")
        raw = r.get("EMPLAZAMIENTO PRINCIPAL", "") or " ".join(
            [r.get("TIPO DE VIA", ""), street, num]
        )
        if not street:
            # Solo una dirección simple, sin rangos ni listas, admite clave exacta candidata.
            m = re.fullmatch(r"([^,;]+?)[,\s]+(\d+\s*[A-Za-z]?)", raw.strip())
            if m:
                street, num = m.groups()
        month = str(r.get("MES", "")).strip()
        date = f"{yr}-{int(month):02d}" if month.isdigit() and 1 <= int(month) <= 12 else yr
        rows.append(
            {
                "event_type": "order",
                "original_id": ident,
                "date": date,
                "origin_date": date,
                "date_raw": date,
                "year": yr,
                "ndp": "",
                "street": street,
                "number_raw": num,
                "kind_raw": r.get("TIPO DE VIA", ""),
                "district_declared": code(r.get("CODIGO DISTRITO", "")).zfill(2)
                if r.get("CODIGO DISTRITO", "")
                else "",
                "address_raw": raw,
                "description": r.get("MOTIVO", ""),
                "category": classify(r.get("MOTIVO", "")),
                "administrative_status": "orden registrada; vigencia desconocida",
                "source_file": source,
                "source_row": pos,
                "page": None,
                "quality_flags": "",
                "raw_json": json.dumps(original, ensure_ascii=False),
            }
        )
    return rows


def pdf_events(text, source):
    rows = []
    rejected = []
    typ = "IEE" if "I.E.E." in text[:1000] else "ITE"
    header_year = re.search(r"presentar I\.T\.E\. en (20\d{2})", text[:1000])
    query = re.search(r"Datos a fecha\s+(\d+/\d+/\d+)", text)
    query_date = pd.to_datetime(query[1], dayfirst=True).strftime("%Y-%m-%d") if query else ""
    for page, content in enumerate(text.split("\f"), 1):
        lines = content.splitlines()
        header = next((line for line in lines if "Tipo Vía" in line and "C. Postal" in line), None)
        if header is None:
            continue
        starts = [header.index(s) for s in ["Tipo Vía", "Nombre de la Vía", "Nº", "C. Postal"]]
        tail_start = header.index("Fecha Max IEE" if typ == "IEE" else "Año Insp.")
        partial_start = header.index("Parcial/Total")
        for line_no, line in enumerate(lines, 1):
            if not re.search(r"\b(?:28\d{3}|null)\b", line):
                continue
            kind = line[starts[0] : starts[1]].strip()
            street = line[starts[1] : starts[2]].strip()
            num = line[starts[2] : starts[3]].strip()
            postal = line[starts[3] : tail_start].strip()
            tail = line[tail_start:partial_start].strip()
            partial = line[partial_start:].strip()
            if not re.fullmatch(r"28\d{3}|null", postal):
                rejected.append(
                    {"page": page, "line": line_no, "raw": line, "reason": "column_alignment"}
                )
                continue
            yr = (
                header_year[1]
                if header_year
                else tail[-4:]
                if re.fullmatch(r"\d{2}/\d{2}/20\d{2}", tail)
                else ""
            )
            flags = []
            n, q = number(num)
            if not n or not street or postal == "null":
                flags.append("incomplete_address")
            if n and int(n) > 1000:
                flags.append("extraordinary_number")
            if typ == "ITE" and tail != yr:
                flags.append("inspection_year_differs_from_obligation")
            rows.append(
                {
                    "event_type": typ.lower() + "_pending",
                    "original_id": "",
                    "date": f"{yr}-12-31" if yr else "",
                    "origin_date": "",
                    "date_raw": tail,
                    "year": yr,
                    "query_date": query_date,
                    "ndp": "",
                    "street": street,
                    "number_raw": num,
                    "kind_raw": kind,
                    "district_declared": "",
                    "address_raw": " ".join([kind, street, num]),
                    "description": f"{typ}; columna inspección/plazo: {tail}; Parcial/Total: {partial}",
                    "category": "obligación pendiente según consulta",
                    "administrative_status": "pendiente según consulta oficial",
                    "source_file": source,
                    "source_row": line_no,
                    "page": page,
                    "quality_flags": ";".join(flags),
                    "raw_json": json.dumps(
                        {
                            "line": line,
                            "postal": postal,
                            "partial_total": partial,
                            "inspection_or_deadline": tail,
                        },
                        ensure_ascii=False,
                    ),
                }
            )
    return rows, rejected


def match_all(events, bridge):
    ndps = lookup_bridge(bridge, "ndp")
    addresses = lookup_bridge(bridge, "address_key")
    # Sin tipo de vía solo candidato: evita homónimos y abreviaturas no verificadas.
    out = events.copy()
    out["page"] = out["page"].map(
        lambda v: str(int(v)) if isinstance(v, (int, float)) and pd.notna(v) else str(v or "")
    )
    out["address_normalized"] = [
        address(s, n, kind=t) for s, n, t in zip(out.street, out.number_raw, out.kind_raw)
    ]
    ndp_addresses = {}
    for portal in bridge[["ndp", "street", "number_raw", "qualifier_raw"]].itertuples(index=False):
        if pd.notna(portal.street):
            n, q = number(portal.number_raw)
            ndp_addresses.setdefault(portal.ndp, set()).add(
                (key(portal.street), n, key(portal.qualifier_raw) or q)
            )
    matched = []
    for row in out.itertuples():
        hit = ndps.get(row.ndp) if row.ndp else addresses.get(row.address_normalized)
        hit = hit or ("unmatched", "", "", "")
        status, ref, district, candidates = hit
        if row.ndp and row.ndp in ndp_addresses:
            n, q = number(row.number_raw)
            if n and key(row.street) and (key(row.street), n, q) not in ndp_addresses[row.ndp]:
                status, ref = "contradictory", ""
                out.at[row.Index, "quality_flags"] = (
                    row.quality_flags + ";ndp_address_disagreement"
                ).strip(";")
        if row.quality_flags or (
            row.district_declared and district and row.district_declared != district
        ):
            status, ref = "contradictory" if ref or status == "contradictory" else "unmatched", ""
        matched.append(
            (
                status,
                ref,
                district or row.district_declared,
                candidates,
                "official_ndp" if row.ndp else "exact_official_address",
            )
        )
    out[["match_status", "parcel_ref14", "district_code", "candidate_refs", "match_method"]] = (
        pd.DataFrame(matched, index=out.index)
    )
    out["match_level"] = out.match_status.map(
        lambda s: "parcel" if s == "confirmed" else "unconfirmed"
    )
    out["authority"] = "Ayuntamiento de Madrid"
    out["capture_date"] = ""  # Fecha de copia no equivale a descarga.
    out["source"] = "archivo oficial aportado por usuario; licencia no verificada"

    def identity(r):
        fields = [r.event_type, r.original_id]
        if r.event_type == "order":
            fields += [r.year, r.date, r.address_raw, r.description]  # ordinal de publicación
        if not r.original_id:
            fields += [r.address_raw, r.year, getattr(r, "query_date", ""), r.description]
        return hashlib.sha256(json.dumps(fields, ensure_ascii=False).encode()).hexdigest()

    out["event_id"] = [identity(r) for r in out.itertuples()]
    return out


def deduplicate(events):
    """Publicaciones idénticas se relacionan; identidades contradictorias se retienen fuera de CP."""
    compare = ["event_id", "address_raw", "description", "date", "ndp", "raw_json"]
    pubs = events[["event_id", "source_file", "source_row", "page"]].copy()
    out = events.drop_duplicates(compare).copy()
    conflict = out.event_id.duplicated(keep=False)
    out.loc[conflict, ["match_status", "parcel_ref14", "match_level"]] = [
        "contradictory",
        "",
        "unconfirmed",
    ]
    out["identity_conflict"] = conflict
    # Identidad estable de cada versión sin perder identidad del expediente.
    out["event_version_id"] = [
        hashlib.sha256((r.event_id + r.raw_json).encode()).hexdigest() for r in out.itertuples()
    ]
    return out.reset_index(drop=True), pubs


def run(source, output, report, raw_root):
    if output.exists():
        raise FileExistsError("Usar --output-dir nuevo")
    started = time.perf_counter()
    times = {}
    items = inventory(source, report)
    times["inventory_s"] = time.perf_counter() - started
    print("A: inventario completado", flush=True)
    output.mkdir(parents=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    cp_path = Path("data/processed/session_2/parcels_audited.parquet")
    cp_hash = digest(cp_path)
    cp = pd.read_parquet(cp_path)
    frames = {}
    rows = []
    rejects = []
    equivalence = []
    t = time.perf_counter()
    for item in items:
        p = Path(item["path_original"])
        stored = raw_root / item["sha256"] / p.name
        stored.parent.mkdir(exist_ok=True)
        existing = list(stored.parent.iterdir())
        if existing:
            stored = existing[0]
        if not stored.exists():
            shutil.copyfile(p, stored)
        if digest(stored) != item["sha256"]:
            raise ValueError("Copia corrupta")
        item["raw_copy"] = str(stored)
        item["transformation"] = (
            "XLSX XML inerte; selección explícita de campos y normalización"
            if p.suffix == ".xlsx"
            else "CSV delimitado por punto y coma; utf-8-sig/cp1252; normalización explícita"
            if p.suffix == ".csv"
            else "pdftotext -layout; extracción por columnas y página"
            if "Subv" not in str(p)
            else "Documento de convocatoria preservado; sin concesiones importables"
        )
        item["observation_period"] = item.get("years", []) if p.suffix != ".pdf" else None
        item["source_authority"] = (
            "Comunidad de Madrid / BOCM" if "Subv" in str(p) else "Ayuntamiento de Madrid"
        )
        item["download_date"] = None
        if p.suffix == ".csv":
            frames[p.name] = csv(stored)[0]
        elif p.suffix == ".xlsx":
            frames[p.name] = pd.concat(xlsx(stored).values(), ignore_index=True)
    # Verifica equivalencia CSV/XLSX en todos los campos no fecha y fechas descompuestas.
    for kind, prefix in [("declaration", "133556"), ("license", "640505")]:
        names = [n for n in frames if n.startswith(prefix)]
        csv_name = next(n for n in names if n.endswith(".csv"))
        xls_name = next(n for n in names if n.endswith(".xlsx"))
        a, b = frames[csv_name], frames[xls_name]
        cols = [c for c in a if c not in ["FECHA_ALTA", "FECHA_FIRMA_RESOLUCION"]]
        equal = a[cols].reset_index(drop=True).equals(b[cols].reset_index(drop=True))
        equivalence.append(
            {
                "csv": csv_name,
                "xlsx": xls_name,
                "rows_csv": len(a),
                "rows_xlsx": len(b),
                "non_date_and_date_parts_equal": equal,
            }
        )
        if not equal:
            raise ValueError("Versiones CSV/XLSX difieren; revisión requerida")
        rows += urban_events(a, kind, csv_name)
    for name, frame in frames.items():
        if name.startswith("300377"):
            rows += order_events(frame, name)
    for item in items:
        if item["format"] == ".pdf" and "Subv" not in item["path_original"]:
            text = (report / (item["name"] + ".txt")).read_text()
            parsed, rejected = pdf_events(text, item["name"])
            rows += parsed
            rejects += [dict(r, source_file=item["name"]) for r in rejected]
            item["observation_period"] = sorted({r["year"] for r in parsed} - {""})
            item["query_dates"] = sorted({r["query_date"] for r in parsed} - {""})
            item["extracted_records"] = len(parsed)
            item["rejected_lines"] = len(rejected)
    times["normalization_s"] = time.perf_counter() - t
    print(f"C–G: {len(rows)} filas extraídas", flush=True)
    t = time.perf_counter()
    bridge = build_bridge(
        frames["213605-4-callejero-oficial-madrid-csv.csv"],
        frames["200075-1-callejero-csv.csv"],
        cp,
    )
    bridge.to_parquet(output / "ndp_bridge.parquet", index=False)
    # Se conservan columnas y valores originales en Parquet separados, no expuestos por el visor.
    for name, frame in frames.items():
        frame.to_parquet(output / (name + ".parquet"), index=False)
    print("B: puente generado", flush=True)
    events = match_all(pd.DataFrame(rows).fillna(""), bridge)
    events, pubs = deduplicate(events)
    events.to_parquet(output / "events.parquet", index=False)
    pubs.to_parquet(output / "event_publications.parquet", index=False)
    times["bridge_matching_s"] = time.perf_counter() - t
    print("H: matching global completado", flush=True)
    t = time.perf_counter()
    audits = {}
    for typ, g in events.groupby("event_type"):
        original = sum(1 for r in rows if r["event_type"] == typ)
        counts = g.match_status.value_counts().to_dict()
        audits[typ] = {
            "original_rows": original,
            "normalized_rows": len(g),
            "rows_without_quality_flags": int(g.quality_flags.eq("").sum()),
            "technical_duplicates": original - len(g),
            "with_address": int(g.address_normalized.ne("").sum()),
            "with_ndp": int(g.ndp.ne("").sum()),
            "with_reference_candidate": int(g.candidate_refs.ne("").sum()),
            "matching": counts,
            "confirmed_rate": counts.get("confirmed", 0) / len(g),
            "years": sorted(set(g.year) - {""}),
            "outside_madrid": "unknown; absent CP does not establish other municipality",
            "quality_flags": g.quality_flags.value_counts().to_dict(),
        }
    events.groupby(["district_code", "event_type", "match_status"], dropna=False).size().rename(
        "events"
    ).reset_index().to_parquet(output / "district_summary.parquet", index=False)
    events.groupby(["event_type", "year", "category"], dropna=False).size().rename(
        "events"
    ).reset_index().to_parquet(output / "time_summary.parquet", index=False)
    for district, g in events.groupby("district_code", dropna=False):
        part = output / "districts" / (district or "unknown")
        part.mkdir(parents=True)
        g.to_parquet(part / "events.parquet", index=False)
    confirmed = events[events.match_status.eq("confirmed")]
    features = pd.read_parquet("data/processed/session_7_final/parcel_features.parquet")
    count = confirmed.groupby("parcel_ref14").event_version_id.nunique()
    profile = features.merge(
        count.rename("administrative_events_observed"), on="parcel_ref14", how="left"
    )
    profile["administrative_events_observed"] = profile.administrative_events_observed.fillna(
        0
    ).astype(int)
    profile.to_parquet(output / "parcel_profiles.parquet", index=False)
    linked = confirmed.merge(features, on="parcel_ref14", how="left", suffixes=("", "_cp"))
    linked.groupby(["event_type", "construction_period", "energy_profile"], dropna=False).agg(
        events=("event_version_id", "nunique"), parcels=("parcel_ref14", "nunique")
    ).reset_index().to_parquet(output / "observed_context.parquet", index=False)
    bridge_audit = {
        "rows": len(bridge),
        "unique_ndp": int(bridge.ndp.nunique()),
        "duplicated_ndp_rows": int(bridge.ndp.duplicated(keep=False).sum()),
        "multi_reference_ndp": int(bridge.loc[bridge.reference_count.gt(1), "ndp"].nunique()),
        "matching": bridge.match_status.value_counts().to_dict(),
        "references_present_rows": int(bridge.cp_rows.gt(0).sum()),
        "references_absent_rows": int(
            (bridge.parcel_candidate.notna() & bridge.cp_rows.eq(0)).sum()
        ),
        "invalid_reference_rows": int(
            (bridge.reference_raw.fillna("").ne("") & bridge.parcel_candidate.isna()).sum()
        ),
        "coordinates_available": int((bridge.x.notna() & bridge.y.notna()).sum()),
        "distance_denominator": int(bridge.distance_to_cp_m.notna().sum()),
        "distance_gt_100m": int(bridge.distance_to_cp_m.gt(100).sum()),
        "distance_m_quantiles": bridge.distance_to_cp_m.quantile([0, 0.5, 0.9, 0.99, 1]).to_dict(),
        "cp_source_dates": cp.source_date.dropna().unique().tolist(),
        "cp_capture_dates": cp.captured_at.dropna().unique().tolist(),
        "street_snapshot_date": None,
    }
    bridge.groupby(["district_code", "match_status"], dropna=False).size().rename(
        "rows"
    ).reset_index().to_csv(report / "bridge_districts.csv", index=False)
    bridge[bridge.match_status.ne("confirmed")].head(500).to_parquet(
        report / "bridge_review_examples.parquet", index=False
    )
    for district in ["01", "07", "06", "11", "03", "19"]:
        sample = (
            bridge[bridge.district_code.eq(district)]
            .groupby("match_status", group_keys=False)
            .head(10)
        )
        sample.to_csv(report / f"cross_validation_{district}.csv", index=False)
    events[events.match_status.ne("confirmed")].groupby("event_type", group_keys=False).head(
        50
    ).to_parquet(report / "event_review_examples.parquet", index=False)
    events[events.quality_flags.ne("")].to_parquet(output / "review_queue.parquet", index=False)
    json_write(report / "pdf_rejected_lines.json", rejects)
    json_write(report / "format_equivalence.json", equivalence)
    json_write(report / "matching.json", audits)
    json_write(report / "bridge_audit.json", bridge_audit)
    json_write(report / "inventory.json", items)
    json_write(output / "input_manifest.json", items)
    times["analytics_s"] = time.perf_counter() - t
    times["total_s"] = time.perf_counter() - started
    times["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    json_write(report / "benchmark.json", times)
    if digest(cp_path) != cp_hash:
        raise ValueError("CP modificada")
    for item in items:
        if digest(Path(item["path_original"])) != item["sha256"]:
            raise ValueError("Original modificado")
    manifest = {
        "version": VERSION,
        "cp_sha256": cp_hash,
        "input_manifest_sha256": digest(output / "input_manifest.json"),
        "code_sha256": {
            p.name: digest(p)
            for p in [Path(__file__), Path(__file__).with_name("administrative_io.py")]
        },
        "rows": len(events),
        "unique_event_ids": int(events.event_id.nunique()),
        "matching": events.match_status.value_counts().to_dict(),
        "sources": audits,
        "bridge": bridge_audit,
        "grant_status": "only_call_document_no_awards",
        "outputs": {
            str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*.parquet"))
        },
        "limitations": "parcel evidence only; source coverage unknown; no execution or current diagnosis inferred",
    }
    json_write(output / "manifest.json", manifest)
    json_write(
        report / "phases.json",
        {
            phase: "completed with limitations in matching.json, bridge_audit.json and inventory.json"
            for phase in "ABCDEFGHI"
        },
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir", type=Path, default=Path("/mnt/c/Users/apalo/Downloads/Mapas Rehab")
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--report-dir", type=Path, default=Path("reports/session_10"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/administrative"))
    a = parser.parse_args()
    m = run(a.source_dir, a.output_dir, a.report_dir, a.raw_dir)
    print(json.dumps({"rows": m["rows"], "matching": m["matching"]}, indent=2))


if __name__ == "__main__":
    main()
