# Calidad CEEE regional — sesión 13

El denominador regional es **236.134 contenidos canónicos**, obtenidos de 236.173 apariciones originales. No es un censo de inmuebles ni un inventario de certificados vigentes. Producto: `data/processed/energy/session_13_final_03/`; auditoría: `reports/session_13/audit_final_03/`.

| Indicador | Resultado |
| --- | ---: |
| Fuentes originales procesadas | 2 |
| Apariciones originales | 236.173 |
| Contenidos canónicos | 236.134 |
| Apariciones exactas redundantes | 39 |
| Contenidos exactos presentes en ambas capturas | 12 |
| Inscripciones con contenido conflictivo | 12 (26 contenidos) |
| Identidad de inscripción insuficiente | 1 |
| Versiones documentadas | 0 |
| Municipios con observaciones | 179 |
| Municipio verificado | 234.172 |
| Municipio desconocido | 1.922 |
| Municipio en conflicto por provincia | 40 |
| Referencia con estructura urbana válida, al menos una | 233.166 |
| Referencia ausente/no soportada, al menos una | 2.973 |
| CEEE con CP confirmada A | 136.742 |
| CEEE con concordancia espacial B | 0 |
| CEEE candidato por dirección/posición C | 0 |
| CEEE ambiguo D | 155 |
| CEEE sin relación E | 99.237 |
| CEEE que apunta a CP en cuarentena | 75 |
| CEEE con BU confirmado | 0 |
| Pares temporales físicos confirmados | 0 |
| Parcelas con CEEE confirmado | 62.589 |
| Parcelas con CEEE y PRTR confirmado | 3.440 |
| Contenidos CEEE únicos asociados a esas parcelas | 13.408 |
| Expedientes PRTR únicos del solapamiento | 4.054 |
| Importe de esos expedientes únicos | 187.366.346,02 € |
| Edificio completo declarado | 30.929 |
| Vivienda individual declarada | 192.202 |
| Local declarado | 12.659 |
| Ámbito desconocido | 344 |
| Consumo sin letra A–G interpretable | 104 |
| Emisiones sin letra A–G interpretable | 86 |
| Fechas no convertibles | 59 |
| Fecha posterior a captura | 1 |
| Contenidos con indicio de columnas desplazadas | 6 |

Los 40 conflictos municipales proceden de provincias contradictorias. Se admite «Comunidad de Madrid» como variante provincial de Madrid; las demás contradicciones impiden confirmar CP. Cinco confirmaciones CP de la captura provisional pasan a estado sin municipio verificado; también se reclasifican tres sospechas de desplazamiento de columnas.

Los indicadores «al menos una referencia válida» y «al menos una no soportada» se solapan en cinco contenidos con referencias mixtas. Las tablas de vínculos pueden tener más filas que certificados. Los recuentos de certificados por nivel A/D/E son distintos y reconcilian el total canónico. Los 75 certificados en cuarentena no representan las 8.048 filas CP en cuarentena: son unidades de conteo diferentes. Los 94.428 vínculos sin cobertura CP se conservan; no se inventan parcelas de los otros municipios.

## Anomalías investigadas

Hay mojibake dentro del ZIP latin-1 y errores de escritura, nombres de núcleos, distritos, municipios de otras comunidades y valores ajenos al municipio. Las siete variantes controladas resuelven 2.393 contenidos adicionales respecto de la primera ejecución; no se corrige automáticamente el resto. Entre los no resueltos: Cerceda, «LAS ROZAS», «GUADARRAMA ALTITUD 880», nombres cortados y variantes mal codificadas de Alcalá. Se preserva cada literal y su frecuencia, sin reasignación por similitud. Dos apariciones contienen un correo en el campo municipal: los perfiles detallados no son un producto público.

En seis contenidos de 2025, `edif_tipo` contiene `ElectricidadPeninsular` o fechas: evidencia de corrupción/desplazamiento de campos en la propia fuente, no un nuevo ámbito energético. Se mantienen íntegros y no confirman CP (los seis permanecen E por municipio desconocido o conflictivo tras contrastar provincia). No se intenta reparar columnas de manera especulativa.

