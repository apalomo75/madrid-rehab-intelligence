# Navegación y ficha municipal compartidas

La entrada normal abre **Explorar municipios**. La demostración y la navegación regional usan el mismo explorador. El selector de inmuebles muestra Madrid, Getafe, Móstoles, Leganés, Alcorcón y Alcalá de Henares. Los otros 173 municipios permanecen en los productos territoriales y estadísticos, sin modificaciones.

## Componentes compartidos con Madrid

`municipal_navigation.py` implementa municipio → zona → parcela/objeto, búsqueda, selección gráfica, limpieza y distribución mapa/ficha en dos columnas. Reutiliza `city_maps.unit_selection`, que valida la identidad seleccionada contra los objetos realmente visibles, y `regional_view.geometry_deck`. Madrid y los pilotos ejecutan exactamente este componente, tanto para CP como para BU independientes.

`municipal_fiche.py` define una sola ficha con seis apartados, siempre en este orden:

1. Identificación.
2. Características constructivas.
3. Certificados CEEE.
4. Conservación e ITE/IEE.
5. Subvenciones PRTR.
6. Calidad, limitaciones y procedencia.

Se reutilizan `energy_view.render_energy_parcel` (incluidos niveles de vínculo y ámbito), `conservation_view.render_conservation_parcel`, `rec_view.render_rec_parcel`, el lector de expedientes de `grants_view` y los contratos de integridad distritales de `city_store`. La ficha incorpora los atributos constructivos de Madrid ya disponibles. Los apartados sin fuente permanecen visibles con «No disponible en las fuentes integradas». La exportación HTML sigue limitada a identificación; no exporta evidencias pendientes de revisión de redistribución.

La vista analítica histórica **Madrid capital**, con 21 distritos y sus filtros, sigue accesible en la barra lateral para preservar el análisis previo. No es la navegación principal de inmuebles ni un requisito para abrir las fichas de Madrid en el explorador común.

## Cobertura y diferencias justificadas

El selector se deriva de los manifiestos de particiones CP/BU aceptadas, no de una lista de seis códigos. Para Madrid se verifican los hashes históricos CP y BU. Los nombres proceden del catálogo territorial conservado. Incorporar una nueva partición validada al producto integrado permite ampliar el selector sin añadir códigos al componente.

Los cinco pilotos tienen cobertura parcial; se muestra expresamente. Sus BU conservan atributos e identidades independientes (incluidos Building/BuildingPart) y pueden explorarse en el mapa. Nunca se utiliza una referencia incidental ni una coincidencia espacial para atribuirles CEEE, PRTR, NDP o conservación de una parcela. La ausencia de una relación BU–CP deja esos apartados sin evidencia atribuida.

Madrid dispone de relaciones documentales y atributos BU históricos, antecedentes municipales y accesos NDP. REC se presenta solo en Madrid y mantiene sus requisitos previos de habilitación y selección expresa de un portal verificado; abrir una ficha no ejecuta consultas. Los pilotos no ofrecen enlaces ni consultas REC de Madrid. Obligaciones ITE/IEE y órdenes no son dictámenes ni acreditan estado físico o subsanación.

Los lectores de energía y subvenciones mantienen municipio y referencia como claves; los niveles ambiguos/candidatos no se convierten en confirmaciones. Los importes siguen perteneciendo al expediente único. El modo público conserva las protecciones CEEE, PRTR y conservación.

## Recorrido espacial y límites

El índice ligero incluye todos los identificadores únicos con geometría utilizable. Se excluyen todas las ocurrencias de identidades ambiguas. Se asigna cada objeto a una celda de 1 km mediante sus coordenadas de referencia (CP) o centro de envolvente (BU). Son celdas de navegación, nunca barrios oficiales. Un objeto que cruza una celda permanece accesible en la celda asignada, con su geometría completa.

La vista general pagina las celdas y cada celda pagina sus objetos: máximo 500 geometrías por carga. Se muestran denominador y página. El orden por identificador se aplica después de seleccionar la celda; recorrer todas las páginas recupera la totalidad del índice, independientemente del orden de las filas del archivo. Buscar un identificador abre su celda y página. Se pueden volver a elegir Vista general y otras zonas. La ficha tiene desplazamiento interno junto al mapa.

## Validación reproducible

Instalación: `.venv/bin/python -m pip install -r requirements.lock`.

Suite: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`.

Navegación común: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_municipal_navigation.py -v`.

Regresión regional: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_regional_navigation.py -v`.

Lint: `.venv/bin/ruff check src tests`.

Servidor: `MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512`.

Navegador (servidor previo; salida nueva): `PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_municipal_navigation.py --output-dir reports/municipal_navigation/browser_nuevo`.

Las pruebas comprueban exhaustividad y ausencia de duplicados al recorrer las páginas CP, estructura idéntica y controles de ficha en los seis municipios, BU independientes, limpieza, evidencias reales, protecciones y regresiones del analista de Madrid. AppTest no sustituye la selección real en WebGL. En este entorno el servidor local está bloqueado por `PermissionError: [Errno 1] Operation not permitted` al crear el socket. Chromium también falla al arrancar por restricciones del sandbox (`sandbox_host_linux.cc`, `Operation not permitted`); el resultado se conserva en `reports/municipal_navigation/browser_six_01/browser.json`. La validación visual queda **bloqueada**, no superada; tampoco se acredita una revisión visual conjunta.

No se descargan, reconstruyen ni modifican snapshots históricos, ni se realizan commits, push o publicación.

## Resultado de esta ejecución

Suite completa: **457 pruebas, OK**. Tras reiniciar también la selección gráfica al pulsar Limpiar, se repitió la suite específica: **4 pruebas, OK**, con fichas CP y BU de los seis municipios. Ruff y el formato de los módulos nuevos pasan. Logs y resumen: `reports/municipal_navigation/validation_01/`. La validación visual permanece bloqueada por sockets y sandbox de Chromium; no se acredita clic WebGL real ni revisión visual humana.

## Corrección posterior del flujo y límites de validación

La auditoría posterior y la navegación por un solo mapa se documentan en
[diagnostico_navegacion_municipal.md](diagnostico_navegacion_municipal.md).
Incluye causas confirmadas del mapa territorial inerte/duplicado, hipótesis del
panel vacío, contrato serializado del callback y pasos de comprobación en Ubuntu.
Los resultados anteriores de AppTest no acreditan selección real WebGL.
