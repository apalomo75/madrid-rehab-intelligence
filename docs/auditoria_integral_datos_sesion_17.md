# Auditoría integral de datos — sesión 17

Auditoría local offline, 26-10-2026. **Decisión: priorizar recuperación del GML y relaciones documentales; mantener en pausa nuevas funcionalidades del visor.** Hay datos útiles para objetos catastrales y parcelas, pero no identidad física acreditada ni evidencias energéticas o administrativas confirmadas a BU.

No se ha cambiado código de producción, originales, snapshots ni cuarentenas; tampoco se ha descargado, publicado, hecho commit o push. Se preservan los cambios locales de sesión 16. No se inició Streamlit ni Chromium. Las verificaciones son de datos y lectores Python, no validación visual.

## 1. Alcance y trazabilidad

Se inspeccionaron los productos reales mediante metadatos Parquet (`product_inventory.json`), código, manifiestos y GML completos de los seis ZIP BU. Se contaron también `OtherConstruction` en los originales. El análisis principal usa las mismas fuentes predeterminadas que la navegación: Madrid `session_2`; pilotos `cadastre/session_12_2_partial_validated_01`; energía `energy/session_13_final_03`; PRTR regional dentro del snapshot parcial y expedientes `grants/session_11_final_03`; conservación `conservation/session_14_final_02`.

Evidencia reproducible en `reports/auditoria_integral_sesion_17/`: `run_02/results.json` (recuentos, distribuciones completas, ejemplos y hashes SHA-256 de entradas principales); `supplement.json` (cuarentenas, normalización, conservación); `relations.json`; `date_quality.json`; `raw_inventory.json`. Los `schema_*.json` enumeran campos y los CSV por CP conservan los identificadores comprobables. Los candidatos documentales son artefactos de investigación: **no activan ni confirman vínculos en la aplicación**.

## 2. Inventario contrastado

«CP aceptada» en Madrid significa utilizable y referencia única para el lector: sus 141.244 filas tienen geometría válida, pero 865 filas pertenecen a 216 referencias repetidas y no se resuelven de forma unívoca. No existe una cuarentena física Madrid equivalente a la de pilotos. En pilotos se utiliza literalmente la vista aceptada, sin rescatar filas de cuarentena.

| Municipio (INE) | CP observadas | CP aceptadas = refs únicas | CP excluidas | CP duplicadas no nulas¹ | BU observados | BU utilizables | BU excluidos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Madrid (28079) | 141.244 | 140.379 | 865 | 865 | 124.396 | 124.395 | 1 |
| Alcalá de Henares (28005) | 13.930 | 13.037 | 893 | 18 | 86.052 | 86.040 | 12 |
| Alcorcón (28007) | 6.614 | 5.734 | 880 | 16 | 37.605 | 37.595 | 10 |
| Getafe (28065) | 18.210 | 16.149 | 2.061 | 16 | 93.014 | 93.014 | 0 |
| Leganés (28074) | 11.823 | 10.541 | 1.282 | 106 | 59.508 | 59.506 | 2 |
| Móstoles (28092) | 11.912 | 8.980 | 2.932 | 37 | 56.610 | 56.591 | 19 |

¹ Se cuentan todas las ocurrencias de una clave no nula repetida, no solo las posteriores a la primera. `run_02/inventory.csv:cp_duplicate_rows` también agrupa nulos en pilotos; no debe interpretarse como duplicidad documental. El recuento corregido es `supplement.json:*_duplicate_nonnull_rows`, utilizado arriba.

Los cinco pilotos suman **62.489 CP observadas, 54.441 aceptadas; 332.789 BU observados y 332.746 utilizables**. Los 43 BU rechazados obedecen al límite municipal (cruce/exterior), no a ausencia de uso o año. No hay IDs BU duplicados en los productos de los seis municipios. Las CP de pilotos son geométricamente válidas incluso en cuarentena: la validez geométrica no resuelve identidad ni pertenencia municipal. Solo hay una geometría BU inválida entre los productos auditados: Madrid `ES.SDGC.BU.1324507VK4812C`, autointersección, excluida del análisis utilizable.

