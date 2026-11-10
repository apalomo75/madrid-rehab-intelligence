# Sesión 19 — Catastro enriquecido en las fichas municipales

## Resultado y alcance

Integración offline de `data/processed/cadastre/session_18_enriched_01/` para Alcalá de Henares, Alcorcón, Getafe, Leganés y Móstoles. Árbol inicial limpio (`git status --short` sin salida), HEAD `f3ecfe5`. No se descargan fuentes, reconstruye Catastro, modifican snapshots, activan punteros ni hacen commits/push. Las cinco particiones están presentes y autenticadas por SHA-256 contra sus manifiestos municipales y colección. Las CP se contrastan con el hash de la entrada histórica de sesión 18; un override incompatible falla de forma explícita.

332.746 BU: 48.820 Building y 283.926 BuildingPart. Vínculos A=313.621, B=12.135, C=6.990; D=0. La comparación exhaustiva de identificador, tipo y geometría con los cinco productos históricos da cero diferencias. Esquemas completos, ejemplos individuales, tiempos y resultados: `reports/session_19_integration/real_validation.json`.

## Arquitectura y contrato reutilizable por dirección

1. **Resolución de identidad:** `cadastral_identity.resolve_object(municipality_code, identifier, kind)` devuelve estado explícito y una sola fila utilizable. Clave estable `(municipio INE, cp|bu, RC14|building_id completo)`. CP admite las identidades históricas conservadas; BU distingue mayúsculas. Ambigüedad, municipio incompatible, cuarentena y errores no producen selección.
2. **Recuperación:** `enriched_cadastre.metadata`, `links`, `parcel_buildings` y `building`; lectores CEEE, PRTR y conservación existentes. `parcel_buildings` devuelve registros A y relaciones con incidencia por separado. `links(..., kind="bu")` preserva también C con referencia no normalizable. No se construyen enlaces por geometría ni por prefijo de identificador.
3. **Presentación:** `municipal_fiche.render_fiche(code, name, identifier, objects=None, kind="cp")`. Si no se proporcionan filas, resuelve la identidad por sí misma. No necesita mapa, cuadrícula ni selección PyDeck. Ejemplo desde una futura pantalla de búsqueda:

```python
from madrid_rehab.municipal_fiche import render_fiche
render_fiche("28005", "Alcalá de Henares", "0015301VK7801N")
```

La búsqueda futura resolverá dirección → candidatos de portal/CP con calidad explícita → esta API. No deberá convertir un resultado de geocodificación en identidad física confirmada. El mapa se conserva como exploración secundaria; no se implementa aún un nuevo buscador.

`municipal_navigation` conserva exports de compatibilidad y la selección espacial. La ficha obtiene datos sin importar el componente del mapa. El lector histórico de construcción Madrid se ha extraído sin cambiar su contrato ni sus controles de hash.

## Ficha y navegación

Los seis apartados siguen en orden: Identificación; Características constructivas; Certificados CEEE; Conservación e ITE/IEE; Subvenciones PRTR; Calidad, limitaciones y procedencia. Cada apartado conserva su frontera de errores: una partición ausente o incompatible bloquea la integración afectada, mostrando consulta fallida, sin eliminar las demás evidencias de la parcela ni transformarla en ausencia.

En CP: recuento de objetos A y de Building/BuildingPart, tabla de atributos propios, selector de construcción y botón **Consultar construcción**. En BU: identificador original, tipo, atributos con estado, valores originales y evidencia XML desplegable, procedencia, calidad y botón para abrir CP exclusivamente si existe relación A. **Volver al objeto de origen** conserva el municipio, zona, página y selección del explorador. Se cambia el contenido de la ficha, sin crear mapas ni escribir el estado de PyDeck. Cambiar el objeto de origen reinicia la ruta y elimina sus claves anteriores; cambiar el municipio también cambia la identidad y namespace. Una parcela con más de 500 BU puede consultarlos sin introducir más geometrías en el mapa (que mantiene su límite de 500).

