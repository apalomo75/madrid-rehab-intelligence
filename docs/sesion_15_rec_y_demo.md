# Sesión 15 — REC, auditoría y demostración

Base comprobada: `ebe1e36 — feat: integrate conservation evidence and REC groundwork`, árbol inicialmente limpio. Sin commits, push, publicación, reingestas masivas ni modificaciones de originales, snapshots o cuarentenas. Fecha de revisión: 26/10/2026.

## Resultado independiente de los entregables

**A — Estado B:** consulta individual municipal pública documentada, patrón POST/NDP y reutilización automatizada sin acreditar. El proceso local está bloqueado en DNS; no se alcanzó HTTPS ni hubo código HTTP. Cero consultas de fichas, cero dictámenes ITE/IEE incorporados. El NDP manual mantiene correspondencia de dirección histórica, pero no CP urbana confirmada. No hay permiso acreditado para ampliación por lotes. RIEECM sigue anunciado como próximo dataset y su aviso legal restringe reproducción comercial. Véase [acceso, evidencia, diagnóstico y propuesta institucional no enviada](rec_acceso_y_escala.md).

**B — MVP parcialmente funcional, con revisión humana pendiente:** nueva entrada de demostración real con búsqueda municipio/RC14, candidatos explicables, seis apartados de ficha, geometría CP y exportación HTML reducida. Convive con Analista. No hay buscador regional de direcciones, selección cartográfica de parcela en demo, exportación completa de evidencias ni PDF. No se afirma aceptación visual: servidor y Chromium bloqueados por permisos locales. [Guion y casos](demo_uci.md), [revisión pendiente](auditoria_visual_pendiente.md), [licencias](licencias_demo.md).

## Protección y arquitectura revisadas

Se leyeron AGENTS, README, fuentes/conservación y modelos anteriores. Entrada real: `app.py`, salvo piloto histórico; deriva a `city_app.py`, con navegación Madrid/distrito/celda/parcela y `regional_view.py`. CEEE, PRTR y conservación poseen lectores selectivos y cierres `MADRID_REHAB_PUBLIC`. La demo incorpora su propio cierre antes de leer evidencia y reutiliza lectores energéticos y de conservación; no consulta REC en arranque.

Snapshots utilizados: límites `territory/session_12_1_final_01`, energía `energy/session_13_final_03`, conservación `conservation/session_14_final_02`, pilotos **parciales** `cadastre/session_12_2_partial_validated_01`, CP Madrid `session_2/parcels_audited.parquet`. No se activa el snapshot parcial como cobertura completa. Se verifican hashes antes de leer productos nuevos a caché. Se rechazan CP no únicas/no utilizables y no se crean relaciones BU.

Dependencias disponibles, sin instalación adicional: Python 3.13, Streamlit 1.50.0, Pandas 2.3.3, PyArrow 23.0.1, Shapely 2.1.2, PyProj 3.7.2, Ruff 0.14.2, Playwright 1.56.0. Manifiestos de dependencias existentes conservados.

## Componentes y correcciones

- `demo.py`: portada, selección real de municipio, búsqueda RC14, filtros CEEE/PRTR/letras EFG/órdenes, ficha en seis pestañas y exportación HTML de identificación. Selección expresa de candidato, sin ranking ni diagnóstico.
- `rec_diagnostic.py`: solo GET de portada, sesión propia, clasificación DNS/TLS/HTTP/redirección, formularios sin tokens, límites de tamaño/tiempo y salida nueva. No hay recolector ni POST de registros.
- `demo_audit.py`: reproducción de casos, integridad de productos y métricas de lectura/exportación.
- `tests/browser_session15.py` y `tests/benchmark_session15.py`: comprobación reproducible de navegador y rendimiento Python.
- Mensaje de conservación corregido para expresar resultado ITE/IEE no disponible; evita interpretar ausencia como dictamen.
- Contador energético usa 136.742 contenidos distintos de la auditoría, en lugar de sumar membresías municipales potencialmente repetidas.
- El modo público oculta también accesos rápidos cuyo texto revelaría coexistencia PRTR.

Las fichas conservan la ausencia de año/dirección cuando no hay verificación suficiente. Las fechas energéticas no se convierten en vigencia; las letras de viviendas no califican CP/BU. Ayudas no se presentan como pagos, y no se muestran importes en demo. La ficha reducida no incluye datos restringidos ni personales y advierte que no es certificación.

## Casos reales

| Municipio | RC14 | Comprobado |
|---|---|---|
| Madrid | `0010510VK4701A` | CP única, 4 contenidos CEEE individuales, 2 órdenes, 1 acceso documental |
| Alcalá | `0015301VK7801N` | CP aceptada, 1 contenido CEEE y 1 expediente PRTR vinculado |
| Getafe | `0036104VK4603N` | CP aceptada, 2 contenidos CEEE, cobertura parcial |