En pilotos hay 207 grupos de colisión GML/INSPIRE que afectan a 461 ocurrencias; no equivalen a las 193 filas con referencia normalizada no nula repetida. Las referencias no soportadas explican parte de esa diferencia. `supplement.json` conserva todas las causas de cuarentena por municipio. No se elige una versión vigente por fecha.

| Municipio | Aceptación CP dentro de captura | Cobertura respecto al Catastro real |
| --- | --- | --- |
| Madrid | 99.39% | Desconocida |
| Alcalá de Henares | 93.59% | Desconocida |
| Alcorcón | 86.69% | Desconocida |
| Getafe | 88.68% | Desconocida |
| Leganés | 89.16% | Desconocida |
| Móstoles | 75.39% | Desconocida |

La tasa anterior mide selección interna, **no exhaustividad territorial**. Las cabeceras CP piloto declaran 62.767 entidades frente a 62.489 observadas: 278 sin reconciliar. Madrid declara 141.430 frente a 141.244 en el producto; este contraste de cabecera y producto no demuestra por sí solo la causa de la diferencia. Ni el límite oficial ni el éxito de lectura prueban cobertura catastral actual del 100%.

Campos disponibles: CP tiene referencia, identificadores, geometría, municipio, calidad y procedencia; piloto añade clave INSPIRE, vida del registro, área y hashes/offsets. BU tiene identidad, geometría y cinco atributos constructivos, más procedencia; el piloto distingue tipo y conserva XML por registro. No hay identidad acreditada de edificio físico, unidad energética persistente ni relación BU–portal confirmada. Los enlaces AD originales son consultas parametrizadas, no direcciones postales ya recuperadas.

## 3. BU: completitud real y pérdida de información

Denominador por tipo de objeto aceptado. «Declarado» significa texto no nulo ni vacío; **no necesariamente año válido o cantidad positiva**. En todas las filas `Building` son 100% declarados inicio, fin, viviendas y unidades; en `BuildingPart` son 0% los cinco campos procesados. No hay vacíos de cadena en esos campos: los ausentes son nulos. Cero es un valor declarado y se cuenta aparte.

| Municipio | Building | BuildingPart | Uso / cinco simultáneos (Building) | Viviendas=0 / unidades=0 | Año inicial utilizable (Building) |
| --- | --- | --- | --- | --- | --- |
| Madrid | 124.395 | 0 | 99.73% | 13.254 / 17 | 124.154 |
| Alcalá de Henares | 12.156 | 73.884 | 99.58% | 2.661 / 0 | 12.145 |
| Alcorcón | 4.820 | 32.775 | 99.85% | 1.869 / 2 | 4.814 |
| Getafe | 15.039 | 77.975 | 99.89% | 1.732 / 4 | 15.026 |
| Leganés | 8.374 | 51.132 | 99.87% | 1.857 / 5 | 8.365 |
| Móstoles | 8.431 | 48.160 | 99.89% | 1.493 / 0 | 8.428 |

| Municipio | Uso / cinco simultáneos (% BU) | Inicio / fin / viviendas / unidades declarados (% BU) | Sin cinco atributos (% BU) |
| --- | --- | --- | --- |
| Madrid | 99.73% | 100.00% cada campo | 0.00% |
| Alcalá de Henares | 14.07% | 14.13% cada campo | 85.87% |
| Alcorcón | 12.80% | 12.82% cada campo | 87.18% |
| Getafe | 16.15% | 16.17% cada campo | 83.83% |
| Leganés | 14.05% | 14.07% cada campo | 85.93% |
| Móstoles | 14.88% | 14.90% cada campo | 85.10% |

Los 48.820 `Building` piloto tienen al menos cuatro de los cinco atributos; 48.726 tienen los cinco. Sus 283.926 `BuildingPart` (85,33% de BU utilizables) no tienen ninguno de esos cinco campos en Parquet. No son viviendas ni edificios completos. Madrid dispone de 124.395 `Building` utilizables, 124.065 con los cinco campos.

