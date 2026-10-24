# Sesión 12.2: ingesta parcial y cuarentena de objetos

Esta continuación reutiliza la evidencia de `session_12_2_validation_real_01` y los
diez ZIP existentes. No descarga, repite auditorías generales ni modifica fuentes,
snapshots históricos, Streamlit o importes PRTR. La nueva vía es optativa y genera
un snapshot independiente: no rebaja la validación estricta existente ni activa
un puntero de cobertura completa en el visor.

## Comparación de los CP repetidos

Se comparan todos los atributos y el árbol XML completo, incluidos QNames expandidos,
atributos ordenados y texto con espacios XML normalizados. Se preservan orden de hijos,
atributos desconocidos y texto significativo. La comparación geométrica adicional usa
igualdad topológica de Shapely, no solo igualdad textual de coordenadas. No se infiere
vigencia a partir de la fecha mayor ni se fusionan geometrías.

Hay 207 grupos de `gml:id` repetidos, con **461 filas**, es decir, 254 ocurrencias
adicionales tras la primera. No son 254 filas que se puedan eliminar dejando intactas
las otras 207. Todos los grupos tienen contenidos diferentes; tampoco hay parejas de
copias exactas dentro de ellos. Se repiten tanto la clave INSPIRE `(namespace, localId)`
como `nationalCadastralReference`, además de los IDs GML de geometrías asociadas.
No se han encontrado referencias o claves INSPIRE que unan IDs CP diferentes en esta
captura. El pipeline usa `parcel_id` (gml:id) y `parcel_ref14` (referencia normalizada)
y, por tanto, las colisiones sí afectan a las claves operativas.

En 47 grupos hay fechas distintas. Eso describe posibles versiones o componentes con
historia diferente, sin acreditar cuál es vigente. No se reinterpretan las otras
geometrías como partes de una sola parcela. La fecha final nula tampoco permite elegir
una fila. Las diferencias completas y ejemplos de los cinco municipios quedan en
`reports/session_12_2/partial_validated_01/cp_full_comparison.json` y en las tablas
fuente del nuevo snapshot; los informes por municipio añaden hashes y geometrías.

Las cabeceras permanecen sin explicar: 62.767 CP declaradas frente a 62.489 observadas
(diferencia 278). `CadastralZoning` tiene otra cabecera: 8.043 declaradas frente a 7.074
observadas (diferencia 969). Cada fichero contiene exclusivamente su tipo de entidad;
los tipos presentes no reconcilian esas diferencias. Las repeticiones tampoco las
explican. No se afirma que los contadores estén desactualizados y no se fabrican filas
para los registros posiblemente ausentes.

## Criterio de selección

La cobertura se declara siempre **parcial validada**, limitada a los objetos observados.
Se pone en cuarentena toda fila con una clave de identidad CP repetida: gml:id,
INSPIRE sin escoger versionId, referencia normalizada o cualquier gml:id de su árbol.
Se incluyen **todas** las ocurrencias, aunque fueran idénticas: no se selecciona una
representante por orden ni fecha. También se ponen en cuarentena identidades CP
incompletas, geometrías ilegibles/inválidas, CRS o posición incompatibles, y objetos
que cruzan o quedan fuera del límite oficial. No se recorta ni repara una geometría.

BU se valida independientemente de CP. Conserva Building y BuildingPart como tipos
distintos; exige identidad GML e INSPIRE no conflictiva y geometría y municipio válidos.
Compartir referencia de parcela entre varios edificios no es una colisión de identidad
BU. Una BuildingPart sin referencia CP puede aceptarse como objeto BU autónomo, sin
inventar una relación con una parcela o un Building padre.

Los XML mal formados, DTD, ZIP corruptos, fuentes con hash diferente, esquema inesperado
o recuentos observados distintos de la evidencia congelada impiden publicar el snapshot.
La nueva selección parcial no convierte esas situaciones en advertencias.

## Conservación y cruce PRTR

Cada municipio contiene:

- `cp_source_records.parquet` / `bu_source_records.parquet`: bytes originales exactos de
  cada entidad, offsets en bytes en el GML, ordinal, miembro ZIP, hash del ZIP, hash del
  fragmento y hash de contenido normalizado. El ZIP original conserva además el contexto
  de namespaces y codificación; los offsets permiten reconstruir y verificar cada fila.
- `cp_all.parquet` / `bu_all.parquet`: todas las filas parseadas y sus decisiones, claves
  INSPIRE, referencia original, flags geométricos y criterio de selección versionado.
- `cp.parquet` / `bu.parquet`: vistas aceptadas exclusivamente; y `*_quarantine.parquet`:
  todas las filas excluidas de esas vistas, con los motivos. Aceptadas + cuarentena debe
  coincidir exactamente con las filas de fuente procesadas, por identificador de registro.
