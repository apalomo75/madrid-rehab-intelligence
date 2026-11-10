# Sesión 24 — Catálogo comercial de seis municipios

Sesión local offline, 10/11/2026. **El catálogo local admite 153.929 CP distintas de 194.820 CP aceptadas** en las capturas de Madrid y cinco pilotos; excluye 40.891. En Madrid el buscador comercial ofrece **178.243 versiones postales/NDP**, y excluye 35.840 de las 214.083 versiones originales. Los originales, índices históricos y registros excluidos permanecen intactos en la capa técnica.

**Visibilidad pública efectiva: cero parcelas.** Se mantienen las restricciones vigentes de los productos, sin convertir disponibilidad local o acceso libre en autorización de difusión. La experiencia local de seis municipios está implementada; no se declara un MVP listo para publicar. Las sesiones 25–26 deben resolver permisos por fuente/campo y revisión visual antes de publicación.

No se descargaron datasets, incorporaron fuentes, ejecutaron consultas web o servicios externos, ni se hicieron commits/push. El prototipo catastral S23 no se activa ni se usa como fuente adicional del catálogo.

## Resultado por municipio

Población: CP aceptada, referencia única y geometría utilizable dentro de cada producto existente. No es censo territorial ni recuento de edificios físicos.

| Municipio | CP de referencia | Incluidas | Excluidas | Construcción residencial suficiente | CEEE | Conservación / obligaciones | PRTR | Plan Rehabilita |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Madrid | 140.379 | **114.706** | 25.673 | 111.369 | 51.842 | 9.036 | 3.300 | 1.919 |
| Getafe | 16.149 | **13.339** | 2.810 | 13.026 | 2.472 | No integrada | 151 | No corresponde |
| Móstoles | 8.980 | **6.819** | 2.161 | 6.635 | 2.229 | No integrada | 277 | No corresponde |
| Leganés | 10.541 | **6.597** | 3.944 | 6.467 | 2.133 | No integrada | 198 | No corresponde |
| Alcorcón | 5.734 | **3.008** | 2.726 | 2.820 | 1.470 | No integrada | 244 | No corresponde |
| Alcalá de Henares | 13.037 | **9.460** | 3.577 | 9.112 | 2.442 | No integrada | 208 | No corresponde |
| **Total** | **194.820** | **153.929** | **40.891** | **149.429** | **62.588** | **9.036** | **4.378** | **1.919** |

Las columnas de evidencia se solapan: no se suman para obtener incluidas. CEEE cuenta CP con al menos un contenido utilizable, no certificados únicos ni viviendas. Ayudas cuentan CP relacionadas con expedientes, no importes o beneficiarios físicos. Conservación incluye obligaciones de presentación identificables; **no son resultados efectivos ITE/IEE**.

Las 194.820 claves compuestas municipio–CP corresponden también a 194.820 referencias CP distintas: no se observan referencias aceptadas repetidas entre estos seis productos. Las filas históricas duplicadas/no utilizables y cuarentenas previas quedan fuera de este denominador y se conservan en sus fuentes originales; no se cuentan como parcelas comerciales ni se eliminan.

## Direcciones, accesos y versiones

| Ámbito / modo | Versiones originales | Versiones incluidas | Versiones excluidas | NDP incluidos | Literales distintos incluidos |
| --- | ---: | ---: | ---: | ---: | ---: |
| Madrid local | 214.083 | **178.243** | **35.840** | **178.243** | **178.243** |
| Madrid público | 214.083 | **0** | **214.083** | **0** | **0** |
| Cinco pilotos | Sin índice postal fiable | No evaluable | No evaluable | No evaluable | No evaluable |

Madrid conserva 213.685 NDP distintos en la población postal original; las 214.083 versiones no son 214.083 edificios. La coincidencia numérica de versiones/NDP/literales incluidos en este resultado no los hace conceptos equivalentes. En pilotos no se usan URLs AD para inventar direcciones; se investiga mediante CP y navegación a BU.

Las **18.691 versiones casi vacías de S22 quedan excluidas**. Se excluyen además **17.149** que tenían alguna evidencia según el umbral antiguo, pero no superan el nuevo: por ejemplo, atributos de objetos no residenciales sin otra evidencia, o contexto de licencia/declaración sin conservación. No se afirma que esas direcciones hayan dejado de existir ni que carezcan de información fuera de nuestra captura.

