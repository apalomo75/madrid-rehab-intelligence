# Sesión 13 — Energía regional y evidencias por parcela

Se han procesado realmente los dos originales locales CEEE, sin descargas, cambios de fuentes ni activación de parcelarios históricos. Producto vigente: `data/processed/energy/session_13_final_03/`. Las ejecuciones exploratoria y provisional quedan conservadas en `session_13_final_01` y `session_13_final_02`; no son la captura del visor. Los productos sintéticos de pruebas no entran en estas salidas.

## Fuentes y significado de las filas

| Captura | Formato y codificación detectada | Filas | Madrid | Otros municipios verificados | Sin clasificar | Municipios |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| certificados_2025.zip | CSV interno; latin-1; separador `;` | 110.650 | 55.266 | 54.393 | 991 | 177 |
| certificados_2026.csv | CSV; utf-8-sig; separador `;` | 125.523 | 60.398 | 64.134 | 991 | 176 |

Las capturas, de 17.757.703 y 86.187.051 bytes, se conservaron el 22/10/2026. El catálogo local `data/raw/session_1/catalog.json` describe **inmuebles inscritos en el registro**. Las filas no son inmuebles únicos ni prueban el estado vigente de una inscripción. El catálogo menciona recursos anteriores a 2024 y de 2024, pero sus archivos no están disponibles localmente y no se han integrado. No hay cobertura histórica exhaustiva.

El inventario `source_inventory.json` contiene rutas, hashes, miembro ZIP, esquema, ausencias, cardinalidades, categorías y metadatos de cada recurso oficial. La auditoría `reports/session_13/audit_final_03/column_profiles.json` añade los valores frecuentes de todas las columnas. `historical_energy_products.json` inventaría los Parquet previos derivados, que no se contabilizan como nuevas fuentes. Se revisaron los CSV/ZIP bajo `data/raw/`: los demás corresponden a Catastro o archivos administrativos.

`edif_fecha` se interpreta únicamente como **fecha declarada en la fuente**: su semántica exacta no queda acreditada por un diccionario oficial local. No se sustituye por fecha de captura, publicación ni modificación HTTP. Las fechas observadas van de 24/05/2013 a 24/07/2027; esta última es posterior a la captura y se marca como anomalía. Hay 59 fechas no convertibles. No se ha deducido caducidad.

## Municipio, identidad y alcance

Se contrastan nombres completos contra los 179 municipios del producto oficial 12.1, normalizando tildes, espacios y mayúsculas. Siete variantes explícitas de preposición/separación se conservan en el manifiesto; también se permite el artículo oficial al final con coma. No se usan subcadenas, códigos postales ni inferencias de códigos Catastro–INE. Las Rozas de Madrid no se asigna a Madrid. Se verifican 234.172 observaciones canónicas; 1.922 quedan con municipio desconocido y 40 en conflicto por provincia contradictoria. «Sin clasificar» en la tabla de fuentes reúne desconocidos y conflictos. Los cuatro estados municipales están implementados, incluidos conflicto y ambigüedad, aunque las fuentes reales no aportan código INE explícito ni coordenadas de certificado para contrastes adicionales.

La clave canónica es SHA-256 del contenido completo original, con columnas ordenadas; no normaliza formatos numéricos ni modifica textos antes del hash. Conserva las 236.173 apariciones, fuente y ordinal. Se obtienen **236.134 contenidos canónicos**, 39 apariciones redundantes y 12 contenidos exactos presentes en ambas capturas. Los restantes duplicados son repeticiones dentro de una captura. Un mismo identificador con contenido distinto no se fusiona: 12 inscripciones reúnen 26 contenidos conflictivos; una observación carece de identidad de inscripción suficiente. No se han acreditado modificaciones ordenables ni versiones vigentes. «Canónico» designa aquí contenido deduplicado, sin afirmar identidad física individual verificada para todos los registros.

El ámbito procede exclusivamente de `edif_tipo`: vivienda individual/en bloque y unifamiliar → unidad individual; bloque completo y edificio terciario explícito → edificio completo declarado; local terciario → local. `Vivendas`, `Edificio terciario` y valores corruptos permanecen desconocidos. Se conservan 192.202 viviendas individuales, 30.929 edificios completos declarados, 12.659 locales y 344 ámbitos desconocidos. El alcance declarado no acredita un BU concreto.

## Cruce catastral y PRTR

Se reutilizan CP de Madrid y `session_12_2_partial_validated_01` de los cinco pilotos. RC14 y RC20 urbanas se reconocen por estructura; solo después se deriva RC14 y se comprueba su existencia exacta y municipio. Se registra la pérdida del sufijo de unidad. No se verifica el dígito de control RC20; una estructura válida no prueba existencia. Referencias rústicas/formatos no soportados se conservan sin truncarlas. No se utiliza proximidad ni dirección como confirmación.

