# Sesión 25 · filtros comerciales y mapa documental

## Uso

La entrada **Mapa comercial** conserva los seis municipios y ofrece cuatro casillas visibles: **Solo CEEE**, **Solo ITE/IEE**, **Solo Plan Rehabilita**, **Solo ayudas PRTR**. Sin casillas se consulta el catálogo admitido completo. OR selecciona la unión de identidades; AND, su intersección. **Limpiar filtros** restablece las casillas y OR. No se calcula scoring.

El contador mide referencias de parcela distintas dentro del municipio seleccionado. Mapa, zonas y lista parten del mismo DataFrame filtrado, deduplicado por referencia. La vista general agrupa parcelas en celdas de navegación y la vista de zona pagina como máximo 500 geometrías originales. Cada celda contiene exclusivamente parcelas filtradas; no es un barrio oficial. El mapa nunca dibuja un marcador por expediente o certificado.

La lista, junto al mapa, pagina diez parcelas: dirección documental cuando existe, municipio, código de distrito Madrid, evidencias y referencia secundaria. Una parcela puede tener varias versiones postales: se presenta un literal documental como etiqueta, sin declarar que sea su única dirección. En los pilotos se muestra localización catastral/zona, sin inventar calles. Dentro de una zona, la lista indica expresamente ese alcance; el contador principal sigue contando todo el municipio filtrado.

**Abrir ficha** selecciona la misma identidad que el mapa. **Volver al mapa** limpia la selección conservando filtros, zona y páginas. La ficha mantiene el resumen comercial y su detalle constructivo/técnico, con navegación documental CP/BU. No se propagan evidencias de parcela a Building/BuildingPart ni se suman sus magnitudes. La búsqueda postal Madrid queda disponible como ruta secundaria y mediante botón al pie del mapa en la aplicación principal.

## Reglas de evidencia

- **CEEE:** máscara documental validada S24, vínculo A utilizable, identidad no ambigua y controles de fecha/esquema. La ficha distingue vivienda individual, edificio completo declarado, local y ámbito desconocido. No se asigna una letra global a la parcela. Se omite el selector opcional A–G para evitar mezclar ámbitos y criterios de consumo/emisiones.
- **ITE/IEE:** eventos fechados, vínculo `confirmed`, sin conflicto de identidad, marcados como evidencia de conservación. Solo obligaciones `ite_pending`/`iee_pending` o una orden con indicador de mención desfavorable **y texto explícito ITE/IEE**. Una orden genérica, licencia o declaración no cualifica. No se promueve el texto histórico «acta» a resultado integrado. **No hay resultados reales de inspección integrados.** La ficha y el detalle conservan tipo, fecha, fuente, motivo y carácter indirecto; ninguna señal acredita estado físico actual o subsanación.
- **Plan Rehabilita:** máscara de expedientes municipales confirmados del catálogo, vínculos A S23, identidad utilizable. Ficha: dirección original, convocatoria, expediente, componentes de actuación, viviendas del expediente y subvención revisada/presupuesto protegible con su significado original. El distrito disponible se identifica también en la lista. Importe por expediente único; no se suma por parcela, portal o capa. No acredita pago ni ejecución.
- **PRTR:** máscara de vínculos confirmados, identidad de expediente no conflictiva y territorio no contradictorio. No incluye candidatos espaciales o vínculos ambiguos. Ficha con programa, expediente y concesión documentada; el importe pertenece al expediente, incluso si aparece en varias parcelas. No se mezcla con Plan Rehabilita.

Los filtros de fuentes no integradas en pilotos no acreditan cero ocurrencias reales. Plan Rehabilita es exclusivamente municipal Madrid; conservación/ITE/IEE no tiene cobertura integrada en los otros cinco municipios.

## Recuentos reales

Unidad: parcelas distintas admitidas; las columnas se solapan.

