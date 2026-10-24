# Sesión 14 — inteligencia administrativa de conservación

Resultado: productos offline reales de órdenes y obligaciones municipales, vinculados con CP y contexto energético/PRTR sin modificar las capturas anteriores. **No se ha integrado ninguna ficha REC ni ninguna acta ITE/IEE real.** El acceso masivo REC no está acreditado y no se ha implementado un recolector. No hubo commits, push, publicación ni revisión visual del usuario.

## Auditoría y fuentes

Se partió de `9da1b6e`, con árbol Git inicialmente limpio. Se revisaron AGENTS, README, arquitectura, ingesta y visor administrativo, normalizadores y manifests de energía, Catastro y PRTR. Línea base específica: 34 pruebas administrativas correctas. No se repitió inicialmente toda la suite.

La captura de sesión 10 ya contenía 124.175 eventos: 98.032 declaraciones, 11.498 licencias, 3.935 órdenes, 4.952 obligaciones ITE y 5.758 IEE. Hay 109.530 referencias completas de expediente en licencias/declaraciones. Las órdenes solo tienen ordinal de publicación; las obligaciones no son expedientes de inspección con dictamen. No se reconstruyó esa ingesta ni se cambiaron sus IDs.

Se inventariaron 15 familias de fuentes, incluyendo callejero y contexto administrativo: diez con descargas oficiales documentadas o preservadas; seis efectivamente reutilizadas. **Ninguna descarga nueva de registros se completó** desde Python: tres GET oficiales fallaron por DNS y se cerró esa vía. La navegación de investigación sí permitió localizar documentación y catálogos. El detalle, las URL y los permisos están en [fuentes](fuentes_conservacion_madrid.md) y `config/conservation_sources.json`.

REC queda clasificado como consulta individual pública, reutilización no verificada. Se consultaron la entrada del portal y documentación oficial, no fichas individuales. No había HTML de fichas REC en `data/`; la observación manual del usuario no se importó ni se presentó como comprobación de la ficha actual. El portal RIEECM está documentado y dispone de contenido indexado; su apertura directa dio timeout. No se deduce inexistencia ni disponibilidad de una exportación completa.

## Identificación del acceso

Se contrastó un acceso del ejemplo manual contra el callejero local verificado: COD_NDP 11140360, calle de Ezequiel Peñalver 8, código vía 285300, distrito 21, CP postal 28042, X/Y ETRS89 453035,95 / 4477850,34. Coincide con la dirección indicada por el usuario. Esta correspondencia puntual no demuestra que todo parámetro `ndp` del REC sea intercambiable universalmente con COD_NDP.

El puente conserva la referencia original `28900M01100041`, fuera del patrón urbano soportado; **no hay CP confirmada para ese acceso**. No se ha forzado una conversión ni una parcela por proximidad. Se conservan 214.676 versiones de dirección para 214.278 NDP del archivo observado, incluidos 78 con varias denominaciones. El puente previo incorpora también identidades del callejero anterior y totaliza 215.663 NDP; por eso su denominador difiere del archivo de direcciones. Hay 207.648 accesos con CP confirmada y 338 ambiguos. No se acredita ningún BU.

## Productos y semántica

Captura activa de esta sesión: **`data/processed/conservation/session_14_final_02/`**. Las tentativas de preparación y `session_14_final_01` se preservan como antecedentes de desarrollo, sin sobrescribirlas. El segundo cierre endurece la interpretación de estados negados del parser; no añade registros REC.

Los productos conservan los 124.175 eventos y sus procedencias. Se marcan 14.645 como evidencia de conservación: órdenes históricas y obligaciones de presentación. Se obtienen **9.036 perfiles CP**, de los que 3.894 tienen CEEE vinculado, 239 PRTR y 184 ambos. Hay 8.934 vínculos de contenidos energéticos en esas parcelas y 264 expedientes PRTR únicos en la tabla de casos. Una concesión puede relacionarse con varias parcelas: los importes permanecen en casos, nunca se suman por vínculo.

En motivos de órdenes hay 60 menciones indirectas de dictámenes desfavorables, incluidas erratas literales. No se convierten en 60 actas, inspecciones desfavorables ni deficiencias vigentes. No hay datos acreditados de subsanación, sanción coercitiva o resolución material integrados. La ausencia de esas entidades significa falta de cobertura, no ausencia de incidencias.

Los perfiles conservan plazo/fecha administrativa y fecha de observación cuando está acreditada, separando ambas. No inferimos fecha de captura por mtime. El conjunto registra condición física no evaluable, estado de subsanación desconocido y cobertura individual REC ausente. Las licencias/declaraciones son contexto independiente. Compartir parcela no fusiona expedientes.

Se documentan las reglas de estado, las relaciones A/B/C/D y las entidades en [modelo](modelo_conservacion.md). Sin registros REC no se puede medir solapamiento con expedientes municipales: queda explícitamente no evaluable. Las causas no se clasifican con categorías inventadas; el parser mantiene literal, código original si existe y categoría sin mapear.

## Parser local

`rec.py` analiza bytes con hash, UTF-8 o ISO-8859-1, entidades HTML, tablas verticales y horizontales, cierres omitidos, colspan, cabeceras repetidas y secciones ausentes. Extrae etiquetas de acceso, expediente, registro, dictamen, alcance, causa, situación, dependencia, fechas, actuaciones y antecedentes. No usa posiciones fijas de filas. Preserva bloques y filas no reconocidos y registra anomalías. Casos, observaciones y actuaciones tienen identidades distintas; una repetición idéntica no duplica el caso.

