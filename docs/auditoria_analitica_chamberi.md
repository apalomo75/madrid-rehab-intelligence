# Auditoría analítica de Chamberí — profundización 23/10/2026

La auditoría usa exclusivamente las capturas locales verificadas de sesión 2. No hubo nuevas descargas ni eventos ITE/IEE o ayudas reales. Producto vigente: `data/processed/session_6_audited/`, contrato `session6-v2`. Los productos v1 y checkpoints intermedios se conservan. El visor usa final por defecto y mantiene override `MADRID_REHAB_SESSION6_DIR`.

## Reconciliación y alcance

| Comprobación real | Resultado |
| --- | ---: |
| Parcelas únicas / filas CP del piloto | 3.790 / 3.790 |
| BU asociados por parcela | 3.761 |
| Filas de enlace CEEE | 5.106 |
| Pares registro/parcela distintos | 5.105 |
| Registros CEEE confirmados distintos | 5.105 |
| Códigos administrativos CEEE repetidos | 0 |
| Parcelas con construcción / con energía | 3.760 / 2.105 |
| Parcelas con 1–2 letras observadas | 1.426 |
| Parcelas con más de un ámbito | 424 |
| CP no utilizables / cruzando límite | 0 / 0 |
| Intervalos constructivos invertidos | 0 |
| Fechas energéticas inválidas o ausentes | 0 |

El enlace repetido no multiplica el recuento. Todos los registros del piloto confirman parcela; ninguno confirma cobertura del edificio físico. Ámbitos: 4.023 vivienda, 507 parte/local, 476 edificio completo declarado y 99 desconocidos. Mediana de registros por parcela observada: 2; percentil 95: 6; máximo: 44. Los recursos de extracción 2025–2026 contienen fechas declaradas desde 2013: se separan ambos conceptos.

`audit.json` reconcilia de forma programática universo, unicidad de parcela, recuento por parcela contra enlaces deduplicados, suma A–G frente al denominador, proporción E/F/G frente a numerador y denominador, nulos cuando faltan letras, rango de proporciones y ausencia de IPR. Los estados de enlaces, exclusiones, códigos, ámbitos, fechas, geometrías y quantiles quedan en el informe. La CLI aborta ante una reconciliación incorrecta. Esto comprueba coherencia interna de las capturas; no acredita exactitud administrativa, vigencia de certificados ni correspondencia física independiente.

Se compararon todas las columnas compartidas v1/v2 mediante `assert_series_equal`: los indicadores originales son iguales. El replay compara todos los Parquet y los JSON de auditoría/cobertura. Duración y procedencia del código pueden variar entre manifiestos; son metadatos de ejecución, no diferencias analíticas.

## Defectos preventivos corregidos

- Una identidad BU/CEEE con atributos contradictorios ya no se resuelve por primera fila: se rechaza. Repeticiones idénticas en atributos analíticos se deduplican.
- Una RC con dos filas CP no se vuelve única al filtrar distrito: la ambigüedad se cuenta en toda la captura. Solo CP globalmente única acepta evidencia energética confirmada.
- Referencias/enlaces huérfanos, estados contradictorios y claves vacías se rechazan; códigos administrativos con referencias diferentes se excluyen aunque se recibiera un estado confirmado incoherente.
- Las fechas energéticas se convierten antes de agregar; no se ordenan cadenas. Años fraccionarios, fuera de 1000–2026 y periodos invertidos no generan antigüedad interpretable.
- Universo vacío, ninguna letra válida y ausencia de fechas tienen pruebas específicas; no se sustituyen proporciones ausentes por cero.
- La exportación neutraliza cadenas que una hoja de cálculo podría ejecutar como fórmulas. No altera números ni el dataset fuente.
- En eventos: infinitos, extracción inválida, URL sin HTTP(S), evidencia vacía y expedientes en blanco no producen importes o ejecución confirmada. Se preserva `amount_raw`. Se rechazan concesiones con resolución, importe o localización contradictorios.

No se detectaron estos errores latentes en los datos reales de Chamberí; las correcciones protegen futuras capturas y extensiones. Las pruebas sintéticas nunca se incorporan a productos reales.

