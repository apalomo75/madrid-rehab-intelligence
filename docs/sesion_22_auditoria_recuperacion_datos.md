# Sesión 22 — Auditoría y recuperación de datos

Auditoría local offline, 10 de noviembre de 2026. Se conservan todos los cambios pendientes de sesiones anteriores. No hay descargas, consultas externas, commits, push, publicaciones ni modificaciones de originales o snapshots históricos.

## Resultado comercial

**193.797 versiones postales de Madrid ganan al menos un campo en la ficha**, correspondientes a 193.797 accesos NDP distintos y 119.806 CP distintas alcanzables desde esas entradas. Son poblaciones diferentes: no se suman. El recuento se limita a los campos medidos en la comparación; no añade fichas por aclaraciones de dirección/NDP en antecedentes. La superficie bruta catastral llega a 193.091 versiones; otras 706 ganan detalle energético sin nueva superficie constructiva.

**No se ha reducido el número de fichas casi vacías: 18.691 de 214.083 versiones postales (8,73%), antes y después.** Las 195.392 restantes (91,27%) tienen al menos un atributo constructivo o evidencia documental utilizable. Esto no significa que todas tengan información suficiente para decidir una rehabilitación. La mejora en profundidad es real, pero no aumenta la población que ya disponía de alguna evidencia.

En Madrid, sobre las 140.379 CP aceptadas de la captura, 124.627 ganan algún campo; 124.310 ganan superficie bruta. En los cinco pilotos otras 47.650 CP ganan campos antes conservados pero omitidos del modelo comercial. Los pilotos siguen sin buscador postal fiable. No se han incorporado nuevas relaciones CP–BU, certificados, expedientes ni inspecciones.

Artefactos principales en `reports/session_22_data_recovery/`:

- `baseline_coverage.json`, `final_coverage.json`: numeradores, denominadores, unidad, método, ámbito, límites y hashes de población/entradas.
- `coverage_comparison.csv`: comparación por municipio, campo y población; denominadores y hashes idénticos.
- `improvements.json`, `commercial_impact.json`: unión de entidades que ganan campos, sin sumar coberturas solapadas.
- `*_coverage_*.parquet`: máscaras individuales reproducibles, sin geometrías.
- `baseline_coverage_sample.csv`, `final_coverage_sample.csv`: misma muestra postal, idéntica byte a byte.
- `raw_cases.json`: declaraciones XML de los objetos de Moncloa, con miembro GML, ordinal, valores originales, estados y enlaces.
- `sources_01/source_audit.json`: auditorías exhaustivas de energía, enlaces PRTR y particiones administrativas; `integrity.json` acredita hashes.
- `real_validation_final/`: 16 casos reales comprobados con los lectores/modelo finales, tablas seleccionadas y `case_traceability.csv`.
- `original_admin_case_checks.json`: contraste exacto de ambos antecedentes de Moncloa con las filas de CSV originales.
- `performance_before.json`, `performance_after_final.json`: mismo benchmark anterior/posterior.
- Logs focalizados y `full_tests.log`: resultados de validación, separados de los intentos interrumpidos.

De las 18.691 versiones casi vacías, 7.101 no tienen puente postal confirmable (6.371 sin vínculo y 730 ambiguas), y **11.590 tienen CP confirmada pero no evidencia adicional utilizable**. Otras 2.301 versiones tienen alguna evidencia aunque carezcan de superficie constructiva. Los campos más ausentes siguen siendo plantas y resultados de inspección (214.083 versiones cada uno), PRTR (202.995), conservación (198.955) y CEEE (114.728); son ausencias en nuestras fuentes, no eventos inexistentes.

## Método y denominadores

El censo de Madrid parte exclusivamente del índice SQLite postal de sesión 20: **214.083 versiones, 213.685 NDP distintos, 206.982 versiones confirmadas a CP, 6.371 sin vínculo y 730 ambiguas**. Se conservan también las versiones que no se pueden abrir; no se mejora el porcentaje eliminándolas.

Se mide por separado CP aceptada única, versión postal y NDP. La disponibilidad por CP significa «existe al menos un valor en un objeto documental relacionado», nunca «ese valor caracteriza todo el portal». Por versión con varias CP se usa unión lógica de disponibilidad, sin sumar atributos ni certificados. Por NDP se agrupan sus versiones, conservando el denominador inicial. El código coteja BU Madrid con el distrito de la CP, reproduciendo el lector histórico: no basta que un BU aparezca en cualquier partición.

