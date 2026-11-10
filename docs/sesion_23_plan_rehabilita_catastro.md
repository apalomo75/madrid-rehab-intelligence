# Sesión 23 — Plan Rehabilita y viabilidad catastral

Sesión local del 10/11/2026. Se preservaron los cambios pendientes, los snapshots y los resultados S22. Sin commits, push ni publicación. No se volvió a descargar Plan Rehabilita. El único acceso de datos externo fue una muestra catastral acotada de ocho peticiones; no hay cliente de red en la ficha.

## Resultados

| Indicador | Resultado |
| --- | ---: |
| Expedientes únicos conservados | **2.085 / 2.085** |
| Filas originales preservadas, diez capas | **7.990** |
| Expedientes con dirección/acceso/CP confirmados, clase A | **1.977** |
| Expedientes candidatos o ambiguos, clase B | **103** |
| Expedientes sin correspondencia postal exacta, clase C | **5** |
| CP distintas con relación A | **1.919** |
| Versiones postales con nueva evidencia municipal | **3.194 / 214.083 (1,49%)** |
| Versiones casi vacías rescatadas por Plan Rehabilita | **0** |
| CP con atributos del prototipo catastral activados en producción | **0** |
| Versiones con alguna evidencia antes → después | **195.392 → 195.392 (91,27%)** |
| Versiones casi vacías antes → después | **18.691 → 18.691 (8,73%)** |

**La integración aumenta la profundidad de 3.194 fichas postales, pero no reduce las casi vacías.** No se ha modificado el denominador, promovido candidatos ni contado el prototipo como cobertura operativa.

«CP con ayuda» significa CP relacionada documentalmente con un expediente del conjunto municipal, no edificio físico ni beneficiario jurídico identificado. La fuente aporta importes revisados y componentes de subvención, pero no acredita aquí pagos, obras ejecutadas o necesidad actual de financiación.

## Preparación y preservación

Se revisaron AGENTS, documentos S19–S22, lectores y manifiestos CP/BU, índice postal S20, energía S13, PRTR regional, conservación S14 y recuperación S22. El árbol ya contenía cambios de sesiones anteriores: se conserva el estado inicial en `reports/session_23_plan_rehabilita/git_status_initial.txt`. No se revierten ni atribuyen a S23 esas modificaciones previas.

Los informes S22 se utilizan como referencia de solo lectura. En particular `final_coverage_postal.parquet`, `final_coverage.json` y el índice SQLite de 214.083 versiones. La ejecución no regenera S22 ni reconstruye GML histórico.

## Original localizado y procedencia

La carpeta indicada `/mnt/c/Users/apalo/Downloads/Mapas Rehab/` no contenía ZIP. Una búsqueda local por nombre en Downloads localizó:

- **Ruta original:** `/mnt/c/Users/apalo/Downloads/PLAN_REHABILITA.zip`.
- **Tamaño:** 712.277 bytes.
- **SHA-256:** `5c9ba32bb5871e5c0af2f7b15148373a694d635c8ca633a7e7d05e4bcaedd66b`.
- Copia exacta preservada una sola vez bajo `data/raw/plan_rehabilita/<SHA-256>/PLAN_REHABILITA.zip`.
- Diez capas Shapefile de puntos, DBF UTF-8, CRS ETRS89 / UTM 30N, **EPSG:25830**. Se validaron WKT, estructura DBF/SHP, número de registros y correspondencia de X/Y; el control CRC de todos los miembros del ZIP también pasa (`zip_integrity.json`).
- XML ESRI: creación/modificación 19/10/2026; no se confunde con captura original, fecha de concesión o actualización de cada expediente.

Las diez capas, los campos, tipos, longitudes, miembros, tamaños, CRC y XML completos están en `source_inventory.json`. La estructura, los 2.085 expedientes y los 233,05 millones coinciden con las señales de la auditoría previa; no se dispone de un hash previo independiente para afirmar igualdad binaria con aquella inspección.

