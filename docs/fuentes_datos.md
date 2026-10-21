# Fuentes de datos

Investigación: **21 de octubre de 2026**. Alcance: Madrid municipio; las fuentes autonómicas necesitan filtrado municipal.

Actualización posterior, alcance Catastro–CEEE: se ha implementado un pipeline de muestra. Su [registro HTTP](../reports/first_run/http_manifest.json) contiene dos intentos fallidos por resolución DNS, cero bytes y ningún código HTTP recibido. Las nuevas consultas web a DataStore (límite 2/3) y a capacidades/consultas WFS tampoco proporcionaron observaciones. Continúan sin verificarse los esquemas reales. Los [resultados](resultados_pipeline.md) y la [guía de ejecución](pipeline.md) sustituyen cualquier interpretación de que ya hay integración real.

## Cómo interpretar la evidencia

- **Verificado documentalmente (D):** una página oficial, un diccionario o una especificación describe el recurso. No acredita su calidad real.
- **Verificado por respuesta (R):** la herramienta web pudo leer el formulario o metadatos del servicio. Puede utilizar contenido indexado; no equivale a una prueba HTTP directa desde el entorno de ejecución.
- **Pendiente (P):** falta una muestra, acceso operativo o condiciones de reutilización confirmadas.

Se consultaron páginas, especificaciones y metadatos, sin guardar datasets ni ejecutar extracciones masivas. También se leyó la representación indexada de un listado PDF oficial de concesiones; no se descargó su archivo al repositorio. No se han medido coberturas ni tasas de enlace.

## 1. ITE/IEE municipal