Las distribuciones exactas de uso y fechas por municipio/tipo están en `results.json:attributes`; las de años interpretables en `date_quality.json`. Hay 111.410 `Building` residenciales Madrid; en pilotos: Alcalá 9.495, Alcorcón 2.993, Getafe 13.322, Leganés 6.539, Móstoles 6.986. Se conservan además agricultura, industria, comercio, oficinas y servicios públicos; uso nulo no equivale a residencial.

La fecha `--01-01T00:00:00` está declarada pero carece de año. Madrid tiene 241 inicios sin año de cuatro dígitos interpretable (232 con `--`); pilotos 43. También aparecen años de uno o tres dígitos: no se reparan suponiendo un milenio. El informe de fechas ofrece histograma, valores rechazados e inicio residencial anterior a 1980. Estos recuentos son atributos del objeto catastral, no diagnóstico de antigüedad física verificada. La validación de año no constituye una validación completa de fecha/calendario.

### Pérdida ETL demostrada

La comparación exhaustiva GML–Parquet de los cinco campos que sí procesa el parser da **cero discrepancias** para IDs presentes en cada producto (incluidas sus filas en cuarentena). Sin embargo, el esquema omite información adicional existente:

| Municipio | Building originales: superficie/condición declaradas² | BuildingPart originales: plantas/altura declaradas | OtherConstruction fuera del producto |
| --- | --- | --- | --- |
| Madrid | 124.396 | 811.691 | 15.697 |
| Alcalá de Henares | 12.160 | 73.892 | 1.240 |
| Alcorcón | 4.824 | 32.781 | 540 |
| Getafe | 15.039 | 77.975 | 1.193 |
| Leganés | 8.375 | 51.133 | 1.083 |
| Móstoles | 8.437 | 48.173 | 1.435 |

² `officialArea/value` con unidad m² y referencia `grossFloorArea`; `conditionOfConstruction` incluye marcadores `-` además de functional/declined/ruin. Son declaraciones catastrales históricas, no inspecciones actuales. En Building, plantas sobre rasante está presente pero nulo; no debe contarse como atributo conocido. En BuildingPart, plantas sobre/bajo rasante y altura bajo rasante sí tienen valores, incluidos ceros.

En Madrid se han omitido **811.691 BuildingPart** completos de la ingestión histórica: `parse_buildings` solo acepta `Building`. En los pilotos se preservó el tipo y XML, pero no se proyectaron plantas, altura ni enlace CP. En los seis se pierden como campos consultables enlaces `addresses`, `cadastralParcels`, superficie y condición; Madrid también pierde metadatos INSPIRE/vida del objeto en su esquema reducido. `area_value` piloto busca `areaValue`, mientras el BU declara `officialArea/value`: queda nulo pese a existir superficie. La evidencia original no se ha destruido: ZIP local y XML por registro piloto permiten recuperarla.

Ejemplo exacto: Alcalá `ES.SDGC.BU.000300100VK78C`: uso `2_agriculture`, inicio/fin 1986, 0 viviendas, 1 unidad; GML declara superficie 18 m² y enlace CP `000300100VK78C`. La normalización urbana deja `parcel_ref14=None`, aunque `reference_original` y el enlace conservan la clave. Su `..._part1` declara 1 planta sobre rasante, 0 bajo rasante y altura bajo rasante 0 m; estos campos no están en Parquet. No se debe convertir esa referencia no soportada en CP aceptada.

## 4. Relaciones CP–BU

Todos los `Building` y `BuildingPart` originales auditados llevan `cadastralParcels` con `GetParcel&refcat=...`, además de enlace AD. Eso es evidencia documental de referencia, **no una mera coincidencia por prefijo INSPIRE**. Los `Building` tienen también `externalReference/reference`; las partes no necesitan ese elemento para declarar su enlace CP. No se siguió ningún enlace de red.

| Municipio | BU utilizables con enlace CP original | A CP aceptada única | Sin CP aceptada | Discordantes geométricos entre los anteriores |
| --- | --- | --- | --- | --- |
| Madrid | 124.395 | 124.316 | 79 | 0 |
| Alcalá de Henares | 86.040 | 84.319 | 1.721 | 140 |
| Alcorcón | 37.595 | 36.981 | 614 | 181 |
| Getafe | 93.014 | 92.147 | 867 | 519 |
| Leganés | 59.506 | 58.033 | 1.473 | 266 |
| Móstoles | 56.591 | 53.292 | 3.299 | 76 |

