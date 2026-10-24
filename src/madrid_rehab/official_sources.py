"""Adquisición acotada de recursos oficiales, sin formularios ni automatización del visor."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import zipfile
import json
from pathlib import Path
import urllib.request
import urllib.parse

SOURCES = {
    "urban_2026": {
        "url": "https://datos.madrid.es/dataset/300373-0-inspecciones-urbanisticas/resource/300373-20-inspecciones-urbanisticas/download/300373-20-inspecciones-urbanisticas.xlsx",
        "filename": "urban_2026.xlsx",
        "license": "CC BY 4.0",
        "period": "2026; recurso actualizado 2026-06-11",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    "urban_2019": {
        "url": "https://datos.madrid.es/dataset/300373-0-inspecciones-urbanisticas/resource/300373-17-inspecciones-urbanisticas-csv/download/300373-17-inspecciones-urbanisticas-csv.csv",
        "filename": "urban_2019.csv",
        "license": "CC BY 4.0",
        "period": "2019; recurso actualizado 2026-06-11",
        "mime": "text/csv",
    },
    "bdns_schema": {
        "url": "https://www.infosubvenciones.es/bdnstrans/estaticos/doc/snpsap-api.json",
        "filename": "snpsap-api.json",
        "license": "Ver aviso legal SNPSAP; documentación, no dataset de concesiones",
        "period": "OpenAPI 1.1.0 observado 2026-10-23",
        "mime": "application/json",
    },
}
MAX_BYTES = 2 * 1024**2


def acquire(source, root, opener=None):
    """Un intento GET, máximo 2 MiB, salida nueva y manifiesto solo de archivo completo.

    Reintentos incrementales: reutilizar una captura íntegra (sin red) o crear otra
    carpeta para una actualización; nunca sobrescribir un original o un intento.
    """
    resource = SOURCES[source]
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / resource["filename"]
    manifest = root / (resource["filename"] + ".json")
    if target.exists() or manifest.exists():
        metadata = json.loads(manifest.read_text())
        if (
            metadata["url"] != resource["url"]
            or hashlib.sha256(target.read_bytes()).hexdigest() != metadata["sha256"]
        ):
            raise ValueError("Original o manifiesto alterado")
        return metadata
    attempt_path = root / (source + "_attempt.json")
    if attempt_path.exists():
        raise FileExistsError("Usar captura nueva; no sobrescribir evidencia de intento")
    attempt = {
        **resource,
        "source": source,
        "method": "GET",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        request = urllib.request.Request(
            resource["url"],
            headers={
                "User-Agent": "MadridRehabIntelligence/0.3 limited-official-research",
                "Accept-Encoding": "identity",
            },
        )
        with (opener or urllib.request.urlopen)(request, timeout=20) as response:
            if (
                urllib.parse.urlsplit(response.geturl()).netloc
                != urllib.parse.urlsplit(resource["url"]).netloc
            ):
                raise ValueError("Redirección fuera del origen")
            attempt["status"] = response.status
            length = response.headers.get("Content-Length")
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
            if response.status != 200 or content_type != resource["mime"]:
                raise ValueError("Estado o tipo de respuesta inesperado")
            if length and int(length) > MAX_BYTES:
                raise ValueError("Respuesta supera 2 MiB")
            body = response.read(MAX_BYTES + 1)
            if not body or len(body) > MAX_BYTES or (length and len(body) != int(length)):
                raise ValueError("Descarga vacía, incompleta o excesiva")
        if source == "bdns_schema":
            schema = json.loads(body)
            if "openapi" not in schema or "paths" not in schema:
                raise ValueError("No es OpenAPI")
        elif source == "urban_2026":
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 20 * 1024**2:
                    raise ValueError("XLSX descomprimido supera 20 MiB")
                if "xl/workbook.xml" not in archive.namelist() or archive.testzip() is not None:
                    raise ValueError("XLSX incompleto o corrupto")
        elif source == "urban_2019" and b"<html" in body[:500].lower():
            raise ValueError("HTML en lugar de CSV")
        attempt.update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body), complete=True)
        target.write_bytes(body)
        manifest.write_text(json.dumps(attempt, ensure_ascii=False, indent=2))
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        attempt.update(error_type=type(exc).__name__, error=str(exc), complete=False)
    attempt_path.write_text(json.dumps(attempt, ensure_ascii=False, indent=2))
    return attempt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=SOURCES)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    result = acquire(args.source, args.raw_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("complete"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
