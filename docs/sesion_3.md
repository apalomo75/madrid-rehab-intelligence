# Sesión 3 · evolución del visor

22/10/2026. **Implementación entregada con aceptación visual pendiente por restricciones del entorno.** No se consideran cumplidos aún los criterios de clic fiable comprobado, alineación visual, rendimiento en navegador y capturas.

## Preparación

Se revisaron AGENTS, README, sesiones 1/2, arquitectura, contratos de integración, código de la aplicación/mapa/integración y pruebas unitarias/AppTest/navegador. Rama inicial `main`; único elemento previo sin seguimiento: `reports/`. Referencia: **63 pruebas superadas**, registrada en `reports/session_3/baseline_tests.log`.

Se registraron SHA-256 de 39 archivos de originales y resultados bajo las rutas de sesiones 1/2 antes de trabajar. No se ejecutó ingesta ni integración, no se generaron datos auxiliares ni se sobrescribieron resultados. No hubo commits, publicación o despliegue.

## Implementación

- Mapa: PolygonLayer con selección nativa de Streamlit activada, ID BU en cada miembro, validación contra IDs visibles y contorno azul del agregado completo. Estado propio para conservar ficha al navegar, botón de limpieza e invalidación de eventos al cambiar filtros.
- Contexto: fondo raster urbano OpenStreetMap con atribución, calles y nombres; alternativa sin recursos externos desde el interruptor o `MADRID_REHAB_OFFLINE=1`. Límite distrital diferenciado.
- Ficha: referencia de parcela, BU, distrito/uso, intervalo constructivo con semántica, cantidades declaradas, número de BU relacionados, advertencias de ambigüedad/cobertura, distribución A–G, todos los registros de la parcela, ámbitos originales, identificadores, fechas, métricas energéticas y fuentes. Dirección declarada no disponible.
- Modos separados: disponibilidad y exploración energética con letra, ámbito, año de fecha declarada, nivel y estado. Certificados deduplicados por registro antes de contar. Ausencia en captura diferenciada de filtros que excluyen información existente.
- Interfaz en tres pestañas, mapa junto a ficha, indicadores compactos, búsqueda alternativa, mensajes vacíos, JSON reservado al apartado técnico.
- Análisis de registros piloto por letra, ámbito y fecha; cobertura condicionada del piloto diferenciada de cobertura municipal. Metodología incorpora auditoría y comparación distrital.

Ningún color asigna letra al BU. Los certificados de vivienda/local y el ámbito declarado de edificio completo no acreditan cobertura física. Varios miembros poligonales no se cuentan como edificios independientes.

## Problemas y decisiones

El código anterior tenía `on_select="ignore"`. La prueba histórica de navegador solo abría el desplegable. Se investigó la API y el código instalado de Streamlit 1.50; se implementó selección por identidad en PolygonLayer. Folium/streamlit-folium se evaluó como alternativa; la instalación no pudo acceder al índice por DNS. No hay nuevas dependencias ni cambios en locks.

El servidor falla al crear el socket local (`PermissionError: Operation not permitted`); Chromium falla en `sandbox_host_linux.cc` también con `--no-sandbox`. Son bloqueos anteriores al renderizado de la aplicación. Se conservan `server_attempt.log`, `browser_attempt.log` y `browser_validation.json`. No se solicitaron permisos ni se fabricaron capturas. Tampoco se declara demostrada la robustez del clic por haber pasado AppTest.

## Validación y límites

**73 pruebas unitarias/AppTest superadas** y Ruff sin incidencias. Nuevas comprobaciones: identidad del evento frente a índices y eventos obsoletos, anillos interiores/multipolígonos, invariancia de cámara, selección persistente/limpieza/exclusión, ficha con múltiples certificados, varios BU sin multiplicar registros, vivienda frente a edificio completo, fechas y estilo sin fuentes remotas. La prueba histórica de sesión 2 permanece como evidencia del visor anterior; el script vigente es `tests/browser_session3.py`.

La prueba Playwright nueva hace clic de ratón en puntos interiores de geometrías reales, exige ficha del ID correcto, navegación, limpieza, elemento sin certificados, modo local con red exterior bloqueada y exclusión por filtros. **Escrita, intentada y bloqueada; no superada.** Tampoco se verificó la entrega real de teselas. Al ejecutarse correctamente producirá `mapa_urbano.png`, `ficha_seleccionada.png`, `mapa_sin_conexion.png` y latencias; actualmente no hay capturas nuevas.

Medición Python real en `performance.json`: carga aproximada 0,30 s; filtrado 0,37–0,38 s; preparación/serialización 0,27–0,82 s, para 3.311/3.761 BU y 3.492/4.174 miembros poligonales. JSON 8,2–9,6 MB. No mide GPU ni fluidez. Los tiempos son observaciones del entorno, sin umbral universal.

Pendientes: ejecutar la aceptación en un entorno que permita servidor y Chromium, inspeccionar capturas/alineación/contraste y comprobar continuidad de navegación. Si el picking falla, corregirlo o migrar componente; no considerar la sesión aceptada hasta entonces. Los cambios de filtro o limpieza explícita restablecen la vista inicial; la navegación ordinaria conserva el componente. El servicio de teselas requiere internet y no garantiza disponibilidad.

## Entrega y ejecución

Código modificado: `app.py`, `map_view.py`. Pruebas: `test_app.py`, `test_session3.py`, `browser_session3.py`, `benchmark_session3.py`. Documentos: README, AGENTS, arquitectura, integración, esta sesión, `visor.md` y `componente_cartografico.md`. Evidencias nuevas exclusivamente en `reports/session_3/`, incluidos hashes y comprobación final de integridad.

```bash
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512 --server.headless true \
  --browser.gatherUsageStats false
```

Abrir http://127.0.0.1:8512. Instalación, pruebas y modo sin conexión: [guía del visor](visor.md). Justificación, alternativas y licencias: [decisión cartográfica](componente_cartografico.md).
