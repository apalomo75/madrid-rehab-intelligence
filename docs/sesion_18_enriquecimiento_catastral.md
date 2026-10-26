# Sesión 18 — enriquecimiento catastral offline

**Completados y validados los cinco pilotos: 332.746 BU enriquecidos, 313.621 relaciones documentales A y 20 ejemplos reales trazables.** No se cambia el visor ni se propagan CEEE/PRTR a BU. Una relación BU–CP sigue sin identificar edificio físico, portal, vivienda o unidad certificada.

## 1. Productos y confirmación de sesión 17

Snapshot nuevo e independiente: `data/processed/cadastre/session_18_enriched_01/`. Sus cinco manifiestos municipales y el manifiesto de colección están validados. No hay puntero de activación ni cambios en snapshots previos. Informe reproducible: `reports/session_18_enrichment/`; ejecución final de controles: `validation_02/`.

Se han confirmado directamente los cinco hallazgos: 332.746 BU aceptados, 283.926 BuildingPart, 324.772 referencias documentales a CP aceptada única y 1.182 disjuntos. El inventario incremental de Madrid vuelve a contar 811.691 BuildingPart originales. Las definiciones coinciden con sesión 17: BU utilizable del snapshot parcial; CP en vista aceptada, única; disjunto topológico exacto, sin tolerancia. No se confunde intersección con confirmación.

Corrección incidental: el texto de sesión 17 decía 43 inicios de construcción piloto sin año interpretable; las distribuciones originales y el nuevo parser dan **42** (41 `--...` y uno con año de un dígito). No cambia ninguna de las cinco cifras principales ni se modifica aquel informe.

| Municipio | BU anteriores = enriquecidos | Building | BuildingPart | Mejoran atributos propios | BU sin emparejar / IDs duplicados |
| --- | --- | --- | --- | --- | --- |
| Alcalá de Henares | 86.040 | 12.156 | 73.884 | 86.040 | 0 / 0 |
| Alcorcón | 37.595 | 4.820 | 32.775 | 37.595 | 0 / 0 |
| Getafe | 93.014 | 15.039 | 77.975 | 93.014 | 0 / 0 |
| Leganés | 59.506 | 8.374 | 51.132 | 59.506 | 0 / 0 |
| Móstoles | 56.591 | 8.431 | 48.160 | 56.591 | 0 / 0 |

Todos los identificadores, tipos, geometrías, columnas anteriores y estados de aceptación se conservan, incluidos tipos pandas anulables: comparación exhaustiva antes/después, sin diferencias. Se contrastó el árbol XML normalizado de cada objeto aceptado con el SHA-256 del registro histórico; también miembro, ordinal y tipo.

Los diez ZIP CP/BU siguen intactos; el enriquecimiento lee los cinco ZIP BU y las CP ya aceptadas/completas. Los GML `.building.gml`, `.buildingpart.gml` y `.otherconstruction.gml` se recorren incrementalmente. Se conservan aparte los 43 BU originales excluidos y los 5.491 OtherConstruction en `source_only_objects.parquet`: **no se convierten en BU aceptados ni forman parte de los 332.746**. Las relaciones de estos objetos se conservan como declaraciones originales, sin validarlas como vínculos activos.

| Municipio | SHA-256 ZIP BU (prefijo; completo en manifiesto) | Captura BU UTC | BU observados no aceptados | OtherConstruction separados |
| --- | --- | --- | --- | --- |
| Alcalá de Henares | 0102234a9bdabbe9 | 2026-10-24T15:04:50.991405+00:00 | 12 | 1240 |
| Alcorcón | fb91b2d56c6abcc0 | 2026-10-24T15:04:41.261752+00:00 | 10 | 540 |
| Getafe | ea960f1be188ae4e | 2026-10-24T15:04:16.128915+00:00 | 0 | 1193 |
| Leganés | abb6c1cb19a32d3f | 2026-10-24T15:04:37.228803+00:00 | 2 | 1083 |
| Móstoles | a4c4a0f7630e43fd | 2026-10-24T15:04:27.418748+00:00 | 19 | 1435 |

## 2. Esquema y procedencia de atributos

Por municipio:

