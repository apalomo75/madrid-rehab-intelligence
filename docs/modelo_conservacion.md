# Modelo de conservación — v1, sesión 14

La capa `conservation-evidence-v1` reutiliza la captura administrativa de sesión 10 y los enlaces energéticos y PRTR auditados. No importa actas REC. Distingue acceso municipal, parcela CP, objeto BU, BuildingPart, unidad inmobiliaria, certificado y expediente. No crea vínculos a edificios físicos ni asigna un estado material a la parcela.

## Entidades efectivamente materializadas

| Producto Parquet | Unidad y contenido |
| --- | --- |
| `conservation_accesses` | Versión observada de una dirección oficial; `access_id=28079:ndp:COD_NDP`, identificador de versión y fila original. Un NDP puede conservar varias denominaciones. |
| `conservation_parcel_links` | Todas las filas del puente documental previo, candidatos y contradicciones incluidos; referencia confirmada separada. |
| `conservation_events` | Los 124.175 eventos municipales previos, mismos ID y literales; 14.645 órdenes/obligaciones y el resto contexto de licencias/declaraciones. |
| `conservation_source_records` | Evento, versión, archivo, fila/página, hash original y fechas conocidas. Los bytes originales siguen en su almacén por SHA-256. |
| `conservation_evidence_profile` | Una fila por CP con evidencia de conservación confirmada; señales explicables, fechas, ID de eventos y contexto energético/PRTR. |
| `conservation_energy_links` | Relaciones CEEE–CP de nivel A para esas parcelas, con ámbitos, letras observadas, fechas e identidad del contenido. |
| `conservation_grant_links` | Relaciones documentales de expedientes PRTR con esas CP. No incluyen importes como medida aditiva. |
| `conservation_grant_cases` | Una fila por expediente PRTR; programa, importe en céntimos y disponibilidad real de fecha. |
| `conservation_quality` | Cobertura y límites explícitos; solapamiento REC no evaluable. |
| `conservation_sources` | Inventario de fuentes y permisos, separado de la procedencia por registro. |
| `conservation_regional_coverage` | Los 179 municipios, distinguiendo cobertura administrativa histórica de disponibilidad de inspecciones individuales. |

No se materializan tablas vacías de inspecciones, deficiencias, sanciones u órdenes REC. Las órdenes reales anteriores ya tienen entidad en eventos. El parser experimental devuelve entidades separadas de casos, inspecciones, deficiencias literales, actuaciones y relaciones cuando encuentra evidencia, pero no las ingiere en estos productos. Las fixtures son exclusivamente pruebas.

## Vínculos y calidad

`confirmed_access_parcel` exige puente documental previamente auditado, CP única y utilizable y ausencia de conflicto entre versiones del acceso. `candidate_access_parcel` conserva propuestas no confirmadas; `ambiguous_access_parcel` conserva multiplicidad, contradicción, cuarentena o versiones incompatibles; `unmatched_access` no tiene vínculo utilizable. La columna `confirmed_parcel_ref14` solo se rellena para confirmaciones. No se emplea vecino más próximo. Un NDP puede conservar varios candidatos y una CP numerosos accesos.

Se verifican geometría utilizable y topología de CP; duplicados de referencia o cuarentena excluyen todas sus ocurrencias. El enlace previo de los eventos no se rehace por semejanza de dirección. Las CP externas no reciben NDP madrileños. Las asociaciones energéticas y PRTR permanecen en sus niveles auditados; coexistencia no prueba causalidad ni financiación de una deficiencia.

## Fechas e interpretación

Se conservan `date`, `origin_date`, `date_raw`, `query_date`, `capture_date`, estado y motivo originales. La fecha de una orden tiene precisión mensual; la fecha de una obligación es su plazo, no la realización de una inspección. `latest_administrative_date` puede por tanto ser un plazo futuro. Una fecha de descarga desconocida permanece nula: ni mtime ni generación del nuevo producto la sustituyen.

Todos los eventos históricos tienen `inspection_outcome=unknown`, `remediation_status=unknown` y condición física no evaluable. Las menciones desfavorables en el motivo de órdenes se etiquetan **indirectas**, sin generar inspecciones ni distinguir artificialmente el resultado de un acta no disponible.

El parser conserva los literales. Sus reglas reversibles producen:

| Evidencia explícita | Estado derivado |
| --- | --- |
| Desfavorable + pendiente de subsanación | `unfavorable_explicitly_pending` |
| Desfavorable + campo de subsanación «subsanación acreditada» o «deficiencias subsanadas» | `unfavorable_remediation_evidenced` |
| Favorable | `favorable` |
| Archivo sin acreditación material | `archived_material_outcome_unknown` |
| En tramitación | `in_progress` |
| Pendiente y acreditada simultáneas, o favorable y subsanación pendiente | `contradictory` |
| Evidencia insuficiente, terminado o resolver | `unknown` |

Estas reglas describen lo observado en la fuente y su fecha, no vigencia actual. No se usa una búsqueda parcial de «subsanado» que acepte negaciones. Las causas se conservan como `unmapped`, sin crear una taxonomía a partir de ejemplos manuales. No hay códigos de deficiencia REC reales integrados.

## Identidad y cronología

La identidad futura de caso REC combina órgano municipal y referencia documental completa. El acta/dictamen y cada actuación son registros distintos. Repeticiones idénticas de un bloque se deduplican; sus apariciones siguen en las filas preservadas. Un antecedente genera una relación, no una inspección nueva. La identidad de un mismo caso puede relacionarse con varios accesos mediante la tabla de relaciones.

El comparador `relation_level` ofrece A (expediente exacto y organismo), B (además NDP concordante), C (posible relación por acceso/dirección) y D (expediente concordante pero accesos incompatibles). Un ordinal de publicación de órdenes nunca es un número de expediente. C no autoriza fusiones; compartir parcela tampoco. No hay estadísticas de solapamiento REC calculables sin registros REC: se registra `not_evaluable_no_rec_records`.

La cronología de eventos, ordenada por fecha y conservando su precisión, es administrativa. No reconstruye ejecución material de obras. El perfil separa órdenes históricas de obligaciones observadas y no calcula score estructural, comercial o financiero. La función de señales distingue evidencia resuelta, pendiente en una observación, favorable, histórica y contradictoria; no cambia el estado de productos sin evidencia.

## Consulta y publicación

Las fichas consultan buckets por los dos primeros caracteres de RC14, filtro Parquet de referencia y row groups de 128 filas ordenadas. Caché de máximo 24 consultas, invalidación por tamaño/mtime/ctime, verificación SHA-256 y comprobación del CP municipal vigente. No se cargan todos los eventos en cada ficha. Las tablas globales se construyen solo offline.

La nueva sección completa se oculta con `MADRID_REHAB_PUBLIC=1`, antes de leer datos, por mezclar fuentes y relaciones con permisos no acreditados. Mantiene las protecciones energéticas y PRTR anteriores. No existe recolector REC, endpoint de lotes ni vía de activación de fixtures en la ingesta productiva.
