# Pipeline inicial Catastro–CEEE

## Estado y alcance

Implementado con Python, Pandas y PyArrow. Pruebas unitarias y de integración **offline**; sin muestras oficiales disponibles en este entorno. Se produce Parquet convencional con coordenadas y CRS explícitos, no GeoParquet. No se utiliza DuckDB: una muestra de hasta 30 filas no justifica otro motor. GeoPandas es opcional para la evaluación distrital con límites oficiales locales; su instalación no pudo resolverse aquí.

Leer primero [AGENTS.md](../AGENTS.md) y los [resultados](resultados_pipeline.md). No hay interfaz web ni otras fuentes integradas.

## Entorno e instalación

Instalación limpia prevista, desde la raíz, con acceso al índice de paquetes:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
```

El backend de construcción necesita setuptools >=68 y soporte de wheel. Si no están disponibles, instalarlos dentro de `.venv` o usar `PYTHONPATH=src` con los comandos siguientes sin instalar el proyecto. No modificar Python global.

En esta sesión se creó `.venv` con `--system-site-packages` para reutilizar Pandas 2.3.3/PyArrow 23.0.1 preexistentes. Es un entorno local con paquetes heredados, no un aislamiento limpio validado. El lock registra versiones observadas; no se pudo comprobar su resolución desde el índice. No se instalaron paquetes globales. Ruff queda configurado en `pyproject.toml`, pero no disponible ni ejecutado.

## Ejecutar una muestra limitada

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cli \
  --config config/sample.json \
  --raw-dir data/raw/run_002 \
  --output-dir data/processed/run_002 \
  --report-dir reports/run_002
```

El comando devuelve código 2 cuando no obtiene filas CEEE. Un resultado parcial conserva las observaciones y sus motivos pendientes. Los directorios de informes son inmutables una vez generado `results.json`: usar un nombre nuevo.

La configuración solicita la primera página DataStore de hasta 30 filas, ordenada por `_id asc`, sin filtro municipal inicial. Permite examinar el dominio de municipio sin presuponer mayúsculas ni valores. Solo se consultan referencias de filas cuyo municipio normalizado es exactamente Madrid. Se seleccionan las primeras cinco referencias urbanas únicas en orden lexicográfico, no las cinco que mejor coincidan.

**Presupuesto máximo:** 20 peticiones, 512 KiB por respuesta y 5 MiB de cuerpos por ejecución; estimación esperada inferior a 1 MiB para cinco identidades, no medida en este entorno. Las cabeceras HTTP y negociación de conexión no están incluidas en el contador. Los límites son una barrera incluso si el servidor ignora el tamaño esperado. No hay paginación automática, ZIP municipal ni lectura de CSV completo. Aumentar estos topes requiere informar del tamaño y obtener aprobación.

Los adaptadores intentan:

1. `datastore_search` sobre el recurso 2026 identificado en la ficha CEEE.
2. WFS CP `GetParcel` por RC14 y WFS BU `GetBuildingByParcel`, en EPSG:25830. Se conserva la grafía `STOREDQUERIE_ID` de los ejemplos de Catastro; el comportamiento actual sigue pendiente de respuesta real.
3. [DNPRC](https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx?op=Consulta_DNPRC) por RC20 para confirmar identidad de inmueble, cuando exista esa referencia. La página oficial confirma el parámetro `RC`; no usar el parámetro `RefCat` de la variante WCF JSON en este endpoint ASMX.

Los endpoints son documentados/candidatos, **sin validación operacional exitosa aquí**. La base CKAN `/catalogo/api/3/action` puede probarse mediante una copia de la configuración si la base configurada no responde; no se hacen reintentos ni cambios automáticos de origen. Un fallo de descarga catastral detiene nuevas consultas a ese dominio, conservando las filas pendientes.

## Reproducir sin red

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cli \
  --offline-snapshot data/raw/run_002/snapshot.json \
  --output-dir data/processed/replay_002 \
  --report-dir reports/replay_002