| Municipio | Todo el catálogo | CEEE | ITE/IEE | Plan Rehabilita local | PRTR local |
| --- | ---: | ---: | ---: | ---: | ---: |
| Madrid | 114.706 | 51.842 | 8.238 | 1.919 | 3.300 |
| Getafe | 13.339 | 2.472 | 0* | 0* | 151 |
| Móstoles | 6.819 | 2.229 | 0* | 0* | 277 |
| Leganés | 6.597 | 2.133 | 0* | 0* | 198 |
| Alcorcón | 3.008 | 1.470 | 0* | 0* | 244 |
| Alcalá de Henares | 9.460 | 2.442 | 0* | 0* | 208 |
| Total seis municipios | 153.929 | 62.588 | 8.238 | 1.919 | 4.378 |

\* Fuente no integrada/no aplicable; no es tasa cero del fenómeno. Las 8.238 parcelas ITE/IEE son un subconjunto específico de los 9.036 antecedentes generales S24.

Ejemplos Madrid: CEEE `0002601VK4700A`; ITE/IEE `0004407VK4700C`; Plan Rehabilita `0006718VK4800E`; PRTR `0006716VK4800E`. El informe JSON incluye tres ejemplos reales por categoría y municipio cuando hay resultados. Son ejemplos de identidad documental, no diagnósticos de edificios.

Pruebas reales de combinaciones en Madrid:

| Selección | OR | AND |
| --- | ---: | ---: |
| CEEE + ITE/IEE | 56.613 | 3.467 |
| CEEE + Plan Rehabilita | 52.495 | 1.266 |
| CEEE + PRTR | 52.564 | 2.578 |
| ITE/IEE + Plan Rehabilita | 9.939 | 218 |
| ITE/IEE + PRTR | 11.318 | 220 |
| Plan Rehabilita + PRTR | 4.931 | 288 |

Se comprueba igualdad con unión/intersección de conjuntos, nunca suma de contadores. Véanse todas las parejas, municipios y modos en `reports/session_25_filters/real_validation_02.json`.

## Modo público y bloqueo verificable

El snapshot S24 público y su membresía se preservan. **No hay despliegue externo autorizado**: la interfaz muestra el bloqueo de publicación por licencia/procedencia PRTR y Plan Rehabilita pendientes. Sus casillas están deshabilitadas, el motor devuelve cero resultados si se solicitan por código en modo público y `load_fiche(..., public_catalog=True)` no consulta esas dos fuentes. Las pruebas verifican que dicho indicador no elude la restricción. Cero aquí significa **restricción de exposición**, no ausencia de ayudas.

En la **previsualización pública local** los recuentos de catálogo, CEEE e ITE/IEE coinciden con la tabla anterior; Plan Rehabilita y PRTR dan cero en los seis municipios. Esto no certifica un «modo público autorizado para despliegue»: no se ha concedido ese permiso ni auditado de nuevo toda la aplicación. Se mantiene el bloqueo explícito, opción prevista por el encargo, en lugar de reinterpretar la membresía como licencia. Las rutas técnicas/exportadores históricos mantienen sus controles; no constituyen un backoffice autenticado.

Antes del 20/11/2026 es crítico:

1. Cerrar licencia/procedencia y campos redistribuibles de PRTR y Plan Rehabilita, o excluir de un despliegue los productos/rutas que dependan de ellas. No retirar el aviso como sustituto de esta decisión.
2. Revisar condiciones/atribución del producto Catastro y de los puentes municipales, conservación, callejero y límites; mantener atribución CEEE CC BY 4.0 y sus ámbitos.
3. Hacer revisión visual real de mapas, selección, retorno, seis municipios y tamaños de pantalla. AppTest no acredita WebGL, legibilidad ni interacción física.
4. Revisar acceso externo a rutas técnicas/Analista, cachés y exportaciones antes de desplegar. No se ha publicado nada en esta sesión.

## Rendimiento y arquitectura

