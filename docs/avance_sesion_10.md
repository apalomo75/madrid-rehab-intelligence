# Avance y cierre de sesión 10

Sesión ejecutada el 24/10/2026 sobre el repositorio indicado. Estado inicial de Git limpio; no se han hecho commits ni push. Se han procesado archivos reales, no fixtures de producción. La sesión está implementada con las limitaciones de cobertura y revisión que se detallan; la aceptación visual permanece bloqueada.

| Fase | Resultado |
| --- | --- |
| A | 22 archivos de seis familias inventariados; todos legibles; SHA-256 y copias originales verificadas. |
| B | 216.061 filas de puente, 215.663 NDP; 207.648 filas inequívocas CP. |
| C | 3.935 órdenes 2018–2026; 1.091 confirmadas a parcela. Se excluyen 2.125 filas vacías de formato. |
| D | 11.498 licencias 2023–2026; 10.464 confirmadas; CSV/XLSX equivalentes no duplicados. |
| E | 98.032 declaraciones 2022–2026; 91.300 confirmadas; cuatro clases administrativas conservadas. |
| F | 10.712 filas PDF → 10.710 identidades; 9.928 confirmadas; consulta 24/10/2026 y obligaciones 2025/2026 diferenciadas. |
| G | Una convocatoria BOCM 2022; no hay concesiones individuales disponibles. |
| H | 124.175 eventos únicos; 112.783 confirmados; 5.711 contradictorios, 148 ambiguos, 36 candidatos y 5.497 sin correspondencia. |
| I | 49.855 parcelas con eventos, resúmenes por fuente/año/distrito, contextos energéticos/constructivos y perfiles descriptivos. |
| J | Pestaña administrativa municipal/distrital, filtros, series, CSV, capa de celda y ficha CP/BU. AppTest correcto; navegador bloqueado. |
| K | 229 pruebas completas correctas, Ruff y formato correctos, reproducción e integridad verificadas. |

Los perfiles son observaciones con reglas transparentes y fechas; no hay diagnóstico actual, recomendación comercial, índice global ni necesidad financiera inferida. Los casos sin evidencia permanecen en el universo CP; las referencias candidatas no se dibujan como confirmadas.

## Evidencia cuantitativa y productos finales

Captura: `data/processed/administrative_events/session_10_final_01/`. Perfiles: `data/processed/administrative_profiles/session_10_final_01/`. Reproducción: `data/processed/administrative_events/session_10_final_replay_01/`. Originales de contenido único en `data/raw/administrative/`. Todos están ignorados en Git.

Informe principal, con inventario completo y cobertura de los 21 distritos: [sesión 10](sesion_10_integracion_administrativa.md). [Puente](auditoria_matching_callejero.md), [diccionario](diccionario_eventos_administrativos.md), [calidad e indicadores](calidad_eventos_rehabilitacion.md) y [visor](visor.md).

Datos disponibles no equivale a eventos integrados: 15 archivos aportan eventos; dos CSV aportan el puente; dos CSV de vías son metadatos; dos XLSX urbanísticos verifican equivalencia de formatos; un PDF es normativa de convocatoria. No se cuentan 22 fuentes independientes.

De los 11.392 eventos sin vínculo inequívoco, 7.358 tienen distrito declarado o candidato del puente; 4.034 carecen de distrito. Un territorio de puente contradictorio no se anuncia como ubicación validada. Fuera de Madrid: no determinable con estos archivos; ausencia de RC en CP no prueba otro municipio.

Los 5.323 desacuerdos literales entre NDP y dirección de licencias/declaraciones se conservan en cola de revisión. Podrían incluir cambios de numeración, calificadores y errores; no se resuelven con fuzzy matching. Los años 2018–2023 de órdenes conservan 2.725 registros no localizados inequívocamente; las 1.210 órdenes de 2024–2026 permiten 1.091 confirmaciones. Se conservan todas las órdenes, sin eliminar por dirección repetida.

## Pruebas e integridad

