# Sesión 12.2: validación de la captura real

Se reutilizan exclusivamente los diez ZIP de `data/raw/cadastre/session_12_2_capture_01/`.
No se modifica ningún original, snapshot anterior, importe ni decisión municipal PRTR.
La ingesta sigue bloqueada: además de la discrepancia de cabecera existen identificadores
`CadastralParcel` duplicados en los cinco municipios. No se ha demostrado la condición
que permitiría aceptar una discrepancia exclusivamente del contador con una advertencia.
No se ha añadido una excepción ni se ha rebajado `strict_count`.

## Estructura y diagnóstico

Los CP usan `wfs:FeatureCollection` y `wfs:member` del namespace
`http://www.opengis.net/wfs/2.0`. Cada miembro contiene una entidad
`{http://inspire.ec.europa.eu/schemas/cp/4.0}CadastralParcel` en
`cadastralparcel.gml`, o `CadastralZoning` en `cadastralzoning.gml`.
Los IDs y las geometrías usan `http://www.opengis.net/gml/3.2`.
No hay miembros con otras entidades que expliquen la diferencia de parcelas.
La zonificación tiene su propia cabecera, tampoco reconciliada; no son parcelas
adicionales y sus cifras no se deben sumar al contador CP.

Los BU usan `gml:FeatureCollection/gml:featureMember`, con entidades del namespace
`http://inspire.jrc.ec.europa.eu/schemas/bu-ext2d/2.0`. Hay tres GML separados:
`Building`, `BuildingPart` y `OtherConstruction`. No declaran `numberReturned`
ni `numberOfFeatures`: no se inventa un contador. La integración existente incorpora
Building y BuildingPart por separado; OtherConstruction se inventaría y verifica como
capa independiente, sin reclasificarla como edificio.

Los CRC y el parseo XML hasta EOF son correctos en los diez ZIP y los 25 GML.
No se detecta truncamiento sintáctico, pero un XML bien formado no demuestra
exhaustividad ni permite descartar omisiones del productor. No puede determinarse
con estos archivos si las cabeceras quedaron obsoletas o si la exportación omitió
entidades. Se conserva esta discrepancia abierta, sin atribuirla al parser.

| Municipio | CP declaradas | CP observadas | Repeticiones de ID CP¹ | CZ declaradas / observadas | Building | BuildingPart | OtherConstruction |
|---|---:|---:|---:|---:|---:|---:|---:|
| Getafe | 18.242 | 18.210 | 48 | 1.825 / 1.643 | 15.039 | 77.975 | 1.193 |
| Móstoles | 11.981 | 11.912 | 71 | 1.329 / 1.063 | 8.437 | 48.173 | 1.435 |
| Leganés | 11.921 | 11.823 | 88 | 1.928 / 1.742 | 8.375 | 51.133 | 1.083 |
| Alcorcón | 6.638 | 6.614 | 23 | 1.234 / 1.064 | 4.824 | 32.781 | 540 |
| Alcalá de Henares | 13.985 | 13.930 | 24 | 1.727 / 1.562 | 12.160 | 73.892 | 1.240 |

¹ Ocurrencias adicionales tras la primera, no número de IDs distintos afectados.
También se repiten IDs de geometría asociados a las parcelas. El inventario JSON
incluye los recuentos por QName y ejemplos. No hay IDs GML duplicados en las capas
BU ni en CZ. Ejemplo de ID de parcela repetido: `ES.SDGC.CP.28065A01500002`.

## Cambio acotado de validación

`inspect_zip` conserva CRC, control DTD/entidades y parseo completo, y añade
inventario por GML: namespaces, cabecera, miembros, entidades por QName, IDs únicos,
repeticiones de ID tanto de entidades como del conjunto XML y ejemplos limitados.
Rechaza miembros vacíos/múltiples e identidades de entidad ausentes.

El modo auditado comprueba ese inventario antes de ingerir: los IDs duplicados,
las discrepancias no justificadas, los miembros no reconciliados y la paginación
pendiente bloquean la partición. La geometría ilegible/vacía y los IDs ausentes o
duplicados en las filas parseadas también bloquean: no pasan a ser simples flags
del modo auditado. Los flags previos de geometría/topología y límite municipal
siguen excluyendo objetos problemáticos de los cruces. Los parsers CP y BU
conservan el control estricto de sus contadores.

