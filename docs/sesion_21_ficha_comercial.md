# Sesión 21 — Ficha comercial

## Auditoría previa y matriz de disponibilidad

Se ejecutó `git status --short` antes de editar: había modificaciones de sesiones 19/20 en AGENTS, README, city_app, municipal_fiche, municipal_navigation y tests, además de módulos y documentos no versionados. Se preservan. Se leyeron AGENTS y los documentos 19/20; se inspeccionaron app, city_app, address_search/view, municipal_navigation/fiche, cadastral_identity, enriched_cadastre, energy_view, grants_view, regional_view, conservation_view y rec_view.

La ficha técnica tenía seis pestañas ejecutadas en cada rerun. El resumen postal volvía a resolver CP y construcción. Los pilotos tienen BU/BuildingPart documentales A y B/C de incidencia, pero no literales postales. Madrid usa BU históricos asociados a CP. No existe equivalencia general acceso = CP = BU = edificio físico.

| Campo | Entidad | Fuente local | Relación/calidad | Ámbito y presentación | Limitaciones |
| --- | --- | --- | --- | --- | --- |
| Dirección, complemento | Versión de acceso/NDP | Índice postal S20, puente municipal S14/S10 | confirmed exclusivamente; versión explícita | Título de la dirección seleccionada | No prueba edificio físico; varias versiones no se fusionan |
| Otros accesos | Acceso→CP | S14 accesses | confirmed_access_parcel | Número de accesos y direcciones de parcela | No equivale a número de comunidades |
| Referencia, fecha fuente | CP | Catastro S2 / CP parcial piloto | Única, aceptada, geometría utilizable | Identidad secundaria; fecha catastral explícita | No fecha de actualización de otras fuentes |
| Uso y años | BU histórico Madrid / BU enriquecido piloto | S7 / S18 | Asociación histórica Madrid / A validada piloto | Valores distintos de objetos asociados a CP | No fecha ni uso verificado del portal |
| Viviendas, plantas, superficie | Objeto BU/BuildingPart | S7 / S18 | Declaración por objeto | Valores por objeto; sin suma | No total de CP; Building y partes pueden solaparse; Madrid sin superficie/plantas en tabla distrital |
| Certificados, letras, fechas, ámbito | Contenido canónico CEEE | S13 | A documental; D no confirmado | Distribución de contenidos; cada fila conserva ámbito | No inmuebles únicos, vigencia ni letra de edificio físico |
| Programa, importe, fecha | Expediente PRTR | S11 y clasificación regional activa | Solo estados confirmados | Importe por expediente único; fecha con nombre original | Concesión no pago ni ejecución; fecha individual no contrastada; licencia pendiente |
| Obligaciones ITE/IEE | Evento administrativo | S14/S10 | Confirmado, sin conflicto | Obligaciones observadas | No inspección realizada ni resultado |
| Órdenes, licencias, declaraciones | Evento/versionado | S14/S10 | Confirmado, sin conflicto | Historial con fecha y semántica | No diagnóstico actual; archivo no subsanación |
| Resultados REC | Consulta explícita | Estado de sesión, controles técnicos existentes | Identidad y fecha de consulta propias | Detalle técnico bajo demanda | Sin consultas automáticas ni nuevas llamadas en resumen |
| Postal pilotos | No disponible | Auditoría S20 | Fuente sin cobertura | Aviso explícito | URLs AD no son direcciones |
| Conservación pilotos | No cubierta | Fuente municipal Madrid | No aplicable | Fuente no cubierta para ese municipio | No cero incidencias |

Hallazgo real previo: Bailén 16 tiene también acceso Yeseros 6 y **una declaración responsable de 10/01/2024**. No es una orden ni una inspección; el resumen S20 de conservación cero no significaba ausencia de todo antecedente administrativo. Se hará visible esta distinción.

## Implementación y arquitectura

