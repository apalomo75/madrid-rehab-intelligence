# Madrid Rehab Intelligence

Corrección de navegación regional: [productos, cobertura y pruebas](docs/correccion_navegacion_regional.md). La navegación regional activa los cinco pilotos con CP/BU aceptado parcial, además de Madrid; mantiene la consulta territorial de los otros 173 municipios.

**Sesión 15:** demostración local opcional con búsqueda por municipio/RC14, tres casos reales y ficha conjunta. **REC: consulta individual documentada, POST/NDP sin reproducir y cero dictámenes integrados**; no hay permiso de extracción masiva. MVP parcial y revisión visual pendiente por bloqueo de sockets/Chromium. [Resultados y validación](docs/sesion_15_rec_y_demo.md), [ejecutar y presentar](docs/demo_uci.md), [acceso REC](docs/rec_acceso_y_escala.md), [licencias](docs/licencias_demo.md). Las cifras y estados de secciones anteriores son históricos.

```bash
MADRID_REHAB_DEMO=1 MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512 --server.headless true --browser.gatherUsageStats false
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_demo.py -v
PYTHONPATH=src .venv/bin/python -m madrid_rehab.demo_audit --output-dir reports/session_15/audit_nuevo
PYTHONPATH=src .venv/bin/python tests/benchmark_session15.py --output reports/session_15/benchmark_nuevo.json
```

Sin dependencias nuevas ni compilación. Instalación: `.venv/bin/python -m pip install -r requirements.lock`; suite y Ruff como abajo. `MADRID_REHAB_PUBLIC=1` mantiene protecciones y limita la demo a identificación. No publicar ni redistribuir evidencias pendientes de licencia. El exportador nuevo produce HTML reducido, sin PRTR/REC ni otras evidencias. [Revisión visual y prueba de navegador](docs/auditoria_visual_pendiente.md).

**Resultado vigente de sesión 13:** 236.134 contenidos CEEE canónicos regionales, 179 municipios con observaciones verificadas y 136.742 contenidos vinculados a CP aceptadas de Madrid y cinco pilotos parciales. Panel energético regional y fichas con evidencia separada de PRTR. [Resultados, límites y reproducción](docs/sesion_13_energia_regional.md). Las secciones de sesiones anteriores conservan sus estados históricos; los recursos reales del piloto 12.2 ya están disponibles localmente.

Resultado histórico: **sesión 12.1, 179 municipios oficiales con límites validados y 7.532 concesiones PRTR territorializadas**: 3.808 Madrid capital y 3.724 en otros 116 municipios; 315.527.338,99 € reconciliados. CP/BU integrado únicamente en Madrid. [Resultados, fuentes, conflictos y reproducción](docs/sesion_12_1_limites_prtr.md). Sin publicación; licencias de redistribución pendientes y validación visual bloqueada por permisos de socket. Las secciones de sesiones anteriores conservan su estado histórico.