Los campos mostrados son uso, fechas inicial/final constructivas (con año cuando interpretable), viviendas, unidades, plantas sobre/bajo rasante, altura sobre/bajo rasante, superficie bruta de plantas y condición catastral. Ceros permanecen como valores; los estados `absent`, `present_empty`, `invalid` y `pending_interpretation` no se sustituyen por datos del padre. La altura sobre rasante no está disponible en esta captura. Las partes tienen plantas y altura bajo rasante; generalmente carecen de uso, año, viviendas y superficie propios. Se indican nulos y campos no declarados válidos; el detalle permite consultar texto original, unidad, QName, ruta XML y regla.

No hay sumas de superficies ni deducciones de parentesco Building–BuildingPart. Compartir CP no confirma edificio físico. La condición catastral no es una inspección actual. CEEE, conservación y PRTR se consultan únicamente en CP: incluso un BU con A no recibe esas evidencias. El enlace a CP permite consultarlas en su entidad correcta. Se mantienen programas, estados de vínculo e importes por expediente único; una vivienda certificada no califica todo Building. El modo público sigue protegiendo evidencias y no expone esta nueva integración, conforme al snapshot.

## A, B y C

- A: referencia documental explícita a CP aceptada única y regla geográfica de sesión 18 (≥95% dentro y ninguna otra CP con >5%). Se exige también `relation_validated`.
- B: incidencia de identidad/integridad o geometría, con motivo visible; nunca confirmada ni ruta acreditada a CP.
- C: declaración sin CP aceptada resoluble; conserva referencia original. Los formatos sin normalizar se consultan por BU, no se inventa una RC14 para incorporarlos a una CP aceptada.

Calidad muestra snapshot, distribución de clases e incidencias. BU añade archivo GML, ordinal, hashes, captura y regla. Las incidencias no se ocultan ni se promocionan a relaciones A.

## Muestras reales y rendimiento

Las muestras verificadas incluyen un Building A, un BuildingPart A, un BuildingPart B y un Building C por municipio; se comparan todas las columnas recuperadas con el Parquet original. Incluyen valores nulos y ceros. Además se consulta la CP con más A de cada partición y una CP sin A.

| Municipio | CP con múltiples A | BU A | CP sin A |
|---|---|---:|---|
| 28005 | 0048601VK7804N | 751 | 0029602VK7802N |
| 28007 | 8551201VK2685S | 218 | 0052501VK3605S |
| 28065 | 4836301VK4643N | 1014 | 0014501VK4601S |
| 28074 | 1427504VK3612N | 333 | 1127801VK3612N |
| 28092 | 0924603VK2602S | 211 | 0029106VK2602N |

Ejemplos individuales reproducibles (el JSON contiene atributos y estados completos):

| Municipio | Building A | BuildingPart A |
|---|---|---|
| 28005 | ES.SDGC.BU.0015101VK7801N | ES.SDGC.BU.0015101VK7801N_part1 |
| 28007 | ES.SDGC.BU.0048401VK3604N | ES.SDGC.BU.0048401VK3604N_part1 |
| 28065 | ES.SDGC.BU.0032404VK4603S | ES.SDGC.BU.0032404VK4603S_part1 |
| 28074 | ES.SDGC.BU.1222402VK3612S | ES.SDGC.BU.1222402VK3612S_part1 |
| 28092 | ES.SDGC.BU.0029101VK2602N | ES.SDGC.BU.0029101VK2602N_part1 |

Lectura de Parquet con filtros de clave y proyección: la lista CP no carga geometrías ni JSON de atributos. Solo el BU individual carga toda su evidencia. Parquet puede descomprimir grupos para evaluar filtros: no se promete acceso constante ni un índice que estos archivos no tienen. No se cargan los 332.746 BU completos por selección.

LRU de consultas: 32 entradas por proceso; verificación: 8 entradas. Claves incluyen municipio, archivo, campo, valores, proyección y firma de ruta/tamaño/mtime/ctime de manifiestos, productos y CP de origen. Cambio de firma vuelve a comprobar hashes. Se devuelven copias para proteger datos cacheados de mutaciones del consumidor. Las firmas se consultan también en llamadas calientes; no se recalculan hashes completos en cada selección. Las verificaciones municipales son independientes.

Medición del lector en un proceso separado, excluyendo los DataFrames de auditoría exhaustiva y la UI (`tests/benchmark_session19_reader.py`):

