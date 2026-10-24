# Uso local del visor · sesión 3

Desde la raíz del repositorio:

```bash
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512 --server.headless true \
  --browser.gatherUsageStats false
```

Abrir http://127.0.0.1:8512. Lee los resultados existentes de sesión 2 y comprueba sus hashes; no hay que volver a ejecutar la ingesta ni la integración. `MADRID_REHAB_SESSION2_DIR=/ruta/local` permite utilizar otra reproducción verificable.

Para iniciar sin peticiones cartográficas externas:

```bash
MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python -m streamlit run \
  src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

## Explorar mapa

La vista inicial representa 3.311 agregados catastrales de uso residencial declarado en Chamberí. Al desactivar el filtro de uso aparecen 3.761. Un agregado BU puede reunir distintos cuerpos construidos; no equivale necesariamente a un bloque físico.

Arrastra para desplazarte y usa la rueda para acercarte. Haz clic en el interior de un polígono: la ficha debe aparecer a la derecha con su identificador BU y referencia de parcela, y el contorno seleccionado será azul. La selección se almacena por identificador, separada del índice gráfico. Navegar conserva la selección; «Limpiar selección» la borra y restablece la vista inicial. El clic en el fondo o la limpieza nativa de PyDeck no borra la ficha; utiliza el botón de la ficha.

Los cambios de filtros renuevan el componente para descartar eventos antiguos y restablecen la vista. Si el BU sigue visible conserva su ficha y contorno; si queda excluido se limpia la selección y se avisa. La búsqueda alternativa por identificador público está en un desplegable bajo el mapa; los resultados se limitan a los 15 primeros elementos visibles coincidentes.

**La aceptación visual de esta interacción está pendiente:** el entorno de desarrollo de esta sesión impide abrir Streamlit y Chromium. Véanse los intentos en `reports/session_3/` y la prueba reproducible de navegador indicada abajo.

El interruptor «Mapa urbano» activa calles y rótulos de OpenStreetMap, con atribución visible. Solicita únicamente las teselas de la vista actual al proveedor externo; necesita internet, no utiliza claves ni descarga mapas por adelantado. Si no carga, desactiva el interruptor: las geometrías oficiales y sus fichas siguen disponibles sobre fondo local. No habilites descargas masivas. El navegador gestiona la caché HTTP ordinaria.

## Modos y ficha

- **Disponibilidad de información:** certificados confirmados a parcela en turquesa; información sin confirmación en naranja; ausencia de CEEE vinculados en esta captura en gris. Los filtros energéticos están desactivados y sus valores anteriores no se aplican.
- **Exploración energética:** filtra registros por ámbito, letra, año de la fecha declarada (incluye opción sin fecha), estado y nivel de vínculo. Un polígono indica presencia de registros que cumplen esos filtros en su parcela. Un BU con otros certificados que no cumplen el filtro se oculta, sin reclasificarlo como carente de información.

La casilla de elementos sin CEEE es independiente: añade únicamente BU realmente sin contexto en estas tablas. Por eso un filtro energético puede mantener polígonos grises. Las letras nunca se transfieren al polígono; varias letras se muestran como distribución en la ficha. Al seleccionar, se muestra **todo el historial disponible de la parcela**, con el número que cumple los filtros indicado aparte.

La ficha conserva ámbito original, códigos e identificadores de los registros, fechas, superficies declaradas y valores energéticos con unidades. La dirección se declara no disponible; no se infiere del mapa base ni de una vivienda. El intervalo constructivo corresponde a unidades del agregado, no a una reforma. Los números de BU relacionados se refieren a los objetos disponibles en el piloto.

## Análisis y metodología

«Análisis energético» muestra toda la captura piloto sin filtros del mapa: letras, ámbitos y meses de la fecha declarada. Se cuentan versiones de registros, no edificios ni necesariamente certificados administrativos distintos. La cobertura de localización del piloto está condicionada por su selección; consulta la cobertura municipal en «Calidad y metodología».

La tercera pestaña presenta fuentes, auditoría, comparación distrital y limitaciones. El JSON queda en un apartado técnico plegado. Ninguna relación confirma edificio físico, tampoco un ámbito declarado como edificio completo. Los datos de 2025–2026 no son un censo exhaustivo.

## Validación reproducible

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python tests/benchmark_session3.py
.venv/bin/python -m pip install -r requirements-browser.lock
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser .venv/bin/python -m playwright install chromium
# Con el servidor del primer comando en otra terminal y acceso a las teselas:
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src \
  .venv/bin/python tests/browser_session3.py
```

