# Sesión 12.2 — piloto catastral real y contingencia de descarga

Corte: 24/10/2026. **El sandbox sigue sin resolver el host oficial de Catastro. No se ha incorporado cartografía externa real.** La conectividad de Ubuntu comunicada por el usuario no se extrapola a este proceso. Se conservan los productos de Madrid y las decisiones territoriales de sesión 12.1. No hay commits, push, publicación ni dependencias nuevas.

## Resultado real

| Municipio | INE | Código Catastro leído del feed | CP cargadas | BU cargados | PRTR | Vinculados CP | Pendientes CP | Concesión PRTR |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Getafe | 28065 | 28065 | 0 | 0 | 165 | 0 | 165 | 6.504.414,98 € |
| Móstoles | 28092 | 28092 | 0 | 0 | 327 | 0 | 327 | 19.194.235,90 € |
| Leganés | 28074 | 28074 | 0 | 0 | 234 | 0 | 234 | 9.562.241,86 € |
| Alcorcón | 28007 | 28007 | 0 | 0 | 290 | 0 | 290 | 27.596.650,56 € |
| Alcalá de Henares | 28005 | 28005 | 0 | 0 | 229 | 0 | 229 | 13.234.398,51 € |
| Total piloto | | | 0 | 0 | 1.245 | 0 | 1.245 | 76.091.941,81 € |

«0 cargados» expresa ausencia de incorporación, **no ausencia de parcelas u objetos en el municipio**. No se pueden medir incidencias o ambigüedades de CP/BU real. Hay cero relaciones ambiguas nuevas registradas porque el cruce externo no ha podido evaluarse: no se afirma que los datos futuros carezcan de ellas.

Previstos: cinco municipios, diez recursos. Descargados y verificados: cero. Municipios externos con CP/BU integrado: cero. Cobertura total CP/BU de la plataforma: **Madrid capital, un municipio**, igual que antes. Madrid mantiene 141.244 filas CP de origen (140.595 referencias distintas auditadas), 124.396 objetos BU, CEEE, conservación y 21 distritos. Una fila CP o un objeto BU no equivale a edificio físico, vivienda o portal.

PRTR regional permanece en **7.532 expedientes y 315.527.338,99 €**: 3.808 geográficamente en Madrid y 3.724 externos. Las 3.805 confirmaciones CP históricas permanecen; clasificar tres expedientes adicionales en Madrid no resuelve sus vínculos CP pendientes. La decisión municipal de sesión 12.1 se copia **byte a byte**, sin ejecutar otra clasificación territorial.

## Auditoría inicial y fuentes reutilizadas

Se leyeron AGENTS, README, arquitectura, sesiones 11/12/12.1, los importadores regionales y manifests. Git contenía modificaciones y archivos sin seguimiento de sesiones anteriores: se preservaron. La línea base completa pasó **311 pruebas en 216,339 s antes de modificar código**. `reports/session_12_2/initial_state.json` registra Git y hashes de 416 archivos originales/productos; la auditoría final no encuentra cambios en ellos.

Se reutilizan el inventario `data/processed/territory/session_12_final_01/cadastre_resources.parquet`, ambos ATOM originales, los límites normalizados `territory/session_12_1_final_01`, PRTR original/procesado de sesión 11 y la clasificación `grants/regional/session_12_1_final_02`. No se reconstruye el inventario ni se descarga PRTR.

El manifiesto mantenido [config/cadastre_pilot_12_2.json](../config/cadastre_pilot_12_2.json) enumera los diez recursos con:

- Nombre oficial IDEM, INE y `source_fids` del catálogo territorial.
- Código Catastro, título literal completo y `id` exacto de cada entrada ATOM CP/BU.
- URL de ZIP exacta, URL del feed y SHA-256 del feed/inventario/catálogo utilizado.
- Actualización publicada: `2026-08-21T00:00:00Z` para estos diez recursos, comprobada individualmente.
- Derechos literales: uso gratuito con mención de la Dirección General del Catastro, Ministerio de Hacienda, como autor y propietario. No se traslada este permiso a PRTR.
- Tamaño esperado: `null`, porque las entradas no declaran `length`. No se inventa un tamaño ni un checksum oficial.

La correspondencia se revisa **solo para los cinco nombres completos únicos** del catálogo oficial y de ambas entradas ATOM; los códigos se leen separadamente de esas fuentes. La igualdad numérica observada no es la regla de correspondencia. Madrid continúa con INE 28079 / Catastro 28900. No se extiende esta revisión a las otras correspondencias pendientes de sesión 12.1 ni se usan recuadros ATOM como límites.

## Descargas: evidencia y comando único de contingencia

