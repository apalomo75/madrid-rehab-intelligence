# Sesión 12.1 — límites oficiales y clasificación territorial PRTR

Procesamiento local: 24/10/2026. Se reutilizan los módulos de sesiones 11/12 y sus capturas; no se descargan concesiones ni Catastro, no se reconstruyen productos históricos y no hay commits, push ni publicación. El bloqueo de adquisición de límites queda resuelto mediante el GeoPackage aportado por el usuario. Las limitaciones históricas de sesión 12 siguen describiendo aquel snapshot, no el estado actual.

## Resultado verificado

| Indicador | Resultado |
| --- | ---: |
| Entidades originales / municipios oficiales | 194 / 179 |
| Municipios con geometría validada | 179 |
| Expedientes PRTR | 7.532 |
| Madrid capital | 3.808 |
| Otros municipios | 3.724 en 116 municipios |
| Sin municipio / ambiguos o contradictorios detectados | 0 / 0 |
| Concesiones Madrid capital | 126.405.605,98 € |
| Concesiones otros municipios | 189.121.733,01 € |
| Importe sin asignar | 0,00 € |
| Total regional | 315.527.338,99 € |
| Evidencia B / A | 7.530 / 2 |
| Municipios con CP/BU realmente integrado | 1: Madrid capital |

Todos los puntos de esta captura pasan el criterio espacial. **No se ha establecido como objetivo asignar el 100 %.** Los estados sin localización, exterior, frontera, jurisdicción compartida y contradicción están implementados y probados; en los datos reales no se activan. Los resultados describen puntos publicados y su relación con esta capa; no certifican la precisión de geocodificación, deslindes legales, obras, pagos ni edificios rehabilitados.

## Fuente oficial y normalización

Fuente declarada por el usuario: `https://idem.comunidad.madrid/geoidem/UnidadesAdministrativas/ows`, capa `UnidadesAdministrativas:IDEM_CM_UNID_ADMIN`. Original: `data/raw/territory/madrid/unidades_administrativas.gpkg`, 2.793.472 bytes. SHA-256:

```
4f6f7f6f919d16e82ba83b41dc4d7899b1d7919aa308ffe837d7833d26415e66
```

La base SQLite pasa `quick_check`; `gpkg_contents` describe recintos inscritos en el Registro Central de Cartografía. Capa geométrica `GEOMETRY1`, SRS 25830, sin Z/M declarados. `last_change=2026-10-24T14:11:26.667Z` es metadato del contenedor. El mtime se conserva en el manifiesto como dato del sistema de archivos: **no se presenta como fecha de actualización de la fuente ni como captura independientemente acreditada**. No hay filas en las tablas de metadatos. La fecha de corte de la fuente y su licencia específica siguen sin verificar. El origen de descarga es la declaración del usuario; no se sustituye por una descarga nueva. Una consulta adicional del WFS con la herramienta web no permitió acceder a GetCapabilities.

`municipal_boundaries.py` abre SQLite en modo de solo lectura, interpreta magic/version/flags, endian, SRS y longitud de envelope OGC; valida valores finitos y su concordancia con WKB. No usa un offset fijo ni trata el blob entero como WKB. Rechaza geometrías vacías, inválidas y no poligonales; comprueba posición regional como control de CRS, no como límite de asignación. No aplica reparaciones geométricas silenciosas.

Se identifican 178 registros «Término Municipal» y uno «Termino Municipal»: 179 códigos INE y nombres municipales únicos. Se conservan separadamente 13 enclaves y dos comunidades jurisdiccionales. Todas las geometrías son válidas y positivas; no se detectan solapamientos de superficie >0,001 m² entre las 194 entidades. La validación de carga municipal mantiene también el control de solapamientos existente de sesión 12.

Para cada municipio se une exclusivamente su término con los enclaves cuyo `CD_INE` es explícito, cuyo nombre completo concuerda y sin atribución secundaria. `source_fids` enumera las entidades utilizadas. La unión no añade territorios por nombre, cercanía o recuadro. Superficie municipal sumada: 8.019,570199 km². No existe contraste independiente con una envolvente provincial oficial; no se afirma integridad territorial jurídica absoluta.

| Territorio compartido | fid | CD_INE / CD_INE_1 | Tratamiento |
| --- | --- | --- | --- |
| Los Baldios, comunidad de Cercedilla y Navacerrada | 84 | 28038 / 28093 | Conservado aparte; no añadido a Cercedilla |
| El Redegüelo, comunidad de El Boalo y Manzanares el Real | 159 | 28082 / 28023 | Conservado aparte; no añadido a Manzanares el Real |

Superficie compartida: 5,741099 km². Los puntos en estos recintos o a ≤1 m se dejan sin asignar, nivel C. Cercedilla y Manzanares el Real mantienen como nombres municipales los de sus registros de término municipal. No se fusionan indiscriminadamente todos los códigos repetidos.

