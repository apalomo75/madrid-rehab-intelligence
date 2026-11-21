# Sesión 39 · Mapa, búsqueda y experiencia móvil

## Paquete revisado

La revisión utiliza `madrid_rehab_v1_04.tar.gz` extraído en un directorio temporal. El SHA-256 comprobado es `eacac41b3583b2bc2f14661c66c0d0323892de52b67fd811f25795eec7feca5c`. La aplicación autentica el manifiesto y los archivos al abrir el paquete. Los cambios se aplican en el visor y en la consulta de datos existentes. Para esta corrección basta v1.04.

## Qué explicaba la alineación

Se cruzaron las referencias efectivamente enviadas al mapa con el Parquet catastral del mismo municipio. En cada combinación con resultados se comprobó igualdad de los anillos y sus vértices frente a una proyección directa EPSG:25830 → EPSG:4326 con `always_xy=True`. Las coordenadas GeoJSON son longitud y latitud. Se comprobó una página de la selección original para cada caso de la tabla, además de la coherencia de referencias, el límite de carga y la ausencia de polígonos sustitutos en esas páginas. El visor comercial ya conservaba la geometría sin simplificar.

| Municipio | Sin filtro | CEEE | ITE/IEE | Plan Rehabilita | NextGenerationEU | P5 | CEEE OR P5 | CEEE AND P5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Madrid | 113.550 | 51.842 | 0 | 1.919 | 3.300 | 491 | 52.001 | 332 |
| Móstoles | 6.819 | 2.229 | 0 | 0 | 277 | 78 | 2.244 | 63 |
| Alcalá de Henares | 9.460 | 2.442 | 0 | 0 | 208 | 43 | 2.455 | 30 |
| Alcorcón | 3.008 | 1.470 | 0 | 0 | 244 | 39 | 1.473 | 36 |
| Leganés | 6.597 | 2.133 | 0 | 0 | 198 | 22 | 2.137 | 18 |
| Getafe | 13.339 | 2.472 | 0 | 0 | 151 | 7 | 2.476 | 3 |

Los ceros corresponden al alcance del paquete. En particular, la lista de referencias ITE/IEE del manifiesto v1.04 está vacía. El filtro por sí solo no permite concluir nada sobre inspecciones, obligaciones o conservación.

- **Paginación.** Antes, la primera página se recortaba por orden de referencia catastral. En Alcalá, sus centroides abarcaban 496 m este-oeste y 3.636 m norte-sur frente a 8.374 × 6.280 m en el conjunto sin filtro. Con CEEE, la primera página de Leganés abarcaba 2.750 × 6.108 m frente a 6.990 × 6.108 m en el conjunto filtrado. El selector de página funcionaba, pero la página inicial, el orden de referencias y el zoom fijo podían hacer que esa franja pareciera representar el resultado entero.
- **Encuadre.** La vista anterior centraba un punto representativo de la unión y usaba zoom fijo. Al seleccionar, centraba toda la página en una sola parcela. El encuadre actual con límites de la página permite mantener visibles las demás parcelas durante la selección. El mapa de una ficha abierta por dirección enfoca su propia parcela.
- **Concentración real.** Getafe arroja tres parcelas con CEEE AND P5. Su dispersión por el eje menor es aproximadamente el 2,1 % de la del eje mayor, calculada con los centroides en metros. Las tres están en la única página. La alineación de ese conjunto ya está en los datos.
- **Geometría.** La comparación no detectó vértices alterados ni ejes intercambiados. La selección sigue limitada a las referencias catastrales presentes en geometrías utilizables de la página activa.

## Experiencia de mapa

La vista comercial retira la lista, conserva el contador de parcelas, agrupa por cercanía en páginas deterministas de hasta 500 CP y centra cada página según sus límites. Toda referencia del resultado pertenece a una sola página. Las agrupaciones son de navegación y no corresponden a nuevos barrios o divisiones oficiales.

