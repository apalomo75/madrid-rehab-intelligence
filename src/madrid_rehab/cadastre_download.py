"""Descargador ATOM del piloto: biblioteca estándar, caché íntegra y ZIP/XML verificados."""

import argparse
import hashlib
import http.client
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = Path("config/cadastre_pilot_12_2.json")
RAW = Path("data/raw/cadastre/session_12_2_capture_01")
MAX_BYTES = 160 * 1024**2
MAX_EXPANDED = 2 * 1024**3
HOST = "www.catastro.hacienda.gob.es"


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path, value):
    path = Path(path)
    partial = path.with_name(path.name + ".tmp")
    partial.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    partial.replace(path)


def official_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != HOST
        or parsed.username
        or parsed.port not in (None, 443)
        or not parsed.path.startswith("/INSPIRE/")
    ):
        raise ValueError("URL fuera del servicio oficial permitido")
    return urllib.parse.quote(url, safe=":/?=&%")


def load_manifest(path):
    document = json.loads(Path(path).read_text())
    resources = document["resources"]
    if document["version"] != "cadastre-pilot-12.2-v1" or len(resources) != 10:
        raise ValueError("Se requiere manifiesto de diez recursos del piloto")
    pairs = set()
    for r in resources:
        pair = (r["municipality_code"], r["kind"])
        if (
            pair in pairs
            or r["municipality_code"] not in {"28065", "28092", "28074", "28007", "28005"}
            or r["kind"] not in {"cp", "bu"}
            or not r["cadastre_code"].isdigit()
            or len(r["cadastre_code"]) != 5
        ):
            raise ValueError("Identidad o recurso duplicado/incompatible")
        pairs.add(pair)
        official_url(r["url"])
    for name, expected in document["inputs"].items():
        if sha256(name) != expected:
            raise ValueError("Entrada del manifiesto alterada: " + name)
    return document


