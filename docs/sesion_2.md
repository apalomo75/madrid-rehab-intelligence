# Sesión 2: integración Catastro–CEEE y mapa local

La sesión procesa exclusivamente los tres Parquet de sesión 1 y los límites oficiales de distritos del Ayuntamiento. Los originales y resultados de sesión 1 permanecen intactos. No se ha vuelto a descargar Catastro/CEEE, publicado la aplicación, realizado commits ni incorporado otras capas o modelos.

## Resultados de integración

El denominador municipal es **115.664 versiones de registro CEEE**, no certificados administrativos únicos ni edificios físicos.

| Nivel | Confirmados | Candidatos | Ambiguos | Sin correspondencia |
| --- | ---: | ---: | ---: | ---: |
| Parcela | 113.072 (97.7590%) | 6 (0.0052%) | 66 (0.0571%) | 2.520 (2.1787%) |
| Inmueble RC20 | 0 (0.0000%) | 95.490 (82.5581%) | 56 (0.0484%) | 20.118 (17.3935%) |
| Edificio físico | 0 (0.0000%) | 112.260 (97.0570%) | 72 (0.0622%) | 3.332 (2.8808%) |

114.172 registros (98,7101%) tienen todas sus referencias con formato admitido urbano/rústico; 114.176 tienen al menos una. No se validan caracteres de control ni existencia de RC20. Se generan 115.731 filas de referencia para 115.664 registros; 31 contienen varias referencias. Los seis casos parcialmente resueltos a parcela quedan candidatos, no confirmados.

**Uso seguro:** 113.072 registros confirman identidad de parcela (97,759% del total). De ellos, 113.070 permiten asignación distrital única y utilizable (97,7573% del total). Otros 66 tienen distrito candidato pero identidad de parcela ambigua. Ninguno puede utilizarse para colorear un edificio físico con la letra de una vivienda o local. La ausencia de confirmaciones físicas expresa falta de evidencia de cobertura en estas tablas, no imposibilidad de resolverla con documentación pública futura.

La ampliación al formato rústico y la comprobación de todas las referencias explican la diferencia frente al recuento preliminar de sesión 1. La normalización no corrige referencias ni conserva solo el primer componente.

## Distribución por ámbito

| Ámbito conservado | Registros | Confirmados a parcela | Confirmados a edificio físico |
| --- | ---: | ---: | ---: |
| building_part | 7.118 | 6.979 | 0 |
| dwelling | 85.599 | 83.706 | 0 |
| unknown | 1.654 | 1.610 | 0 |
| whole_building | 21.293 | 20.777 | 0 |

Los 1.654 ámbitos desconocidos se conservan. Entre los literales sin clasificar aparecen etiquetas terciarias no revisadas, errores de escritura, vacíos y tres valores con aspecto de fecha. No se corrigen por suposición. Las letras siguen en cada registro original; no se elige automáticamente un certificado vigente entre versiones históricas.

## Auditoría de entidades y geometrías

Hay 216 referencias CP repetidas con geometrías distintas; se conservan sus 865 filas y se evita escoger una arbitrariamente. Hay 10.513 valores literales de referencia CEEE con varios registros, lo que puede reflejar viviendas distintas o historial; no se deduplica por referencia. Se conservan las dos repeticiones no vacías de código de certificado ya detectadas en sesión 1.

No hay parcelas con varios identificadores BU en esta captura, pero 14.869 objetos BU tienen varios miembros poligonales. Un identificador BU representa un agregado catastral; no demuestra un único bloque físico. Las pruebas cubren también el caso de varios BU por parcela aunque no aparezca en la captura real.

Las 141.244 geometrías CP son válidas. De 124.396 BU, 124.395 tienen geometría utilizable y uno inválido se conserva en la auditoría y se excluye del mapa. Hay 15 filas CP y cuatro BU sin asignación distrital única; este último recuento incluye el BU inválido. Se señalan 105 parcelas y diez BU que cruzan límites distritales sin duplicarlos ni recortarlos en las métricas. Se mantiene documentada la diferencia de 186 registros entre la cabecera CP y sus elementos reales.

Los atributos utilizables son identificadores, uso declarado, cantidades declaradas y fechas constructivas del agregado con su semántica oficial. Los años mostrados son el más antiguo y el más reciente de las unidades del BU; no indican una reforma ni un año único del bloque. La superficie habitable CEEE no se compara con la huella para confirmar cobertura.

## Comparación y elección del piloto