«Útil» significa al menos un uso, año interpretable, superficie, viviendas, plantas, unidades o condición declarados, CEEE utilizable, concesión confirmada o antecedente administrativo confirmado. Incluye el cero declarado como valor; no implica viviendas positivas, deficiencia, diagnóstico, vigencia ni oportunidad comercial. «Casi vacía» significa identificación/dirección sin ninguna de esas evidencias. Se distinguen los antecedentes de conservación propiamente dichos de licencias y declaraciones responsables.

Muestra residencial potencial: se excluyen versiones con alguna CP vinculada cuyos usos conocidos sean exclusivamente no residenciales; se retienen usos desconocidos y direcciones sin vínculo. Universo elegible: **192.689 versiones**. Selección reproducible: primeras 300 por SHA-256 de `session22:<id>`, desempate por ID. No es una muestra de viviendas acreditadas ni garantiza representatividad estadística de los edificios físicos. **273/300 tienen alguna evidencia (91%); 27/300 siguen casi vacías (9%)**. La superficie pasa de 0 a 267/300. La muestra sirve para inspección reproducible; los porcentajes censales anteriores no se extrapolan de ella.

Los porcentajes son disponibilidad dentro de capturas congeladas, no exhaustividad territorial. Conservación, inspecciones y direcciones de los pilotos constan como **fuente no integrada**, con porcentaje no evaluable: el numerador cero de disponibilidad no es una tasa cero de eventos. En Madrid hay cero resultados efectivos de inspección integrados, no evidencia de ausencia de inspecciones reales.

La línea base reproduce explícitamente las reglas S21 anteriores a la recuperación. Los borradores `draft_baseline*` no son resultados de comparación: se corrigieron el alcance distrital del lector, el marcador de resultado `unknown` y el filtro municipal/calidad PRTR, y se añadieron las columnas nuevas inicialmente no expuestas. Los dos JSON finales usan las mismas reglas y poblaciones. El cambio de 18.689 del primer diagnóstico a **18.691** es una corrección de medición previa, no un empeoramiento provocado por la recuperación.

## Casos concretos: trazabilidad campo por campo

### Avenida de América 113 A — CP 8781605VK4788B

La CP está aceptada y asignada al distrito 21; hay un acceso documental. La revisión de **todos los miembros GML de Building, BuildingPart y OtherConstruction** encuentra **cero ocurrencias de la referencia** —incluidos enlaces de objetos cuyo ID pudiera ser diferente—. El producto histórico tampoco contiene un Building con esa CP. El lector devuelve correctamente cero construcciones.

| Campo | Original local / producto | Lector y ficha final | Diagnóstico |
| --- | --- | --- | --- |
| Dirección y CP | Versión S20 confirmada; CP original capturada el 22/10/2026, fecha de fuente 21/08/2026 | Identidad conservada; un acceso | No demuestra identidad física o actualidad |
| Uso | Sin objeto BU documentado en esta captura para esa referencia | No disponible | Ausencia de evidencia, no pérdida del campo por lector |
| Año | Sin BU relacionado | No disponible | No inferir por barrio, dirección o edificios vecinos |
| Superficie constructiva | Sin Building/parte con enlace a esta CP | No disponible | El área geométrica de parcela no sustituye superficie construida |
| Viviendas / unidades | Sin BU relacionado | No disponibles | No derivar viviendas del número de accesos |
| Plantas | Sin BuildingPart con esa referencia en el GML | No disponibles | La integración general de partes tampoco resolvería este caso con esta captura |
| CEEE | Cero vínculos en el producto energético para la CP | Ninguno asociado | No significa que el registro actual no tenga certificados |
| PRTR | Cero vínculos para la CP en productos actuales | Sin concesión vinculada | Sin inventar vínculos por dirección |
| Antecedentes / ITE / IEE | Cero eventos relacionados | Sin antecedentes integrados; sin resultado de inspección | No equivale a ausencia de actuaciones |

**Este caso no mejora.** No existe un atributo recuperable del Building correspondiente en los archivos locales revisados. Hace falta una consulta/fuente oficial catastral adicional que resuelva documentalmente esa referencia y su temporalidad; no se puede afirmar si la ausencia responde a actualización, segregación, omisión del suministro u otra causa.

