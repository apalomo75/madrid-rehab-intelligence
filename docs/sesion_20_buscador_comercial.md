# Sesión 20 — Buscador comercial y cobertura postal

La aplicación abre «Buscar por dirección». Un comercial elige municipio, introduce calle y número (o «CL Bailén 12»), pulsa **Buscar** o Enter, selecciona expresamente el acceso y abre la ficha. Puede volver a resultados conservando la consulta o limpiar. No necesita mapa, referencia, BU, NDP ni cuadrícula. Los identificadores de acceso aparecen únicamente para distinguir versiones/resultados; las referencias de parcela solo se piden cuando hay varias vinculadas. No hay puntuaciones ni estimaciones de viviendas, obras o superficie rehabilitable.

El estado inicial de Git contenía cambios de sesión 19 en AGENTS/README, ficha, navegación y pruebas, además de sus módulos/documentación nuevos. Se preservaron; no se hicieron commits, push, descargas ni modificaciones de snapshots históricos. La única adaptación a una prueba previa cambia la expectativa de portada y después verifica que «Explorar municipios» sigue funcionando.

## Cobertura medida, no exhaustividad municipal

Resultados reproducibles: `reports/session_20_address_search/address_coverage.json`.

| Municipio | Versiones postales indexadas | Confirmadas a CP | Ambiguas | Sin vínculo confirmado | CP distintas accesibles |
| --- | ---: | ---: | ---: | ---: | ---: |
| Madrid | 214.083 | 206.982 | 730 | 6.371 | 128.998 |
| Getafe | 0 | 0 | 0 | 0 | 0 |
| Móstoles | 0 | 0 | 0 | 0 | 0 |
| Leganés | 0 | 0 | 0 | 0 | 0 |
| Alcorcón | 0 | 0 | 0 | 0 | 0 |
| Alcalá de Henares | 0 | 0 | 0 | 0 | 0 |

Los ceros piloto significan **fuente postal local insuficiente**, no ausencia de direcciones o edificios. No hay denominador postal conocido ni porcentajes calculables allí (`null`). Sus capturas CP/BU son parciales y siguen consultables por el explorador, incluida la integración de sesión 19.

Madrid: 214.676 filas oficiales con calle/número y 214.278 NDP distintos; se excluyen del buscador de números de portal 593 filas cuya clase es KILÓMETRO. Las 214.083 versiones restantes corresponden a 213.685 accesos distintos, de los cuales 160.256 son de tipo PORTAL (otros son fachada, parcela, garaje o jardín). No se llaman portales a todos los NDP. Hay 8.621 códigos de vía indexados, 78 accesos con varias versiones, 35.667 CP con varias versiones postales confirmadas (113.651 vínculos dirección–CP en esas parcelas; máximo 136 por parcela) y 24 claves del puente con varias CP candidatas. No hay NDP con varias CP candidatas diferentes en el puente de esta captura. Las 206.982 versiones confirmadas corresponden también a 206.982 accesos distintos. Las 7.101 versiones restantes no permiten abrir una ficha confirmada desde esta ruta.

Las versiones postales y los enlaces del puente tienen granos distintos: las métricas del puente pueden incluir filas sin literal oficial actual. El informe distingue ambos denominadores. La identificación física de edificios permanece sin acreditar.

## Fuentes auditadas

Madrid: `data/processed/conservation/session_14_final_02/conservation_accesses.parquet` (214.676 filas; 33 columnas), `conservation_parcel_links.parquet` (216.061 filas), más CP histórica única/utilizable `data/processed/session_2/parcels_audited.parquet`. Se reutiliza el puente oficial NDP/Código de número ya auditado: [reglas y conflictos](auditoria_matching_callejero.md). No se busca una parcela próxima.

Campos postales: COD_NDP, COD_VIA, VIA_CLASE, VIA_PAR, VIA_NOMBRE, VIA_NOMBRE_ACENTOS, CLASE_APP, NUMERO, CALIFICADOR, TIPO_NDP; access_id, access_version_id, source_row, source_sha256 y procedencia del snapshot. Hay códigos de vía y dos representaciones documentadas del nombre, suficientes para búsquedas exactas normalizadas sin inventar equivalencias.

