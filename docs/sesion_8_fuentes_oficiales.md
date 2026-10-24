# Sesión 8 — investigación y preparación de fuentes oficiales

Resultado al 23/10/2026: **sin nuevos archivos de registros adquiridos**. La adquisición no se declara completada. Se han verificado páginas, enlaces, un diccionario de columnas y documentación API. Ninguno se presenta como dataset de eventos. Catastro/CEEE y productos auditados se mantienen.

Véanse [inventario](inventario_fuentes.md), [ITE/IEE](viabilidad_ite_iee.md) y [subvenciones](viabilidad_subvenciones.md). La documentación previa de sesiones 4–6 se conserva como antecedente, no como prueba de una descarga actual.

## Accesos realizados

Fecha: 23/10/2026. Herramienta web GET y búsqueda oficial; Python urllib GET con timeout 15 s y tope 2 MiB. Errores Python completos en `reports/session_8/source_attempts.json`; intento adicional CSV en `data/raw/session_8_attempt_01/urban_2019_attempt.json`. Los errores no son manifiestos de datasets.

| Acceso | Resultado web | Resultado local | Interpretación |
| --- | --- | --- | --- |
| GITEP_WBINFORME/SGiteInforme | HTML legible | DNS Errno -3 | Formulario público; sin registros adquiridos |
| GITEP_WBFICHA/SGiteCons | HTML legible | No repetido | Consulta individual; sin descarga comprobada |
| Catálogo 300373/downloads | HTML legible | No repetido | Recursos 2017–2026 anunciados |
| Recurso 300373-20 | Metadatos legibles | Descarga DNS Errno -3 | XLSX y licencia comprobados en catálogo |
| XLSX 2026 directo | Unsupported content-type (400 de la herramienta) | DNS Errno -3 | No es evidencia de un HTTP 400 del publicador |
| datastore_search del recurso 2026, limit=5 | 404 | No repetido | Ejemplo del catálogo no funciona en este acceso |
| package_show del conjunto | Inaccesible por herramienta | No repetido | Sin esquema de paquete descargado |
| Recurso CSV Agencia 2019 | Diccionario legible | Descarga DNS Errno -3 | Estructura conocida, valores no inspeccionados |
| CSV directo / exportación JSON | Tipo no soportado / cache miss | No repetido tras DNS | Sin filas adquiridas |
| Página PRTR Comunidad | HTML legible | No repetido | Enlace y alcance del visor verificados |
| Visor COAM | 403 Forbidden | DNS Errno -3 | No explorar endpoints no documentados ni eludir acceso |
| SNPSAP Swagger | HTML sin texto extraíble; se revisó OpenAPI directamente | No repetido | Interfaz documental, no datos |
| SNPSAP OpenAPI | JSON legible | DNS Errno -3 | Documentación, no registros |
| Concesiones, una fila y un mes | Inaccesible por herramienta | DNS Errno -3 | Sin respuesta de datos ni muestra verificable |

Las URLs completas están en el inventario, en `official_sources.SOURCES` y en el registro local. Un fallo DNS del sandbox no prueba indisponibilidad pública. No se repiten solicitudes fallidas indefinidamente.

## Esquemas y adaptadores

`public_events.py` reutiliza `events.normalize_events` para contratos separados `ite_iee`, `urban_inspection`, `grant_call`, `grant_award` y `grant_phase`. Exige captura/versión, conserva origen/fecha/ID, marca normalización pendiente de revisión y precisión espacial no verificada. Tipos ITE/IEE explícitos y fases administrativas separadas. No añade coordenadas supuestas. No se conecta un evento normalizado sin revisar al visor.

El diccionario **CSV 2019 de Agencia de Actividades** enumera `No orden`, `Tipo de Via`, `Calle`, `Distrito`, `Codigo Distrito`, `Materia objeto de la inspeccion`, `Mes`, `Ano`. `normalize_urban_2019` valida esas columnas, IDs contradictorios, distrito y mes/año; omite calle del producto porque carece de portal, no crea RC ni geometrías y conserva precisión mensual. La materia conserva literal: aún no se sabe qué filas tratan conservación, disciplina o rehabilitación. Como máximo permite proponer agregación distrital, pendiente de adquisición/revisión. No extrapolar este esquema al XLSX 2026. No hay parser XLSX verificado contra archivo real; queda pendiente.

Todos los ejemplos de prueba son fixtures artificiales expresamente identificados dentro de `tests/`. No se incorporan a `data/processed/`. Pruebas cubren campos opcionales, fuente vacía, cambio de columnas, IDs duplicados, fechas, importes, privacidad, trazabilidad, ausencia de geometrías y compatibilidad canónica. No se afirma parsing de archivos reales que no se han obtenido.

## Adquisición reproducible

Sin dependencias nuevas. Ejecutar fuera del sandbox con acceso DNS:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.official_sources urban_2026 --raw-dir data/raw/session_8_capture_02
PYTHONPATH=src .venv/bin/python -m madrid_rehab.official_sources urban_2019 --raw-dir data/raw/session_8_capture_03
PYTHONPATH=src .venv/bin/python -m madrid_rehab.official_sources bdns_schema --raw-dir data/raw/session_8_capture_04
```

Una petición GET por recurso, timeout 20 s, tope 2 MiB, validación de estado/MIME/longitud, sin seguir redirección a otro origen. Conserva fecha, URL, periodo, licencia y SHA-256 solo de archivo completo. Error deja registro de intento y código de salida 2; usar carpeta nueva para repetir. Captura íntegra verificada se reutiliza sin red; una actualización requiere nueva carpeta. No hay incremental por ID sin identidad temporal oficial comprobada. El esquema BDNS se guarda como documentación, nunca como concesiones.

Consulta BDNS manual reproducible, después de revisar condiciones:

```bash
curl --fail --max-time 30 --get 'https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda' \
  --data-urlencode 'page=0' --data-urlencode 'pageSize=1' --data-urlencode 'vpd=GE' \
  --data-urlencode 'descripcion=rehabilitación' --data-urlencode 'fechaDesde=01/07/2026' \
  --data-urlencode 'fechaHasta=31/07/2026' --output /tmp/bdns_sample_review.json
```

Esa respuesta sería muestra pendiente de revisión, no dataset definitivo. No publicar beneficiarios. Para formularios ITE/IEE y PRTR, seguir procedimientos de las respectivas viabilidades; no se automatizan sesiones ni controles de acceso.

Normalizados y controles de calidad deberán ir en nueva salida `data/processed/session_8_<captura>/normalized/` y `quality/`, con hash del original, licencia revisada y esquema observado. Esas carpetas no se generan mientras no haya registros reales. Métricas de calidad y matching: no calculables; no se fuerza asignación a Catastro.
