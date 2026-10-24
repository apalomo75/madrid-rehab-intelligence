"""Parser local experimental REC. No cliente de red ni autorización de publicación.

Reglas por etiquetas y cabeceras; no validado contra una ficha REC real.
Los campos no reconocidos y los bloques originales permanecen en source_records.
"""

import hashlib
import re
from datetime import date
from html.parser import HTMLParser

from .administrative import key

SCHEMA = "rec-local-v1"
FIELDS = {
    "DIRECCION": "address_raw",
    "DIRECCION DEL ACCESO": "address_raw",
    "CODIGO POSTAL": "postal_code",
    "DISTRITO": "district_raw",
    "NDP": "ndp",
    "COD_NDP": "ndp",
    "IDENTIFICADOR NDP": "ndp",
    "ANO DE CONSTRUCCION": "construction_year_raw",
    "PROXIMA OBLIGACION": "next_obligation_raw",
    "PROXIMA OBLIGACION DE ITE/IEE": "next_obligation_raw",
    "EXPEDIENTE": "case_reference",
    "NUMERO DE EXPEDIENTE": "case_reference",
    "FECHA DE PRESENTACION": "presentation_date_raw",
    "FECHA DEL DICTAMEN": "opinion_date_raw",
    "NUMERO DE REGISTRO": "registration_raw",
    "TIPO": "inspection_type",
    "TIPO DE EXPEDIENTE": "inspection_type",
    "DICTAMEN": "opinion_raw",
    "ALCANCE": "scope_raw",
    "CAUSA": "deficiency_raw",
    "CAUSAS DE DICTAMEN DESFAVORABLE": "deficiency_raw",
    "SITUACION ADMINISTRATIVA": "status_raw",
    "SITUACION": "status_raw",
    "DEPENDENCIA ADMINISTRATIVA": "department_raw",
    "DEPENDENCIA ACTUAL": "department_raw",
    "FECHA": "event_date_raw",
    "RESOLUCION": "resolution_raw",
    "ACTUACION": "action_raw",
    "SEGUIMIENTO": "followup_raw",
    "EXPEDIENTES ANTECEDENTES": "antecedents_raw",
    "ANTECEDENTES": "antecedents_raw",
    "SUBSANACION": "remediation_raw",
}
ACCESS_FIELDS = {
    "address_raw",
    "postal_code",
    "district_raw",
    "ndp",
    "construction_year_raw",
    "next_obligation_raw",
}
CASE_RE = r"\b\d{3}/\d{4}/\d+\b"


def label(value):
    return FIELDS.get(key(value).rstrip(" :."))


