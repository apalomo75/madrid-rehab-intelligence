"""Orquestación y artefactos reproducibles con estados de ejecución explícitos."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from .http import Client, DownloadError
from .integrate import integrate, quality, schema_profile
from .normalize import reference, split_references, text_key
from .pilot import evaluate_pilot
from .sources import (
    building_sample, energy_sample, parcel_sample, parse_buildings, parse_parcels,
    parse_properties, property_sample,
)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def validate_config(config):
    if not 1 <= config["sample_limit"] <= 30:
        raise ValueError("Máximo 30 filas CEEE")
    if not 1 <= config["max_references"] <= 5:
        raise ValueError("Máximo cinco referencias; ampliar requiere aprobación")
    if not 1 <= config["timeout_seconds"] <= 30:
        raise ValueError("Timeout debe estar entre 1 y 30 segundos")
    if not 0 <= config["interval_seconds"] <= 10:
        raise ValueError("Intervalo debe estar entre 0 y 10 segundos")


def capture(client, config):
    snapshot = {"energy": {"records": [], "fields": []}, "parcels": [], "buildings": [],
                "properties": [], "errors": [], "selected_references": [],
                "resource_id": config["resource_id"], "data_kind": "official_http_sample"}
    try:
        snapshot["energy"] = energy_sample(client, config)
    except (DownloadError, ValueError, KeyError) as exc:
        snapshot["errors"].append({"source": "energy", "error": str(exc)})
        # Una única prueba pequeña e independiente de Catastro, sin descargar paquetes.
        try:
            client.get(config["wfs_bu"], {
                "service": "WFS", "version": "2.0.0", "request": "GetCapabilities",
            })
        except DownloadError as cat_exc:
            snapshot["errors"].append({"source": "catastro_capabilities", "error": str(cat_exc)})
        return snapshot
    refs = []
    for row in snapshot["energy"]["records"]:
        # El muestreo CEEE puede devolver otros municipios: no geocodificarlos como Madrid.
        if text_key(row.get("edif_muni")).strip() != "MADRID":
            continue
        refs.extend(reference(v) for v in split_references(row.get("edif_refcat")))
    selected = sorted({r["reference_normalized"] for r in refs if r["reference_format_valid"]})[
        :config["max_references"]
    ]
    snapshot["selected_references"] = selected
    parcels_done = set()
    failed_hosts = False
    for selected_ref in selected:
        if failed_hosts:
            break
        ref = reference(selected_ref)
        if ref["parcel_ref14"] not in parcels_done:
            parcels_done.add(ref["parcel_ref14"])
            for name, download, parse in (
                ("parcels", parcel_sample, parse_parcels),
                ("buildings", building_sample, parse_buildings),
            ):
                try:
                    snapshot[name].extend(parse(download(client, config, ref["parcel_ref14"])))
                except (DownloadError, ValueError, KeyError) as exc:
                    snapshot["errors"].append({"source": name, "reference": selected_ref, "error": str(exc)})
                    if isinstance(exc, DownloadError):
                        failed_hosts = True
                        break
        if ref["property_ref20"] and not failed_hosts:
            try:
                snapshot["properties"].extend(parse_properties(property_sample(client, config, selected_ref)))
            except (DownloadError, ValueError, KeyError) as exc:
                snapshot["errors"].append({"source": "properties", "reference": selected_ref, "error": str(exc)})
                if isinstance(exc, DownloadError):
                    failed_hosts = True
    return snapshot


def run(config, raw_dir, output_dir, report_dir, offline_snapshot=None):
    validate_config(config)
    raw_dir, output_dir, report_dir = map(Path, (raw_dir, output_dir, report_dir))
    for path in (raw_dir, output_dir, report_dir):
        path.mkdir(parents=True, exist_ok=True)
    # Una ejecución tiene salida inmutable; evitar mezclar resultados de capturas distintas.
    if (report_dir / "results.json").exists():
        raise ValueError("Ya existe results.json; utilice otro directorio de ejecución")
    if offline_snapshot:
        snapshot_bytes = Path(offline_snapshot).read_bytes()
        snapshot = json.loads(snapshot_bytes)
        if snapshot.get("resource_id") != config["resource_id"]:
            raise ValueError("Recurso del snapshot distinto de la configuración")
        manifest = {"mode": "offline", "snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
                    "snapshot_path": str(offline_snapshot)}
    else:
        client = Client(raw_dir / "http", config)
        try:
            snapshot = capture(client, config)
        finally:
            client.manifest(report_dir / "http_manifest.json")
        write_json(raw_dir / "snapshot.json", snapshot)
        manifest = {"mode": "http", "snapshot_sha256": hashlib.sha256(
            (raw_dir / "snapshot.json").read_bytes()).hexdigest(), "snapshot_path": str(raw_dir / "snapshot.json")}
    records = snapshot["energy"]["records"]
    if len(records) > config["sample_limit"]:
        raise ValueError("El snapshot excede la muestra configurada")
    ids = [r.get("_id") for r in records]
    if len(ids) != len(set(ids)) or any(i is None for i in ids):
        raise ValueError("Identidades de fila nulas o duplicadas")
    frame = integrate(records, snapshot["parcels"], snapshot["buildings"], snapshot["properties"],
                      config["resource_id"], config.get("scope_map"))
    metrics = quality(frame, records, snapshot["buildings"])
    status = "blocked" if not records else (
        "partial" if snapshot["errors"] or (frame.match_status != "matched").any() else "sample_integrated"
    )
    # Pandas + PyArrow bastan para un Parquet con coordenadas explícitas. No es GeoParquet.
    parquet_path = output_dir / "certificate_reference_links.parquet"
    frame.to_parquet(parquet_path, engine="pyarrow", index=False)
    buildings_path = output_dir / "building_objects.parquet"
    building_columns = ["building_id", "parcel_ref14", "construction_begin", "construction_end",
                        "current_use", "dwellings_raw", "building_units_raw", "geometry_wkt",
                        "geometry_crs", "building_geometry_status"]
    buildings_frame = pd.DataFrame(snapshot["buildings"], columns=building_columns).astype("string")
    buildings_frame.to_parquet(buildings_path, engine="pyarrow", index=False)
    observed_schema = schema_profile(records, snapshot["energy"].get("fields", []))
    write_json(report_dir / "source_schema.json", observed_schema)
    write_json(report_dir / "integration_schema.json", {
        "pandas": {name: str(dtype) for name, dtype in frame.dtypes.items()},
        "arrow": str(pq.read_schema(parquet_path)),
    })
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(), "status": status,
        "data_kind": snapshot.get("data_kind", "unverified_local_snapshot"),
        "config": config, "provenance": manifest, "metrics": metrics,
        "selected_references": snapshot["selected_references"], "errors": snapshot["errors"],
        "pilot": evaluate_pilot(frame, config),
        "outputs": [str(parquet_path), str(buildings_path)],
        "artifacts_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (parquet_path, buildings_path)},
    }
    write_json(report_dir / "results.json", report)
    write_json(report_dir / "config.json", config)
    (report_dir / "results.md").write_text(render_report(report))
    return report


def render_report(report):
    m = report["metrics"]
    percentage = m["reference_match_percent"]
    percentage_text = f"{percentage}%" if percentage is not None else "no calculable (sin denominador)"
    return f"""# Resultado de la muestra Catastro–CEEE

