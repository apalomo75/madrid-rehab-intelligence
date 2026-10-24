# Avance nocturno

Inicio: 2026-10-22T22:00:53.402315+00:00

Git limpio. Línea base: 73 pruebas unittest superadas. Inventario Parquet verificado. Originales y sesiones anteriores protegidos mediante hashes en reports/session_6/input_hashes.json.

En curso: auditoría oficial ITE/IEE y ayudas; contratos independientes de acceso externo.

Pendientes prioritarios: adaptadores, análisis real por parcela, visor, validación y documentación.

## Hito 1 — auditoría y contratos

Consultadas fuentes oficiales municipales ITE/IEE, registro autonómico, PRTR y documentación OpenAPI SNPSAP. No se obtuvo exportación real de eventos. Formularios ITE accesibles por web, sin dataset verificado; visor PRTR 403, API de concesiones inaccesible por web y DNS desde Python. Intentos acotados en `reports/session_6/source_attempts.json`. Alternativa: importación canónica local con CLI, validación y matching por RC/CP, sin inventar datos. Documentos de fuentes y sesiones 4/5 completos. Resumen de concesiones evita sumar pagos y republicaciones, excluye conflictos.

## Hito 2 — análisis real y reproducción

Dataset generado en `data/processed/session_6`: 3.790 parcelas; construcción disponible 3.760; energía confirmada 2.105; ambas 2.105; ninguna 30. Fuentes de inspección/ayudas explícitamente desconocidas. Perfil A principal. Comparador B elegible en 679 parcelas; sensibilidad mediana 9,5, máxima 50 puntos; sin IPR global. Salida replay en `data/processed/session_6_replay` idéntica con comparación de DataFrames. Hashes de entrada contrastados contra sesión 2 y al terminar. Pipeline aproximadamente 4,28 s.

## Hito 3 — visor y validación

Nueva pestaña por parcela, filtros independientes, exportación y mensajes de ausencia. AppTest ejecutado con datos reales y cambio a «Sin evidencia energética», sin excepciones. Conservados mapa OSM, selección y filtros anteriores. Servidor local bloqueado por PermissionError al crear socket; Chromium falla SIGTRAP/sandbox. No hay validación visual de la ampliación ni capturas válidas nuevas. Logs en `reports/session_6`. Pytest intentado: no instalado; alternativa oficial del proyecto unittest. Sin dependencias nuevas ni instalaciones globales.

22 pruebas nuevas de contratos, matching, fechas, fases, privacidad de columnas, deduplicación, agregación, nulos, elegibilidad, sensibilidad, filtros y smoke CLI inspection/grant en directorios temporales de tests. Validación final: 95 pruebas unittest/AppTest superadas (73 previas + 22 nuevas), incluidas ambas CLI. Log: reports/session_6/unittest_final.log. Ruff y formato nuevos módulos correctos. Benchmark sesión 3 ejecutado, solo preparación Python. Ningún original ni archivo de sesiones 1/2 alterado según hashes.

## Archivos de la entrega

Nuevos: `events.py`, `analytics.py`, `analysis_view.py`, `tests/test_sessions456.py`; documentos sesiones 4/5/6, auditorías de fuentes, modelo, índice y este seguimiento. Modificados: app, README, AGENTS, arquitectura, plan y visor. Datos y reports generados ignorados por Git. Sin commits, push, contactos externos ni publicación.

## Pendientes por prioridad

1. Obtener exportación ITE/IEE reutilizable con licencia y RC/identificador, revisar esquema real y una muestra; no automatizar consultas individuales indiscriminadamente.
2. Resolver acceso PRTR/BDNS en entorno con red, verificar condiciones y filtrar programas/municipio; confirmar inmueble objeto, fases y expedientes.
3. Crear adaptadores específicos a esos esquemas e integrar eventos revisados al dataset y filtros de visor. La CLI canónica no equivale a integración real terminada.
4. Validar manualmente nueva pestaña, CSV, selección, filtros y modo offline en navegador permitido.
5. Revisar sesgos/umbrales y evidencia de conservación antes de plantear IPR. Sin modelos supervisados ni clustering pendiente prioritario.

