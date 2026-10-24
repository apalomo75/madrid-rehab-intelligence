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