La cobertura visible de Madrid es 178.243/214.083 (**83,26%**), manteniendo el denominador de referencia. Decir que todas las fichas visibles cumplen el nuevo criterio es una definición de selección, no una recuperación del 100% de las direcciones ni una mejora de los datos originales.

## Reglas operativas y ajustes respecto al enunciado inicial

Las cuatro alternativas son:

**A. Construcción residencial suficiente.** Un mismo objeto constructivo relacionado documentalmente tiene uso `1_residential` y al menos dos atributos útiles: año, superficie construida, viviendas o plantas. No se unen un año de un BU y una superficie de otro para alcanzar el umbral. Los pilotos solo usan A y `relation_validated` de S18. Madrid reproduce el lector distrital histórico y el suplemento S22 sobre sus mismos IDs.

Ajustes justificados de validez:

- Año interpretable entre 1000 y 2026, con precisión conocida en origen; 2026 es el corte fijo de estas capturas, no el reloj del servidor. No se completan fechas incompletas.
- Superficie bruta **positiva** del objeto, nunca superficie de suelo ni área calculada de geometría CP.
- Viviendas declaradas **positivas**; cero no aporta evidencia residencial suficiente por sí solo.
- Plantas sobre rasante **positivas y propias del objeto residencial**. Cero plantas bajo rasante no se usa para hacer útil un objeto vacío.
- La condición catastral, las unidades y la geometría no puntúan para A. No se suman superficies de Building/BuildingPart ni se infiere parentesco por sufijo.

Estos ajustes evitan falsos positivos de ceros o mezclas entre objetos. No se amplía el criterio a construcción no residencial sin alguna evidencia B/C/D: es una limitación deliberada del MVP, no prueba de inutilidad comercial de esos inmuebles.

**B. Energía.** Al menos un CEEE con nivel A, identidad de contenido única, sin fecha posterior a captura ni sospecha de alineación de columnas, y CP aceptada. Se conservan ámbitos vivienda individual, edificio completo declarado, local u otro/desconocido. No se atribuye una letra de vivienda a edificio, ni se afirma vigencia.

**C. Administración.** Relación confirmada, sin conflicto de identidad, tipo reconocible y fecha válida identificable. Tipos actuales: orden histórica, obligación ITE y obligación IEE. Se conserva precisión año/mes/día. Una obligación no acredita una inspección realizada. Las licencias y declaraciones responsables **no bastan por sí solas** para entrar por C; siguen en la ficha/capa técnica como contexto.

**D. Ayudas.** PRTR con estado documental confirmado, identidad válida y sin contradicción territorial, o Plan Rehabilita A. Un candidato espacial, B/C, expediente ambiguo o identidad conflictiva no cualifica por D. Se mantiene su ámbito de expediente, sin repartir el importe por CP. La disponibilidad en cada modo depende de la autorización de esa fuente.

No se diagnostica necesidad, defecto, oportunidad segura, ahorro o financiación. El color y el nivel no son una puntuación comercial.

## Niveles de ficha

- **Ficha documentada:** A, o al menos dos familias complementarias entre construcción, energía, administración y ayudas.
- **Ficha parcial con evidencia:** solo una familia documental B/C/D, sin A.
- **Registro técnico excluido:** ninguna alternativa autorizada suficiente.

PRTR y Plan Rehabilita son dos programas, pero una sola familia «ayudas»: su coexistencia no convierte por sí sola una ficha parcial en documentada ni prueba dos actuaciones físicas.

| Nivel local | CP |
| --- | ---: |
| Ficha documentada | **149.643** |
| Ficha parcial con evidencia | **4.286** |
| Registro técnico excluido | **40.891** |

Hay 64.867 CP con varias familias de evidencia; 576 admitidas sin objetos constructivos enlazados; 1.226 de Madrid admitidas solo por administración. Esto último no significa resultado real de inspección.

49.348 CP admitidas tienen algún CEEE de vivienda individual; 36.862 solo tienen CEEE de ese ámbito entre sus contenidos energéticos. Pueden tener otras evidencias no energéticas. No se cuentan esas CP como viviendas o edificios certificados íntegramente.

## Evaluación antes de activación y muestra

La primera medición y su muestra se generaron antes de abrir la nueva experiencia. `review_sample.json` selecciona hasta tres CP por municipio/estrato mediante el menor SHA-256 de `catalog24:<RC>`. Estratos: residencial incluido, solo energía, solo administración, solo ayudas, excluido con construcción y excluido sin construcción. **90 registros reales** en el conjunto resultante.