Próxima tarea concreta: aceptación visual con el comando de README y después adquisición de exportación oficial autorizada; no requiere modificar ni regenerar datos previos.

## Cierre de ejecución

95 pruebas superadas; Ruff y diff --check correctos. Revisión de Git: solo código/documentación/tests previstos; ningún dataset ni report seguido por Git. Escaneo de patrones de secretos en código nuevo sin hallazgos. Hashes de todos los originales y sesiones 1/2 comprobados nuevamente al cierre: intactos. Ampliación lista para revisión, sin commit.

## Profundización autónoma — hito 4: auditoría y motor v2

Reconciliación real: 5.106 filas de enlace corresponden a 5.105 pares registro/parcela únicos. Los 5.105 registros tienen códigos administrativos distintos en Chamberí; 4.023 ámbito vivienda, 507 parte/local, 476 edificio completo declarado y 99 desconocidos. No se detecta multiplicación de recuentos, CP ambigua ni intervalos invertidos en este piloto. Sesgo relevante: 1.426 parcelas con 1–2 letras; 424 con ámbitos heterogéneos; máximo 44 registros por parcela observada.

Correcciones preventivas verificables: identidades BU/CEEE contradictorias ahora se rechazan; CP ambigua se cuenta globalmente aunque la segunda fila quede fuera del distrito; fechas se agregan cronológicamente; intervalos invertidos y años fuera de rango no se usan. Se conserva API parcel_features. Nuevos módulos features/profiles/analysis_audit separan lógica de presentación. Salida nueva `session_6_v2`, sin sobrescribir v1. Las 22 pruebas existentes de sesiones 4–6 se ejecutaron; se detectó y corrigió un caso vacío de Pandas al contar fechas ausentes. Auditoría v2 reconcilia universo, recuentos por parcela y letras/denominadores/nulos; ocho comprobaciones pasan. Nuevas pruebas de regresión y validación de visor en preparación.

Próxima tarea: cerrar pruebas de filtros/caché/integridad, endurecer contrato de eventos y preparar agregación opcional sin datos inventados.

## Profundización — hito 5: exploración y comparaciones

Pestaña ampliada con filtros AND de cobertura, RC literal, periodo, perfil energético, uso residencial, mínimo de registros y CP única; ordenación explícita y CSV neutralizado frente a fórmulas de hoja de cálculo. Gráficos Altair con tooltip/leyenda por ámbitos, evolución por año de certificado, dispersión año–proporción observada (zoom/arrastre), cobertura por periodo y por malla de 500 m. No se inventan barrios: 29 celdas CP; 23 cumplen mínimos de comparación (3.759 parcelas). Grupos pequeños conservan tamaños/cobertura y ocultan proporciones comparativas. Mediana por parcela y proporción agrupada por registro distinguen ponderaciones.

Perfiles reales: 1.685 sin registros, 1.426 con muestra escasa, 357 con E/F/G en ≥75% de ≥3 registros y 322 con otras distribuciones. 20 escenarios de sensibilidad: mínimos 1/3/5/10 → 2.105/679/208/30 parcelas evaluables para B; pesos 0/0,25/0,5/0,75/1. No hay IPR global.

Se corrigió incompatibilidad de API Altair/Streamlit detectada por AppTest, usando la firma instalada. 39 pruebas de profundización pasaron, incluidas tres AppTest de controles combinados, vacíos, ámbitos y malla. No representan validación visual WebGL.

## Profundización — hito 6: caché, procedencia y eventos opcionales

`analysis_store.py` verifica hashes y versiones con lectura de nombres fijos; la caché se invalida mediante tamaño/mtime/ctime del manifiesto y productos. No recalcula tablas. Benchmark real: mediana 0,156 s carga íntegra frente a 0,0037 s con caché, cero lecturas Parquet en diez llamadas; filtrado 0,024 s, CSV de 679 parcelas 0,019 s. Valores del entorno, no tiempos de navegador.