El piloto guarda `collection_inventory.json` en su nuevo snapshot regional,
con hashes de los diez originales en el manifiesto. Distingue
`blocked_source_integrity` de ausencia de datos reales. No se escribe el puntero
`active_prtr.json` si ninguna partición supera la validación.

## Ejecución y evidencia

Pruebas específicas, antes de la suite completa:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_cadastre*.py' -v
```

Piloto real, sin red y con salidas nuevas (estas rutas ya se han usado; para repetir,
elegir otras):

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_pilot --offline \
  --output-dir data/processed/cadastre/session_12_2_validation_real_01 \
  --regional-output data/processed/grants/regional/session_12_2_validation_real_01
```

Después, una sola ejecución de la suite completa y Ruff:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
```

Evidencia detallada en `reports/session_12_2/validation_real_01/`:
`independent_xml_audit.json` (inspección independiente, namespaces y ejemplos),
`geometry_audit.json` (lectura de geometrías e identidad por recurso),
`audit_geometry.py` (procedimiento de esa comprobación),
`pilot.log`, `targeted_tests.log`, `full_tests.log` y `ruff.log`.
Los recuentos de fuente no deben presentarse como CP/BU integrados.
Los vínculos candidatos/ambiguos no evaluados por bloqueo tampoco son ceros observados.

## Resultado del piloto

Salida **2**, cinco municipios `ingestion_blocked`, ninguna partición activada.
La suma de los cinco recuentos individuales es **62.489** CP observadas frente a
62.767 declaradas: diferencia **278**. El total 62.509 indicado inicialmente no
coincide con la suma de los recuentos de municipio, que sí reproduce la auditoría.

| Municipio | CP observadas | BU observados (Building + BuildingPart) | Nuevos confirmados PRTR/CP | Candidatos | Ambiguos | Expedientes pendientes |
|---|---:|---:|---:|---|---|---:|
| Getafe | 18.210 | 93.014 | 0 | No evaluados | No evaluados | 165 |
| Móstoles | 11.912 | 56.610 | 0 | No evaluados | No evaluados | 327 |
| Leganés | 11.823 | 59.508 | 0 | No evaluados | No evaluados | 234 |
| Alcorcón | 6.614 | 37.605 | 0 | No evaluados | No evaluados | 290 |
| Alcalá de Henares | 13.930 | 86.052 | 0 | No evaluados | No evaluados | 229 |
| **Total** | **62.489** | **332.789** | **0** | **No evaluados** | **No evaluados** | **1.245** |

Las columnas CP/BU son inventario físico de fuente, incluidas repeticiones, no
productos validados. Los ceros de relaciones registrados por el pipeline son
resultados no calculados por bloqueo, no prueba de ausencia de candidatos o
ambigüedad. Pendientes cuenta expedientes; no se confunden con filas de relación.
La contabilidad regional permanece en 7.532 expedientes y 31.552.733.899 céntimos.
Las decisiones municipales se copian sin cambios del snapshot 12.1.

La comprobación geométrica independiente ha leído las 62.489 filas CP y los
332.789 objetos Building/BuildingPart: no hay geometrías ilegibles, vacías ni
con topología inválida en esos objetos. Los IDs BU son únicos también al reunir
Building y BuildingPart de cada municipio. En CP hay 254 ocurrencias adicionales
de IDs, correspondientes a 207 IDs distintos repetidos (46 Getafe, 38 Móstoles,
82 Leganés, 20 Alcorcón y 21 Alcalá). No se deduplica ni reconstruye la fuente.
No se ha ejecutado el contraste geométrico contra límites ni el cruce PRTR/CP
sobre particiones rechazadas. OtherConstruction se ha contado e inspeccionado
como XML, sin incorporarlo a la comprobación geométrica de CP/Building/BuildingPart.

`municipality_summary.csv` contiene los recuentos observados y el estado de cruce;
`reconciliation.json` verifica hashes, conservación de relaciones previas,
decisiones municipales e importes, y ausencia de activación de cobertura nueva.

Validación final: **30 pruebas específicas correctas** (incluida integridad real
10/10, sin omisión), **341 pruebas de la única suite completa correctas**
(306,866 s), y **Ruff correcto**. Piloto real: salida 2 por integridad de fuente;
no se presenta como integración satisfactoria. Sin descargas, commits ni push.