El script exige teselas reales, clics de ratón en puntos interiores de geometrías reales, ficha correcta, persistencia al navegar, limpieza, objeto sin certificados, modo sin conexión y exclusión por filtros. Nunca sustituye el clic por una escritura de estado. Si termina correctamente genera tres capturas y resultados/tiempos en `reports/session_3/`. Si falla, conserva el error y no declara aceptación visual.

## Ampliación sesiones 4–6

Generar `PYTHONPATH=src .venv/bin/python -m madrid_rehab.analytics` una vez; si la salida existe, usar `--output-dir` nuevo. Abrir «Rehabilitación e ITE/ayudas»: universo CP completo de Chamberí, filtros independientes del mapa por disponibilidad energética y referencia, tabla y exportación CSV. Las parcelas no evaluables permanecen visibles. No se muestran inspecciones, ayudas ni IPR ficticios. `MADRID_REHAB_SESSION6_DIR` selecciona otro perfil. La ausencia del archivo se muestra con instrucciones, sin romper el mapa anterior. El perfil comprueba su manifiesto.

Comprobación manual pendiente: abrir pestaña nueva, alternar cobertura, buscar RC14 y exportar CSV; revisar nulos y denominadores; volver al mapa y comprobar selección/filtros/OSM y modo offline. No se ha validado visualmente esta ampliación.

## Exploración ampliada v2

El perfil vigente se lee de `data/processed/session_6_audited/`. Las capturas previas siguen disponibles por `MADRID_REHAB_SESSION6_DIR`. No se recalculan features al cambiar controles: la lectura verificada está en caché y se invalida si cambia un producto/manifiesto.

Filtros combinables AND: cobertura energética, referencia literal, periodo, perfil energético, BU residencial declarado, mínimo de registros y CP única. Selecciones vacías producen cero resultados explícitos. Ordenación por RC, cantidad CEEE, año o proporción, ascendente/descendente y nulos al final. CSV incluye todas las columnas del subconjunto y neutraliza posibles fórmulas. La tabla tiene títulos legibles; el desplegable de explicación individual permite consultar denominadores y avisos.

Gráficos del subconjunto: periodos constructivos, dimensiones disponibles, letras por ámbito (leyenda seleccionable), fechas, dispersión año–E/F/G con zoom y tooltip. El filtro de ámbito afecta solo gráficos energéticos, no altera silenciosamente el perfil de parcela. Comparaciones por periodo o malla CP de 500 m, con tamaños y supresión de proporciones de grupos pequeños. La auditoría de sensibilidad muestra siempre el distrito completo. No hay barrios oficiales nuevos ni IPR global.

Aceptación manual pendiente: probar filtros AND y orden, descargar CSV y contrastarlo con la tabla, explicación individual, leyenda por ámbito, zoom/tooltip, cambios de zona, grupos pequeños, etiquetas y contraste; después confirmar continuidad de clic/ficha, OSM y offline del mapa previo. AppTest valida lógica y construcción de gráficos, no representación real ni entrega de teselas.

## Entrada municipal vigente — sesión 7

`app.py` abre Madrid capital con 21 distritos, agregados, cobertura y comparación. Selector lateral o clic en polígono llevan al distrito; «Volver a Madrid capital» limpia selección. `MADRID_REHAB_PILOT=1` conserva el visor histórico; los scripts antiguos de navegador requieren ese modo. `MADRID_REHAB_SESSION7_DIR` cambia la captura municipal.