El amarillo ocre tiene relleno translúcido y un borde más claro. La selección intensifica el borde y el relleno. En escritorio, la ficha abre a la derecha y el mapa ocupa todo el ancho cuando se cierra. En móvil, la ficha aparece debajo y los filtros y la zona se abren en un desplegable. Se conservan «Ampliar ficha» y el retorno a la página actual. Los filtros y la selección se conservan al alternar las secciones de producto. Al cambiar de filtros se mantiene la parcela si sigue incluida. Cambiar de página cierra la ficha de la página anterior.

## Cobertura de búsqueda

| Municipio | Versiones en el índice postal v1.04 | Resultados recuperables | Vías en los resultados | Números distintos |
| --- | ---: | ---: | ---: | ---: |
| Madrid | 214.083 | 176.344 versiones postales públicas | 7.872 | 978 |
| Móstoles | 0 | 265 direcciones de expediente | 118 | 64 |
| Alcalá de Henares | 0 | 41 direcciones de expediente | 35 | 20 |
| Alcorcón | 0 | 12 direcciones de expediente | 11 | 10 |
| Leganés | 0 | 173 direcciones de expediente | 82 | 69 |
| Getafe | 0 | 33 direcciones de expediente | 30 | 16 |

Madrid utiliza el callejero municipal y sus accesos con puente documental CP. El índice contiene 8.621 vías, 188.271 pares vía/número, 206.982 versiones con relación CP confirmada, 730 ambiguas y 6.371 sin vínculo confirmado. Las 176.344 versiones admitidas por el catálogo público representan 156.484 pares vía/número. Los números de la tabla son valores de número distintos incluso cuando se repiten en varias vías. Las versiones pueden compartir literal o parcela.

Fuera de la capital, el índice postal no contiene versiones. El buscador recupera un subconjunto de domicilios declarados de los expedientes PRTR autorizados de v1.04. Exige referencia catastral explícita única, vínculo de expediente confirmado y parcela admitida en el mismo municipio. Acepta literales numerados simples y elimina las claves de consulta que apuntan a más de una parcela. Las cifras cuentan pares de literal original y CP recuperables. Los datos de expediente siguen asociados a la parcela documentada. La selección no acredita la identidad de un portal, edificio o vivienda. Los literales complejos, con rangos, calificadores de significado incierto o varios inmuebles, quedan fuera de ese subconjunto. Los textos de CEEE y enlaces AD del GML tienen otros ámbitos y no se incorporan como callejero.

La búsqueda pública admite calle más número en dos campos o una dirección completa con el número al final. «Complemento» se conserva en la consulta técnica. Los calificadores admitidos en Madrid se pueden escribir junto al número, como `24 B` o `24 BIS`. El buscador tolera tildes, mayúsculas, prefijos como `C/`, `Cl`, `Av.`, `Avda` y `P.º`, y conserva los literales en los resultados. El botón de apertura lleva a la CP confirmada. En Madrid también se conserva la apertura al seleccionar explícitamente una coincidencia de una sola CP.

Búsquedas reales de regresión con variantes acentuadas, sin acento y abreviadas.

| Municipio | Consulta completa | Variante en los dos campos |
| --- | --- | --- |
| Madrid | Calle Bailén 12 | C/Bailen · 12 |
| Móstoles | Calle Joaquín Blume 9 | C/Joaquin Blume · 9 |
| Alcalá de Henares | Calle Santa Mónica 10 | Cl Santa Monica · 10 |
| Alcorcón | Calle Berlín 16 | Cl Berlin · 16 |
| Leganés | Avenida Bélgica 83 | Avda Belgica · 83 |
| Getafe | Avenida Manuel Azaña 13 | Av. Manuel Azana · 13 |

«Calle Río Bidasoa 1» devuelve una CP diferente en Móstoles y Alcalá de Henares. «Calle Madrid 8» devuelve una CP en Alcorcón y ninguna coincidencia de expediente en Getafe. Se comprobó también la ausencia de resultados para números ausentes en las muestras piloto.