**Licencia y fecha de captura originales no acreditadas.** No hay aviso de reutilización verificado en el ZIP; los XML contienen linaje de procesamiento y rutas locales, no una licencia de redistribución. Procedencia declarada: archivo facilitado por el usuario, atribuido al conjunto municipal. Se mantiene exclusivamente local y oculto con `MADRID_REHAB_PUBLIC=1`. La fecha de ingestión no se presenta como fecha de captura oficial.

## Auditoría de capas y campos

| Capa | Filas | Función documental en el ZIP |
| --- | ---: | --- |
| SUB_TOTAL_XY | 2.085 | Catálogo principal por NUMERO_EXP |
| SUB_AC_XY | 1.516 | Componente de accesibilidad |
| SUB_CON_XY | 287 | Componente de conservación |
| SUB_EE_XY | 568 | Componente energético |
| SUB_SA_XY | 264 | Componente de salubridad |
| IND_ASC_XY | 1.332 | Indicador de ascensores |
| IND_OTRAS_XY | 657 | Otras actuaciones de accesibilidad |
| ELI_AMI_XY | 203 | Indicador de amianto |
| IND_AH_ENER_XY | 539 | Indicadores energéticos |
| IND_AH_EMI_XY | 539 | Indicadores de emisiones |

No son diez poblaciones independientes de ayudas. Todos los IDs secundarios aparecen en la principal; no hay IDs duplicados en SUB_TOTAL, filas marcadas como eliminadas ni conflictos de dirección/distrito/convocatoria/viviendas/fechas entre capas. En este ZIP no hay expedientes con varias direcciones declaradas; el código conserva las filas originales y bloquea A si aparecen en otro suministro. Varias actuaciones/componentes sí pueden corresponder al mismo expediente.

Campos principales y tratamiento:

| Original | Interpretación y límite |
| --- | --- |
| NUMERO_EXP | Identificador de expediente municipal; distinto de expediente PRTR |
| DIRECCION / DISTRITO / ZONA | Dirección, distrito y zona declarados; la dirección es la entrada al puente postal |
| NUM_VIVIEN | Viviendas declaradas del ámbito del expediente; no viviendas verificadas del portal |
| X / Y y geometría SHP | Punto de localización de fuente; cero discrepancias X/Y >0,001 m; no identidad física ni confirmación espacial |
| TOT_PRES_P | Linaje XML: `tot_pres_protegible`; presupuesto protegible por expediente |
| SUB_AYTO_R | Linaje XML: `sub_ayto_revisada`; importe revisado del expediente, no pago |
| AC_SUBV_CO / CN_CIM_SUB / EE_SUBV_CO / SA_SUBV_CO | Componentes fuente con nombres de subvención concedida; no sumar con total revisado ni contar cada capa como expediente adicional |
| BOAM_C / BOCM_C | Campos de publicación; no se inventa fecha individual de concesión, solicitud o resolución |
| CONVOCATOR | REHABILITA 2020–2025 |
| FECHA_ACTU | Linaje XML: `fecha_actualizacion`; **30/08/2026 en los 2.085 registros** |
| Indicadores / SUPERFICIE / AHORRO_* | Conservados en source_rows y raw_json; no se convierten en mediciones independientes de obra ejecutada o ahorro real |

Importes DBF se validan con Decimal y céntimos exactos, sin reparar formatos locales ambiguos. Todos los importes principales son numéricos válidos. **SUB_AYTO_R suma 233.045.136,10 € una sola vez por expediente. En 2.042 casos no coincide con la suma de los cuatro componentes.** No se reconcilia suponiendo descuentos, fases o pagos: se documenta el desacuerdo y se conserva cada columna.

Las fechas BOAM_C van de 08/09/2021 a 04/08/2026; BOCM_C de 16/09/2021 a 04/08/2026. Convocatorias: 2020: 186; 2021: 548; 2022: 547; 2023: 347; 2024: 314; 2025: 143. Están presentes los 21 distritos. No hay columna de pago o estado de ejecución contrastado por expediente; no se usan fechas de publicación para fabricarlo.

## ETL y productos

