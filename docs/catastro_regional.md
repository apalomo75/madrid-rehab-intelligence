# Catastro regional — implementación y límites

**Actualización 12.2:** [piloto y descargador Ubuntu](sesion_12_2_piloto_catastral.md). El modo estricto descrito aquí sigue disponible. El piloto añade un modo auditado optativo que conserva incidencias/BuildingPart y relaciones no confirmadas sin modificar Madrid. No se incorporaron archivos reales externos: los diez GET fallaron por DNS.

El módulo `regional_cadastre.py` está operativo y probado offline con fixtures sintéticas y feeds oficiales conservados. **No se han descargado ni procesado CP/BU reales de municipios externos.** Los cinco candidatos siguen bloqueados por acceso DNS. No hay justificación empírica para escalar lotes reales todavía.

## Fuente y condiciones

La [página oficial INSPIRE](https://www.catastro.hacienda.gob.es/webinspire/index.html) publica servicios ATOM por municipio y actualización dos veces al año. La [descripción oficial ATOM](https://www.catastro.hacienda.gob.es/webinspire/documentos/inspire-ATOM.pdf) describe el servicio. Feeds provinciales usados y comprobados contra originales:

- CP: `https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/28/ES.SDGC.CP.atom_28.xml`.
- BU: `https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/28/ES.SDGC.bu.atom_28.xml`.

No se construyen URLs de ZIP por nombres: se leen los enlaces `enclosure` oficiales. Se codifican los espacios de las rutas, presentes por ejemplo en Alcalá de Henares. Los errores de esa codificación se detectaron y corrigieron durante la sesión. No se usan endpoints privados, descarga por inmueble, OSM ni WFS masivo para sustituir ATOM.

La [licencia DGC enlazada](https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf), consultada el 24/10/2026, permite uso propio y productos transformados con condiciones, pero restringe la difusión del original sin transformación. La frase de atribución del feed no se interpreta aislada como permiso para republicar ZIP originales. La documentación de acceso también permite suspensión por intensidad perjudicial. Las capturas originales permanecen locales. El visor no se ha publicado; los derechos PRTR continúan sin verificar.

## Identidad y configuración

La clave de partición es `municipality_code` INE, nunca el nombre. La clave del proveedor es `cadastre_code`. Las correspondencias requieren revisión y evidencia explícitas, no se aplica igualdad automática. La configuración final almacena código INE/catastral, nombre, evidencia de correspondencia, URLs CP/BU y fechas de recurso separadas. El manifiesto registra procesamiento, validación, hashes, rutas, número de objetos, segundos, RSS máximo y bytes de red. El inventario publica disponibilidad del recurso; no afirma descarga ni calidad de su contenido.

El CLI recibe una tabla Parquet revisada con `municipality_code`, `cadastre_code`, `name`, `evidence_url`. El cruce exige unicidad en ambos códigos y presencia en los feeds. Debe revisarse contra catálogo INE y evidencia oficial de Catastro; el validador estructural no demuestra por sí solo esa correspondencia.

## Ejecución después de desbloquear fuentes

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_cadastre \
  --crosswalk /ruta/correspondencias_revisadas.parquet \
  --boundaries /ruta/territorio/municipality_boundaries.parquet \
  --boundaries-manifest /ruta/territorio/manifest.json \
  --municipalities 28065 28092 28007 28074 28005 \
  --raw-dir data/raw/cadastre/capture_new \
  --output-dir data/processed/cadastre/pilot_new
```

Los códigos de esta línea son los INE de los candidatos; **la captura revisada y los límites necesarios aún no están disponibles**. El CLI resuelve sus códigos Catastro mediante tabla, no asume intercambiabilidad. Se permite como máximo cinco municipios por llamada. Añadir `--offline` para reproducir desde originales capturados. Reutilizar una partición validada exige misma configuración, mismo límite y hashes originales/productos intactos. Para actualizar fuente/fecha usar nuevas rutas. No se reprocesa Madrid salvo petición explícita; no hace falta copiar su CP histórico a la nueva estructura.

## Controles y checkpoints

Descarga secuencial HTTPS al host oficial, timeout del archivo 60 s, máximo 160 MiB por fichero y 320 MiB de red por municipio según el archivador existente. Dos intentos por defecto, máximo tres; 404 y errores de validación no se reintentan. Respeta datos válidos de caché, verifica URL/hash y rechaza originales sin metadatos antes de arriesgar sobrescritura. Los temporales truncados se eliminan; la reanudación es por archivo completo validado, sin afirmar soporte HTTP Range. Paquetes que excedan el presupuesto no se descargan; se auditan y requieren revisión del recurso/estrategia.

Los ZIP se leen sin extracción al sistema de archivos; máximo un GML de la clase esperada y expansión ≤2 GiB. El parser es incremental y ahora puede exigir coincidencia estricta con `numberReturned`. La validación rechaza colección vacía, IDs nulos/repetidos, CRS distintos de EPSG:25830, geometría inválida/vacía/sin área y coordenadas fuera de sobre regional. Exige ≥95% del área del objeto dentro del límite municipal; es umbral operativo revisable, no prueba de precisión de deslinde. CP con RC repetida no se fusiona: las relaciones la consideran ambigua.

CP–BU cruza referencia y geometría (distancia ≤1 m, umbral operativo). Un solo caso ambiguo, contradictorio o ausente detiene la promoción de esa partición; no elimina objetos incómodos para mejorar métricas. Esto es conservador y debe calibrarse con piloto real. El manifiesto final solo existe tras validar ambas tablas y relaciones; se publica mediante renombrado de un staging temporal. `checkpoint.json` resume el lote y se detiene ante el primer fallo. Las particiones previas correctas sobreviven a reinicios, incluso si el checkpoint no se terminó de escribir.

Productos por municipio INE: `cp.parquet`, `bu.parquet`, `cp_bu_links.parquet`, `manifest.json`. Orden por RC14/ID y grupos Parquet de 10.000 filas, geometría completa, bounding boxes escalares y CRS explícito. El mapa simplifica solo al renderizar y recorta por ventana/zoom, hasta 1.500 parcelas. El índice de selección carga únicamente referencias. CP/BU de la ficha se leen por filtro Parquet; cachés municipales acotadas.

## PRTR regional

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_grants \
  --boundaries /ruta/territorio/municipality_boundaries.parquet \
  --boundaries-manifest /ruta/territorio/manifest.json \
  --cadastre-dir data/processed/cadastre/pilot_new \
  --output-dir data/processed/grants/regional/replay_new
```

Lee PRTR de sesión 11 y nunca vuelve a descargar los 7.532 expedientes. La decisión territorial tiene candidato espacial, evidencia CP Madrid, contraste textual y conflicto separado. El matching carga solo CP del municipio de cada grupo, comprueba manifiestos, referencia exacta, unicidad y distancia ≤100 m. No usa proximidad para inventar referencias. Las ambiguas Madrid se preservan y los importes no entran en la tabla relacional. `grant_match_summary.parquet` registra número de relaciones y coberturas por expediente; varias relaciones no generan varias concesiones.

Antes de un escalado deben medirse descarga, Parquet, segundos, RSS y calidad reales de los cinco candidatos. No existe aún estimación basada en piloto ni criterio superado. Los límites por archivo y lote no sustituyen medir memoria: la validación mantiene temporalmente las geometrías del municipio y debe supervisarse antes de ampliar a municipios grandes.