No hay destinos ambiguos dentro de la vista CP aceptada (por definición excluye colisiones). «Sin CP aceptada» mezcla formato no soportado, ausencia y cuarentena: no significa enlace original falso. La clave documental debe contrastarse contra CP completa y sus causas antes de habilitar relaciones. En pilotos, 925 referencias `externalReference` declaradas se pierden en normalización urbana, conservándose en `reference_original`.

Cardinalidad: un BU declara un enlace CP; una CP puede reunir Building y varias BuildingPart. Las frecuencias por CP y tipo están en `relations.json`. El análisis léxico `_partN` encuentra un ID Building presente para 283.871 partes aceptadas; **es hipótesis de agrupación**, no relación padre-hijo explícita acreditada ni número de edificios físicos. No se ha encontrado un enlace padre explícito en los atributos `xlink` recorridos; los únicos enlaces son AD/CP. No sumar superficies de Building y partes superpuestas.

### Exploración espacial independiente

CRS EPSG:25830; geometrías utilizables, sin reparar, recortar ni tolerancia. `covered_by` incluye borde; `intersects` incluye contacto sin área. Las columnas contenido e intersecciones **se solapan**, no son categorías sumables.

| Municipio | BU contenidos en ≥1 CP | Intersección 1 CP | Intersección >1 CP | Fuera CP aceptada | CP con 0 / 1 / >1 BU |
| --- | --- | --- | --- | --- | --- |
| Madrid | 73.416 | 14.162 | 110.192 | 41 | 12.103 / 16.754 / 111.522 |
| Alcalá de Henares | 60.296 | 36.739 | 47.490 | 1.811 | 870 / 0 / 12.167 |
| Alcorcón | 24.016 | 22.226 | 14.591 | 778 | 828 / 3 / 4.903 |
| Getafe | 67.002 | 29.282 | 62.374 | 1.358 | 956 / 0 / 15.193 |
| Leganés | 45.780 | 27.288 | 30.506 | 1.712 | 1.963 / 0 / 8.578 |
| Móstoles | 41.156 | 27.061 | 26.198 | 3.332 | 774 / 0 / 8.206 |

En Madrid un BU queda cubierto por dos CP aceptadas, señal de solape que requiere revisión. Hay 215.138 pares de contacto solo por borde Madrid; pilotos 213.551. Por eso el alto número de intersecciones múltiples no equivale a otras tantas asignaciones reales ambiguas. Los CSV guardan conteos por ID. La clasificación topológica exacta no descuenta contactos ni estima qué CP es dominante; no se ha ejecutado una asignación espacial definitiva.

Diagnóstico: combinación de **pérdida de proyección ETL**, enlaces documentales no explotados, formatos excluidos y discordancias estructurales/geométricas. No hay evidencia para atribuir las 1.182 discordancias piloto a diferencias temporales; las fechas de captura, vida del registro y observación tienen semánticas distintas. Falta reconciliación, no basta un matcher espacial nuevo.

## 5. CEEE, PRTR y conservación

Solo vínculos CEEE A y PRTR `confirmed*`, limitados a CP aceptadas; no se trasladan a BU. Conservación cuenta perfiles con eventos de conservación, no todos los contextos administrativos.

| Municipio | CP con CEEE (%) | CP con PRTR | Ambas | Con conservación | Sin CEEE ni PRTR | Sin las tres evidencias observadas |
| --- | --- | --- | --- | --- | --- | --- |
| Madrid | 51.842 (36.93%) | 3.300 | 2.578 | 9.036 | 87.815 | 82.728 |
| Alcalá de Henares | 2.442 (18.73%) | 208 | 151 | Fuente no integrada | 10.538 | 10.538 |
| Alcorcón | 1.471 (25.65%) | 244 | 212 | Fuente no integrada | 4.231 | 4.231 |
| Getafe | 2.472 (15.31%) | 151 | 107 | Fuente no integrada | 13.633 | 13.633 |
| Leganés | 2.133 (20.24%) | 198 | 161 | Fuente no integrada | 8.371 | 8.371 |
| Móstoles | 2.229 (24.82%) | 277 | 231 | Fuente no integrada | 6.705 | 6.705 |

