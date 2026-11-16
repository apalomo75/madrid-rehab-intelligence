# Sesión 29 — Paquete de producción

16/11/2026. Objetivo de publicación: 20/11/2026.

**NO LISTO PARA DESPLEGAR desde GitHub todavía.** El paquete y el arranque público están preparados y probados. Faltan dos acciones de entrega expresamente no autorizadas en esta sesión: publicar los cambios de código y colocar el archivo de datos en una URL HTTPS de solo lectura. No queda pendiente reconstruir fuentes ni desarrollar funciones para este alcance. Después se necesita la revisión del primer despliegue real, especialmente WebGL y recursos con varias sesiones.

No se ha hecho commit, push, despliegue ni subida de datos. Las modificaciones de S28 siguen presentes. No se modificaron snapshots ni originales y no se ejecutó el ETL de fuentes.

## A. Paquete y tamaño

Producto final: **`data/deployment/madrid_rehab_v1_02/`**. No utilizar `madrid_rehab_v1/`, que es la primera preparación de trabajo. La reproducción independiente está en `data/deployment/replay_s29_01/`; no se activa ni se distribuye junto al paquete.

| Medida | Resultado |
| --- | ---: |
| Inventario conservador S28 | 445 archivos; **1.242.181.124 bytes** |
| Paquete S29 | 260 archivos, incluido manifiesto; **562.372.274 bytes** |
| Reducción absoluta | **679.808.850 bytes** |
| Reducción porcentual | **54,727 %** |
| Archivo de entrega gzip | **355.944.811 bytes** |

No se compara el archivo comprimido con el inventario sin comprimir para inflar la reducción. `reports/session_29_deployment/build_02/comparison.json` contiene cifras y denominadores.

| Contenido del paquete | Archivos | Bytes |
| --- | ---: | ---: |
| Catálogo SQL único | 1 | 175.337.472 |
| CP/BU, relaciones, construcción y distritos | 45 | 328.852.847 |
| CEEE de seis municipios | 12 | 43.782.607 |
| Accesos municipales | 100 | 10.865.367 |
| Órdenes municipales autorizadas | 97 | 3.034.820 |
| Plan Rehabilita: expedientes, vínculos y actuaciones | 3 | 313.341 |
| Atribución | 1 | 651 |
| Manifiesto | 1 | 185.169 |

Cada archivo está descrito en `manifest.json`: ruta relativa, tamaño, SHA-256, origen/hash original, familia, filas, transformación y columnas retiradas. Los hashes de entradas son procedencia histórica; **no son rutas que deban existir en producción**. El manifiesto tiene versión `public-runtime-v1`, política explícita, versión de catálogo, cobertura postal y contadores. `attribution.json` conserva identificación de productores y la prueba de Plan Rehabilita.

### Cómo se redujo sin perder las consultas autorizadas

Se siguieron `app.py` → `city_app` y las tres rutas públicas. Los adaptadores se introducen en las fronteras de lectura existentes: `production_bundle.py` verifica el contrato nuevo; los lectores históricos conservan sus validaciones cuando no hay paquete activo. No se simulan hashes históricos ni se retiran comprobaciones para hacer pasar archivos modificados por originales.

- **Construcción del catálogo:** se autentican las fuentes existentes al preparar; sus agregados globales y manifiestos históricos dejan de ser dependencias de arranque. Tampoco se copian los Parquet comerciales que duplicaban geometrías ya disponibles en CP.
- **Auditoría histórica:** ZIP, GML, cuarentenas, perfiles mixtos, replays y documentos originales no forman parte del runtime. Se conservan en sus ubicaciones originales.
- **Producción:** se conserva una sola base SQLite con las versiones postales, alias y membresía; se elimina la segunda base S20 de 197 MB. La tabla de alias usa clave compuesta `WITHOUT ROWID`, evitando almacenar a la vez toda la tabla y un índice duplicado equivalente. Se conserva la distinción entre dirección no localizada y dirección localizada sin ficha admitida.
- **Fichas y navegación:** se conservan los objetos originales aceptados CP/BU, sus geometrías WKT exactas, relaciones A/B/C y atributos/procedencia necesarios para las seis secciones. Los Building y BuildingPart siguen separados. Se conserva el suplemento S22 y la selección histórica por distrito.
- **Parquet:** orden estable por identidad, compresión Zstandard y grupos de 1.024 filas para selección acotada. Se retira únicamente `raw_json`, serialización del ETL no consultada por los modelos/vistas; sus campos tipados y hashes de procedencia permanecen. No se simplifican geometrías ni se suman superficies.