**Sesión 12.2: 332 pruebas superadas y una omitida por ausencia de los recursos reales; Ruff correcto.** Piloto Getafe/Móstoles/Leganés/Alcorcón/Alcalá preparado; los diez GET fallan por DNS en el sandbox, sin CP/BU externo incorporado. Descarga reanudable e integración desde Ubuntu con un comando: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_pilot`. [Resultados, manifiesto, límites y reproducción](docs/sesion_12_2_piloto_catastral.md). Madrid y la clasificación 12.1 permanecen intactos.

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

## Sesión 10: archivos administrativos reales

Se integran los archivos locales de `Mapas Rehab`: 98.032 declaraciones, 11.498 licencias, 3.935 órdenes y 10.710 obligaciones ITE/IEE únicas según consulta 24/10/2026. Total: **124.175 eventos**, **112.783 vinculados inequívocamente a 49.855 parcelas**. El único PDF de subvenciones es una convocatoria, sin concesiones individuales. [Inventario, cobertura y ejecución](docs/sesion_10_integracion_administrativa.md), [puente NDP](docs/auditoria_matching_callejero.md), [diccionario](docs/diccionario_eventos_administrativos.md) y [calidad](docs/calidad_eventos_rehabilitacion.md).

La captura administrativa vigente es `data/processed/administrative_events/session_10_final_01/`; la aplicación añade «Actividad y rehabilitación», filtros, series, exportación segura, capas de celda y eventos asociados a CP/BU. La evidencia sigue siendo de parcela; no diagnostica edificios ni acredita obras ejecutadas. `MADRID_REHAB_ADMIN_DIR` permite otra captura compatible con el mismo CP. No se regeneran productos anteriores.

```bash
# Python: dependencias ya incluidas en requirements.lock.
.venv/bin/python -m pip install -r requirements.lock
# Requisito PDF del sistema, si falta: sudo apt-get install poppler-utils
# Cada reproducción requiere directorios nuevos:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.administrative --output-dir data/processed/administrative_events/replay_nuevo --report-dir reports/session_10/replay_nuevo
PYTHONPATH=src .venv/bin/python -m madrid_rehab.administrative_audit --output-dir data/processed/administrative_profiles/replay_nuevo --report-dir reports/session_10/audit_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_administrative.py -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python tests/benchmark_administrative.py --output reports/session_10/benchmark_nuevo.json
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Sin compilación ni dependencias Python nuevas. Los originales quedan copiados por SHA-256; no se ejecutan fórmulas ni macros. Los datos e informes voluminosos están ignorados. La validación visual permanece bloqueada por permisos del socket; AppTest no sustituye WebGL/clic real. Véase [avance y resultados finales](docs/avance_sesion_10.md).

## Sesión 11: subvenciones PRTR reales y base regional

7.532 concesiones reales conservadas localmente; entidad especializada con importes por expediente y relaciones catastrales sin doble conteo. Nueva pestaña «Subvenciones PRTR» en Madrid/distritos y navegación «Comunidad de Madrid — Subvenciones». [Resultados](docs/sesion_11_subvenciones_prtr.md), [calidad](docs/calidad_subvenciones_prtr.md), [arquitectura regional](docs/arquitectura_regional.md), [licencia](docs/licencia_datos_prtr.md) y [validación manual](docs/avance_sesion_11.md). Catálogo/límites de los 179 municipios pendientes por bloqueo DNS; CP/BU sigue siendo solo Madrid. Sin publicación ni derechos de redistribución inferidos.

```bash
# Instalación sin dependencias nuevas:
.venv/bin/python -m pip install -r requirements.lock
# Captura vigente ya generada; para repetir, salida nueva obligatoria:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.grants --output-dir data/processed/grants/replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_grants.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python tests/benchmark_grants.py --output reports/session_11/benchmark_nuevo.json
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

`MADRID_REHAB_GRANTS_DIR` selecciona captura PRTR con el mismo CP. `MADRID_REHAB_PUBLIC=1` desactiva exposición PRTR por licencia no verificada. No hay paso de build. Las afirmaciones anteriores sobre ausencia de concesiones describen sesiones históricas; la sesión 11 incorpora la nueva fuente PRTR sin sustituir la base administrativa de sesión 10.

## Sesión 12: arquitectura regional y cobertura parcial

**Inventario oficial de 179 recursos municipales Catastro; catálogo INE completo, límites y piloto externo pendientes por DNS.** Continúan procesados únicamente Madrid capital (CP/BU) y sus 21 distritos. Se preservan los 7.532 PRTR y 315.527.338,99 €; 3.805 expedientes siguen confirmados en Madrid y 3.727 pendientes. No se declara clasificación espacial regional ni ampliación catastral conseguida.

Componentes nuevos: inventario y cobertura por recurso, importador de límites oficiales/catálogo revisado, pipeline CP/BU municipal con checkpoints, cruce PRTR regional independiente, navegación por 179 recursos y estados de disponibilidad. El visor no presenta municipios sin CP como si tuvieran ficha catastral. Las ramas externas se han probado con fixtures sintéticas; no sustituyen el piloto real. Sin nuevas dependencias, compilación ni servidores.

```bash
# Reproducción: cada producto/informe exige una ruta nueva.
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_cadastre --inventory-output data/processed/territory/replay_new
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_grants --output-dir data/processed/grants/regional/replay_new
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_audit --output-dir reports/session_12/audit_new
PYTHONPATH=src .venv/bin/python tests/benchmark_regional.py --output reports/session_12/benchmark_new.json
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_regional_expansion.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Instalación: `.venv/bin/python -m pip install -r requirements.lock`. Productos vigentes en `data/processed/territory/session_12_final_01/` y `data/processed/grants/regional/session_12_final_01/`. Overrides de vista: `MADRID_REHAB_TERRITORY_INVENTORY_DIR`, `MADRID_REHAB_REGIONAL_GRANTS_DIR`; `MADRID_REHAB_TERRITORY_DIR` para límites validados y `MADRID_REHAB_CADASTRE_DIR` para particiones municipales nuevas. Estos dos últimos productos **no se han generado con datos externos reales**. `MADRID_REHAB_PUBLIC=1` sigue desactivando PRTR. El servidor local y la validación en navegador están bloqueados en este entorno por permisos de socket.