El detalle carga un distrito y dibuja una celda de 500 m. CP y BU son capas y fichas distintas; para seleccionar una CP cubierta por BU, desactivar «Mostrar objetos BU» o usar la búsqueda de referencias. La búsqueda recorre el distrito completo y cambia a su celda. El máximo de 2.500 unidades es explícito; si hay truncamiento se informa, sin cambiar indicadores del conjunto filtrado. Las geometrías analíticas nunca se recortan ni se sustituyen por la copia visual.

Filtros energéticos por ámbito, letra, año, nivel y estado; residencial y unidades sin información; activación CP/BU. Los filtros del perfil analítico mantienen ámbito propio, documentado, con estado por distrito. Se conservan tabla AND, ordenación, CSV seguro, explicación individual y gráficos. Por encima de 5.000 puntos, el gráfico se agrega en periodos de 10–20 años y bandas de 5–10% con recuentos reales. No se inventan barrios ni se dibuja un IPR. La comparación municipal permite elegir distritos, ordenar y alternar letras/ámbitos, incluyendo letras no interpretables.

Caché: la portada no carga geometrías CP/BU; cambios de archivos/manifiestos invalidan lecturas. Cambios de distrito limpian la selección; eventos obsoletos se contrastan con IDs visibles y distrito activo. OSM es opcional y `MADRID_REHAB_OFFLINE=1` lo desactiva. Datos reales y auditorías en [sesión 7](sesion_7_expansion_madrid.md).

Verificación manual pendiente: portada con 21 distritos, selección por clic, cambiar a distrito y celda, seleccionar CP y BU, buscar una RC fuera de la celda inicial, filtros vacíos/combinados, exportación y explicación, comparar varios distritos, volver al municipio y repetir en offline. Revisar contraste, cámara, legibilidad y fluidez. AppTest no acredita WebGL, teselas ni clic real. El intento de servidor de sesión 7 falló al abrir socket local, no por un error del producto.

## Navegación por zonas — sesión 7.1

Al entrar en distrito se ve su extensión completa y las zonas de 500 m disponibles. Pulsar una zona abre CP/BU; «Ver distrito completo» permite elegir otra. Se mantiene la búsqueda de referencia/BU en todo el distrito y el selector técnico secundario plegado. «Restablecer filtros» conserva ubicación y limpia ficha. Un objeto excluido por distrito/celda/filtros/capa no conserva ficha. Leyenda municipal y tooltips muestran evidencia energética sobre parcelas del distrito, no potencial de rehabilitación. [Cambios, benchmark y validación pendiente](sesion_7_1_usabilidad.md).

La [sesión 9](sesion_9_integracion.md) documenta escenario D: no hay nuevas capas reales ITE/IEE/ayudas. No se presentan fixtures ni eventos ficticios. Clic WebGL, OSM y legibilidad del nuevo recorrido siguen pendientes de prueba manual; el socket local está bloqueado en este entorno.

## Actividad administrativa — sesión 10

La aplicación municipal incorpora «Actividad y rehabilitación» con archivos reales normalizados. En Madrid aparecen agregados y selector de distrito para lectura selectiva. Dentro del distrito, filtros por fuente, tipo, periodo, categoría, vínculo y estado; series y conteos de expedientes/obligaciones, parcelas confirmadas, repeticiones y no vinculados. Los filtros son independientes de los energéticos.

Al seleccionar una celda, se puede activar «Mostrar eventos confirmados de la celda»: rojo órdenes, azul licencias, violeta declaraciones, amarillo ITE y verde IEE. Se dibujan como máximo 2.500 geometrías de parcelas, nunca ubicaciones territoriales candidatas. Los tipos pueden superponerse en la misma parcela. La ficha CP y la de BU incluyen «Eventos administrativos asociados», siempre con evidencia de parcela, origen, fecha, estado y limitaciones. El estado vacío dice «No se han localizado eventos en las fuentes integradas».