- `buildings_enriched.parquet`: columnas históricas intactas más `recovered_<atributo>` y `recovered_<atributo>_state`.
- `cp_bu_documentary_links.parquet`: una fila por declaración CP explícita; fila D si no existe declaración utilizable. Retiene todas las ocurrencias y claves, sin colapsar relaciones múltiples.
- `cp_bu_link_issues.parquet`: todas las relaciones B/C/D, con motivos y medidas geométricas; no modifica la cuarentena histórica de objetos.
- `attribute_quality.parquet`: municipio, tipo, atributo, estado, recuento y denominador; `previous_nonempty` se repite por estado y **no se suma entre estados**.
- `source_only_objects.parquet`, `summary.json`, `examples.json`, `manifest.json`.

Estados: `absent` (elemento inexistente), `present_empty` (vacío o `xsi:nil`), `declared` (válido para la regla), `invalid` (fecha/cantidad inválida o nil contradictorio), `pending_interpretation` (código desconocido, unidad no soportada o elementos múltiples). Cero es declarado; nunca se sustituye por nulo. Un texto original puede existir y ser inválido.

Los valores normalizados se almacenan como cadenas anulables, con semántica controlada por el atributo; cantidades enteras y decimales conservan reglas distintas. `attributes_json` guarda por atributo el texto original exacto, QName, ruta XML, atributos XML completos (unidad, nil y nilReason), estado y regla `catastre-attributes-v1`. Se conserva el valor original incluso cuando se rechaza su normalización. `source_declarations_json` retiene también otras hojas no geométricas sin interpretarlas. ZIP/hash, miembro, ID, ordinal, registro/hash histórico y fecha de captura permiten volver a la evidencia original.

| Campo recuperado | Elemento XML relativo al objeto | Interpretación |
| --- | --- | --- |
| Identidad INSPIRE | inspireId/Identifier/{localId,namespace,versionId} | Identidad del objeto, no CP por prefijo |
| Uso | currentUse | Catálogo conservador; desconocidos pendientes |
| Fechas de construcción | dateOfConstruction/DateOfEvent/{beginning,end} | Fecha ISO con año de cuatro dígitos y calendario válido |
| Viviendas y unidades | numberOfDwellings; numberOfBuildingUnits | Entero no negativo, incluido 0; no conteo de edificios físicos |
| Plantas | numberOfFloorsAboveGround; numberOfFloorsBelowGround | Entero no negativo propio del objeto |
| Altura bajo rasante | heightBelowGround[@uom=m] | No equivale a altura total del edificio |
| Superficie | officialArea/OfficialArea/value[@uom=m2] | Solo grossFloorArea interpretada: superficie bruta de plantas declarada |
| Condición | conditionOfConstruction | Declaración catastral funcional/declinada/ruina; no REC ni inspección actual |
| Vida y geometría | begin/endLifespanVersion; BuildingGeometry/... | Fechas del registro, precisión y representación declaradas |
| CP y direcciones | cadastralParcels/@xlink:href; addresses/@xlink:href | Referencia explícita y URL AD, sin ejecutar consultas de red |

Las rutas técnicas completas están en el parser versionado y en cada evidencia JSON. `heightAboveGround` se busca pero no está disponible: no se inventa altura sobre rasante. Las URLs AD no se convierten en una dirección postal consultada.

### Completitud después (recuentos válidos)

| Municipio | Uso | Fecha inicial/final válida¹ | Plantas sobre / bajo | Altura bajo rasante | Superficie bruta | Viviendas / unidades |
| --- | --- | --- | --- | --- | --- | --- |
| Alcalá de Henares | 12.105 | 12.145 / 12.145 | 73.884 / 73.884 | 73.884 | 12.156 | 12.156 / 12.156 |
| Alcorcón | 4.813 | 4.814 / 4.814 | 32.775 / 32.775 | 32.775 | 4.820 | 4.820 / 4.820 |
| Getafe | 15.023 | 15.026 / 15.026 | 77.975 / 77.975 | 77.975 | 15.039 | 15.039 / 15.039 |
| Leganés | 8.363 | 8.365 / 8.365 | 51.132 / 51.132 | 51.132 | 8.374 | 8.374 / 8.374 |
| Móstoles | 8.422 | 8.428 / 8.428 | 48.160 / 48.160 | 48.160 | 8.431 | 8.431 / 8.431 |