### Avenida de la Moncloa 14 — CP 9377401VK3797G

| Campo | Registro original y trazabilidad | Antes → después | Ámbito |
| --- | --- | --- | --- |
| Uso | `ES.SDGC.BU.9377401VK3797G`: `1_residential` | Residencial → igual | Building asociado a CP |
| Año | Inicio y fin `1978-01-01T00:00:00` | 1978 → igual | Año declarado por objeto; no comprobación física |
| Viviendas | `numberOfDwellings=14` | 14 → igual | No viviendas del portal acreditadas |
| Unidades | `numberOfBuildingUnits=16` | Omitidas → 16 | No equivalen a 16 viviendas |
| Superficie | `officialArea/OfficialArea/value=5346`, unidad `m2`, referencia `grossFloorArea` | No disponible → **5.346 m²** | Superficie bruta del Building, sin sumar partes |
| Condición | `conditionOfConstruction=functional` | Omitida → visible con ámbito catastral | No es resultado de inspección actual |
| Plantas del Building | Elementos sin valor declarado | No disponibles → igual | No completar desde las partes |
| Partes | 9 objetos `..._part1` a `..._part9`; plantas sobre: 5,6,2,2,4,4,5,1,1; bajo: 2,2,2,2,2,0,2,2,2 | Fuera del producto Madrid → siguen fuera de la ficha | Evidencia original auditada; no son nueve edificios ni plantas globales |
| OtherConstruction | `..._PI.14797`, sin los atributos constructivos anteriores | No incorporado | No sustituye Building |
| CEEE 2025 | Registro `10/084960.9/25`, RC20 `9377401VK3797G0007FQ`, fila 92.721 de captura 2025 | E/E → E/E y detalle cuantitativo | Vivienda individual: Moncloa 14, esc. A, 3.º derecha |
| CEEE 2026 | Registro `10/084007.9/26`, RC20 `9377401VK3797G0014KT`, fila 50.846 de captura 2026 | E/E → E/E y detalle cuantitativo | Vivienda individual: **Moncloa 16, 3.º izquierda** |
| Concesión PRTR | Sin expediente vinculado | Ninguna → igual | No convertir otro antecedente en ayuda |
| Declaración | `350/2025/30096`, alta 30/09/2025, NDP `20017066`; CSV línea 68.149 | Visible → además expediente, dirección y NDP | **Santiago Rusiñol 13**, otro acceso de esta CP |
| Licencia | `350/2024/35844`, resolución «Conceder», 22/01/2025, NDP `20017052`; CSV línea 243 | Visible → además expediente, dirección y NDP | Moncloa 14; no acredita obra ejecutada |
| Accesos | Cinco NDP documentales relacionados con la CP | Cinco → igual | No cinco edificios o comunidades |
| Resultado ITE/IEE | No integrado | No disponible → igual | Obligación/licencia no es resultado |

Ambos contenidos energéticos originales se conservan celda por celda en Parquet. El primero declara consumo **184,97**, emisiones **38,76**, superficie certificada **151,40**; el segundo **169,11**, **34,65** y **173,00**, respectivamente. Fechas declaradas: 03/02/2025 y 02/02/2026. Las unidades de estas magnitudes están **sin verificar en el esquema local** y se muestran así; no se presupone kWh/m² ni se suma la superficie de viviendas. Ambos certificados siguen siendo de viviendas individuales; no existe una letra global atribuible al edificio ni vigencia comprobada.

El Building aparece en el miembro `A.ES.SDGC.BU.28900.building.gml`, ordinal 113.826. `raw_cases.json` conserva las declaraciones XML, incluso nulos y enlaces, de los once objetos encontrados. Las tablas JSON y CSV de `real_validation_final/` permiten contrastar los valores que llegan al modelo final.

### Evidencia adicional pendiente: Moncloa 14 y 16

La revisión textual local de direcciones encuentra además la fila 257 del XLSX oficial `300377-9-conservacion-rehabilitacion.xlsx`, SHA-256 `160b2990e54ef9560d85bad3ef36bd9edfd43ea1238661e44c82f471c361befe`. Declara orden ordinal **256**, septiembre de 2026, «AVENIDA MONCLOA 14 Y 16», motivo «OBRAS DE REPARACIÓN». El contraste inerte del XLSX original confirma todos los campos de `raw_json`. La numeración es ordinal de publicación, no un ID global de expediente.

