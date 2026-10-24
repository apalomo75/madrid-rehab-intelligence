# Arquitectura regional preparada — cobertura aún parcial

**Actualización sesión 12.1:** el GeoPackage oficial ya está integrado: 179 municipios validados, 7.532 PRTR territorializados (3.808 Madrid y 3.724 externos). Solo Madrid tiene CP/BU integrado. [Fuente, catálogo, criterios, importes y pendientes vigentes](sesion_12_1_limites_prtr.md). El contenido de sesión 12 que sigue es histórico; su bloqueo de adquisición de límites queda superado.

La Comunidad tiene [179 municipios según su directorio oficial](https://www.comunidad.madrid/administracion-local/municipios-comunidad-madrid). La captura integrada CP/BU y eventos urbanísticos es únicamente Madrid capital (INE 28079). PRTR se conserva regionalmente sin filtrar por pertenencia al CP. El catálogo materializado tiene **una identidad oficial confirmada**, Madrid; no es un catálogo completo de 179 municipios. Completar identidades y límites es trabajo pendiente por acceso de red, no una cobertura conseguida.

## Componentes ejecutables

`grants.py` procesa la captura regional completa y utiliza el CP municipal existente. `regional.py` ofrece configuración por código, fuentes, rutas, disponibilidad, procesamiento, fecha, cobertura y calidad; validación de catálogo oficial y asignación espacial. No hay 179 pipelines ni descargas CP/BU nuevas. Los consumidores actuales y sus rutas no cambian.

`grants.parquet` mantiene el importe a nivel expediente. `grant_parcel_links` es una relación muchos-a-muchos sin importe; `grant_municipality_links` mantiene decisión territorial. `municipalities.parquet` contiene el registro efectivamente disponible. Los agregados con municipio desconocido conservan un grupo residual; no se crean filas con cero expedientes para municipios sin cobertura confirmada. Una relación `regional_cp_pending` no afirma otro municipio ni una parcela confirmada.

La identidad regional es INE, no nombres normalizados libres. `municipality_config('28005', 'Alcalá de Henares')` muestra cómo registrar un municipio oficial **sin declarar fuentes descargadas ni procesadas**. Más adelante se aportarán rutas verificadas y manifiestos CP/BU/CEEE; no se recicla la captura de Madrid para otro municipio. Ninguna ficha catastral regional se habilita sin productos auditados propios.

## Límites oficiales: fuente localizada y bloqueo

La página [IDEM — servicios web](https://www.comunidad.madrid/geoportal/idem) publica el servicio INSPIRE de Unidades Administrativas:

```
https://idem.comunidad.madrid/geoidem/UnidadesAdministrativas/wfs?REQUEST=GetCapabilities&Service=WFS&VERSION=1.1.0
```

El directorio municipal oficial enlaza asimismo el catálogo IDEM. Procedencia oficial localizada; licencia específica, fecha de corte, CRS y nombres efectivos de capas **pendientes de leer del recurso**. La página descriptiva no sustituye esos metadatos. El intento local de GetCapabilities falló por DNS (`reports/session_11/network_audit.json`). No hay polígonos municipales oficiales nuevos, áreas calculadas, ni clasificación exhaustiva.

Procedimiento reproducible cuando haya red:

1. Crear un directorio nuevo de captura. Guardar GetCapabilities, metadatos y condiciones de uso con SHA-256, URL y fecha real de descarga; resolver nombre de capa municipal a partir de la respuesta, sin adivinarlo.
2. Descargar únicamente los recintos municipales de Madrid con GetFeature, comprobando paginación y total de entidades. No descargar CP/BU. Revisar licencia y fecha del conjunto.
3. Convertir la fuente oficial a Parquet canónico: `municipality_code` INE textual de cinco posiciones, `name` oficial, `geometry_wkt`, `geometry_crs=EPSG:25830`. Transformar desde el CRS declarado, con orden de ejes verificado. Preservar el original. No generar polígonos de nombres o centroides.
4. Crear JSON con `source_url`, `publisher`, `license`, `source_date`, `sha256` del Parquet. `regional.load_official_boundaries` exige 179 códigos únicos 28xxx, geometrías válidas poligonales, CRS métrico y ausencia de solapamientos mayores de 1 m²; calcula área métrica. Completar catálogo y disponibilidades a partir de capturas verificadas.
5. Ejecutar el pipeline con los parámetros reales:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.grants \
  --municipalities /ruta/municipios_oficiales.parquet \
  --municipalities-manifest /ruta/municipios_manifest.json \
  --output-dir data/processed/grants/replay_con_limites
```

La asignación espacial diferencia una intersección, ninguna y varias. Contrasta el nombre oficial al final del literal de dirección y las relaciones CP Madrid. Un desacuerdo queda contradictorio, conservando candidato; no se resuelve por similitud. Variantes toponímicas requieren revisión. Confirmar municipio por límites no confirma parcela regional. La interfaz vigente avisa de la cobertura incompleta y no dibuja municipios ni puntos cuya pertenencia regional no ha sido auditada. La futura vista con recintos deberá consumir este catálogo verificado; no está validada con geometrías reales en esta sesión.

## Rendimiento y evolución

Parquet y agregados, lectura cacheada de proyección sin atributos originales, índices lógicos por RC14 e identidad. Un conjunto PRTR de 7.532 filas no requiere PostGIS ni servidor nuevo. La selección de parcela solo consulta relaciones confirmadas. Los cruces conservan identidades administrativas independientes. Todos los replays necesitan salida nueva. La siguiente sesión puede añadir CP/BU de un municipio oficial y revisar referencias pendientes sin perder la captura PRTR regional.

## Sesión 12 — componentes implementados y estado vigente

El diseño anterior se amplía con `regional_cadastre`, `regional_territory`, `regional_grants`, `regional_view` y `regional_audit`. El inventario oficial conservado tiene 179 recursos CP/BU; no es un catálogo INE completo ni un conjunto de límites. Los identificadores catastrales se preservan en una columna distinta. Las correspondencias INE–Catastro requieren evidencia revisada, incluyendo diferencias distintas de Madrid. No se emplean los rectángulos del feed para asignación espacial.

Las particiones nuevas se organizan por INE bajo un directorio de captura: `<cadastre_root>/<INE>/cp.parquet`, `bu.parquet`, `cp_bu_links.parquet`, `manifest.json`. Publicación atómica, orden por referencia, bounding boxes y grupos Parquet limitan lecturas; las consultas del visor cargan índice de un municipio y geometrías de la selección/ventana. Los hashes y metadatos de archivos forman parte de la invalidación de caché. El consumidor histórico de Madrid no cambia de rutas.

El producto territorial esperado conserva geometría oficial íntegra EPSG:25830 y una tabla de identidades normalizadas con fuente, fecha y manifiesto. El importador valida 179 identidades y la topología, pero la integridad frente a una geometría provincial independiente requiere revisión adicional. Todavía no se obtuvo la captura completa. La navegación vigente usa un inventario con nombres/códigos Catastro claramente etiquetados como tales; solo se habilita INE completo tras importar fuentes revisadas.

El cruce regional está separado del pipeline histórico PRTR: `grant_municipality_links` registra candidato espacial, evidencia CP histórica, conflicto, estado y distancia al borde. `grant_parcel_links` no contiene importes y conserva ambigüedades históricas. `grant_match_summary` permite evaluar multiparcela sin multiplicar concesiones; `municipality_program_summary` mantiene residuo desconocido y suma exacta en céntimos. Los manifiestos identifican la captura PRTR y las entradas territoriales/catastrales usadas. La vista impide mezclar decisiones con otra captura PRTR.

Estado real: cero nuevos CP/BU externos, límites regionales no importados, 3.727 PRTR pendientes. Los nuevos flujos con geometrías externas tienen pruebas sintéticas y necesitan piloto real. No hay base para estimar cobertura regional o throughput de ingesta. Las capturas CEEE existentes contienen otros literales municipales, sin identidad INE verificada; sesión 13 podrá usar estas particiones manteniendo ámbitos y IDs originales. Véase [sesión 12](sesion_12_expansion_regional.md).

## CEEE regional — sesión 13

`regional_energy` produce una capa independiente en `data/processed/energy/session_13_final_03/`: apariciones, contenidos canónicos, relaciones municipales/CP, cobertura municipal y coexistencia PRTR. Mantiene separados contenido energético, identidad de inscripción, ámbito, parcela y expediente. No hay vínculos BU ni pares físicos temporales demostrados. El ámbito de una vivienda no se propaga a la parcela. El catálogo CEEE local declara CC BY 4.0; PRTR mantiene su restricción. La sección nueva se oculta en modo público.

Hay particiones de certificados y vínculos por INE, lectura Parquet por RC14/identificador y caché acotada. Los otros 173 municipios conservan observaciones municipales sin parcelario integrado. Los pilotos parciales se consultan mediante el panel energético sin activar una falsa cobertura CP/BU completa. Importes exclusivos de la tabla por expediente evitan multiplicación por certificados o parcelas. Véanse [ejecución y modelo](sesion_13_energia_regional.md) y [calidad](calidad_energia_regional.md).

## Conservación administrativa — sesión 14

`conservation.py` consume productos administrativos de sesión 10, CP municipal auditado y contexto CEEE/PRTR de las capturas reales. No reconstruye Catastro ni modifica sus identidades. Materializa evidencia y trazabilidad independientes: 9.036 perfiles parcelarios de conservación, con enlaces energéticos y PRTR en tablas separadas. Los importes permanecen por expediente; una orden no se fusiona con una ayuda por coexistir en CP.

El inventario cubre los 179 municipios en términos de disponibilidad de fuentes, con cobertura individual ITE/IEE no integrada. Madrid tiene órdenes y obligaciones históricas; Alcalá, Getafe, Móstoles, Alcorcón y Arganda tienen distintas vías documentadas de padrón, consulta o dataset pendiente de adquisición. No se declara cobertura regional de resultados ni se aplica NDP fuera de Madrid. Las CP/BU y evidencias energéticas de los cinco pilotos siguen en sus snapshots parciales auditados.

`rec.py` es un parser experimental local sin red, pendiente de validación contra fichas legítimas reales. No existe recolector masivo autorizado. La capa conjunta de conservación se oculta en modo público. [Modelo y estados](modelo_conservacion.md), [fuentes y permisos](fuentes_conservacion_madrid.md).
