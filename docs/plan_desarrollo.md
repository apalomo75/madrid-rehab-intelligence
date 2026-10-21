# Plan de desarrollo

Fecha: 21/10/2026. **El usuario ha autorizado un pipeline inicial Catastro–CEEE y pruebas de calidad.** El alcance vigente excluye ITE/IEE, órdenes, subvenciones, Streamlit y publicación. Las fases siguientes describen el plan general; no amplían esa autorización. Véase el [resultado de esta iteración](resultados_pipeline.md).

## Fase 0 — Investigación inicial completada

- Inventario de seis familias de fuentes, documentación y accesos candidatos.
- Distinción entre verificación documental, respuesta de metadatos y pruebas pendientes.
- Evaluación de viabilidad, propuesta Usera y diseño de arquitectura.
- Sin dependencias instaladas, código de aplicación, datasets locales ni publicación.

Consultar [fuentes](fuentes_datos.md), [viabilidad](viabilidad.md) y [arquitectura](arquitectura.md).

## Fase 1 — Resolver accesos y reutilización

Tras aprobación, confirmar primero las bases API CEEE y una consulta de un registro; después capacidades WFS y una geometría acotada. Inspeccionar el visor PRTR únicamente mediante recursos públicos documentados y con límites explícitos. Revisar aviso BDNS y condiciones de cada fuente.

Preparar solicitudes municipales para ITE/IEE y órdenes: pedir formato estructurado, identificadores de edificio/parcela/portal, fechas, resultados, deficiencias publicables, subsanación, actualización y licencia. Preparar consulta COAM/Comunidad sobre exportación del visor, RC, programas, importes y estados. **Redactar estas solicitudes no equivale a enviarlas: cualquier contacto externo requiere autorización expresa.**

Entregable: matriz de acceso operativo/licencia y muestras mínimas. Cierre: confirmar alcance viable o presentar alternativa reducida; no declarar disponibles las seis fuentes sin evidencia.

## Fase 2 — Muestreo y contratos

Proponer 30 casos revisables de Usera, dentro y fuera de ERRP, sin seleccionar solo beneficiarios. Incluir edificios con y sin certificados localizados y relaciones complejas entre parcela, portal y bloque.

Registrar dominios reales de `edif_tipo`, RC múltiples, formatos históricos, unidades y duplicados. Medir enlaces correctos, ambiguos y fallidos por método; publicar denominadores. Determinar qué significa cada estado de ayuda y cada fecha ITE. Fijar umbrales de aceptación a partir de la revisión, antes de automatizar a escala.

Entregable: diccionario contrastado, contratos y decisión motivada de mantener o cambiar el piloto. No prometer cobertura de edificios completos usando certificados de vivienda.

## Fase 3 — Base técnica reproducible

Solo entonces seleccionar versiones de Python y dependencias, manifiesto y lockfile; configurar formateador, lint y pruebas. Implementar adaptadores con límites, caché, tiempos de espera, reintentos acotados y manifiestos de procedencia.

Construir universo residencial desde Catastro, normalizar fuentes y producir Parquet/GeoParquet y vistas DuckDB. Conservar todos los edificios de partida. Respetar la licencia catastral en los productos distribuidos.

Pruebas necesarias: formatos de RC, múltiples referencias, ámbitos energéticos, cruces ambiguos, CRS, historial y ausencia de doble conteo de ayudas. Verificar explícitamente que un edificio sin coincidencias permanece en el universo.

## Fase 4 — Prototipo del piloto

Crear mapa Streamlit/PyDeck con filtros, ficha de procedencia y estados desconocidos visibles. Separar diagnóstico energético, conservación y ayudas. Incorporar ITE/órdenes solo cuando sus accesos y permisos estén resueltos; cualquier exclusión cambia el alcance y debe constar en la revisión.

Validar con casos manuales; no publicar una puntuación de potencial hasta acordar reglas, pesos y tratamiento de ausencias. Medir tamaño de artefactos, memoria y latencia con concurrencia representativa.

## Fase 5 — Revisión y publicación

Revisar atribuciones, licencias, privacidad y accesibilidad; documentar cobertura, corte temporal y limitaciones. Preparar repositorio GitHub y configuración Cloud, evitando subir originales o secretos. Someter la versión concreta a aprobación antes de publicación pública.

Entregable: aplicación revisable y procedimiento de actualización con métricas y reversión de versión. No fijar una frecuencia de refresco más exigente que la de las fuentes.

## Fase 6 — Ampliación

Extender a otros distritos después de comparar cobertura y precisión. Evaluar MapLibre/FastAPI cuando las mediciones de rendimiento o requisitos de uso lo justifiquen. No se asignan fechas de entrega hasta resolver los accesos administrativos.