- `*_comparisons.json`: contenido y clasificación de grupos de IDs repetidos.
- `source_inventory.json`: evidencia previa, tipos, namespaces y cabeceras, incluidas
  CadastralZoning y OtherConstruction. Estas capas auxiliares se conservan en los ZIP
  inmutables y no se reclasifican ni se cuentan como CP o Building/BuildingPart aceptados.

El cruce PRTR usa **todas las filas CP**, con `usable_geometry=False` en la cuarentena.
Así, no desaparece una fila conflictiva para convertir otra de la misma referencia en
una coincidencia única. Una identidad en cuarentena tampoco confirma por referencia
si su grupo de referencia tiene una sola fila. La posición por sí sola sigue siendo
candidata. No se crean relaciones CP/BU en esta ingesta.

Los manifiestos incluyen hashes de entradas, salidas y política. El manifiesto es de
versión distinta de las particiones históricas completas: no puede pasar inadvertidamente
por una partición completa en `verify_partition`. No se modifica `active_prtr.json`.

## Reproducción

No hay dependencias nuevas. Instalación y comandos generales siguen en README.md.
Ejecutado sobre salidas nuevas (para repetir usar otro directorio):

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.partial_cadastre \
  --output-dir data/processed/cadastre/session_12_2_partial_validated_01
```

La evidencia predeterminada es
`data/processed/grants/regional/session_12_2_validation_real_01/`; `--evidence-dir`
permite otra captura de evidencia compatible. Se verifican los hashes de los ZIP
contra esa evidencia antes de leer registros; no hay código de descarga en esta vía.

Pruebas específicas y, al terminar los cambios, una sola suite completa y Ruff:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_partial_cadastre.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
```

## Ejemplos representativos

Se muestran un grupo con fecha común y otro con fechas diferentes por municipio.
En todos estos ejemplos las geometrías difieren y los tres identificadores de identidad
(gml:id, namespace/localId INSPIRE y referencia original) se repiten. Las superficies
son los valores de `areaValue`, sin sumarlos ni reemplazarlos por área calculada.
Los XML, atributos, coordenadas y hashes completos están en `examples.json` del informe.

| Municipio | gml:id (sin prefijo ES.SDGC.CP.) | Filas | Superficies declaradas (m²) | Fechas beginLifespanVersion |
|---|---|---:|---|---|
| Getafe | 28065A01500002 | 3 | 5.402 / 2.448 / 59.791 | 2013-04-04 |
| Getafe | 28065A02100218 | 2 | 11.906 / 3.150 | 2010-11-04 / 2015-02-10 |
| Móstoles | 28092A00400081 | 2 | 6.381 / 1.126 | 2009-04-14 |
| Móstoles | 5847302VK2654N | 4 | 195 / 164 / 19 / 19 | 2002-02-26 / 2006-11-27 |
| Leganés | 28074A01600112 | 2 | 4.389 / 974 | 2011-10-27 |
| Leganés | 28074A00100032 | 3 | 12.024 / 3.783 / 17.675 | 2011-09-21 / 2014-03-11 |
| Alcorcón | 28007A00110028 | 2 | 1.123 / 2.412 | 2010-03-25 |
| Alcorcón | 28007A90300066 | 4 | 1.838 / 22.074 / 21.760 / 3.140 | 2011-10-18 / 2013-09-09 |
| Alcalá de Henares | 28005A01400003 | 2 | 5 / 3.066.489 | 2025-11-25 |
| Alcalá de Henares | 3A28083E17RAD2 | 3 | 47.682 / 92.341 / 664.523 | 2010-01-15 / 2024-11-26 |

Una superficie igual (por ejemplo, dos valores 19) no implica duplicado exacto: las
coordenadas y el resto del contenido se comparan por separado. Tampoco se diagnostica
como error de Catastro toda diferencia geométrica: podrían ser componentes espaciales
o registros con historia distinta. Sin un criterio documental para resolver esa
identidad repetida se trata como conflicto operativo no resuelto y se conserva completo.

El motivo `missing_parcel_ref14` se refiere a **ausencia de la clave admitida por el
normalizador histórico**, no necesariamente a ausencia de referencia original. Este
normalizador solo admite el patrón urbano y devuelve nulo para formatos originales
como `28065A01500002` y `3A28083E17RAD2`. Las referencias originales se mantienen en
`reference_original` y en el XML exacto. No se declara que sean referencias oficiales
inválidas; se conservan en cuarentena por formato no soportado, sin ampliar el contrato
del matcher en esta sesión. La cuarentena puede tener varios motivos simultáneos.

## Resultado definitivo

**Integración parcial validada**, snapshot
`data/processed/cadastre/session_12_2_partial_validated_01/`.
Aceptadas **387.187 filas de objeto** (54.441 CP y 332.746 BU); en cuarentena
**8.091** (8.048 CP y 43 BU). Total conservado: **395.278 registros observados**.
No se incluyen CadastralZoning ni OtherConstruction en estos totales de CP/BU.
Los BU aceptados son **48.820 Building** y **283.926 BuildingPart**; son dos tipos,
no 332.746 edificios físicos independientes confirmados.