- `commercial_data.py`: recuperación selectiva por municipio/CP o BU. Reutiliza lectores autenticados de conservación/energía y relaciones A de sesión 18. PRTR comprueba versión, hash y compatibilidad CP, y lee solo los expedientes seleccionados. Cachés acotadas por firma de fuente, con copias antes de modificar. No hay productos nuevos, consultas de red, LLM ni índices reconstruidos.
- `commercial_fiche.py`: modelo independiente de Streamlit (`CommercialFiche`, `Evidence`, `Quality`) y reglas deterministas. Cada observación conserva valor, fuente, identificador, calidad, ámbito, periodo y limitación. No contiene geometrías ni sumas de superficies/viviendas.
- `commercial_view.py`: presentación nativa con cabecera postal, características en dos columnas, energía, ayudas, antecedentes y comprobaciones pendientes. Valores distintos se muestran conjuntamente, con acceso a todos por objeto. Los listados de procedencia y las seis pestañas originales están plegados.
- `municipal_fiche.py`: integra los dos niveles desde buscador y explorador, conservando navegación CP→BU→CP, identidad, secciones, REC bajo control explícito y exportación limitada anterior. Se reutiliza la tabla constructiva ya recuperada; no se vuelve a resolver CP para preparar el resumen.
- `address_view.py`: mantiene formulario, selección explícita, paginación y vuelta a resultados; pasa la versión postal seleccionada a la ficha compartida. No se reimplementa la búsqueda.
- `cadastral_identity.py`: acepta proyección opcional de columnas constructivas. El resumen Madrid excluye geometrías BU. Los pilotos recuperan atributos resumidos solo de objetos relacionados con la CP, nunca el BU municipal completo.

El desplegable técnico oculta visualmente su contenido; Streamlit sigue ejecutando sus controles para conservar la navegación existente. No se afirma carga diferida del desplegable. La verificación inicial de integridad puede recorrer bytes completos para SHA-256; no materializa por ello todos los registros en DataFrames. El resumen de una parcela muy grande sí recorre sus atributos proyectados: el caso Getafe contiene 1.014 objetos. Una futura agregación persistida auditada podría reducir ese coste sin inventar un edificio agregado.

## Semántica de presentación

El título es la dirección original seleccionada y el municipio. La CP queda como referencia secundaria. Si se abre desde mapa, se enumeran hasta dos direcciones de accesos confirmados y se indica pluralidad; no se elige una comunidad. Sin dirección piloto se muestra consulta catastral y falta de cobertura postal.

Uso y años son valores declarados de objetos; no características verificadas del portal. Las viviendas, plantas y superficie se presentan por objeto, sin totalizar ni fusionar Building/BuildingPart. Las diferencias de años no acreditan reformas. Los nulos no se sustituyen por cero. El resumen agrupa valores distintos únicamente para lectura; la procedencia retiene el identificador de cada objeto.

CEEE cuenta contenidos canónicos documentales A con identidad de inscripción no conflictiva y sin fecha posterior a captura; otras relaciones se presentan aparte como incidencias. Se muestran distribuciones separadas de consumo/emisiones, fechas declaradas y ámbitos. Los contenidos no son inmuebles únicos ni prueba de vigencia. La letra de una vivienda no se extiende al edificio; «edificio completo» sigue siendo un ámbito declarado.

PRTR cuenta expedientes únicos confirmados por parcela. El importe corresponde al expediente completo, aunque haya varias parcelas. Se muestra el nombre del programa; P4 corresponde a vivienda. La fecha de actualización no se transforma en concesión; no consta fecha individual contrastada en el caso real. No se infieren pago, inicio ni terminación. Plan Rehabilita no se incorpora.

Conservación separa órdenes históricas, obligaciones ITE, obligaciones IEE, licencias y declaraciones. Las obligaciones no prueban realización ni resultado. La declaración de Bailén no se presenta como resultado de inspección. No se realizan consultas REC automáticas; se mantienen los controles y resultados expresos en la sección técnica, con su identidad y fecha independientes.

Los seis estados son: documentada, asociada a parcela, parcial, ambigua, no disponible y fuente no cubierta para ese municipio. La ausencia en una captura consultada se distingue del error de lectura/integridad y de la falta de cobertura territorial. Las advertencias de ámbito están junto a su sección, sin semáforos diagnósticos. En modo público no se recuperan evidencias protegidas ni se amplía la exportación HTML.

Las comprobaciones previas dependen de hechos: varios accesos, falta de CEEE utilizable tras consulta de la fuente, concesión registrada, antecedentes de órdenes/obligaciones o uso distinto del residencial. Ninguna regla recomienda rehabilitar por antigüedad, asigna puntuaciones o clasifica oportunidades.

## Casos reales

