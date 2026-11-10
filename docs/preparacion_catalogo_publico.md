# Preparación del catálogo público

## Comportamiento

El modo `MADRID_REHAB_PUBLIC=1` utiliza el mismo catálogo comercial validado que el modo local para los seis municipios. El catálogo mantiene las reglas de inclusión/exclusión de la sesión 24; solo cambia la visibilidad. En Madrid, la búsqueda postal y el mapa consultan las mismas CP admitidas; los cinco pilotos continúan con mapa CP y navegación documental CP/BU, sin índice postal inventado.

Se generó un producto nuevo en `data/processed/commercial_catalog/session_24_public_02/`. El producto histórico `session_24_01` y sus informes no se modificaron. El nuevo manifiesto contiene política, atribuciones, URLs y notas de condiciones por fuente. La ficha pública recupera evidencia selectiva y mantiene los ámbitos originales; el detalle CEEE de vivienda no se convierte en calificación de parcela, las ayudas conservan ámbito de expediente y los antecedentes de ITE/IEE siguen diferenciados de resultados de inspección.

## Cobertura comparada

| Métrica | Local | Público | Diferencia |
| --- | ---: | ---: | ---: |
| CP aceptadas | 194.820 | 194.820 | 0 |
| CP visibles en seis municipios | 153.929 | 153.929 | 0 |
| CP excluidas por el umbral de calidad | 40.891 | 40.891 | 0 |
| Versiones postales Madrid | 214.083 | 214.083 | 0 |
| Versiones postales visibles Madrid | 178.243 | 178.243 | 0 |
| Versiones postales excluidas Madrid | 35.840 | 35.840 | 0 |

Las evidencias por fuente se solapan y no se suman como parcelas:

| Fuente | CP relacionadas en ambos modos |
| --- | ---: |
| Construcción | 149.429 |
| CEEE | 62.588 |
| Conservación/obligaciones identificables | 9.036 |
| PRTR | 4.378 |
| Plan Rehabilita | 1.919 |

Los cinco pilotos no tienen búsqueda postal fiable; sus métricas son CP y objetos catastrales de capturas parciales. No son recuentos de edificios físicos.

## Atribución y condiciones conocidas

- **Catastro:** atribución a la Dirección General del Catastro y enlace al portal INSPIRE. La licencia del producto de origen aplicable debe acompañar cualquier despliegue; no se incluyen datos catastrales protegidos.
- **CEEE:** atribución a la Comunidad de Madrid. El catálogo oficial declara CC BY 4.0; conservar ámbito, fecha y atribución. [Catálogo CEEE](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica).
- **Conservación:** atribución al Ayuntamiento de Madrid y al recurso de órdenes 300377. Cobertura parcial; órdenes históricas y obligaciones ITE/IEE no equivalen a dictámenes. El callejero puenteado conserva su procedencia y calidad de vínculo.
- **PRTR:** atribución al visor de rehabilitación de la Comunidad de Madrid alojado en COAM, con fechas de captura conocidas. La licencia específica del dataset sigue sin verificarse.
- **Plan Rehabilita:** atribución declarada al Ayuntamiento de Madrid, indicando que es un fichero local facilitado por el usuario y su SHA-256. No se verificaron de forma independiente la procedencia oficial, la captura original ni la licencia.

La configuración atiende la instrucción del propietario del proyecto de igualar la visibilidad pública y local del catálogo. No constituye una licencia ni sustituye la autorización documental que falta para PRTR y Plan Rehabilita. Por ello, el producto está preparado técnicamente para la revisión del propietario, pero no se ha publicado ni desplegado. El [portal municipal de reutilización](https://datos.madrid.es/pages/preguntas-frecuentes-sobre-reutilizacion) explica que las condiciones y licencias aplicables dependen de cada documento/fuente.

## Validación y preparación visual

- Suite general ejecutada una sola vez después de estabilizar los cambios: **543 pruebas, 1018,533 s, todas satisfactorias**; resultado en `reports/session_24_public_catalog_02/full_tests.log` y `validation_summary.json`.
- Lectura manual focal en modo público: CEEE en CP 9377401VK3797G (Moncloa); PRTR en CP 0006716VK4800E; Plan Rehabilita en CP 0006718VK4800E; conservación en CP 0004407VK4700C. Se recuperaron las respectivas filas de evidencia con errores de lectura vacíos. Los vínculos permanecen en ámbito CP/expediente y no se interpretan como estado físico u obra ejecutada.
- Ruff: `.venv/bin/ruff check src tests`.
- Validación visual pendiente: no se encontró Chromium en el entorno. AppTest confirma controles y rutas, pero no reemplaza la inspección de mapa/renderizado en navegador.
- Cuando Chromium esté disponible, arrancar: `MADRID_REHAB_PUBLIC=1 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512`.
- Recorridos visuales pendientes: Madrid dirección→CP→BU→CP; los cinco mapas piloto CP→BU→CP; filtros por evidencia; direcciones excluidas; Moncloa 14 y América 113 A; fuentes, atribución y avisos en fichas.
- No se desplegó ni publicó el proyecto. Antes del deployment externo se requiere la validación visual y cerrar la licencia/procedencia de PRTR y Plan Rehabilita, o excluir esas evidencias y recalcular el catálogo conforme a una decisión del propietario.

## Archivos de evidencia

- `data/processed/commercial_catalog/session_24_public_02/manifest.json`: hashes, criterio, políticas y atribución.
- `reports/session_24_public_catalog_02/metrics.json`: conteos por modo, municipio, categoría y nivel.
- `reports/session_24_public_catalog_02/coverage_by_municipality.csv` y `postal_coverage.csv`.
- `reports/session_24_public_catalog_02/validation_summary.json` y `full_tests.log`.