Los controles directos de identidad por municipio están en `evidence_counts.json`: duplicados de ID, conflictos, ocurrencias exactas adicionales, ámbitos y filas repetidas de enlace; `evidence_ceee_counts_*.csv` distingue filas de vínculo y certificados únicos. Las listas completas `ceee_per_cp_*.csv` y `prtr_per_cp_*.csv` cuentan certificados y expedientes únicos por parcela; importes pertenecen al expediente, nunca a cada enlace. Un expediente puede referirse a varias CP. `results.json:inventory` conserva por municipio los estados CEEE y PRTR, incluidos D, referencias ausentes, contradicciones y cuarentena. Para CEEE, los pilotos tienen 75 enlaces D y Madrid 117; no se contabilizan como evidencia confirmada. PRTR: Alcorcón tiene tres relaciones ambiguas y una contradictoria; Móstoles una CP no utilizable; Madrid tres relaciones históricas ambiguas.

Las fuentes energéticas contienen conflictos de inscripción y duplicados exactos preservados/deduplicados con trazabilidad; no interpretar contenidos canónicos como inmuebles únicos. `supplement.json:energy_quality` aporta controles históricos (39 ocurrencias exactas adicionales, 26 contenidos conflictivos y uno insuficiente), que deben distinguirse de los conteos directos de enlaces realizados aquí. Los IDs de certificados se cuentan distintos por CP para evitar multiplicar referencias.

### Contraste positivo y negativo de lectores

Se comprobaron **cinco CP CEEE y cinco CP PRTR por municipio**, más una negativa por municipio: 66 comprobaciones sin discrepancia de conjuntos de IDs. Los expedientes se cruzaron con el lector de detalle real `grants_view.read_view`; CEEE con `energy_view.read` y sus particiones de certificados. No se infiere de esta muestra igualdad exhaustiva ni corrección visual. Ejemplos (todos los IDs esperados/recuperados en `results.json:examples`):

- Madrid: CEEE 0002601VK4700A, 0002602VK4700A, 0002603VK4700A, 0002604VK4700A, 0003401VK4700C; PRTR 0006716VK4800E, 0006718VK4800E, 0010901VK4801A, 0010902VK4801A, 0010904VK4801A.
- Alcalá de Henares: CEEE 0015101VK7801N, 0015102VK7801S, 0015301VK7801N, 0015302VK7801N, 0016302VK7801N; PRTR 0015301VK7801N, 0016401VK7801N, 0018901VK7801N, 0019101VK7801N, 0019401VK7801N.
- Alcorcón: CEEE 0048401VK3604N, 0049901VK3604N, 0050901VK3605S, 0051901VK3605S, 0054401VK3605S; PRTR 0051901VK3605S, 0065404VK3606S, 0065407VK3606S, 0067003VK2696N, 0068101VK2696N.
- Getafe: CEEE 0036104VK4603N, 0120402VK4601N, 0131401VK4603S, 0132901VK4603S, 0132902VK4603S; PRTR 3843334VK4634S, 4138201VK4643N, 4341136VK4644S, 5414707VK3651S, 5604501VK3650S.
- Leganés: CEEE 1427501VK3612N, 1427504VK3612N, 1522402VK3612S, 1822801VK3612S, 2065123VK3626S; PRTR 2729311VK3622N, 2936921VK3623N, 3133404VK3633S, 3135902VK3633N, 3233701VK3633S.
- Móstoles: CEEE 0029101VK2602N, 0029102VK2602N, 0030804VK2603S, 0031009VK2603S, 0031101VK2603S; PRTR 0031117VK2603S, 1534723VK2613S, 1827302VK2612N, 1828202VK2612N, 4848801VK2644N.

