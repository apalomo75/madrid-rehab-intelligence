# Sesión 10 — integración administrativa real

Se han inventariado **22 archivos** de las seis familias, preservados sin modificación. Git no se ha confirmado ni enviado. La suite inicial tenía 195 pruebas correctas. Los productos históricos CP/BU/CEEE y los 21 distritos se conservan.

## Datos disponibles, integrados y vinculados

**Disponibles:** cuatro CSV de callejero, dos parejas CSV/XLSX administrativas, nueve XLSX de órdenes, cuatro PDF de obligaciones y un PDF BOCM. Todos se leen correctamente. **Integrados:** 124.175 identidades administrativas de 124.177 filas con datos, después de conservar dos publicaciones nulas repetidas en trazabilidad; no se duplica la pareja CSV/XLSX. **Vinculados:** 112.783 eventos en 49.855 parcelas CP únicas. **Sin vínculo inequívoco:** 11.392; 7.358 tienen distrito declarado o candidato de puente y 4.034 no tienen distrito. Un distrito inferido de un puente contradictorio sigue siendo candidato territorial.

| Fuente | Filas con datos | Normalizadas únicas | Confirmadas CP | Tasa | Contradictorias | Ambiguas | Candidatas | Sin vínculo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Declaraciones | 98032 | 98032 | 91300 | 93.13% | 4821 | 100 | 33 | 1778 |
| IEE pendientes | 5758 | 5758 | 5299 | 92.03% | 284 | 11 | 0 | 164 |
| ITE pendientes | 4954 | 4952 | 4629 | 93.48% | 77 | 16 | 0 | 230 |
| Licencias | 11498 | 11498 | 10464 | 91.01% | 518 | 21 | 3 | 492 |
| Órdenes | 3935 | 3935 | 1091 | 27.73% | 11 | 0 | 0 | 2833 |

Hay 148 casos `ambiguous`, 5.711 `contradictory`, 36 `candidate` y 5.497 `unmatched`. No hay NDP multiparcela en esta captura; sí direcciones multiparcela. Estas categorías no acreditan edificios físicos. Cobertura de fuentes desconocida: no se puede declarar que los no vinculados estén fuera del municipio.

## Inventario completo

Ruta raíz original: `/mnt/c/Users/apalo/Downloads/Mapas Rehab`. La organización real añade `Madrid/`; las carpetas tienen variantes de acentos y espacios. El inventario JSON conserva ruta absoluta, nombre, bytes, formato, mtime UTC, SHA-256, cabeceras, muestras, hojas/páginas, años observados, fecha de consulta y limitaciones. mtime no prueba descarga. Licencias de reutilización y fecha de descarga no acreditadas: permanecen nulas.