def inspect_zip(path, kind):
    """Lee CRC y XML hasta EOF sin extraer archivos; no confundir HTML con datos."""
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if (
            not infos
            or len({i.filename for i in infos}) != len(infos)
            or any(i.flag_bits & 1 for i in infos)
        ):
            raise ValueError("ZIP vacío, cifrado o con miembros duplicados")
        if sum(i.file_size for i in infos) > MAX_EXPANDED:
            raise ValueError("Expansión ZIP supera 2 GiB")
        expected_suffix = "cadastralparcel.gml" if kind == "cp" else "building.gml"
        targets = [i for i in infos if i.filename.lower().endswith(expected_suffix)]
        if len(targets) != 1:
            raise ValueError("Falta GML principal o es ambiguo")
        members = []
        for item in infos:
            if item.is_dir():
                continue
            if item.filename.lower().endswith((".xml", ".gml")):
                with archive.open(item) as stream:
                    # Escaneo incremental de DTD/entidades también cuando cruzan bloques.
                    tail = b""
                    for chunk in iter(lambda: stream.read(65536), b""):
                        block = (tail + chunk).upper()
                        if b"<!DOCTYPE" in block or b"<!ENTITY" in block:
                            raise ValueError("DTD/entidades no permitidas")
                        tail = block[-16:]
                with archive.open(item) as stream:
                    root_tag = None
                    stack = []
                    namespaces = []
                    entities = Counter()
                    seen_ids = set()
                    duplicate_ids = Counter()
                    duplicate_examples = []
                    feature_ids = set()
                    feature_duplicates = Counter()
                    member_count = 0
                    for event, element in ET.iterparse(stream, events=("start", "end", "start-ns")):
                        if event == "start-ns":
                            namespaces.append(element)
                            continue
                        tag = element.tag.rsplit("}", 1)[-1]
                        if root_tag is None:
                            root_tag = tag
                            xml_root = element
                            header = dict(element.attrib)
                        if tag in {"html", "ExceptionReport", "ExceptionText", "ServiceException"}:
                            raise ValueError("HTML/excepción OGC dentro del ZIP")
                        if event == "start":
                            stack.append(element.tag)
                            ident = element.get("{http://www.opengis.net/gml/3.2}id")
                            if ident:
                                if ident in seen_ids:
                                    duplicate_ids[element.tag] += 1
                                    if len(duplicate_examples) < 10:
                                        duplicate_examples.append(ident)
                                seen_ids.add(ident)
                            if len(stack) == 3 and stack[-2].rsplit("}", 1)[-1] in {
                                "member",
                                "featureMember",
                            }:
                                entities[element.tag] += 1
                                if not ident:
                                    raise ValueError("Entidad GML sin gml:id")
                                if ident in feature_ids:
                                    feature_duplicates[element.tag] += 1
                                feature_ids.add(ident)
                        else:
                            if len(stack) == 2 and tag in {"member", "featureMember"}:
                                member_count += 1
                                if len(element) != 1:
                                    raise ValueError("Miembro GML vacío o con múltiples entidades")
                                element.clear()
                                xml_root.clear()
                            stack.pop()
                if item in targets and root_tag != "FeatureCollection":
                    raise ValueError("GML principal no es FeatureCollection")
                members.append(
                    dict(
                        name=item.filename,
                        bytes=item.file_size,
                        root=root_tag,
                        root_qname=xml_root.tag,
                        header=header,
                        namespaces=namespaces,
                        feature_members=member_count,
                        entities=dict(entities),
                        unique_feature_ids=len(feature_ids),
                        duplicate_feature_ids=dict(feature_duplicates),
                        unique_gml_ids=len(seen_ids),
                        duplicate_gml_ids=dict(duplicate_ids),
                        duplicate_id_examples=duplicate_examples,
                    )
                )
            else:
                # Leer hasta EOF para verificar CRC de todos los miembros.
                with archive.open(item) as stream:
                    while stream.read(65536):
                        pass
        return dict(zip_integrity="verified", xml_integrity="verified", members=members)


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(resource, root, attempts=2, timeout=20, offline=False):
    if attempts not in (1, 2, 3) or not 1 <= timeout <= 120:
        raise ValueError("Intentos 1..3 y timeout 1..120 segundos")
    url = official_url(resource["url"])
    directory = Path(root) / resource["cadastre_code"]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (resource["kind"] + ".zip")
    meta = path.with_suffix(".zip.json")
    if path.exists() or meta.exists():
        if not path.exists() or not meta.exists():
            raise ValueError("Original/metadatos incompletos: conservar y usar captura nueva")
        record = json.loads(meta.read_text())
        if (
            record["url"] != url
            or record["sha256"] != sha256(path)
            or record["bytes"] != path.stat().st_size
        ):
            raise ValueError("Original de caché alterado")
        inspect_zip(path, resource["kind"])
        return dict(status="verified_cached", path=str(path), **record)
    if offline:
        return dict(
            status="missing", path=str(path), error="Original no disponible; sin petición de red"
        )
    partial = path.with_suffix(".zip.part")
    if partial.exists():
        # Una descarga interrumpida nunca se interpreta como ZIP ni se sobreescribe.
        partial.rename(directory / (partial.name + ".interrupted-" + uuid.uuid4().hex))
    opener = urllib.request.build_opener(OfficialRedirect())
    started = time.perf_counter()
    for attempt in range(attempts):
        attempt_started = time.perf_counter()
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "MadridRehab/12.2 bounded-official-pilot",
                    "Accept-Encoding": "identity",
                },
            )
            with opener.open(req, timeout=timeout) as response, partial.open("xb") as out:
                official_url(response.geturl())
                if response.status != 200:
                    raise ValueError("HTTP no confirma un archivo completo")
                length = response.headers.get("Content-Length")
                expected = int(length) if length is not None else None
                if expected is not None and (expected <= 0 or expected > MAX_BYTES):
                    raise ValueError("Tamaño HTTP incompatible con presupuesto")
                if "html" in response.headers.get("Content-Type", "").lower():
                    raise ValueError("Respuesta HTML en lugar de ZIP")
                count = 0
                while chunk := response.read(1024**2):
                    if time.perf_counter() - attempt_started > 120:
                        raise TimeoutError("Presupuesto de 120 s por intento agotado")
                    count += len(chunk)
                    if count > MAX_BYTES:
                        raise ValueError("Descarga supera 160 MiB")
                    out.write(chunk)
                if not count or (expected is not None and count != expected):
                    raise ValueError("Descarga vacía o truncada")
                if (
                    resource.get("expected_bytes") is not None
                    and count != resource["expected_bytes"]
                ):
                    raise ValueError("Tamaño distinto del declarado en el feed")
                out.flush()
                headers = dict(response.headers)
            integrity = inspect_zip(partial, resource["kind"])
            record = dict(
                url=url,
                captured_at=datetime.now(timezone.utc).isoformat(),
                bytes=count,
                sha256=sha256(partial),
                headers=headers,
                validation=integrity,
                attempts=attempt + 1,
                seconds=time.perf_counter() - started,
            )
            partial.rename(path)
            write_json(meta, record)
            return dict(status="verified_downloaded", path=str(path), **record)
        except (
            urllib.error.URLError,
            TimeoutError,
            http.client.IncompleteRead,
            ConnectionError,
        ) as exc:
            # DNS no mejora reintentando diez veces el mismo host dentro del sandbox.
            reason = getattr(exc, "reason", None)
            retry = not isinstance(reason, socket.gaierror)
            if isinstance(exc, urllib.error.HTTPError):
                # 429 se deja pendiente para otra ejecución; no ignorar Retry-After.
                retry = exc.code in {408, 500, 502, 503, 504}
            if attempt + 1 >= attempts or not retry:
                return dict(
                    status="blocked",
                    path=str(path),
                    error=str(exc),
                    attempts=attempt + 1,
                    seconds=time.perf_counter() - started,
                )
            time.sleep(2**attempt)
        finally:
            partial.unlink(missing_ok=True)
    raise AssertionError("Bucle de descarga sin resultado")