`real_review_benchmark.json` compara cada registro con los lectores originales y los datos seleccionados del modelo comercial, recalculando de forma independiente el criterio sobre cada objeto y contrastando fuentes/IDs. **Cero divergencias en esos 90 registros.** No es estimación estadística de error ni validación física del parque.

Se revisaron tanto falsos positivos potenciales (certificados individuales, varios programas, obligaciones sin resultado, múltiples partes) como exclusiones potencialmente útiles (construcción no residencial, ausencia de puente, escasez de atributos). Se mantienen las reglas: ampliar indiscriminadamente a cualquier atributo constructivo reproduciría el umbral débil de S22.

La revisión encontró un registro técnico excluido, `13000N7DS1810D`, cuyo formato no está soportado por el lector urbano de conservación. Se conserva su diagnóstico técnico previo; no se transforma en una parcela confirmada con antecedentes ni se cambia su identidad. Las fichas admitidas de la muestra no presentan fallos de recuperación.

## Implementación y productos

Generador offline: `commercial_catalog.py`. Snapshot `data/processed/commercial_catalog/session_24_01/`:

- Un Parquet por municipio con **todas sus CP aceptadas**, incluidas las excluidas: máscaras A/B/C/D, recuentos, nivel, motivos local/público, zona y geometría original con hash.
- `catalogue.sqlite`: CP sin duplicación por portal, metadatos de navegación y copia derivada de todas las versiones/alias postales con sus máscaras de visibilidad. Índices de identidad, vía y zona.
- `manifest.json`: versión, municipio, reglas, política pública, hashes de entradas/salidas y código del generador.

La geometría WKT se copia exactamente. En el mapa comercial se proyecta para mostrarla, **sin simplificación de sus vértices**. La cuadrícula de navegación es un recurso de paginación, no una geometría de parcela ni un barrio oficial.

Una reproducción completa en `replay_24_01/` produce **los mismos hashes de los seis Parquet y de SQLite**. El generador inicial queda archivado en `builder_executed.py`, con hash igual al del manifiesto canónico. El código mantenido añade autenticación explícita de particiones distritales y validación de calendario; el replay confirma que no cambian estos resultados reales.

Los lectores verifican hashes, reglas y compatibilidad con las capturas activas. Un índice ausente, alterado o desactualizado no activa el buscador completo como fallback comercial. El índice no se recalcula en Streamlit y no se abren GML o ZIP durante una búsqueda.

## Experiencia comercial y consulta técnica

La entrada normal ahora es **Mapa comercial**. Selector limitado a Madrid, Getafe, Móstoles, Leganés, Alcorcón y Alcalá de Henares. Reutiliza `municipal_navigation.render_explorer(..., commercial=True)` y la ficha municipal existente:

- En comercial se muestran solo CP admitidas, máximo 500 geometrías por carga y una geometría por CP. No hay capa BU independiente sin pasar por una CP admitida.
- Vista general por cuadrículas, acceso a zona/páginas y selección por mapa con lista positiva de IDs visibles; también puede consultarse una RC admitida.
- Filtros por construcción, energía, conservación/obligaciones, PRTR o Plan Rehabilita. En pilotos los filtros de fuentes no integradas lo dicen expresamente, sin afirmar cero ocurrencias.
- Colores consistentes: azul construcción suficiente; ámbar energía sin construcción suficiente; violeta antecedentes/ayudas sin las anteriores. En coexistencia prevalece ese orden de representación; **no es prioridad comercial ni necesidad**.
- Al abrir CP se indica el nivel de la parcela de origen. Se conserva la navegación documental CP→BU→CP, sin propagar CEEE/ayudas/administración al BU.
- Cambiar evidencia/municipio/modo cambia el contexto de selección y evita reutilizar un evento de otro mapa.

**Buscar por dirección** consulta SQL sobre las filas admitidas, con recuento/paginación después del filtro. Las versiones no se deduplican por su literal postal; conservan sus IDs y puentes. Si un acceso tiene varias CP, solo ofrece las admitidas y exige selección expresa; no confirma una CP excluida ni combina sus datos.

Una dirección localizada pero no admitida muestra exactamente:

> No hay información suficiente para ofrecer una ficha comercial de esta dirección.

No aparece botón para abrir una ficha vacía. Una dirección no localizada conserva un mensaje distinto. Las sugerencias comerciales se limitan a vías con registros admitidos. Los municipios piloto no obtienen buscador postal a partir de AD.