Se realizaron diez HEAD acotados, dos conexiones simultáneas y timeout 12 s: todos fallaron por DNS. Después, el descargador definitivo intentó los diez GET, un intento por recurso, timeout 12 s: todos devolvieron `Temporary failure in name resolution`. **No hay ZIP ni GML real descargado**, ni bytes/hash de un archivo inexistente. Se detuvieron los reintentos DNS; no se insistió indefinidamente.

Evidencia: `reports/session_12_2/network_probe.json`, `download_sandbox_01/downloads.json` y su manifiesto. Los directorios de captura vacíos y `pilot_manifest.json` no se contabilizan como archivos catastrales.

Desde la raíz del proyecto, **Ubuntu puede ejecutar un solo comando para descargar, validar, integrar y cruzar los cinco pilotos**:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_pilot
```

No requiere descargar diez archivos manualmente. Por defecto conserva los ZIP en `data/raw/cadastre/session_12_2_capture_01/`, particiones en `data/processed/cadastre/session_12_2_pilot_01/<INE>/` y genera un snapshot regional nuevo `data/processed/grants/regional/session_12_2_run_<fecha>_<id>/`. Cada ejecución crea un informe de descarga distinto bajo `reports/session_12_2/download_<fecha>_<id>/`. Devuelve código **0 solo si se integran los cinco municipios**, y **2 si queda cobertura pendiente**. El código 2 de esta sesión es el resultado esperado por bloqueo, no éxito de descarga.

El mismo comando permite reanudar: verifica y reutiliza archivos completos; procesa particiones con la misma configuración/límite y publica un snapshot regional nuevo. Si se integra al menos un municipio, escribe atómicamente `active_prtr.json` en el directorio catastral. El visor comprueba su hash y selecciona ese producto sin cambiar el snapshot histórico. Un intento sin incorporaciones no cambia la captura activa. No es necesario pedir revisión visual para ejecutar el pipeline.

Si se prefiere **solo descargar** (este módulo usa únicamente biblioteca estándar):

```bash
PYTHONPATH=src python3 -m madrid_rehab.cadastre_download
```

El descargador tiene dos intentos por defecto, máximo tres, timeout de socket 20 s y presupuesto de 120 s por intento de transferencia; espera progresiva 1/2 s ante errores transitorios. DNS y 404 no se reintentan. Un 429 queda pendiente para otra ejecución, sin ignorar una espera impuesta por el proveedor. Solo se admiten HTTPS y el host oficial también en redirecciones. Las URLs con espacios se codifican para transporte, conservando la URL literal del feed en el informe.

Límites: 160 MiB por ZIP y 2 GiB expandidos por ZIP. Diez recursos fijos, secuenciales; no hay expansión masiva regional. Un archivo demasiado grande queda bloqueado para revisión; no se amplía el presupuesto automáticamente.

La descarga usa `.part`, comprueba Content-Length si consta, tamaño declarado en feed si consta, ZIP, CRC de todos los miembros, XML completo de GML/XML, DTD/entidades prohibidas y ausencia de HTML/excepciones OGC. No extrae rutas del ZIP al sistema de archivos. Los metadatos de cada ZIP válido incluyen URL efectiva de petición, captura UTC, cabeceras, tamaño real, SHA-256 y resultado de integridad. Es hash local de integridad, no checksum publicado por el proveedor.

Un parcial interrumpido se aparta con sufijo `.interrupted-*`; nunca se interpreta como ZIP válido ni se reanuda por Range. Una caché con ZIP/metadatos incompletos o hash alterado se conserva y se rechaza: usar otra captura, sin sobrescribir el original. Reanudar significa reutilizar archivos completos verificados. Para actualizar el feed o corregir una captura alterada se requieren rutas nuevas.

## Ingesta preparada y controles

`regional_cadastre.process_municipality` conserva su modo estricto histórico. El piloto activa **opcionalmente** el modo auditado, reutilizando archivador, parser CP, normalización de referencias, geometría GML, relaciones CP/BU y publicación atómica. No cambia la ingesta de Madrid.

El modo auditado conserva todas las filas parseadas y referencias originales. Mantiene IDs de origen y `source_row`, geometrías multiparte, tipo de entidad, CRS y procedencia. Señala IDs nulos/repetidos, referencias no admitidas, geometrías inválidas/vacías/no poligonales, CRS/posición incompatibles y fracción de área dentro del municipio. No repara ni elimina silenciosamente geometrías.

Solo se usa en cruces y mapas una geometría válida, con identidad utilizable y totalmente interior al recinto (tolerancia relativa numérica 1e-8). Un cruce real de frontera queda `crosses_boundary`, sin forzar el municipio geográfico de ese objeto. `source_municipality_code` conserva siempre el municipio al que corresponde el recurso descargado; `municipality_code` queda vacío cuando no se acredita la asignación. Las incidencias permanecen en las tablas y en `cp_issues.parquet` / `bu_issues.parquet`.

`pilot_objects.building_rows` lee los GML Building y BuildingPart, incluyendo partes anidadas, conservando ID individual y padre explícito cuando existe. No hereda una referencia CP de un padre como si la parte la declarase. No toma atributos del descendiente para rellenar los ausentes del padre. Conserva los atributos constructivos del adaptador existente solo cuando están presentes. Otras capas del ZIP se conservan en el original y se verifican en integridad; no se convierten en Building ni en parcelas. Un cambio de esquema/recuento no reconocido bloquea la ingesta y conserva el original para revisión.

Las relaciones CP/BU registran referencia exacta, multiplicidad y distancia; los objetos sin referencia, ambiguos, no utilizables o con contradicción geométrica permanecen explícitos. Una referencia CP repetida sigue siendo ambigua aunque una de sus filas no sea utilizable: no se limpia la ambigüedad eliminando el caso problemático.

Cada partición final incluye `cp.parquet`, `bu.parquet`, `cp_bu_links.parquet`, tablas de incidencias y manifiesto con hashes, límites, configuración, calidad, recuentos cargados/utilizables, tipos BU, tiempo y RSS. `validation_status=validated` acredita el contrato/integridad de la partición; `quality_status=review_required` puede coexistir con incidencias conservadas y filas no utilizables. No se debe interpretar como validación de cada objeto.

**Estas rutas de ingesta están probadas con fixtures, pero su comportamiento sobre los cinco conjuntos reales sigue pendiente.** No se presenta un benchmark ni una precisión catastral real sin captura.

## Cruce PRTR/CP preparado

Se usa la decisión geográfica congelada de sesión 12.1, comprobando sus hashes. El cruce selecciona el CP de ese municipio y comprueba su partición. Una incoherencia de municipio entre hechos, partición y argumento se rechaza.

- A: referencia documental normalizada exacta, una sola fila CP utilizable y municipio coherente, sin punto fiable disponible para contraste; estado `confirmed_reference`, sin atribuir evidencia espacial.
- B: misma referencia exacta y contraste geométrico adicional. Se mantiene el umbral operativo heredado de ≤100 m para la distancia del punto a la parcela; se conserva la distancia, no se afirma precisión legal ni identidad de edificio.
- C: punto situado sobre una posible parcela, sin confirmación por referencia. Se guarda aparte como `spatial_candidate` o `ambiguous_spatial`; nunca se transforma automáticamente en confirmación documental.
- D: referencia ambigua, geometría/identidad no utilizable o coordenadas contradictorias; sin vínculo confirmado. «Referencia no encontrada» y «sin cartografía disponible» son estados distintos.

Los candidatos espaciales se limitan a 20 filas por expediente e informan el número real y si se truncó su presentación. Un expediente sin vínculo permanece en hechos/resúmenes. Los importes se calculan solo por expediente y se reconcilian por programa; ninguna relación o candidato lleva importe. Un caso con varias parcelas verificadas conserva varias relaciones, pero una sola concesión.

En esta sesión **no se han obtenido vínculos CP externos nuevos**. Los 1.245 expedientes y 76.091.941,81 € del piloto siguen pendientes de ese contraste. La copia regional local conserva la totalidad de los 7.532 expedientes, relaciones históricas y resúmenes contables; no sustituye por defecto al producto activo cuando no hay incorporaciones.

## Visor y carga selectiva

La navegación sigue siendo regional, con selección INE y filtros PRTR ya existentes. Por defecto busca particiones del piloto en `session_12_2_pilot_01`; `MADRID_REHAB_CADASTRE_DIR` permite otra raíz. Solo habilita cartografía que existe y pasa su contrato de integridad. Los municipios sin datos mantienen el mensaje «CP/BU sin procesar»; no se dibuja cartografía ficticia.

La selección carga un índice de RC sin geometrías; el mapa consulta por ventana/zoom y limita a 1.500 parcelas. Las fichas consultan CP/BU de la referencia mediante filtros Parquet. Las geometrías no utilizables permanecen en incidencias y se excluyen del mapa/cruce. La ficha diferencia referencias y geometría concordantes, referencias sin contraste espacial, candidatos por punto y ambigüedades; puede mostrar los expedientes permitidos asociados. Se advierte que los importes por expediente no deben sumarse entre fichas.

La cobertura visual y el contador CP/BU reconocen particiones realmente integradas, en lugar de afirmar siempre que solo existe Madrid. CEEE sigue siendo cobertura histórica de Madrid. Al volver a un municipio se mantienen los mecanismos anteriores de contexto/limpieza de selección; no hay rediseño de modos.

La asignación CP actual se carga separada de la decisión territorial histórica, evitando modificar sus columnas para actualizar el filtro. `MADRID_REHAB_PUBLIC=1` mantiene PRTR deshabilitado en vista municipal y fichas: no se cargan ni se muestran enlaces, candidatos o exportaciones PRTR. La licencia PRTR continúa sin verificar.

**Revisión visual conjunta pendiente**, según el alcance solicitado. Se han ejecutado pruebas técnicas AppTest; no se ofrecen capturas ni validación de clic/renderizado en navegador real, ni se solicita revisión al usuario ahora.

## Productos y reproducción

Fuente/plan mantenido: `config/cadastre_pilot_12_2.json`.

Informe real de descarga: `reports/session_12_2/download_sandbox_01/`.

Snapshot de contabilidad/cobertura sin CP nuevo: `data/processed/grants/regional/session_12_2_final_01/`. Conserva decisiones municipales, relaciones sin importes, candidatos vacíos, estado CP por expediente, resumen del piloto, productos municipales y resúmenes por programa. Los procesamientos intermedios propios `session_12_2_pilot_01/02` se conservan.

Auditoría: `reports/session_12_2/audit_final_02/`: `municipality_summary.csv`, `download_report.json`, `resource_integrity.json`, `cp_bu_quality.json`, `prtr_cp_quality.json`, `quality.json` y manifiesto de hashes. Los informes de calidad sin datos reales lo dicen expresamente.

Reproducción sin red de la situación actual (cada salida regional/de informe debe ser nueva):

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cadastre_pilot --offline \
  --regional-output data/processed/grants/regional/session_12_2_replay_new
# Código 2 si siguen ausentes los archivos: consultar el resumen, no interpretarlo como éxito.
PYTHONPATH=src .venv/bin/python -m madrid_rehab.pilot_audit \
  --regional-dir data/processed/grants/regional/session_12_2_replay_new \
  --download-report reports/session_12_2/download_sandbox_01 \
  --output-dir reports/session_12_2/replay_new
```