También se contrastaron cinco perfiles positivos de conservación con sus lectores de eventos y accesos: `0004407VK4700C`, `0004414VK4700C`, `0004514VK4700C`, `0004515VK4700C`, `0004516VK4700C`. La tercera devuelve dos filas de eventos, pero solo una es evento de conservación: contexto no equivale a resultado ITE/IEE. No hay fichas REC reales integradas.

## 6. Utilidad de las fichas actuales

Niveles calculados con datos procesados y enlaces actualmente acreditados, sin utilizar candidatos nuevos. N0: identificación/geométrica sin atributos constructivos ni evidencias; N1: atributos constructivos propios; N2: evidencia confirmada a CP; N3: atributos constructivos propios y evidencias múltiples al mismo objeto acreditado. CP conserva metadatos catastrales en N0: la etiqueta no implica ausencia literal de toda columna adicional.

| Municipio | CP N0 | CP N2 | Building N1 | BuildingPart N0 | BU N2/N3 y CP N3 |
| --- | --- | --- | --- | --- | --- |
| Madrid | 82.728 | 57.651 | 124.395 | 0 | 0 |
| Alcalá de Henares | 10.538 | 2.499 | 12.156 | 73.884 | 0 |
| Alcorcón | 4.231 | 1.503 | 4.820 | 32.775 | 0 |
| Getafe | 13.633 | 2.516 | 15.039 | 77.975 | 0 |
| Leganés | 8.371 | 2.170 | 8.374 | 51.132 | 0 |
| Móstoles | 6.705 | 2.275 | 8.431 | 48.160 | 0 |

N0 sirve para localizar el objeto y decidir qué investigar; no prioriza rehabilitación. N1 permite seleccionar uso/antigüedad declarados del objeto. N2 permite consultar certificados, concesiones y antecedentes en su unidad de referencia. N3 físico no está acreditado: ni varias evidencias de parcela ni información de otro BU permiten promoverlo. Las partes hoy N0 podrían alcanzar N1 al recuperar sus atributos originales, sin inventar uso o año propios.

## 7. Auditoría del visor: incidencias concretas

- **Construcción piloto omitida por contrato:** `municipal_navigation.construction_records` devuelve vacío para todo código distinto de Madrid. Es prudente ante el contrato existente, pero los enlaces GML permiten preparar una reconciliación documental que hoy falta. No es ausencia general de datos constructivos.
- **Esquema constructivo incompleto:** `municipal_fiche.CONSTRUCTION_LABELS` no incluye plantas, altura, superficie ni condición; añadir etiquetas por sí solo no recuperaría datos que no están proyectados.
- **Separación BU–CP correcta, pero costosa en utilidad:** sesión 16 pone `ref=None` para fichas BU. Así ningún BU muestra evidencia CP automáticamente. No debe revertirse usando mera geometría: recuperar primero la relación documental y mantener alcance de parcela.
- **Mensajes confluyen:** CEEE usa el mismo genérico si falta una partición y si la consulta devuelve cero enlaces. PRTR lo usa si el lector de casos es `None`, además de cuando no hay vínculos. Conservación fuera de Madrid devuelve `None`, no un cero observado. En público, la ficha oculta CEEE/PRTR/conservación mediante `demo.private()`; CEEE tiene licencia local CC BY y no debe confundirse esta decisión de interfaz con ausencia de datos o licencia PRTR acreditada.
- **Errores de consulta:** sesión 16 ya aísla excepciones por panel y declara fallo; `resolve_object` diferencia error, ambigüedad y no utilizable. No eliminar esa distinción con el mensaje genérico. Los cinco ejemplos Madrid CEEE recuperan una fila constructiva cada uno: no se demuestra un fallo general del lector Madrid.
- **Detalle limitado aunque no falten filas:** PRTR muestra expediente/programa/importe pese a que el producto conserva actuación, superficie y otros atributos; CEEE muestra una selección de columnas y conserva en fuente más detalle. Es una reducción de presentación, no pérdida de expedientes/certificados demostrada en las muestras.

Propuesta para una futura sesión: estados explícitos «sin vínculos observados», «fuente no integrada», «consulta fallida», «ambiguo», «confirmado» y «oculto por modo/licencia», conservando la razón y la captura. No se ha implementado.

