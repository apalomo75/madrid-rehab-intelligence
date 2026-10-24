# Diccionario administrativo — sesión 10

Esquema `administrative-v1`, separado de los contratos históricos de resultados de inspección y ayudas. Una fila canónica es una versión observada de un evento; no un edificio ni una obra ejecutada.

| Campo | Definición |
| --- | --- |
| event_id | SHA-256 de familia e ID oficial; órdenes incluyen año, periodo, dirección y motivo porque la numeración es ordinal de publicación con repeticiones. Obligaciones sin ID usan dirección literal, año, consulta y alcance. |
| event_version_id | SHA-256 de identidad y contenido original; conserva versiones contradictorias. |
| original_id | Expediente u orden original; vacío en consultas PDF sin identificador. |
| event_type | order, license, declaration, ite_pending, iee_pending. |
| date / origin_date | Fecha de resolución en licencias y alta en declaraciones; año/mes de órdenes; vencimiento en obligaciones. Precisión original conservada. |
| date_raw | Fecha literal de alta o columna original del PDF. |
| year | Año de resolución/registro u obligación; no equivale al año de consulta. |
| query_date | Fecha explícita «Datos a fecha» en PDF; desconocida en otros archivos. |
| capture_date | Vacío si no consta descarga/captura; mtime no se usa como sustituto. |
| address_raw / address_normalized | Literal y clave exacta tipo-vía/nombre/número/calificador. No fuzzy matching. |
| ndp | Código de número normalizado; no identifica por sí solo un edificio físico. |
| district_declared / district_code | Declaración de la fuente y territorio del puente; diferencias impiden confirmación. |
| parcel_ref14 | Solo se rellena en relaciones inequívocas con una fila CP única. |
| candidate_refs | Referencias oficiales candidatas separadas por `\|`; nunca se dibujan como confirmadas. |
| match_status | confirmed, multiparcel, ambiguous, contradictory, candidate, unmatched. |
| match_method / match_level | NDP oficial o dirección oficial exacta; nivel parcel/unconfirmed. |
| administrative_status | Literal de resolución o estado observado; no infiere vigencia ni ejecución. |
| category / description | Clasificación transparente por términos explícitos y categoría original. Residencial solo no permite clasificar rehabilitación. |
| raw_json | Campos originales completos para auditoría local; fuera de las exportaciones del visor. |
| source_file / source_row / page | Archivo original, fila tabular o línea en página PDF. |
| quality_flags | Dirección incompleta, número extraordinario, fecha inválida o año de inspección distinto del de obligación. |
| identity_conflict | Mismo ID con contenidos diferentes; fuera de recuentos inequívocos de parcelas. |

`event_publications.parquet` conserva las publicaciones y su posición. CSV y XLSX equivalentes no se importan dos veces; `format_equivalence.json` contrasta todos los campos salvo las fechas formateadas, sustituidas para esta comparación por sus componentes oficiales año/mes/día. No se relacionan licencias y declaraciones solo por parcela y año.

El puente incluye NDP, códigos de vía, literal numérico, calificador, clase de numeración, coordenadas ETRS89, referencias originales y candidatas, filas CP, distrito declarado y CP, distancia en metros a la geometría referida. Los Parquet por archivo preservan las tablas completas originales. Las referencias RC20 no acreditan inmueble ni checksum: se conserva la validación de formato del proyecto y la comprobación de existencia RC14.

Las concesiones futuras usan el contrato de `events.py` (`grant`, fase `award`, inmueble subvencionado, importe/moneda y expediente). La convocatoria BOCM no satisface ese contrato y no genera eventos de ayuda.