La fecha 24/07/2027, inscripción `10/699593.9/26`, es posterior a la captura 22/10/2026: se conserva con advertencia. No se usa para elegir una versión vigente o crear un par temporal. La presencia de fechas anteriores al año del recurso confirma que el nombre del fichero no es una fecha de emisión individual.

Los valores numéricos se conservan sin convertir unidades. La documentación anterior atribuía unidades convencionales a consumo/emisiones; esta sesión no ha encontrado un diccionario oficial local que las acredite para cada columna y captura, por lo que etiqueta la unidad como no verificada. No se mezclan indicadores totales y por superficie. A–G son categorías ordenadas; no se calculan promedios numéricos de letras. No se confunde cero con nulo. Centinelas de magnitud 99.999 o superior y valores negativos se señalan como sospechosos, sin eliminar observaciones: un valor negativo tampoco se declara imposible automáticamente.

## Regresión de Madrid y pilotos

Los 115.664 contenidos históricos con literal Madrid permanecen en el producto regional; seis con provincia contradictoria ya no se asignan al municipio, quedando 115.658 observaciones municipales verificadas. La comparación por identificador con `session_2/certificates_integrated.parquet` detecta **25 confirmaciones menos**, ninguna nueva: 16 referencias rústicas no soportadas por la regla urbana de esta sesión, seis contenidos con varias parcelas o referencias mixtas y tres con provincia contradictoria. Los 16 vínculos rústicos históricos siguen existiendo en sus snapshots; no se han invalidado ni borrado. La tabla regional es más restrictiva y no debe sustituir silenciosamente la evidencia histórica. Reconciliación y filas afectadas: `reports/session_13/audit_final_03/madrid_regression.json` y `madrid_regression_changes.parquet`. Ampliar el reconocedor rústico con validación documental específica queda pendiente.

Para los cinco pilotos se comprueba que cada referencia confirmada está en `cp.parquet` aceptado; todas las referencias originales de CP en cuarentena prevalecen sobre la aceptación. Se mantienen 54.441 CP aceptadas, 8.048 en cuarentena y BU independiente. Los 1.241 expedientes piloto confirmados no se recalculan ni sustituyen: se leen sus decisiones auditadas. El análisis conjunto cuenta expedientes distintos y guarda importes solo en la tabla por expediente.

## Integridad, reproducción y rendimiento

`manifest.json` registra SHA-256 de 14 entradas, del código del pipeline, reglas de ámbito y alias, y 370 archivos de salida (incluidas las particiones). El hash del manifiesto vigente es:

`ed983218521a4877525a0da06bb3aac77f2c98860443a7c31849c8f3bc11bbc1`

SHA-256 de fuentes originales:

- ZIP 2025: `15c3dbe564f7dbd5e5ca757679838513379fb0035019cfd89538b0ef463531b0`.
- CSV 2026: `69c1f2b4e5b33f11092dd25c1fe02779d091fde57ed19b3db93ab3a30f5678fa`.

La auditoría valida todos los productos de sesión 13 y las salidas declaradas por los manifiestos de límites 12.1 (6), clasificación PRTR 12.1 (9) y Catastro parcial 12.2 (64). No se reescriben. La validación de los ficheros reales de origen del piloto se hereda de 12.2; esta sesión lee sus productos y comprueba hashes, sin volver a descargar ni afirmar una nueva revisión completa de cada GML.

Procesamiento real: 63,43 s para lectura/hash/normalización; 12,66 s para cruce CP; 146,18 s hasta escribir productos y calcular memoria; pico RSS 1.804,94 MiB. La verificación final de entradas y cálculo de hashes de salidas ocurre después de ese cronómetro: el tiempo total de CLI es algo mayor. Lectura Python del visor: resumen regional 0,132 s, Getafe 0,676 s, parcela de muestra 0,082 s (dos observaciones). Son accesos de datos con comprobación de hash y caché, no mediciones de renderizado, WebGL o navegador. `reports/session_13/benchmark_final.json` contiene valores sin redondeo.

