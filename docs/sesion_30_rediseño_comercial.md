# Sesión 30 — mapa, búsqueda y ficha comercial

La aplicación ya está publicada en https://madrid-rehab-intelligence.streamlit.app, según el contexto del propietario, con código base `26312ed` y paquete del Release `v1.0.0`. Esta sesión prepara cambios locales para revisión del propietario. Sin commit, push, publicación, cambios de despliegue ni reconstrucción del paquete de datos. El árbol estaba limpio al iniciar; se leyeron AGENTS.md, documentación S25–S29, componentes y pruebas existentes.

## Navegación

«Explorar inmuebles» conserva municipio, distrito, filtros OR/AND y páginas. Tras los filtros, dos columnas nativas Streamlit (65/35) contienen mapa y panel lateral. El contador, lista de diez y ficha comparten el panel derecho: seleccionar sustituye la lista por la ficha, en vez de añadirla debajo. «Volver a la lista» recupera la página anterior; esta se conserva separadamente porque Streamlit elimina el estado de widgets ausentes. «Ampliar ficha» abre un diálogo nativo grande. El panel usa un contenedor nativo de altura acotada con desplazamiento propio para conservar el mapa a la vista al recorrer fichas largas. No se manipula el DOM ni se añade CSS.

La selección del mapa usa el callback y el validador `picked` existentes. La selección de lista incluye la parcela en el mapa aunque pertenezca a otra página cartográfica, manteniendo un máximo de 500 geometrías dibujadas. Se destaca el contorno azul y se encuadra la selección a partir de su geometría real. Las columnas usan el comportamiento adaptable nativo de Streamlit; la disposición efectiva en móvil y WebGL quedan pendientes de revisión en navegador.

## Ficha en dos niveles

`commercial_view.render` presenta dirección disponible, municipio, distrito atribuido documentalmente cuando exista, referencia secundaria y uso. Año, viviendas y superficie se muestran como indicadores. Los valores distintos siguen separados: no se suman objetos ni superficies Building/BuildingPart. Una nota común explica el ámbito constructivo y evita atribuir datos al portal.

CEEE muestra número de certificados utilizables, distribución de letras de consumo/emisiones, ámbitos y fechas. No elige un representante ni asigna una letra a la parcela. Los registros individuales mantienen fechas, ámbito, calidad y procedencia. Las relaciones ambiguas no entran en el recuento utilizable y siguen disponibles en detalles.

Plan Rehabilita muestra convocatoria, expediente, actuaciones, subvención revisada, fuente y fecha, por expediente único; varios expedientes se agrupan en una relación desplegable compacta. No se suman importes ni se afirma pago u obra terminada. El ámbito de viviendas sigue siendo el expediente. Los expedientes completos se conservan en los detalles ampliados. PRTR conserva las restricciones existentes; el paquete público no lo recupera.

El render anterior completo se conserva dentro de «Detalles ampliados»: características y procedencia por objeto, CEEE, expedientes, conservación, recomendaciones y errores. Las seis secciones técnicas originales permanecen disponibles, incluida la navegación CP/BU. No hay propagación CP→BU. El diálogo utiliza la misma ficha comercial y los detalles técnicos siguen en el panel de origen.

## Buscar por dirección

La selección confirmada abre automáticamente mapa y ficha, sin un segundo clic obligatorio. Se mantiene el botón de apertura para reabrir una selección tras volver a resultados. El retorno conserva consulta y coincidencia; no vuelve a abrir la ficha automáticamente hasta nueva selección o apertura expresa.

Las etiquetas muestran el literal postal original y municipio. Los nombres oficiales no se transforman; acceso, versión, tipo, hash y referencias permanecen en un desplegable técnico. `parse_query` ya separaba el número final inequívoco: «Calle Bailén 12» equivale a calle «Calle Bailén» y número «12». No se ha cambiado el parser ni los índices.

`commercial_map.py` lee únicamente la CP confirmada del producto existente. Calcula centro y zoom a partir de sus límites, proyectados para visualización sin simplificar ni escribir geometrías. No hay geocodificación. Sin geometría utilizable se conserva la ficha y se informa de la ausencia de mapa. Los cinco pilotos siguen sin búsqueda postal fiable; no se amplía cobertura.

## Inspecciones y conservación

Bloque visible «Inspecciones y conservación»: resultados reales sistemáticos no integrados, obligaciones y antecedentes administrativos diferenciados. Una orden, obligación o archivo no se presenta como resultado de inspección ni estado físico actual.

