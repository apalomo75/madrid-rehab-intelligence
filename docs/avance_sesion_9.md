# Avance y cierre de sesiones 7.1–9

Fecha: 23/10/2026. Estado: navegación y preparación de contratos implementadas; **sesión 9 en escenario D, integración de nuevas evidencias no conseguida**. La sesión 8 no adquirió registros reales. No se declara éxito de adquisición ni aceptación visual.

## Evidencia inicial y preservación

Estado Git inicial con cambios de sesiones anteriores, preservados. Baseline: 174 pruebas unittest/AppTest correctas en 83,322 s antes de editar código. No había productos/documentos de sesión 8. Se revisaron contratos de eventos, arquitectura, fuentes y visor municipal. No commits, push ni publicación.

Control SHA-256: **373 archivos protegidos sin cambios**, incluidos originales y productos de sesiones 1, 2, 6 auditada y 7 final. Detalle en `reports/session_9/protected_before.json` y `protected_verification.json`. No se regeneraron ni editaron esos productos.

## Entregado

- Recorrido Madrid → distrito completo → zona por ID → CP/BU, vuelta y búsqueda; filtros organizados/reset y fichas por secciones. Selector técnico secundario y leyenda municipal. [Sesión 7.1](sesion_7_1_usabilidad.md).
- Investigación de ITE/IEE, inspecciones urbanísticas, PRTR y BDNS; inventario, límites y adquisición reproducible. **0 registros nuevos**. [Sesión 8](sesion_8_fuentes_oficiales.md).
- Contratos separados de tipos/fases y adaptador territorial de esquema urbanístico 2019; fixtures solo en tests. Informe del escenario D con cobertura nula/desconocida, no eventos vacíos de producción. [Sesión 9](sesion_9_integracion.md).

## Validación

Primer cierre: 194 pruebas correctas en 116,138 s (`reports/session_9/tests_final.log`), incluidas las 174 anteriores sin eliminar aserciones. Se añadió después una regresión de XLSX truncado: resultado de aceptación final al pie. Ruff y formato de los diez archivos editados/nuevos comprobados. `git diff --check` correcto.

AppTest recorre los 21 distritos y prueba el nuevo recorrido de Chamberí, Tetuán y Vicálvaro, filtros principales/avanzados, vacíos, reset, retorno y contadores. Pruebas Python verifican selección por ID, callback obsoleto, CRS/ejes/bordes, CSV y estilo OSM/local; contratos, privacidad, captura, fechas, importes, esquemas, duplicados e idempotencia. La auditoría del escenario D produce informes iguales y Parquet byte a byte idénticos en dos salidas temporales. No mide calidad de matching sobre fuentes que no se han obtenido.

**Navegador bloqueado:** Streamlit falla al crear socket con `PermissionError: [Errno 1] Operation not permitted`; evidencia `reports/session_7_1/server_attempt.log`. No se lanzaron reintentos indefinidos ni se fabricaron capturas. Picking real, alineación, contraste, portátil, OSM y fluidez visual pendientes. AppTest no los acredita.

## Rendimiento real local

`tests/benchmark_session71.py`: mallas de Chamberí/Tetuán/Vicálvaro de 29/29/156 zonas, JSON 22.921/24.563/120.217 bytes; preparación 0,0016–0,0027 s. La primera serialización incluye inicialización (0,277 s); posteriores 0,0027–0,0036 s. No son latencias de navegador.

`tests/benchmark_session7.py --report-dir reports/session_9`: portada 0,0224 s; caché mediana 0,00050 s; cero lecturas Parquet calientes; JSON 251.893 bytes. 21 distritos: carga 0,055–0,175 s, filtrado 0,055–0,213 s y serialización de detalle 0,029–0,076 s; JSON de celdas 0,72–2,44 MB. RSS pico 561,6 MiB. Ejecución local con caché de sistema no vaciada; no garantiza concurrencia/GPU/red. Archivos `viewer_benchmark.json` y `reports/session_7_1/benchmark.json`.

## Pendiente externo

Descargar recursos oficiales fuera del entorno con DNS, revisar valores y licencia, obtener exportación reutilizable ITE/IEE/PRTR y verificar geografía de la actuación. Luego auditar calidad, fase, alcance, duplicidades y correspondencia CP antes de integrar. Hoy no existen nuevos indicadores de conservación, inspecciones o ayudas, ni capas administrativas verificadas.

Para iniciar y lista corta de comprobaciones manuales: [sesión 7.1](sesion_7_1_usabilidad.md). Comandos de adquisición, auditoría y pruebas en README y sesiones 8/9.

## Resultado final de aceptación

```text
Ran 195 tests in 110.515s

OK
```

195 pruebas: las 174 anteriores y 21 nuevas. Log `reports/session_9/acceptance_tests.log`. Ruff correcto, diez archivos con formato correcto y `git diff --check` sin incidencias. Sin commits ni push.