**Es experimental y solo está validado con fixtures sintéticas explícitas.** No se afirma compatibilidad comprobada con el HTML real de una ficha REC. No hay cliente HTTP, parser activado en la ingesta productiva ni mezcla de fixtures con Parquet reales. La futura incorporación necesita HTML legítimo preservado y revisión del esquema y sus permisos.

Las reglas conservadoras no convierten «archivado», «terminado», «resolver» ni una multa en obras terminadas o deficiencias actuales. La subsanación acreditada exige literal afirmativo específico; los estados negados no se convierten en evidencia positiva. Toda interpretación mantiene el literal y la fecha de observación.

## Visor y protección

Las fichas de parcela/contexto BU de Madrid muestran «Conservación e inspecciones», accesos vinculados, órdenes/obligaciones, fuente, fecha y calidad. El mensaje para inspecciones es «No constan inspecciones vinculadas en las fuentes integradas». El panel de actividad añade filtros específicos con datos disponibles; no inventa filtros de dictamen o causa. La nueva sección completa se oculta con `MADRID_REHAB_PUBLIC=1`, conservando las protecciones anteriores de PRTR y energía.

La nueva capa regional enumera disponibilidad de fuentes en los 179 municipios; no inventa actas externas ni extiende COD_NDP. Alcalá, Getafe, Móstoles, Alcorcón y Arganda ofrecen distintas posibilidades documentadas de expansión, todavía sin adquisición en esta sesión. No se ejecutó inspección integral visual ni se solicita al usuario; AppTest no reemplaza navegación de navegador/WebGL.

## Reproducción e integridad

Dependencias existentes, sin manifiestos de paquetes ni lockfiles nuevos. Instalación y app:

```bash
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
PYTHONPATH=src .venv/bin/python -m madrid_rehab.conservation --output-dir data/processed/conservation/replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_conservation.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_conservation.py --output reports/session_14/benchmark_nuevo.json
PYTHONPATH=src .venv/bin/python tests/verify_conservation.py --snapshot data/processed/conservation/session_14_final_02 --compare data/processed/conservation/replay_nuevo --historical-baseline reports/session_14/audit_01/historical_before.json --output reports/session_14/verificacion_nueva.json
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src/madrid_rehab/administrative_view.py src/madrid_rehab/conservation.py src/madrid_rehab/conservation_view.py src/madrid_rehab/rec.py tests/test_conservation.py tests/benchmark_conservation.py tests/verify_conservation.py
```

`--administrative-dir` y `--energy-dir` permiten entradas equivalentes; se exige CP concordante. Se verifican originales por hash, productos administrativos consumidos y salidas de los manifests energéticos, catastrales y PRTR. El manifiesto PRTR real es `grant_source_manifest.json`, no `manifest.json`. No se regeneran esos productos. Los overrides de directorio del visor se documentan en README y AGENTS.

Las fichas usan buckets CP, filtros Parquet y caché de máximo 24 consultas. Consulta de eventos de una parcela (tres filas): medición inicial 0,0467 s en frío y 0,0020 s en caché; cierre bajo carga concurrente 0,2864 s y 0,0143 s respectivamente. Pico de asignaciones Python 1,56 MiB; dataframe 0,0114 MiB. No mide renderizado completo de ficha, buffers nativos Arrow, GPU ni capacidad concurrente. Generación final 94,87 s y replay 95,86 s. Informes bajo `reports/session_14/audit_01/`.

Verificación final: 312 productos idénticos en replay por SHA-256, 40 entradas verificadas y 777 archivos históricos sin cambios; código productor y parser coincidentes con el manifiesto. Las 40 pruebas específicas pasan, incluidas ejecución AppTest, filtros, modo público, 21 distritos, cobertura regional e invariantes CEEE/PRTR. Ruff y formato de los siete archivos Python añadidos/modificados pasan. La primera ejecución global se interrumpió para endurecer el literal negado del parser; la única ejecución global completada, sobre el código definitivo, se registra en `full_suite_final.log`: **412 pruebas correctas, ninguna omitida, 380,60 s**. AppTest pasa; no se declara validación visual en navegador.

## Pendientes

Obtener autorización/exportación oficial REC, fichas reales legítimas y fechadas para validar el parser, comprobar esquemas y licencias de recursos regionales, y resolver identidades urbanas/rústicas mediante evidencia oficial sin alterar los normalizadores auditados. La revisión visual integral queda para una sesión posterior. No hay score de riesgo estructural, diagnóstico de edificio ni recomendación financiera.

## Balance cuantitativo

Los ceros siguientes significan **cero registros integrados de ese tipo**, no ausencia de hechos en Madrid. Los accesos pertenecen al puente completo, no exclusivamente a parcelas con órdenes/obligaciones.

| Indicador | Resultado |
| --- | ---: |
| Familias investigadas, incluidas auxiliares | 15 |
| Fuentes con descargas oficiales documentadas/preservadas | 10 |
| Familias realmente reutilizadas | 6 |
| REC analizado | Portal y documentación; ninguna ficha |
| Autorización masiva REC | No verificable |
| COD_NDP contrastados contra la observación manual | 1 |
| Accesos vinculados a CP | 207.648 |
| Accesos ambiguos | 338 |
| Actas ITE/IEE reales integradas | 0 |
| ITE favorables / desfavorables | 0 / 0 |
| IEE favorables / desfavorables | 0 / 0 |
| Subsanaciones expresamente pendientes / acreditadas | 0 / 0 |
| Órdenes de ejecución reutilizadas | 3.935 |
| Multas coercitivas integradas | 0 |
| Eventos municipales reutilizados | 124.175 |
| Eventos de conservación | 14.645 |
| Parcelas con evidencia de conservación | 9.036 |