La capa de obligaciones se interpreta como «Obligaciones ITE/IEE pendientes según consulta oficial» de 24/10/2026; no informa resultados, deficiencias ni infracciones. La convocatoria BOCM no se muestra como ayuda concedida. Exportación CSV neutralizada contra fórmulas y sin raw_json ni campos personales ajenos a la consulta. Las fechas de descarga y licencias de reutilización no verificadas siguen desconocidas; uso local.

La nueva captura se selecciona con `MADRID_REHAB_ADMIN_DIR` (por defecto `data/processed/administrative_events/session_10_final_01/`) y debe corresponder al mismo hash CP municipal. La caché verifica productos y carga una partición distrital; la portada no lee todos los expedientes. Si falta la captura, aparecen instrucciones y el visor energético sigue disponible.

Aceptación visual **bloqueada** en esta sesión: `reports/session_10/server_attempt.log` registra `PermissionError` al crear el socket. Revisar manualmente mapa, leyendas, superposición, clic/ficha CP y BU, filtros, exportaciones y continuidad del recorrido Madrid → distrito → celda; repetir con mapa urbano desactivado. La construcción de la nueva capa en AppTest no acredita su representación real.

## Subvenciones PRTR — sesión 11

Nueva pestaña municipal/distrital «Subvenciones PRTR»: programa, modalidad, importes, año declarado, calidad territorial, tabla y CSV local seguro. Tipología física y datos energéticos individuales no constan: la interfaz lo indica y no los inventa. La ficha CP muestra solo relaciones PRTR confirmadas y distingue expedientes múltiples, viviendas P4 y edificio físico. Concesión no implica pago o ejecución.

El selector «Navegación» separa Madrid capital de «Comunidad de Madrid — Subvenciones». La vista regional conserva toda la captura, agrupa calidad y programa y permite filtrar Madrid confirmado o pendientes/contradictorios. No hay límites municipales oficiales descargados ni comparación exhaustiva entre 179 municipios; el aviso permanece visible. No se muestran fichas CP/BU fuera de la captura municipal.

Captura por defecto `data/processed/grants/session_11_final_03/`, override `MADRID_REHAB_GRANTS_DIR`; verificación de hashes y compatibilidad CP antes de mostrar relaciones. `MADRID_REHAB_PUBLIC=1` desactiva PRTR en todas sus vistas y exportaciones. [Resultados y comandos](sesion_11_subvenciones_prtr.md), [limitaciones y revisión manual](avance_sesion_11.md). Validación visual real pendiente; AppTest no acredita clic o legibilidad.

## Sesión 12 — navegación regional por cobertura

La opción «Comunidad de Madrid — Subvenciones» abre ahora la cobertura municipal de sesión 12. El selector permite los 179 recursos de los feeds oficiales, usando **código Catastro** mientras falta el catálogo INE completo. Al elegir un municipio externo muestra pendientes; no inventa límites, fichas ni cifras de cero ayudas. Madrid enlaza conceptualmente con su navegación completa de 21 distritos en la opción «Madrid capital».

La captura regional PRTR se conserva y permite programa, rango de importe y cobertura CP confirmada. Las métricas indican selección / 7.532 expedientes; los importes se suman por expediente. Los detalles municipales externos solo aparecerán tras aportar asignaciones oficiales verificadas. La tabla principal PRTR muestra columnas breves y nombres legibles; campos originales permitidos quedan en desplegable técnico y CSV seguro local. No se exponen direcciones, atributos originales completos ni variables censales privadas. `MADRID_REHAB_PUBLIC=1` desactiva PRTR también en esta ruta.

Con `MADRID_REHAB_TERRITORY_DIR` apuntando a límites importados se habilita mapa municipal y selector INE. Con `MADRID_REHAB_CADASTRE_DIR` apuntando a particiones verificadas se habilitan selector RC14, contexto de parcelas por ventana y zoom (máximo 1.500), BU y ficha. Se leen geometrías solo del municipio y selección; al cambiar municipio se reinicia la selección parcelaria. Las geometrías analíticas originales se conservan. Esta rama externa está comprobada mediante fixtures sintéticas, no con datos catastrales reales nuevos.

