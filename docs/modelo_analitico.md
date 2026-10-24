# Modelo analítico por parcela

Unidad: RC14 del universo CP con asignación distrital 07 en sesión 2. No se limita a parcelas visibles en el mapa ni solo a residencial; uso residencial se muestra mediante número de BU declarados residenciales. Se agrupan las filas CP por RC14 y se conserva `cp_rows`; BU y energía se agregan por separado antes de unir. Una parcela no es un edificio físico. El mapa anterior sigue mostrando BU.

`analytics.parcel_features` es función pura. Entrada: parcelas auditadas, BU auditados, certificados integrados y enlaces de sesión 2. Salida: una fila por RC14. No se modifican entradas. CLI verifica los hashes contra el manifiesto de sesión 2 y vuelve a comprobarlos al finalizar. Se exige directorio de salida nuevo.

Variables: número de filas CP y BU únicos, BU residenciales declarados; extremos del periodo constructivo (1000–2026); número de registros CEEE confirmados, recuentos A–G, número con letra válida, proporción E/F/G, recuentos por año de fecha declarada, primera/última fecha y número de ámbitos diferentes. No se promedian consumo/emisiones entre ámbitos dispares. No hay barrio verificable en estas tablas.

La unidad energética es versión de registro `record_id`, no certificado administrativo único. No se selecciona arbitrariamente una versión vigente de `edif_codreg`. Se deduplican record_id y pares certificado/parcela, y se exige confirmación tanto del enlace como del registro completo. No se atribuye letra al BU. Los años de fecha declarada pueden ser anteriores a los recursos 2025–2026 de extracción.

Denominador E/F/G: registros únicos observados en parcela con letra A–G. Ausencia de letras válidas produce nulo, nunca cero. Recuentos cero significan cero registros vinculados en esta captura. Extremos constructivos nulos no se imputan. No se agregan viviendas con superficies de huella.

Conservación/ayudas: `inspection_source_status` y `grant_source_status` valen `not_integrated`. No se crean importes ni recuentos falsamente cero. `observed_dimensions` cuenta disponibilidad de construcción y energía (0–2), no calidad del inmueble. Cobertura guarda nulos para fuentes no integradas y faltantes por columna. Eventos importados por CLI aún no se conectan automáticamente al análisis; requiere revisión del esquema real.

Artefactos: `parcel_features.parquet`, `coverage.json`, `sensitivity.parquet`, `construction_periods.csv`, `manifest.json`. Este último registra versión, hashes de entradas/salidas y duración. Datos e informes generados están ignorados por Git. Comparaciones descriptivas por periodo tienen sesgo de selección de certificados y no establecen causalidad.

## Contrato v2 vigente

La profundización materializa `data/processed/session_6_audited/` sin sobrescribir v1. Véase [auditoría completa](auditoria_analitica_chamberi.md). El motor conserva `analytics.parcel_features`, con implementación en `features.py`. Rechaza identidades contradictorias y enlaces huérfanos y usa ambigüedad CP global. Añade recuentos por ámbito, letras/fechas ausentes, intervalos inválidos, perfiles y malla métrica de 500 m (no barrio). CSV de comparaciones incorpora denominadores y distingue mediana por parcela de proporción agrupada por registros.

Nuevos artefactos: `audit.json` con reconciliación, sesgos y estados; `energy_observations.parquet` mínimo por registro/parcela confirmado (fecha, año, letra y ámbito, sin nombres); `sensitivity_summary.parquet` con 20 escenarios. Manifiesto registra parámetros, hashes del manifiesto fuente y de módulos principales. `analysis_store` acepta capturas v1, ofrece funciones de lectura sin Streamlit y verifica hashes; el visor añade caché con invalidación por cambios de archivos.

Eventos opcionales: `--inspections-dir` y `--grants-dir` consumen capturas canónicas revisadas contra la misma versión CP. Solo entonces se crean columnas observadas de eventos, con importes desconocidos nulos. Cobertura administrativa permanece distinta de las dos dimensiones construcción/energía de `observed_dimensions`. La mera presencia de eventos no habilita IPR global.

## Generalización municipal de sesión 7

`parcel_features(..., district='all')` conserva una fila por referencia CP de toda la captura y utiliza una asignación territorial única solo cuando todas sus CP concuerdan. Se mantiene el comportamiento histórico por distrito para regresión; las particiones nuevas se derivan del universo municipal canónico, evitando duplicar una RC entre distritos. `district_assignment` y los residuales explican diferencias entre filas geométricas y referencias. Chamberí mantiene las 47 variables previas.

`district_summary` separa CP espaciales, RC analíticas, BU espaciales y BU por contexto de parcela, registros únicos y pares registro/parcela. Agregados de letras y ámbitos deduplican registros dentro de distrito; las pertenencias entre distritos no se suman sin comprobar intersecciones. Dos registros confirmados en CP quedan sin distrito. 38 referencias residuales completan el universo. Los perfiles/umbrales y sensibilidad se reutilizan sin introducir IPR global. [Contratos y denominadores municipales](calidad_sesion_7.md).