Pilotos: se autentican las cinco particiones de sesión 18 y se revisa `address_references_json`, derivado de los GML BU ya descargados. La auditoría reproducible de los 15 GML BU originales (`tests/audit_address_sources.py`, `raw_ad_audit.json`) verifica los hashes de los ZIP y recorre también los objetos excluidos y OtherConstruction: 338.280 declaraciones AD, todas con href, cero con texto o hijos y cero Address embebidos. En esos originales, `addresses/@xlink:href` es una URL Catastro WFS `GetadByRefcat` con `refcat`, sin calle ni número. No se ejecutan esas URLs. Las 332.746 declaraciones de objetos aceptados son referencias de consulta AD, con cero literales postales. La referencia AD no acredita una dirección consultada ni añade una relación CP/BU diferente de las revisadas en sesión 18.

| Municipio | CP aceptadas sin dirección recuperable | BU aceptados con URL AD / BU aceptados |
| --- | ---: | ---: |
| Getafe | 16.149 | 93.014 / 93.014 |
| Móstoles | 8.980 | 56.591 / 56.591 |
| Leganés | 10.541 | 59.506 / 59.506 |
| Alcorcón | 5.734 | 37.595 / 37.595 |
| Alcalá de Henares | 13.037 | 86.040 / 86.040 |

No existe muestra postal positiva real piloto verificable con estos productos. Las pruebas de esos municipios comprueban aislamiento, limitación explícita y regresiones de sus fichas existentes; no inventan calles positivas. Para habilitarlos hacen falta datos oficiales AD descargables o callejeros municipales: ID estable de dirección/acceso y versión, municipio, código/tipo/nombre de vía, número y clase, complemento, referencia CP explícita y, si existe, relación BU explícita; fechas y licencia. Un catálogo de nombres de calles sin puentes CP no basta. No se realizó búsqueda web de nuevas fuentes.

## Arquitectura, esquema e integridad

`address_search.py`: normalización, generación offline, SQLite de solo lectura, búsqueda acotada y hechos de parcela para el resumen. `address_view.py`: único formulario compartido y ruta comercial. `city_app.py`, invocado desde **app.py**, incorpora esa entrada antes de los tres exploradores existentes. No hay reescritura de mapas ni de la ficha.

Producto predeterminado: `data/processed/addresses/session_20_01/addresses.sqlite` (~189 MiB) y `manifest.json`. No duplica geometrías, CEEE completos ni atributos BU. Tablas:

- `addresses`: una versión postal por fila; ID estable, access_id, municipio, original, calle/tipo/número/complemento originales, claves normalizadas, código de vía, tipo de acceso, estado, listas JSON de CP confirmadas/candidatas, motivo, fila y SHA-256 fuente.
- `aliases`: ID de versión, municipio y grafía normalizada documentada (nombre con/sin partícula oficial y tipo). Índice compuesto municipio/grafía y acceso por ID.
- `parcel_facts`: municipio/CP, años constructivos y disponibilidad, recuentos de certificados, expedientes PRTR confirmados, eventos administrativos y conservación. No sustituye a las evidencias originales.

El manifiesto guarda política versionada, SHA-256 de entradas, manifiestos y producto. Al primer acceso se verifican bytes; siguientes consultas reutilizan verificación con clave de tamaño/mtime/ctime de todas las entradas. Un cambio invalida caché y bloquea el índice si el hash difiere. Un cambio de captura activa de PRTR o un override incompatible de CP, energía, conservación, administración o sesión 7 bloquea el resumen para impedir mezclar capturas. Los overrides de capturas no soportados requieren adaptar/revisar la generación, no simplemente silenciar la comprobación. `MADRID_REHAB_ADDRESS_DIR` selecciona otro índice reproducido con las mismas fuentes soportadas.

La generación rechaza directorios existentes. No escribe punteros activos. La app usa SQLite en modo solo lectura. Solo un envío de formulario ejecuta búsqueda; no hay carga por pulsación. Hasta 100 resultados por página con navegación explícita. Las sugerencias son prefijos exactos de grafías integradas y solo aparecen tras buscar sin resultado. No hay fuzzy matching ni geocodificación externa.

## Normalización y resolución

Se pliegan mayúsculas, tildes y espacios; CL/C → CALLE, AV/AVDA → AVENIDA, PZ/PL/PZA → PLAZA y PS → PASEO. Se conserva el original. No se eliminan partículas ni signos internos, ni tipos de vía: «CALLE MAYOR» no se convierte en «PLAZA MAYOR». La búsqueda sin tipo puede devolver varias vías; el usuario decide.

