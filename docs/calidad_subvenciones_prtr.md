# Calidad PRTR — corte local 24/10/2026

| Indicador | Recuento | Unidad |
| --- | --- | --- |
| Originales | 7532 | features |
| Identidades | 7532 | expedientes |
| Referencias distintas | 6604 | RC14 con formato admitido; no confirmación regional |
| Relaciones | 7561 | expediente–RC14 |
| Multiparcela | 12 | expedientes con varias RC14 distintas |
| Lista refs con varios elementos | 19 | expedientes, incluye inválidos y repetidos |
| Viviendas declaradas | 72693 | suma por expediente, no viviendas únicas |
| Madrid confirmado | 3805 | expedientes |
| Pendientes territoriales | 3727 | expedientes; no equivale a otros municipios |
| Relaciones CP confirmadas | 3809 | relaciones |
| RC14 CP confirmadas | 3300 | parcelas |


No hay identidades repetidas: 0/7.532. Geometrías Point válidas: 7.532/7.532 (100%); CRS84, dos coordenadas finitas y límites angulares correctos. Fuera del sobre regional conservador: 0/7.532; **esto no verifica pertenencia a Comunidad de Madrid**, que requiere límites oficiales. Importes positivos finitos: 7.532/7.532; negativos: 0/7.532. Cada uno de los 28 campos originales está presente y no nulo en 7.532/7.532 registros. Cero y vacío no se interpretan automáticamente como información válida.

## Incidencias no destructivas

| Control | Expedientes | Denominador | Porcentaje |
| --- | --- | --- | --- |
| amount_over_1m_review | 26 | 7532 | 0.3452% |
| ano_construccion_review | 7 | 7532 | 0.0929% |
| invalid_reference | 9 | 7532 | 0.1195% |
| superficie_review | 5 | 7532 | 0.0664% |
| superficie_vivienda_review | 7 | 7532 | 0.0929% |


Los controles se superponen: no sumar incidencias como expedientes distintos. Cola `grant_quality.parquet`; literales en `raw_json`. Anomalías no eliminadas. Importe >1 M€ se marca para revisar, no como error demostrado; vivienda fuera de 1–1.000, superficie total fuera de 10–20.000 m², superficie vivienda fuera de 10–500 m² y año fuera de 1600–2026 son umbrales operativos explícitos, no reglas oficiales de elegibilidad. Hay un año 2649 y años 0: se conservan, no se corrigen. Número máximo declarado de viviendas: 354; superficie total máxima: 32,956; importe máximo: 4,159,912.95 €.

Formato RC14 urbano admite posiciones alfanuméricas iniciales, incluidos ejemplos reales como `02129E1VK4801A`; formato no equivale a checksum ni a existencia catastral. No se modifica el validador histórico para no alterar productos anteriores. Las 19 listas con múltiples elementos incluyen repeticiones, referencias truncadas y fragmentos de pocas letras; solo 12 expedientes contienen varias RC14 distintas admitidas. Todos los literales se mantienen; los no admitidos no se convierten en parcelas. Las referencias principales admitidas son 7532/7.532 (control de longitud, no checksum).

Estados de relación: {"ambiguous_cp": 3, "confirmed": 3809, "regional_cp_pending": 3749}. Distancias contrastables: 3809 relaciones; máximo 9.971 m; mediana 0.000 m. Sin contradicciones geométricas observadas en las relaciones contrastables; las pruebas incluyen contradicciones artificiales solo como fixtures. Ninguna ausencia en CP prueba que el inmueble esté fuera de Madrid.

## Semántica y sesgos

7.532/7.532 etiquetas administrativas son `APROBACIÓN CONCESIÓN`; fase normalizada `award`, nunca pago, justificación u obra terminada. No hay fechas individuales ni atributos verificables de tipología física o ahorro energético de la actuación. `age` se conserva como año declarado sin reparación. `sup_vivienda` y `viviendas_sup` se mantienen por separado: sus nombres y valores no acreditan superficies medidas de edificio físico.

`cns_t3_1`, `cns_t4_*`, `rnt_uc`, `viv_total` y distribuciones `viv_*` carecen de diccionario semántico verificado dentro del archivo. Se conservan en atributos originales para auditoría; no se presentan como ahorro energético individual ni renta de propietarios. No hay base para detectar «ahorro fuera de rango» sin inventar esa semántica; pendiente de diccionario oficial. Los porcentajes censales no son datos de cada beneficiario. No se deriva un índice comercial.

Viviendas, superficie y antigüedad son declaraciones asociadas a expediente, con cobertura y duplicidad potencial entre programas. La suma de viviendas no cuenta viviendas únicas. P4 no se atribuye al conjunto del edificio. P1 no equivale a un único edificio. Una parcela puede alojar varios edificios, viviendas y concesiones. El sesgo temporal y por programa impide inferir demanda abierta o ausencia de otras ayudas.

Las coincidencias administrativas/CEEE/antigüedad describen coexistencia a nivel de parcela. No enlazan obras por causalidad. Los eventos anteriores permanecen separados e intactos. Cobertura de otros programas y Catastro regional desconocida.

La unión de controles de fuente afecta a **51/7.532 expedientes (0,6771%)**; conserva 54 incidencias, pues algunos expedientes tienen varias. Además hay tres relaciones ambiguas por multiplicidad de filas CP. Estos controles no estiman precisión geográfica ni convierten importes altos en inválidos. Idempotencia operativa: repetir sobre la salida vigente produce `FileExistsError` y deja todos sus archivos con el mismo hash (`reports/session_11/idempotency.json`).