El inventario de 445 archivos no contiene archivos con SHA-256 idéntico. Hay solapamiento de atributos/geometrías entre productos CP/BU y enriquecidos, pero sus registros y contratos son distintos; no se eliminaron por parecido. El volumen restante se concentra en esos objetos y el índice postal. No se ha impuesto un límite artificial ni se afirma que 562 MB sea un mínimo matemático.

**Conservación comprobada:** `value_preservation.json` contrasta los **257 Parquet** del paquete con sus filas de origen y columnas conservadas, incluidas geometrías. Los únicos subconjuntos distintos son los documentados por permisos y vínculos A de Plan Rehabilita; los dos campos nuevos de procedencia oficial están identificados. Las 445 fuentes del inventario mantienen sus hashes. Una segunda preparación produce **los mismos 260 archivos byte por byte**, incluido SQLite y manifiesto: `reproducibility.json`.

## B. Arranque y memoria

La prueba final usa `/tmp/madrid-rehab-s29-clean`, un HOME temporal, entorno `env -i`, paquete independiente y dependencias declaradas en el venv limpio creado en S28. Se reinstala el paquete Python desde la copia S29, sin PYTHONPATH en el recorrido. No hay `data/processed/` fuera del paquete en esa copia. Son archivos mantenidos del árbol de trabajo, incluidos los cambios S28/S29 pendientes de commit; no se afirma que estén ya publicados en GitHub.

El guard de prueba rechaza toda lectura Pandas Parquet o conexión SQLite fuera de la raíz del paquete y registra las rutas. La ausencia física de snapshots alternativos evita fallback de otras lecturas. El intérprete y bibliotecas pertenecen al venv/host; no es una imagen nueva de Linux ni la infraestructura de Streamlit Cloud.

| Fase final | Tiempo de esa fase | RSS actual | Pico acumulado |
| --- | ---: | ---: | ---: |
| Inicial, antes de abrir la app | — | 132,8 MiB | 132,8 MiB |
| Arranque y primer mapa | 2,951 s | 359,9 MiB | 359,9 MiB |
| Filtro Plan Rehabilita | 0,499 s | 349,7 MiB | 406,0 MiB |
| Ficha con Plan Rehabilita | 0,751 s | 434,2 MiB | 434,2 MiB |
| Cambio a inglés, misma ficha/filtros | 0,770 s | 436,1 MiB | 450,7 MiB |
| AND / OR | 0,923 / 0,508 s | 445,4 / 471,6 MiB | 454,8 / 478,8 MiB |
| Recorrido completo, incluido buscador y cinco pilotos | 17,265 s total | 383,4 MiB al final | **478,8 MiB** |

Referencia S28: **941,375 MiB** de pico; reducción final **462,586 MiB / 49,14 %**. Su primer arranque medido fue 4,225 s. Los recorridos completos no son idénticos: S29 añade Plan público, OR/AND y comprobaciones, por lo que no se comparan sus tiempos totales como benchmark equivalente.

La primera prueba del paquete todavía alcanzó 853 MiB. Se corrigió el origen de esa presión sin cambiar datos: lectura Arrow sin prebuffer ni paralelismo por consulta, categorías para etiquetas repetidas del índice y booleanos compactos. Se evita construir en RAM el diccionario postal de todo Madrid para etiquetar diez resultados: hay una tabla indexada de etiquetas y consultas acotadas. Los recuentos específicos ITE se preparan desde las órdenes autorizadas, sin releer todos los eventos al arrancar. La preparación no recalcula uniones espaciales ni correspondencias postales.

Las cachés existentes siguen limitadas; el contrato del paquete comprueba cambios de tamaño/mtime/ctime y autentica SHA-256 en frío. No se carga otro municipio para dibujar una página. Hay máximo 500 geometrías por mapa. La descarga inicial se comparte mediante un bloqueo entre hilos y caché de proceso.