Número entero exacto, sin vecinos (24 nunca es 26); se aceptan ceros iniciales como grafía numérica. Complementos se conservan; no se interpreta DUP como B ni se colapsan letras. Complemento vacío busca todos los complementos para selección. Dirección completa solo se interpreta si acaba en un entero, opcionalmente una letra o BIS; rangos y formatos dudosos no se expanden. Con calle y número separados se admiten los números y complementos originales sin interpretación aproximada.

Todos los estados/versiones del puente se consideran. Solo `confirmed_access_parcel` sin contradicción en otras filas del acceso, con CP única y utilizable, produce `confirmed`. Conflictos quedan `ambiguous`, sin CP abrible. Candidatos o ausencia quedan `unlinked`, sin promoverlos. Las CP candidatas permanecen para auditoría. Si una futura fuente documenta varias CP confirmadas para un acceso, el componente exige otra selección explícita; esta cardinalidad se prueba con fixture, pues no existe en los NDP reales actuales. Varias versiones o accesos con igual calle/número se presentan separadamente, nunca se fusionan atributos.

Ejemplo real: «CL BAILEN 12» y «CALLE BAILÉN 12» recuperan el mismo acceso confirmado, CP `9542204VK3794A`. «CALLE SAN BERNARDO 91» tiene antecedentes de identidad CP ambigua; se conserva la revisión. «CALLE MIRA EL SOL 25» incluye el NDP no vinculado del audit histórico. Las muestras reales detalladas están en los benchmark JSON con IDs de fuente y resultados. La frase sin coincidencias es: **No hemos encontrado esta dirección en las fuentes integradas.** No se declara que el inmueble no existe.

## Ficha y resumen

La ruta llama `municipal_fiche.render_fiche(code, name, ref)` sin mapa ni objetos precargados. Se mantienen los seis apartados, lectores autenticados, detalles constructivos y navegación documental CP→BU→CP de sesión 19. El buscador no solicita REC ni modifica sus autorizaciones.

Cabecera «Dirección localizada»: dirección/municipio, vínculo documental a parcela, años asociados a objetos de la parcela, certificados CEEE con advertencia de ámbito, expedientes PRTR confirmados, conservación disponible y limitaciones. No se presenta una antigüedad o uso único del portal como si fuera edificio físico. El resumen enumera los usos declarados de objetos asociados a la parcela; sus valores propios y procedencia permanecen en los detalles constructivos. Cero registros significa ausencia en captura, no ausencia real. Estado actual, necesidad de obras y dictámenes REC no están acreditados.

El resumen es exclusivamente de CP; se oculta durante la navegación a BU. La ficha BU no recibe certificados, ayudas ni conservación de CP. En modo público se muestra únicamente identificación y el aviso de protección, preservando las restricciones anteriores. No se exportan nuevas evidencias.

## Utilidad, muestras y rendimiento

Sobre **128.998 CP distintas accesibles por dirección**, no edificios de Madrid: 119.349 tienen información constructiva (92,52%); 51.641 certificados CEEE (40,03%); 3.210 expedientes PRTR confirmados (2,49%); 49.826 antecedentes administrativos (38,63%); 9.036 antecedentes de conservación (7,00%). Las dimensiones se solapan y no se suman. Energía conserva niveles y ámbitos; PRTR cuenta expedientes únicos por parcela, nunca suma importes entre vínculos. Conservación no equivale a inspecciones realizadas ni resultados.

`tests/benchmark_address_search.py`: muestra determinista espaciada por ID de todo el índice, más cada estado. 21 casos postales reales Madrid (18 confirmados) y cinco comprobaciones negativas de aislamiento piloto sin muestra positiva inventada. No se selecciona por abundancia de datos. Registra consulta, versión esperada, resultados, estado, disponibilidad de ficha, construcción y hechos CEEE/PRTR/conservación, y tiempos. Es una **reproducción documental interna**, no validación independiente ni estimación de precisión. No se afirma 100% de precisión a partir del mismo índice.