[Entrega y reproducción](docs/sesion_12_expansion_regional.md), [límites](docs/calidad_limites_municipales.md), [pipeline catastral](docs/catastro_regional.md), [cobertura](docs/cobertura_municipal.md) y [avance y comprobación manual](docs/avance_sesion_12.md). No commits ni push.

## Sesión 12.1: clasificación PRTR con GeoPackage IDEM

No requiere paquetes nuevos ni descargas. Fuente local: `data/raw/territory/madrid/unidades_administrativas.gpkg`.

```bash
# Elegir directorios nuevos en cada ejecución:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.municipal_boundaries --output-dir data/processed/territory/replay_121_new
PYTHONPATH=src .venv/bin/python -m madrid_rehab.territorial_prtr --boundaries-dir data/processed/territory/replay_121_new --output-dir data/processed/grants/regional/replay_121_new
PYTHONPATH=src .venv/bin/python -m madrid_rehab.territorial_report --boundaries-dir data/processed/territory/replay_121_new --classification-dir data/processed/grants/regional/replay_121_new --output-dir reports/session_12_1/replay_new
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_territorial_prtr.py -v
.venv/bin/ruff check src tests
```

El visor regional usa por defecto `territory/session_12_1_final_01` y `grants/regional/session_12_1_final_02`, ambos bajo `data/processed/`. Variables de selección y metodología en la [documentación de sesión 12.1](docs/sesion_12_1_limites_prtr.md). El modo público sigue sin exponer PRTR. Las dos comunidades jurisdiccionales no se atribuyen a un municipio único.

## Piloto CP/BU de sesión 12.2

```bash
# Ubuntu, desde la raíz: descarga, valida, integra y cruza; reanudable.
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_pilot
# Solo descarga; biblioteca estándar, sin instalaciones nuevas:
PYTHONPATH=src python3 -m madrid_rehab.cadastre_download
# Pruebas específicas y suite completa:
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_cadastre_pilot.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
```

Código 2 indica cobertura pendiente; no una descarga completada. Las fuentes se conservan bajo `data/raw/cadastre/session_12_2_capture_01`, las particiones bajo `data/processed/cadastre/session_12_2_pilot_01` y cada ejecución genera un snapshot regional nuevo. La activación del visor ocurre solo con incorporación de particiones; mientras falten archivos sigue el estado anterior. Ver [sesión 12.2](docs/sesion_12_2_piloto_catastral.md) para informes, overrides y replay offline.