El pico local queda por debajo del mínimo aproximado de memoria publicado por [Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app), pero **no acredita la concurrencia ni la asignación real de Cloud**. Las medidas son AppTest/Python; excluyen GPU/renderizado del navegador. No hay Chromium disponible y no se declara validación visual. El servidor real arrancó en 127.0.0.1:8529, respondió `ok` en health y se detuvo.

## C. Datos públicos y Plan Rehabilita

| Fuente | Política del paquete nuevo |
| --- | --- |
| Catastro INSPIRE | Producto derivado de integración: identidades normalizadas, selección documental y relaciones entre fuentes; geometrías conservadas, sin originales ZIP/GML ni datos protegidos. Se aplica la [licencia específica](https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf): transformación sin desnaturalización, producto independiente y no fehaciente. No se presenta como servicio oficial ni se deduce autorización de un mero cambio de formato. |
| CEEE | Disponible, con ámbito, estados y unidades originales, atribución Comunidad de Madrid y [ficha CC BY 4.0](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica). |
| Órdenes de conservación | Solo eventos de la fuente municipal [300377, CC BY 4.0](https://datos.madrid.es/dataset/300377-0-conservacion-rehabilitacion). Mantienen condición histórica y vínculos. |
| ITE/IEE | Los PDF de obligaciones y resultados no se distribuyen por permiso pendiente. El filtro sigue funcionando exclusivamente sobre menciones explícitas ITE/IEE en órdenes 300377; la limitación aparece en ES/EN. No son inspecciones realizadas ni cero incidencias. |
| Callejero/puente | Se completó la comprobación puntual de [200075, CC BY 4.0](https://datos.madrid.es/dataset/200075-0-callejero), que identifica la asociación de parcelas; complementa 213605 ya acreditado. No se incorpora otra fuente ni versión. Los límites regionales IDEM no son necesarios en estas rutas y quedan fuera del paquete. |
| Plan Rehabilita | **Habilitado solo en este paquete**, después de verificar archivo oficial exacto y condiciones específicas. Los snapshots y controles históricos no se modifican. |
| PRTR | **Bloqueado y excluido**, incluidos importes, expedientes, conteos de coexistencia y contribución a la membresía. No hay fallback al visor ni a datos locales. |

### Verificación puntual de Plan Rehabilita

La [ficha oficial](https://geoportal.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=00000009-b145-11ea-a01e-ecb1d753f6e8) enlaza expresamente el ZIP y las [condiciones municipales](https://datos.madrid.es/pages/condiciones-generales-ayuntamiento-de-madrid). Se obtuvo una sola copia acotada del mismo recurso ya integrado, únicamente para contrastar procedencia: HTTP 200, **712.277 bytes**, Last-Modified **19/10/2026 07:19 UTC**. Coincide byte por byte y todos sus miembros coinciden con el archivo local preservado.

SHA-256 común: `5c9ba32bb5871e5c0af2f7b15148373a694d635c8ca633a7e7d05e4bcaedd66b`.

Prueba: `plan_source_verification.json` y copia oficial conservada en el informe, **fuera del paquete**. No se volvió a ingerir ni se sustituyó el ZIP original. La fecha HTTP se presenta como versión oficial contrastada, no como fecha de concesión o de captura original. Se informó al propietario antes de implementar la habilitación limitada.

En la ficha, sin exigir abrir otro sitio, se muestran programa, convocatoria, expediente, actuaciones documentadas, presupuesto protegible, **subvención revisada**, viviendas del expediente, estado individual no verificado y fuente/versión. No se etiqueta `SUB_AYTO_R` como pago o concesión individual acreditada. Se conserva el desplegable de procedencia.

El paquete contiene **1.977 expedientes** con relaciones A utilizables y **1.919 parcelas confirmadas**. Se excluyen vínculos B/C; un mismo expediente puede aparecer en varias fichas sin generar otra entidad ni sumar importes. No existe un total de importes por parcela que multiplique esos expedientes. Las viviendas pertenecen al expediente, no al portal ni al BU.

### Reconciliación del catálogo autorizado

Las reglas A/B/C/D se conservan. Cambian las fuentes que pueden contribuir: desaparecen PRTR y obligaciones PDF sin permiso; Plan A conserva la procedencia ahora acreditada. La política es propia del paquete, sin alterar S24.

| Municipio | CP autorizadas S29 |
| --- | ---: |
| Madrid | 113.543 |
| Getafe | 13.335 |
| Móstoles | 6.817 |
| Leganés | 6.594 |
| Alcorcón | 3.007 |
| Alcalá de Henares | 9.456 |
| **Total** | **152.752** |

Respecto a 153.929 de S28 se retiran **1.177 CP**, por alcance autorizado, no por pérdida de geometría o modificación de umbrales. Hay **176.332 versiones postales admitidas** en Madrid, frente a 178.243; el índice mantiene las 214.083 versiones originales para distinguir localización y exclusión. No se convierten versiones, CP y edificios en el mismo denominador.

## D. Preparación reproducible y entrega

Código añadido: `prepare_production.py`, `production_bundle.py`, `bundle_delivery.py`. Las ramas nuevas se activan únicamente con `MADRID_REHAB_BUNDLE_DIR` o entrega configurada. Los lectores normales y sus snapshots permanecen disponibles para desarrollo local.

Preparación desde las fuentes actuales, siempre en rutas nuevas, sin activar modo bundle durante la construcción:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.prepare_production \
  --output-dir data/deployment/replay_nuevo \
  --report-dir reports/session_29_deployment/build_nuevo \
  --plan-evidence reports/session_29_deployment/plan_source_verification.json

PYTHONPATH=src .venv/bin/python -m madrid_rehab.bundle_delivery verify \
  --bundle-dir data/deployment/madrid_rehab_v1_02

PYTHONPATH=src .venv/bin/python -m madrid_rehab.bundle_delivery pack \
  --bundle-dir data/deployment/madrid_rehab_v1_02 \
  --output reports/session_29_deployment/entrega_nueva.tar.gz
```

La preparación autentica las capturas, copia/reordena/recomprime productos tipados y aplica la política autorizada; no hace descargas, ETL de originales, matching, nuevas inferencias ni procesamiento geográfico. El archivo de evidencia de la verificación puntual ya existe y no se vuelve a descargar al preparar.

Archivo de entrega final disponible:

`reports/session_29_deployment/madrid_rehab_v1_02.tar.gz`

SHA-256:

`ab45ae4d5933e3886d22f47fe201ff074afd1f54a0f9abd3019075c021257c5f`

Se verificó también su extracción completa y los hashes del contenido: `delivery_roundtrip.json`. No hace falta entregar originales, replays, el resto de `data/` o `reports/`.

### Instalación y arranque local equivalentes

Python **3.13**, comprobado en 3.13.5. `requirements.txt` instala el lock de producción y `-e .`; no hace falta PYTHONPATH después de instalar. Se mantienen `.streamlit/config.toml`, el punto de entrada y la configuración segura de S28. Sin nuevas dependencias ni credenciales.

```bash
python3.13 -m venv /tmp/madrid-rehab-production-venv
/tmp/madrid-rehab-production-venv/bin/python -m pip install -r requirements.txt
/tmp/madrid-rehab-production-venv/bin/python -m pip check

MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 \
MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 \
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_02 \
/tmp/madrid-rehab-production-venv/bin/python -m streamlit run \
  src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Las rutas son relativas a la raíz del checkout, como en [Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization). No hay dependencia de `/home/apalo` o `/mnt/c` en el runtime. Las rutas absolutas que aparecen en logs/informes son ubicaciones de la auditoría, no configuración de despliegue.

### Almacenamiento propuesto

El catálogo SQL aún ocupa 175 MB y el archivo de entrega 356 MB; **no conviene Git ordinario**. No se ha añadido ningún dataset a Git. LFS requeriría aprobar almacenamiento/cuotas y versionado de binarios. Se propone **un único objeto HTTPS inmutable de lectura**, con una versión en su URL, y código/configuración en Git.

La entrega ya está implementada: `bundle_delivery.ensure()` descarga solo si se configura URL, verifica el SHA-256 del archivo antes de extraer, rechaza rutas externas/enlaces/duplicados, limita descarga y extracción a 2 GiB, extrae por streaming en staging y activa el directorio al terminar. Se vuelven a verificar los hashes individuales. No sobrescribe un paquete distinto: exige destino nuevo. Descarga fría aproximada: 356 MB; disco transitorio para archivo y contenido: unos 918 MB, aparte de dependencias. No almacena el archivo completo en RAM.

La configuración no contiene credenciales y no crea buckets, permisos, URLs ni subidas. Un montaje local de solo lectura también sirve si proporciona el árbol completo. Un proveedor distinto no requiere cambios de código, solo una URL HTTPS GET válida y estable.

### Primer despliegue: intervención mínima

1. **Aprobar y realizar** commit/push del código y configuración S28–S29. Los informes y datos siguen ignorados; revisar por separado qué evidencia se conserva en Git. Nada se ha publicado en esta sesión.
2. **Aprobar y subir únicamente** `madrid_rehab_v1_02.tar.gz` al almacenamiento elegido, con lectura HTTPS y sin escritura pública. Copiar su URL; conservar el SHA-256 anterior.
3. Crear app en Streamlit Community Cloud con repositorio/rama revisados, Python **3.13** y entrada **`src/madrid_rehab/app.py`**. Pegar `config/deployment_public.toml.example` en Advanced settings y **cambiar solo la URL** por la real. El SHA y la ruta de caché ya están preparados. Siempre PUBLIC=1; no activar PILOT/DEMO. No añadir overrides de snapshots históricos.
4. Esperar descarga/verificación y recorrer ES/EN, municipios, distrito, CEEE, menciones ITE, Plan, OR/AND, mapa/clic, ficha, regreso y buscador. Confirmar que PRTR y herramientas privadas siguen cerrados. Medir memoria con varias sesiones. No considerar health ni AppTest como prueba WebGL.

Si falta un archivo, cambia su hash, se intenta usar modo privado/piloto/demo o falla la entrega, la aplicación muestra un error genérico claro, sin trazas/rutas ni datos alternativos. Las cuatro condiciones de arranque fallido están comprobadas en `fail_closed.json`. No se arregla un despliegue fallido poniendo PUBLIC=0.

## E. Pruebas, decisión y límites

- **85 pruebas focalizadas satisfactorias**: paquete, S28, catálogo, filtros, ficha, direcciones, S19, i18n y navegación. Se añadió después una prueba de identidad de caché/entrega; las **8 pruebas finales del módulo nuevo** pasan (7 solapadas con las 85): **86 casos distintos comprobados**. No se repite la suite general de 566.
- Recorrido aislado completo y guard de datos: `smoke_optimized.json`; sin lecturas Parquet/SQLite externas, sin errores de recuperación en fichas y sin llamadas PRTR.
- Seis municipios, 21 distritos de Madrid, filtros CEEE/ITE acotado/Plan y PRTR deshabilitado, OR/AND, contadores, mapa serializado de máximo 500 geometrías, lista, fichas, vuelta con contexto, ES/EN, búsqueda y Acerca: correctos.
- Datos ausentes y modos incorrectos: fallo explícito y cerrado. Servidor y health reales correctos. Integridad, valores y reproducción byte a byte comprobados.
- **WebGL/navegador no validado en S29**: no se instaló Chromium. Tampoco se ha ejecutado Cloud ni una carga multiusuario. La revisión visual previa del usuario no se extrapola a ese despliegue.

**Decisión: NO LISTO PARA DESPLEGAR desde el repositorio publicado actual.** Está terminado el trabajo técnico local para el alcance autorizado. Los bloqueos de entrega son concretos: GitHub aún contiene el commit anterior y no existe una URL de datos materializada. Se pueden cerrar con las dos acciones de publicación/subida que el propietario reservó para aprobación. PRTR y padrones ITE/IEE no impiden esta primera versión porque se han excluido y su cobertura se declara. No se necesita ampliar fuentes ni repetir una auditoría general para realizar el primer despliegue.

Después de entregar código y archivo, la validación en Cloud/WebGL es el último control antes de abrir la app al público. Si la memoria real no basta, elegir alojamiento o ajustar cachés según la medición; no prometer recursos ilimitados ni volver a incluir fuentes pendientes.