Selección reproducible en `tests/benchmark_commercial_fiche.py`: Bailén conocido; primera CP por referencia en los hechos del índice con cada evidencia solicitada; primera sin construcción ni eventos/energía/ayudas; y CP Getafe con más relaciones A (caso exigente, no muestra representativa). `real_cases_verified.json` conserva modelo, entidades, datos, filas seleccionadas y mediciones. No es contraste independiente de identidad física ni de exactitud postal.

| Caso | CP | Resultado documental |
| --- | --- | --- |
| Bailén 16, Madrid | `9540103VK3794B` | Dos accesos: Bailén 16 / Yeseros 6. BU histórico residencial, años 1890–1890 y 11 viviendas declaradas por objeto; no superficie/plantas en producto Madrid. Sin CEEE ni PRTR vinculados. Una declaración responsable 10/01/2024, sin órdenes/obligaciones ni resultado actual acreditado. |
| Cristo de la Victoria 239, Madrid | `0002601VK4700A` | Dos contenidos CEEE: E consumo y E emisiones; uno de edificio completo declarado (30/12/2024), otro de vivienda (17/06/2026). Sin letra atribuida al portal. |
| Isabelita Usera 72, Madrid | `0004407VK4700C` | Obligación IEE observada; 31/12/2025 es plazo de obligación, no fecha de una inspección. Sin resultado vigente acreditado. |
| Ribadavia 16, Madrid | `0006716VK4800E` | Expediente `10-PRV1-01927.7/2022`, P4, 1.253,74 € concedidos; actualización fuente 20/07/2026, sin fecha individual de concesión contrastada, pago ni obras acreditados. |
| Getafe | `4836301VK4643N` | 1.014 objetos con relación documental A. Se resumen valores distintos y tipos; identificadores y tablas completos plegados, sin suma de partes. 21 relaciones energéticas recuperadas, con calidad propia. Sin fuente municipal de conservación ni postal piloto. |
| Alberdi 27, Madrid | `0000602VK4800A` | Sin construcción, CEEE, PRTR ni eventos en las fuentes integradas; tres accesos documentados. Sigue siendo útil comprobar portal/comunidad y solicitar CEEE. |

Los cinco pilotos conservan su cobertura catastral parcial. Ninguno dispone de índice postal fiable. No se interpreta fuente municipal no cubierta como cero incidencias.

## Rendimiento

`real_cases_verified.json` mide recuperación por fuente, construcción del modelo, repetición, memoria Python con tracemalloc y máximo RSS del proceso (incluye bibliotecas, cachés y casos previos, no memoria incremental de una parcela). La instrumentación añade coste y se ejecutó mientras había pruebas: no son garantías de latencia.

En esa ejecución: recuperación+modelo Madrid 303–737 ms, repetición 102–199 ms. Getafe exigente: 1.121 ms iniciales, 443 ms repetición; construcción del modelo 348 ms instrumentados. Pico Python por caso 4,58–13,42 MiB; máximo RSS acumulado del proceso 721,5 MiB. Los valores exactos y su alcance están en el informe.

`fiche_render_final.json` aplica el mismo muestreo de sesión 20: Bailén 12, Lillo 14 y Marina Vega 59 A, sin seleccionar por abundancia de evidencias. Apertura completa AppTest: 1,12–1,72 s; repetición 0,19–0,39 s. Sesión 20 documentaba 1,63–1,80 s y 0,27–0,42 s, respectivamente. No se observa regresión en esta muestra; procesos/cachés/concurrencia varían y no constituye una comparación controlada ni pintura del navegador.

Se corrigió la construcción reiterada de Series por objeto en el modelo (diccionarios de atributos una sola vez), se reutilizó la lectura constructiva y se hizo selectiva la lectura PRTR. El buscador y su índice permanecen intactos.

## Validación y comandos

No hay dependencias nuevas ni build adicional. Instalación y suite general se mantienen:

