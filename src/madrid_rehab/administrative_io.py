"""Lectura inerte de CSV, XML de XLSX y PDF de texto mediante Poppler."""

import json
import re
import subprocess
from datetime import datetime, timezone
from zipfile import ZipFile
from xml.etree import ElementTree as E
import pandas as pd

from .ingest import digest

N = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def xlsx(p):
    result = {}
    with ZipFile(p) as z:
        if (
            any(i.file_size > 256 * 1024**2 for i in z.infolist())
            or sum(i.file_size for i in z.infolist()) > 512 * 1024**2
        ):
            raise ValueError("XLSX supera el límite de expansión segura")
        ss = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss = [
                "".join(t.text or "" for t in x.iter("{" + N["m"] + "}t"))
                for x in E.fromstring(z.read("xl/sharedStrings.xml"))
            ]
        for name in z.namelist():
            if not re.fullmatch(r"xl/worksheets/sheet\d+.xml", name):
                continue
            rows = []
            for r in E.fromstring(z.read(name)).findall(".//m:row", N):
                vals = {}
                for c in r:
                    col = re.match("[A-Z]+", c.get("r")).group()
                    i = 0
                    for a in col:
                        i = i * 26 + ord(a) - 64
                    v = c.find("m:v", N)
                    v = (
                        v.text
                        if v is not None
                        else "".join(t.text or "" for t in c.findall(".//m:t", N))
                    )
                    vals[i - 1] = ss[int(v)] if c.get("t") == "s" and v else v
                rows.append([vals.get(i, "") for i in range(max(vals, default=-1) + 1)])
            if rows:
                h = rows[0]
                result[name] = pd.DataFrame(
                    [r[: len(h)] + [""] * max(0, len(h) - len(r)) for r in rows[1:]], columns=h
                ).fillna("")
    return result


def csv(p):
    for enc in ["utf-8-sig", "cp1252"]:
        try:
            return pd.read_csv(p, sep=";", encoding=enc, dtype=str, keep_default_na=False), enc
        except UnicodeError:
            pass


def inventory(root, out):
    out.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        item = {
            "path_original": str(p),
            "name": p.name,
            "bytes": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(),
            "format": p.suffix.lower(),
            "source_type": p.parent.name,
            "sha256": digest(p),
            "capture_date": None,
            "license_verified": None,
            "schema_version": "administrative-v1",
            "limitations": "mtime no acredita fecha de descarga; licencia no verificada",
        }
        try:
            if p.suffix == ".csv":
                d, enc = csv(p)
                sheets = {"csv": d}
                item["encoding"] = enc
            elif p.suffix == ".xlsx":
                sheets = xlsx(p)
            else:
                txt = subprocess.check_output(["pdftotext", "-layout", str(p), "-"], text=True)
                (out / (p.name + ".txt")).write_text(txt)
                item.update(
                    pages=len(txt.rstrip("\f\n").split("\f")),
                    years=sorted(set(re.findall(r"\b20\d{2}\b", txt))),
                    quality="texto extraíble; años incluyen normativa, no equivalen a periodo observado",
                    query_dates=sorted(set(re.findall(r"Datos a fecha\s+(\d+/\d+/\d+)", txt))),
                )
                sheets = {}
            if sheets:
                item["sheets"] = {
                    k: {
                        "records": len(d),
                        "nonempty_records": int(d.ne("").any(axis=1).sum()),
                        "blank_rows": int(d.eq("").all(axis=1).sum()),
                        "columns": list(d),
                        "sample": d.head(3).to_dict("records"),
                    }
                    for k, d in sheets.items()
                }
                item["sheet_count"] = len(sheets) if p.suffix == ".xlsx" else None
                item["records"] = sum(len(d) for d in sheets.values())
                item["years"] = sorted(
                    {
                        v.strip()
                        for d in sheets.values()
                        for c in d
                        if "AÑO" in c.upper() or "ANO" == c.upper()
                        for v in d[c].astype(str)
                        if re.fullmatch(r"20\d{2}", v.strip())
                    }
                )
                item["quality"] = "esquema observado; pendiente controles semánticos"
        except Exception as e:
            item["error"] = str(e)
        items.append(item)
    for item in items:
        item["identical_files"] = [
            i["path_original"] for i in items if i["sha256"] == item["sha256"] and i is not item
        ]
    (out / "inventory.json").write_text(json.dumps(items, ensure_ascii=False, indent=2))
    return items
