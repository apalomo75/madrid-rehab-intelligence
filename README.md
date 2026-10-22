# Madrid Rehab Intelligence

Proyecto de plataforma pública para explorar el potencial de rehabilitación residencial en Madrid.

**Sesión 1 completada:** 115.664 registros de certificados, 141.244 filas de parcelas y 124.396 objetos BU. Originales verificables, tablas separadas y reproducción sin red. Véanse los [resultados y limitaciones](docs/sesion_1.md) y la [guía de ingesta](docs/ingesta.md). Los resultados reales y su calidad se guardan en `data/processed/session_1/informe_ingesta.md`.

## Sesión 3: visor y análisis energético

El visor incorpora tres pestañas, selección por ID en PolygonLayer, mapa urbano OpenStreetMap con alternativa sin conexión, ficha de parcela y filtros energéticos. **La comprobación real de clic y las capturas están pendientes:** este entorno bloquea el puerto local y Chromium. Las 73 pruebas Python/AppTest pasan; no sustituyen la aceptación en navegador. Véanse [sesión 3](docs/sesion_3.md), [uso del visor](docs/visor.md) y [decisión cartográfica y licencias](docs/componente_cartografico.md).

La ejecución local usa el comando Streamlit de abajo y los datos existentes de sesión 2, sin regenerarlos. Para iniciar sin teselas externas, anteponer `MADRID_REHAB_OFFLINE=1`. No se incorporan nuevas dependencias.

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python tests/benchmark_session3.py
# Prueba visual: requiere el servidor local en otra terminal e internet para OSM.
.venv/bin/python -m pip install -r requirements-browser.lock
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser .venv/bin/python -m playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_session3.py
# Solo pruebas de esta sesión:
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_session3.py' -v
```

Informes en `reports/session_3/`; las capturas se producirán únicamente si la prueba de navegador puede ejecutarse correctamente.

## Sesión 2: integración y aplicación local

La integración conserva los niveles de parcela, inmueble RC20 y edificio físico. **113.072 de 115.664 registros (97,759%) confirman parcela; ninguno acredita todavía cobertura de edificio físico.** El piloto seleccionado es **Chamberí**, por calidad de localización y menor carga de revisión frente a los otros candidatos. Véanse la [metodología](docs/integracion_ceee_catastro.md) y los [resultados de sesión 2](docs/sesion_2.md).

```bash
.venv/bin/python -m pip install -r requirements.lock
# Solo si aún no están guardados los límites oficiales:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.districts
# No usa red ni vuelve a descargar Catastro/CEEE:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.session2
# Abrir http://127.0.0.1:8512
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512 --server.headless true \
  --browser.gatherUsageStats false
```

Los nuevos Parquet e `informe_calidad.md` quedan en `data/processed/session_2/`. El pipeline rechaza salidas existentes; para reproducir, añadir `--output-dir data/processed/session_2_replay`. La sesión 1 permanece intacta. La aplicación es exclusivamente local, muestra geometrías oficiales y no atribuye la letra de viviendas al edificio. Las capturas de validación están en `reports/session_2/`.

## Ingesta municipal

```bash
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m madrid_rehab.ingest
```

Genera `certificados_madrid.parquet`, `parcelas_madrid.parquet`, `edificios_madrid.parquet` e `informe_ingesta.md` en `data/processed/session_1/`. Conserva originales en `data/raw/session_1/`. Cada ejecución completada requiere una salida nueva. Para repetir sin red: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.ingest --offline --output-dir data/processed/session_1_replay`.

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src/madrid_rehab/ingest.py tests/test_ingest.py
```

## Ejecutar

Desde la raíz, con Python >=3.11 y acceso al índice de paquetes:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cli \
  --raw-dir data/raw/run_002 \
  --output-dir data/processed/run_002 \
  --report-dir reports/run_002
```

En este entorno `.venv` hereda Pandas/PyArrow preexistentes mediante `--system-site-packages`; no se modificaron instalaciones globales. Los detalles y limitaciones de instalación figuran en la [guía del pipeline](docs/pipeline.md).

La muestra tiene un máximo de 30 filas CEEE, cinco referencias, 20 peticiones y 5 MiB por ejecución. No descarga ZIP municipales. Se conservan originales, errores, configuración y hashes. Una ejecución sin filas devuelve código 2; usar un directorio de informes nuevo para cada ejecución.

## Pruebas

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

73 pruebas: contratos offline y pruebas de Streamlit con los Parquet reales cuando están disponibles. Incluyen referencias múltiples, varios BU por parcela, conflictos, geometría, ausencia de información y reproducción de cruces. Las pruebas sintéticas no representan precisión ni cobertura de las fuentes reales.

## Organización y reglas de integración

- `src/madrid_rehab/`: adaptadores, normalización, cruce, informes y CLI.
- `tests/`: pruebas con ejemplos sintéticos; `config/`: límites y fuente candidata.
- `data/raw/` y `data/processed/`: artefactos locales excluidos de Git.
- `reports/first_run/`: evidencia de la ejecución bloqueada.
- `docs/`: investigación, arquitectura, ejecución y resultados.

Se distinguen parcela RC14, inmueble RC20 y objetos BU. Las direcciones no fuerzan coincidencias. El ámbito energético original se conserva; el mapa revisado de cuatro valores está versionado en la ingesta. Una vivienda no transfiere su letra al edificio y un punto de parcela no cuenta como bloque identificado.

Usera, Chamberí y Carabanchel son candidatos a comparar por disponibilidad y calidad, sin usar subvenciones. La selección de distrito requiere todavía medir cobertura contra límites oficiales.

## Documentación

| Documento | Contenido |
| --- | --- |
| [Guía del pipeline](docs/pipeline.md) | Instalación, límites, reproducción y métricas |
| [Resultados](docs/resultados_pipeline.md) | Cifras reales, bloqueo, validación y pendientes |
| [Fuentes](docs/fuentes_datos.md) | Accesos, variables, granularidad y licencias |
| [Viabilidad](docs/viabilidad.md) | Riesgos y criterios de decisión |
| [Arquitectura](docs/arquitectura.md) | Diseño general y alcance implementado |
| [Plan](docs/plan_desarrollo.md) | Fases y autorización vigente |
| [AGENTS.md](AGENTS.md) | Instrucciones de contribución |

Streamlit y el mapa local están implementados en la sesión 2. No se han incorporado ITE/IEE, órdenes ni subvenciones. La sesión 1 autoriza la descarga municipal oficial dentro de los límites documentados. La muestra nueva confirma cinco parcelas con coordenadas y aplica la normalización de ámbito; no resuelve la cobertura física de los certificados.