| Municipio | CP fría con verificación (ms) | CP cacheada (ms) | BU sin caché (ms) | Bytes de resultados CP/incidencias/BU |
|---|---:|---:|---:|---:|
| 28005 | 231.88 | 2.64 | 42.58 | 435692 |
| 28007 | 68.32 | 3.35 | 37.89 | 141446 |
| 28065 | 141.39 | 2.58 | 29.35 | 612282 |
| 28074 | 93.80 | 2.38 | 25.23 | 201423 |
| 28092 | 77.48 | 2.25 | 32.47 | 138395 |

RSS máximo inicial 132.40 MiB y final 427.52 MiB; incluye Python, pandas, Arrow y buffers de lectura, no solo caché. Tras recorrer cinco municipios: 15 entradas de consulta. La auditoría exhaustiva independiente alcanza 856.79 MiB: no representa memoria de una ficha. No se fijan umbrales ficticios ni se equiparan estos tiempos a latencia completa de Streamlit. Son una ejecución local, con caché de disco del SO no controlada y otras comprobaciones en procesos concurrentes; no constituyen un benchmark aislado del sistema.

## Direcciones: preparación de la siguiente sesión

Inventario local contrastado en `address_inventory.json`:

- Madrid: `conservation_accesses.parquet` contiene 214.676 versiones observadas de acceso, 214.278 COD_NDP distintos; todas las filas tienen nombre de vía y número. Hay 476 filas con múltiples versiones observadas de dirección, no resolubles automáticamente por elegir la primera. Municipio exclusivamente 28079. Incluye clase/nombre de vía, número/calificador, distrito/barrio y coordenadas.
- El puente histórico `administrative_events/session_10_final_01/ndp_bridge.parquet` conserva 216.061 filas y 215.663 NDP distintos: 207.648 filas `confirmed`, 7.561 `unmatched`, 493 `contradictory`, 243 `ambiguous` y 116 `candidate`. Es otra captura/contrato: no mezclar sus denominadores con el anterior. Las particiones de accesos usadas por conservación conservan el estado del vínculo y CP confirmada cuando procede. NDP identifica acceso, no BU físico.
- Cinco pilotos: enlaces AD `GetadByRefcat` recuperados del GML y preservados en `address_references_json`; son URLs parametrizadas, no un catálogo postal consultado. No proporcionan por sí solas búsqueda inversa calle+número→CP. Los textos de dirección CEEE/expedientes son evidencia parcial propia de esos registros y no un callejero exhaustivo.
- Otros municipios: el catálogo territorial de 179 municipios no aporta cobertura postal ni CP/BU validada adicional.

Madrid es el único municipio con base local estructurada suficiente para preparar un piloto de búsqueda por dirección. No se acredita exhaustividad, actualidad ni resolución inequívoca de toda dirección. Ninguno de los cinco pilotos dispone aún de cobertura demostrada suficiente para prometer un buscador postal fiable.

Falta: un índice local versionado de vías/alias/acentos, normalización conservadora de número/calificador, tratamiento de rangos y varios accesos, conciliación de versiones NDP/CP y duplicados, cobertura cuantificada por municipio y fecha, y licencia/condiciones de la fuente postal seleccionada. Para pilotos deberá revisarse una fuente oficial AD/callejero y adquirirla en otra sesión autorizada; no ejecutar las URLs desde la ficha. La API de resolución debe devolver candidatos y motivos de ambigüedad, permitir selección expresa y conservar la distinción portal/CP/BU/vivienda. El resultado abrirá la misma ficha en una pantalla, sin obligar a recorrer cuadrículas.

## Madrid y límites

Madrid conserva `session_2`, particiones distritales y los lectores históricos de CEEE, PRTR, conservación, accesos NDP y consulta REC individual. La navegación analítica por 21 distritos no se modifica. No se importan las 811.691 BuildingPart ni se aplica el contrato piloto a Madrid. Los atributos constructivos históricos y controles de hash siguen intactos. La ficha BU continúa sin heredar evidencias CP. No hay consultas REC al abrir ficha ni cambios de permisos de REC.