| Municipio | CP aceptadas | CP cuarentena | BU aceptados | BU cuarentena | Expedientes con algún CP confirmado | Expedientes pendientes |
|---|---:|---:|---:|---:|---:|---:|
| Getafe | 16.149 | 2.061 | 93.014 | 0 | 165 | 0 |
| Móstoles | 8.980 | 2.932 | 56.591 | 19 | 326 | 1 |
| Leganés | 10.541 | 1.282 | 59.506 | 2 | 234 | 0 |
| Alcorcón | 5.734 | 880 | 37.595 | 10 | 287 | 3 |
| Alcalá de Henares | 13.037 | 893 | 86.040 | 12 | 229 | 0 |
| **Total** | **54.441** | **8.048** | **332.746** | **43** | **1.241** | **4** |

Impedimentos para aceptar las filas restantes (motivos CP no excluyentes):

- **461 CP** pertenecen a los 207 grupos con identidad repetida. Todas sus ocurrencias
  están en cuarentena, incluidas las primeras 207; no solo las 254 repeticiones adicionales.
- **7.714 CP** no tienen clave `parcel_ref14` admitida por el normalizador histórico;
  la referencia original se conserva y no se diagnostica como inválida. Admitirlas
  exigiría revisar el contrato de referencias soportadas. No se amplía aquí.
- **550 CP** presentan conflicto de límite: 547 cruzan el límite y 3 quedan fuera.
- **43 BU** presentan conflicto de límite: 41 lo cruzan y 2 quedan fuera. No hay
  colisiones de identidad BU ni geometrías ilegibles en esta captura.

La comparación geométrica final confirma geometrías distintas en los 207 grupos:
192 tienen componentes separados entre sí y 15 se tocan sin solapamiento de área.
**No hay grupos con solapamiento de área**; por tanto, no se prueban contradicciones
físicas por superposición ni se afirma que todas estas filas sean errores de Catastro.
Son colisiones operativas de identidad con geometrías diferentes, compatibles con
posibles componentes, sin regla documental para reconstruir una sola entidad.
Los 47 grupos con fechas diferentes tampoco acreditan versiones sustituibles.
Se mantienen separados, completos y sin seleccionar una versión ni unir geometrías.

En PRTR hay **1.263 relaciones confirmadas**, correspondientes a **1.241 expedientes
con al menos una relación confirmada**. Eso no significa que todas sus referencias
estén resueltas. Se conservan fuera de confirmados:

- Tres relaciones ambiguas de tres expedientes de Alcorcón (referencias
  `1066001VK3616N` y `0966101VK3606N`). Son tres expedientes pendientes.
- Una relación de Móstoles con CP en cuarentena por cruce de límite
  (`4974902VK2647S`). Es el cuarto expediente pendiente.
- Una relación contradictoria de Alcorcón (`1374308VK3617S`, distancia 107,43 m,
  superior al umbral existente de 100 m). Su expediente tiene otra relación confirmada;
  esta relación contradictoria no se convierte en confirmada ni se oculta.

No hay candidatos espaciales en esta ejecución. No se genera ninguna relación CP/BU.
Se conservan las decisiones municipales, los vínculos históricos fuera del piloto y la
contabilidad regional: **7.532 expedientes y 31.552.733.899 céntimos**.
Las diferencias de cabecera siguen abiertas; los 278 CP y 969 CZ no observados no son
filas inventadas ni cuarentena reconstruida. La cobertura sigue siendo parcial.

## Verificación final

**14 pruebas específicas correctas**, **355 pruebas de una única suite completa
correctas** (362,215 s), y **Ruff correcto**. La ingesta parcial termina con salida 0
porque produce el subconjunto validado solicitado; eso no certifica cobertura completa
ni cambia la salida 2 del piloto estricto histórico para esta captura.

`reports/session_12_2/partial_validated_01/` conserva los logs, ejemplos y comparación,
`municipality_summary.csv`, `quarantine_reasons.json`, `reconciliation.json` y el
procedimiento `verify_partial.py`. La reconciliación comprueba los hashes de todos
los productos, las **395.278 filas XML originales y sus hashes**, que aceptadas +
cuarentena reproduce exactamente todas las filas parseadas, y que ninguna CP en
cuarentena participa en relaciones confirmadas. Quince muestras (una por cada GML
CP/Building/BuildingPart) se reconstruyen contra los offsets del original, sin repetir
la auditoría general de ZIP/XML. Las fuentes previas y los snapshots históricos no se
modifican. Sin activación de visor, exposición pública PRTR, commit ni push.

El diagnóstico exploratorio `cp_full_comparison.json` y el producto usan serializaciones
estructurales distintas para sus hashes normalizados; no se deben comparar hashes entre
ambos formatos. La trazabilidad autoritativa del producto usa `source_record_id`, el
SHA-256 de los bytes XML exactos y el algoritmo `normalized_tree` de la política de
selección. El informe exploratorio conserva su algoritmo en `compare_cp.py`.