Ninguno dispone de dictamen REC integrado. Detalles, alcance, fechas y ausencias en guía y auditoría local; sin nombres personales. Las cinco particiones piloto tienen prueba de consulta de CP real. Municipio sin CP: La Acebeda. Ausencias energéticas y de conservación se prueban sin fabricar favorabilidad.

## Validación ejecutada

1. Inicial focalizada: **40/40 conservación**, incluidas 20 del parser REC con fixtures sintéticas.
2. Nueva batería focalizada: **14/14**, casos reales, cinco pilotos, ausencia de CP/energía/conservación, público, exportación, navegación y diagnóstico de red/permisos.
3. Suite completa: **426 pruebas en 261,585 s; 425 correctas y una aserción de texto desactualizada** en conservación tras corregir el mensaje de ausencia. Se actualizó esa aserción y se ejecutaron **40/40 de conservación** nuevamente, en 3,968 s. No se repitió toda la suite por un cambio menor de texto. No se presenta el primer comando completo como verde.
4. Ruff `check src tests`: correcto. Formato de todos los archivos modificados/nuevos: correcto. `format --check src tests` identifica **7 incumplimientos preexistentes**, comprobados también contra HEAD: cli.py, http.py, integrate.py, pilot.py, pipeline.py, sources.py y test_pipeline.py. No se reformatea código ajeno a la sesión.
5. Integridad: **1.088 entradas de archivo/manifiesto verificadas**, sin discrepancias, en 1,908 s; incluye límites, CP parcial/cuarentenas, energía, conservación, eventos, PRTR y particiones de los 21 distritos. La prueba histórica de diez recursos catastrales reales también terminó `ok` en la suite completa.
6. Navegador: **bloqueado**, cero casos de navegador y sin capturas válidas. AppTest no sustituye esta validación.

Los escenarios pendiente/archivado, NDP sin CP y múltiples candidatos siguen cubiertos por pruebas anteriores, sin modificar reglas de identidad. La nueva prueba de permiso REC usa un contrato sintético; no acredita permiso municipal real. La sesión ausente no pudo probarse contra portal: sigue desconocida. No existe HTML real para validar parser, por lo que no se cuenta como prueba real superada.

## Rendimiento medido

| Operación | Medición |
|---|---|
| Portada, ejecución Python AppTest | 2,070 s |
| Seleccionar caso y ficha, AppTest | Madrid 1,653 s; Alcalá 0,225 s; Getafe 0,225 s |
| Lectura fría de ficha y evidencia | 1,141 / 0,103 / 0,098 s |
| Lectura repetida en caché | 0,004–0,006 s |
| Generación HTML reducido | 0,0002–0,0003 s |
| RSS máxima del benchmark AppTest | 600,3 MiB, proceso completo |
| RSS máxima de auditoría Python | 544,2 MiB, incluye verificación de integridad |

No son tiempos percibidos por usuario. Arranque real del servidor, selección por clic, WebGL, descarga real y memoria del servidor permanecen sin medir por bloqueo. Se consulta una CP y certificados selectivos; los índices de candidatos contienen referencias/atributos, no centenares de miles de geometrías. No hubo optimización especulativa ni cambio de arquitectura.

## Productos y reproducción

- Inventario mantenido: `config/session15_sources.json`.
- Diagnóstico: `data/raw/rec/session_15_diagnostic_01/manifest.json` (sin bytes HTML nuevos).
- Auditoría válida: `reports/session_15/audit_02/`: `audit.json`, `historical_integrity.json`, tres HTML reducidos y `manifest.json`. `audit_01` fue un intento incompleto por nombre de manifiesto PRTR diferente; no se sobrescribió ni se considera resultado válido.
- Rendimiento: `reports/session_15/benchmark_01.json`.
- Navegador bloqueado: `reports/session_15/browser_01/browser.json`.
- Evidencia final y manifiesto: `reports/session_15/final_01/`.

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_demo.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_conservation.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
# Los siete archivos históricos indicados arriba incumplen este chequeo global:
.venv/bin/ruff format --check src tests
# Usar salidas nuevas para cada reproducción:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.demo_audit --output-dir reports/session_15/audit_nuevo
PYTHONPATH=src .venv/bin/python tests/benchmark_session15.py --output reports/session_15/benchmark_nuevo.json
```

Ejecutar Streamlit y completar revisión humana siguiendo [demo_uci.md](demo_uci.md). No hace falta cuenta corporativa; sí los snapshots locales, entorno Python y navegador funcional fuera del sandbox. Antes de enseñar evidencias de reutilización no acreditada a terceros, resolver esa revisión o utilizar modo público reducido.
