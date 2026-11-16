# Sesión 28 — Preparación de despliegue

Auditoría del 16/11/2026. Objetivo: 20/11/2026. **El arranque técnico se ha reproducido; la publicación sigue bloqueada por derechos y empaquetado.** No se ha desplegado, subido datos, hecho commit/push ni rehecho ETL. Las autorizaciones y membresías históricas permanecen intactas.

Estado inicial comprobado: `main`, `5311a5238f37dd645663ba9e5daa82c435485fb5`, árbol limpio; `origin/main` local apunta al mismo hash. No se hizo fetch: esto verifica la referencia remota conservada, no cambios remotos posteriores. Se acepta la revisión visual previa del propietario; no se presenta como prueba visual de esta versión en Cloud.

## Entrega verificable

Los resultados locales están en `reports/session_28_deployment/` (directorio ignorado por Git):

- `license_matrix.csv`, `sources.json`: estado por fuente, URL, condiciones y propuesta.
- `plan_zip_evidence.json`: hash, miembros, CRC, fechas y XML del ZIP local, leído sin extraer ni modificar originales.
- `inventory_final/files.csv`: **445 archivos**, rutas relativas, bytes, SHA-256, función, familia y revisión de licencia. `summary.json` y `groups.json` contienen agregados. Es una envolvente conservadora de ejecución, no un paquete autorizado ni una afirmación de mínimo matemático.
- `preflight_local.json`, `missing_data.json`: dependencia presente frente a checkout sin datos.
- `clean_smoke_release.json`, logs de instalación, `pip_check.txt`, `server_health.json`: instalación nueva y recorrido público.
- Logs de pruebas, Ruff, `path_network_scan.txt` y revisión heurística de columnas. Los informes iniciales se conservan para explicar los fallos encontrados; usar los resultados finales indicados aquí.

Código de auditoría mantenido: `deployment.py`, `tests/audit_deployment.py`, `tests/smoke_deployment.py`. Los CSV de inventario se enriquecieron con la matriz de fuentes; sus hashes corresponden a los archivos de datos, no a los CSV.

## Licencias: decisión por recurso

No se equipara que un fichero sea accesible con que pueda redistribuirse. La siguiente matriz distingue el recurso oficial de la copia local. No se ha activado ninguna fuente pendiente.