No hay nuevas fuentes, descarga, ETL ni producto de datos. `commercial_filters.py` consulta el índice S24 autenticado y lee una proyección de eventos conservados para construir el conjunto específico ITE/IEE, cacheado por firma de fuentes. El contador no carga fichas ni GML. Los literales postales se cachean como etiquetas por identidad y modo; la página solicita solo el distrito de sus diez referencias. Las geometrías proceden de los Parquet existentes, filtrados por las referencias de la página, sin simplificación.

La medición inicial registró consultas calientes Madrid aproximadamente 58–79 ms y pilotos 6–14 ms. La primera consulta Madrid, con verificación y preparación, fue 2,14 s. Son tiempos Python locales, no garantías del navegador. El informe definitivo `real_validation_02.json` contiene tiempos por filtro/modo; `list_and_map_preparation.json` mide adicionalmente preparación de mapa y etiquetas de lista, con una carga limitada de geometrías para cada categoría disponible. Ninguno es una validación visual.

## Validación y reproducción

Instalación y servidor: comandos habituales de README/AGENTS, sin dependencias nuevas. No se requiere conexión de red. Informes siempre en rutas nuevas.

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_commercial_filters.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_filter_navigation.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_commercial_filters.py --output reports/session_25_filters/replay_nuevo.json
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Pruebas nuevas: semántica OR/AND, unicidad, especificidad ITE/IEE, permisos por fuente sin bypass, controles públicos, lista→ficha→mapa y persistencia. Las pruebas existentes comprueban vínculos confirmados de CEEE/ayudas, exclusiones, listas positivas de selección cartográfica, navegación de seis municipios y CP/BU. El benchmark real reconcilia conjuntos y páginas geométricas en los seis municipios y ambos modos. Navegador bloqueado si falta Chromium; véase `browser_status.json`. La suite completa se invoca una sola vez al cierre; su resultado final se registra en `validation_summary.json`.

El informe inicial `real_validation.json` precede al endurecimiento del texto explícito ITE/IEE; se conserva como trazabilidad. La revisión final es `_02`. No se modifican snapshots, originales, informes previos, commits ni ramas remotas.

Medición final resumida (`performance_summary.json`): consultas calientes 5,6–119,2 ms; primera consulta máxima 2,70 s; preparación Python de mapa 16,8–1.083,7 ms, máximo 500 geometrías; etiquetas de lista 0,15–786,1 ms incluyendo preparación fría. No incluyen transporte, GPU o renderizado WebGL. `counts_by_municipality_and_mode.csv` distingue explícitamente la previsualización bloqueada de un despliegue autorizado.

Auditoría de tipos (`ite_evidence_kinds.json`): 3.401 parcelas admitidas con obligaciones ITE y 4.886 con obligaciones IEE; hay solapamiento y la unión es 8.238. En esta captura no hay órdenes con mención explícita que además superen todos los controles de vínculo/fecha ni resultados reales integrados. Los 4.629 y 5.299 registros de obligaciones confirmadas son eventos, no inmuebles adicionales.

Recorridos adicionales registrados: `filtered_six_city_navigation.json` prueba CEEE activo en los seis municipios, eventos cartográficos serializados, apertura por identidad y retorno conservando filtro/contador. `distant_list_and_map_navigation.json` prueba apertura desde la página 1.001 de la lista y selección posterior por el callback registrado del mapa. Son comprobaciones de integración en AppTest, no de ratón/WebGL.

## Cierre

Suite general: **550 pruebas, OK, 779,699 segundos**, una única invocación y salida 0. Código estable durante toda esa ejecución. Ruff global y comprobación de formato de los siete archivos Python modificados/nuevos correctos. Los hashes de todas las entradas y salidas del manifiesto canónico coinciden antes y después de las pruebas (`preservation_after_tests.json`). HEAD permanece en `d1aa6d8`; no se realizaron commits, push, descargas ni publicación. La validación visual queda bloqueada por ausencia de Chromium y el despliegue externo sigue pendiente de permisos y revisión visual.
