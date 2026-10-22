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