Evento `595e9f541a269765236e08575774afbaa706523969835de867ee1631de89bed9`, estado **unmatched**, sin RC/NDP ni resultado de inspección. Se preserva en `moncloa_unmatched_order.json` y `unlinked_case_review.json`. No se incorpora como antecedente confirmado: el matcher actual no resuelve direcciones múltiples y no se introduce una excepción manual de identidad durante el cierre. Hace falta revisar una regla documental para direcciones enumeradas/rangos, con todas sus versiones y accesos, generar un derivado administrativo auditado y validar el conjunto. No es evidencia de reparación ejecutada o subsanación.

La búsqueda textual no es un matcher: también encuentra «Golondrina (Moncloa) 14» con otra CP y «Ronda Hispano-Americana 113», en Nuevo Baztán, con RC20 distinta. Se rechazan para estos casos; no aumenta su cobertura. No se encuentra otro CEEE textual de Avenida de América 113 en Madrid ni concesión o evento para esa dirección en los productos locales examinados.

## Cobertura anterior y posterior

### Madrid: versiones postales (denominador fijo 214.083)

| Dato disponible en la ficha | Antes | Después | Cobertura final |
| --- | ---: | ---: | ---: |
| Dirección | 214.083 | 214.083 | 100% |
| CP confirmada | 206.982 | 206.982 | 96,68% |
| Uso por objeto | 192.695 | 192.695 | 90,01% |
| Año por objeto | 192.814 | 192.814 | 90,07% |
| Superficie bruta de Building | 0 | **193.091** | **90,19%** |
| Viviendas por objeto | 193.091 | 193.091 | 90,19% |
| Plantas | 0 | 0 | 0% |
| Unidades por objeto | 0 | **193.091** | 90,19% |
| Condición catastral interpretada | 0 | **192.826** | 90,07% |
| CEEE utilizable | 99.355 | 99.355 | 46,41% |
| Magnitudes de consumo/emisiones de CEEE | 0 | **99.355** | 46,41% |
| Superficie de la unidad certificada | 0 | **99.348** | 46,41% |
| Concesión PRTR | 11.088 | 11.088 | 5,18% |
| Antecedente administrativo | 93.997 | 93.997 | 43,91% |
| Orden/obligación de conservación | 15.128 | 15.128 | 7,07% |
| Resultado efectivo de inspección | 0 | 0 | 0% disponible en captura |
| Al menos una evidencia útil | 195.392 | 195.392 | 91,27% |
| Casi vacía | 18.691 | 18.691 | 8,73% |

Los porcentajes y diferencias exactos, sin redondeo editorial, están en el CSV. Los nuevos campos de unidades, condición y energía son **recuperación de exposición del modelo**, no nuevos datos de origen o vínculos. La superficie Madrid sí es recuperación de una proyección ETL omitida.

### CP aceptadas: seis municipios

| Municipio | Denominador CP | Ganan algún campo | Con alguna evidencia antes = después | Casi vacías antes = después | Superficie antes → después |
| --- | ---: | ---: | ---: | ---: | ---: |
| Madrid | 140.379 | 124.627 | 125.463 (89,37%) | 14.916 | 0 → 124.310 |
| Getafe | 16.149 | 14.873 | 14.990 (92,82%) | 1.159 | 14.665 → 14.665 |
| Móstoles | 8.980 | 8.001 | 8.021 (89,32%) | 959 | 7.877 → 7.877 |
| Leganés | 10.541 | 8.234 | 8.264 (78,40%) | 2.277 | 8.194 → 8.194 |
| Alcorcón | 5.734 | 4.689 | 4.740 (82,66%) | 994 | 4.602 → 4.602 |
| Alcalá de Henares | 13.037 | 11.853 | 12.028 (92,26%) | 1.009 | 11.627 → 11.627 |

Las CP con superficies no equivalen a número de Building, BuildingPart o edificios físicos. El producto Madrid recupera 124.316 Building aceptados; 124.310 CP llegan al lector distrital comercial. La diferencia se debe al alcance del índice histórico de mapa/distrito, que se mantiene sin reconstrucción. No se utilizan sus seis registros adicionales para inflar cobertura de la ficha.