Se comprobó por lectura de la [consulta oficial REC del Ayuntamiento de Madrid](https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons) el 16/11/2026 que ofrece consulta individual ITE/IEE por dirección o expediente. Se reutiliza `rec_client.official_url()` sin parámetros. No se verificó un enlace profundo por referencia catastral o dirección. El acceso visible abre el formulario externo y ofrece el literal de dirección para copiar. No se hace ninguna consulta automática ni POST; las funciones técnicas REC permanecen intactas. El enlace es específico de Madrid, no se atribuye cobertura a los otros municipios.

## Compatibilidad y permisos

Se conserva el contrato `public-runtime-v1` y el paquete existente `data/deployment/madrid_rehab_v1_02/`, correspondiente al Release v1.0.0. No hay dependencias nuevas, nuevas tablas ni ETL. Los lectores y controles de permisos se mantienen. La prueba pública activa el paquete mediante variables solo en el proceso local; no modifica configuración de despliegue. `smoke_production.py` mantiene el guard que rechaza lecturas Parquet/SQLite fuera del paquete y comprueba que PRTR no se llama.

Las nuevas claves ES/EN están en `i18n.py`, sin renumerar mensajes existentes. Se conservan valores internos y estado al cambiar idioma. Las direcciones y datos originales siguen intactos.

## Validación

Evidencia en `reports/session_30_ux/`. Las pruebas S30 cubren encuadre y geometría intacta, extracción del número, apertura automática Bailén 12, fallback sin geometría, reemplazo de lista por ficha, página preservada y diálogo. Se conservan las pruebas documentales de certificados múltiples, ámbitos y expedientes únicos. Los tests de i18n se ajustan al retorno a lista y a la página guardada mientras la lista está ausente.

El recorrido público comprueba los seis municipios, filtros, distrito, selección/lista, ES/EN, Plan, búsqueda y restricciones, con máximo 500 geometrías serializadas y sin lecturas fuera del paquete. Se añadió además un evento de selección serializado contra el callback real: abre ficha, conserva distrito/filtro y verifica el resaltado. Esto es AppTest, no prueba WebGL ni clic real de navegador.

El intento de navegador está **bloqueado**: falta el ejecutable Chromium en `/tmp/madrid-rehab-browser/`. No se instaló ni descargó. `browser_01/browser.json` conserva el fallo. No hay screenshots ni validación visual; el propietario debe revisar escritorio, móvil, arrastre/zoom, clic real sobre parcelas y encuadre antes de preparar una actualización pública.

Los resultados finales de Ruff, suite general y smoke se recogen en el informe de cierre de esta sesión.

## Comandos

```bash
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session30_ux.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_02 PYTHONPATH=src .venv/bin/python tests/smoke_production.py --output reports/session_30_ux/smoke_otro.json
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_session30.py --output-dir reports/session_30_ux/browser_otro
```

Para revisión manual, anteponer las mismas variables públicas y de bundle al comando Streamlit habitual de AGENTS.md, puerto 8512. Los informes de nuevas ejecuciones deben usar rutas nuevas. No publicar antes de la validación visual del propietario.


## Resultado final

Ruff y comprobación de whitespace correctos. S30: **6/6**; direcciones: **16/16**; ficha: **14/14**; navegación S26: **6/6**; navegación/filtros: **2/2**. Los diez casos i18n pasan en la ejecución general. Smoke público: **18 etapas**, seis municipios, sin errores de ficha, lecturas fuera del paquete ni llamadas PRTR. Verificación del bundle correcta; SHA-256 del archivo S29 sin cambios.

Suite general ejecutada una sola vez: **583 pruebas en 884,254 s, un fallo y un error**. Eran dos expectativas antiguas ya cargadas por el proceso: ausencia de mapa en búsqueda y etiqueta antigua de retorno. Se actualizaron y sus módulos completos pasaron después (16 y 6 casos); no se repitió la suite completa ni se declara verde su log original. Dos casos adicionales del módulo S30 se añadieron después de cargar la suite y están incluidos en sus seis pruebas focalizadas finales.

Evidencia de cierre: `reports/session_30_ux/results.md`, `summary.json`, `acceptance.md`, `session30_review.txt`, `address_final.txt`, `session26_final.txt`, `fiche_final.txt`, `full_suite.txt`, `smoke_review.json`, `bundle_verify.txt` y `release_sha256.txt`. El navegador está bloqueado por Chromium ausente. El servidor local queda en http://127.0.0.1:8512 para revisión del propietario. Sin publicación de cambios.