## 8. Preguntas prácticas y lagunas

| Pregunta | Respuesta actual / escala | Limitación y siguiente dato necesario | ETL u otra fuente |
| --- | --- | --- | --- |
| Residenciales antiguos | Sí, uso y año interpretables de Building; no censo de edificios físicos | Fecha declarada no siempre válida; partes sin uso/año propio; identidad física pendiente | ETL para campos/relaciones; otra evidencia para validar actualidad |
| Certificados desfavorables | Sí, certificados F/G observados y CP A | Unidad individual no califica edificio; sin identidad temporal física; no diagnóstico | ETL para detalle ya local; otra evidencia para edificio/unidad persistente |
| Antecedentes de conservación | Sí, 9.036 CP Madrid con perfil; pilotos sin fuente integrada | Obligaciones/órdenes/contextos no acreditan resultado o subsanación; sin REC real | ETL mejora acceso; resultados reales requieren otra fuente autorizada |
| Propiedades con ayudas | Sí, concesiones PRTR vinculadas a CP; no prueba de pago/obra | Expediente y CP no equivalen a propiedad individual o edificio; licencia sin verificar | ETL documental; pagos/ejecución requieren otra fuente |
| Sin evidencia en captura | Sí, última columna de cobertura | No equivale a ausencia real: fuentes, fechas, formatos y cuarentena limitan | ETL para estados; exhaustividad no acreditable con lo disponible |
| Construcción en dirección postal | Parcial: accesos NDP Madrid y enlace AD en GML | URL AD no es dirección recuperada; BU–portal físico no acreditado; sin llamar red | ETL de fuentes locales para candidatos; dato postal externo si no existe localmente |

## 9. Reproducción y límites

Desde la raíz, sin instalar ni descargar dependencias:

```bash
PYTHONPATH=src .venv/bin/python reports/auditoria_integral_sesion_17/audit.py --output reports/auditoria_integral_sesion_17/replay_nuevo
PYTHONPATH=src .venv/bin/python reports/auditoria_integral_sesion_17/supplement.py
.venv/bin/python reports/auditoria_integral_sesion_17/raw_inventory.py
.venv/bin/python reports/auditoria_integral_sesion_17/product_inventory.py
PYTHONPATH=src .venv/bin/python reports/auditoria_integral_sesion_17/date_quality.py
PYTHONPATH=src .venv/bin/python reports/auditoria_integral_sesion_17/relations.py --input reports/auditoria_integral_sesion_17/replay_nuevo --output reports/auditoria_integral_sesion_17/relations_replay.json
PYTHONPATH=src .venv/bin/python reports/auditoria_integral_sesion_17/evidence_counts.py
.venv/bin/python reports/auditoria_integral_sesion_17/write_report.py
PYTHONPATH=src .venv/bin/python reports/auditoria_integral_sesion_17/validate.py
.venv/bin/ruff check reports/auditoria_integral_sesion_17/*.py
```

El script principal exige directorio nuevo; relations admite entrada/salida alternativas; los auxiliares reconstruyen solo sus propios informes y el generador Markdown lee `run_02`, la ejecución validada. Para un replay independiente, cambiar esa ruta exclusivamente en copias de los scripts de informe o usar el resultado JSON nuevo directamente. `run_01` se interrumpió por coste de búsqueda: sus salidas parciales no son resultados válidos. La validación final (`validation.json`) rehasheó 31 entradas sin cambios y reconcilió las seis particiones espaciales. No se ejecutó la suite funcional porque no se cambió producción; se ejecutaron comparaciones reales y Ruff sobre los scripts nuevos.

Limitaciones: no inspección visual; no comparación con Catastro vivo; no control temporal común entre fuentes; no revisión humana individual de todos los conflictos. Las distribuciones y ejemplos no son datos sintéticos. El catálogo de todos los snapshots no autoriza sumarlos: hay replays y versiones. No se deduplica por geometría ni se transforma relación espacial en documental. El enlace documental original tampoco se convierte aquí automáticamente en confirmación física: exige calidad de identidad, unicidad y revisión de discordancias.

