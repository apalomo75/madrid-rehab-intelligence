# Análisis de la ejecución real run_002

Fecha de revisión: 21 de octubre de 2026. No se ha ampliado la muestra ni desarrollado interfaz. Los originales de `data/raw/run_002`, `data/processed/run_002` y `reports/run_002` permanecen intactos.

## Evidencia y alcance

Se han leído `results.json`, `config.json`, ambos esquemas, `snapshot.json`, los dos Parquet y los cuerpos HTTP GML conservados. Los SHA-256 de los dos Parquet y del snapshot coinciden con los declarados en `results.json`. Se han contrastado también `normalize.py`, `sources.py`, `integrate.py` y `pipeline.py`.

La ejecución es una muestra HTTP oficial, sin errores registrados, no una prueba sintética. Procesa 30 filas y 30 referencias, sin identificadores de fila ni códigos de certificado repetidos. Confirma cuatro inmuebles RC20 y cinco parcelas; cinco filas tienen coincidencia de identidad (16,67%). Esto no equivale a cinco edificios certificados. Los 24 `parcel_not_confirmed` corresponden a referencias no consultadas: no son respuestas negativas de Catastro. La restante está fuera del patrón admitido.

Se seleccionaron las cinco primeras referencias válidas ordenadas lexicográficamente **solo entre las filas cuyo municipio es Madrid**. Por tanto, 5/30 no estima precisión del cruce, cobertura municipal ni frecuencia de certificados de edificio. Las cinco seleccionadas obtuvieron parcela y candidato BU; las cuatro RC20 seleccionadas también obtuvieron confirmación DNPRC.

## Columnas reales y ámbito energético

Hay 87 columnas originales. `source_schema.json` describe tipos y nulos, pero no conserva las notas semánticas: estas sí están en `snapshot.energy.fields[].info.notes`. `edif_tipo` se define allí como «Tipo de edificio o parte del edificio certificado». `edif_tiporeg` describe el registro nuevo/existente; sus valores (29 `Edificio Existente`, uno `Edificio Terminado`) **no indican** que el certificado cubra todo un edificio.

Las columnas pertinentes son `edif_refcat`, `edif_muni`, `edif_direc`, `edif_codreg`, `edif_tipo`, `edif_fecha` y `edif_superf`. Esta última es superficie habitable en m², no huella en planta. `cal_norenovglobal` y `cal_co2global` son letras; `norenov_global` y `norenov_co2global` son valores numéricos. En el Parquet de enlaces estos valores numéricos se conservan como cadenas, por lo que requieren conversión controlada antes de cálculos.

| Valor exacto observado de edif_tipo | Filas | Normalización recomendada | Interpretación y cautela |
| --- | ---: | --- | --- |
| ViviendaIndividualEnBloque | 11 | dwelling | Vivienda dentro del bloque: nunca trasladar su letra al conjunto |
| ViviendaUnifamiliar | 8 | dwelling | Vivienda unifamiliar; puede cubrir su edificio residencial, pero exige comprobar correspondencia física y anexos antes de enlazar toda la geometría BU |
| BloqueDeViviendaCompleto | 10 | whole_building | Declaración explícita de bloque completo; no acredita por sí misma qué construcciones catastrales abarca |
| LocalUsoTerciario | 1 | building_part | Local de uso terciario; no edificio terciario completo |

Esta propuesta se apoya en la descripción oficial del campo y la semántica inequívoca de los cuatro nombres; no se presenta como un catálogo exhaustivo oficial de códigos. Conviene versionar la tabla y su evidencia por recurso. Cualquier valor futuro no revisado debe seguir como `unknown`.

Los 30 `unknown` actuales son consecuencia de `scope_map: {}` y del comportamiento de `certification_scope`, no de ausencia de información en la fuente. Una aplicación **en memoria**, sin escribir los resultados originales, de la tabla anterior devuelve 19 viviendas, 10 bloques completos, una parte y cero desconocidos. Esta clasificación es de ámbito declarado, no validación física.