```

El snapshot conserva registros originales y respuestas parseadas. Los cuerpos HTTP y sus hashes quedan en `data/raw/.../http/`; el informe guarda hash del snapshot, configuración, incidencias y hashes de Parquet. Repetir una consulta futura no garantiza los mismos datos: `_id` y recurso pueden cambiar. La reproducción exacta depende de conservar snapshot, cuerpos y versiones. No publicar originales catastrales sin revisar las condiciones.

## Reglas de identidad y certificación

- RC14: clave de parcela urbana. RC20: clave de inmueble dentro de esa parcela. Las referencias rurales, truncadas o no reconocidas quedan pendientes; no se reparan a ciegas.
- La validación de formato no comprueba dígitos de control. `checksum_status=not_checked` permanece explícito. La confirmación de existencia exige respuesta de la autoridad; para RC20 se solicita DNPRC exacto.
- Una RC20 con CP pero sin DNPRC es `parcel_candidate`, no un inmueble confirmado. Un fallo no se interpreta como inexistencia.
- Una dirección se normaliza preservando el original y los datos de planta/puerta. No existe cruce automático aproximado por dirección.
- Cada RC de una fila se expande a una fila de enlace; las filas sin RC también se conservan. No se eliminan históricos ni códigos repetidos.
- `certificate_scope_raw` conserva `edif_tipo`. `scope_map` está vacío: solo se añadirá un catálogo explícito tras contrastar valores reales. Los códigos sin revisar son `unknown`, nunca edificio completo por defecto.
- Las letras permanecen en las observaciones CEEE. `building_id` queda nulo mientras no haya evidencia de bloque físico; los objetos BU de la parcela figuran únicamente como candidatos. Incluso una única geometría BU puede representar una agrupación de parcela.
- Las coordenadas CP corresponden a su punto de referencia, no a la puerta de la vivienda. BU conserva geometría WKT cuando el GML tiene anillos 2D reconocidos y CRS correcto; su validación es estructural, sin garantía topológica.

## Archivos y métricas

`certificate_reference_links.parquet` contiene el cruce conservador; `building_objects.parquet`, objetos BU sin calificaciones energéticas. `source_schema.json` registra tipos JSON observados, tipos declarados y tipos inferidos; permanece vacío si no hay observaciones. `integration_schema.json` documenta el contrato Pandas/Arrow, incluso para salidas vacías.

`results.json` y `results.md` distinguen filas originales, referencias expandidas, formato válido, existencia confirmada, coincidencias y alcance de coordenadas. El porcentaje principal usa todas las filas de referencia como denominador; también se calcula el de filas CEEE con todas sus referencias confirmadas. Sin filas, el porcentaje es `null`, no 0%.

## Piloto y cobertura

Se retira el criterio inicial basado en subvenciones. Usera, Chamberí y Carabanchel son **candidatos**, no distritos con cobertura demostrada. Para evaluarlos, configurar `district_boundaries` con un fichero oficial local y su campo de nombre; requiere GeoPandas. La selección exploratoria utiliza el número de filas con identidad confirmada y punto dentro del distrito. Los puntos sobre límites o ambiguos no se asignan automáticamente.

Una página ordenada por `_id` y cinco referencias no estima cobertura poblacional ni compara representativamente distritos. La selección definitiva exigirá muestreo equilibrado y denominadores catastrales por distrito. No se puede seleccionar honestamente un piloto definitivo con la ejecución actual.

## Verificación

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Las fixtures son sintéticas y solo viven en pruebas temporales. Se verifican límites HTTP, caché, errores de red/XML, RC múltiples, ámbito desconocido, separación vivienda/parcela/edificio, ambigüedad, geometría estructural y escritura/lectura Parquet. Estas pruebas no verifican disponibilidad de las fuentes ni precisión en datos reales.