Se conserva **Consulta técnica · direcciones**, con el índice completo S20, y **Explorar municipios**, explícitamente identificado como explorador técnico completo. Las rutas históricas de Analista siguen disponibles. El lector técnico y sus fuentes no se filtran ni se alteran: permiten auditar por qué un registro fue excluido. Las pruebas anteriores de resultados no resueltos, múltiples CP y protección pública del lector se ejecutan en esta ruta técnica; las pruebas nuevas verifican el bloqueo comercial.

## Modo público y publicación

No hay una autorización nueva de difusión en esta sesión. Se respetan los cierres de las sesiones anteriores:

| Fuente | Local | Catálogo público actual | Motivo |
| --- | --- | --- | --- |
| Construcción Catastro | Sí, relación/objeto acreditados | No | Productos enriquecidos no aprobados para exposición pública; revisión de condiciones/atribución por campo pendiente |
| CEEE | Sí, documental utilizable | No | Cierre público histórico conservado; el catálogo local CC BY no se usa como aprobación automática de todos los campos |
| Conservación | Madrid, fuentes parciales | No | Mezcla de fuentes y puente no revalidados para redistribución |
| PRTR | Sí, confirmado | No | Licencia de reutilización no verificada |
| Plan Rehabilita | Madrid, A | No | Procedencia, captura y licencia originales no acreditadas |

La política está versionada en el manifiesto; cada CP guarda sus motivos de inclusión por modo. Los registros públicos no heredan la visibilidad local ni permanecen gracias a evidencias ocultas. Las 194.820 CP quedan fuera del **catálogo público** hasta autorizar alguna fuente que alcance el umbral.

Esto no declara ilegal el uso ni revoca permisos existentes: **no se inventa una autorización de publicación** durante una sesión sin nuevas fuentes o revisión de derechos. Identificación/geometría técnica no basta para superar el criterio comercial.

El mapa público muestra el cierre, sin parcelas o fichas basadas en fuentes restringidas. El buscador público no ofrece fichas del catálogo. Las protecciones originales de lectores y exportadores permanecen. Las rutas técnicas/Analista históricas no constituyen un backoffice autenticado ni una auditoría completa de publicación; deberán revisarse/restringirse antes de despliegue externo.

## Casos solicitados

**Avenida de América 113 A — 8781605VK4788B.** Excluida local y públicamente: ninguna alternativa A/B/C/D utilizable. El buscador distingue que está localizada y no ofrece abrir ficha comercial. El índice postal y la CP siguen presentes en la consulta técnica. No se activa la respuesta de suelo del prototipo S23 ni se busca un Building vecino para rellenar atributos.

**Avenida de la Moncloa 14 — 9377401VK3797G.** Ficha documentada local: Building residencial con año 1978, 5.346 m² y 14 viviendas declaradas por objeto; CEEE individuales y contexto administrativo conservados en su ámbito. No se extiende la oficina individual del prototipo S23 ni se fabrica una letra global de edificio. Excluida del catálogo público por la política actual, no por falta de información.

Los cinco pilotos tienen CP admitidas verificadas y navegación a BU A. Los tests y la muestra usan registros reales; no se inventan portales ni se alteran vínculos B/C.

## Rendimiento y comprobaciones

Tras validación inicial de hashes (aproximadamente 1,10 s en el benchmark de búsqueda), las consultas medidas tardaron:

- América excluida y localizada: 2,5–3,2 ms.
- Moncloa admitida: 2,1–2,3 ms.
- Calle Bailén sin número: 2,9–3,1 ms para recuento/resultados filtrados.

Índice de mapa: primera consulta Madrid 1.728,7 ms, incluida validación fría; repetida 16,6 ms. Pilotos: primeras 16,0–59,8 ms, repetidas 2,9–4,0 ms. Caché por municipio/modo/evidencia y firma de fuente; se leen metadatos, no geometrías completas para preparar el selector. Los Parquet originales solo se consultan para la página geométrica seleccionada. Son tiempos Python locales, no garantías de renderizado o navegador.

Pruebas focalizadas: 14 nuevas de catálogo, 16 del buscador, 4 de navegación municipal, 14 comerciales y 7 S19; todas satisfactorias. Comprueban alternativas/niveles, mismo objeto, cantidades positivas, ayuda ambigua no contada, una vivienda certificada, modo público, exclusión de América, Moncloa, duplicados, correspondencia geométrica sin simplificar, selección y CP/BU. Ruff global y formato de 11 archivos correctos.