No inferir ámbito a partir de RC14/RC20: siete bloques completos tienen RC14 y tres tienen RC20. Todos los otros tipos usan RC20. Los tres bloques con RC20 declaran superficies de 70,5, 170 y 64 m²: son señales de posible incoherencia que requieren revisión, no prueba automática de error. Las superficies de bloques con RC14 van de 455 a 2.380 m².

## Distribución municipal

| Municipio, conservando denominación de origen | Filas |
| --- | ---: |
| Madrid | 16 |
| Alcalá de Henares | 2 |
| Móstoles | 2 |
| Boadilla del Monte | 1 |
| Valdemoro | 1 |
| Torres de la Alameda | 1 |
| Villanueva de la Cañada | 1 |
| Casarrubuelos | 1 |
| Villaviciosa de Odón | 1 |
| Getafe | 1 |
| CAMPO REAL | 1 |
| Aranjuez | 1 |
| VILLANUEVA DEL PARDILLO | 1 |

Son 13 municipios: 16 filas de la capital y 14 de otros municipios. Los cinco candidatos consultados son de la capital por decisión del código. No hay evidencia distrital ni base para escoger Usera, Chamberí o Carabanchel. Para futuras selecciones usar municipio normalizado/código oficial y declarar el denominador municipal; conservar siempre el literal original.

## Referencias: longitud, formato y anomalías

Hay 23 cadenas de 20 caracteres y siete de 14; ninguna vacía, ninguna multirreferencia y ninguna longitud distinta. Son 30 valores distintos. El algoritmo admite las 23 RC20 y seis RC14 (29 en total), sin validar caracteres de control. Una RC20 identifica inmueble y su prefijo RC14 parcela; ninguna de las dos identifica necesariamente un bloque físico.

La RC14 restante tiene una `J` en la sexta posición, dentro del primer grupo de siete caracteres que el patrón exige numérico. Ejemplo enmascarado: `*****J********`. Se clasifica correctamente como **no admitida por nuestro patrón**, pero no hemos confirmado con autoridad si es errata, codificación excepcional o referencia válida no soportada. No sustituir letras por números ni declararla inexistente. No se consultó. Debe quedar en revisión separada con motivo preciso.

Los cuatro inmuebles confirmados por DNPRC no equivalen a comprobar localmente el checksum de todas las RC20. `checksum_validated_count=0` sigue siendo correcto.

## Las cinco geometrías BU y los enlaces que faltan

Ejemplos seudonimizados A–E, ordenados como los cinco candidatos seleccionados. No se reproducen direcciones, RC, códigos de certificado ni coordenadas individuales.

| Caso | Ámbito literal | Referencia | Superficie CEEE m² | Viviendas / unidades BU | Diagnóstico |
| --- | --- | --- | ---: | --- | --- |
| A | BloqueDeViviendaCompleto | RC20 | 170 | 132 / 301 | Ámbito declarado completo, pero inmueble individual y muchas unidades en el BU; no atribuir su letra al agregado sin revisar cobertura |
| B | ViviendaIndividualEnBloque | RC20 | 64 | 47 / 50 | Certificado de vivienda; la coincidencia de parcela no certifica las 47 viviendas |
| C | ViviendaIndividualEnBloque | RC20 | 73 | 16 / 16 | Igual limitación de ámbito |
| D | ViviendaIndividualEnBloque | RC20 | 34 | 83 / 287 | Igual limitación; agregado con numerosas unidades |
| E | BloqueDeViviendaCompleto | RC14 | 1.000 | 18 / 20 | Mejor candidato para revisión de edificio completo; falta demostrar que el bloque certificado cubre la construcción representada |

Los cinco BU tienen uso `1_residential`, identificador y geometría. Cada parcela tiene un único identificador BU candidato. Esto **no prueba** que tenga un único bloque físico: la documentación de la DGC explica que su Building agrega construcciones sobre rasante de la parcela. BuildingPart representa volúmenes homogéneos, no viviendas ni necesariamente bloques independientes. No se debe equiparar BuildingPart catastral con `building_part` energético.