El nivel A exige CP aceptada y única en la captura. D recoge cuarentena, varias filas CP o varias referencias parcelarias, referencias mixtas y desplazamientos de columnas sospechosos. E conserva lo no vinculable y la ausencia de cobertura CP. No hay B (sin geometría fiable de certificado) ni C (no se ha implantado un buscador de candidatos por dirección). Las 8.048 CP en cuarentena se mantienen excluidas; tampoco se construyen relaciones CP/BU.

| Municipio | Contenidos canónicos | Con CP confirmada |
| --- | ---: | ---: |
| Madrid | 115.658 | 113.047 |
| Getafe | 5.410 | 5.384 |
| Móstoles | 5.114 | 4.963 |
| Leganés | 4.565 | 4.472 |
| Alcorcón | 4.046 | 3.979 |
| Alcalá de Henares | 4.978 | 4.897 |

Se preservan los 115.664 contenidos históricos con literal Madrid; seis tienen provincia contradictoria y quedan sin asignación municipal verificada, por lo que la nueva vista municipal contiene 115.658. La diferencia respecto de las 113.072 confirmaciones históricas se explica en la auditoría de calidad: la regla nueva trata conservadoramente referencias múltiples, aún no soporta las referencias rústicas y excluye provincias contradictorias; no modifica los productos anteriores.

El producto conjunto tiene una fila por municipio/RC14: 59.149 parcelas con CEEE sin PRTR confirmado en estas fuentes, 3.440 con ambas evidencias y 938 con PRTR sin CEEE confirmado. Los 4.054 expedientes únicos del solapamiento suman 187.366.346,02 €; el importe se guarda únicamente en `energy_grant_cases`, una fila por expediente, nunca en la tabla de parcelas. Los expedientes multiparcela pueden aparecer relacionados con varias parcelas; sus importes no se suman por fichas. La distribución energética asociada a PRTR se calcula sobre 13.408 contenidos únicos, conservando ámbito y municipio.

No se alteran las decisiones territoriales ni los 1.241 expedientes piloto confirmados anteriormente. No se infieren obras, pagos, necesidad de financiación ni causalidad. Ausencia de vínculo PRTR no significa ausencia de cualquier ayuda; ausencia de CEEE no significa incumplimiento.

## Productos, ejecución y visor

El directorio contiene `energy_source_records`, `energy_certificates`, `energy_municipality_links`, `energy_parcel_links`, `energy_municipality_summary`, `energy_grants_summary`, `energy_grant_cases`, `energy_identity_conflicts`, `energy_capture_overlap`, `energy_unresolved_municipalities` (Parquet), inventario, calidad y manifiesto. No se crean tablas BU o temporales vacías: su omisión está motivada en calidad. Hay particiones por municipio para consulta selectiva, sin geometrías.

```bash
# Desde la raíz, dependencias existentes; salida nueva obligatoria.
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_energy --output-dir data/processed/energy/replay_nuevo
PYTHONPATH=src .venv/bin/python -m madrid_rehab.energy_audit --energy-dir data/processed/energy/replay_nuevo --output-dir reports/session_13/audit_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_regional_energy.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src/madrid_rehab/regional_energy.py src/madrid_rehab/energy_audit.py src/madrid_rehab/energy_view.py tests/test_regional_energy.py tests/benchmark_energy.py
PYTHONPATH=src .venv/bin/python tests/benchmark_energy.py
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

El benchmark requiere que `reports/session_13/benchmark.json` no exista; para otra medición añadir `--output reports/session_13/benchmark_nuevo.json`, conservando la anterior. No hay dependencias nuevas ni compilación. El pipeline consume unos 1,76 GiB de RSS máximo en esta ejecución; no es una medición de memoria del navegador.

La vista regional incorpora tabla de cobertura, selección de municipio, distribución A–G, porcentaje de referencias con estructura válida, recuentos por ámbito, coexistencia PRTR y consulta por parcela aceptada. Madrid añade una sección regional a la ficha existente sin reemplazar el mapa ni sus filtros históricos. Los pilotos se consultan en el panel energético regional, aunque su parcelario parcial no se activa como cobertura catastral completa. `MADRID_REHAB_ENERGY_DIR` permite otra captura. Caché acotada, filtros Parquet por referencia/identificador y selección de columnas evitan cargar toda la región para una ficha. AppTest verifica selección real de Getafe; la aceptación visual con navegador queda para la revisión posterior del usuario.

## Licencias y privacidad

El catálogo local identifica CEEE como CC BY 4.0 (`license_url` conservada). No se han enviado datos a servicios externos. Se observan direcciones de unidades y literales de correo en el campo municipal; los originales y perfiles detallados son locales, sin exportación pública nueva. La nueva sección energética se oculta con `MADRID_REHAB_PUBLIC=1`, sin modificar la política histórica del visor. La licencia PRTR continúa sin verificar y no se publica el producto conjunto. No hay commits ni push.

Para verificar una reproducción contra el snapshot vigente: `PYTHONPATH=src .venv/bin/python tests/verify_energy_replay.py --replay data/processed/energy/replay_nuevo --output reports/session_13/verificacion_nueva.json`. Requiere una ruta de informe nueva. La auditoría final incorpora su propio manifiesto y el contraste de Madrid con sesión 2.
