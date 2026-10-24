# Procedencia y reutilización PRTR

Estado: **licencia específica no verificada; datos locales, sin redistribución autorizada inferida**.

La descarga aportada procede de `https://visorrehabilitaprtrmadrid.coam.org/api/main.cgi?method=resum&pr=all`, bajo dominio `coam.org`. Es el visor de rehabilitación PRTR de la Comunidad de Madrid indicado en la entrega. El dominio permite identificar el alojamiento vinculado a COAM; no acredita por sí solo quién es titular jurídico del dataset, responsable formal del visor o licenciante. Estas identidades y posibles acuerdos con Comunidad de Madrid deben contrastarse en aviso legal y metadatos antes de publicar.

La fecha de actualización 20/07/2026 proviene del metadato del visor descrito por la entrega; no figura en el GeoJSON. La descarga declarada es 24/10/2026. Fecha de publicación y periodicidad desconocidas. No se interpreta mtime ni año de expediente como fecha administrativa.

El navegador de investigación obtuvo HTTP 403 al abrir la raíz del visor; las peticiones locales fallaron por DNS. No se han podido verificar condiciones de acceso, reutilización, atribución, restricciones ni una licencia explícita. La API pública, HTTP 200 anterior o CORS no conceden derechos de redistribución. No se hicieron descargas masivas ni consultas individuales. Evidencia de red en `reports/session_11/network_audit.json`.

Atribución de procedencia local: «Visor rehabilitación PRTR Comunidad de Madrid, dominio COAM; API resum/all; actualización indicada 20/07/2026; captura aportada 24/10/2026». No es una declaración de cumplimiento de requisitos de licencia aún desconocidos. Para resolver la incertidumbre deben conservarse aviso legal, condiciones de reutilización y metadatos oficiales, o autorización del titular.

Los 28 campos originales no incluyen columnas nominales de beneficiarios, NIF, correos ni teléfonos. Sí contienen dirección, referencias catastrales, expediente y atributos territoriales que pueden permitir inferencias sobre viviendas o personas al cruzarlos con otras fuentes. No se garantiza anonimato. `rnt_uc` y distribuciones censales son contexto agregado, nunca ingresos individuales. Se mantienen en `raw_json` local para trazabilidad, fuera de la proyección de Streamlit y CSV.

Los datos originales, Parquet y relaciones completas están bajo `data/` ignorado por Git. No se han publicado ni agregado a Git. La exportación del visor es local y usa una lista de campos permitidos con neutralización de fórmulas CSV. No exporta direcciones, RC originales completas, `raw_json`, ni variables de renta. `MADRID_REHAB_PUBLIC=1` desactiva PRTR en vistas, fichas y descargas; este control preventivo no autoriza el despliegue del resto de fuentes. La aplicación debe seguir ejecutándose localmente hasta resolver derechos. Las pruebas y el análisis offline no dependen de la licencia de redistribución.

Las definiciones de programas se contrastaron en el [RD 853/2021 del BOE](https://boe.es/buscar/act.php?id=BOE-A-2021-16233). Este texto normativo no concede licencia sobre la descarga del visor. Concesión, pago y ejecución permanecen separados.