Ingesta parcial explícita del piloto 12.2, reutilizando la última evidencia real y sin
red: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.partial_cadastre --output-dir data/processed/cadastre/replay_partial_new`.
Usar siempre una salida nueva. Conserva XML exacto por registro, vistas aceptadas y
cuarentena; declara cobertura parcial y no activa el visor. Pruebas específicas:
`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_partial_cadastre.py -v`.
Ver [criterios y trazabilidad](docs/sesion_12_2_ingesta_parcial.md).

## Sesión 13: evidencia energética regional

Dos fuentes locales, 236.173 apariciones y 236.134 contenidos canónicos; observaciones verificadas en los 179 municipios. 136.742 contenidos con parcela confirmada en Madrid y cinco pilotos; 3.440 parcelas con evidencia CEEE y PRTR. Sin BU o series físicas temporales confirmadas. No es un censo ni una calificación del edificio. [Resultados y comandos](docs/sesion_13_energia_regional.md), [auditoría](docs/calidad_energia_regional.md).

```bash
# Sin nuevas dependencias; salidas nuevas siempre.
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_energy --output-dir data/processed/energy/replay_nuevo
PYTHONPATH=src .venv/bin/python -m madrid_rehab.energy_audit --energy-dir data/processed/energy/replay_nuevo --output-dir reports/session_13/audit_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_regional_energy.py -v
```

Visor: `MADRID_REHAB_ENERGY_DIR` (por defecto `data/processed/energy/session_13_final_03/`). La información nueva está protegida en modo público. Licencia CEEE declarada CC BY 4.0 en el catálogo local; PRTR pendiente, sin publicación. Se conservan snapshots anteriores y sus reglas históricas.

## Sesión 14: conservación e inspecciones

Capa offline con **14.645 órdenes/obligaciones en 9.036 parcelas**, reutilizando los 124.175 eventos municipales. No se han integrado actas REC: las obligaciones de presentación y las menciones indirectas desfavorables no se cuentan como dictámenes. El contraste de COD_NDP 11140360 coincide con la dirección indicada, pero no confirma CP. Sin recolector masivo ni publicación. [Resultados y límites](docs/sesion_14_conservacion_ite_iee.md), [fuentes y permisos](docs/fuentes_conservacion_madrid.md), [modelo](docs/modelo_conservacion.md).

No hay nuevas dependencias. Instalación y app conservan los comandos anteriores. Productos por defecto: `data/processed/conservation/session_14_final_02/`; el visor admite `MADRID_REHAB_CONSERVATION_DIR`. La nueva sección está oculta en modo público. Cada reproducción requiere directorio nuevo:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.conservation --output-dir data/processed/conservation/replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_conservation.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_conservation.py --output reports/session_14/benchmark_nuevo.json
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src/madrid_rehab/conservation.py src/madrid_rehab/conservation_view.py src/madrid_rehab/rec.py src/madrid_rehab/administrative_view.py tests/test_conservation.py tests/benchmark_conservation.py
```

La entrada habitual ofrece ahora el [explorador y ficha compartidos de los seis municipios](docs/navegacion_municipal_compartida.md), con zonas y páginas acotadas. La vista histórica por distritos de Madrid continúa en la barra lateral.

Diagnóstico y corrección de la navegación por un solo mapa, contrato de eventos y
validación pendiente en navegador: [auditoría municipal](docs/diagnostico_navegacion_municipal.md).

Sesión 19: fichas constructivas de los cinco pilotos, navegación CP–BU y API de
ficha independiente del mapa. Contratos, fuentes postales, ejemplos y validación:
[Integración Catastro enriquecido](docs/sesion_19_integracion_catastro_enriquecido.md).
Pruebas: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session19_integration.py -v`.
Benchmark: `PYTHONPATH=src .venv/bin/python tests/benchmark_session19_reader.py`.

## Sesión 20: búsqueda comercial por dirección

La entrada normal abre **Buscar por dirección**: municipio → calle/número → Buscar (o Enter) → selección expresa → ficha sin mapa. Madrid tiene 214.083 versiones postales indexadas, 206.982 con parcela confirmada. Los cinco pilotos conservan el explorador y las fichas enriquecidas, pero sus URL AD locales no contienen calle/número: no tienen cobertura postal acreditada. [Arquitectura, cobertura, límites y uso](docs/sesion_20_buscador_comercial.md).

Sin dependencias nuevas. Índice SQLite local, sin geometrías y con huellas de fuentes; no reconstruye Catastro ni descarga fuentes. Primera generación (ambos directorios deben ser nuevos):

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.address_search
# Replay: siempre salidas nuevas; para utilizarlo, MADRID_REHAB_ADDRESS_DIR apunta al nuevo índice.
PYTHONPATH=src .venv/bin/python -m madrid_rehab.address_search --output-dir data/processed/addresses/replay_nuevo --report-dir reports/session_20_address_search/replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_address_search.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_address_search.py --output reports/session_20_address_search/benchmark_nuevo.json
# Comprobar primero si 8512 está ocupado; reutilizar el servidor existente si corresponde.
ss -ltn 'sport = :8512'
MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_address_search.py --output-dir reports/session_20_address_search/browser_nuevo
```