El catálogo normalizado es `data/processed/territory/session_12_1_final_01/municipality_boundaries.parquet`; SHA-256:

```
36e2acec3119969c1a9a26302fb1ec9ea3eb88105edc9fbaff8aac1e548b46b2
```

El directorio contiene además las 194 entidades completas, las dos jurisdicciones compartidas, catálogo sin geometría, comparación catastral, calidad y manifiesto. Las geometrías analíticas no se simplifican; el visor simplifica solamente su representación.

## Método de clasificación

Se comprueba el hash del GeoJSON PRTR original existente y la igualdad de IDs/coordenadas procesadas con sus filas originales. El CRS declarado es `urn:ogc:def:crs:OGC:1.3:CRS84`: longitud/latitud. Se transforma mediante PyProj a EPSG:25830 con `always_xy=True`. La consulta STRtree usa polígonos originales, nunca bounding boxes o centroides municipales.

- A: punto válido en un único municipio, a más de 1 m del borde, sin contradicción reconocida. Dos casos de Gargantilla del Lozoya y Pinilla de Buitrago mantienen el literal truncado «GARGANTILLA DEL LOZOYA Y PINIL» como no reconocido: no se eleva a evidencia documental por semejanza.
- B: misma evidencia espacial y concordancia con nombre municipal completo declarado en el literal administrativo, o con CP histórico verificado. El contraste textual exige delimitación y prioriza el nombre completo más largo; «Las Rozas de Madrid» no equivale a «Madrid». El texto nunca asigna por sí solo.
- C: varias intersecciones, cercanía a frontera ≤1 m, jurisdicción compartida, contradicción con declaración municipal reconocida o con CP histórico, o conflicto de identidad. No se asigna municipio; se conserva el candidato y las evidencias.
- Sin asignación: geometría ausente/inválida, coordenadas no finitas/fuera de rango, marcador (0,0), o punto exterior sin evidencia territorial suficiente. Una referencia catastral válida o ambigua no resuelve estos casos.

Las coordenadas reales están dentro del rango regional esperado; todos los puntos tienen geometría válida. Hay coordenadas repetidas, compatibles con varias concesiones para una localización: no se deduplican expedientes por punto ni se consideran automáticamente marcadores. Ninguna coordenada repetida recibe municipios distintos. La distancia mínima al borde es 3,697088 m; tres puntos están a ≤10 m y trece a ≤25 m. La tolerancia operativa de 1 m **no acredita la precisión de la geocodificación**; esos casos merecen revisión si se necesita una decisión parcelaria o jurídica. Cambiar la tolerancia exigiría un replay nuevo y podría reducir asignaciones.

Cada decisión registra método, nivel, candidato(s), municipio documental reconocido, concordancia, distancia al borde, municipio CP y decisiones históricas. `historical_cp_only` identifica el modo heredado sin límites, no se confunde con evidencia espacial A/B.

## Reconciliación y comparación con sesión 12

Las 3.805 asignaciones históricas de Madrid, por 126.328.673,63 €, se conservan íntegramente. No hay revocaciones ni cambios del municipio previamente asignado. De los 3.727 casos pendientes se asignan 3.724 a municipios externos y tres a Madrid. Estos tres añaden 76.932,35 € y están a más de 1.970 m del límite, con concordancia documental; no se promociona su relación CP ambigua a confirmada. Sus decisiones e importes están en la comparación local, sin exponer direcciones en los informes agregados.

| Programa | Expedientes | Concesión regional |
| --- | ---: | ---: |
| P1 | 364 | 68.107.496,98 € |
| P3 | 1.380 | 229.790.531,46 € |
| P4 | 4.889 | 12.232.015,84 € |
| P5 | 899 | 5.397.294,71 € |
| Total | 7.532 | 315.527.338,99 € |

Los importes permanecen como enteros en céntimos por expediente. Las relaciones CP, incluidos varios accesos/parcelas y ambigüedades históricas, no contienen importes. Se contrastan exactamente recuentos e importes por programa antes de generar productos. La tabla de expedientes conserva los 7.532 IDs originales, uno por decisión territorial.

`municipal_products.parquet` tiene 179 filas: INE, nombre oficial, número e importe total y por programa, niveles de evidencia, porcentaje de expedientes con CP confirmado, cobertura PRTR y disponibilidad real CP/BU/CEEE. Los 62 municipios sin concesiones asignadas en esta captura tienen recuento cero de la captura, **no una tasa de ausencia de ayudas ni cobertura exhaustiva**.

