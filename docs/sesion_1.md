# Sesión 1: base de datos oficial de Madrid

Se han descargado los archivos oficiales CEEE de 2025 y 2026 y los dos paquetes ATOM de ámbito municipal de Madrid (parcelas CP y edificios BU). No se ha necesitado reducir el ámbito geográfico ni hacer consultas catastrales individuales durante la descarga masiva. Las fuentes originales permanecen en `data/raw/session_1/`, con metadatos HTTP y SHA-256 comprobados.

La muestra previa, nueva e independiente de `run_002`, está en `reports/session_1_sample/`. Recupera cinco parcelas con punto EPSG:25830 y cinco objetos BU; confirma cuatro inmuebles RC20. La normalización revisada de `edif_tipo` produce 19 viviendas, diez edificios completos y una parte de edificio en las 30 filas de la muestra. Las otras referencias no se consultaron por el límite de muestreo, salvo una que queda fuera del patrón admitido; no deben contarse como respuestas negativas de Catastro.

La ingesta masiva se ha ejecutado sin red a partir de los originales ya descargados. Las instrucciones están en [ingesta.md](ingesta.md); los recuentos, esquemas, hashes y resultados de calidad están en `data/processed/session_1/informe_ingesta.md` y `ingestion_metrics.json`.

## Resultado real

| Archivo | Registros |
| --- | ---: |
| certificados_madrid.parquet | 115.664 |
| parcelas_madrid.parquet | 141.244 |
| edificios_madrid.parquet | 124.396 |

Se procesan 110.650 filas CEEE de 2025 y 125.523 de 2026: 55.271 y 60.399 corresponden a Madrid capital antes de deduplicar. Se eliminan seis filas con contenido idéntico. Las tres tablas se han vuelto a leer desde Python; sus hashes coinciden con el manifiesto y todos sus `record_id` son únicos.

113.060 registros de certificados vinculan todas sus referencias admitidas a una única fila de parcela; 66 quedan ambiguos, 1.029 no encuentran parcela en este archivo y 1.509 tienen referencia vacía o fuera del patrón admitido. No se confirma por ello identidad RC20 ni edificio físico. Entre BU y CP hay 124.317 enlaces por referencia única, 72 ambiguos y siete sin parcela encontrada.

Se conservan 1.654 ámbitos desconocidos o pendientes de revisar, tres fechas no convertibles y dos repeticiones de código con contenido distinto. Todas las conversiones numéricas de valores no vacíos de superficie/consumo/emisiones son correctas. Hay una geometría BU topológicamente inválida, conservada y marcada; las 141.244 geometrías CP son válidas. Ninguna envolvente geométrica queda fuera de los límites métricos amplios comprobados.

## Incidencias de la fuente que se conservan

La cabecera del GML CP declara 141.430 registros, pero el XML completo contiene 141.244 elementos de parcela: diferencia de 186. La descompresión finaliza sin error CRC; no se deduce que existan 186 parcelas concretas ausentes ni se inventan registros. La causa de la discrepancia del productor queda pendiente de aclaración.

Hay 140.595 identificadores CP distintos en esas 141.244 filas. Se conservan todas las filas con su identificador oficial y un `record_id` adicional derivado del hash del archivo y su posición. Las referencias con varias filas se consideran ambiguas para vincular certificados o edificios; no se fuerza una elección. No se afirma que todos los identificadores repetidos sean duplicados técnicos eliminables.

Los 141.244 puntos CP tienen coordenadas finitas dentro de la envolvente métrica comprobada. La validación topológica de cada geometría queda en las tablas y en el informe. Esta comprobación no acredita precisión posicional ni asigna distritos.

La auditoría de texto del conjunto regional original detecta caracteres de control C1 en 77 de 110.650 filas del CSV 2025 y en 38 de 125.523 filas del CSV 2026. Se han conservado sin reparación automática; ISO-8859-1 permite leer el archivo 2025 sin descartar sus bytes incompatibles con UTF-8 y Windows-1252. Esta auditoría comprende toda la Comunidad, antes del filtro municipal. Conviene revisar esas anomalías antes de basar enlaces en direcciones.

Los certificados conservan historial por contenido: una nueva fecha o cualquier otro valor distinto conserva otra versión, aunque se repita código o referencia. Una coincidencia con parcela no confirma vivienda ni edificio físico; los objetos BU no reciben letras energéticas.

## Validación del código

35 pruebas automatizadas offline, incluidas una ejecución completa con lectura de las tres tablas, preservación de historial, selección de capas ZIP, discrepancias de recuento, ámbito, geometría, CRS, hash de originales y límites HTTP. Ruff y comprobación de dependencias sin errores. Las pruebas sintéticas no estiman calidad ni cobertura de las fuentes reales.
