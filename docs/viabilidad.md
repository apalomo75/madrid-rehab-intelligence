# Viabilidad

Evaluación inicial: **21/10/2026**. Evidencias y enlaces técnicos en [fuentes de datos](fuentes_datos.md).

Actualización de implementación: el [pipeline Catastro–CEEE](pipeline.md) existe, pero la [ejecución real](resultados_pipeline.md) no obtuvo observaciones por fallo DNS. No se han medido coberturas. La anterior elección de Usera por ERRP deja de ser criterio de selección en esta iteración: se compararán disponibilidad e identidades confirmadas sin usar ayudas. La selección definitiva sigue pendiente.

## Dictamen

**Viabilidad parcial y condicionada.** Existe una base documental sólida para explorar Catastro, certificados y límites. No está demostrada la extracción reproducible de las seis fuentes ni la cobertura por edificio. El objetivo completo sigue pendiente; un mapa preliminar no debe presentarse como diagnóstico integral de rehabilitación.

| Componente | Situación | Condición para avanzar |
| --- | --- | --- |
| Base residencial catastral | Servicios documentados | Validar muestra, grano, licencia y atributos |
| Eficiencia energética | Diccionario y descargas identificados | Comprobar tipos certificados, históricos y enlace |
| ITE/IEE | Consulta pública confirmada | Obtener acceso reutilizable a resultados e historia |
| PRTR | Visor documentado; listado P1 parcial | Validar exportación, RC, importes y estados |
| Órdenes | Procedimiento acreditado | Obtener extracto estructurado y condiciones |
| Límites | Metadatos REST accesibles | Validar geometrías y vigencia |

## Piloto propuesto: Usera

La Comunidad documenta el ERRP de **Meseta de Orcasitas y Poblado Dirigido de Orcasitas** en su [página oficial de entornos](https://www.comunidad.madrid/vivienda/entornos-residenciales-rehabilitacion-programada-errp-programa-1). Permite comprobar el tratamiento del programa territorial P1 y contrastarlo con el resto de Usera.

La elección es metodológica: delimitar un distrito y estudiar tanto edificios vinculados a ayudas localizadas como edificios sin coincidencia. No se ha demostrado que Usera tenga más necesidades o mejores datos que otros distritos. No se han calculado antigüedad, volumen de certificados ni número de concesiones del piloto.

El ERRP no equivale al barrio administrativo ni prueba ayudas individuales. Antes de confirmar el piloto, medir cobertura CEEE, accesibilidad ITE y correspondencia de ayudas. Si faltan casos comparables, ampliar la muestra o reconsiderar el distrito con evidencia cuantitativa.

## Riesgos que afectan a la interpretación

- **Universo sesgado:** partir de certificados o subvenciones excluiría edificios sin esos registros. Partir del inventario catastral residencial y enlazar las demás fuentes mediante uniones que lo conserven.
- **Granularidad:** una parcela puede agrupar bloques; una inspección, varios portales; un certificado, una vivienda o varias RC. Preservar relaciones múltiples.
- **Energía:** separar certificado de edificio completo, parte y ámbito desconocido. No trasladar la peor vivienda al bloque ni promediar letras A–G. Los certificados pueden ser anteriores a una reforma.
- **Ayudas:** «sin subvención localizada» no significa «sin subvención». Mostrar programas, periodo y cobertura investigados. No equiparar concesión, abono y obra finalizada.
- **Conservación:** ITE desfavorable histórica puede estar subsanada. No inferir deficiencias desde edad ni desde ausencia de ITE. El estado catastral no sustituye una inspección técnica.
- **Actualización:** fuentes con distintos cortes temporales requieren historial y fecha por dato; no combinar sin advertencia observaciones incompatibles.

## Publicación y coste

La publicación gratuita es un objetivo razonable para un piloto precalculado, todavía no una garantía operativa. [Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) ofrece alojamiento gratuito; deben comprobarse memoria, concurrencia, dependencias geoespaciales y tiempos de arranque con la muestra real.

La [licencia catastral](https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf) exige atención a la transformación del producto. Publicar análisis derivados con trazabilidad requiere revisar el cumplimiento antes de distribuir geometrías u originales. Las licencias del visor PRTR, REC y órdenes siguen pendientes. El listado P1 contiene datos personales: la vista pública propuesta se limita a edificios y ayudas pertinentes, sin nombres de personas ni NIF.

## Criterios de decisión

Tras autorización, una muestra revisada manualmente debe cuantificar cobertura, duplicados, ámbitos energéticos y precisión de enlace por método. Propuesta inicial: 30 casos diversos, incluyendo varios portales por parcela, certificados de vivienda/edificio y ayudas múltiples; no constituye una estimación estadística de toda Madrid.

Avanzar al prototipo cuando exista base residencial coherente, mediciones de enlace y permiso de reutilización claro para las capas publicadas. Si ITE/órdenes no son accesibles, presentar explícitamente una versión de alcance reducido para aprobación; no sustituir esas fuentes por indicadores inventados. No establecer todavía pesos de una puntuación de potencial.