Se detectó además un riesgo de duplicar certificados multiparcela al sumar denominadores de grupos. La comparación v2 ahora deduplica por `(record_id, grupo)` usando observaciones y muestra `pooled_grade_denominator`, `pooled_efg_numerator` y `pooled_unit=unique_records_per_group`. Si solo se dispone de features v1, la unidad se declara explícitamente `record_parcel_pairs`; no se anuncia como registros únicos. Las medianas por parcela siguen usando cada parcela una vez. Un certificado que abarca varios grupos puede contar una vez en cada grupo; los grupos no forman un censo disjunto de certificados. El piloto actual no tiene certificados multiparcela distintos, por lo que sus cifras no cambian.

## Sesgo de cobertura y de ponderación

| Periodo más antiguo | Parcelas | Con energía | Cobertura | Mediana E/F/G por parcela | Proporción E/F/G agrupada por registro |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hasta 1940 | 1.230 | 677 | 55,0% | 1,000 | 0,778 |
| 1941–1960 | 1.391 | 777 | 55,9% | 1,000 | 0,701 |
| 1961–1980 | 786 | 476 | 60,6% | 0,750 | 0,665 |
| 1981–2000 | 247 | 131 | 53,0% | 0,750 | 0,603 |
| 2001–2026 | 106 | 44 | 41,5% | 0,619 | 0,570 |

30 parcelas no tienen periodo, ninguna con energía vinculada en esta captura. La mediana da el mismo peso a cada parcela con letras; la proporción agrupada usa registros únicos con letra dentro de cada grupo. Su divergencia evidencia por qué no se deben intercambiar. Cobertura no es porcentaje de viviendas o edificios certificados. La captura administrativa no es muestra aleatoria: no cabe inferir necesidad de rehabilitación de las parcelas sin registros ni causalidad entre año y letra. No se construyen intervalos de confianza de población sobre una selección administrativa.

Para comparación espacial se deriva una malla de 500 m en EPSG:25830 del punto de referencia CP, con origen métrico fijo: `E{x//500*500}_N{y//500*500}`. No son barrios ni distritos nuevos. Hay 29 celdas, 23 con ≥20 parcelas y ≥5 con letras (3.759 parcelas en esas celdas). Se muestran tamaños/cobertura de todas las celdas; se ocultan proporciones comparativas de grupos pequeños o de localización desconocida. Son umbrales operativos, no garantía de precisión. Las celdas periféricas tienen superficies parciales dentro del distrito; no se calculan densidades ni se atribuye significado social a la retícula.

## Perfiles y sensibilidad

Perfiles descriptivos mutuamente excluyentes, independientes del contexto constructivo:

| Perfil | Parcelas |
| --- | ---: |
| Sin registros vinculados | 1.685 |
| Sin letra interpretable | 0 |
| Muestra escasa (1–2 letras) | 1.426 |
| E/F/G en ≥75% de al menos 3 registros | 357 |
| Otras distribuciones observadas | 322 |

No son categorías de necesidad de obras. Los umbrales 3 y 75% son explícitos y revisables, sin calibración técnica. Cada parcela conserva periodo, cantidad de BU, cantidad de letras, proporción, ámbitos y avisos; se ofrece explicación individual. No hay compensación entre dimensiones ni ranking recomendado.

20 escenarios del comparador B: pesos de antigüedad 0/0,25/0,5/0,75/1 y mínimos de letras 1/3/5/10. Elegibilidad: 2.105/679/208/30 parcelas respectivamente (55,5%/17,9%/5,5%/0,8% del universo). Las diferencias se calculan sobre la intersección con el escenario base peso 0,5/mínimo 3; no se asignan puntuaciones a excluidas. Correlación de rangos mediante Pearson de rangos medios, con empates; nula si no hay variación suficiente.

En mínimo 3, peso 0 frente al base: cambio absoluto mediano 9,5 puntos y correlación de rangos 0,851; peso 1: 9,5 puntos y 0,694. El máximo cambio frente al base llega a 50 puntos. La diferencia entre los escenarios 0,25 y 0,75 mantiene mediana 9,5 y máximo 50. Con peso 0,5, subir el mínimo cambia la población elegible, aunque no la fórmula de las parcelas comunes: un cambio cero no demuestra robustez frente a selección. El factor de antigüedad se satura a cien años, generando empates. Se mantiene el perfil A como principal; B es solo auditoría, no IPR global.

