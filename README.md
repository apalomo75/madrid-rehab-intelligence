# Madrid Rehab Intelligence

Estado vigente: **Madrid capital, 21 distritos seleccionables y 174 pruebas unittest/AppTest superadas**. Producto local `data/processed/session_7_final/`. [Expansión y cobertura](docs/sesion_7_expansion_madrid.md), [calidad municipal](docs/calidad_sesion_7.md). El piloto de Chamberí conserva sus indicadores. Sin eventos oficiales nuevos ni IPR global; validación visual pendiente por restricciones del sandbox.

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

## Sesiones 4–6: contratos de eventos y análisis por parcela

Se incorporan adaptadores CSV canónicos de ITE/IEE y ayudas con procedencia, validación, matching conservador y manifiestos. **No se han obtenido registros reales nuevos de estas dos fuentes**: formularios sin exportación verificada, HTTP 403 y restricciones DNS/API. Véanse [sesión 4](docs/sesion_4.md), [sesión 5](docs/sesion_5.md) y sus auditorías. No se utilizan fixtures en producción.

El análisis offline real produce 3.790 parcelas de Chamberí, 3.760 con periodo constructivo y 2.105 con evidencia energética confirmada en parcela. El perfil multidimensional es el resultado principal; no se publica IPR global. [Sesión 6](docs/sesion_6.md), [modelo](docs/modelo_analitico.md), [sensibilidad](docs/indice_rehabilitacion.md) y [seguimiento](docs/avance_nocturno.md).

```bash
# Sin dependencias nuevas; instalación y desarrollo como arriba.
PYTHONPATH=src .venv/bin/python -m madrid_rehab.analytics
# Para repetir, usar siempre salida nueva:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.analytics --output-dir data/processed/session_6_replay_02
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

La pestaña nueva permite consultar/exportar el perfil completo, incluyendo parcelas sin evidencia. No hay paso de compilación. Los productos se generan bajo `data/processed/session_6/`, sin sobrescribir sesiones anteriores. Las CLI de eventos requieren exportaciones oficiales adaptadas al contrato documentado; no descargan formularios. El plan histórico de autorización inicial queda ampliado por la misión de sesiones 4–6, manteniéndose prohibidos commits y publicación automática.

## Profundización: perfil v2, auditoría y exploración

La captura vigente pasa a **`data/processed/session_6_audited/`**, conservando todas las anteriores. La [auditoría de Chamberí](docs/auditoria_analitica_chamberi.md) reconcilia datos y documenta sesgos: 1.426 parcelas con solo 1–2 letras, 424 con ámbitos mezclados. No cambian las cifras originales. La pestaña incorpora filtros AND, ordenación, explicación individual, CSV, gráficos interactivos y comparación por malla de 500 m (no barrios). Perfil descriptivo, sin IPR global. Lectura en caché verificada; diez interacciones de benchmark no releen Parquet.

```bash
# Materializar una vez; si existe, usar siempre --output-dir nuevo:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.analytics
PYTHONPATH=src .venv/bin/python -m madrid_rehab.analytics --output-dir data/processed/session_6_audited_replay_02
# Pruebas completas y de profundización:
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_analysis_deepening.py -v
.venv/bin/ruff check src tests
# Rendimiento Python, sin navegador:
PYTHONPATH=src .venv/bin/python tests/benchmark_analysis.py
# Aplicación local; añadir MADRID_REHAB_OFFLINE=1 si se desea:
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Sin instalaciones nuevas ni paso de compilación. `MADRID_REHAB_SESSION6_DIR` permite abrir otra captura, incluida v1. Solo cuando haya eventos oficiales revisados, añadir a la CLI `--inspections-dir /ruta/captura_ite` y/o `--grants-dir /ruta/captura_ayudas`; se verifican manifiestos y misma captura CP. No hay eventos reales nuevos. Las pruebas sintéticas de integración usan directorios temporales y no entran en datasets reales. La validación de navegador permanece pendiente; AppTest no la sustituye.

## Sesión 7: Madrid capital y los 21 distritos

La entrada habitual `app.py` abre ahora la vista municipal. Productos vigentes: **`data/processed/session_7_final/`**. Las salidas de Chamberí y de sesiones anteriores se conservan. [Sesión 7 y tabla de cobertura](docs/sesion_7_expansion_madrid.md), [calidad municipal](docs/calidad_sesion_7.md) y [avance](docs/avance_sesion_7.md).

```bash
# Una sola generación municipal, con datos locales. Si la salida existe, usar otra:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.city_pipeline --city madrid --district all
# Distrito por nombre o código, conservando la auditoría global:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.city_pipeline --district chamberi --output-dir data/processed/session_7_chamberi_02
# Entrada principal municipal:
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512 --server.headless true --browser.gatherUsageStats false
# Regresión histórica del piloto, si se necesita:
MADRID_REHAB_PILOT=1 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
# Pruebas y benchmark real:
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python tests/benchmark_session7.py
```

`MADRID_REHAB_SESSION7_DIR` permite seleccionar otra captura. Anteponer `MADRID_REHAB_OFFLINE=1` para no cargar OSM. Sin dependencias ni infraestructura nuevas. La portada carga solo 21 límites y agregados; cada distrito lee su partición y dibuja una celda, con límite explícito de 2.500 CP/BU. Se mantienen fichas, filtros, perfiles, CSV protegido y comparación por periodos/mallas, sin IPR global.

La captura contiene 141.244 filas CP, **140.595 RC distintas**, 124.396 BU y 115.664 registros CEEE. Hay 113.072 registros confirmados en parcela, 113.082 pares registro/parcela y 51.860 RC con evidencia. Las 38 RC sin distrito único quedan en el residuo, no se reparten arbitrariamente. No se afirma exhaustividad del parque ni cobertura física del certificado. La validación visual municipal está pendiente por restricciones de sockets del sandbox.

## Sesiones 7.1, 8 y 9: navegación y auditoría de fuentes

El distrito abre una vista completa con zonas de 500 m seleccionables por identidad; después se carga el detalle CP/BU. Búsqueda por referencia, selector técnico secundario, regreso al distrito/municipio, filtros AND y restablecimiento. [Usabilidad y comprobación manual](docs/sesion_7_1_usabilidad.md).

**Escenario D: cero registros nuevos adquiridos o integrados.** La investigación verificó formularios ITE/IEE, catálogo/diccionario de inspecciones urbanísticas y documentación BDNS; DNS del sandbox, formatos no procesables por la herramienta web y visor PRTR 403 impidieron adquirir registros. [Inventario](docs/inventario_fuentes.md), [sesión 8 y adquisición reproducible](docs/sesion_8_fuentes_oficiales.md), [sesión 9 y cobertura distrital](docs/sesion_9_integracion.md). No hay capas ficticias ni tasas cero de fenómenos desconocidos. Validación visual del nuevo recorrido bloqueada por permisos de socket; AppTest no la sustituye.

```bash
# Sin nuevas dependencias ni compilación; instalación y suite completas como arriba.
PYTHONPATH=src .venv/bin/python -m madrid_rehab.integration_audit --output-dir reports/session_9/replay_02
PYTHONPATH=src .venv/bin/python tests/benchmark_session71.py
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session71_navigation.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_public_sources.py -v
# Fuera del sandbox con DNS; salida nueva, no reescribe originales:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.official_sources urban_2019 --raw-dir data/raw/session_8_capture_03
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```