Se mantienen instalación, suite completa y Ruff documentados arriba. Formato: `.venv/bin/ruff format --check src/madrid_rehab/address_search.py src/madrid_rehab/address_view.py tests/test_address_search.py tests/benchmark_address_search.py tests/browser_address_search.py`; integridad del diff: `git diff --check`. No hay paso de compilación. La prueba visual requiere Chromium disponible; no confundir AppTest con validación visual. No commits/push/publicación.

### Sesión 21: ficha comercial

La ficha compartida muestra primero la dirección, características por objeto, CEEE con
ámbito, concesiones PRTR y antecedentes administrativos, seguidos de comprobaciones
basadas en evidencia. Las seis secciones anteriores permanecen en «Detalles técnicos».
No hay diagnósticos, puntuaciones ni consultas REC automáticas. Sin dependencias nuevas.

```bash
MADRID_REHAB_DEMO=0 MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_commercial_fiche.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_commercial_fiche.py --output reports/session_21_commercial_fiche/replay_nuevo.json
```

Arquitectura, matriz de fuentes, seis casos reales, límites y validación:
[Sesión 21](docs/sesion_21_ficha_comercial.md). La revisión de navegador está bloqueada
por falta de Chromium; las pruebas AppTest no constituyen validación visual.

### Sesión 22: auditoría y recuperación offline

El producto lateral `data/processed/cadastre/session_22_madrid_01/` recupera superficie bruta, condición y unidades de los Building Madrid ya aceptados. La ficha conserva el objeto de origen y añade magnitudes/dirección de cada certificado y el acceso de cada antecedente. No integra BuildingPart Madrid nuevos ni cambia vínculos documentales.

Resultados, denominadores y trazabilidad: [auditoría de sesión 22](docs/sesion_22_auditoria_recuperacion_datos.md). No hay dependencias ni build nuevos. Instalación: `.venv/bin/python -m pip install -r requirements.lock`. Desarrollo: servidor Streamlit habitual; no se requiere ejecutar GML al abrir fichas.

```bash
# Solo si hace falta un replay; siempre salida nueva, sin activación automática
PYTHONPATH=src .venv/bin/python -m madrid_rehab.madrid_recovery --output-dir data/processed/cadastre/replay_22_nuevo
mkdir -p reports/session_22_data_recovery/replay_nuevo
PYTHONPATH=src .venv/bin/python -m madrid_rehab.data_recovery_audit --output reports/session_22_data_recovery/replay_nuevo/baseline_coverage.json
PYTHONPATH=src .venv/bin/python -m madrid_rehab.data_recovery_audit --final --output reports/session_22_data_recovery/replay_nuevo/final_coverage.json
PYTHONPATH=src .venv/bin/python tests/audit_data_recovery_sources.py --cases-only --output-dir reports/session_22_data_recovery/cases_replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_data_recovery.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
```

La auditoría completa de fuentes, si se necesita reproducirla en otra salida, usa `tests/audit_data_recovery_sources.py --output-dir reports/session_22_data_recovery/sources_replay_nuevo` con el mismo prefijo Python. El benchmark usa `tests/benchmark_commercial_fiche.py --output reports/session_22_data_recovery/benchmark_nuevo.json`. No confundir la mejora de profundidad con reducción de fichas vacías; las fuentes de inspección no integradas no equivalen a cero inspecciones.