¹ «Declarado antes» no equivalía a fecha válida: se conservan los 48.820 textos originales y se normalizan 48.778 fechas iniciales y finales; 42 quedan inválidas. Uso, viviendas y unidades mantienen su cobertura anterior: no se completan con datos del padre.

Antes: plantas/altura/superficie/condición no eran consultables como atributos propios en estos productos. Ahora: **283.926 partes con plantas sobre/bajo rasante y altura bajo rasante (100% de partes); 48.820 Building con superficie; 48.779 con condición interpretada** y 41 con marcador pendiente. La disponibilidad de algún atributo constructivo útil pasa de 48.820/332.746 (14,67%) a 332.746/332.746 (100%): +283.926 objetos y +85,33 puntos. No aumenta la cobertura territorial; se recupera información de objetos ya aceptados.

Las partes siguen sin uso, año, viviendas, unidades ni superficie propia cuando el GML no los declara. No se heredan valores Building→BuildingPart ni a la inversa. `geometry_accuracy` declarado para todos no acredita exactitud física real.

## 3. Relaciones documentales y regla geográfica

Se utiliza exclusivamente `cadastralParcels/@xlink:href`, URL Catastro `GetParcel`, parámetro explícito `refcat`. Se conserva URL, QName, referencia original, clave normalizada si está soportada, archivo/ordinal/hash, CP candidata y motivos. Se contrasta `externalReference` cuando existe; no se deriva CP del identificador BU ni de proximidad. Los formatos rústicos no soportados quedan preservados, sin ampliar el normalizador histórico.

**A** exige declaración explícita, CP aceptada única sin colisión en CP completa, geometrías válidas EPSG:25830 y al menos 95% del área BU dentro de la CP declarada; ninguna otra CP puede cubrir más del 5% del BU. Es una regla operativa conservadora y versionada, no un estándar de identidad física. El informe incluye sensibilidad a 90/95/99% antes de otros controles (`summary.json`). Intersecar mínimamente o tocar el borde no basta.

**B**: referencia con incidencia de identidad/integridad o geometría. **C**: referencia explícita sin CP aceptada resoluble (formato no soportado o CP en cuarentena). **D**: sin referencia documental utilizable. En esta captura todas las filas tienen declaración, por eso D=0. Los casos de CP completa ambigua prevalecen como B incluso cuando no existe CP aceptada.

| Municipio | Declaración CP | A CP aceptada única² | A validado | B incidencia | C sin CP | D |
| --- | --- | --- | --- | --- | --- | --- |
| Alcalá de Henares | 86.040 | 84.319 | 81.748 | 2.612 | 1.680 | 0 |
| Alcorcón | 37.595 | 36.981 | 35.436 | 1.596 | 563 | 0 |
| Getafe | 93.014 | 92.147 | 88.202 | 4.134 | 678 | 0 |
| Leganés | 59.506 | 58.033 | 55.643 | 3.068 | 795 | 0 |
| Móstoles | 56.591 | 53.292 | 52.592 | 725 | 3.274 | 0 |

² Definición de sesión 17, previa al control geográfico más estricto. **324.772/332.746 = 97,60%** resuelven una CP aceptada única; **313.621/332.746 = 94,25%** pasan la clasificación A. Las 19.125 relaciones restantes no se confirman: B=12.135 (984 de identidad ambigua, 1.182 disjuntas, 5.101 contactos de borde, 4.868 solapes insuficientes); C=6.990 (6.660 formato no soportado y 330 CP en cuarentena). No hay IDs BU duplicados ni BU perdidos; sí se preservan las ambigüedades CP de origen.

Cardinalidad observada: una declaración CP por BU, múltiples BU por CP; 47.842 CP aceptadas tienen al menos un BU A. El modelo conserva múltiples declaraciones por BU si aparecen, poniéndolas en B cuando son destinos distintos. Compartir CP no confirma una relación padre-hijo entre Building y BuildingPart. No se suman superficies de entidades potencialmente superpuestas.

