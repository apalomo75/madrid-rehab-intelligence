"""Ingesta municipal oficial, con originales verificables y sin consultas por inmueble."""

import argparse
import codecs
import hashlib
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pyproj import Transformer
from shapely import from_wkt, is_valid, bounds

from .normalize import certification_scope, reference, split_references, text_key
from .sources import local_name, parse_buildings, parse_parcels

ATOM = "http://www.w3.org/2005/Atom"
PACKAGE = "https://datos.comunidad.madrid/api/3/action/package_show?id=registro_certificados_eficiencia_energetica"
FEEDS = {
    "edificios": "https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/28/ES.SDGC.bu.atom_28.xml",
    "parcelas": "https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/28/ES.SDGC.CP.atom_28.xml",
}
MAX_FILE = 160 * 1024**2
MAX_TOTAL = 320 * 1024**2


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class Archive:
    """Descargas secuenciales, límite efectivo, caché comprobada y escritura atómica."""

    def __init__(self, root, offline=False):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.total = 0

    def fetch(self, url, name):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "datos.comunidad.madrid",
            "www.catastro.hacienda.gob.es",
        }:
            raise ValueError("Origen de descarga no permitido")
        path = self.root / name
        meta = path.with_suffix(path.suffix + ".json")
        if path.exists() and meta.exists():
            record = json.loads(meta.read_text())
            if record["url"] != url or record["sha256"] != digest(path):
                raise ValueError("Original o URL de caché alterado")
            return path, record
        if self.offline:
            raise ValueError(f"Falta original para reproducción offline: {name}")
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MadridRehab/0.2 official-bulk-ingestion",
                "Accept-Encoding": "identity",
            },
        )
        partial = path.with_suffix(path.suffix + ".part")
        try:
            with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as out:
                if urllib.parse.urlsplit(response.geturl()).hostname != parsed.hostname:
                    raise ValueError("Redirección fuera del origen")
                length = response.headers.get("Content-Length")
                limit = min(MAX_FILE, MAX_TOTAL - self.total)
                if length and int(length) > limit:
                    raise ValueError("Paquete supera presupuesto; usar subconjunto WFS geográfico")
                count = 0
                while block := response.read(min(1024**2, limit - count + 1)):
                    count += len(block)
                    if count > limit:
                        raise ValueError("Descarga supera presupuesto")
                    out.write(block)
                if length and count != int(length):
                    raise ValueError("Descarga truncada")
                out.flush()
                record = {
                    "url": url,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "bytes": count,
                    "headers": dict(response.headers),
                    "sha256": digest(partial),
                }
            partial.replace(path)
            save_json(meta, record)
            self.total += count
            print(f"Descargado {name}: {count:,} bytes", flush=True)
            return path, record
        finally:
            partial.unlink(missing_ok=True)


def madrid_entry(body):
    root = ET.fromstring(body)
    entries = [
        e
        for e in root.findall(f"{{{ATOM}}}entry")
        if (e.findtext(f"{{{ATOM}}}title") or "").strip().startswith("28900-MADRID ")
    ]
    if len(entries) != 1:
        raise ValueError("El feed no identifica un único Madrid municipio (código catastral 28900)")
    entry = entries[0]
    links = [
        e.attrib["href"] for e in entry.findall(f"{{{ATOM}}}link") if e.get("rel") == "enclosure"
    ]
    if len(links) != 1:
        raise ValueError("Enclosure municipal ambiguo")
    return links[0], {
        "title": entry.findtext(f"{{{ATOM}}}title"),
        "updated": entry.findtext(f"{{{ATOM}}}updated"),
        "rights": root.findtext(f"{{{ATOM}}}rights"),
    }