| Distrito | BU | CEEE localizados | Confirmados a parcela | % entre localizados | Ambiguos a parcela | Geometría BU válida |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Chamberí | 3.761 | 5.105 | 5.105 | 100.0000% | 0 | 100% |
| Carabanchel | 9.439 | 8.792 | 8.786 | 99.9318% | 6 | 100% |
| Usera | 6.313 | 4.435 | 4.435 | 100.0000% | 0 | 100% |

**Seleccionado: Chamberí.** Chamberí y Usera alcanzan el 100% de confirmaciones a parcela entre sus registros localizados y geometrías válidas. Chamberí requiere revisar 3.761 BU frente a 6.313 en Usera. Carabanchel presenta seis localizados ambiguos y mayor volumen. La elección sigue el criterio previo de calidad y carga de revisión, no una necesidad de rehabilitación presumida.

La asignación usa puntos interiores de las geometrías completas en EPSG:25830, con indicador de cruce de frontera. Las parcelas ambiguas solo aportan distrito candidato si todas sus geometrías caen en ese mismo distrito. Los límites oficiales y su procedencia quedan en `data/raw/session_2/districts/`; la consulta poligonal devuelve los 21 distritos, sin solapamientos de superficie relevantes para la tolerancia documentada.

## Aplicación y limitaciones

La vista inicial filtra uso residencial declarado: **3.311 BU**, 4.922 registros CEEE en sus parcelas y 1.996 BU con ese contexto, cobertura de contexto del 60,3% sobre 3.311 BU dibujados. Al incluir todos los usos se dispone de 3.761 BU y 5.105 registros. La comparación distrital y la vista residencial tienen denominadores distintos, visibles en la interfaz.

Se ofrecen filtros de ámbito, letra y estado/nivel; distinción entre información confirmada al nivel elegido, información sin confirmación y ausencia de contexto en la captura; fichas con ámbito original, niveles, identificadores, fechas constructivas y procedencia. No se asigna letra a los BU. La visualización usa copia simplificada a 0,25 m con topología conservada y cambio de área máximo del 1% (máximo real 0,969912%). Las geometrías analíticas y originales permanecen intactas.

El mapa usa fondo autocontenido sin teselas ni peticiones externas. La ficha se selecciona por identificador público. La selección mediante clic de GeoJsonLayer no resultó verificable con fiabilidad en este entorno y se desactiva; la navegación y el selector de ficha funcionan. Esta limitación de interacción no modifica relaciones ni indicadores.

## Pruebas y reproducción

63 pruebas pasan, incluidas pruebas sintéticas de ambigüedad, múltiples referencias, varios BU, viviendas frente a edificios completos, errores de geometría, ausencia de información y estabilidad ante reordenación. Las pruebas de Streamlit usan datos reales cuando los Parquet de sesión 2 están disponibles. Las pruebas sintéticas nunca alimentan el mapa final.

Dos ejecuciones municipales completas sin red producen hashes idénticos para los nueve Parquet, métricas e informe. Los hashes de sesión 1 siguen intactos. Véase `reports/session_2/reproducibility.json`. La validación adicional en Chromium verifica renderizado, ficha por identificador, filtro de ámbito y cero errores JavaScript/peticiones externas; capturas y resultado en `reports/session_2/`.

```bash
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m madrid_rehab.session2
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512 --server.headless true \
  --browser.gatherUsageStats false
```

Abrir `http://127.0.0.1:8512`. Para una nueva reproducción, usar `--output-dir data/processed/session_2_replay`; si ya existe, escoger otro directorio vacío. Los límites oficiales solo necesitan capturarse una vez con `python -m madrid_rehab.districts`, según la [guía completa](integracion_ceee_catastro.md).

## Archivos entregados

- Código: `districts.py`, `session2.py`, `map_view.py`, `app.py` bajo `src/madrid_rehab/`.
- Pruebas: `tests/test_session2.py`, `tests/test_app.py`, `tests/browser_session2.py`.
- Configuración: `.streamlit/config.toml`, dependencias y archivos de versiones fijadas.
- Documentación: esta sesión, metodología de integración, README, arquitectura y AGENTS actualizados.
- Datos: nueve Parquet y manifiestos/informe bajo `data/processed/session_2/`; reproducción bajo `session_2_replay/`. `session_2_initial/` conserva una corrida de desarrollo previa; no alimenta la aplicación ni es la entrega validada.
- Evidencia legible: `reports/session_2/informe_calidad.md`, `auditoria_tablas.md`, `reproducibility.json`, `browser_validation.json` y dos capturas PNG.

Quedan pendientes evidencia pública de cobertura física, revisión semántica de ámbitos desconocidos, causa de duplicidades CP y del recuento declarado, y corrección del único BU inválido mediante un procedimiento explícito. No se han sustituido esas verificaciones por inferencias espaciales o letras agregadas.
