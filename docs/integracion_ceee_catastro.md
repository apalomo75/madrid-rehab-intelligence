# Integración CEEE–Catastro y cartografía distrital

## Reproducción

Desde la raíz del repositorio, con Python 3.11 o superior:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
```

Solo la primera captura de límites necesita red. No vuelve a descargar los conjuntos masivos:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.districts \
  --raw-dir data/raw/session_2/districts
```

Pipeline municipal, sin red:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.session2 \
  --input-dir data/processed/session_1 \
  --boundary-dir data/raw/session_2/districts \
  --output-dir data/processed/session_2
```

Una salida no vacía se rechaza para evitar mezclar ejecuciones. Para reproducir:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.session2 \
  --output-dir data/processed/session_2_replay
```

La sesión 1 es de solo lectura: se comprueban los hashes de su manifiesto antes de procesar y nuevamente al terminar. El pipeline no hace peticiones HTTP. Los originales y las salidas grandes están excluidos de Git.

## Entidades y claves

| Entidad | Clave | Qué acredita |
| --- | --- | --- |
| Versión de fila CEEE | `record_id` de sesión 1 | Identidad de contenido, no certificado administrativo único |
| Certificado administrativo declarado | `edif_codreg` | Identificador declarado; se conserva su historial y posibles repeticiones |
| Inmueble declarado | RC20 completa | Declaración del registro CEEE; el sufijo no verifica existencia del inmueble |
| Parcela | RC14, prefijo de RC20 | Identidad explícita de parcela contra `nationalCadastralReference` de CP |
| Fila CP | `record_id` y `parcel_id` originales | Fila concreta; el identificador oficial puede repetirse con geometrías distintas |
| Objeto BU | `building_id` y `record_id` | Agregado catastral de construcciones de la parcela |
| Distrito | Código municipal de dos dígitos | Geometría administrativa oficial, independiente de códigos postales |

El enlace se hace por referencias explícitas. Se conservan el literal, su normalización, posición dentro de la fila, tipo admitido y todos los registros CP/BU candidatos. No se resuelven discrepancias por dirección, proximidad, superficie ni selección de una fila arbitraria.

La normalización elimina espacios y pasa letras a mayúsculas; no corrige caracteres ni elimina acentos. Se admiten las estructuras urbana y rústica documentadas de RC14 y RC20. `format_valid` significa únicamente **formato admitido**. No se calculan caracteres de control y no se admiten automáticamente referencias de 18 caracteres. Una referencia no admitida puede ser válida en un caso no soportado; no se declara inexistente.

Las referencias múltiples se expanden conservando sus posiciones. La tabla de certificados mantiene una fila por `record_id`; las métricas de certificados no usan el número de referencias ni el número de BU como denominador. Un certificado con parte de sus referencias resuelta queda `candidate`, aunque una referencia individual esté confirmada.

## Estados y evidencia por nivel

| Nivel | Confirmed | Candidate | Ambiguous | Unmatched |
| --- | --- | --- | --- | --- |
| Parcela | Una única fila CP coincide con RC14 | Solo algunas referencias del certificado se han confirmado | Varias filas CP o conflicto de código del certificado | Sin CP en la captura o referencia no admitida |
| Inmueble RC20 | Requeriría confirmación del registro de inmuebles, ausente de estas tablas | RC20 declarada y parcela encontrada | Identidad de parcela/certificado en conflicto | Sin RC20 o sin correspondencia en la captura |
| Edificio físico | Requiere evidencia independiente de cobertura física del certificado | BU plausible por parcela; no hay evidencia de cobertura | Más de un BU candidato o conflicto de parcela | No hay BU para la referencia |

No existe una regla de confirmación física automática en esta versión: las tres tablas no contienen la documentación necesaria para acreditar cobertura de bloque. Un certificado de bloque completo es una declaración de ámbito, incluso si usa RC20; no demuestra correspondencia con un agregado BU. Un BU único o una vivienda unifamiliar tampoco bastan para promover la relación a `confirmed` físico. Las razones quedan registradas en cada enlace. Para admitir evidencia adicional en una sesión posterior será necesario añadir su fuente pública y un procedimiento de revisión verificable.

El ámbito energético de sesión 1 permanece intacto: `dwelling`, `whole_building`, `building_part`, `unknown`. La etiqueta de parte comprende locales, sin equipararla con BuildingPart de Catastro. Los valores nuevos de `edif_tipo` siguen desconocidos hasta revisar su semántica. Las letras pertenecen al certificado y a su ámbito, nunca al polígono BU por una coincidencia de parcela.