- Baseline antes de modificar código: **195 pruebas**, correctas en 143,171 s.
- Suite final: **229 pruebas**, correctas en 141,354 s; sin omisiones. Log `reports/session_10/final_tests.log`.
- Incluye parsing CSV CP1252/UTF-8, XLSX XML/celdas dispersas/fórmulas inertes, extracción PDF, fechas inválidas, direcciones incompletas, conflictos y ambigüedades NDP/CP, multirreferencia, duplicidad de formatos, órdenes/periodos, estados administrativos, ausencia de ayudas, manifiestos y copias, CSV seguro, caché, filtros vacíos, selección CP, construcción de capa PyDeck, perfiles y regresión municipal/piloto. Los contratos históricos conservan pruebas de concesiones con RC/fases; no hay ayudas sintéticas en datos reales.
- `ruff check src tests` y formato de módulos nuevos/modificados, correctos.
- **47 Parquet finales idénticos byte a byte**, además del manifiesto de entradas y el manifiesto de captura; `reports/session_10/final_reproducibility.json`.
- **288 archivos protegidos anteriores** y **22 originales externos** comprobados por hash, ninguno modificado; `reports/session_10/final_integrity.json`.

La duración de suites distintas con cachés y carga concurrente no es una medición causal del impacto de la interfaz. Las pruebas de caché confirman ausencia de relectura Parquet caliente; el benchmark original sigue verificando las 21 particiones.

## Rendimiento

Captura final: inventario 23,134 s; normalización 15,108 s; puente/matching 24,749 s; analítica 2,239 s; total **65,755 s**, RSS máxima aproximada **2.032,1 MiB**. El checkpoint optimizado anterior tardó 58,926 s. Medidas reales de proceso, no promesa de latencia multiusuario.

Los seis distritos de contraste leen una partición pública de 2.545–10.461 eventos, 3,45–14,04 MiB; el primer benchmark administrativo midió 0,015–0,076 s con comprobación de hash, y copias de caché 0,0035–0,0177 s. Resultados finales en `reports/session_10/final_view_benchmark.json`; no se interpreta la lectura como tiempo de renderizado WebGL.

El benchmark de vistas originales está en `reports/session_10/original_views/viewer_benchmark.json`: portada verificada 0,0442 s; caché mediana 0,00097 s y cero lecturas calientes. Se conservan los 21 distritos y el límite cartográfico. Los perfiles se preparan fuera de Streamlit; la portada administrativa solo carga agregados, y el detalle una partición distrital cacheada. No hay base de datos externa ni descarga de red.

## Incidencias resueltas y pendientes

Se preservan las tentativas incompletas `session_10` (interrumpida para optimizar índices) y `session_10_final` (tipado de página PDF corregido), así como checkpoints `session_10_audited`/`session_10_release`. No son entradas vigentes. La versión final valida tipos, equivalencia y contradicciones y se ha reproducido desde los originales.

`openpyxl` no pudo instalarse por DNS. Se usa XML XLSX de biblioteca estándar, con límites de expansión; no es dependencia pendiente. Poppler `pdftotext` 24.02.0 está disponible. No se ejecutan fórmulas, macros, enlaces ni instrucciones de documentos. Dos avisos de ligaduras del PDF no impidieron extracción de tablas; texto y páginas quedan auditables. No hay archivos corruptos pendientes.

Faltan concesiones PRTR estructuradas con fase, expediente, importe, inmueble y fecha; el BOCM de convocatoria no las sustituye. Licencias de reutilización, fechas de descarga y periodicidades no acreditadas permanecen desconocidas. No se hicieron nuevos intentos de red para obtener registros faltantes.

**Validación visual bloqueada**, evidenciada en `reports/session_10/server_attempt.log`: `PermissionError: Operation not permitted` al crear socket. AppTest acredita construcción/lógica y capa serializable, no clic real, teselas, cámara, leyendas ni legibilidad.

Comando local:

```bash
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Revisión manual necesaria: abrir Madrid y distritos, seleccionar celda/CP/BU, alternar filtros y capas administrativas, contrastar ficha y CSV, comprobar ausencia de afirmaciones de diagnóstico/ejecución, repetir offline y conservar el funcionamiento energético anterior. La tarea no se presenta como validada visualmente.