Después de un procesamiento Ubuntu con datos reales, usar en la auditoría el directorio regional y el informe de descarga que haya impreso el comando. Si se eligieron otras rutas, pasar además `--cadastre-dir` y `--raw-dir`. El visor acepta `MADRID_REHAB_REGIONAL_GRANTS_DIR` para revisar un snapshot concreto; sin override usa el puntero verificado del piloto si existe, o sesión 12.1 si no hubo incorporaciones.

Instalación, si ya no existe el entorno: `.venv/bin/python -m pip install -r requirements.lock`. No se añade manifiesto de dependencias nuevo porque no cambia el toolchain. No hay build adicional.

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_cadastre_pilot.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
```

## Validación y limitaciones

Pruebas nuevas: resolución de diez entradas oficiales, caché/hashes, ZIP/HTML/XML truncado, DTD, parciales, reintentos/DNS, parsing de BuildingPart, multipartes, geometría/identidad conflictiva conservada, fronteras, CP/BU, referencias ambiguas incluso con filas no utilizables, coincidencia documental y candidata, varias parcelas sin multiplicar importes, coherencia municipal y replay. Un ensayo integral con ZIP **sintéticos exclusivamente en un directorio temporal del test** comprueba la publicación/cruce de un piloto y la conservación binaria de decisiones reales; no valida cartografía catastral real.

La prueba de integridad de los diez recursos reales está **omitida con motivo explícito** mientras no existan todos. La suite completa incluye las regresiones de los 21 distritos, snapshots originales y modo público. Cierre: **333 pruebas ejecutadas: 332 superadas y una omitida por falta de los diez recursos reales; 194,183 s. Ruff correcto y ocho archivos con formato verificado.** Tras el ajuste de presentación de URLs y salida CLI, las 22 pruebas específicas se repitieron: 21 superadas y la misma omitida. El resultado final y los logs están en `reports/session_12_2/validation.json` y `full_tests.log`.

Medición del procesamiento real de contingencia: **0,8065 s; RSS máxima 209.860 KiB (~204,94 MiB)**. Mide carga/reconciliación sin CP/BU externo; no es rendimiento de descarga ni de ingesta catastral. Los ensayos sintéticos tampoco se extrapolan a cinco municipios reales.

Pendientes principales: ejecutar el descargador en Ubuntu con conectividad, comprobar la integridad real de los diez archivos, calibrar incidencias/recuentos y memoria sobre esos datos, verificar vínculos PRTR/CP reales y realizar después la revisión visual conjunta. La antigüedad no se usa para diagnosticar necesidades, una subvención no implica préstamo y una concesión no acredita pago ni ejecución.