| Municipio | Contenido en CP declarada | Solape parcial | Solo borde | Disjunto | Interseca >1 CP³ | Área positiva en >1 CP³ | Geometría inválida resuelta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Alcalá de Henares | 60.296 | 22.159 | 1.724 | 140 | 47.490 | 18.755 | 0 |
| Alcorcón | 24.015 | 12.225 | 560 | 181 | 14.591 | 8.868 | 0 |
| Getafe | 67.001 | 23.195 | 1.432 | 519 | 62.374 | 17.985 | 0 |
| Leganés | 45.779 | 10.801 | 1.187 | 266 | 30.506 | 7.286 | 0 |
| Móstoles | 41.151 | 11.867 | 198 | 76 | 26.198 | 10.096 | 0 |

³ Incluyen otras CP aceptadas solo como diagnóstico, sin crear relaciones alternativas. La intersección topológica incluye bordes y no equivale a ambigüedad de área. Los vínculos sin CP resoluble no entran en las cuatro primeras columnas; sus conteos espaciales siguen conservados.

### Revisión exhaustiva de los 1.182 disjuntos

Todos son BuildingPart; todos mantienen referencia urbana idéntica antes/después de normalizar, geometrías válidas, CRS concordante y un componente geométrico en BU y CP. Ninguna CP tiene huecos interiores en estos casos; no se explica por multipartes ni por pérdida de clave ETL. Los árboles XML contrastados descartan que el nuevo pipeline haya alterado sus coordenadas. Los 1.182 intersectan el Building cuyo ID coincide con la hipótesis léxica `_partN`, sin confirmar por ello paternidad física.

1.033 separaciones mínimas ≤0,01 m; otras 112 entre 0,01 y 1 m; 30 entre 1 y 10 m y 7 mayores de 10 m (máximo 40,07 m). La distancia mínima pequeña es compatible con diferencias de representación/contorno, pero **no demuestra que un objeto enteramente fuera de CP sea un mero redondeo**. Solo dos tienen área positiva en otra CP aceptada, que no se adopta como sustituta. 479 tienen fechas de vida de registro distintas; no prueban causa temporal. CP/BU se capturaron el mismo 24-10-2026, con segundos de diferencia; las cabeceras Last-Modified son del 21-08-2026 a horas diferentes. Tampoco eso acredita una actualización física discordante.

Quedan sin causa probada las divergencias documentales/geométricas: requieren revisar representación del objeto, alcance legal de CP y evidencia de origen, especialmente los siete alejados. Ejemplos: Alcorcón `ES.SDGC.BU.9769001VK2696N_part23` (40,07 m); Móstoles `ES.SDGC.BU.8040106VK2674S_part30` (16,13 m). Se conserva la lista completa con fuente, parcela, métricas y motivos en `validation_02/s17_disjoint_review.{parquet,csv}` y el diagnóstico de huecos en `disjoint_geometry_diagnostics.csv`. Sin reparación geométrica ni parcela próxima automática.

## 4. Veinte ejemplos reales de mejora

Dos Building y dos BuildingPart por municipio. Cada fila conserva evidencia XML completa en `validation_02/examples.json` y en el snapshot; el ordinal y el miembro permiten reproducirla en el ZIP cuyo hash figura arriba. Los ejemplos prueban recuperación de atributos, no confirmación de CP ni identidad física (algunas referencias iniciales son rurales no soportadas).

