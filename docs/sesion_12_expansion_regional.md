# Sesión 12 — expansión regional, ejecución parcial verificable

Corte: 24/10/2026. **No se ha completado la expansión territorial ni el piloto real.** El entorno permite investigar páginas mediante la herramienta web, pero Python no resuelve los hosts de descarga. Trece comprobaciones de acceso a INE, IDEM, IGN y CP/BU de los cinco municipios piloto fallaron por DNS. No se sustituyeron fuentes ausentes por fixtures.

## Resultado y coberturas separadas

| Cobertura | Resultado real |
| --- | --- |
| Inventario oficial Catastro | 179 entradas CP y 179 BU reconciliadas |
| Catálogo INE completo | Pendiente; solo Madrid está confirmado en la integración histórica |
| Límites municipales regionales importados | 0; permanecen los 21 distritos oficiales de Madrid |
| Municipios con CP / BU procesado | 1 / 1: Madrid capital, captura histórica |
| Nuevas parcelas / nuevos objetos BU | 0 / 0 |
| PRTR preservados | 7.532 expedientes; 31.552.733.899 céntimos |
| Municipio confirmado por CP | Madrid: 3.805 expedientes; 126.328.673,63 € |
| Pendientes municipales | 3.727; no equivalen a municipios externos confirmados |
| Relaciones confirmadas | 3.809 sobre 3.300 RC14 de Madrid |
| Relaciones ambiguas históricas | 3 |
| Relaciones sin cobertura CP regional confirmada | 3.749; unidad relación, no expediente |

Los 179 recursos se recuperaron de los feeds oficiales **ya conservados** en `data/raw/session_1/`, comprobados por hash y reconciliados entre CP/BU. Sus fechas de recurso son las publicadas en cada entrada; no se supone que una fecha sea común a todos. `cadastre_code`, nombres literales y códigos INE son conceptos distintos. Por ejemplo, Madrid usa 28900/28079; Berzosa y El Berrueco muestran además que ni siquiera basta sustituir únicamente el código de Madrid. No se deducen los restantes INE por igualdad numérica ni por nombre. Los rectángulos GeoRSS ATOM no se importan como límites.

## Componentes funcionales

- `regional_cadastre.py`: inventario oficial, contrato de correspondencia explícita INE–Catastro, descarga secuencial con dos intentos por defecto (máximo tres), reutilización de originales con hash, procesamiento CP/BU, control estricto del número declarado en GML, CRS, IDs, duplicados, geometrías, superposición municipal y relaciones CP/BU. Publicación atómica de particiones después de validar. Lotes máximos de cinco; detención del lote ante el primer fallo. Las particiones válidas se reutilizan; un original incompleto se vuelve a descargar, no se hace HTTP Range sin verificar compatibilidad.
- `regional_territory.py`: importación de catálogo INE revisado y GeoJSON oficial, correspondencia explícita por ID de fuente, CRS declarado, conservación del original, 179 identidades, geometría íntegra analítica, huecos y multipartes. Rechaza capturas incompletas/paginadas, solapamientos >1 m², geometrías inválidas y ejes fuera del sobre regional. La coherencia contra un límite provincial independiente sigue pendiente.
- `regional_grants.py`: tabla territorial independiente de la evidencia CP histórica; diferencia ausencia de límites, límites, contradicciones, geometría inválida y exterior. Umbral limítrofe operativo de 1 m. Matching por municipio, RC14, unicidad y distancia a CP ≤100 m, heredada del control conservador de sesión 11; no es precisión oficial ni acreditación física. Conserva ambiguas históricas y separa «no encontrada» de «sin cobertura». Importe en hechos de expediente, nunca en relaciones.
- `regional_view.py`: exploración de los 179 recursos municipales, estados de cobertura, selección, filtros PRTR, importes legibles, exportación segura y modo público sin exposición PRTR. Habilita mapa oficial y navegación por INE cuando se aporte el catálogo validado. Las fichas externas solo se habilitan con una partición municipal validada. Esta rama se ha probado con fixtures sintéticas, no con Catastro externo real.
- `regional_audit.py`: reconciliación de importes/identidades, hash de productos e inventario de archivos protegidos, informe de cobertura y comprobaciones de acceso opcionales.

Madrid mantiene su ruta y sus 21 distritos, mapa, CEEE, eventos y PRTR. Se ha añadido un parámetro opcional `strict_count` al lector GML: el comportamiento histórico permanece, y la nueva ingesta exige colecciones completas.

## Productos y reproducción