def normalize_certificates(frame, scope_map):
    required = {"edif_muni", "edif_tipo", "edif_codreg", "edif_fecha", "edif_refcat"}
    if not required <= set(frame.columns):
        raise ValueError(f"Faltan columnas CEEE: {required - set(frame.columns)}")
    frame = frame.fillna("").astype(str)
    frame = frame[frame.edif_muni.map(lambda s: text_key(s).strip()) == "MADRID"].copy()
    columns = sorted(frame.columns)
    # No incluye año/recurso: solo contenido fuente; códigos iguales con contenido distinto sobreviven.
    frame["record_id"] = [
        hashlib.sha256(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        for row in frame[columns].itertuples(index=False, name=None)
    ]
    frame["certificate_scope"] = frame.edif_tipo.map(lambda s: certification_scope(s, scope_map))
    frame["certificate_date"] = pd.to_datetime(frame.edif_fecha, errors="coerce", dayfirst=True)
    for field in ("edif_superf", "norenov_global", "norenov_co2global"):
        if field in frame:
            frame[field + "_numeric"] = pd.to_numeric(
                frame[field].str.replace(",", ".", regex=False), errors="coerce"
            )
    frame["parcel_references"] = frame.edif_refcat.map(
        lambda s: sorted(
            {r["parcel_ref14"] for v in split_references(s) if (r := reference(v))["parcel_ref14"]}
        )
    )
    frame["municipality_code"] = "28079"
    frame["scope_mapping_version"] = "ceee-reviewed-2026-10-22-v1"
    return frame


def csv_encoding(stream):
    sample = stream.read(65536)
    stream.seek(0)
    try:
        codecs.getincrementaldecoder("utf-8-sig")().decode(sample, final=False)
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "latin-1"


def read_energy(path):
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = [i for i in archive.infolist() if i.filename.lower().endswith(".csv")]
            if len(members) != 1 or members[0].file_size > 1024**3:
                raise ValueError("ZIP CEEE inesperado")
            with archive.open(members[0]) as stream:
                yield from pd.read_csv(
                    stream,
                    sep=";",
                    dtype=str,
                    encoding=csv_encoding(stream),
                    chunksize=20000,
                    keep_default_na=False,
                )
    else:
        with path.open("rb") as stream:
            yield from pd.read_csv(
                stream,
                sep=";",
                dtype=str,
                encoding=csv_encoding(stream),
                chunksize=20000,
                keep_default_na=False,
            )


def cadastral_rows(path, kind, strict_count=False):
    target = "Building" if kind == "edificios" else "CadastralParcel"
    parser = parse_buildings if kind == "edificios" else parse_parcels
    with zipfile.ZipFile(path) as archive:
        members = [
            i
            for i in archive.infolist()
            if i.filename.lower().endswith(".gml")
            and (
                ("building.gml" in i.filename.lower())
                if kind == "edificios"
                else "cadastralparcel.gml" in i.filename.lower()
            )
        ]
        if len(members) != 1 or members[0].file_size > 2 * 1024**3:
            raise ValueError(f"Miembros GML inesperados: {[i.filename for i in members]}")
        print(f"Leyendo {members[0].filename}: {members[0].file_size:,} bytes GML", flush=True)
        with archive.open(members[0]) as stream:
            root = None
            seen = 0
            expected = None
            for event, element in ET.iterparse(stream, events=("start", "end")):
                if root is None:
                    root = element
                    declared = root.get("numberReturned")
                    expected = int(declared) if declared and declared.isdigit() else None
                if event == "end" and local_name(element.tag) == target:
                    yield parser(ET.tostring(element))[0]
                    seen += 1
                    if seen % 25000 == 0:
                        print(f"{kind}: {seen:,} objetos leídos", flush=True)
                    element.clear()
                    root.clear()
            if expected is not None and seen != expected:
                if strict_count:
                    raise ValueError(f"Colección incompleta: cabecera {expected}; objetos {seen}")
                print(f"AVISO {kind}: cabecera declara {expected}; XML contiene {seen}", flush=True)


def geometry_quality(frame):
    geometry = from_wkt(frame.geometry_wkt.fillna("").to_numpy(), on_invalid="ignore")
    frame["geometry_valid"] = is_valid(geometry)
    box = bounds(geometry)
    frame["geometry_in_madrid_envelope"] = (
        (box[:, 0] > 350000) & (box[:, 2] < 500000) & (box[:, 1] > 4400000) & (box[:, 3] < 4550000)
    )
    return frame


def run(raw_dir, output_dir, offline=False):
    raw, out = Path(raw_dir), Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "informe_ingesta.md").exists():
        raise ValueError("Salida existente; usar un directorio nuevo")
    archive = Archive(raw, offline)
    catalog_path, catalog_meta = archive.fetch(PACKAGE, "catalog.json")
    catalog = json.loads(catalog_path.read_bytes())
    if not catalog.get("success"):
        raise ValueError("Catálogo CKAN sin success")
    scope_map = json.loads(Path("config/sample.json").read_text())["scope_map"]
    normalized, energy_stats = [], {}
    for year in (2025, 2026):
        matches = [
            r for r in catalog["result"]["resources"] if r["name"] == f"Registro CEEE {year}"
        ]
        if len(matches) != 1:
            raise ValueError(f"Recurso {year} ambiguo o ausente")
        resource = matches[0]
        path, meta = archive.fetch(
            resource["url"], f"certificados_{year}" + Path(resource["url"]).suffix
        )
        rows, madrid = 0, 0
        for chunk in read_energy(path):
            rows += len(chunk)
            cleaned = normalize_certificates(chunk, scope_map)
            madrid += len(cleaned)
            cleaned["source_url"] = resource["url"]
            cleaned["source_resource_id"] = resource["id"]
            cleaned["source_year"] = year
            cleaned["source_sha256"] = meta["sha256"]
            cleaned["captured_at"] = meta["captured_at"]
            normalized.append(cleaned)
        energy_stats[str(year)] = {
            "downloaded_rows": rows,
            "madrid_rows": madrid,
            "bytes": meta["bytes"],
            "original": meta,
            "columns": list(chunk.columns),
        }
    cert = pd.concat(normalized, ignore_index=True)
    occurrences = cert.groupby("record_id", sort=False).agg(
        source_occurrences=("record_id", "size"),
        source_years=("source_year", lambda s: sorted(set(s))),
        source_urls=("source_url", lambda s: sorted(set(s))),
    )
    before = len(cert)
    cert = cert.drop_duplicates("record_id").merge(
        occurrences, on="record_id", validate="one_to_one"
    )
    stats = {
        "normalization": {
            "scope_map": scope_map,
            "scope_map_version": "ceee-reviewed-2026-10-22-v1",
            "deduplication": "all_original_columns_exact_content",
            "numeric_decimal_separator": ",",
        },
        "energy": energy_stats,
        "technical_duplicates_removed": before - len(cert),
        "catalog_license": catalog["result"].get("license_title"),
        "catalog": catalog_meta,
    }
    tables = {}
    for kind, feed_url in FEEDS.items():
        feed_path, feed_meta = archive.fetch(feed_url, f"{kind}_atom.xml")
        zip_url, entry = madrid_entry(feed_path.read_bytes())
        path, meta = archive.fetch(zip_url, f"{kind}_28900.zip")
        frame = geometry_quality(pd.DataFrame(cadastral_rows(path, kind)))
        identity = "building_id" if kind == "edificios" else "parcel_id"
        frame["source_record_position"] = range(len(frame))
        frame["record_id"] = [
            hashlib.sha256(f"{meta['sha256']}:{i}".encode()).hexdigest() for i in range(len(frame))
        ]
        frame["source_identifier_duplicated"] = frame[identity].duplicated(keep=False)
        frame["source_identifier_missing"] = frame[identity].isna()
        with zipfile.ZipFile(path) as source_zip:
            member = next(
                n
                for n in source_zip.namelist()
                if n.endswith("building.gml" if kind == "edificios" else "cadastralparcel.gml")
            )
            with source_zip.open(member) as source_gml:
                _, header = next(ET.iterparse(source_gml, events=("start",)))
                declared = header.get("numberReturned")
                declared_count = int(declared) if declared and declared.isdigit() else None
                source_timestamp = header.get("timeStamp")
        frame["source_url"] = zip_url
        frame["source_sha256"] = meta["sha256"]
        frame["captured_at"] = meta["captured_at"]
        frame["source_date"] = entry["updated"]
        frame["municipality_code"] = "28079"
        frame["geographic_scope"] = "Madrid municipio completo; código Catastro 28900"
        frame["entity_scope"] = (
            "cadastral_building_aggregate" if kind == "edificios" else "cadastral_parcel"
        )
        frame["link_quality"] = "authority_parcel_reference"
        tables[kind] = frame
        stats[kind] = {
            "rows": len(frame),
            "declared_rows": declared_count,
            "declared_minus_parsed_rows": declared_count - len(frame)
            if declared_count is not None
            else None,
            "gml_timestamp": source_timestamp,
            "unique_source_identifiers": int(frame[identity].nunique()),
            "rows_with_repeated_source_identifier": int(frame.source_identifier_duplicated.sum()),
            "missing_source_identifiers": int(frame.source_identifier_missing.sum()),
            "invalid_geometries": int((~frame.geometry_valid).sum()),
            "outside_madrid_envelope": int((~frame.geometry_in_madrid_envelope).sum()),
            "missing_geometry": int(frame.geometry_wkt.isna().sum()),
            "entry": entry,
            "archive": meta,
            "feed": feed_meta,
        }
        print(f"{kind}: {len(frame):,} registros", flush=True)
    parcels = tables["parcelas"]
    counts = parcels.parcel_ref14.value_counts()
    buildings = tables["edificios"]
    buildings["parcel_reference_normalized"] = (
        buildings.parcel_ref14.fillna("").str.strip().str.upper()
    )
    buildings["link_quality"] = buildings.parcel_reference_normalized.map(
        lambda ref: "missing_reference"
        if not ref
        else "authority_parcel_reference"
        if counts.get(ref, 0) == 1
        else "ambiguous"
        if counts.get(ref, 0) > 1
        else "authority_not_found"
    )
    stats["edificios"]["parcel_link_quality"] = buildings.link_quality.value_counts().to_dict()
    cert["parcel_link_quality"] = cert.parcel_references.map(
        lambda refs: (
            "invalid_or_unsupported_reference"
            if not len(refs)
            else "authority_parcel_reference"
            if all(counts.get(r, 0) == 1 for r in refs)
            else "ambiguous"
            if any(counts.get(r, 0) > 1 for r in refs)
            else "authority_not_found"
        )
    )
    cert["building_link_quality"] = "unresolved_physical_building"
    cert["geographic_scope"] = "Madrid capital; filtro literal normalizado edif_muni=MADRID"
    tables["certificados"] = cert
    transformer = Transformer.from_crs(25830, 4326, always_xy=True)
    valid_points = parcels.dropna(subset=["x", "y"])
    lon, lat = transformer.transform(valid_points.x.to_numpy(), valid_points.y.to_numpy())
    if not len(valid_points) or not ((lon > -5) & (lon < -2) & (lat > 39) & (lat < 42)).all():
        raise ValueError("Verificación CRS fallida")
    stats["crs_check"] = {
        "source": "EPSG:25830",
        "target": "EPSG:4326",
        "always_xy": True,
        "points_checked": len(valid_points),
        "finite_madrid_envelope": True,
    }
    stats["certificates"] = {
        "rows": len(cert),
        "scope_counts": cert.certificate_scope.value_counts().to_dict(),
        "parcel_link_quality": cert.parcel_link_quality.value_counts().to_dict(),
        "invalid_dates": int(cert.certificate_date.isna().sum()),
        "scope_raw_unknown_counts": cert.loc[cert.certificate_scope == "unknown", "edif_tipo"]
        .value_counts()
        .to_dict(),
        "numeric_conversion_failures": {
            field: int(((cert[field] != "") & cert[field + "_numeric"].isna()).sum())
            for field in ("edif_superf", "norenov_global", "norenov_co2global")
            if field in cert
        },
        "repeated_certificate_codes": int(cert.edif_codreg.duplicated().sum()),
    }
    stats["outputs"] = {}
    for kind, frame in tables.items():
        path = out / f"{kind}_madrid.parquet"
        frame.to_parquet(path, index=False)
        reread = pd.read_parquet(path)
        if len(reread) != len(frame):
            raise ValueError("Roundtrip Parquet incorrecto")
        stats["outputs"][path.name] = {
            "rows": len(frame),
            "sha256": digest(path),
            "columns": {c: str(t) for c, t in reread.dtypes.items()},
        }
    save_json(out / "ingestion_metrics.json", stats)
    report = (
        "# Informe de ingesta de Madrid\n\n"
        + f"Captura UTC: {datetime.now(timezone.utc).isoformat()}.\n\n"
    )
    report += "| Tabla | Registros |\n| --- | ---: |\n"
    report += "".join(f"| {k}_madrid.parquet | {len(v):,} |\n" for k, v in tables.items())
    report += "\n## Controles de calidad\n\n"
    report += f"Duplicados técnicos eliminados: {stats['technical_duplicates_removed']:,}. "
    report += f"Ámbito desconocido: {int((cert.certificate_scope == 'unknown').sum()):,}. "
    report += f"Fechas no convertibles: {stats['certificates']['invalid_dates']:,}.\n\n"
    report += "| Cartografía | Sin geometría | Topología inválida (incluye ausentes) | Fuera de envolvente (incluye ausentes) |\n| --- | ---: | ---: | ---: |\n"
    for kind in FEEDS:
        q = stats[kind]
        report += f"| {kind} | {q['missing_geometry']:,} | {q['invalid_geometries']:,} | {q['outside_madrid_envelope']:,} |\n"
    report += f"\nPuntos CP reproyectados y verificados: {len(valid_points):,}. "
    report += "Las tres tablas se han vuelto a leer desde Python después de su escritura.\n"
    for kind in FEEDS:
        q = stats[kind]
        report += f"\n{kind}: {q['unique_source_identifiers']:,} identificadores oficiales distintos; {q['rows_with_repeated_source_identifier']:,} filas con identificador repetido. "
        report += f"Registros declarados en cabecera: {q['declared_rows']}; diferencia declarados menos leídos: {q['declared_minus_parsed_rows']}.\n"
    report += "\n## Procedencia y calidad\n\n"
    report += "CEEE: Comunidad de Madrid. Catastro: Dirección General del Catastro, Ministerio de Hacienda, autor y propietario. "
    report += "Se conserva cada original con URL, fecha de captura, cabeceras y SHA-256. Los feeds ATOM permiten reutilización gratuita con atribución. "
    report += "Madrid usa INE 28079 y código catastral 28900. Paquetes oficiales de ámbito municipal, sin peticiones individuales; las discrepancias de recuento de origen se documentan en las métricas.\n\n"
    report += "Se eliminan únicamente filas con idéntico contenido fuente; se conservan ocurrencias y fuentes. "
    report += "Un código de certificado repetido con distinto contenido permanece. No se deduplica por referencia catastral ni se elimina el historial. "
    report += "2026 es el recurso disponible en la captura, no un año cerrado. Campos originales conservados; conversiones numéricas y fechas son derivados.\n\n"
    report += "Geometría WKT y CRS explícito, Parquet convencional. Se valida topología con Shapely y posición/CRS con PyProj; "
    report += "las geometrías inválidas se conservan y señalan, sin reparación silenciosa. Una relación de parcela no confirma inmueble RC20 ni cobertura de edificio físico; "
    report += (
        "las letras energéticas permanecen en certificados. Los BU son agregados catastrales.\n\n"
    )
    report += (
        "## Métricas completas\n\n```json\n"
        + json.dumps(stats, ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    (out / "informe_ingesta.md").write_text(report)
    print(json.dumps({k: v["rows"] for k, v in stats["outputs"].items()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default="data/raw/session_1")
    parser.add_argument("--output-dir", default="data/processed/session_1")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    run(args.raw_dir, args.output_dir, args.offline)


if __name__ == "__main__":
    main()