class Rows(HTMLParser):
    """Tolera cierres td/tr omitidos, entidades y colspan sin índices fijos."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = []
        self.cell = None
        self.heading = None
        self.section = ""
        self.hidden = []
        self.ignored = 0

    def flush_cell(self):
        if self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None

    def flush_row(self):
        self.flush_cell()
        if any(self.row):
            self.rows.append((self.section, self.row))
        self.row = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.ignored += 1
        if tag == "input" and key(attrs.get("name", "")) in {"NDP", "COD_NDP"}:
            self.hidden.append(attrs.get("value", ""))
        if tag == "tr":
            self.flush_row()
        elif tag in {"td", "th"}:
            self.flush_cell()
            self.cell = []
        elif tag in {"h1", "h2", "h3", "h4", "legend", "caption"}:
            self.flush_row()
            self.heading = []
        elif tag in {"br", "p", "div"} and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignored = max(0, self.ignored - 1)
        if tag in {"td", "th"}:
            self.flush_cell()
        elif tag in {"tr", "table"}:
            self.flush_row()
        elif tag in {"h1", "h2", "h3", "h4", "legend", "caption"} and self.heading is not None:
            self.section = " ".join("".join(self.heading).split())
            self.heading = None

    def handle_data(self, data):
        if self.ignored:
            return
        if self.cell is not None:
            self.cell.append(data)
        if self.heading is not None:
            self.heading.append(data)


def administrative_state(opinion, status, remediation=""):
    """Derivación reversible; nunca equipara archivo/terminación con obras."""
    opinion, status, remediation = key(opinion), key(status), key(remediation)
    pending = bool(re.fullmatch(r"PENDIENTE (?:DE )?SUBSANACION(?: DE DEFICIENCIAS)?[. ]*", status))
    resolved = remediation in {"SUBSANACION ACREDITADA", "DEFICIENCIAS SUBSANADAS"}
    if (pending and resolved) or (opinion == "FAVORABLE" and pending):
        return "contradictory"
    if opinion == "DESFAVORABLE" and resolved:
        return "unfavorable_remediation_evidenced"
    if re.match(r"^ARCHIVAD[OA](?:$|[ .;])", status):
        return "archived_material_outcome_unknown"
    if opinion == "DESFAVORABLE" and pending:
        return "unfavorable_explicitly_pending"
    if opinion == "FAVORABLE":
        return "favorable"
    if status == "EN TRAMITACION":
        return "in_progress"
    return "unknown"


def parse_date(value):
    if not value:
        return "", ""
    try:
        d, m, y = map(int, value.split("/"))
        return date(y, m, d).isoformat(), ""
    except (ValueError, TypeError):
        return "", "unparsed_date"


def ident(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def parse_rec(content, *, source_id, observed_at, synthetic=False, encoding=None):
    """Analiza bytes legítimos aportados por el llamante, sin descargar nada.

    source_id debe identificar el archivo preservado. observed_at es fecha de
    observación, nunca se usa como fecha administrativa. synthetic viaja en todas
    las entidades y este módulo no escribe productos de producción.
    """
    if not isinstance(content, bytes):
        raise TypeError("Se requieren bytes para conservar su SHA-256")
    date.fromisoformat(observed_at[:10])
    if encoding is None:
        try:
            text = content.decode("utf-8-sig")
            encoding = "utf-8-sig"
        except UnicodeDecodeError:
            encoding = "iso-8859-1"
            text = content.decode(encoding)
    else:
        text = content.decode(encoding)
    parser = Rows()
    parser.feed(text)
    parser.flush_row()
    sha = hashlib.sha256(content).hexdigest()
    provenance = dict(
        source_id=source_id,
        source_sha256=sha,
        observed_at=observed_at,
        synthetic=synthetic,
        schema_version=SCHEMA,
        public_exposure=False,
    )
    access = dict(provenance)
    warnings, blocks = [], []
    if parser.hidden:
        values = set(parser.hidden) - {""}
        if len(values) == 1:
            access["ndp"] = next(iter(values))
        elif values:
            warnings.append("conflicting_ndp")
    current, headers, section_before, local_section = {}, None, None, ""

    def flush():
        nonlocal current
        if current:
            blocks.append(current)
            current = {}

    for section, cells in parser.rows:
        if section != section_before:
            flush()
            headers = None
            section_before = section
            local_section = section
        section = local_section
        fields = [label(c) for c in cells]
        # Single-cell table headings also delimit records (including legacy HTML).
        if (
            len(cells) == 1
            and not fields[0]
            and re.search(
                r"\b(ITE|IEE|ORDEN|ORDENES|MULTA|MULTAS|ANTECEDENTES|RESOLUCIONES)\b", key(cells[0])
            )
        ):
            flush()
            local_section = cells[0]
            headers = None
            continue
        if sum(f is not None for f in fields) >= 2 and all(f is not None for f in fields):
            flush()
            headers = fields
            continue
        pairs = []
        if fields and fields[0] and len(cells) >= 2:
            # Alternating label/value pairs, irrespective of colspan.
            for i in range(0, len(cells) - 1, 2):
                if label(cells[i]):
                    pairs.append((label(cells[i]), cells[i + 1]))
        elif headers:
            flush()
            pairs = list(zip(headers, cells))
            if len(cells) != len(headers):
                warnings.append("incomplete_table_row")
        else:
            warnings.append("unrecognized_row")
        for field, value in pairs:
            if field in ACCESS_FIELDS:
                if field in access and access[field] != value:
                    warnings.append("conflicting_" + field)
                else:
                    access[field] = value
                continue
            if field == "case_reference" and "case_reference" in current:
                flush()
            current.setdefault("section_raw", section)
            if field in current and current[field] != value:
                warnings.append("repeated_field_" + field)
                current[field] += " | " + value
            else:
                current[field] = value
    flush()
    access["access_id"] = (
        ident("28079", access.get("ndp", "")) if access.get("ndp") else ident(sha, "access")
    )
    accesses, inspections, events, deficiencies, relations, cases = [access], [], [], [], [], {}
    seen = set()
    for block in blocks:
        ref = block.get("case_reference", "")
        case_id = ident("Ayuntamiento de Madrid", ref) if re.fullmatch(CASE_RE, ref) else ""
        if ref and not case_id:
            warnings.append("unrecognized_case_reference")
        if case_id:
            cases.setdefault(
                case_id,
                dict(case_id=case_id, case_reference=ref, authority="Ayuntamiento de Madrid"),
            )
            relations.append(
                dict(access_id=access["access_id"], case_id=case_id, relation="observed_on_access")
            )
        row = dict(provenance, **block, case_id=case_id, access_id=access["access_id"])
        flags = []
        for field in ["presentation_date_raw", "opinion_date_raw", "event_date_raw"]:
            parsed, flag = parse_date(row.get(field, ""))
            row[field.removesuffix("_raw")] = parsed
            if flag:
                flags.append(flag + ":" + field)
            if parsed and parsed > observed_at[:10]:
                flags.append("date_after_observation")
        if (
            row["opinion_date"]
            and row["presentation_date"]
            and row["opinion_date"] > row["presentation_date"]
        ):
            flags.append("opinion_after_presentation_requires_review")
        row["quality_flags"] = "|".join(flags)
        row["derived_state"] = administrative_state(
            row.get("opinion_raw", ""), row.get("status_raw", ""), row.get("remediation_raw", "")
        )
        row["record_id"] = ident(case_id, str(sorted(block.items())))
        if row["record_id"] in seen:
            continue
        seen.add(row["record_id"])
        kind = key(block.get("inspection_type", ""))
        section = key(block.get("section_raw", ""))
        if not kind and section in {"ITE", "IEE"}:
            kind = section
        if kind in {"ITE", "IEE"} and case_id:
            row["inspection_type"] = kind
            inspections.append(row)
            if block.get("deficiency_raw"):
                deficiencies.append(
                    dict(
                        provenance,
                        inspection_id=row["record_id"],
                        original_code="",
                        description_raw=block["deficiency_raw"],
                        category="unmapped",
                        interpretation_quality="literal_only",
                    )
                )
        else:
            row["event_kind"] = (
                "coercive_fine"
                if "MULTA COERCITIVA" in section
                else "execution_order"
                if "ORDEN" in section
                else "administrative_event"
            )
            events.append(row)
        for antecedent in re.findall(CASE_RE, block.get("antecedents_raw", "")):
            ancestor_id = ident("Ayuntamiento de Madrid", antecedent)
            cases.setdefault(
                ancestor_id,
                dict(
                    case_id=ancestor_id,
                    case_reference=antecedent,
                    authority="Ayuntamiento de Madrid",
                ),
            )
            relations.append(
                dict(case_id=case_id, related_case_id=ancestor_id, relation="antecedent")
            )
    result = {
        "accesses": accesses,
        "cases": list(cases.values()),
        "inspections": inspections,
        "events": events,
        "deficiencies": deficiencies,
        "relations": list({str(sorted(r.items())): r for r in relations}.values()),
        "source_records": [
            dict(
                provenance,
                encoding=encoding,
                rows=parser.rows,
                blocks=blocks,
                warnings=sorted(set(warnings)),
                validation="synthetic_only" if synthetic else "requires_real_layout_review",
            )
        ],
    }
    return {name: rows for name, rows in result.items() if rows}