| Archivo (ruta relativa a Mapas Rehab) | Bytes | Formato | Filas u hojas/páginas | Periodo comprobado |
| --- | ---: | --- | --- | --- |
| Madrid/Callejero/200075-1-callejero-csv.csv | 96166309 | .csv | 215618 filas; 1 hoja(s) | Corte de callejero sin fecha acreditada |
| Madrid/Callejero/213605-0-callejero-oficial-madrid-csv.csv | 625467 | .csv | 11113 filas; 1 hoja(s) | Corte de callejero sin fecha acreditada |
| Madrid/Callejero/213605-3-callejero-oficial-madrid-csv.csv | 643672 | .csv | 11113 filas; 1 hoja(s) | Corte de callejero sin fecha acreditada |
| Madrid/Callejero/213605-4-callejero-oficial-madrid-csv.csv | 34705052 | .csv | 214676 filas; 1 hoja(s) | Corte de callejero sin fecha acreditada |
| Madrid/Declaraciones responsables/133556-0-declaraciones-responsables.csv | 17433974 | .csv | 98032 filas; 1 hoja(s) | 2022, 2023, 2024, 2025, 2026 |
| Madrid/Declaraciones responsables/133556-1-declaraciones-responsables.xlsx | 7408452 | .xlsx | 98032 filas; 1 hoja(s) | 2022, 2023, 2024, 2025, 2026 |
| Madrid/Licencias urbanísticas/640505-0-licencias-urbanisticas-otorgadas.xlsx | 1291290 | .xlsx | 11498 filas; 1 hoja(s) | 2023, 2024, 2025, 2026 |
| Madrid/Licencias urbanísticas/640505-1-licencias-urbanisticas-otorgadas.csv | 2921075 | .csv | 11498 filas; 1 hoja(s) | 2023, 2024, 2025, 2026 |
| Madrid/Pendientes de presentar ITE  IEE/IEE2025.pdf | 223501 | .pdf | 47 páginas | 2025 |
| Madrid/Pendientes de presentar ITE  IEE/SGiteInforme.pdf | 365455 | .pdf | 116 páginas | 2026 |
| Madrid/Pendientes de presentar ITE  IEE/SGiteInformeIEE.pdf | 401684 | .pdf | 136 páginas | 2026 |
| Madrid/Pendientes de presentar ITE  IEE/SGiteInformeITEE_2025.pdf | 212700 | .pdf | 41 páginas | 2025 |
| Madrid/Subv/rehab_fe_edif_bocm-20220531-28.pdf | 105092 | .pdf | 3 páginas | Convocatoria 2022 |
| Madrid/Órdenes de ejecucion/300377-0-conservacion-rehabilitacion-xlsx.xlsx | 36212 | .xlsx | 656 filas; 1 hoja(s) | 2022 |
| Madrid/Órdenes de ejecucion/300377-1-conservacion-rehabilitacion-xlsx.xlsx | 56940 | .xlsx | 1226 filas; 1 hoja(s) | 2024 |
| Madrid/Órdenes de ejecucion/300377-2-conservacion-rehabilitacion-xlsx.xlsx | 55215 | .xlsx | 1218 filas; 1 hoja(s) | 2025 |
| Madrid/Órdenes de ejecucion/300377-3-conservacion-rehabilitacion-xlsx.xlsx | 32951 | .xlsx | 547 filas; 1 hoja(s) | 2021 |
| Madrid/Órdenes de ejecucion/300377-4-conservacion-rehabilitacion-xlsx.xlsx | 19970 | .xlsx | 260 filas; 1 hoja(s) | 2019 |
| Madrid/Órdenes de ejecucion/300377-5-conservacion-rehabilitacion-xlsx.xlsx | 20530 | .xlsx | 288 filas; 1 hoja(s) | 2018 |
| Madrid/Órdenes de ejecucion/300377-7-conservacion-rehabilitacion-xlsx.xlsx | 30515 | .xlsx | 530 filas; 1 hoja(s) | 2023 |
| Madrid/Órdenes de ejecucion/300377-8-conservacion-rehabilitacion-xlsx.xlsx | 28044 | .xlsx | 444 filas; 1 hoja(s) | 2020 |
| Madrid/Órdenes de ejecucion/300377-9-conservacion-rehabilitacion.xlsx | 40504 | .xlsx | 891 filas; 1 hoja(s) | 2026 |

Los XLSX de órdenes contienen 6.060 filas estructurales: **2.125 están vacías** (731 en 2024, 766 en 2025 y 628 en 2026); quedan 3.935 registros. Distribución anual: 2018 288; 2019 260; 2020 444; 2021 547; 2022 656; 2023 530; 2024 495; 2025 452; 2026 263. La numeración de orden es ordinal de publicación y presenta repeticiones; no se vende como ID de expediente. Se conservan año, periodo, dirección, motivo y fila original. No se infiere vigencia actual.

Las parejas CSV/XLSX son equivalentes en todos los campos no formateados de fecha y en los componentes oficiales año/mes/día. Solo se incorpora CSV a eventos; los dos formatos originales y sus tablas quedan preservados. El CSV de declaraciones contiene cuatro categorías, no solo obras residenciales: 61.212 residencial, 34.863 actividad, 1.633 primera ocupación y 324 funcionamiento. Las licencias contienen 11.498 resoluciones «Conceder», con nueve categorías administrativas. El uso residencial no permite identificar rehabilitación; la categoría queda no determinada cuando falta objeto de obra.