| Fuente | Estado | Evidencia y acción pendiente |
| --- | --- | --- |
| Catastro INSPIRE, producto transformado CP/BU/AD | **Reutilización condicionada** | [Licencia específica 1.0](https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf), enlazada desde [INSPIRE](https://www.catastro.hacienda.gob.es/webinspire/). Documentar la transformación del producto y su carácter no oficial; conservar el significado. |
| Catastro original sin transformación | **Uso público no permitido** | La licencia excluye distribuir el original sin transformación. No subir ZIP/GML originales; cambiar de formato por sí solo no acredita una obra distinta. |
| CEEE Comunidad de Madrid | **Reutilización acreditada** | La [ficha específica](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica) enlaza CC BY 4.0 y recursos anuales. Conservar Comunidad de Madrid, título, URL, licencia, fecha disponible y cambios. No convertir certificados individuales en calificación del edificio. |
| Órdenes de conservación 300377 | **Reutilización acreditada** | La [ficha específica](https://datos.madrid.es/dataset/300377-0-conservacion-rehabilitacion) declara CC BY 4.0. Atribuir al Ayuntamiento, enlazar licencia y distinguir transformación/corte. |
| PDF de obligaciones ITE/IEE; REC | **Reutilización no acreditada** | El [servicio de informes](https://servpub.madrid.es/GITEP_WBINFORME/SGiteInforme) no acredita la reutilización de los PDF concretos. REC no está integrado. La partición mixta de conservación no hereda la licencia de las órdenes. |
| Callejero actual 213605 | **Reutilización acreditada** | [Ficha CC BY 4.0](https://datos.madrid.es/dataset/213605-0-callejero-oficial-madrid). No extender a otra versión o al puente histórico. |
| Puente histórico 200075 y límites IDEM | **Reutilización no acreditada en esta revisión** | Falta cerrar términos y versión de ambos productos concretos. Son dependencias auxiliares, también requieren revisión. |
| Plan Rehabilita oficial | **Reutilización condicionada** | La [ficha Geoportal específica](https://geoportal.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=00000009-b145-11ea-a01e-ecb1d753f6e8) enlaza la descarga y remite expresamente a condiciones municipales. Hay base documental para una propuesta. |
| ZIP Plan Rehabilita local exacto | **Reutilización no acreditada todavía** | Correspondencia documental fuerte por nombre/formato/linaje; no hay prueba independiente de identidad de bytes con el recurso oficial. Mantener cerrado hasta vincular el hash con su origen. |
| PRTR, API del visor alojado en COAM | **Reutilización no acreditada** | [Visor](https://visorrehabilitaprtrmadrid.coam.org/), raíz 403 durante revisión; no se encontró licencia específica del recurso conservado. La [política regional general](https://www.comunidad.madrid/datos-abiertos/reutiliza-datos-abiertos-comunidad-madrid) no demuestra cobertura de esa API. |

Las [condiciones municipales](https://datos.madrid.es/pages/condiciones-generales-ayuntamiento-de-madrid) exigen fuente, fecha cuando figure, metadatos y ausencia de respaldo institucional implícito. El [portal](https://datos.madrid.es/pages/condiciones-de-uso) ofrece condiciones generales y CC BY; la ficha concreta decide qué referencia resulta aplicable. La matriz no constituye permiso nuevo del proyecto.

### Procedencia del ZIP Plan Rehabilita

Original: `/mnt/c/Users/apalo/Downloads/PLAN_REHABILITA.zip`, **712.277 bytes**, SHA-256 `5c9ba32bb5871e5c0af2f7b15148373a694d635c8ca633a7e7d05e4bcaedd66b`. Existe copia preservada bajo `data/raw/plan_rehabilita/<SHA-256>/PLAN_REHABILITA.zip`.

Los XML ESRI documentan procesamiento de 19/10/2026 y rutas de ArcGIS; no contienen una licencia. Las fechas ZIP son fechas internas, no prueba de adquisición. El Geoportal identifica al Ayuntamiento y enlaza [esta descarga concreta](https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/VIVIENDA/PLAN_REHABILITA_MADRID/DESCARGA_TOTAL/SHP_ZIP/PLAN_REHABILITA.zip). Su fecha de creación de catálogo de 2022 no es la actualización del ZIP local.

**Propuesta para resolver el bloqueo:** registrar esa ficha y condiciones junto al hash preservado; aportar el registro de descarga del propietario o confirmación del productor que vincule el archivo/corte; incorporar atribución municipal y fecha acreditada al nuevo manifiesto autorizado. Después presentar el cambio de política para decisión del propietario. No se ha descargado otra versión ni sustituido el snapshot. No se propone habilitar Plan Rehabilita automáticamente por coincidencia de nombre.

## Inventario y cadena real de lectura

`app.py` importa el paquete y dirige a `city_app.main`; `navigation.main_view` admite las tres rutas públicas. Explorador: `commercial_catalog_view` → `commercial_catalog_store` → `commercial_explorer`, filtros y geografía. Ficha: `municipal_fiche` → `cadastral_identity`, `enriched_cadastre`, `commercial_data`, lectores energéticos/conservación y suplemento S22. Buscador: `address_view` autentica S20, consulta el catálogo comercial y abre la misma ficha. Acerca usa texto de código. Se instala el paquete completo `src/madrid_rehab`, incluidos módulos históricos importados; no es necesario servir sus datos si sus rutas están cerradas.

| Conjunto/ruta bajo `data/processed/` | Archivos del inventario | Bytes | Necesidad actual y sustitución |
| --- | ---: | ---: | --- |
| `commercial_catalog/session_24_public_02/` | 8 | 288.548.226 | SQL de identidad/postal y Parquet comerciales. Imprescindible. No sustituir por S24 local ni cambiar umbral. |
| `addresses/session_20_01/` | 2 | 197.280.374 | Validación S20 y búsqueda. Imprescindible actualmente incluso con catálogo postal duplicado. Futuro manifiesto autónomo podría evitar duplicación. |
| Catastro/territorio, S2/S7, parcial S12.2, enriquecido S18 y suplemento S22 | 110 | 465.205.750 | Geometrías originales, relaciones CP/BU, atributos y manifiestos. Imprescindibles para las fichas/navegación conservadas; seleccionar columnas exigiría producto/manifiesto nuevo. |
| `conservation/session_14_final_02/` | 305 | 148.092.794 | Filtros, accesos, particiones por CP y autenticación postal. Mixto, revisión pendiente. |
| `energy/session_13_final_03/` | 16 | 140.571.838 | Particiones de seis municipios y fuentes globales exigidas por hashes del catálogo. Procesado menor posible tras contrato independiente. |
| PRTR: maestro y enlaces parciales | 2 | 2.329.786 | Consulta pública prohibida; **el arranque aún exige sus bytes por autenticación**. No basta con quitarlos del servidor. |
| `plan_rehabilita/session_23_01/` | 2 | 152.356 | Manifiesto y `locations.parquet`, exigidos por autenticación. Consulta pública cerrada. |
| **Total conservador** | **445** | **1.242.181.124** | **1,157 GiB**, sin ZIP/GML ni replays históricos. |

El catálogo por sí solo exige **88 archivos / 943.022.677 bytes**. `commercial_catalog_store.signature/_verify` recorre sus 80 entradas y siete salidas. S20 añade dependencias administrativas y de conservación: suprimir originales de ETL no basta para independizar lectores. Los originales grandes de Windows no son necesarios para servir las funciones comprobadas. No hay dependencia de Windows en el paquete simulado.

**Todo `data/` está ignorado y hay cero archivos `data/` versionados.** Un checkout nuevo no dispone de datos. `reports/` también está ignorado. No se cambia `.gitignore` para incorporar datasets. El inventario conserva rutas relativas porque los contratos las autentican; los overrides incompatibles se rechazan deliberadamente.

La búsqueda de rutas/red se conserva en `path_network_scan.txt`: las rutas WSL/Windows de ingesta y prototipos no se ejecutan desde las tres rutas públicas probadas. No se necesita `pdftotext`, GML, ZIP, REC, cliente catastral ni adquisición en producción. Se mantienen enlaces de consulta voluntaria. `MADRID_REHAB_OFFLINE=1` evita el mapa base externo en las vistas que lo admiten; cualquier mapa base activado exige conectividad y atribución OpenStreetMap. No hay credenciales.

## Estrategia de empaquetado y almacenamiento

**No existe todavía un paquete de datos íntegramente autorizado.** La copia de `/tmp` es una simulación privada con productos existentes, no una entrega redistribuible. Ocultar importes no elimina del catálogo su selección o procedencia PRTR/Rehabilita. Tampoco autoriza subir sus archivos de autenticación.

Propuesta mínima de producción: código/configuración en Git; un producto de ejecución inmutable con solo seis municipios, referencias/relaciones explícitas, geometrías exactas, índices postales, atributos necesarios, ámbitos, fechas, hashes y atribuciones. Excluir ZIP/GML originales, cuarentenas, evidencias sin autorización, prototipo S23, replays y expedientes no necesarios. Mantener expedientes como entidades únicas y nunca sumar importes por enlaces. No se ha generado ese derivado porque supondría nuevos contratos/datos y requiere cerrar las autorizaciones. No se presume que convertir GML a Parquet resuelva la condición de transformación de Catastro.

| Opción | Datos reales | Complejidad y decisión |
| --- | --- | --- |
| A. Repositorio | Conjunto actual 1,24 GB. `addresses.sqlite`: 197.275.648 bytes; `catalogue.sqlite`: 226.926.592 bytes. | Ambos superan 100 MiB: no usar Git ordinario para ellos. Un repositorio público expondría todos sus bytes, aunque la interfaz los oculte. Git LFS es [compatible con Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization), pero exige revisión de cuotas/licencias y aprobación de subida. Solo recomendar Git para código y manifiestos pequeños autorizados. |
| B. Almacenamiento externo de lectura | Mismo conjunto de 1,24 GB hoy; el arranque valida unos 943 MB. | Preferible por volumen/versionado. Descarga única a caché local, SHA-256 antes de apertura, escritura atómica y fallo explícito si falta algo; mantener árbol relativo. SQLite necesita archivo local, no URL. Requiere decidir proveedor, coste, disponibilidad, licencia y entrega. No hay descargador de producción implementado ni subida realizada. |

Almacenamiento externo no reduce por sí solo la RAM ni sustituye permisos. No dividir índices o cambiar manifiestos solo para eludir límites. Los tamaños del futuro paquete autorizado son desconocidos hasta definir su contenido; no se promete una reducción inventada.

## Configuración preparada para Community Cloud

Se han contrastado [dependencias](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [rutas](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization), [secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) y [recursos](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) oficiales.

- Punto de entrada: `src/madrid_rehab/app.py`; directorio de trabajo: raíz del checkout, como ejecuta Cloud.
- Python: **3.13**, probado localmente en 3.13.5. Seleccionarlo expresamente en Advanced settings; no depender de la versión predeterminada futura.
- `requirements.txt` reconocido por Cloud incluye el cierre transitivo `requirements-production.lock` y `-e .`. Esto instala `madrid_rehab` desde `src` sin depender de `PYTHONPATH`. El lock de desarrollo original no cambia; Ruff queda fuera del runtime.
- Sin `packages.txt`: servir los productos no requiere herramientas de extracción. Sin build frontend adicional.
- `.streamlit/config.toml`: headless, sin dirección/puerto WSL, watcher desactivado, telemetría desactivada, detalles de excepciones ocultos al cliente y logger warning. Se preservan errores explícitos de datos; ocultar traceback no declara éxito.
- `.streamlit/secrets.toml.example`: configuración sin credenciales para pegar en Advanced settings. El archivo real se ignora. Valores raíz: `MADRID_REHAB_PUBLIC="1"`, `MADRID_REHAB_OFFLINE="1"`, `MADRID_REHAB_DEV="0"`, `MADRID_REHAB_DEMO="0"`, `MADRID_REHAB_PILOT="0"`. No fijar PUBLIC a cero. No introducir rutas de `/home` o `/mnt/c` ni overrides incompatibles.
- Cloud sigue necesitando que el paquete de datos aprobado esté físicamente disponible. La variable PUBLIC no autoriza la publicación ni materializa archivos.
- Consultas geométricas limitadas a 500 objetos; selección por identidad, índices y cachés existentes. Las cachés verifican firmas/hash; no se reconstruye ETL. La memoria de cachés crece con municipios/fichas usados; no hay prueba de carga concurrente.
- Logs del servidor son para el propietario: pueden contener rutas/identificadores ante errores de integridad. No compartir logs completos públicamente. La UI pública ya no expone el detalle bruto de errores iniciales de catálogo/índice.

Detección offline, sin modificar datos:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.deployment --output reports/session_28_deployment/preflight_nuevo.json
```

Salida 2: faltan dependencias de arranque; salida 0: están presentes. **No valida licencias, hashes ni todas las fichas**; los lectores conservan su propia autenticación y el smoke recorre las funciones. El informe no autoriza publicación. Usar siempre ruta nueva.

## Cambios mínimos y pruebas

Problemas corregidos:

1. Declaración de instalación Cloud e importaciones `src`, configuración portable y ejemplo de variables sin secretos.
2. **Fuga de consulta PRTR en Detalles técnicos:** el resumen estaba protegido, pero `municipal_fiche.render_prtr` recuperaba datos con `public_catalog=True`. Ahora se cierra antes de llamar al lector en público; prueba de regresión. No se abre ninguna fuente.
3. `_parcel_index` usaba el contexto de transacción SQLite sin cerrar conexión. Ahora usa `closing`; prueba de cierre explícito. No cambian filas ni reglas.
4. Errores de arranque siguen visibles, con detalle técnico solo en privado. Preflight reproducible y pruebas de datos ausentes.

La instalación se realizó en un venv nuevo bajo `/tmp`, con dependencias declaradas, código/datos copiados a `/tmp/madrid-rehab-s28-clean`, HOME vacío temporal y `env -i`, sin PYTHONPATH ni caché Streamlit persistente. El intérprete base del venv es el Python 3.13.5 del host; no es una imagen Linux independiente ni una ejecución en la infraestructura Cloud. Un intento auxiliar con `--no-build-isolation` falló por ausencia de setuptools; la instalación normal con aislamiento funcionó. `pip check`: correcto.

| Comprobación | Resultado |
| --- | --- |
| Checkout sin datos | Catálogo y buscador informan ausencia, sin excepción no controlada; Acerca sigue disponible. |
| Arranque con copia declarada | Correcto; ES predeterminado, EN seleccionable. |
| Seis municipios y distrito Madrid | Correcto; conteo inicial Madrid 114.706 CP, distrito/filtro conservados. |
| Filtros, mapa/lista y ficha | Correcto en AppTest; un mapa serializado, diez botones de lista, fichas Madrid y cinco pilotos. |
| Buscador Madrid | Bailén 12 devuelve selección expresa y abre ficha de CP. |
| Fuentes restringidas | Filtros PRTR/Rehabilita deshabilitados; llamadas de recuperación de ficha interceptadas con fallo si se usan; recorrido final sin llamadas. Autenticación de archivos restringidos sigue siendo dependencia separada. |
| Servidor real local | Arranca en 127.0.0.1:8528; `/_stcore/health` responde `ok`; detenido al terminar. Health no ejecuta una sesión de navegador. |
| Navegador/WebGL Cloud | **Pendiente/bloqueado en esta sesión:** Chromium no disponible; no se descargó. AppTest no es validación visual. |
| Pruebas automatizadas | 5 nuevas + 5 filtros + 10 i18n + 6 navegación: **26 satisfactorias**. Ruff y diff check correctos. No se repite la suite general de 566. |

Comandos reproducibles:

```bash
python3.13 -m venv /tmp/madrid-rehab-cloud-venv
/tmp/madrid-rehab-cloud-venv/bin/python -m pip install -r requirements.txt
/tmp/madrid-rehab-cloud-venv/bin/python -m pip check
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_deployment.py -v
PYTHONPATH=src .venv/bin/python tests/audit_deployment.py --output-dir reports/session_28_deployment/inventory_nuevo
MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 /tmp/madrid-rehab-cloud-venv/bin/python tests/smoke_deployment.py --output reports/session_28_deployment/smoke_nuevo.json
.venv/bin/ruff check src tests
git diff --check
```

Ejecutar desde la raíz y con datos revisados disponibles. Para reproducir aislamiento, copiar **sin symlinks** código/configuración y los archivos del inventario a otra raíz; instalar `-e .` allí y ejecutar con HOME temporal/entorno limpio. No copiar `.aws`, `.codex`, `.agents`, secretos o originales. No ejecutar ETL como remedio automático a datos ausentes.

### Tamaño, memoria y viabilidad

La primera prueba limpia midió 679 MiB de RSS máximo en arranque y 900 MiB después del recorrido; el recorrido final tras los últimos cambios alcanzó **941 MiB**. Son procesos AppTest de una sesión con cachés compartidas, no memoria garantizada del servidor ni una medición multiusuario. El tiempo local final fue aproximadamente 14,5 s para todo el recorrido; no es SLA.

La documentación de Cloud publica límites aproximados de febrero de 2024 (revisables): memoria 690 MB mínimo/2,7 GB máximo, disco hasta 50 GB y CPU variable. El conjunto cabe en ese máximo de disco; **la memoria observada supera el mínimo anunciado y no acredita compatibilidad estable**. Hace falta medir con la asignación real y varias sesiones. No se presupone un límite fijo de 1 GB ni disponibilidad garantizada del máximo. Diagnóstico: candidato técnicamente viable para prueba controlada en Cloud tras cerrar permisos/entrega, aún no listo para publicación abierta.

## Decisión y primer despliegue

| Prioridad | Bloqueo | Resolución concreta |
| --- | --- | --- |
| **CRÍTICO** | PRTR sin licencia y dependencia en selección/autenticación | Obtener permiso del recurso concreto o autorizar un derivado revisado que elimine sus dependencias sin alterar silenciosamente membresía. No basta con mantener el filtro gris. |
| **CRÍTICO** | Copia exacta Plan Rehabilita, PDF ITE/IEE y auxiliares pendientes | Resolver origen/términos según matriz; el ZIP tiene ahora una propuesta documental concreta. |
| **CRÍTICO** | Producto Catastro/paquete público no formalizado | Acreditar transformación, atribución y contenido distribuible; revisar bytes/campos y nuevo manifiesto. No subir los productos actuales sin revisión. |
| **CRÍTICO** | Datos ausentes de Git y entrega no elegida | Aprobar paquete autorizado y opción LFS o almacenamiento de lectura; materializarlo en Cloud. No se ha subido nada. |
| **IMPORTANTE** | Memoria y concurrencia sin prueba en Cloud | Probar asignación real; medir RSS, sesiones y cachés. Si no cabe, reducir producto/cachés de forma revisada o elegir otro alojamiento. |
| **IMPORTANTE** | WebGL/navegador del despliegue no probado | Revisar en URL de prueba municipio, mapa/clic, ficha, ES/EN y móviles antes de apertura. |
| **POSTERIOR** | Duplicación S20/S24 y dependencias históricas | Contrato de ejecución autónomo y compacto cuando se autorice; no necesario para demostrar el arranque actual. |

Secuencia para llegar al primer despliegue:

1. Cerrar decisiones críticas de la matriz y aprobar alcance/almacenamiento. Registrar autorizaciones con hash, fuente y atribución. Este informe **no solicita desactivar los controles actuales**.
2. Preparar el producto autorizado y verificar sus hashes/relaciones. Si cambia la selección, revisar denominadores y manifestar el cambio; no sustituir el snapshot histórico.
3. Aprobar por separado commit/push de código/configuración y, cuando corresponda, entrega de datos. No se ha realizado en esta sesión. Los informes ignorados se entregan por separado o se versiona solo evidencia revisada.
4. En Community Cloud, elegir repositorio/rama revisados y `src/madrid_rehab/app.py`. Advanced settings: Python 3.13 y valores del ejemplo, con PUBLIC=1. Materializar datos autorizados antes de aceptar el arranque.
5. Comprobar instalación, preflight y sesión real; comparar contadores con el paquete aprobado, no asumir 153.929 si cambia su alcance. Recorrer las doce comprobaciones solicitadas en navegador y medir recursos reales. Mantener advertencias/restricciones hasta resolverlas documentalmente.
6. Solo tras aprobación final, abrir la URL al público. Si faltan datos o hay OOM, corregir el paquete/carga/alojamiento; no cambiar PUBLIC a cero ni ocultar el error.

La fecha 20/11 es alcanzable solo si se resuelven los críticos y la prueba real de alojamiento. La siguiente decisión útil es el alcance autorizado y cómo entregar sus datos; no ampliar fuentes ni funcionalidades.
