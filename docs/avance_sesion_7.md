# Sesión 7 — avance

Inicio UTC: 2026-10-22T22:30:58.647830+00:00

Estado inicial: cambios de sesiones 4–6 sin commit conservados. Suite 142 pruebas en ejecución; hashes de originales/sesiones 1/2/6 auditada guardados. Inspección local de cobertura municipal y límites, sin nuevas descargas.

Fases pendientes: A auditoría; B límites; C/D pipeline y análisis; E productos selectivos; F/G visor y comparación; H regresión, benchmarks y documentación.

## Fases A/B — auditadas

Suite inicial: 142 pruebas superadas, log baseline.log. Datos locales verificados por SHA-256: CP 141.244 filas/140.595 RC, BU 124.396, CEEE 115.664. Paquetes Catastro municipales 28900/INE 28079; CRS EPSG:25830. CEEE procede de filtro literal normalizado MADRID; no se infiere cobertura del parque completo. 216 RC repetidas, 23 con varios distritos; 15 filas CP y cuatro BU sin distrito; una geometría BU no utilizable. 105 CP y diez BU cruzan límites. Catálogo oficial de distritos verificado vía web, licencia CC BY 4.0. Captura local de 21 geometrías válidas sin solapamientos reutilizada; sin descarga nueva. Asignación espacial recalculada contra límites y concordante con sesión 2.

14 pruebas nuevas de territorio/agregación superadas (21 códigos, geometrías/CRS/solapamientos, referencias fronterizas o sin distrito, múltiples CP, multiparcela, estados y denominadores). 22 pruebas previas de sesiones 4–6 también superadas.

## Fases C/D/E — primera generación real

CLI funcional `python -m madrid_rehab.city_pipeline --city madrid --district all`; acepta código/nombre y chamberi sin acentos. Motor único, una agregación municipal y particiones distritales; no 21 pipelines copiados. 140.595 referencias, 51.860 con energía, 113.072 registros confirmados y 113.082 pares registro/parcela. 38 referencias residuales, incluidas 23 con conflicto territorial, no se fuerzan a ningún distrito. Totales reconciliados. Chamberí compara todas las columnas históricas compartidas y registros CEEE, sin cambios. Generados 21 perfiles, escenarios y copias visuales por distrito; ningún evento ficticio.

La vista municipal leerá solo 21 límites y agregados. El detalle carga una partición y dibuja una celda de 500 m con tope explícito de 2.500 unidades CP/BU, búsqueda para recorrer el distrito y sin reinterpretar celdas como barrios. Preparadores vectorizados mantienen originales y copias simplificadas con control de área 1%. Interfaces de lectura con hashes/caché ya implementadas; visor municipal en conexión y pruebas.

## Fases F/G — visor conectado y probado

Entrada municipal implementada con lectura de dos Parquet pequeños (21 límites y resumen); ninguna geometría CP/BU se lee en portada. Selector de 21 distritos y selección por identidad en mapa, regreso a municipio y limpieza de selección al cambiar distrito. Detalle CP/BU, búsquedas en distrito completo, filtros por ámbito/letra/año/nivel/estado, residencial y unidades sin información; mapa por celda (no barrio), ficha y exportaciones. Se mantienen perfiles/filtros/explicaciones/gráficos de sesión 6, con controles separados por distrito y gráfico agregado para más de 5.000 puntos.

14 pruebas del visor municipal pasaron (AppTest de rutas/filtros y pruebas de lectura/caché/seguridad). Suite completa de checkpoint: 170 pruebas superadas. Las 142 previas conservan sus aserciones; dos helpers AppTest ahora invocan explícitamente main del piloto para distinguir regresión histórica de la portada municipal. `app.py` abre Madrid por defecto; `MADRID_REHAB_PILOT=1` conserva el modo histórico. AppTest del acceso principal municipal y siete pruebas históricas del piloto superados tras el cambio.

Se detectó y corrigió la extensión territorial de eventos con tablas CP antiguas sin distrito (no se inventa distrito). Se añadió municipio/distrito verificado separado del literal declarado: candidato nunca obtiene parcela o distrito verificados. La prueba de filtro físico se corrigió para excluir explícitamente unidades sin CEEE antes de esperar cero unidades, conservando la semántica del control.

Benchmark real preliminar de 21 distritos: portada 0,021 s sin caché y 0,00049 s con caché, sin relecturas calientes; JSON municipal 251.181 bytes. Lecturas distritales verificadas 0,036–0,108 s; filtrado 0,028–0,167 s. JSON de celdas por defecto 0,72–2,44 MB, frente a 8,2–9,6 MB del mapa completo piloto anterior (cohortes distintas, no comparación de velocidad equivalente). Memoria máxima del benchmark 569 MiB. Son tiempos Python, no navegador.