PDF: 1.455 filas IEE 2025, 4.303 IEE 2026, 1.275 ITE 2025 y 3.679 ITE 2026. Consulta explícita 24/10/2026 en todos. Los tres nulos repetidos ITE se conservan en publicaciones, con una identidad no localizable; no permiten contar edificios distintos. No hay OCR ni corrección de numeraciones. Hay 298 numeraciones extraordinarias y 81 diferencias entre año de inspección y obligación (16 comparten ambos problemas). Esas filas quedan fuera de confirmación y en revisión. No hay resultados favorables/desfavorables.

## Cobertura territorial

Conteos de expedientes/obligaciones observados; las parcelas solo incluyen relaciones confirmed. Los no confirmados pueden tener distrito candidato, que no debe presentarse como localización confirmada. No son tasas de edificios afectados.

| Distrito | Eventos observados | Confirmados a CP | Parcelas distintas confirmadas | Sin vínculo inequívoco |
| --- | ---: | ---: | ---: | ---: |
| Sin distrito | 4034 | 0 | 0 | 4034 |
| 01 | 10461 | 10361 | 4104 | 100 |
| 02 | 4538 | 4245 | 1556 | 293 |
| 03 | 4555 | 4442 | 1403 | 113 |
| 04 | 10068 | 9906 | 3196 | 162 |
| 05 | 7430 | 7148 | 2728 | 282 |
| 06 | 7412 | 7248 | 2928 | 164 |
| 07 | 8264 | 8151 | 2665 | 113 |
| 08 | 7167 | 6054 | 2910 | 1113 |
| 09 | 6976 | 6253 | 3254 | 723 |
| 10 | 6224 | 5983 | 3300 | 241 |
| 11 | 6844 | 6630 | 3694 | 214 |
| 12 | 3279 | 3141 | 1769 | 138 |
| 13 | 5262 | 4966 | 2863 | 296 |
| 14 | 2013 | 1670 | 734 | 343 |
| 15 | 7347 | 7101 | 3230 | 246 |
| 16 | 6729 | 5687 | 2785 | 1042 |
| 17 | 3257 | 2884 | 1488 | 373 |
| 18 | 2955 | 2671 | 1215 | 284 |
| 19 | 2545 | 2330 | 1250 | 215 |
| 20 | 4507 | 3963 | 1958 | 544 |
| 21 | 2308 | 1949 | 825 | 359 |

## Productos y arquitectura

`administrative_io.py` lee CSV UTF-8/CP1252, celdas XML XLSX y PDF de texto mediante `pdftotext -layout`. No evalúa fórmulas ni ejecuta macros. `administrative.py` inventaría, copia por hash, normaliza, construye puente y eventos, deduplica publicaciones, audita y particiona. `administrative_audit.py` genera perfiles descriptivos y auditoría territorial adicional. `administrative_view.py` verifica productos, carga agregados municipales pequeños y una sola partición distrital con caché.

Captura vigente: `data/processed/administrative_events/session_10_final_01/`. Copias originales: `data/raw/administrative/<sha256>/`; conservan nombre/procedencia en manifiesto, sin repetir contenido idéntico. Las tentativas `session_10`, `session_10_final` y checkpoints `session_10_audited`/`session_10_release` se conservan separados; no son la entrada vigente. Las rutas data y reports ya están ignoradas en Git.

Productos: manifiesto de archivos y hash CP; puente NDP; tablas completas por original; eventos; publicaciones; resumen distrital y temporal; contexto constructivo/energético observado; perfiles CP; cola de revisión; particiones `districts/XX/events.parquet` y `unknown`. Los perfiles descriptivos adicionales están en `data/processed/administrative_profiles/session_10_final_01/`, con reglas y procedencia propias. No se añaden eventos a los contratos históricos de resultados ITE/IEE ni se modifica sesión 7 para fingir simultaneidad de capturas.

