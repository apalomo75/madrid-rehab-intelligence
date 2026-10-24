# Calidad de límites municipales — sesión 12

**Actualización sesión 12.1:** el GeoPackage oficial ya está integrado: 179 municipios validados, 7.532 PRTR territorializados (3.808 Madrid y 3.724 externos). Solo Madrid tiene CP/BU integrado. [Fuente, catálogo, criterios, importes y pendientes vigentes](sesion_12_1_limites_prtr.md). El contenido de sesión 12 que sigue es histórico; su bloqueo de adquisición de límites queda superado.

**No hay límites municipales regionales importados ni validación de precisión geográfica real.** El catálogo INE completo tampoco se ha capturado. Un inventario de 179 recursos ATOM no resuelve ninguno de esos dos objetivos.

## Fuentes verificadas en investigación web

| Fuente | URL | Resultado |
| --- | --- | --- |
| Directorio oficial autonómico | https://www.comunidad.madrid/administracion-local/municipios-comunidad-madrid | Confirma 179 municipios; enlaza IDEM |
| Instituto de Estadística / relación INE 01/01/2026 | https://www.madrid.org/iestadis/fijas/clasificaciones/muni.htm | Página legible; enlaza XLSX |
| XLSX autonómico | https://www.madrid.org/iestadis/fijas/clasificaciones/descarga/mcmva26.xlsx | URL enlazada verificada; bytes no recuperados, web no admite ese MIME y Python falla por DNS |
| IDEM WFS | https://idem.comunidad.madrid/geoidem/UnidadesAdministrativas/wfs?REQUEST=GetCapabilities&Service=WFS&VERSION=1.1.0 | Captura local bloqueada por DNS; capa, CRS, fecha y licencia específica pendientes |
| IGN, colección oficial | https://api-features.ign.es/collections/administrativeunit | Página, esquema, CRS y licencia accesibles mediante investigación web |
| IGN, esquema | https://api-features.ign.es/collections/administrativeunit/schema | Expone `nationalcode`, `nameunit`, `codnut3` y nivel administrativo |
| IGN, directorio de servicios | https://www.ign.es/web/ign/portal/ide-area-nodo-ide-ign | Publica WFS y ATOM oficiales |
| IGN, licencia enlazada desde colección | https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf | CC BY 4.0, reconocimiento y atribución de obra derivada |

Consulta: 24/10/2026. Fecha de consulta no es fecha del dataset. El primer GeoJSON de ejemplo de IGN pudo inspeccionarse en web, pero no se obtuvo la colección completa madrileña. No se ensamblaron polígonos desde resultados parciales ni se usaron URLs de descarga supuestas. La ficha del IGN no demuestra por sí sola que una futura captura tenga 179 recintos completos.

## Contrato de importación funcional

`regional_territory.py` recibe:

1. CSV revisado con 179 filas y `municipality_code` INE de cinco posiciones, `name` oficial y `boundary_source_id` exacto. `boundary_source_id` se corresponde con un atributo configurado de la geometría; no se deduce por texto ni por sufijos numéricos. Es una adaptación revisada de las fuentes, no un catálogo ficticio incluido en el repositorio.
2. GeoJSON oficial completo, con originales conservados. El importador admite CRS84/lon-lat, EPSG:4326/lon-lat tras revisar ejes, o EPSG:25830. Rechaza contradicción con CRS declarado y paginación pendiente.
3. JSON de procedencia con `source_url`, `catalogue_source_url`, `publisher`, `license`, `source_date` y `identity_mapping_review`, completados con evidencia real. No usar fechas inventadas o mtime como fecha de fuente.

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.regional_territory \
  --catalogue /ruta/catalogo_ine_revisado.csv \
  --geojson /ruta/limites_oficiales_completos.geojson \
  --provenance /ruta/procedencia_revisada.json \
  --id-property nationalcode --source-crs OGC:CRS84 \
  --output-dir data/processed/territory/official_new
```

El nombre `nationalcode` es un atributo efectivamente publicado por IGN; el CSV debe conservar su ID exacto. El ejemplo **no afirma** que esos ficheros ya existan ni propone una consulta WFS sin comprobar. Apuntar `MADRID_REHAB_TERRITORY_DIR` a la nueva salida únicamente tras revisar los informes.

Produce `municipalities.parquet`, `municipality_boundaries.parquet`, `municipality_catalog.json`, `quality.json` y `manifest.json`. Conserva polígonos completos, áreas métricas, punto representativo interior, multipartes, CRS y origen. No aplica `make_valid` ni simplificación analítica silenciosa. El mapa deriva una representación simplificada sin modificar los originales.

## Controles y límites de los controles

Exige 179 códigos únicos 28xxx, nombres/IDs completos y únicos, Madrid presente, geometrías Polygon/MultiPolygon válidas y no vacías, CRS25830, sobre regional amplio y ausencia de intersecciones con área >1 m². El sobre solo detecta errores gruesos de CRS; no acredita pertenencia municipal. Informa huecos, área de huecos y área total de unión. **No acredita ausencia de huecos ni exhaustividad territorial sin contraste independiente con provincia/Comunidad.** Los enclaves o huecos pueden ser reales y requieren revisión oficial; no se rellenan automáticamente. La licencia y fecha exactas se revisan por captura.

El cruce PRTR usa el límite original. Un punto compartido o a ≤1 m de un borde se deja limítrofe; cero intersecciones queda exterior o próximo a borde. La tolerancia es operativa, no precisión legal de deslinde. Una discrepancia espacial con CP histórico se conserva en campos separados, sin revocar silenciosamente 3.805 confirmaciones anteriores. Los nombres solo sirven para contraste de una declaración reconocida; nunca para asignación exclusiva.