Las pruebas focalizadas previas a la corrección provincial son 16/16, incluyendo municipios semejantes, código incompatible, referencias CP/RC20, duplicación exacta, inscripción conflictiva, fechas no ordenables, letras fuera de escala, números/unidades no interpretables, alcances, varias parcelas, cuarentena, ausencia CP/BU, importes por expediente, modo público e integración Streamlit con selección de Getafe. La suite completa y la reproducción independiente se registran en `reports/session_13/`; el informe final de validación se genera al terminar.

## Límites de uso

La energía describe observaciones certificadas de ámbitos distintos. Una vivienda con letra F/G no califica el edificio ni demuestra necesidad de obras. Un edificio completo declarado no es todavía un BU identificado. No hay series físicas temporales verificadas ni análisis causal de ayudas. No hay ranking comercial. Los indicadores de coexistencia, ámbito, calidad y letras observadas permiten investigar, sin diagnosticar inmuebles ni predecir financiación.

La licencia CEEE consta como CC BY 4.0 en el catálogo local; el producto conjunto continúa protegido por la licencia PRTR no verificada. No se publica ni se amplía automáticamente la exposición pública del visor.

La primera reproducción independiente `data/processed/energy/session_13_replay_01/` (anterior a la corrección provincial) ha generado **368 Parquet idénticos byte a byte**, con las mismas entradas, código y diagnósticos no temporizados. Resultado verificable en `reports/session_13/reproduction.json`. Su duración (171,13 s; 1.802,99 MiB) estuvo condicionada por la suite completa concurrente y no se compara como benchmark aislado.

Ruff lint pasa en todo `src` y `tests`. El formato pasa en los ocho archivos Python nuevos/modificados de esta sesión. El chequeo global de formato detecta siete archivos históricos fuera de formato (`cli.py`, `http.py`, `integrate.py`, `pilot.py`, `pipeline.py`, `sources.py`, `test_pipeline.py`); se dejan intactos para evitar cambios ajenos. Registro: `reports/session_13/format.log`. [Diccionario de las 86 columnas originales](diccionario_ceee_regional.md).

El desglose por año/período constructivo literal y ámbito de los certificados asociados a PRTR está en `audit_final_03/prtr_energy_construction_period.parquet`; no se imputa antigüedad BU ni se convierten intervalos a años exactos. La auditoría final añade un manifiesto de sus propios archivos. Los diagnósticos iniciales y logs de la regresión de navegación se conservan, sin presentarlos como validaciones satisfactorias.

La prueba específica de provincia contradictoria eleva las pruebas energéticas a **17/17**, ejecutadas sobre `session_13_final_03`. La captura provisional 02 y su primera reproducción se conservan como evidencia anterior a esta corrección. La suite completa se repite por los fallos de navegación detectados y por la corrección posterior de consistencia provincial; no se presentan las ejecuciones fallidas como satisfactorias.

La reproducción final `data/processed/energy/session_13_replay_02/`, posterior a la corrección provincial, reproduce **368 Parquet idénticos byte a byte**, todas las entradas, el código y los diagnósticos (excepto tiempos/RSS). Ver `reports/session_13/reproduction_final_03.json`. Duración concurrente: 203,18 s; pico RSS 1.804,25 MiB. Consulta selectiva real en Madrid (RC14 `8238105VK3783G`): vínculos 0,335 s y dos certificados 0,131 s; pico RSS del proceso de consulta 229,64 MiB. No incluye navegador.

Validación final: **372/372 pruebas de la suite completa** en 529.590 s; **17/17 energéticas** tras la última integración de ficha conjunta. Ruff correcto y ocho archivos afectados con formato correcto. `reports/session_13/validation_final.json` y `final_results.md` consolidan los resultados. La ficha conjunta real de Alcalá se comprueba en `parcel_joint_ui.json`.