| Municipio | Objeto BU | Tipo | Dato recuperado propio | Miembro / ordinal |
| --- | --- | --- | --- | --- |
| Alcalá de Henares | ES.SDGC.BU.000300100VK78C | Building | superficie bruta 18 m²; condición functional | building / 1 |
| Alcalá de Henares | ES.SDGC.BU.000300200VK78C | Building | superficie bruta 57 m²; condición functional | building / 2 |
| Alcalá de Henares | ES.SDGC.BU.000300100VK78C_part1 | BuildingPart | plantas 1 sobre / 0 bajo; altura bajo 0 m | buildingpart / 1 |
| Alcalá de Henares | ES.SDGC.BU.000300200VK78C_part1 | BuildingPart | plantas 1 sobre / 0 bajo; altura bajo 0 m | buildingpart / 2 |
| Alcorcón | ES.SDGC.BU.000600100VK26H | Building | superficie bruta 463 m²; condición functional | building / 1 |
| Alcorcón | ES.SDGC.BU.000600200VK26H | Building | superficie bruta 1475 m²; condición functional | building / 2 |
| Alcorcón | ES.SDGC.BU.000600100VK26H_part1 | BuildingPart | plantas 1 sobre / 1 bajo; altura bajo 3 m | buildingpart / 1 |
| Alcorcón | ES.SDGC.BU.000600100VK26H_part2 | BuildingPart | plantas 1 sobre / 0 bajo; altura bajo 0 m | buildingpart / 2 |
| Getafe | ES.SDGC.BU.000400200VK36D | Building | superficie bruta 3343 m²; condición functional | building / 1 |
| Getafe | ES.SDGC.BU.000700200VK35H | Building | superficie bruta 271 m²; condición functional | building / 2 |
| Getafe | ES.SDGC.BU.000400200VK36D_part1 | BuildingPart | plantas 1 sobre / 0 bajo; altura bajo 0 m | buildingpart / 1 |
| Getafe | ES.SDGC.BU.000400200VK36D_part2 | BuildingPart | plantas 1 sobre / 0 bajo; altura bajo 0 m | buildingpart / 2 |
| Leganés | ES.SDGC.BU.000101300VK36C | Building | superficie bruta 690 m²; condición functional | building / 1 |
| Leganés | ES.SDGC.BU.000200100VK36F | Building | superficie bruta 140 m²; condición functional | building / 2 |
| Leganés | ES.SDGC.BU.000101300VK36C_part1 | BuildingPart | plantas 1 sobre / 0 bajo; altura bajo 0 m | buildingpart / 1 |
| Leganés | ES.SDGC.BU.000101300VK36C_part2 | BuildingPart | plantas 1 sobre / 0 bajo; altura bajo 0 m | buildingpart / 2 |
| Móstoles | ES.SDGC.BU.000300100VK26A | Building | superficie bruta 17 m²; condición functional | building / 1 |
| Móstoles | ES.SDGC.BU.000300300VK26A | Building | superficie bruta 4965 m²; condición functional | building / 2 |
| Móstoles | ES.SDGC.BU.000300100VK26A_part1 | BuildingPart | plantas 1 sobre / 0 bajo; altura bajo 0 m | buildingpart / 1 |
| Móstoles | ES.SDGC.BU.000300300VK26A_part1 | BuildingPart | plantas 1 sobre / 0 bajo; altura bajo 0 m | buildingpart / 2 |

## 5. Alcance CEEE/PRTR: navegación posible, sin atribución a BU

Fuentes energéticas y de ayudas originales inalteradas. CEEE solo nivel A; PRTR solo estados confirmados. Recuento de CP distintas, no de importes ni edificios.

| Municipio | CP con BU A | CP CEEE | CP PRTR | CEEE y BU A | PRTR y BU A | Ambas y BU A | CEEE o PRTR y BU A |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Alcalá de Henares | 11.960 | 2.442 | 208 | 2.374 | 208 | 151 | 2.431 |
| Alcorcón | 4.738 | 1.471 | 244 | 1.469 | 244 | 212 | 1.501 |
| Getafe | 14.943 | 2.472 | 151 | 2.425 | 151 | 107 | 2.469 |
| Leganés | 8.253 | 2.133 | 198 | 2.122 | 198 | 161 | 2.159 |
| Móstoles | 7.948 | 2.229 | 277 | 2.156 | 277 | 231 | 2.202 |

En total **10.546 CP con CEEE**, **1.078 con PRTR**, **862 con ambas** y **10.762 con alguna** podrían navegar a BU A. Eso permite explorar entidades relacionadas, **no asigna el certificado o expediente al cuerpo construido**. Una vivienda certificada no califica Building completo y una concesión no acredita pago/obra. El producto BU no recibe ningún campo CEEE/PRTR ni altera sus vínculos o importes.

## 6. Madrid: viabilidad demostrada parcialmente y plan

Prueba independiente: `data/processed/cadastre/session_18_madrid_probe_01/`, estado `research_only_not_accepted`, sin introducir objetos en la captura histórica. Inventario incremental completo: **811.691 partes**, cero IDs duplicados y cero colisiones exactas con Building existentes; las 811.691 declaran EPSG:25830, plantas sobre/bajo y altura bajo con unidad m, y enlace CP explícito. 809.721 apuntan a CP histórica aceptable única (antes de revisar geometría). 811.678 coinciden con una hipótesis de ID padre existente; no es enlace padre acreditado.