En pilotos solo se consultan relaciones A y `relation_validated`; las 12.135 B y 6.990 C de S18 permanecen incidencias, sin promoción. El conjunto S18 conserva 48.820 Building y 283.926 BuildingPart aceptados. Las superficies de Building ya se mostraban; ahora llegan también unidades/condición y magnitudes de certificados. No se suman las superficies de Building y partes ni se heredan uso, viviendas o año del supuesto padre.

## Flujo de datos y correcciones

| Campo / etapa | Hallazgo | Acción segura |
| --- | --- | --- |
| Uso/año/viviendas Madrid | Conservados en BU histórico, proyectados al índice y al lector | Sin nueva coincidencia ni modificación de valores |
| Superficie Madrid | GML declara `grossFloorArea`; no hay columna en el producto histórico | Producto lateral nuevo por el mismo ID Building y referencia CP explícita |
| Condición Madrid | GML conservado localmente, omisión ETL | Recuperada con estado y evidencia XML; «-» queda sin interpretar |
| Unidades | Ya estaban en Parquet/lector pero no en modelo | Se muestran por objeto, distintas de viviendas |
| Superficie/plantas piloto | Ya recuperadas en S18 y disponibles en lector S19 | Conservadas; no reconstrucción de GML piloto |
| Plantas Madrid | El Building no las declara; están en 811.691 partes ausentes del histórico | Se documenta el bloqueo; no ingestión apresurada de todo Madrid |
| Magnitudes CEEE | Parquet conserva valores y estados; lector/modelo omitían parte del detalle | Exponer solo estado `observed`, con ámbito/unidades originales |
| Dirección CEEE | Conservada pero omitida en resumen comercial | Registro, dirección y tipo original visibles por certificado |
| Antecedentes | La ficha mostraba el evento pero no el acceso de origen | Añadir expediente, dirección y NDP originales dentro del antecedente |
| PRTR / particiones de conservación | No se observa pérdida de IDs entre master, enlaces y particiones | Mantener estados/ámbitos; sin aumentar vínculos |

`madrid_recovery.py` crea `data/processed/cadastre/session_22_madrid_01/` con manifiesto versionado, hashes de ZIP, CP y BU históricos y productos de salida. Identidad única del Building, geometría ya utilizable en el histórico, CP aceptada única, enlace original `cadastralParcels` y `externalReference` deben coincidir exactamente. Se excluyen 80 registros originales no elegibles; no se elige entre versiones.

El lector solo complementa filas que **ya devuelve el lector autenticado histórico**. No agrega un BU a una ficha vacía. Verifica el producto y su compatibilidad con CP/BU históricos, además del manifiesto municipal activo; un override incompatible bloquea la recuperación. No carga GML al abrir una dirección. La tabla lateral ocupa aproximadamente 13 MiB, ordenada por CP/ID y con grupos de filas para filtros selectivos. Los atributos conservan estado, evidencia XML, miembro, ordinal y hash del ZIP. El hash de código del manifiesto corresponde al generador ejecutado antes del ajuste/formato posterior del lector; la transformación de extracción no cambió y el producto no se regeneró.

La condición es una declaración histórica catastral, no una inspección. No se reparan años inválidos ni se convierten unidades en viviendas. Las recomendaciones y las protecciones públicas existentes continúan vigentes.

## Energía: alcance y falsos negativos

Contraste exhaustivo de los **86 campos originales** de ambas capturas con `energy_source_records.parquet`, y de sus IDs de contenido: todas las celdas coinciden.

- 236.173 ocurrencias originales: 110.650 de captura 2025 y 125.523 de captura 2026.
- 236.134 contenidos canónicos; 39 ocurrencias exactas adicionales. Cero IDs canónicos duplicados.
- 233.166 contenidos con alguna referencia de formato válido. No equivale a checksum contrastado ni CP integrada.
- Nivel A: 136.742 contenidos distintos; D: 155; E: 99.237. Son IDs distintos por nivel, no filas de referencia.
- 136.735 contenidos son utilizables comercialmente tras identidad única y fecha no posterior a captura; **99.399 quedan fuera de ese conjunto**.
- 192.202 de vivienda individual; 30.929 de edificio completo declarado; 12.659 de local; 344 desconocidos. Sin atribución de vivienda a edificio.
- 26 contenidos con identidad conflictiva en 12 números de registro, uno insuficiente. No se selecciona versión «vigente» por fecha. Cero pares físicos temporales verificados.
- 37 filas candidatas tienen CP aceptada pero siguen D por referencias múltiples o mixtas. Son falsos negativos **potenciales**, no confirmaciones recuperables automáticamente. Se conservan en `ceee_false_negative_review.csv`.
- Cero asociaciones confirmadas solo por dirección; no se introduce normalización nueva que cambie identidad.
- Cero IDs/vínculos perdidos entre enlaces y particiones de certificados de los seis municipios.
- Estados de magnitudes preservados: consumo observado 236.032, emisiones 236.033, superficie 236.049; los faltantes o sospechosos no se convierten en valores utilizables.