Sin dependencias ni servidores nuevos. Instalación: `.venv/bin/python -m pip install -r requirements.lock`. No hay compilación. Ejecutar desde la raíz.

```bash
# Cada reproducción necesita salida nueva. Los originales se reutilizan.
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_cadastre \
  --inventory-output data/processed/territory/replay_new
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_grants \
  --output-dir data/processed/grants/regional/replay_new
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_audit \
  --output-dir reports/session_12/audit_new
# Añadir --check-network para repetir 13 HEAD oficiales, secuenciales y acotados.
PYTHONPATH=src .venv/bin/python tests/benchmark_regional.py \
  --output reports/session_12/benchmark_new.json
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_regional_expansion.py -v
.venv/bin/ruff check src tests
```

Productos vigentes: `data/processed/territory/session_12_final_01/` y `data/processed/grants/regional/session_12_final_01/`. Se conservaron también los productos intermedios propios. Los manifiestos incluyen hashes de entradas y salidas; la clasificación sin límites queda explícita, no como asignación espacial conseguida. Las tablas PRTR siguen bajo `data/` ignorado. El informe agregado por municipio/programa incluye el residuo desconocido y no publica identificadores de expedientes.

Para importar fuentes oficiales recuperadas fuera de este entorno, véanse [límites](calidad_limites_municipales.md) y [Catastro](catastro_regional.md). No hay una descarga automática regional de límites implementada: el importador exige una captura completa revisada y no inventa una consulta WFS.

## Rendimiento y validación

Baseline: 252 pruebas en 177,042 s. Mediciones reales en `reports/session_12/benchmark.json`: apertura regional AppTest 1,804 s; selección Getafe/Madrid/Móstoles 0,032/0,109/0,033 s; lectura CP Madrid 0,802 s; lectura BU Madrid 0,717 s; consulta CP histórica por RC14 0,435 s. Pico conjunto, incluida la lectura completa de Madrid: 827.628 KiB (~808 MiB). No es el consumo de una ingesta externa. La segunda medición, con la suite concurrente, registra 3,140 s de apertura, 0,048–0,205 s de cambios, 233.624 KiB de RSS regional AppTest (~228 MiB), 1,359/1,066 s de lectura CP/BU y 851.612 KiB (~832 MiB) de RSS conjunto (`benchmark_final.json`). La diferencia de carga concurrente impide interpretar esas variaciones como regresión de rendimiento. El cruce regional final sin límites tardó 3,624 s, sin descargar PRTR.

Las nuevas particiones almacenan bounding boxes escalares, orden por referencia y grupos Parquet de 10.000 filas. La vista carga un índice municipal sin geometrías, consulta CP/BU de la selección con filtros Parquet y recorta contexto por ventana/zoom con un máximo de 1.500 parcelas. Cachés acotadas a 2–4 entradas; no se carga todo Catastro regional. La simplificación se aplica únicamente al mapa. No existe benchmark de ingesta regional real: no se extrapolan tiempos por municipio, bytes ni memoria a 179 municipios sin piloto.

Las pruebas comprueban catálogo de 179 identidades con fixtures **sintéticas**, errores HTTP, ZIP corrupto/inexistente, reintentos, caché, checkpoints, CRS, geometrías, límites, conflictos, matching, exportación, navegación y datos reales PRTR. AppTest no acredita clic ni legibilidad en navegador. Estado final de pruebas y servidor: [avance](avance_sesion_12.md).

## CEEE y sesión 13

Auditoría por chunks, sin reprocesar matching ni publicar detalles, en `reports/session_12/ceee_coverage.json`. Captura 2025: 110.650 filas, 55.271 con literal Madrid y 55.379 con otros literales. Captura 2026: 125.523, 60.399 y 65.124 respectivamente. Hay 885/1.009 literales distintos, **no municipios únicos**: incluyen variantes/ruido y no acreditan 179 identidades. Los totales no se suman como certificados únicos entre recursos.

Se conserva `edif_refcat` y su ámbito; RC14/RC20 no identifican edificio físico. El normalizador histórico filtra Madrid por `edif_muni`; no se ha extendido automáticamente. La futura sesión 13 puede resolver INE y usar CP municipal particionado conservando `record_id`, ámbito y referencias múltiples; requiere normalización revisada, deduplicación entre capturas y cobertura explícita. Primero siguen pendientes el catálogo completo, límites y piloto de esta sesión.

No se hicieron commits ni push. Se respaldaron las 16 rutas iniciales en `/tmp/madrid_rehab_session12_initial/`. Los 1.718 archivos originales/productos existentes al inicio se verificaron sin cambios (`reports/session_12/audit_final_01/quality.json`).
