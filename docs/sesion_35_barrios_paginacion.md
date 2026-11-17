# Sesión 35 · barrios oficiales y paginación del mapa

## Fuente, licencia, fecha y estructura

Fuente principal: [Barrios municipales de Madrid · Ayuntamiento de Madrid](https://servpub.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=422fa235-762b-11e9-861d-ecb1d753f6e8). El catálogo describe **131 barrios de los 21 distritos de Madrid capital**, fecha de datos **31/08/2026**. No acredita divisiones de los otros cinco municipios del catálogo comercial.

Se aplican las [condiciones generales de reutilización del Ayuntamiento de Madrid](https://datos.madrid.es/pages/condiciones-generales-ayuntamiento-de-madrid): reutilización comercial y no comercial, atribución, mención de la fecha disponible, conservación de metadatos y condiciones, sin desnaturalización ni sugerir respaldo municipal. No se ha etiquetado esta fuente como CC BY. Atribución visible: «Origen de los datos: Ayuntamiento de Madrid · Barrios municipales · 31/08/2026». La fecha es la del catálogo, no una fecha de actualización individual de cada parcela.

Se capturó el [TopoJSON oficial](https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/LIMITES_ADMINISTRATIVOS/Barrios/TopoJSON/Barrios.json): `Topology`, objeto `Barrios`, 131 geometrías, arcos delta, transformación y coordenadas de longitud/latitud. El EPSG:25830 indicado por el catálogo no describe las coordenadas decodificadas de ese archivo. La validación estricta detectó extremos de arcos no coincidentes (`Disconnected TopoJSON arcs`); no se aplicaron reparaciones silenciosas para convertirlo en límites utilizables.

**Alternativa oficial del mismo catálogo:** su servicio de límites administrativos, [capa BARRIOS 25](https://sigma.madrid.es/hosted/rest/services/CARTOGRAFIA/LIMITES_ADMINISTRATIVOS/MapServer/25?f=pjson), consultado una vez con `outSR=25830`, `returnGeometry=true` y todos los registros. La respuesta contiene exactamente 131 polígonos válidos, sin solapamientos de área superiores a 0,01 m². Sus códigos, nombres y distritos coinciden exactamente con los del TopoJSON. Los 21 códigos/nombres distritales coinciden con el paquete base. No se empleó `make_valid`, `buffer(0)` ni simplificación.

Los originales y respuestas se conservan en `data/raw/neighborhoods/session_35_capture_02/`, con URLs, SHA-256, tamaños y cabeceras de las respuestas del servicio en `capture.json`. Se reutilizaron por copia los bytes ya obtenidos del TopoJSON y catálogo en `session_35_capture_01/`. La posterior descarga local de las condiciones agotó el tiempo de espera: se revisó la página oficial mediante la herramienta web, pero **no se afirma haber archivado su HTML**. Los metadatos reconstruidos de los dos primeros archivos indican que no se conservaron sus cabeceras HTTP. No se alteraron los originales de ninguna captura.

## Producto y regla espacial

`src/madrid_rehab/neighborhoods.py` prepara offline `data/processed/geography/session_35_01/`. Utiliza exclusivamente las CP existentes del paquete v1_03 y conserva literalmente sus referencias. `boundaries.parquet` mantiene los polígonos oficiales en EPSG:25830; `neighborhoods.parquet` contiene la jerarquía y nombres; `assignments.parquet` contiene una fila por referencia; `issues.parquet` conserva las incidencias y todas las áreas candidatas de los cruces auditados. `counts.csv` permite revisar los recuentos agregados. `manifest.json` fija los hashes de las entradas y productos y el contrato de CP.

Regla determinista:

1. Exigir una sola fila CP para la referencia, geometría utilizable/válida en EPSG:25830 y distrito existente único. Las referencias duplicadas no se resuelven eligiendo una fila.
2. Calcular las intersecciones de área positiva con los barrios mediante un índice espacial. El simple contacto de frontera de área cero no asigna barrio.
3. Elegir la mayor superficie de intersección en m². En empates dentro de 0,000001 m², elegir el menor código oficial. Es una asignación territorial de parcela; no confirma edificios físicos.
4. Exigir que el distrito del barrio ganador coincida con el distrito verificado existente. Si difiere, registrar `district_conflict` y no asignar barrio, sin reasignar el distrito ni forzar el segundo candidato.
5. Mantener una sola salida por referencia y registrar cruces, empates, candidaturas, áreas y proporción ganadora. No se exige cobertura del 100 % de la parcela; se usa el mayor solape, con su proporción auditable.

| Universo | Referencias únicas | Con barrio | Sin barrio |
| --- | ---: | ---: | ---: |
| CP Madrid existentes, 141.244 filas originales | 140.595 | 140.360 | 235 |
| Catálogo comercial Madrid v1_03 | 113.550 | 113.548 | 2 |

Las 235 referencias sin barrio se desglosan en 216 referencias duplicadas, 13 sin distrito y 6 incompatibilidades distritales. Hay 258 cruces con barrio asignado, sin empates reales de área; las pruebas sintéticas sí verifican el desempate. `issues.parquet` conserva las 493 incidencias totales. Los seis conflictos distritales son `2026003VK4722E`, `28900A03809001`, `28900L00509003`, `5481702VK3658B`, `6903601VK4760D` y `8505639VK3880F`.

Las dos CP comerciales sin asignación conservan su estado previo sin distrito; permanecen en «Todos los distritos / Todos los barrios», no se atribuyen a un barrio. Los recuentos por los 131 barrios y el residuo están en `reports/session_35_neighborhoods/review_01/benchmark.json`. No deben confundirse los totales de todo el universo CP con los del catálogo comercial.

## Interfaz y filtros

Escritorio: **Municipio → Distrito → Barrio** en tres columnas. El barrio está deshabilitado hasta elegir distrito, siempre incluye «Todos los barrios» y solo ofrece los barrios de ese distrito. Cambiar distrito reinicia el barrio; cambiar municipio reinicia distrito y barrio. Para Alcalá de Henares, Alcorcón, Getafe, Leganés y Móstoles se ocultan ambos selectores de Madrid. Los nombres oficiales permanecen intactos en ES/EN.

La combinación OR/AND de CEEE, ITE/IEE, Plan Rehabilita y NextGenerationEU se calcula antes de la restricción geográfica común. Contador, mapa, lista y selección de ficha comparten el mismo conjunto. Sin cambios de expedientes, certificados ni autorizaciones. Las fichas conservan evidencias, programas y ámbitos documentales.

Controles centrados inmediatamente bajo el mapa, dentro de su columna izquierda:

`[Anterior]  Página X de Y  [Siguiente]`

Debajo: «Hasta 500 parcelas por página». Se elimina el selector «Página del mapa». El contenedor horizontal permite ajustar los controles al ancho disponible sin anchuras rígidas; las columnas de selectores se adaptan a móvil. ES/EN cubre nombres de controles, estado de página y límite.

- Total: techo del número de referencias filtradas dividido por 500. Deshabilitar el extremo correspondiente.
- Los cambios geográficos y de evidencias reinician la página del mapa a 1. Se conserva la selección únicamente si sigue siendo compatible con esa primera página; en otro caso se limpia.
- Abrir desde la lista una CP de otra página mueve el mapa a su página real. No se inyecta una geometría extra sustituyendo otra de la página.
- Cambiar la página del mapa limpia la ficha si su referencia queda fuera de la página de destino. No mueve ni reinicia la página de la lista lateral.
- Las páginas son segmentos disjuntos del conjunto ordenado existente. Máximo 500 referencias por lectura; sin simplificar ni alterar el WKT original. Sin resultados, el contador indica cero.

## Candidato y producción

Nuevo candidato independiente: **`data/deployment/madrid_rehab_v1_04_candidate_01/`**. No es un Release público y no se ha creado archivo de distribución. `candidate_status=local_visual_review_pending`; el estado de autorización PRTR heredado se conserva para que sus filtros sigan funcionando en esta revisión local.

Conserva byte a byte todos los productos de v1_03, sus políticas, autorizaciones, 5.046 expedientes y 4.378 parcelas PRTR regionales. Solo añade:

| Producto adicional | Bytes | SHA-256 |
| --- | ---: | --- |
| `geography/neighborhoods.parquet` | 5.610 | `23bb72f8d6050402f19b0a59224fb63c4620aa7f77bf657d1e2c1c26f0bfdf91` |
| `geography/assignments.parquet` | 534.731 | `0eeb1887ed50c0da48a96e56bb912c99bee83d9e96c6a638fec0e758acf7a8c0` |

Adición total: **540.341 bytes**. Paquete completo: **564.714.240 bytes** en productos, sin contar el manifiesto. SHA-256 del manifiesto candidato: `09edf48d90c4202e60c97734c740ec09928cf2a71057fb30bb0e52ad2dc7bffe`. Inventario de hashes, tamaños y comparación con el padre en `reports/session_35_neighborhoods/review_01/candidate.json`.

Los polígonos de barrio completos y las incidencias quedan en el producto offline. **El mapa no dibuja una capa adicional de límites**, por lo que no necesita llevar esas geometrías al paquete: utiliza las geometrías CP ya incluidas. Streamlit no descarga fuentes ni ejecuta intersecciones espaciales. No se añade ninguna dependencia; se reutilizan Shapely, PyProj, Pandas y PyArrow ya bloqueados.

Para producción será necesario aprobar y entregar **código actualizado y paquete con estos productos**. v1_02 y v1_03 se mantienen compatibles con la paginación nueva, pero no muestran barrios ni recurren a productos locales externos cuando se activa un bundle sin ellos. No se ha actualizado producción, subido datos ni publicado un Release.

## Reproducir y validar

Instalación de desarrollo: `.venv/bin/python -m pip install -r requirements.lock`. Producción conserva `python -m pip install -r requirements.txt`. No hay cambios de toolchain.

Reproducir offline con nuevas salidas:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.neighborhoods build --raw-dir data/raw/neighborhoods/session_35_capture_02 --base data/deployment/madrid_rehab_v1_03 --output-dir data/processed/geography/replay_35_nuevo
PYTHONPATH=src .venv/bin/python -m madrid_rehab.neighborhoods candidate --base data/deployment/madrid_rehab_v1_03 --geography-dir data/processed/geography/replay_35_nuevo --output-dir data/deployment/replay_35_candidate_nuevo
```

Para otra captura oficial acotada: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.neighborhoods capture --output-dir data/raw/neighborhoods/capture_35_nueva`. Usa una salida nueva; revisar fecha, condiciones y cambios del catálogo antes de sustituir esta versión auditada. La fecha de la versión actual permanece fijada explícitamente en el módulo, sin inferirla de las filas cuya fecha individual es nula.

Validación ejecutada: **Ruff correcto y 48 pruebas focalizadas correctas**, 7 nuevas y 41 regresiones. Incluyen las 131 identidades/21 distritos; rechazo del TopoJSON; correspondencia exacta con el servicio; cruces, empates, duplicados y conflictos; dependencias de selectores; seis municipios; selección/ficha; CEEE y PRTR OR/AND; ES/EN; páginas primera, intermedia y última; reinicios; lista independiente e integridad del padre.

```bash
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_neighborhoods.py -v
PYTHONPATH=src:tests .venv/bin/python -m unittest test_commercial_filters test_filter_navigation test_session30_ux test_i18n test_public_prtr test_session31 test_filter_simplification -v
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_04_candidate_01 MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 PYTHONPATH=src .venv/bin/python tests/benchmark_session35.py --output reports/session_35_neighborhoods/benchmark_nuevo.json
```

Resultados reales del catálogo: Villaverde → Los Rosales (`17` → `174`), **904 CP**; Chamberí → Gaztambide (`07` → `071`), **555 CP**. Gaztambide CEEE+PRTR: **348 OR / 18 AND**. Madrid solo NextGenerationEU: **3.300 CP**. La última página municipal tiene 50 CP; ninguna de las páginas probadas supera 500.

Construcción geográfica offline: **84,87 s y 519,36 MiB de RSS máximo**. Benchmark del recorrido público: **23,48 s y 451,03 MiB de RSS máximo**, primera pantalla a los 4,92 s. Son mediciones locales de proceso completo, sin garantías sobre memoria ni rendimiento en Cloud. El benchmark verifica que todas sus lecturas Parquet/SQLite permanecen dentro del candidato. Informes y registros en `reports/session_35_neighborhoods/review_01/`.

## Revisión local exacta

Desde `/home/apalo/madrid-rehab-intelligence`:

```bash
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_04_candidate_01 MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512 --server.headless true
```

URL: **http://127.0.0.1:8512**. Servidor local preparado con este candidato; revisión visual del propietario pendiente.

Capturas reproducibles cuando exista Chromium, siempre salida nueva:

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_session35.py --output-dir reports/session_35_neighborhoods/browser_nuevo
```

El intento actual queda **bloqueado** por ausencia del ejecutable Chromium; consta en `review_01/browser/browser.json`. No se descargó navegador. AppTest, eventos serializados, salud HTTP y recuentos no acreditan renderizado WebGL, ausencia de desbordamientos ni validación visual móvil. Revisar los tres selectores, 65/35, alineación bajo el mapa, primera/última página, retorno de ficha, ES/EN y anchos de escritorio/móvil antes de publicar.

Sin commit, push, despliegue ni publicación.