La captura fue el **22/10/2026**; los archivos declaran Last-Modified 27/02/2026 (2025) y 05/10/2026 (2026). Las fechas de certificado van de 24/05/2013 a 24/07/2027: el máximo es una anomalía futura conocida, excluida del uso comercial. El nombre del archivo no acredita exhaustividad anual. Necesitamos revisar actualización del registro y semántica/unidades antes de afirmar vigencia o calcular ahorros.

Se conservan en Parquet equipos, combustible, demanda, normativa, año y otros campos energéticos. Parte contiene marcadores como `99999999.99`; no se añade una interpretación comercial general de esos equipos sin contrato de unidades/valores ausentes. No se pierden en el ETL actual: quedan en el detalle fuente para una integración posterior validada.

## PRTR y conservación

PRTR: 7.532 expedientes únicos, cero duplicados de expediente; todos en etapa original «APROBACIÓN CONCESIÓN». **5.046 tienen alguna CP confirmada**, en 5.072 pertenencias expediente–CP; 2.486 no tienen CP confirmada. Los estados no son sumables por expediente: 1.241 con `confirmed`, 3.805 históricos Madrid confirmados, tres ambiguos regionales, tres ambiguos históricos, uno contradictorio, 2.477 sin cobertura CP y uno CP no utilizable. Cero IDs de enlace ausentes del master. No hay fechas individuales contrastadas de concesión o pago en estas columnas; **ningún pago u obra ejecutada queda acreditado por estos productos**. Las cantidades pertenecen al expediente único y no se multiplican por CP. Los candidatos espaciales no se promueven.

Conservación: 124.175 eventos/IDs/versiones únicos, cero filas de versión duplicada. Confirmados 112.783; contradictorios 5.711; sin enlace 5.497; ambiguos 148; candidatos 36. **101.764 eventos confirmados disponen de NDP**; obligaciones y algunas órdenes se vinculan por otros puentes documentales, no se inventa un NDP.

| Categoría | Total | Confirmada |
| --- | ---: | ---: |
| Declaración responsable | 98.032 | 91.300 |
| Licencia | 11.498 | 10.464 |
| Obligación IEE | 5.758 | 5.299 |
| Obligación ITE | 4.952 | 4.629 |
| Orden | 3.935 | 1.091 |

Todos tienen `inspection_outcome=unknown`: **cero resultados efectivos ITE/IEE**. Cero eventos confirmados perdidos entre master y particiones usadas por la ficha. Todas las cinco categorías se muestran conservando su significado; los resultados REC reales no están integrados. Los 207.648 vínculos de versiones de acceso confirmados, 736 ambiguos, 116 candidatos y 7.561 sin vínculo no equivalen a esos eventos ni al número de NDP distintos.

## Validación, rendimiento e interrupciones

Se valida con registros reales América, Moncloa, CP con CEEE, PRTR, conservación, vacía, Getafe con 1.014 objetos A, otro ejemplo de cada piloto y cinco parcelas con relaciones B/C. Las tablas del lector deben coincidir con el conjunto A validado, sin promocionar incidencias. Moncloa conserva plantas nulas en el modelo aunque existan partes en el original; energía, ayudas y antecedentes no se trasladan a BU.

La regresión de magnitudes energéticas fallaba antes del cambio (`regression_before.log`) y pasa después. Se comprueban también identidad CP incompatible, override municipal incompatible, nulos, datos de otra CP y fuentes no cubiertas. El resto de pruebas existentes verifica navegación postal, CP→BU→CP y privacidad.