`unmatched` se refiere a esta captura y a los tipos de referencia admitidos. En inmueble también incluye ausencia de RC20, con motivo explícito. No equivale a ausencia de certificado administrativo o inexistencia en Catastro.

## Geometrías, atributos y distritos

Se lee WKT y se valida otra vez con Shapely. Para uso espacial se exige polígono/multipolígono no vacío, topología válida, CRS EPSG:25830 y envolvente compatible con Madrid. Los errores se conservan y señalan; no se reparan silenciosamente. Las filas descartadas de la visualización siguen en `buildings_audited.parquet`.

Los límites se obtienen de la capa poligonal 26, DISTRITOS, del [servicio oficial de límites administrativos](https://sigma.madrid.es/hosted/rest/services/CARTOGRAFIA/LIMITES_ADMINISTRATIVOS/MapServer), enlazado por el [catálogo municipal](https://datos.madrid.es/dataset/300497-0-distritos-municipales-madrid). Se guardan servicio, esquema de capa, GeoJSON, URL exacta, cabeceras, captura, atribución y SHA-256. La consulta solicita expresamente EPSG:4326; el análisis reproyecta a EPSG:25830 con orden longitud/latitud. Se exigen 21 códigos distintos, polígonos válidos y ausencia de solapamientos de superficie mayores de 0,01 m². Licencia del catálogo: CC BY 4.0, Ayuntamiento de Madrid.

Cada parcela y BU se asigna por su punto interior (`point_on_surface`), no por dirección ni centroide posiblemente exterior. Si el punto cae en un límite compartido se conserva `boundary_ambiguous`; si no cae en ningún distrito, `unassigned`. Un polígono con intersección de superficie mayor de 0,01 m² en varios distritos se marca `crosses_district_boundary`, se cuenta una sola vez por su punto interior y mantiene su geometría entera. No se recorta ni se duplica para aumentar cifras. Hay registros de ámbito municipal sin distrito asignable con esta geometría; se informan aparte.

Los certificados se localizan **a nivel de parcela** mediante la asignación de sus filas CP. Para varias referencias o varias filas CP, solo se da un código distrital si todas las candidatas utilizables caen en ese mismo distrito; se conserva la calidad candidata cuando la identidad de parcela es ambigua. La comparación muestra por separado localizados, confirmados a parcela y ambiguos. No utiliza el distrito como nueva evidencia de identidad.

La comparación se limita a Usera (12), Carabanchel (11) y Chamberí (07). Criterio fijado antes de obtener resultados: al menos 100 registros CEEE localizados y 99% de geometrías BU utilizables; ordenar por porcentaje de confirmación a parcela entre localizados, después validez geométrica, menor número de BU para facilitar revisión y código. No se mide necesidad de rehabilitación ni se usan ayudas.

Atributos utilizables sin añadir inferencias:

- `current_use`: uso declarado del agregado BU; `1_residential` sirve para filtrar residencial, sin inferir uso exclusivo ni ocupación.
- `construction_begin` / `construction_end`: fechas de la unidad constructiva más antigua y más reciente del agregado según el [modelo oficial de conjuntos catastrales](https://www.catastro.hacienda.gob.es/webinspire/documentos/Conjuntos%20de%20datos_en.pdf). El mapa presenta años derivados únicamente cuando son interpretables y están entre 1000 y 2026. El intervalo no es una fecha de reforma ni una antigüedad única del bloque.
- `numberOfDwellings` y `numberOfBuildingUnits`: cantidades declaradas, sin equiparar unidades constructivas/funcionales con hogares ocupados.
- `edif_superf`: superficie habitable declarada en CEEE. No se compara con huella en planta para confirmar cobertura física.

Los miembros de un multipolígono no se cuentan como edificios físicos independientes. La definición oficial de Building agrega las construcciones sobre rasante de una parcela; BuildingPart representa volúmenes homogéneos. Esto explica que cero parcelas con varios identificadores BU no signifique un solo bloque físico por parcela. Véase el [documento oficial de conjuntos de datos](https://www.catastro.hacienda.gob.es/webinspire/documentos/Conjuntos%20de%20datos.pdf).

## Salidas de sesión 2

Todas bajo `data/processed/session_2/`:

| Archivo | Grano |
| --- | --- |
| `certificate_reference_links.parquet` | Certificado × referencia declarada; estados de los tres niveles y razones |
| `certificates_integrated.parquet` | Una fila por registro CEEE; resumen sin multiplicaciones |
| `parcels_audited.parquet` | Filas CP originales con auditoría y distrito |
| `buildings_audited.parquet` | BU originales con auditoría y distrito |
| `building_certificate_contexts.parquet` | Contextos certificado–BU por parcela; nunca cobertura física confirmada |
| `districts.parquet` | Los 21 límites oficiales reproyectados |
| `district_comparison.parquet` | Comparación de los tres candidatos |
| `pilot_buildings.parquet` | BU del piloto utilizables; geometría original y copia GeoJSON para dibujar |
| `pilot_certificates.parquet` | Registros que dan contexto a BU dibujables del piloto |
| `quality_metrics.json` / `informe_calidad.md` | Métricas, denominadores, esquemas, procedencia y hashes |
| `run_config.json` | Configuración de la reproducción |

Son Parquet convencionales con WKT/CRS y, para el mapa, GeoJSON serializado. La simplificación conserva topología, tolerancia 0,25 m y límite de cambio de área del 1%; si se supera vuelve a la geometría original. No altera ninguna geometría analítica. La frontera distrital se simplifica 1 m solo al dibujar.

## Aplicación local

```bash
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512 --server.headless true \
  --browser.gatherUsageStats false
```

Abrir `http://127.0.0.1:8512`. El puerto 8501 estaba ocupado durante la validación. La configuración del proyecto limita la escucha a localhost y desactiva estadísticas de uso. No hay publicación ni subida de datos. Para otra salida local, anteponer `MADRID_REHAB_SESSION2_DIR=/ruta/a/session_2_replay`.

El mapa tiene fondo local sin teselas externas, límites oficiales y polígonos BU. PyDeck permite navegación y consulta emergente. La selección por clic de GeoJsonLayer no se verificó con fiabilidad en el navegador de este entorno y está desactivada; la ficha se abre mediante un selector por identificador público, probado con datos reales. El panel presenta información catastral, fechas, fuentes y certificados **de la parcela**, con los tres estados de vínculo. Los filtros seleccionan ámbito, letra y estado al nivel elegido. No se elige automáticamente el certificado vigente ni se asigna letra al BU.

Los elementos sin contexto CEEE se muestran en gris; información existente sin confirmación al nivel elegido, naranja; relación confirmada **al nivel elegido**, turquesa. El color no codifica una calificación energética. Un objeto que tiene información de otra letra/ámbito y queda fuera del filtro se oculta, en lugar de relabelarlo como sin información. La inclusión de BU sin CEEE es un control independiente.

Indicadores de la vista: BU dibujados; registros CEEE únicos asociados a sus parcelas tras filtros; registros confirmados y ambiguos al nivel elegido; proporción de BU dibujados con contexto CEEE. Se explicita que ese último denominador es el número de BU representados, no el parque total ni cobertura certificada del edificio físico. Las relaciones por varias referencias se deduplican al contar certificados.

## Validación

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_session2.py' -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_app.py' -v
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src/madrid_rehab/{session2,districts,map_view,app}.py tests/test_session2.py tests/test_app.py
```

`test_app.py` utiliza los Parquet reales y se omite explícitamente si aún no se ha generado sesión 2. Las pruebas sintéticas permanecen bajo `tests/`, sin entrar en ninguna salida del mapa. La prueba en Chromium es adicional y local; su captura queda bajo `reports/session_2/`.

Referencias de implementación: [selección en PyDeck, Streamlit 1.50](https://docs.streamlit.io/1.50.0/develop/api-reference/charts/st.pydeck_chart), [referencia catastral oficial](https://www.catastro.hacienda.gob.es/es-ES/referencia_catastral.html), [consulta por los 14 primeros caracteres](https://www.catastro.hacienda.gob.es/ayuda/ayuda_consulta_localizacion.htm).

Comprobación opcional en Chromium (con el servidor local en marcha):

```bash
.venv/bin/python -m pip install -r requirements-browser.lock
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser .venv/bin/python -m playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_session2.py
```

El estilo vacío se incorpora como una URL `data:`; no necesita teselas, fuentes tipográficas remotas ni claves de API cartográfica. La prueba comprueba ausencia de peticiones externas, renderizado, ficha por identificador y filtro de ámbito. Las capturas permanecen locales.