Primera medición en `search_benchmark.json`: búsqueda sin número mediana 2.855 ms. El plan de SQLite recorría direcciones antes de filtrar alias. La consulta corregida empieza con el índice selectivo de municipio/vía. Medición final en `search_benchmark_optimized.json`: mediana calle 2,77 ms (máximo 7,99); portal 2,31 ms (máximo 6,41); segunda búsqueda 2,12 ms (máximo 4,52). Verificación de integridad inicial 635 ms. Identidad CP primera consulta mediana 549 ms (máximo 777), segunda 1,80 ms; atributos constructivos mediana 35 ms. Son tiempos Python locales de consulta/resolución, **no latencia total de renderizado de toda la ficha ni del navegador**. Las cachés existentes evitan lecturas repetidas de identidad. Las cifras dependen de almacenamiento y concurrencia de pruebas.

`tests/benchmark_address_fiche.py` mide además la apertura de los seis apartados y el resumen en Streamlit/AppTest para el primer, mediano y último ID confirmado, sin filtro por evidencias: Bailén 12, Lillo 14 y Marina Vega 59 A. Primera apertura completa en servidor: 1,63–1,80 s; repetición: 0,27–0,42 s; envío de búsqueda con rerun de Streamlit: 43–86 ms. Artefacto: `fiche_render_benchmark.json`. Incluye ejecución Python, no pintura en navegador.

## Uso y regeneración

Instalación: `.venv/bin/python -m pip install -r requirements.lock`. Sin nuevas dependencias ni build. Generación offline y comandos completos en README; nunca reutilizar directorios:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.address_search
PYTHONPATH=src .venv/bin/python -m madrid_rehab.address_search --output-dir data/processed/addresses/replay_nuevo --report-dir reports/session_20_address_search/replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_address_search.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_address_search.py --output reports/session_20_address_search/benchmark_nuevo.json
PYTHONPATH=src .venv/bin/python tests/audit_address_sources.py --output reports/session_20_address_search/raw_ad_audit_nuevo.json
MADRID_REHAB_DEMO=0 MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python tests/benchmark_address_fiche.py --output reports/session_20_address_search/fiche_render_nuevo.json
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src/madrid_rehab/address_search.py src/madrid_rehab/address_view.py tests/test_address_search.py tests/benchmark_address_search.py tests/browser_address_search.py tests/audit_address_sources.py tests/benchmark_address_fiche.py src/madrid_rehab/city_app.py tests/test_municipal_navigation.py
git diff --check
```

## Validación visual y pendientes comerciales

Se comprobó que el puerto 8512 estaba libre antes de arrancar el comando oficial con `MADRID_REHAB_OFFLINE=1`. El servidor arrancó. La prueba de navegador **está bloqueada**: falta `/tmp/madrid-rehab-browser/chromium_headless_shell-1194/chrome-linux/headless_shell`. Evidencia: `browser_01/browser.json`. No hay capturas ni validación visual acreditada. AppTest solo prueba controles/estado y no sustituye navegador ni revisión humana.

Reproducción en un entorno con Chromium (servidor previo):

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser .venv/bin/python -m playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_address_search.py --output-dir reports/session_20_address_search/browser_nuevo
```

Pendientes para producto comercial: fuente postal oficial con puentes documentales para los cinco pilotos, contraste independiente y actualidad de direcciones, revisión humana de ambigüedades, validación visual/teclado exhaustiva, licencias de redistribución pendientes y medición de latencia integral de ficha. El buscador tolera grafías documentadas, no errores ortográficos arbitrarios. No acredita cobertura postal completa ni física del parque.

## Resultado de validación

Suite completa ejecutada: **492 pruebas, OK**, 863,732 segundos (`full_tests.log`). Ejecución final específica del buscador: **16 pruebas, OK**, 9,722 segundos (`address_tests_final_02.log`), incluidas selección de varias CP con fixture explícita y rechazo de resultados reales ambiguos/no vinculados. Las pruebas existentes verifican CEEE/PRTR y ausencia de transferencia a BU, Madrid, los cinco pilotos y navegación por mapas. No sustituyen la revisión visual.

Ruff: correcto. Formato de los nueve archivos de esta sesión: correcto. `git diff --check`: correcto. La comprobación **global** de formato detecta siete archivos previos (`cli.py`, `http.py`, `integrate.py`, `pilot.py`, `pipeline.py`, `sources.py`, `test_pipeline.py`): se comprobó que son idénticos a HEAD y que también fallan formato en HEAD; no se modificaron. Evidencia: `format_all.log`, `format_baseline.json`. Integridad de entradas e índice comprobada tras la suite. Resumen: `validation_summary.json`.