Muestra limitada a los primeros 2.000 objetos por orden del GML, **no representativa**: 2.000 geometrías válidas y cada una intersecta un distrito; no se validaron las otras 809.691 geometrías. El inventario más muestra tardó 128,55 s de pared y alcanzó 752,38 MiB RSS. El Parquet de prueba ocupa 297.215 bytes: extrapolación muy débil, ~115 MiB si la muestra fuese representativa; el producto piloto completo sugiere reservar varios cientos de MiB adicionales para atributos/enlaces y más para índices/diagnósticos. No extrapolar esa compresión a una garantía de almacenamiento.

Impacto distrital: la CP documental propone candidatos en los 21 distritos; 12 partes con CP aceptada no tienen distrito CP. Esto no sustituye asignación geográfica propia. Preservar objetos que crucen distritos y no duplicarlos como edificios distintos.

**Propuesta de próxima ingestión Madrid:** (1) salida nueva y contrato propio, sin sustituir `buildings_audited`; (2) streaming en lotes 1.000–5.000 y dos pasadas para identidad/duplicados, evitando un diccionario con todas las geometrías; (3) validar geometría, CRS, municipio oficial e identidad INSPIRE de todas las partes antes de aceptarlas; (4) mismo control documental CP, sin resolver colisiones por fecha ni heredar padre; (5) particionar por geometría real en 21 distritos, preservando cruces/no asignados; (6) verificar recuentos, hashes y reanudación antes de conectar cualquier lector.

El lote piloto completo tardó **6 min 29,85 s** y alcanzó **1,53 GiB RSS**; el nuevo snapshot ocupa ~128 MiB. Como orden de magnitud, recuperar y contrastar 811.691 partes puede requerir decenas de minutos. No se promete memoria linealmente sostenible con el diccionario actual: a ese tamaño podría superar 10 GiB. El parsing sí es incremental; el matching todavía carga la partición municipal. Hace falta ejecución por bloques para Madrid. No se ha realizado reconstrucción completa ni se ha aceptado la muestra como cobertura.

## 7. Controles, determinismo y preservación

- 7 pruebas focalizadas (con múltiples casos) de parser, estados, fechas/calendario, unidades, XML seguro, tipos, no herencia, cardinalidad, CP ambigua, CRS/municipio, geometrías, clases A–D, determinismo y reejecución sin sobreescritura: OK.
- 14 pruebas del parser/ingesta parcial histórico: OK. Ruff global `src tests`: OK. No suite Streamlit ni navegador.
- Replay real completo Alcorcón (37.595 objetos): manifiestos y los siete hashes de salida **idénticos**; `determinism_validation.json`. Reanudación de cinco municipios verificada sin reescribir productos validados.
- Control inicial del lote real detuvo la publicación por conversión de dtype pandas `boolean`→`bool`. Se conservó la metadata Arrow original y se añadió regresión; no se publicó aquella etapa fallida. `failed_staging_01/` y logs iniciales son diagnóstico, no snapshot válido.
- El probe Madrid ejecutado se archiva en `madrid_probe_executed.py`, cuyo hash coincide con el manifiesto; el módulo mantenido solo elimina después un import sin uso, sin cambiar transformaciones.

Preservación: metadatos de **5.555 archivos previos** sin cambios; hashes íntegros de siete archivos locales de sesión 16, **31 entradas rehasheadas de sesión 17**, y todos los inputs/outputs municipales verificados. El control de metadatos no equivale a rehashear todos los archivos del repositorio. Árbol histórico y artefactos sesión 17 preservados. Sin descargas, commits, push, publicación, activación REC ni cambios del visor.

SHA-256 del manifiesto de colección: `b1bb066425fb3255e63a5d52ba13617b484ea8d814afd73ab33b84734a8a8209`. Los hashes completos de archivos fuente y productos están en los manifiestos y `integrity.json`.

## 8. Reproducción y reanudación

Desde la raíz, con las dependencias ya fijadas en `requirements.lock` (no hay dependencias nuevas):