## Pruebas y verificación Ubuntu

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session19_integration.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_session19.py
PYTHONPATH=src .venv/bin/python tests/benchmark_session19_reader.py
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
```

Los benchmarks escriben solo informes de sesión 19, nunca productos de datos. Para preservar una medición anterior, copiar sus JSON o cambiar su destino antes de repetir. Las pruebas nuevas cubren cinco particiones, exactitud de atributos, B/C, copia de caché, municipio incompatible, carga sin mapa, ida/vuelta, cambio entre parcelas y conservación de zona/página/selección. Las llamadas de evidencias CP se comprueban expresamente ausentes al renderizar BU, incluidas relaciones A. Una prueba adicional contrasta los CEEE y expedientes únicos reales de `0015301VK7801N` antes/después de navegar; otra simula partición enriquecida ausente y verifica que identificación y evidencias CP sobreviven.

Servidor Ubuntu:

```bash
MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

En otra terminal (directorio nuevo):

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_session19.py --output-dir reports/session_19_integration/browser_ubuntu_01
```

El script usa controles reales del navegador: municipio, búsqueda RC, pestaña constructiva, seleccionar BU, abrir detalle, volver a CP; comprueba zona conservada, seis apartados y un único mapa, y guarda capturas. Para clics WebGL reales ejecutar también `tests/browser_municipal_navigation.py --output-dir reports/session_19_integration/webgl_ubuntu_01` con las mismas variables. Si falta Chromium, prepararlo previamente en Ubuntu con `PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser .venv/bin/python -m playwright install chromium` (descarga fuera de esta sesión; aquí no se ejecutó).

En esta ejecución el servidor sí arranca. Chromium falta en la ruta configurada (`chromium_headless_shell-1194/.../headless_shell`), por lo que `browser_01/browser.json` registra bloqueo sin casos ejecutados. No se descarga el navegador en esta sesión. **Interacción de navegador y WebGL pendientes; AppTest no son clics WebGL ni revisión visual humana.**

Comprobación manual: elegir cada CP de la tabla, revisar recuentos y valores, abrir Building y BuildingPart, comprobar estados ausentes, volver y cambiar CP/municipio/página. En `0015301VK7801N` (Alcalá), revisar CEEE/PRTR en CP y su ausencia de atribución en BU. Abrir los B/C de `real_validation.json`: deben mostrar motivos y carecer de ruta acreditada a CP. En Madrid revisar distritos, evidencias históricas y accesos REC sin ejecutar consultas adicionales.

## Resultados finales de comprobaciones focalizadas

- Sesión 19: **7 pruebas, OK**, 28,056 s (`focused_complete.log`).
- Fichas y resistencia de sesión 16: **4 pruebas, OK**, 335,175 s (`madrid_resilience_final.log`), con objetos reales de los seis municipios y fallos auxiliares inyectados deliberadamente.
- Madrid (incluidos 21 distritos), navegación 7.1 y navegación regional: **30 pruebas, OK**, 242,392 s (`madrid_navigation_final.log`).
- Auditoría real: cinco productos presentes, esquemas y clases contrastados, 332.746 identidades/tipos/geometrías sin diferencias, 20 BU contrastados íntegramente y cinco CP con múltiples A más cinco sin A. Consultas y cambio de municipio medidos en JSON separados.
- Ruff global, formato de módulos y pruebas nuevas y `git diff --check`: OK (`ruff.log`, `format.log`, `diff_check.log`).
- Browser: bloqueado por ejecutable ausente, ninguna interacción visual acreditada.

Los logs intermedios se conservan por trazabilidad. Las trazas `injected source failure`, `unreadable` y `missing partition` de las pruebas de resistencia son fallos simulados esperados, no errores ocultos de validación.

Suite completa: **476 pruebas, OK**, 926,365 s (`full_suite.log`), sin omisiones notificadas. Esta ejecución se inició con las tres primeras pruebas de sesión 19; el fichero final ampliado a siete se ejecutó íntegramente en `focused_complete.log`. Las comprobaciones focalizadas finales complementan la suite y no se suman como si fueran casos distintos de aquella. HEAD sigue en `f3ecfe5`; sin commits/push ni cambios en snapshots. La limitación pendiente es la validación visual real, por ausencia de Chromium.