Estado: **{report['status']}**. Tipo de entrada: `{report['data_kind']}`.
Fecha UTC: {report['created_at']}.

| Métrica | Resultado |
| --- | --- |
| Filas CEEE procesadas | {m['source_rows_processed']} |
| Referencias expandidas | {m['reference_rows']} |
| Referencias con formato urbano admitido | {m['references_valid_format']} |
| Inmuebles RC20 confirmados por autoridad | {m['unique_authority_confirmed_properties']} |
| Parcelas confirmadas | {m['unique_confirmed_parcels']} |
| Coincidencias por referencia | {percentage_text} |
| Parcelas con punto geolocalizado | {m['geolocated_parcels']} |
| Objetos BU con geometría, validación estructural | {m['building_objects_with_geometry_structural_only']} |
| Edificios certificados geolocalizados con enlace fiable | {m['certificate_buildings_reliably_geolocated']} |

## Interpretación

El formato no verifica caracteres de control ni existencia. La existencia de una RC20
solo se confirma si DNPRC la devuelve; una RC14 se confirma contra CP.
El porcentaje usa filas de referencia expandidas como denominador. El JSON incluye
también porcentaje de filas CEEE con todas sus referencias confirmadas.
Las filas CEEE no se presuponen certificados únicos: pueden repetirse códigos.
La selección de cinco referencias limita las consultas catastrales: los porcentajes
no estiman cobertura de Madrid ni calidad global del registro.

La ubicación de parcela no identifica vivienda ni bloque físico. Las calificaciones
permanecen en la fila CEEE y su ámbito original. Los candidatos BU no reciben letras.
Los dos Parquet pueden estar vacíos si el acceso está bloqueado: son contratos de
salida, no una integración real exitosa. No contienen datos sintéticos.

## Piloto

{json.dumps(report['pilot'], ensure_ascii=False)}

## Incidencias

```json
{json.dumps(report['errors'], indent=2, ensure_ascii=False)}
```

Próximo paso: resolver acceso a muestras oficiales, contrastar el catálogo de ámbitos
CEEE y comparar identidades geolocalizadas en distritos con límites oficiales.
"""