Para ampliar la cobertura hace falta un producto posterior con callejero/portales y relaciones documentales con CP. El CNIG ofrece CartoCiudad para consolidar vías y portales con atribución CC BY 4.0. El servicio AD de Catastro documenta la consulta de direcciones asociadas a una referencia catastral y es candidato para verificar ese puente bajo sus propios términos. La coincidencia espacial o la proximidad de un punto solo servirían como indicios para revisión. [CartoCiudad, Centro de Descargas del CNIG](https://centrodedescargas.cnig.es/CentroDescargas/novedades?codSerie=02122) · [Servicio de direcciones de Catastro](https://www.catastro.hacienda.gob.es/webinspire/documentos/inspire-ad-wfs.pdf) · [Licencia de Cartografía Catastral INSPIRE](https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf)

## Textos en móviles

Chromium devolvió `UTF-8` y el índice postal y los literales PRTR publicados no contienen el carácter de reemplazo U+FFFD. Las tildes, eñes y nombres se conservaron en la consulta y en los resultados. El tooltip anterior repetía la referencia catastral como nombre y como identificador. Se retiró en la vista comercial y los metadatos postales se muestran solo en la consulta técnica. El control del ámbito CEEE ahora tiene una etiqueta visible, independiente de que cargue la fuente de iconos. Las etiquetas y valores constructivos de la ficha se reparten en varias líneas en paneles estrechos y el botón de pantalla completa deja espacio al texto de ayuda en móvil. También se corrigió el singular «1 coincidencia».

El documento raíz de Streamlit declara `lang=en` incluso al mostrar la interfaz en español. Esta diferencia es comprobable, pero no identifica la causa de lo observado en el teléfono. El selector ES/EN cambia las etiquetas de la aplicación. La traducción automática del navegador, la sustitución de fuente y el renderizado específico del dispositivo requieren una captura del caso real. Para reproducirlo se necesita modelo del móvil, versión del sistema y navegador, URL o sección, texto esperado y observado, idioma de la app, estado de traducción automática y, si es posible, una captura de la misma pantalla con esa traducción desactivada. Chrome Android, Samsung Internet y Safari en teléfonos reales siguen pendientes.

## Revisión local

```bash
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session39.py -v

MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 \
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_04_candidate_01 \
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512

PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser \
.venv/bin/python tests/browser_session39.py --output-dir reports/session_39/browser_nuevo
```

Las cinco pruebas de regresión de la sesión y Ruff pasaron. La comparación de referencia cubrió las 48 combinaciones de municipio y filtro de la tabla. Los resultados están en `reports/session_39/baseline.txt` y las comparaciones de anillos y serialización en `reports/session_39/validation_final.txt`. La preparación de geometría más JSON pasó de 1.125 ms a 307 ms de mediana en la comparación local sobre las mismas páginas. El límite de carga sigue siendo 500 geometrías y se leen tres columnas del Parquet para el mapa. El proceso de auditoría que ejecutó ambas versiones alcanzó unos 400 MiB de memoria máxima. La medición corresponde a Python en este equipo y deja pendiente la latencia y el consumo de memoria de Streamlit Community Cloud y de los teléfonos.

En Chromium se abrió una ficha desde el mapa por clic a 1.440 px y por toque a 320 y 390 px. El equipo carece de GPU accesible y SwiftShader puede demorar la detección por encima de la ventana de 250 ms del reconocedor de gestos. En esa configuración se fijó el reloj de la prueba para validar el envío de la selección y la apertura de la ficha. El parámetro `--software-renderer` reproduce ese modo del ensayo. Esta validación deja pendiente la latencia táctil en hardware real. Las búsquedas abrieron fichas de los seis municipios en escritorio y la de Bailén en ambos anchos móviles, con comprobación de desbordamiento horizontal. El recorrido de Playwright comprobó además la segunda página, el panel lateral o inferior, la apertura y el cierre del diálogo y la ficha, los cinco filtros, OR/AND y el cambio ES/EN entre las secciones del producto. Las capturas y el registro quedaron en `reports/session_39/browser_05/`. La ejecución ampliada de pruebas históricas recibió una señal de terminación y quedó sin resultado global.