```bash
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_commercial_fiche.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_address_search.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session19_integration.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src/madrid_rehab/commercial_fiche.py src/madrid_rehab/commercial_data.py src/madrid_rehab/commercial_view.py src/madrid_rehab/municipal_fiche.py src/madrid_rehab/cadastral_identity.py src/madrid_rehab/address_view.py tests/test_commercial_fiche.py tests/test_address_search.py tests/test_session16_fiches.py tests/benchmark_commercial_fiche.py tests/browser_commercial_fiche.py
git diff --check
PYTHONPATH=src .venv/bin/python tests/benchmark_commercial_fiche.py --output reports/session_21_commercial_fiche/replay_nuevo.json
MADRID_REHAB_DEMO=0 MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python tests/benchmark_address_fiche.py --output reports/session_21_commercial_fiche/render_nuevo.json
```

14 pruebas nuevas pasan (incluyen seis casos reales, datos ausentes/nulos, pluralidad de usos/accesos, ámbito de años, CEEE de distinta naturaleza e incidencias, concesión, historia administrativa, reglas deterministas, CP/BU, privacidad, fuente fallida, apertura postal y vuelta/nueva búsqueda). Pasan también las 16 del buscador y 7 de integración S19, con explorador/mapa y recorridos CP→BU→CP. La aserción S20 comprueba ahora el título postal; dos aserciones históricas S16 buscan la referencia en el encabezado técnico secundario, conservando la comprobación de identidad sin exigirla como título principal.

Navegador: **BLOQUEADO**, falta `/tmp/madrid-rehab-browser/chromium_headless_shell-1194/chrome-linux/headless_shell`. El lanzamiento falla antes de conectar al servidor; no hay capturas, validación WebGL ni comprobación visual de alineación, recorte horizontal, tamaño normal o accesibilidad. `browser_01/browser.json` conserva el error. No se descargó Chromium. AppTest no sustituye esta revisión.

Con un navegador ya disponible y servidor local iniciado:

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_commercial_fiche.py --output-dir reports/session_21_commercial_fiche/browser_nuevo
```

El guion prepara tres recorridos: buscar/seleccionar/abrir, consultar procedencia de antecedentes/CEEE/PRTR, abrir detalles técnicos, volver y cambiar dirección. Queda pendiente ejecutarlo y revisar visualmente las capturas, incluidos otros anchos de ventana.

## Limitaciones y siguientes fuentes a investigar

Antigüedad, uso, viviendas catastrales, letras de certificados parciales, concesiones y órdenes antiguas **no permiten identificar necesidades reales de rehabilitación**, ahorro potencial, presupuesto, solvencia, voluntad de la comunidad ni oportunidad comercial. No existe diagnóstico físico actual ni vinculación física independiente de los portales y objetos BU. No se calcula ninguna de esas magnitudes.

Fuentes futuras de valor (investigación fuera de esta sesión, sin adquisición): AD/callejeros oficiales con vínculos CP/BU y fechas para los pilotos; resultados ITE/IEE actuales y dictámenes REC con autorización acreditada; Plan Rehabilita con identidad/estados/fechas claros; pagos y justificaciones finales de ayudas; actuaciones efectivamente ejecutadas; protección patrimonial y restricciones urbanísticas; identificación documental de comunidad y portales, accesibilidad y ascensores con ámbito verificable. Necesitan licencia y evaluación de identidad/cobertura antes de integrar.

Pendientes: revisión visual conjunta y teclado, contraste independiente de direcciones, cobertura postal piloto, actualización de fuentes y licencias de redistribución PRTR/administración. El resumen no se añade a la exportación HTML mientras falten permisos. Los resultados expresos REC permanecen en el detalle técnico; no se han incorporado actas nuevas ni se acreditan resultados actuales desde las capturas administrativas.

Para abrir:

```bash
MADRID_REHAB_DEMO=0 MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Visitar `http://127.0.0.1:8512`, buscar `Calle Bailén 16`, seleccionar expresamente y abrir la ficha. El nivel comercial está primero; «Detalles técnicos · seis secciones y datos originales» conserva la consulta anterior. Sin commits, push, publicación, descargas ni modificación de snapshots.

## Cierre de verificaciones

Suite general final: **510 pruebas, OK**, 719,089 s (`full_tests_release.log`). Pruebas focalizadas: 14 comerciales, 16 del buscador, 7 de integración S19 y 4 de resistencia S16, todas OK. Ruff global, formato de los 11 archivos Python modificados y `git diff --check`: correctos. `validation_summary.json` distingue resultados finales y bloqueo visual. Se preservan las modificaciones previas de sesiones 19/20 y no se han hecho commits, push, descargas ni cambios en snapshots.