Limitaciones reales: el enlace RC20→parcela no ubica una vivienda en un volumen; el BU puede agregar más de un cuerpo; tres de los cinco certificados son de vivienda; el caso A presenta una discrepancia de granularidad importante; la muestra no contiene documentación del certificado que resuelva exhaustivamente la cobertura de A o E.

Restricciones del algoritmo: `integrate()` asigna `building_id=None` a todas las filas sin evaluar ámbito ni evidencia adicional; solo devuelve candidatos por parcela. `quality()` fija `certificate_buildings_reliably_geolocated=0` como constante. No hay una fase implementada de resolución certificado→bloque, ni validación topológica. Así, el cero actual es también una limitación de implementación; no demuestra que sea imposible resolver E. Conservar la cautela de no enlazar automáticamente por «un solo BU», pero añadir una ruta de validación con evidencia y estados explícitos.

## Geometría disponible y reproyección

`certificate_reference_links.parquet`: 30 filas, 32 columnas; `x`, `y`, `coordinate_crs`, `coordinate_scope` y `building_id` son nulos en las 30 filas. Cinco `candidate_building_ids` contienen un identificador cada uno; los otros 25 contienen listas vacías. No contiene polígonos.

`building_objects.parquet`: cinco filas, diez columnas; contiene cinco `geometry_wkt` MULTIPOLYGON no nulos, `geometry_crs=EPSG:25830` y `building_geometry_status=structural_only`. En total hay siete polígonos exteriores y un anillo interior. El WKT conserva 222 pares de coordenadas (incluidos cierres). Se ha comprobado su transformación local con PROJ (`cs2cs`, EPSG:25830→EPSG:4326), sin descargas: todos los vértices producen coordenadas finitas, con envolvente conjunta aproximada longitud −3,7051 a −3,6874, latitud 40,3894 a 40,4865. La envolvente es agregada para evitar localizar ejemplos individuales.

La reproyección es viable. Eso no valida topología, exactitud posicional ni cobertura del certificado. No están instalados Shapely, PyProj ni GeoPandas en este entorno; no se afirma haber ejecutado `is_valid` ni validación espacial de huellas. Los Parquet son convencionales (WKT y CRS en columnas), no GeoParquet con geometría binaria y metadatos geoespaciales.

Para una futura derivación: leer WKT con Shapely/GeoPandas, validar anillos y topología en CRS métrico, reproyectar con `to_crs(4326)` o `Transformer.from_crs(25830,4326,always_xy=True)` conservando polígonos y huecos. Usar orden longitud/latitud para GeoJSON. Exportar una copia derivada GeoParquet/GeoJSON con procedencia; conservar el original métrico. Si se necesita un marcador, obtener `representative_point()` en CRS métrico y después transformar; no confundirlo con acceso, centroide o ubicación del certificado.

Los GML CP originales también contienen polígonos y cinco `referencePoint`, pero el parser solo intenta conservar los puntos y descarta los polígonos. Los cinco puntos se perdieron porque su `srsName` es `http://www.opengis.net/def/crs/EPSG/0/25830`, URI equivalente no incluida en la lista admitida. Por eso el snapshot y el Parquet tienen puntos nulos pese a existir en los cuerpos HTTP.

Se ha corregido la lista compartida de CRS de CP y BU para admitir exactamente esa URI sin aceptar otros husos. Releer los cinco GML originales y ejecutar `integrate()` **en memoria** recupera cinco parcelas geolocalizadas; mantiene las cinco coincidencias y cero edificios certificados resueltos. Un replay del snapshot por sí solo no recupera los puntos: ya contiene nulos; hay que volver a parsear los cuerpos HTTP. No se ha reescrito el snapshot ni ningún resultado.

## Mejoras concretas, por prioridad