### Sesión 23: Plan Rehabilita municipal y prototipo catastral

Consulta local separada de PRTR en la ficha y en **Plan Rehabilita · Ayuntamiento de Madrid**. Snapshot `data/processed/plan_rehabilita/session_23_01/`: 2.085 expedientes; vínculos A/B/C basados en el índice postal oficial, sin confirmación por proximidad. Los importes son por expediente; no sumar capas ni parcelas. La licencia del ZIP no está acreditada: datos ocultos en modo público.

[Informe y límites](docs/sesion_23_plan_rehabilita_catastro.md). Sin dependencias ni build nuevos. Instalación: `.venv/bin/python -m pip install -r requirements.lock`; desarrollo: servidor Streamlit habitual. No se hace red al abrir la aplicación.

```bash
# Importación local reproducible; salida e informe nuevos siempre
PYTHONPATH=src .venv/bin/python -m madrid_rehab.plan_rehabilita --input /ruta/PLAN_REHABILITA.zip --output-dir data/processed/plan_rehabilita/replay_nuevo --report-dir reports/session_23_plan_rehabilita/replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_plan_rehabilita.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_plan_rehabilita.py --output reports/session_23_plan_rehabilita/benchmark_nuevo.json
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
```

Override local: `MADRID_REHAB_REHABILITA_DIR`, únicamente productos validados con los mismos hashes CP/postal. El cliente `cadastral_service_probe` es investigación aislada: muestra máxima de cuatro entradas/seis peticiones por invocación, nueva salida, sin activación en el visor ni recuperación masiva. No repetir consultas ya capturadas; el informe documenta las ocho peticiones efectivamente realizadas en S23 y los datos de suelo/RC20 que no son atributos de Building.

### Sesión 24: catálogo comercial de seis municipios

La entrada normal **Mapa comercial** filtra CP con información útil en Madrid, Getafe, Móstoles, Leganés, Alcorcón y Alcalá de Henares. **Buscar por dirección** usa el catálogo filtrado únicamente en Madrid. La búsqueda completa sigue en **Consulta técnica · direcciones**; **Explorar municipios** conserva el explorador técnico CP/BU. No se borran fuentes ni registros excluidos.

Catálogo local: 153.929 CP; Madrid: 178.243 versiones postales incluidas, 35.840 excluidas. **Catálogo público cerrado (0 CP)** por las restricciones heredadas, pendientes de revisión por fuente/campo; no es una versión lista para publicar. [Reglas, cifras y límites](docs/sesion_24_catalogo_comercial.md).

Sin dependencias/build nuevos; instalación y servidor local habituales.

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.commercial_catalog --output-dir data/processed/commercial_catalog/replay_nuevo --report-dir reports/session_24_commercial_catalog/replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_commercial_catalog.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_commercial_catalog.py --output reports/session_24_commercial_catalog/review_nuevo.json
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
```

Snapshot `data/processed/commercial_catalog/session_24_01/`; override `MADRID_REHAB_CATALOG_DIR` exige entradas compatibles. Generar siempre en nuevos directorios. El índice se prepara offline; Streamlit no reconstruye el catálogo ni carga GML. Máximo 500 geometrías por página, una por CP, sin simplificación de la geometría comercial. Ningún municipio adicional ni buscador postal piloto.

**Actualización de preparación pública:** por instrucción del propietario, `MADRID_REHAB_PUBLIC=1` usa ahora el mismo catálogo comercial validado que el modo local (153.929 CP; Madrid 178.243 versiones postales). Producto derivado nuevo `data/processed/commercial_catalog/session_24_public_02/`; el snapshot `session_24_01` permanece intacto. Se muestran atribuciones por fuente, se conservan los ámbitos y no se modifican las exclusiones de calidad. CEEE declara CC BY 4.0; PRTR y Plan Rehabilita mantienen licencia/procedencia sin verificar, por lo que el proyecto queda preparado para revisión visual pero no desplegado ni redistribuido. [Detalle y condiciones](docs/preparacion_catalogo_publico.md).