Módulo `plan_rehabilita.py`, solo fuentes locales. Se implementó un lector estricto del subconjunto DBF y Shapefile Point presente, con stdlib y las dependencias ya fijadas; no se añadió una librería GIS ni se ejecutó código del ZIP. Se preservan nombres originales, cadenas originales, número físico de fila, capa, SHA del registro DBF y ZIP.

Snapshot canónico: `data/processed/plan_rehabilita/session_23_01/`.

- `cases.parquet`: 2.085 identidades únicas, campos normalizados, estados por campo y raw_json.
- `source_rows.parquet`: las 7.990 filas de todas las capas, incluidos los valores originales.
- `locations.parquet`: dirección, clase A/B/C, motivos, versiones postales/NDP y CP cuando existe confirmación.
- `actions.parquet`: categorías ligadas a componentes positivos del expediente, con campo e importe de origen; no componentes sumados al total.
- `finance.parquet`: presupuesto, total revisado y componentes por expediente, en céntimos y con estados.
- `quarantine.parquet`: incidencias de identidad o campos; **cero filas en este suministro**. No se eliminan silenciosamente registros.
- `manifest.json`: contrato, hashes, fuentes, original preservado y restricción pública.

Reproducción completa en `replay_23_01/`: **los seis hashes Parquet coinciden exactamente**. El generador ejecutado inicialmente se conserva en `reports/session_23_plan_rehabilita/etl_executed.py`, cuyo hash coincide con el manifiesto canónico. El replay usa el código mantenido después de formato/validaciones defensivas, con las mismas salidas reales. No se sobrescribió la primera versión.

## Relación documental

La confirmación exige conjuntamente:

1. Alias de vía documentado en el índice municipal S20, número y calificador exactos. Solo normalización ya utilizada por el buscador; no fuzzy matching ni eliminación arbitraria de partes del nombre.
2. Todas las versiones coincidentes confirmadas; un único identificador NDP y una única CP.
3. CP histórica utilizable y única, con distrito igual al declarado.
4. Dirección/distrito consistentes entre capas y expediente con identidad utilizable.

Las coordenadas no confirman ningún vínculo. No se escoge un portal de varios aunque compartan parcela. No se expande un rango o una dirección múltiple suponiendo que todos pertenezcan al expediente. Si existiera una dirección secundaria discordante, se conservaría y bloquearía A.

Resultado: **1.977 A (94,82%); 103 B; 5 C**. Dentro de B, **98 tienen acceso postal sin puente CP confirmado y 5 tienen identidad postal ambigua**. El motivo genérico de B en el producto agrupa identidad múltiple/incompleta; no significa que todos sean conflictos de parcelas. Los cinco C son Colonia Occidente 1, 2, 5, 6 y 7, sin correspondencia exacta en el índice.

1.977 expedientes → **1.919 CP**, porque distintas convocatorias/expedientes pueden compartir parcela. Por ejemplo `0892402VK4609D` tiene cuatro expedientes. No se deduplican por dirección, importe o proximidad temporal; se conservan sus identidades.

Granularidad contrastada (`identity_counts.json`): 2.085 expedientes, 2.059 literales de dirección originales distintos; los A se relacionan directamente con 1.953 NDP y 1.919 CP. La consulta por esas CP alcanza 3.194 versiones/NDP postales, incluidos otros accesos de parcela. **No se ha establecido un recuento de edificios físicos.**

Las 3.194 versiones postales con nueva evidencia incluyen otros accesos documentados de una CP; **no se afirma que cada portal sea beneficiario**. El ámbito mostrado es siempre el expediente relacionado con la parcela. Los candidatos no aparecen como subvención confirmada en la ficha.

## Ficha comercial y consulta municipal

`plan_rehabilita_store.py` verifica manifiesto y todos los productos, CP, índice postal y compatibilidad del manifiesto municipal activo. La consulta es selectiva por CP y expediente; las cachés se invalidan por firmas de archivo. Un override incompatible falla explícitamente. Nunca se atribuye a BU o a otro municipio.

La ficha mantiene secciones técnicas y navegación CP/BU. Dentro de Ayudas muestra separadamente:

- **PRTR · Comunidad de Madrid**: contratos y estados previos intactos.
- **Plan Rehabilita · Ayuntamiento de Madrid**: convocatoria, expediente, dirección original, categorías por componentes, viviendas del expediente, presupuesto, importe revisado, publicaciones, actualización, procedencia y estado individual no verificado.

No se suman importes entre CP, capas ni administraciones. No se infieren pago, obra ejecutada, necesidad o compatibilidad de financiación. No se añaden estas evidencias a la exportación HTML.

Nueva opción municipal sencilla en la navegación: **Plan Rehabilita · Ayuntamiento de Madrid**. Filtros de distrito, convocatoria y componente de actuación, tabla por expediente y mapa de puntos de expedientes con relación A, máximo 500 por carga. Selección de expediente y botón para abrir su CP con la ficha existente. Se distinguen casos confirmados y CP distintas; las filas B/C permanecen en el catálogo general con su estado, sin enlace confirmado a ficha. El punto es una localización de expediente, no un edificio.

Se verifica el bloqueo público tanto en lector como en la vista agregada. No se habilitan descargas públicas mientras falte licencia.

## Ejemplos verificables

| Ejemplo | Evidencia conservada |
| --- | --- |
| Avenida Entrevías 120, CP `3999706VK4639H` | Expediente `511/2025/24596`, REHABILITA 2025; importe revisado **105.008,85 €**, presupuesto **164.405,75 €**, 10 viviendas del expediente; componente AC 100.000 €, separado del revisado |
| CP `0892402VK4609D` | `135/2021/02608`, `135/2022/01285`, `135/2022/01296`, `511/2023/13459`; cuatro expedientes, no cuatro edificios |
| CP `0006718VK4800E` | Municipal `511/2024/37976`, junto a PRTR `10-PYL1-01460.2/2022` y `10-PRE1-01170.4/2022`; programas conservados por separado, posible solapamiento pendiente de contraste |
| Encomienda de Palacios 49 | `511/2025/24464` queda B: la dirección no tiene puente postal confirmado; no se usa el punto para asignar CP |
| Colonia Occidente 5 | `511/2024/38099` queda C; expediente conservado sin correspondencia exacta |
| América, CP `8781605VK4788B` | Sin Plan Rehabilita confirmado; continúa sin BU local. El prototipo oficial devuelve suelo y otra denominación postal, no atributos de un edificio |
| Moncloa, CP `9377401VK3797G` | Sin Plan Rehabilita confirmado; mantiene 5.346 m² del Building, 14 viviendas por objeto, 16 unidades y los dos CEEE individuales de S22. No se agrega el dato de una oficina al Building |

Los modelos finales, IDs, tablas y tiempos están en `real_cases_benchmark_final.json`.

## Bloque catastral

Se encontró y probó el servicio oficial no protegido WCF **Consulta_DNPRC**. Investigación web acotada: documentación oficial del servicio, esquema/ayuda y licencia; sin buscar datasets sustitutivos del ZIP ni hacer descargas masivas.

Ocho peticiones totales, cuatro RC14 y dos RC20 explícitas de control; dos RC14 se repitieron tras corregir un supuesto del parser. Se conservan seis respuestas originales válidas; el error inicial y la regresión están documentados. Muestra derivada de cuatro inmuebles, **no activada**: `data/processed/cadastre/session_23_nonprotected_sample_01/`.

América devuelve `8781605VK4788B0000AB`, uso «Obras de urbanización y jardineria, suelos sin edificar», superficie construida 0, sin antigüedad, y dirección **PS Alameda de Osuna 113(A) Suelo**. Esto aporta una explicación documental de la ausencia de BU, pero no prueba identidad con «Avenida de América 113 A». No se corrige automáticamente el puente municipal ni se usa el suelo para afirmar características de un edificio.

Moncloa devuelve 16 RC20; una consulta individual de control identifica una **oficina** de 145, año 1978, con oficina 119 y comunes 26, en planta 00. Es información propia del inmueble, no superficie, uso o plantas globales del Building. Bailén devuelve un inmueble comercial y Alberdi otro suelo sin construir. Los contadores de inmuebles no se convierten en viviendas.