## 10. Decisión estratégica — respuestas obligatorias

**1. ¿Datos suficientes para fichas realmente útiles de edificios físicos?** Para fichas útiles de objetos catastrales y parcelas, sí: 124.395 Building Madrid y 48.820 piloto con atributos propios, más CEEE/PRTR de la tabla. Para afirmar fichas físicas enriquecidas, todavía no: cero CEEE confirmado a BU, cero pares temporales físicos y ningún nivel 3 físico acreditado. El enlace GML CP es una base recuperable, no identidad de portal/vivienda/edificio real.

**2. ¿Por qué muestran poca información?** El 85,33% del BU piloto son partes sin los cinco atributos proyectados; sus plantas/altura se omitieron. Las CP piloto no consultan BU por diseño; los BU no consultan CP sin acreditación. Además 43.478 CP piloto no tienen CEEE ni PRTR observado y conservación no está integrada allí. Reducir todo a «no disponible» oculta estas causas diferentes.

**3. ¿Se perdió información?** Sí en los productos consultables: enlaces CP/AD de todos los objetos, superficie de 48.835 Building piloto originales y 124.396 Madrid, plantas/altura de 283.954 partes piloto originales; Madrid omite 811.691 partes completas. No se observan alteraciones en los cinco campos ya procesados (cero discrepancias), y los bytes originales siguen locales. Recuperable no significa ya validado ni vigente.

**4. ¿Qué es reutilizable?** Las 54.441 CP piloto aceptadas, los 332.746 BU piloto y 124.395 Madrid utilizables, con límites y procedencia; las evidencias CP confirmadas y expedientes únicos, sin sumar importes por enlace. Las cuarentenas y XML también son reutilizables para investigación, nunca como entidades aceptadas. Los 324.772 enlaces documentales piloto a CP aceptada son material de reconciliación; 1.182 discordancias impiden activación ciega.

**5. ¿Principal cuello de botella?** El modelo y la ETL entre objeto, parte, parcela y evidencia: enlace documental existente descartado/no proyectado y atributos omitidos. No falta principalmente un nuevo mapa ni un matcher espacial. También persisten límites de identidad física y cobertura que la ETL sola no resolverá.

**6. ¿Tres actuaciones de mayor impacto y menor esfuerzo?** (i) Proyectar desde XML local plantas/altura/superficie/condición y enlaces CP/AD, con nulos/ceros/unidades; impacto directo en 283.926 partes piloto hoy N0. (ii) Reconciliar los enlaces documentales contra CP completa, separando cuarentena y 1.182 discordancias; habilitar primero solo el subconjunto revisado, sin heredar certificados como atributos BU. (iii) Aclarar estados de consulta y mostrar procedencia/alcance con los lectores existentes: 60 positivos recuperan sus IDs sin discrepancias, por lo que no hace falta otra adquisición para hacer visible lo ya integrado. Son propuestas para otra sesión, no cambios realizados.

**7. ¿Qué dejar de desarrollar temporalmente?** Nuevos filtros, capas, componentes y rediseños; rankings o diagnósticos de edificios físicos; emparejamiento geométrico definitivo; comparación temporal antes/después y atribución de obras a concesiones. No hay identidad física ni pares temporales que los respalden. Mantener consulta y trazabilidad existentes.

**8. ¿Qué conseguir sin datos nuevos?** Recuperar atributos constructivos omitidos y los 811.691 BuildingPart Madrid a un producto nuevo auditado; investigar 15.697 OtherConstruction Madrid y 5.491 piloto sin llamarlos edificios; producir una tabla revisable de vínculos documentales con motivos de aceptación/rechazo; mejorar la información de las partes piloto y explicar estados vacíos. Ya se pueden listar 75.678 objetos Building residenciales Madrid y 11.001 piloto con año inicial interpretable anterior a 1980, y consultar evidencias CP existentes. Todo ello mantiene sin resolver identidad física, exhaustividad y estado actual; ninguna recuperación autoriza atribuir a BU un certificado individual o una concesión de parcela.