Datos por defecto: `data/processed/territory/session_12_final_01/` y `data/processed/grants/regional/session_12_final_01/`. Overrides `MADRID_REHAB_TERRITORY_INVENTORY_DIR` y `MADRID_REHAB_REGIONAL_GRANTS_DIR`; deben apuntar a capturas completas y compatibles. El servidor de esta sesión falla con permiso de socket; no hay aceptación visual en navegador. Véase [lista de comprobación manual](avance_sesion_12.md).

## Sesión 12.1: límites y concesiones regionales

La vista regional usa los límites de `data/processed/territory/session_12_1_final_01` y decisiones de `data/processed/grants/regional/session_12_1_final_02`. Selección por INE, polígonos municipales reales, totales y tabla por programa, filtros de calidad A/B/C y CP. Ocre distingue Madrid con CP/BU integrado; azul corresponde a límite municipal sin CP/BU integrado. Concesión geográficamente localizada no confirma parcela, pago, ejecución ni oportunidad comercial.

Los overrides `MADRID_REHAB_TERRITORY_DIR` y `MADRID_REHAB_REGIONAL_GRANTS_DIR` seleccionan replays auditados; la carga catastral sigue siendo selectiva. `MADRID_REHAB_PUBLIC=1` impide cargar y mostrar PRTR. Licencias específicas pendientes: uso local. [Método, resultados y reproducción](sesion_12_1_limites_prtr.md). AppTest pasa; aceptación visual bloqueada por permiso de socket, sin capturas de navegador.

## Sesión 12.2: fichas piloto y cobertura verificada

El directorio catastral por defecto pasa a `data/processed/cadastre/session_12_2_pilot_01`. Los cinco municipios siguen sin CP/BU real por DNS: la vista conserva el mensaje de ausencia, sin parcelas ficticias. Cuando haya una partición auditada, la selección y el mapa excluyen geometrías no utilizables, conservan incidencias y distinguen Building/BuildingPart. Las relaciones PRTR exactas, posibles y ambiguas se etiquetan por separado; ningún importe se reparte entre parcelas.

El comando de piloto publica snapshots nuevos y solo activa un puntero PRTR verificado si incorpora municipios. Overrides anteriores y modo público protegido siguen vigentes. La revisión visual conjunta queda pendiente; AppTest no sustituye navegador real. [Fuentes, ejecución Ubuntu y limitaciones](sesion_12_2_piloto_catastral.md).

## Información energética regional — sesión 13

En «Comunidad de Madrid» aparece un panel CEEE con cobertura observada, municipio, distribución A–G, ámbitos y consulta por parcela aceptada. Los pilotos tienen acceso por este panel aunque su Catastro siga declarado parcial. La ficha de Madrid añade la sección «Información energética regional», conservando las evidencias históricas. Las cifras regionales nuevas aplican reglas más restrictivas para referencias múltiples y no reconocen aún referencias rústicas: 25 confirmaciones históricas no se incluyen en el nuevo resumen; siguen disponibles en la ficha histórica.

Cada observación muestra fecha declarada, consumo/emisiones, valores originales (unidades sin verificar), ámbito, captura y evidencia del vínculo. D identifica ambigüedad/cuarentena, sin confirmación. Sin registros se muestra «No constan certificados vinculados en las fuentes integradas». No se atribuye letra a parcela/edificio. La coexistencia de concesión PRTR no acredita pago, obras ni mejora energética.

`MADRID_REHAB_ENERGY_DIR` selecciona una captura; por defecto `data/processed/energy/session_13_final_03/`. `MADRID_REHAB_PUBLIC=1` oculta esta sección nueva y conserva la protección PRTR. AppTest ha comprobado navegación con datos reales; la inspección visual de navegador sigue pendiente para la sesión posterior. [Detalle y reproducción](sesion_13_energia_regional.md).