La comparación INE–Catastro mantiene ambos códigos: 173 nombres completos normalizados ofrecen candidato único y seis requieren revisión. Ninguna comparación textual autoriza una correspondencia para ingesta. Se conservan los códigos distintos de Madrid (INE 28079 / Catastro 28900); no se deduce INE de códigos internos. Las URLs CP/BU de los cinco pilotos se reconocen en los feeds oficiales preservados; no se descargan ZIP ni se afirma su accesibilidad HTTP actual.

## Productos y visor

- Territorio: `data/processed/territory/session_12_1_final_01/`.
- Clasificación vigente: `data/processed/grants/regional/session_12_1_final_02/`. El primer procesamiento de esta sesión queda preservado en `session_12_1_final_01`; el segundo añade método y municipio documental explícitos sin cambiar las asignaciones.
- Auditoría agregada: `reports/session_12_1/audit_final_01/quality.json`, `municipal_products.csv`, `municipality_program_summary.csv`, `conflicts.json`, URLs piloto, preservación y manifiesto con hashes de código y entradas.
- Conflictos y comparación detallada local: `territorial_conflicts.parquet`, `session12_comparison.parquet`, `historical_changes.parquet` en el producto. La tabla de conflictos y la de cambios históricos están vacías, con su esquema conservado.

La vista regional utiliza estos productos por defecto y mantiene las variables de entorno de sesión 12 para seleccionar otras capturas. Dibuja los 179 municipios, permite selección INE, filtros de programas, importes, CP y calidad, y muestra recuento e importe por programa. Distingue Madrid con CP/BU integrado de los límites sin cartografía catastral integrada; territorializar PRTR en Getafe no habilita una ficha de parcela de Getafe. Las lecturas CP/BU continúan limitadas al municipio y selección/ventana. Se comprueban hashes y correspondencia con la captura PRTR.

`MADRID_REHAB_PUBLIC=1` conserva la protección: no se cargan decisiones PRTR, no aparecen filtros, expedientes o exportación PRTR. La licencia de redistribución PRTR continúa sin verificar. Tampoco se ha acreditado la licencia específica de la capa IDEM; el trabajo es local.

## Reproducción

Sin instalar dependencias nuevas. Desde la raíz, con las capturas ya conservadas:

```bash
# Cada salida debe ser nueva; no regenerar snapshots históricos.
PYTHONPATH=src .venv/bin/python -m madrid_rehab.municipal_boundaries \
  --output-dir data/processed/territory/session_12_1_replay_new
PYTHONPATH=src .venv/bin/python -m madrid_rehab.territorial_prtr \
  --boundaries-dir data/processed/territory/session_12_1_replay_new \
  --output-dir data/processed/grants/regional/session_12_1_replay_new
PYTHONPATH=src .venv/bin/python -m madrid_rehab.territorial_report \
  --boundaries-dir data/processed/territory/session_12_1_replay_new \
  --classification-dir data/processed/grants/regional/session_12_1_replay_new \
  --output-dir reports/session_12_1/replay_new
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_territorial_prtr.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
# Visor con snapshots vigentes por defecto:
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512
```

Para mostrar el replay: `MADRID_REHAB_TERRITORY_DIR=data/processed/territory/session_12_1_replay_new` y `MADRID_REHAB_REGIONAL_GRANTS_DIR=data/processed/grants/regional/session_12_1_replay_new`. No confundir el inventario (`MADRID_REHAB_TERRITORY_INVENTORY_DIR`) con la capa de límites. Los directorios de datos e informes están ignorados en Git; los detalles originales permanecen locales.

## Validación y pendientes

Línea base: 288 pruebas superadas antes de modificar código. Las pruebas específicas cubren GeoPackage real y sintético, flags/endian/envelopes, 194 entidades, 179 códigos, enclaves, jurisdicciones compartidas, solapamientos, fronteras, CRS, nombres semejantes, puntos exteriores/ausentes/inválidos, referencias ambiguas, importes exactos, relaciones múltiples, replay, preservación, 21 distritos y modo público. Cierre: **311 pruebas superadas en 217,378 s; Ruff sin errores y siete archivos nuevos/modificados con formato verificado**. Evidencia en `reports/session_12_1/validation.json` y `full_tests.log`.

La validación visual en navegador está **bloqueada**: el servidor Streamlit falla al crear el socket local con `PermissionError: [Errno 1] Operation not permitted`. No hay capturas ni validación de clic/renderizado en navegador. AppTest comprueba navegación, filtros y protección, pero no sustituye esa aceptación. Evidencia: `reports/session_12_1/visual_server.log` y `visual_validation.json`.

Pendientes: verificar licencias específicas y fecha de corte, contraste territorial independiente y precisión de puntos próximos a borde, revisión formal de correspondencias Catastro–INE y futura ingesta CP/BU externa acotada, CEEE regional y aceptación visual local. No impiden la reconciliación de esta captura y no se declaran resueltos.