`event_features.py` permite integrar explícitamente capturas canónicas revisadas con `--inspections-dir` / `--grants-dir`, verifica manifiesto, hashes y versión CP compartida. None conserva fuente no integrada; captura vacía revisada no equivale a ausencia del fenómeno. Historiales con resultados distintos en la misma última fecha quedan ambiguos. Concesiones se concilian globalmente por expediente para no duplicar euros entre parcelas; importes/fechas/ubicaciones contradictorios se excluyen. Ningún evento real incorporado. Contrato endurecido frente a infinitos, identidades vacías, procedencia inválida y evidencia de ejecución en blanco; importe literal preservado.

43 pruebas de profundización pasaron, incluido smoke de CLI analítica con eventos opcionales exclusivamente sintéticos en directorios temporales de tests. Salida real definitiva materializada en `data/processed/session_6_current`, contrato `session6-v2`; v1 y los checkpoints v2/review permanecen intactos. App usa current por defecto; todas las rutas admiten override. Manifiesto registra parámetros, hashes de entradas/salidas y módulos de transformación principales. Validación completa y replay final en curso.

## Profundización — hito 7: revisión de multiparcela y cierre

Después de 141 pruebas completas superadas se identificó otro riesgo latente: las proporciones agrupadas sumadas desde features podían contar más de una vez un certificado multiparcela. Corregido en v2 usando observaciones deduplicadas por registro/grupo, con numerador, denominador y unidad explícitos. En v1, sin observaciones, se declara la unidad como pares registro/parcela. No cambia ningún resultado de Chamberí, donde cada registro abarca una sola parcela distinta. Se añade regresión específica; se conserva el checkpoint previo `session_6_final` y se materializa **`data/processed/session_6_audited/`** como salida vigente del visor y CLI.

Se añadió explicación individual y títulos legibles de tabla; prueba AppTest de explicación. Validación previa: 141 tests; cierre con prueba multiparcela en curso. Documentación ampliada: auditoría de Chamberí, modelo, índice, visor, arquitectura, sesiones 4/5/6, README y AGENTS. Ninguna descarga, contacto, commit o push en esta profundización.

Pendientes reales: validación visual en entorno permitido, adquisición de eventos oficiales con licencia/esquema verificados y revisión metodológica de umbrales. No se necesita autorización para pasos técnicos menores ni hay pregunta pendiente.


## Cierre de profundización — estado vigente

**142 pruebas unittest/AppTest superadas** (47 adicionales respecto a la ejecución anterior); Ruff, formato de 12 archivos y diff --check correctos. Logs completos en `reports/session_6_deepening/audited_tests.log`. Replay final en `session_6_audited_replay`: todos los Parquet, auditoría/cobertura JSON y CSV de periodos idénticos. Todas las columnas compartidas con v1 permanecen iguales; código de transformación coincide con hashes del manifiesto. Originales y sesiones 1/2 intactos. Escaneo de patrones de secretos sin hallazgos. Ningún dataset/report seguido por Git y ningún commit/push.

Medición final: CLI 8,12 s; carga verificada mediana 0,174 s frente a 0,00496 s en caché; cero lecturas Parquet en diez llamadas calientes. Filtrado de 679 parcelas 0,0077 s; CSV 0,021 s. No mide navegador. No hubo descargas ni nuevas fuentes fabricadas. Se mantiene el perfil multidimensional como principal.

Archivos de profundización: `features.py`, `profiles.py`, `analysis_audit.py`, `analysis_store.py`, `analysis_charts.py`, `event_features.py`, ampliaciones de analytics/events/analysis_view/app, `tests/test_analysis_deepening.py`, `tests/benchmark_analysis.py`; auditoría nueva y documentación existente actualizada. Los cambios de la primera ejecución siguen preparados conjuntamente para revisión.

Próxima tarea concreta manual: ejecutar `PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512`, comprobar pestaña nueva (filtros AND, orden, explicación, CSV, leyenda, zoom y malla) y continuidad del mapa/selección/OSM/offline. Después priorizar exportación oficial verificable ITE/IEE y ayudas, revisando licencia y esquema antes de usar las opciones de eventos. No queda una decisión técnica menor esperando aprobación.