Salida de aceptación en generación: `data/processed/session_7_final/`, con descomposición explícita de los dos certificados confirmados sin distrito y agregados de ámbito. Checkpoints previos se conservan. Pendientes de cierre: AppTest de los 21 distritos y selección positiva CP/BU, replay completo, CLI chamberi, benchmarks finales y documentación.

## Fase H — evidencias de aceptación en cierre

Salida final generada en `session_7_final`, sin sobrescribir checkpoints ni sesiones anteriores. Generación real: 41,58 s de procesamiento/auditoría municipal, 0,64–2,31 s por producto distrital y 67,46 s total; RSS pico 1.335,5 MiB. La variación frente al primer benchmark responde a caché del sistema y carga: no se presenta como optimización aislada.

El servidor de sesión 7 fue intentado y está bloqueado por `PermissionError` al crear socket; log `server_attempt.log`. No se reintentó Chromium ni se fabricaron capturas. AppTest recorrió los 21 distritos y probó selección positiva CP/BU, ida/vuelta al municipio, filtros y CSV; suite anterior al último test de cobertura desconocida: 173 pruebas superadas. Se agregó caso de cobertura desconocida (no relabelarla cero) y se está ejecutando la suite final.

Replay completo y CLI chamberi ejecutados. Comparación binaria en curso de todos los artefactos deterministas, partición 07 frente a CLI individual y 47 columnas históricas. Se documentan ámbitos y letras no interpretables para no ocultar los 20 registros sin A–G. Documentación actualizada: sesión 7 (tabla 21 distritos), calidad municipal, visor, arquitectura, fuentes, modelo, README y AGENTS.

## Cierre de sesión 7 — fase H completada en backend

**174 pruebas unittest/AppTest superadas** (142 anteriores conservadas y 32 nuevas), incluyendo recorrido de los 21 distritos, selección positiva CP/BU, vuelta al municipio, vacíos, filtros combinados y cachés. Log final: `reports/session_7/acceptance_tests.log`. Ruff correcto, formato de 18 archivos comprobado y `git diff --check` sin incidencias.

Replay: **261 archivos deterministas idénticos byte a byte**, incluidos los manifiestos distritales. Se excluyen benchmark y manifiesto municipal que incorpora su hash temporal. La CLI independiente `--district chamberi` coincide íntegra con la partición municipal 07. Las 47 columnas compartidas de sesión 6, los 5.105 registros y los 3.761 BU permanecen. Código principal coincide con hashes del manifiesto; originales y sesiones 1/2/6 auditada intactos. Evidencia en `verification.json`. Escaneo de patrones de secretos en código/tests/docs sin hallazgos; ningún dataset/report seguido por Git. No se realizaron commits, push ni publicación.

Medición final sin generación concurrente: portada inicial 0,033 s; caché municipal 0,00088 s; carga inicial distrital 0,030–0,154 s, lectura caliente 0,015–0,104 s; filtros 0,026–0,181 s; serialización de celda 0,014–0,061 s. JSON municipal 251.181 bytes; celdas por defecto 0,72–2,44 MB (434–1.712 unidades, bajo el tope). Ninguna relectura Parquet en llamadas calientes verificadas. RSS máxima del benchmark del visor 562,7 MiB; frames distritales aproximados 9,4–42,3 MiB. No son mediciones de navegador ni garantías de concurrencia.

Criterios: portada/21 distritos, datos reales, navegación jerárquica, perfiles/filtros/exportación, regresión, reconciliación, tests y reproducción implementados y comprobados en Python/AppTest. **Clic y renderizado real (parte visual del criterio 4) y ausencia de bloqueo/fluidez de navegador (criterio 6) siguen sin verificar** por el sandbox. Los límites de carga/serialización sí están medidos. No se presenta esta limitación como fallo del producto ni como éxito visual.

## Archivos y próxima acción

Nuevos módulos: city_pipeline, city_audit, territory, city_store, city_maps, district_view y city_app. Se amplían features (ámbito all), events (territorio evidenciado), map_view (filtro reutilizable), app (entrada municipal/piloto explícito), analysis_view (estado por distrito) y analysis_charts (grandes conjuntos agregados). Pruebas nuevas: test_city_pipeline, test_city_view y benchmark_session7. Dos helpers de pruebas previas apuntan explícitamente al piloto, sin eliminar aserciones. Documentación: sesión 7, calidad, avance, README, AGENTS, fuentes, modelo, visor y arquitectura. Cambios sin commit de sesiones anteriores preservados.

Próxima acción manual concreta:
`PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512 --server.headless true --browser.gatherUsageStats false`

Verificar portada y clic distrital; elegir Chamberí y otro distrito; cambiar celda y buscar una referencia; seleccionar CP y BU; comprobar ficha, filtros, CSV, gráficos, regreso al municipio y offline. Revisar cámara/contraste y fluidez. No hay decisión técnica ordinaria esperando aprobación. Adquisición oficial ITE/IEE/subvenciones y barrios queda fuera de esta expansión, con contratos y procedencia preparados para revisión futura.