## Rendimiento y mantenimiento

Los análisis se materializan mediante CLI; Streamlit no lee las cuatro tablas municipales para recalcular features. `analysis_store.py` lee solo nombres fijos y versiones admitidas, verifica SHA-256 al cargar y detecta cambios durante lectura. `st.cache_data` usa ruta resuelta y firma de tamaño/mtime/ctime de los archivos leídos y del manifiesto; invalida al cambiar/eliminar productos. Las copias retornadas no contaminan la caché. Es control de integridad local, no firma criptográfica de una autoridad.

Benchmark reproducible `tests/benchmark_analysis.py`: primera medición v2, mediana 0,156 s sin caché frente a 0,0037 s con caché; diez llamadas calientes sin lectura Parquet; filtrado 679 parcelas 0,024 s; CSV 0,019 s. Medición de cierre: aproximadamente 0,174 s frente a 0,0050 s en la última ejecución; hay variación entre mediciones. Mediciones finales en `reports/session_6_deepening/analysis_performance.json`. No miden red, WebGL, GPU ni tiempos percibidos en navegador. La CLI con auditoría cuesta más que v1 porque añade reconciliación, perfiles, escenarios y observaciones; no se ejecuta por interacción.

La revisión de código no introduce dependencias ni altera fuentes originales. Se separan agregación (`features`), auditoría, perfiles, almacenamiento, gráficos y presentación. La API `analytics.parcel_features` y `analysis_view.filter_profile` se conserva. Los tests previos de selección/filtros del mapa se mantienen. Navegador sigue pendiente por restricciones ya comprobadas: se usa AppTest, sin repetir intentos de red o navegador bloqueados.

## Eventos oficiales futuros

Importación y matching canónico de `events.py`; lectura de captura con `load_event_snapshot`; agregación opcional con `aggregate_event_features`. El manifiesto debe corresponder al mismo SHA-256 de CP que el análisis, al tipo correcto y al hash de `events.parquet`. La CLI acepta `--inspections-dir` y `--grants-dir` únicamente cuando el operador aporta capturas revisadas; la comprobación de hash no valida licencia ni semántica por sí misma.

Sin fuente (`None`) no aparecen recuentos ficticios; captura vacía revisada sí tiene cero enlaces observados, nunca prueba ausencia real. Solo eventos confirmed/parcel y CP única se agregan. ITE mantiene última fecha histórica y resultado ambiguo si hay conflicto en esa fecha; subsanación desconocida permanece nula. Concesiones se concilian globalmente por organismo/programa/expediente antes de repartir, excluyendo conflictos entre parcelas. Solo EUR conocido se suma; se conserva número de importes conocidos. Pago no se suma con concesión. Ningún evento confirma edificio físico ni ejecución por sí solo. No se activó ninguna fuente opcional en productos reales.


## Validación de cierre

142 pruebas unittest/AppTest superadas (95 del cierre anterior más 47 de profundización), Ruff correcto y formato de módulos/tests nuevos correcto. `git diff --check` sin incidencias. CLI final: aproximadamente 8,12 s, con auditoría y escenarios. Replay de todos los Parquet y JSON analíticos idéntico, CSV de periodos idéntico, todas las columnas compartidas v1 preservadas y hashes del código coincidentes con el manifiesto. Originales y sesiones 1/2 comprobados por hash: intactos. Escaneo de patrones de secretos en código/tests sin hallazgos. Git no sigue datos ni reports; sin commits/push. Evidencias: `reports/session_6_deepening/audited_tests.log`, `verification.json`, `analysis_performance.json` y manifiestos de salida.

No se repitieron descargas fallidas ni intentos de navegador bloqueados. Pytest sigue sin instalarse, conforme al bloqueo documentado del cierre anterior; se usa unittest del proyecto. Aceptación manual pendiente para leyenda, zoom, aspecto de gráficos, CSV en hoja de cálculo, continuidad de selección/OSM/offline y distribución horizontal. AppTest no valida representación real de WebGL.
