# Cobertura municipal — corte 24/10/2026

**Actualización sesión 12.1:** el GeoPackage oficial ya está integrado: 179 municipios validados, 7.532 PRTR territorializados (3.808 Madrid y 3.724 externos). Solo Madrid tiene CP/BU integrado. [Fuente, catálogo, criterios, importes y pendientes vigentes](sesion_12_1_limites_prtr.md). El contenido de sesión 12 que sigue es histórico; su bloqueo de adquisición de límites queda superado.

**Inventario catastral de 179 municipios; no cobertura catastral regional de 179 municipios.**

| Grupo | Catálogo/recursos | Límite oficial municipal en producto regional | CP procesado | BU procesado | PRTR municipal | CEEE/eventos |
| --- | --- | --- | --- | --- | --- | --- |
| Madrid capital | INE 28079 confirmado; Catastro 28900 | No incorporado al nuevo catálogo; 21 distritos históricos disponibles | Sí: 140.595 RC14; 141.244 filas | Sí: 124.396 objetos | 3.805 expedientes por CP | Capturas históricas de Madrid |
| Otros 178 recursos municipales | Nombre y código Catastro oficiales; correspondencia INE completa pendiente | No | No | No | Asignación pendiente, no cero ayudas | CEEE sin cobertura validada; eventos no integrados |

Los cinco candidatos Getafe, Móstoles, Alcorcón, Leganés y Alcalá de Henares tienen enlaces oficiales CP/BU en feeds; las diez comprobaciones de acceso fallaron por DNS. Estado: localizado, sin descarga nueva, sin procesamiento y sin validación geométrica real. El escalado está detenido antes del piloto, no tras un supuesto piloto correcto.

`data/processed/territory/session_12_final_01/coverage.parquet` conserva una fila por recurso municipal: `cadastre_code`, literal oficial catastral, INE si está confirmado, estado de correspondencia, límites, CP/BU, CEEE, eventos y asignación PRTR. Es un **snapshot de esta sesión**, no un descubridor automático de nuevas particiones. `cadastre_resources.parquet` conserva las URLs, fechas y derechos de ambos feeds. Solo los productos futuros con manifiesto validado habilitan fichas CP externas en el visor; la ruta de Madrid permanece histórica.

`data/processed/grants/regional/session_12_final_01/municipality_program_summary.parquet` conserva un grupo residual desconocido. Suma: 7.532 expedientes y 315.527.338,99 €. Madrid confirmado: 3.805 y 126.328.673,63 €. Residuo: 3.727 y 189.198.665,36 €. No se distribuye ese residuo por direcciones textuales. No hay tabla real de importes por los 178 municipios externos todavía.

Cero contradicciones espaciales observadas **no significa cero contradicciones reales**: no se pudieron evaluar sin límites. Tampoco se conocen los recuentos limítrofes ni exteriores. Los 7.532 estados territoriales espaciales son `boundaries_unavailable`; en una columna independiente permanecen las 3.805 confirmaciones por CP. Matching: 3.809 relaciones confirmadas históricas, tres ambiguas históricas y 3.749 sin cobertura CP regional confirmada.

Concesión no significa pago/ejecución. Las relaciones representan parcelas, no edificios físicos ni viviendas. No se extienden las licencias ni otros eventos del Ayuntamiento de Madrid al resto de municipios. La ausencia de CEEE integrado significa cobertura pendiente, no inexistencia de certificado. PRTR está deshabilitado en modo público hasta verificar licencia.

Informes: `reports/session_12/audit_final_01/quality.json`, `municipality_program_summary.csv`, `network_audit.json` en el directorio superior, benchmark y pruebas. Los informes públicos de cobertura no incluyen direcciones ni identificadores de expedientes; los productos de detalle permanecen locales bajo `data/` ignorado.
