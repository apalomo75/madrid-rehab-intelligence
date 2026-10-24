# Viabilidad de subvenciones

**Cero concesiones adquiridas; ninguna vinculada a CP/BU.** Las cifras de presupuesto de una convocatoria no son concesiones. No se han obtenido fases de pago, justificación o ejecución.

La [página PRTR autonómica](https://www.comunidad.madrid/vivienda/ayudas-actuaciones-rehabilitacion-energetica-edificios-residenciales-viviendas-prtr) enlaza el [visor COAM](https://visorrehabilitaprtrmadrid.coam.org/). Describe programas 1 (barrio), 3 (edificio), 4 (vivienda) y 5 (libro/proyecto), con actualización anunciada 20/07/2026. El visor devuelve 403 en la herramienta web. No se han podido verificar atributos, geometrías, identificadores persistentes, CRS, exportación, servicio GIS público documentado ni licencia. No se deducen de la presencia anunciada de puntos. No se intentó eludir el bloqueo.

## BDNS/SNPSAP

Se inspeccionó el [OpenAPI oficial 1.1.0](https://www.infosubvenciones.es/bdnstrans/estaticos/doc/snpsap-api.json), además del punto de entrada Swagger. Base documentada `https://www.infosubvenciones.es/bdnstrans/api`:

- `GET /convocatorias/busqueda` consulta convocatorias; no equivale a concesiones.
- `GET /concesiones/busqueda`: `page`, `pageSize`, `vpd`, descripción/tipo de búsqueda, número de convocatoria o concesión, fechas y filtros de organismo. Fechas de búsqueda `dd/mm/yyyy`.
- `GET /concesiones/exportar`: `tipoDoc` obligatorio (`pdf`, `xlsx`, `csv`) y `vpd` obligatorio; filtros de búsqueda. Revisar tamaño y alcance antes de exportar.
- La respuesta de búsqueda documenta `content`, paginación, totales y advertencia legal. El modelo de concesión expone identidad de publicación/convocatoria, organismos, fecha, instrumento e importe. También contiene beneficiario: se excluye de productos públicos del proyecto. El ejemplo embebido en OpenAPI no se utiliza como registro real ni como ayuda de rehabilitación de Madrid.

No se ha obtenido un ejemplo real consultado de rehabilitación madrileña. Consulta acotada: una fila, descripción «rehabilitación», concesión entre 01/07/2026 y 31/07/2026; la herramienta web la declara inaccesible y Python falla por DNS. Una búsqueda textual nacional no garantiza Madrid ni el programa: cualquier resultado exigiría revisión posterior de convocatoria y órgano. El esquema advierte que los datos son dinámicos y permite restricciones ante abuso; no se encontró una cuota numérica que deba inventarse. Un único intento por recurso, sin paginación masiva.

No se ha acreditado localización del inmueble en registros reales. La del beneficiario u órgano no sirve como coordenada de la obra. La conciliación entre visor PRTR y BDNS queda pendiente: necesita expediente/identificador oficial y comprobación de programa, resolución, importe, alcance y fase; no deduplicar por beneficiario ni dirección aproximada. Los contratos existentes excluyen concesiones contradictorias antes de sumar importes; no se aplicaron sobre datos nuevos.

Para desbloquear: abrir exportación oficial con filtros revisados fuera del sandbox o pedir al publicador un recurso con RC/portal de actuación, alcance vivienda/edificio y fase verificable, junto con licencia, corte temporal y clave estable. No se ha realizado la solicitud. Primero revisar [aviso legal](https://www.pap.hacienda.gob.es/bdnstrans/GE/es/avisolegal), luego conservar original y manifiesto, suprimir datos personales innecesarios y normalizar. Concesión nunca acredita ejecución material.