La prueba demuestra acceso y datos nuevos de unidades; no estabilidad continuada, exhaustividad o permiso general de redistribución. **No se integra en producción**: cero CP o versiones postales rescatadas por este bloque. Véase `reports/session_23_plan_rehabilita/cadastral_source_feasibility.md` para fuentes oficiales, URLs, límites, esquema y plan posterior.

## Medición sobre S22

`coverage_before_after.csv` conserva las mismas 214.083 versiones y hash de población. `coverage_masks.parquet` conserva los IDs para comprobar uniones sin sumar recuentos solapados. No se modifica ningún artefacto de S22.

- Indicador A: 2.085 expedientes nuevos, 1.977 relacionados A, 1.919 CP, 3.194 versiones con evidencia municipal nueva, **cero casi vacías rescatadas**.
- Indicador B operativo: **cero CP y cero versiones** con atributos catastrales nuevos activados. La muestra de inmuebles queda exclusivamente en investigación.
- Indicador C: 195.392 útiles y 18.691 casi vacías antes y después; incremento de cobertura útil global **0 puntos**. Los campos constructivos, energía, PRTR, conservación e inspecciones conservan exactamente sus numeradores. La cobertura municipal nueva es 3.194/214.083 = **1,49 puntos**, sin confundirse con utilidad global.
- No se cuentan los 2.085 expedientes, 1.919 CP o 3.194 versiones como edificios. La población NDP y las versiones se mantienen separadas en el índice original.

## Validación y rendimiento

Pruebas focalizadas: 12 nuevas (parser DBF, importes y fechas, varias direcciones, identidad postal A/B/C, RC14→detalle RC20, separación de programas, integridad original/productos, ausencia de duplicación, privacidad/BU, S22, filtros y ficha real); más 14 comerciales, 6 S22, 16 postales y 7 S19. Reproducción ETL completa con hashes idénticos. Ruff global y formato de diez archivos correctos. La suite completa se ejecuta una sola vez al estabilizar código; su resultado queda en el cierre de validación.

Navegador: **BLOQUEADO**, falta Chromium en `/home/apalo/.cache/ms-playwright/chromium-1194/chrome-linux/chrome`. No se descarga. AppTest acredita ejecución/controles, no pintura visual, WebGL ni usabilidad del mapa.

El benchmark final mide primera consulta y repetición de fichas con cero, uno y varios expedientes municipales, y coexistencia con PRTR. Son tiempos de recuperación/modelo Python, no navegador; la primera consulta incluye validación de hashes. En la medición final, la mediana de recuperación/modelo es **266,1 ms** inicialmente y **39,2 ms** en repetición. El primer caso, con dos ayudas, tarda 1.277,5 ms incluyendo 868,6 ms de primera verificación municipal/postal; repetido tarda 39,2 ms. El caso de cuatro expedientes tarda 401,2/67,6 ms y el de municipal+PRTR 266,1/61,0 ms. La consulta municipal repetida añade 1,3–2,7 ms en estos cinco casos. No es un ensayo controlado antes/después ni garantía universal; incluye cachés, verificaciones y ejecución local, no navegador.

## Decisiones para sesión 24

