# Resultados del primer pipeline

Fecha: **21/10/2026**. Alcance autorizado: exclusivamente Catastro y CEEE.

## Resultado real: acceso bloqueado

Se implementó y ejecutó el pipeline. No fue posible descargar observaciones oficiales:
ambos dominios fallan con `Temporary failure in name resolution`. El [manifiesto](../reports/first_run/http_manifest.json) registra dos peticiones intentadas, cero bytes de cuerpo recibidos y código HTTP nulo. No es evidencia de caída de las fuentes.

La herramienta web permitió consultar otra vez el [catálogo CEEE](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica) y la [especificación WFS BU](https://www.catastro.hacienda.gob.es/webinspire/documentos/inspire-bu-WFS.pdf), pero no obtener muestras mediante DataStore ni WFS. El catálogo sigue ofreciendo CSV anual y ZIP históricos; no se solicitaron paquetes completos.

| Indicador solicitado | Resultado en datos oficiales |
| --- | --- |
| Registros CEEE procesados | 0 |
| Referencias de formato válido | 0 observadas; controles de checksum no ejecutados |
| Referencias confirmadas por Catastro | 0 |
| Coincidencias | No calculable: denominador cero |
| Edificios geolocalizados | 0 |
| Parcelas geolocalizadas | 0 |
| Esquemas reales contrastados | Ninguno; solo contrato y diccionario documental |
| Distrito piloto seleccionado con datos | Pendiente |

No se interpreta esto como cobertura nula de Madrid. Los Parquet vacíos generados son contratos de salida, **no un dataset real integrado**. No se han rellenado con ejemplos sintéticos.

## Trabajo implementado y comprobado

- Adaptadores CKAN, WFS CP/BU y DNPRC, con límites de volumen y sin descargas masivas.
- Normalización conservadora de RC y direcciones; conservación de originales.
- Separación de inmueble RC20, parcela RC14 y candidatos BU; pendientes explícitos.
- Conservación de ámbito certificado original, con catálogo normalizado pendiente de datos reales.
- Exportación Parquet, perfil de esquema, hashes, configuración y reproducción offline.
- 25 pruebas offline superadas, incluyendo ida y vuelta Parquet. Los datos sintéticos no aportan métricas de cobertura ni resultados reales.

Python 3.13.5, Pandas 2.3.3 y PyArrow 23.0.1 utilizados desde un entorno local que hereda paquetes preexistentes. GeoPandas no pudo instalarse; DuckDB no es necesario para esta escala. Ruff está configurado, pero no ejecutado. Ninguna instalación global fue modificada.

## Calidad: detectado y todavía no medido

**Detectado en la ejecución:** ausencia de respuestas por DNS, imposibilidad de verificar dominios de columnas, ámbitos, CRS y cobertura efectiva. El sistema informa el bloqueo y no fuerza enlaces.

**Pendiente de muestras reales:** porcentaje de RC mal formadas, controles de referencia, duplicados de certificado, nulos, tipos energéticos, valores A–G, fechas, unidades, RC múltiples, diferencias de dirección y cardinalidad parcela/bloque. No se atribuyen a las fuentes defectos observados solo en pruebas sintéticas.

## Distrito piloto

No se mantiene Usera por su relación con subvenciones. Se proponen Usera, Chamberí y Carabanchel como candidatos a comparar mediante identidades geolocalizadas, proporción de referencias confirmadas y casos ambiguos. No hay observaciones para ordenar su disponibilidad o calidad; por tanto la selección definitiva queda pendiente. La evaluación opcional del código es exploratoria sobre la muestra, no una estimación de cobertura distrital.

## Archivos generados

- `src/madrid_rehab/`: módulos de HTTP, fuentes, normalización, integración, piloto, orquestación y CLI.
- `config/sample.json`, `pyproject.toml`, `requirements.lock`, `.gitignore`.
- `tests/test_pipeline.py` y documentación de fixtures.
- `data/raw/first_run/snapshot.json`: captura vacía con errores, excluida de Git.
- `data/processed/first_run/certificate_reference_links.parquet`: cero filas, contrato tipado.
- `data/processed/first_run/building_objects.parquet`: cero filas, contrato tipado.
- [Informe automático](../reports/first_run/results.md), [métricas JSON](../reports/first_run/results.json), [manifiesto HTTP](../reports/first_run/http_manifest.json), perfiles de esquema y configuración en `reports/first_run/`.
- [Guía de ejecución](pipeline.md), este informe y actualizaciones de la documentación inicial.

## Próximo paso recomendado

Ejecutar la muestra acotada desde un entorno con resolución DNS y acceso HTTPS a los dos orígenes. No necesita paquetes municipales: mantiene un máximo de 5 MiB. Con una primera respuesta, revisar esquema y `edif_tipo` antes de completar el catálogo de ámbitos; después confirmar identidades y contrastar candidatos distritales con límites oficiales. Las descargas mayores requieren estimación y aprobación previa.