**D/R.** La [Sede municipal](https://sede.madrid.es/portal/site/tramites/menuitem.62876cb64654a55e2dbd7003a8a409a0/?vgnextoid=8fe1b4173fd61110VgnVCM2000000c205a0aRCRD) confirma que el resultado favorable/desfavorable es consultable. El [Registro de Edificios y Construcciones](https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons) ofrece búsqueda por expediente, registro o dirección; la respuesta es informativa, sin valor de certificado.

**Granularidad:** expediente y dirección de edificio. **Cobertura:** municipio; exhaustividad e historia no comprobadas. **Actualización:** frecuencia no localizada. **Variables pendientes:** fechas exactas disponibles, categorías de deficiencias, subsanación, referencia catastral y relación entre sucesivas inspecciones. No se ha validado una ficha individual.

El [boletín del Geoportal de mayo de 2023](https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/GEOPORTAL/BOLETINES/Geoportal_Madrid_Boletin_037_Mayo_2023.html) documenta acceso desde el visor urbanístico hacia esa consulta: **el enlace no demuestra una capa descargable de resultados ITE**. El [listado de edificios pendientes](https://servpub.madrid.es/GITEP_WBINFORME/SGiteInforme) anuncia PDFs de obligaciones de presentación; no representa resultados desfavorables.

**Descarga/API:** no se ha localizado CSV, ZIP, WFS, GeoJSON o API documentada de resultados por edificio. Esto no demuestra su inexistencia. **Reutilización:** la Sede distingue información pública de datos del propietario, técnico y expediente en tramitación sujetos a interés legítimo. No trasladar automáticamente la licencia del portal abierto a este formulario.

**Cruce:** dirección normalizada, con validación por portal y parcela; RC solo si se confirma. Solicitar posteriormente al Ayuntamiento un extracto reutilizable con identificadores, resultados, fechas, deficiencias publicables y subsanaciones, sin datos personales. No se ha enviado ninguna solicitud.

## 2. Certificados energéticos autonómicos

**D/R.** El [catálogo CEEE](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica) publica históricos anteriores a 2024 y años 2024/2025 en ZIP; 2026 en CSV, con actualización mensual. Fecha declarada: 05/10/2026. Cobertura: Comunidad de Madrid; no es un censo de todos los edificios. Licencia enlazada: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.es).

El [diccionario 2026](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica/resource/4e42b49c-bb6b-485a-a7b7-8f760f356855) documenta:

| Variables | Significado |
| --- | --- |
| `edif_codreg`, `edif_tipo`, `edif_fecha` | Trazabilidad, ámbito certificado, emisión |
| `edif_direc`, `edif_muni`, `edif_refcat` | Localización y referencias, posiblemente múltiples |
| `edif_año`, `edif_superf` | Antigüedad y superficie habitable |
| `cal_norenovglobal`, `cal_co2global` | Calificaciones globales de consumo y emisiones |
| `norenov_global`, `norenov_co2global` | kWh/m²·a y kg CO₂e/m²·a |

El recurso declara DataStore activo e identificador `4e42b49c-bb6b-485a-a7b7-8f760f356855`. Las acciones CKAN `package_show` y `datastore_search` son **candidatas no verificadas operativamente**. Se intentó `limit=1`, sin obtener registros. Descargas disponibles mediante los enlaces de la ficha; no se solicitaron los CSV/ZIP completos.

**P:** valores reales A–G, dominio de `edif_tipo`, nulos, duplicados, equivalencia de esquemas históricos y existencia de renovaciones. **Cruce propuesto:** separar múltiples RC y conservar ámbito y fecha. Una vivienda certificada no califica todo su edificio; el promedio de letras tampoco constituye una certificación de edificio.

## 3. Subvenciones PRTR

**D.** La [Comunidad de Madrid](https://www.comunidad.madrid/vivienda/ayudas-actuaciones-rehabilitacion-energetica-edificios-residenciales-viviendas-prtr) documenta el [visor COAM–Comunidad](https://visorrehabilitaprtrmadrid.coam.org/), con actualización indicada del 20/07/2026: P1 barrio, P3 edificio, P4 vivienda y P5 libro del edificio/proyecto. **R:** el visor devolvió 403 en la herramienta web.

**P:** endpoints REST/WFS, GeoJSON/CSV/ZIP públicos, esquema, RC, importes, estados, periodicidad, exhaustividad y licencia de extracción/redistribución. No se inspeccionaron recursos internos ni se eludieron restricciones. No confundir este visor con las subvenciones municipales del Plan Rehabilita.

**Alternativa documental verificada:** la página de [ERRP](https://www.comunidad.madrid/vivienda/entornos-residenciales-rehabilitacion-programada-errp-programa-1) enlaza un [listado P1 de Madrid, fechado 09/10/2025](https://www.comunidad.madrid/docs/assets/2025/10/09/errp_beneficiarios_madrid_listado_09_10_2025.pdf). Su representación indexada contiene convocatoria/BDNS 691556, código y fecha de concesión, beneficiario, importe e instrumento. No se observan columnas de RC o geometría; algunas comunidades incorporan dirección en su denominación. Contiene personas físicas: no reproducir nombres/NIF en la plataforma. Remite al [aviso legal BDNS](https://www.infosubvenciones.es/bdnstrans/GE/es/avisolegal), pendiente de revisión. No acredita estados de obra ni cobertura de P3–P5.

**Cruce propuesto:** RC explícita; subsidiariamente dirección validada. Mantener relación muchos-a-muchos entre ayuda y edificios. P1 territorial no implica concesión a cada edificio; P4 no equivale a rehabilitación integral; P5 no prueba obras ejecutadas. Concesión, pago y finalización deben distinguirse.

## 4. Catastro

**D.** El [portal INSPIRE oficial](https://www.catastro.hacienda.gob.es/webinspire/index.html) documenta parcelas CP, direcciones AD y edificios BU. Cubre Madrid; el ámbito nacional excluye País Vasco y Navarra. WMS sirve imágenes, no sustituye la descarga vectorial.

**Accesos documentados:**

```text
https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx
https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx
https://ovc.catastro.meh.es/INSPIRE/wfsAD.aspx
https://www.catastro.hacienda.gob.es/INSPIRE/buildings/ES.SDGC.BU.atom.xml
```

La web publica las bases WFS mediante HTTP; HTTPS se intentó para BU sin respuesta utilizable. ATOM ofrece paquetes municipales; no se abrieron ZIP. Publica dos actualizaciones anuales; registrar fecha real del paquete. WFS se describe como actualizado continuamente.

La [especificación de conjuntos](https://www.catastro.hacienda.gob.es/webinspire/documentos/Conjuntos%20de%20datos.pdf) incluye `inspireId`, RC de parcela, geometría, `dateOfConstruction`, `currentUse`, viviendas, unidades y `officialArea`. El año puede ser un intervalo entre unidades; el uso es dominante y la superficie no equivale a superficie habitable energética. `conditionOfConstruction` no es una ITE. BU puede agrupar construcciones de una parcela: no identificar automáticamente parcela, portal y bloque físico.

La [especificación WFS BU](https://www.catastro.hacienda.gob.es/webinspire/documentos/inspire-bu-WFS.pdf) admite consultas por BBOX y consultas almacenadas; indica hasta 4 km² y 5.000 elementos, sin SQL genérico. **P:** capacidades actuales, esquemas efectivos, completitud y una muestra acotada.

Para atributos de inmueble, existen [servicios no protegidos](https://www.catastro.hacienda.gob.es/ayuda/servicios_web.htm) y [documentación XML/SOAP](https://www.catastro.hacienda.gob.es/ws/Webservices_Libres.pdf), incluida `Consulta_DNPRC`; funcionamiento no probado. La [ayuda de consulta libre](https://www.catastro.hacienda.gob.es/ayuda/ayuda_cl.htm) distingue finca e inmueble. Conservar RC completa; derivar sus primeros 14 caracteres solo como clave de parcela urbana, con validación.

**Reutilización:** la [licencia INSPIRE](https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf) permite productos transformados, incluso comerciales, y restringe redistribuir el original sin transformación. Revisar antes de publicar artefactos; no asumir que convertir formato basta. No incorporar titularidad ni valor catastral.

## 5. Órdenes de ejecución y reparación

**D.** La [Carta de Servicios de Edificación](https://www.madrid.es/portales/munimadrid/es/Inicio/El-Ayuntamiento/Calidad-y-Evaluacion/Cartas-de-Servicios/Servicios-Prestados-Carta-de-Servicios-de-la-Edificacion/?vgnextoid=3b4baa94fc0cb910VgnVCM100000891ecb1aRCRD) acredita la gestión municipal de órdenes estructurales y actuaciones subsidiarias. La [memoria municipal 2020](https://agenciatributaria.madrid.es/UnidadesDescentralizadas/Presupuestos/EjecucionPresupuestaria/MemoriasCumplimientoObjetivos/Ficheros/MCO_2020_Volumen_1.pdf) sitúa órdenes y subsanaciones entre los contenidos del Registro; es evidencia histórica, no del esquema actual.

**P:** no se ha localizado un dataset reutilizable por edificio. Dirección, expediente, fecha, motivo, estado, cumplimiento y RC son campos necesarios, no confirmados. Cobertura municipal teórica; historia, actualización y licencia desconocidas. No confundir una licencia de obra con una orden de ejecución. Cruce condicionado a dirección/RC verificables y a distinguir orden abierta de subsanada. Proponer solicitud municipal específica; no construir un censo desde anuncios aislados de boletines.

## 6. Distritos y barrios

**D/R.** Fichas oficiales de [distritos](https://geoportal.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=541f4ef6-762b-11e9-861d-ecb1d753f6e8) y [barrios](https://servpub.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=422fa235-762b-11e9-861d-ecb1d753f6e8): polígonos, nombres y códigos; 21 distritos y 131 barrios. Recursos SHP/ZIP, KML, CSV, XLSX y **TopoJSON**, que no debe confundirse con GeoJSON. CRS documentado: EPSG:25830. Barrios muestra fecha 31/08/2026; distritos, 12/07/2021. No se verificó una periodicidad fija.

El [REST de límites](https://sigma.madrid.es/hosted/rest/services/CARTOGRAFIA/LIMITES_ADMINISTRATIVOS/MapServer?f=pjson) respondió con metadatos: Query, JSON/GeoJSON/PBF, máximo 2.000 registros; capas 3 distritos y 17 barrios. La [capa 3](https://sigma.madrid.es/hosted/rest/services/CARTOGRAFIA/LIMITES_ADMINISTRATIVOS/MapServer/3?f=pjson) confirma `COD_DIS_TX`, `NOMBRE`, `FCH_ALTA`, `FCH_BAJA` y geometría. No mezclar capas repetidas por escala. La consulta de un registro no produjo respuesta utilizable.

Descargas documentadas, no ejecutadas:

```text
https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/LIMITES_ADMINISTRATIVOS/Distritos/Distritos.zip
https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/LIMITES_ADMINISTRATIVOS/Barrios/Barrios.zip
```

Aplican las [condiciones municipales](https://datos.madrid.es/pages/condiciones-generales-ayuntamiento-de-madrid): atribución, fecha disponible, conservación de metadatos y ausencia de respaldo municipal implícito. Cruce espacial con Catastro en CRS común; resolver edificios sobre límites mediante intersección predominante y revisión de empates.

## Registro de pruebas pequeñas y límites

Todas las pruebas corresponden al 21/10/2026; no hubo carga, enumeración de edificios ni reintentos masivos.

| Petición | Canal y resultado | Conclusión |
| --- | --- | --- |
| GET ficha CEEE y recurso 2026 | Web: HTML y diccionario legibles | Documentación accesible |
| GET `https://datos.comunidad.madrid/api/3/action/package_show?id=registro_certificados_eficiencia_energetica` | Python estándar: fallo DNS antes de HTTP; Web: inaccesible | No atribuir un código HTTP al servidor |
| GET `package_show` también bajo `/catalogo/api/3/action/` | Web: inaccesible | Base API por confirmar |
| GET `datastore_search?resource_id=4e42b49c-bb6b-485a-a7b7-8f760f356855&limit=1`, ambas bases | Web: inaccesible | Sin muestra de certificados |
| GET raíz visor PRTR | Web: 403 | No inferir backend ni licencia |
| GET formulario REC | Web: legible | Sin consulta individual ni POST |
| GET WFS BU `?service=WFS&version=2.0.0&request=GetCapabilities` | Web: inaccesible | Operación pendiente |
| GET REST límites `?f=pjson` y `/3?f=pjson` | Web: metadatos legibles | No se obtuvieron geometrías |
| GET `/17?f=pjson` | Web: inaccesible | Esquema barrios pendiente |
| GET `/3/query?where=1%3D1&outFields=COD_DIS_TX%2CNOMBRE&returnGeometry=false&resultRecordCount=1&f=pjson` | Web: inaccesible | Query documentado, no validado con registros |

Las respuestas web no proporcionan cabeceras, latencias o bytes fiables para este informe. No se inventan. La restricción DNS del entorno impidió una verificación directa adicional; los errores de herramienta no prueban caída del servicio. No se ha usado `Range`: debe limitarse la lectura y abortar si el servidor ignora ese encabezado en futuras muestras.