Pasaron 6 pruebas específicas, 14 comerciales, 16 postales y 7 S19. Ruff global, formato de seis archivos y `git diff --check` son correctos. El resultado de la **única suite general de esta sesión** se consigna en el cierre de validación al final del documento.

Benchmark de seis casos, mismo guion y entradas: mediana recuperación+modelo **250,4 → 290,4 ms**; repetición **58,2 → 71,2 ms**. Hay un coste medible de aproximadamente 40 ms iniciales y 13 ms repetidos; no se afirma rendimiento idéntico. Bailén pasa 212,9→303,6 ms inicialmente; Getafe exigente 446,3→494,6 ms. Instrumentación, cachés y concurrencia varían; son medidas Python locales, no pintura de navegador ni un ensayo controlado. No se descarga ni ejecuta navegador: **sin validación visual nueva**, y AppTest no la sustituye.

Antes de la interrupción se observaron códigos **143 (SIGTERM)** en el intento inicial de cobertura final, otro intento de baseline y el benchmark posterior inicial. No hay causa de terminación acreditada. La cadena de pruebas postal/S19 quedó incompleta: el log postal no tenía cierre y S19 no llegó a iniciarse. No se cuenta ninguno como éxito. Los intentos reemplazados conservan sus logs; las extracciones GML, baseline/censo final de liberación y auditoría de fuentes con integridad sí habían terminado. Tras retomar se verificaron sus artefactos y se completaron únicamente validación de lectores/casos, benchmark y pruebas pendientes. No se repitió la extracción ni el censo de fuentes.

## Fuentes necesarias y prioridades

No se investigan ni adquieren fuentes externas en esta sesión.

| Prioridad / clase | Campo y municipios | Por qué no basta lo actual | Fuente y esquema mínimo / vínculo | Beneficio y riesgo |
| --- | --- | --- | --- | --- |
| P1 A — Catastro | Uso, año, superficie, viviendas y plantas en CP vacías, especialmente América; seis municipios | El suministro local no contiene BU para algunas CP; partes Madrid no integradas | Servicio oficial no protegido o nuevo suministro con RC14/RC20, ID BU/parte, relaciones explícitas, tipo, campos/unidades, estado y fechas; consulta documental de RC exacta | Rescatar vacíos reales; no identificar portal/edificio por proximidad. Comprobar acceso, actualización, licencia y límites de consulta |
| P1 A — Partes locales Madrid | Plantas por parte | Ya hay GML local, faltan aceptación integral, geometría, municipio y contrato/índice | No exige fuente nueva: pipeline por lotes que preserve ID, CP explícita, CRS, evidencia y cuarentena; no suponer padre por sufijo | Mejora plantas de partes; no dará uso/año a América ni plantas globales. Validación amplia pendiente, no arreglo apresurado |
| P1 C — Ayuntamiento Madrid / Comunidad | Resultado real ITE/IEE y subsanación; primero Madrid, después pilotos | Solo obligaciones, órdenes y contextos; no actas REC reales | Actas/dictámenes oficiales autorizados: ID inspección/expediente, fecha, resultado, versión, unidad/ámbito, RC/NDP y puente acreditado, subsanación separada | Evidencia de conservación de mayor valor; riesgo de confundir plazo, licencia, archivo o sanción con estado físico. Verificar acceso/permiso y redistribución antes de lotes |
| P2 B — Registro CEEE Comunidad de Madrid | Actualidad, unidades, tipo y referencias incompletas; seis municipios | Corte 22/10/2026, unidades no verificadas, ámbitos parciales/conflictos | Captura actualizada y diccionario oficial: registro, RC20, fecha/semántica, ámbito, unidades, magnitudes, estados, anulación/versiones y licencia | Mejor evidencia energética; no certificado de vivienda como edificio ni antigüedad como vigencia. Confirmar actualización y vigencia de licencia CC BY catalogada |
| P2 D — Plan Rehabilita y otras ayudas oficiales | Concesión, pago, justificación y obra ejecutada, Madrid/pilotos | PRTR solo concesiones; ningún pago/obra acreditado | Expediente estable, programa, RC/NDP y ámbito, importe por fase, resolución/fecha, estado, pago, ejecución/justificación separadas y versiones | Verificar actuación y compatibilidades; evitar multiplicar importes y confundir licencia/concesión con ejecución. Licencias/acceso pendientes |
| P2 E — Callejeros/portales oficiales piloto | Dirección y puente a CP en Getafe, Móstoles, Leganés, Alcorcón, Alcalá | Los enlaces AD existentes son URLs, no direcciones literales fiables | Identificador de acceso, versión/fecha, vía/tipo/número/calificador, municipio INE validado y puente documental RC/BU con calidad | Habilitar búsquedas piloto; evitar equiparar acceso, comunidad y edificio. Verificar catálogo, permisos, actualización y tratamiento de bajas/duplicados |
| P3 A/C — Ámbito físico | Portal–Building–BuildingPart y accesibilidad, seis municipios | Compartir CP o sufijo de ID no prueba padre o edificio físico | Relación oficial explícita de objetos/portales, identificadores persistentes y temporalidad; accesibilidad/ascensor por unidad acreditada | Evitar atribuciones indebidas y mejorar conversación comercial; acceso/licencia y granularidad por verificar |