```bash
# Instalación, si hace falta en Ubuntu con dependencias disponibles
.venv/bin/python -m pip install -r requirements.lock
# Salida nueva: cinco municipios
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_enrichment --output-dir data/processed/cadastre/replay_18_nuevo
# Solo un municipio; otras invocaciones pueden añadir los restantes al mismo root no sellado
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_enrichment --municipality 28005 --output-dir data/processed/cadastre/replay_18_parcial
# Reanudar: verifica y omite municipios ya validados; rehace solo los incompletos
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_enrichment --output-dir data/processed/cadastre/replay_18_parcial --resume
# Auditar una colección completa, siempre informe nuevo
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_enrichment_audit --enriched-dir data/processed/cadastre/replay_18_nuevo --output-dir reports/session_18_enrichment/replay_validation_nuevo
# Prueba Madrid aislada, salida nueva y límite explícito
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_madrid_probe --limit 2000 --output-dir data/processed/cadastre/replay_18_madrid_probe
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_cadastre_enrichment.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_partial_cadastre.py -v
.venv/bin/ruff check src tests
```

La reanudación es **por municipio**, no desde la mitad de un XML. Una etapa incompleta queda aislada sin manifiesto validado y se rehace en un directorio temporal nuevo; las salidas municipales se renombran al finalizar validación y rehash. Cambiar código/inputs impide reutilizar municipios validados: usar otro root. El manifiesto de colección solo se sella tras los cinco municipios; no se sobrescribe. Los productos tabulares son deterministas con entradas/código y entorno fijados; tiempos de logs/probe son medidas observacionales, no parte del determinismo del snapshot piloto.

## 9. Respuestas obligatorias y decisión

1. **¿Cuántos BU enriquecidos realmente?** 332.746, los mismos aceptados antes: 48.820 Building y 283.926 BuildingPart. Todos recuperan al menos un atributo constructivo útil propio; cero pérdidas o altas artificiales.
2. **¿Qué atributos nuevos podemos mostrar?** Plantas y altura bajo rasante de 283.926 partes, superficie bruta de 48.820 Building, condición interpretada de 48.779, enlaces CP/AD y procedencia/estados por campo. Están disponibles en datos; el visor no se ha modificado. No hay altura total ni dirección postal nueva consultada.
3. **¿Qué porcentaje se relaciona documentalmente con CP aceptada?** 97,60% resuelve CP única (324.772); 94,25% del total pasa la validación A (313.621). Son dos denominadores conceptualmente distintos: resolución frente a validación.
4. **¿Cuántos pendientes?** 19.125: 12.135 B y 6.990 C; cero D. Incluyen exactamente los 1.182 disjuntos, que siguen pendientes pese a sus distancias pequeñas en muchos casos.
5. **¿Mejora cuantificable?** +283.926 objetos con atributos constructivos útiles (+85,33 puntos de cobertura interna); superficie/condición antes omitidas y 313.621 relaciones documentales operativas auditadas. No son edificios físicos nuevos ni ampliación territorial.
6. **¿Parcelas con evidencia que podrían navegar a BU?** 10.546 con CEEE y 1.078 con PRTR; solape 862; unión 10.762 CP. Se navega entre entidades, sin atribuir evidencia de parcela al BU.
7. **¿Madrid viable?** Sí para un pipeline por lotes: inventario íntegro sin duplicados y muestra 2.000/2.000 válida. Falta validar íntegramente otras 809.691 geometrías y construir aceptación/distritos propios; no ejecutar una reconstrucción histórica directa ni escalar el diccionario actual sin controlar memoria.
8. **¿Qué falta para edificio físico?** Relación padre/parte explícita acreditada, portal/dirección y unidad persistentes, resolución humana/documental de incidencias y semántica temporal consistente. Compartir CP y atributos catastrales no demuestra que dos cuerpos sean el mismo edificio o que una evidencia individual les corresponda.

**Próxima actuación recomendada:** revisar una muestra estratificada de B (borde, solape, disjunto y ambigüedad), empezando por los siete disjuntos >10 m; después preparar la aceptación por lotes de Madrid. Mantener congeladas nuevas pantallas y cualquier herencia automática CEEE/PRTR. El contrato enriquecido y sus manifiestos pueden revisarse antes de decidir una integración mínima de navegación A.