1. **Prioridad de rescate:** revisar los 98 accesos sin puente y las cinco ambigüedades; resolver solo mediante evidencia oficial. Revisar Colonia Occidente con el callejero, sin geocodificar a CP por proximidad. Aun resueltos, no prometer que estén entre las casi vacías.
2. **América:** contrastar la versión postal municipal con el domicilio catastral y clasificarla como discrepancia por investigar. No rellenar una ficha de edificio con datos de un suelo.
3. **Vacíos:** estratificar suelo, referencias transformadas, direcciones discordantes y ausencia real de producto. No lanzar 18.691 consultas como si todas correspondieran a edificios.
4. **Catastro:** formalizar contratos RC14/finca, RC20/inmueble, unidades y BU; validar estabilidad/semántica/licencia antes de una ingestión acotada adicional o exposición de muestra.
5. **Plan Rehabilita:** obtener diccionario oficial, URL/procedencia y licencia verificadas; significado de importe revisado frente a componentes y estados individuales de resolución/pago/justificación. No inferir ejecución.
6. **Programas:** estudiar el solapamiento municipal–PRTR por identificadores documentales oficiales; no deduplicar por dirección, importe o programa.
7. **Mayor valor comercial:** resultados efectivos ITE/IEE y licencias pendientes siguen sin resolverse con estas ayudas; no convertir concesiones en diagnósticos.
8. Revisión visual conjunta con Chromium disponible, incluidos filtros, CP con varias ayudas y vuelta de CP/BU. No publicar hasta resolver derechos de los productos afectados.

## Comandos y límites de reproducción

Sin dependencias ni build nuevos. Instalación: `.venv/bin/python -m pip install -r requirements.lock`. Servidor Streamlit habitual de README/AGENTS. El ETL no hace red.

```bash
# Nueva salida y nuevo informe siempre; nunca sobrescribir el snapshot canónico
PYTHONPATH=src .venv/bin/python -m madrid_rehab.plan_rehabilita --input /ruta/PLAN_REHABILITA.zip --output-dir data/processed/plan_rehabilita/replay_nuevo --report-dir reports/session_23_plan_rehabilita/replay_nuevo
# Activación opcional local solo para un producto validado compatible:
# MADRID_REHAB_REHABILITA_DIR=data/processed/plan_rehabilita/replay_nuevo

PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_plan_rehabilita.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_plan_rehabilita.py --output reports/session_23_plan_rehabilita/benchmark_nuevo.json
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v

# Prototipo explícito de red: no repetir capturas ya guardadas ni conectar al visor
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastral_service_probe --output-dir data/raw/cadastre/probe_nuevo --references 8781605VK4788B 9377401VK3797G
```

Cada invocación del prototipo limita entradas a cuatro RC y peticiones a seis, incluidos hasta dos detalles; no eleva esos límites ni ejecuta enumeración regional. Para reevaluar capturas existentes se usa el parser local sin red. El prototipo no es una recomendación de adquisición masiva.

## Artefactos

En `reports/session_23_plan_rehabilita/`: `source_inventory.json`, `source_quality.json`, `matching_quality.json`, `matching_supplement.json`, `coverage_before_after.csv`, `coverage_summary.json`, `validation_summary.json`, `cadastral_source_feasibility.md`, `cadastral_probe_summary.json`, `determinism_validation.json`, casos reales, hashes y logs. Los resultados de sesión 22 permanecen intactos.

## Cierre de validación

**Suite completa: 528 pruebas, OK, 753,232 segundos, una sola ejecución y código de salida 0.** No hubo cambios de código posteriores a esta suite. Las 12 nuevas y las regresiones focalizadas pasaron previamente; Ruff global, formato y control de diferencias son correctos.

Los seis Parquet del replay son idénticos por SHA-256. El ZIP original supera el CRC de todos sus miembros y mantiene su hash; S22 conserva sus hashes y su población. `preservation_final.json` y `validation_summary.json` contienen la evidencia final y los hashes del código validado.

Limitaciones no resueltas: licencia/procedencia oficial y captura originales del ZIP sin verificación independiente; estado individual de resolución/pago/obra desconocido; 103 relaciones pendientes y cinco sin correspondencia exacta; prototipo catastral no activado ni validado a escala; navegador bloqueado por ausencia de Chromium. No hay validación visual acreditada.

**Resultado final:** 2.085 expedientes conservados, 1.977 A, 1.919 CP y 3.194 versiones con evidencia municipal nueva. Cero fichas casi vacías rescatadas: permanecen 18.691/214.083. América devuelve suelo y un domicilio catastral distinto en la prueba oficial; Moncloa mantiene los atributos S22, sin incorporar la oficina individual como característica del Building. Sin commits, push, publicación ni modificación de originales/snapshots.