def download(manifest_path=MANIFEST, root=RAW, report=None, attempts=2, timeout=20, offline=False):
    manifest = load_manifest(manifest_path)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    snapshot = root / "pilot_manifest.json"
    if snapshot.exists() and sha256(snapshot) != sha256(manifest_path):
        raise ValueError("Captura asociada a otro manifiesto")
    if not snapshot.exists():
        snapshot.write_bytes(Path(manifest_path).read_bytes())
    report = (
        Path(report)
        if report
        else Path("reports/session_12_2")
        / (
            "download_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            + "_"
            + uuid.uuid4().hex[:6]
        )
    )
    report.mkdir(parents=True, exist_ok=False)
    results = []
    for r in manifest["resources"]:
        try:
            result = fetch(r, root, attempts, timeout, offline)
        except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError, EOFError) as exc:
            result = dict(status="invalid", error=str(exc))
        results.append({**r, **result, "url": r["url"], "request_url": official_url(r["url"])})
        write_json(report / "downloads.json", results)
        print(f"{r['name']} {r['kind'].upper()}: {result['status']}", flush=True)
    complete = all(r["status"].startswith("verified_") for r in results)
    write_json(
        report / "manifest.json",
        dict(
            input_manifest_sha256=sha256(manifest_path),
            complete=complete,
            verified=sum(r["status"].startswith("verified_") for r in results),
            outputs={"downloads.json": sha256(report / "downloads.json")},
        ),
    )
    return results, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    results, report = download(
        args.manifest, args.raw_dir, args.report_dir, args.attempts, args.timeout, args.offline
    )
    print("Informe:", report)
    raise SystemExit(0 if all(r["status"].startswith("verified_") for r in results) else 2)


if __name__ == "__main__":
    main()