La pestaña «Actividad y rehabilitación» aparece en municipio y distrito. Ofrece filtros por fuente, tipo, año, categoría, vínculo y estado, tabla pública, CSV neutralizado, conteos diferenciados y series. El municipio elige distrito para detalle, sin cargar los 124.175 eventos. Las fichas CP/BU muestran eventos de la parcela, con alcance explícito. Las capas opcionales usan solo confirmed, una celda y máximo 2.500 geometrías; no añaden eventos territoriales a parcelas. Los perfiles energéticos previos siguen separados.

## Reproducción

Dependencias Python existentes, sin cambios de manifiesto ni lockfile. Requisito externo: Poppler `pdftotext` (comprobado 24.02.0). En Ubuntu, instalación del sistema si falta: `sudo apt-get install poppler-utils`. No se pudo instalar openpyxl por DNS; no es necesario para este parser.

```bash
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m madrid_rehab.administrative \
  --output-dir data/processed/administrative_events/replay_nuevo \
  --report-dir reports/session_10/replay_nuevo
PYTHONPATH=src .venv/bin/python -m madrid_rehab.administrative_audit \
  --input-dir data/processed/administrative_events/session_10_final_01 \
  --output-dir data/processed/administrative_profiles/replay_nuevo \
  --report-dir reports/session_10/audit_replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_administrative.py -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python tests/benchmark_administrative.py --output reports/session_10/benchmark_nuevo.json
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Usar siempre salidas nuevas. `--source-dir` permite otra carpeta y `--raw-dir` otro almacén. `MADRID_REHAB_ADMIN_DIR` selecciona una captura administrativa alternativa; el visor contrasta su hash CP con el manifiesto municipal vigente. `MADRID_REHAB_SESSION7_DIR` conserva su uso anterior. No hay red en el pipeline ni base de datos externa.

## Rendimiento, validación y límites

Primera generación completa optimizada: 58,93 s (inventario 18,58; normalización 14,25; puente/matching 22,22; analítica 3,34); RSS máxima 2.031,7 MiB. Lectura verificada de seis distritos: 0,015–0,076 s, copias desde caché 0,0035–0,0177 s; frames públicos 3,45–14,04 MiB. El benchmark demuestra cero relecturas calientes en prueba. No mide GPU, navegador ni concurrencia. Los logs y benchmarks finales se conservan bajo `reports/session_10/`.

Suite final: **229 pruebas correctas**; captura final 65,755 s y RSS 2.032,1 MiB; 47 Parquet y manifiestos idénticos en replay. La suite ampliada y la reproducción final se detallan en [avance](avance_sesion_10.md). Las pruebas municipales conservan regresiones de 21 distritos y Chamberí. Se verifican hashes de 288 archivos históricos y originales externos. Los benchmarks originales se ejecutan en directorio nuevo; no se proclama mejora de velocidad a partir de cargas distintas ni del estado de caché del sistema.

**Validación visual bloqueada:** intento real de Streamlit falla con `PermissionError: Operation not permitted` al abrir socket; `reports/session_10/server_attempt.log`. AppTest no acredita clic WebGL, leyenda, contraste ni fluidez. Revisión manual pendiente: municipio → distrito → celda → CP/BU; filtros administrativos vacíos/combinados; activar capas de cada tipo; comprobar ficha y CSV; repetir offline y revisar que continúan filtros energéticos y navegación.

## Subvenciones y pendientes

El único archivo Subv es el extracto de la convocatoria Orden 1429/2022, BOCM 31/05/2022. No hay concesiones, pagos ni geometrías PRTR; no se importan beneficiarios ni importes presupuestados como ayudas individuales. Falta exportación estructurada del visor con expediente, programa, fase, importe concedido, fecha y referencia/dirección del inmueble subvencionado, licencia y fecha de corte. El contrato reutilizable de `events.py` conserva verificación CP y separación de municipios/fases. No se han hecho descargas reiteradas ni intentos de eludir acceso.

Quedan para revisión las discrepancias NDP/dirección, las referencias ausentes/ambiguas, los números PDF y las órdenes antiguas no vinculables inequívocamente. Tampoco se puede acreditar exhaustividad territorial o periodicidad desconocida. No hay recomendaciones comerciales automáticas, índice opaco, diagnósticos actuales ni necesidad financiera inferida.