Navegador **bloqueado por ausencia de Chromium** en la ruta configurada y en `/tmp/madrid-rehab-browser/`. Sin descargas ni validación visual/WebGL acreditada. AppTest prueba estado y controles, no pintura, legibilidad o interacción física del navegador. El resultado de la única suite general figura en el cierre.

## Preservación y artefactos

`reports/session_24_commercial_catalog/` contiene:

- `metrics.json`, `summary.json`: municipio, modo, fuente, niveles y totales no sumables entre evidencias.
- `coverage_by_municipality.csv`, `postal_coverage.csv`, `metrics_by_unit.json`: CP, NDP, versiones y cobertura postal no integrada explícita.
- `review_sample.json`, `real_review_benchmark.json`: muestra, IDs, resultados independientes y límites.
- `map_index_benchmark.json`, `determinism_validation.json`: rendimiento e igualdad de salidas.
- `preservation_final.json`: hashes de entradas y productos, incluidos los registrados al cierre de S22/S23, y geometrías originales.
- `browser_status.json`, logs focalizados, Ruff/formato, `full_tests.log`, `validation_summary.json`.

Se mantienen intactos originales, snapshots, cuarentenas, índice postal S20 y resultados S22/S23. La exclusión es una máscara derivada, no una eliminación o corrección de identidad.

## Prioridades para cerrar el MVP en sesiones 25 y 26

**Sesión 25:** resolver y registrar permisos concretos de fuente/campo/uso para una primera vista pública útil; preparar un catálogo público separado cuando haya fuentes suficientes autorizadas, sin copiar dependencias privadas indiscriminadamente. Revisar atribución Catastro, campos CEEE, callejero/límites y exportaciones. No levantar PRTR/Plan Rehabilita por conveniencia. Revisar exclusiones y fichas parciales reales con el usuario, sin ampliar a más municipios ni crear datos postales piloto.

**Sesión 26:** revisión visual con Chromium y usuario, recorridos Madrid dirección→CP→BU→CP y mapas piloto, accesibilidad/errores/latencia, despliegue/backoffice/exportadores y comprobación final de la política pública. Publicación solo con alcance autorizado explícito y fuentes permitidas. No confundir el cierre de esta sesión local con permiso de publicar.

## Reproducción

Sin dependencias o build nuevos. Instalación: `.venv/bin/python -m pip install -r requirements.lock`. Servidor local habitual de README/AGENTS. No requiere red.

```bash
# Siempre nuevos directorios; no sobrescribe el catálogo canónico
PYTHONPATH=src .venv/bin/python -m madrid_rehab.commercial_catalog --output-dir data/processed/commercial_catalog/replay_nuevo --report-dir reports/session_24_commercial_catalog/replay_nuevo
# Override local para un replay compatible: MADRID_REHAB_CATALOG_DIR=/ruta/replay_nuevo

PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_commercial_catalog.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_address_search.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_municipal_navigation.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_commercial_catalog.py --output reports/session_24_commercial_catalog/review_nuevo.json
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

El benchmark utiliza la muestra archivada del informe canónico para reproducir su revisión; no es una auditoría física ni un cliente de nuevas fuentes. El manifiesto bloquea fuentes cambiadas o overrides incompatibles en vez de mostrar registros sin filtrar.

## Cierre de validación

**Suite general: 542 pruebas, OK, 635,379 segundos; una única invocación y código de salida 0.** No se modificó código después de esta ejecución. Ruff global, formato de 11 archivos y control de diferencias correctos. Las verificaciones de hashes se repitieron después de la suite, sin recalcular el catálogo ni modificar fuentes: `preservation_after_tests.json`.

Los seis Parquet municipales y SQLite del replay tienen hashes idénticos. La revisión independiente de 90 registros no mostró divergencias con los lectores. La validación visual permanece bloqueada, no se declara realizada.

**Entrega local:** 153.929 CP incluidas; 40.891 CP aceptadas excluidas y conservadas técnicamente; 178.243 versiones/NDP/literales incluidos en Madrid y 35.840 versiones excluidas. Construcción suficiente: 149.429 CP; energía: 62.588; administración: 9.036; PRTR: 4.378; Plan Rehabilita: 1.919, con solapamientos entre fuentes. Público: cero CP por la política actual de autorización. Sin nuevas fuentes, descargas, publicación, commits, push ni modificación de snapshots históricos.