Decisión comercial: medir profundidad y cobertura por separado, mostrar el acceso/unidad de cada evidencia, y priorizar resultados efectivos de inspección y resolución documental de las CP vacías. No construir una puntuación de oportunidad con ausencias o datos parciales. La aceptación de BuildingPart Madrid es una actuación futura de pipeline; la verificación catastral de América y los resultados ITE/IEE requieren evidencia adicional concreta.

## Reproducción

Sin dependencias nuevas. Instalación y servidor local: comandos generales de README/AGENTS. Las salidas deben ser nuevas; nunca reutilizar snapshots.

```bash
# Recuperación offline (NO repetir si el producto ya está validado)
PYTHONPATH=src .venv/bin/python -m madrid_rehab.madrid_recovery --output-dir data/processed/cadastre/replay_22_nuevo
# El lector usa el derivado canónico session_22_madrid_01; un replay no se activa automáticamente.

# Mismo directorio de informes nuevo; conservar estos nombres para comparación
PYTHONPATH=src .venv/bin/python -m madrid_rehab.data_recovery_audit --output reports/session_22_data_recovery/replay_nuevo/baseline_coverage.json
PYTHONPATH=src .venv/bin/python -m madrid_rehab.data_recovery_audit --final --output reports/session_22_data_recovery/replay_nuevo/final_coverage.json
# Crear previamente el directorio nuevo de informes; el censo no sobrescribe archivos.

# Auditoría de originales y de todos los enlaces/particiones (salida nueva)
PYTHONPATH=src .venv/bin/python tests/audit_data_recovery_sources.py --output-dir reports/session_22_data_recovery/source_replay_nuevo
# Solo casos/lectores: evita repetir extracción/censo de originales ya validados
PYTHONPATH=src .venv/bin/python tests/audit_data_recovery_sources.py --cases-only --output-dir reports/session_22_data_recovery/cases_replay_nuevo

PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_data_recovery.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_commercial_fiche.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_commercial_fiche.py --output reports/session_22_data_recovery/benchmark_nuevo.json
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Las métricas de baseline reconstruyen las reglas S21; no dependen de desactivar el lector actual. Las de final usan el derivado canónico y las reglas nuevas. No se ejecuta GML durante la consulta comercial, ni se asigna evidencia de CP a BU.

## Cierre de validación

**Suite general: 516 pruebas, OK, 627,190 segundos; una sola invocación, código de salida 0.** Artefactos: `full_tests.log`, `full_tests.exit` y `validation_summary.json`. No hubo cambios de código posteriores a esta ejecución; únicamente se cerraron informes y documentación. Las pruebas focalizadas pasaron antes de la suite. No se declara validación visual.

La preservación por hashes de las entradas registradas y del derivado está verificada en `preservation_final.json`: 162 parejas de métricas con iguales denominadores y hashes de población, y muestra idéntica byte a byte. Los originales y snapshots no se han alterado. Se conservan los cambios previos, los intentos interrumpidos y los productos históricos. Sin descargas, commits, push ni publicación.

**Entrega cuantitativa:** 193.797 versiones postales ganan campos medidos; 193.091 ganan superficie bruta catastral. 18.691 siguen casi vacías, sin reducción artificial del denominador ni nuevas atribuciones. América no mejora con estas fuentes; Moncloa gana superficie, unidades y detalle verificable de cada vivienda/antecedente, además de una orden candidata documentada que no se promueve a confirmada.