1. **Recuperar datos ya descargados.** Aplicar el parser corregido a los cuerpos HTTP guardados en una futura ejecución derivada offline con directorios nuevos y hashes de origen. Conservar también polígonos CP, CRS, identificadores y precisión declarada. Separar `not_queried`, `authority_not_found`, `parse_failed` y `ambiguous` en las métricas; no presentar 24 no consultadas como fallo de Catastro.
2. **Versionar la clasificación semántica.** Cargar el mapa revisado de cuatro valores anterior para este recurso, conservar el literal, evidencia y versión. Mantener vivienda unifamiliar como vivienda hasta verificar su correspondencia completa con la construcción. Guardar la superficie original numérica y añadir alertas de ámbito/RC/superficie, sin umbrales que cambien silenciosamente el ámbito.
3. **Separar entidades y relaciones.** Certificado, inmueble RC20, parcela RC14, agregado BU y bloque físico deben seguir siendo entidades distintas. Una relación `certificate→parcel` puede ser fiable sin que exista `certificate→physical_building`. Una vivienda puede localizarse a nivel de parcela sin dar una letra al polígono agregado.
4. **Resolver primero el caso E con datos locales.** Revisar documentación/dirección sin unidad, superficie habitable, número de viviendas y composición geométrica; comprobar si el bloque certificado y la construcción representada son coextensivos. La superficie CEEE no se compara directamente con área de huella. Para A, contrastar especialmente qué abarca el certificado frente a las 132 viviendas. Si faltan pruebas, mantener candidato pendiente y explicar cuál falta. No asignar automáticamente ni afirmar hoy que E está resuelto.
5. **Implementar una fase de resolución auditable.** Una vez demostrada cobertura física, aceptar enlaces completos con motivo y evidencia, soportando varios objetos para un certificado o varios bloques en una parcela. Las partes catastrales y portales pueden ayudar a segmentar, pero ni su proximidad ni conectividad bastan por sí solas. Si se requiere información adicional externa, planificar consultas puntuales antes de ampliar descargas. Preservar las letras solo en el certificado y mostrarlas en un bloque únicamente a través de un enlace de cobertura completa validado.
6. **Sustituir la constante de métricas.** Contar enlaces completos con geometría y evidencia validada; distinguir «resolución no implementada» de «ejecutada sin coincidencias». Añadir pendientes específicos por ámbito, cobertura física, topología y anomalías. Medir por separado viviendas localizadas en parcela y edificios completos certificados.
7. **Mejorar el diseño muestral después de esta revisión.** La selección lexicográfica favorece referencias, no representatividad ni certificados completos. Dentro de los límites actuales se puede priorizar revisión de bloques completos y estratificar por municipio/ámbito; cualquier nueva consulta queda fuera de este análisis. No elegir distrito hasta disponer de geometría validada y límites oficiales.

La solución técnica adecuada es un modelo de relaciones con validación de cobertura física, acompañado de recuperación offline de los puntos CP y clasificación semántica revisada. Relajar el cruce por prefijo RC o por número de candidatos aumentaría falsos positivos, especialmente en viviendas y en agregados BU.

## Cambios y validación

Cambio acotado en `src/madrid_rehab/sources.py`: reconocimiento de la URI oficial EPSG:25830 compartido por CP/BU. Prueba de regresión en `tests/test_pipeline.py`: acepta esa URI y mantiene el rechazo de EPSG:25831. Suite ejecutada: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`, **26 pruebas correctas**. Las pruebas son sintéticas; la comprobación adicional en memoria se hizo sobre los cinco cuerpos CP reales. No se ha instalado un toolchain geoespacial ni implementado asignación automática de edificios.

## Fuentes documentales

- [Recurso CEEE 2026 y diccionario oficial](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica/resource/4e42b49c-bb6b-485a-a7b7-8f760f356855): semántica de `edif_tipo`; sus notas también están preservadas en el snapshot analizado.
- [Catálogo CEEE de la Comunidad de Madrid](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica): cobertura de toda la Comunidad, no solo capital.
- [DGC, Conjuntos de datos INSPIRE, julio de 2016](https://www.catastro.hacienda.gob.es/webinspire/documentos/Conjuntos%20de%20datos.pdf), páginas 19 y 24–26: agregado Building y volúmenes BuildingPart. Sustenta la cautela al equiparar un único objeto BU con un bloque físico.

Las fuentes web se han consultado para documentación, sin descargar más registros CEEE ni consultar nuevas referencias catastrales.
