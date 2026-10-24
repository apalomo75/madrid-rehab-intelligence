# Sesión 9 — auditoría de integración efectiva

**Escenario D: no ha sido posible integrar nuevas evidencias.** Al inicio no existían productos ni documentación de sesión 8. Se efectuó la investigación documentada en [sesión 8](sesion_8_fuentes_oficiales.md), sin conseguir registros nuevos. No se declaran cumplidos los objetivos condicionados a disponer de ITE/IEE o concesiones.

| Resultado de nuevas fuentes | Número |
| --- | ---: |
| Registros reales adquiridos/integrados | 0 |
| Nuevos vínculos a parcela | 0 |
| Nuevos registros territoriales | 0 |
| Registros nuevos ambiguos o excluidos procesados | 0 (sin entrada) |

No son estadísticas del universo oficial. No se generaron datasets vacíos que aparenten capturas oficiales. El inventario de calidad es un informe; deja desconocidos los recuentos por distrito de fuentes no integradas.

## Trabajo fundamentado y arquitectura

Se completan mejoras de navegación [7.1](sesion_7_1_usabilidad.md), utilizando productos reales existentes. Se preparan `official_sources.py` (adquisición acotada) y `public_events.py` (tipos/fases separados y adaptación distrital de esquema 2019). `events.py`, `event_features.py`, `territory.py` y los contratos previos permanecen compatibles. No se cambia el pipeline geoespacial ni se altera Catastro/CEEE.

`integration_audit.py` verifica el manifiesto municipal y genera un informe determinista con hash del origen y cobertura distrital existente, dejando fuentes nuevas como `not_integrated` y recuentos nulos. Rechaza una captura que declare `event_inputs`: ese caso necesita auditoría e integración específicas, no una declaración automática de escenario D. No convierte fixtures o normalización pendiente de revisión en evidencia pública.

Los puntos de extensión futuros siguen siendo capturas canónicas revisadas con misma versión CP, controles de identidad/hash y agregaciones de eventos. No se activan pestañas/capas nuevas sin datos; no hay eventos ficticios en ficha. El adaptador urbanístico preparado solo admite precisión territorial; no se conecta al agregador de ITE/IEE.

## Cobertura efectiva por distrito

Son referencias analíticas de la captura de sesión 7; evidencia energética confirma parcela, no edificio. Fuentes nuevas «No integrada» significa cobertura desconocida.

| Código | Distrito | Parcelas | Con evidencia energética | ITE/IEE | Otras inspecciones | Ayudas |
| --- | --- | ---: | ---: | --- | --- | --- |
| 01 | Centro | 6899 | 3065 | No integrada | No integrada | No integrada |
| 02 | Arganzuela | 2660 | 1522 | No integrada | No integrada | No integrada |
| 03 | Retiro | 2238 | 1163 | No integrada | No integrada | No integrada |
| 04 | Salamanca | 5041 | 2419 | No integrada | No integrada | No integrada |
| 05 | Chamartín | 6584 | 2211 | No integrada | No integrada | No integrada |
| 06 | Tetuán | 6982 | 2973 | No integrada | No integrada | No integrada |
| 07 | Chamberí | 3790 | 2105 | No integrada | No integrada | No integrada |
| 08 | Fuencarral - El Pardo | 12248 | 2769 | No integrada | No integrada | No integrada |
| 09 | Moncloa - Aravaca | 10427 | 2490 | No integrada | No integrada | No integrada |
| 10 | Latina | 9310 | 3893 | No integrada | No integrada | No integrada |
| 11 | Carabanchel | 10018 | 4577 | No integrada | No integrada | No integrada |
| 12 | Usera | 6515 | 2447 | No integrada | No integrada | No integrada |
| 13 | Puente de Vallecas | 11215 | 4344 | No integrada | No integrada | No integrada |
| 14 | Moratalaz | 1887 | 861 | No integrada | No integrada | No integrada |
| 15 | Ciudad Lineal | 7227 | 3801 | No integrada | No integrada | No integrada |
| 16 | Hortaleza | 9961 | 2918 | No integrada | No integrada | No integrada |
| 17 | Villaverde | 5319 | 2237 | No integrada | No integrada | No integrada |
| 18 | Villa de Vallecas | 5150 | 1252 | No integrada | No integrada | No integrada |
| 19 | Vicálvaro | 5251 | 1147 | No integrada | No integrada | No integrada |
| 20 | San Blas - Canillejas | 8181 | 2949 | No integrada | No integrada | No integrada |
| 21 | Barajas | 3654 | 715 | No integrada | No integrada | No integrada |

38 referencias residuales completan 140.595 RC municipales; 51.858 parcelas distritales con evidencia más dos residuales completan 51.860. Se conservan 124.396 BU, 115.664 registros CEEE y 113.072 confirmados en parcela. Los denominadores y reconciliación anteriores siguen vigentes.

## Reproducción

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.integration_audit --output-dir reports/session_9/replay_02
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python tests/benchmark_session71.py
PYTHONPATH=src .venv/bin/python tests/benchmark_session7.py --report-dir reports/session_9_benchmark_replay
```

Usar siempre salida nueva para auditorías/replays. No regenerar productos anteriores. Para futuras adquisiciones, seguir [procedimiento de sesión 8](sesion_8_fuentes_oficiales.md); para matching e indicadores, [calidad](calidad_matching_eventos.md) y [definiciones](indicadores_rehabilitacion.md).

## Sesgos y siguiente paso

Diferencias de CEEE entre distritos reflejan cobertura administrativa y ámbitos mezclados, no tasas de necesidad. La antigüedad BU no mide conservación. Sin fechas/eventos nuevos no se puede medir desfase entre fuentes ni detectar duplicidades PRTR/BDNS; ambos controles quedan pendientes. Los distintos cortes temporales se deben conservar, no tratar como observaciones simultáneas.

La siguiente sesión debe obtener primero un archivo oficial reutilizable: priorizar CSV urbanístico 2019 para verificar materias y capacidad de agregación, y solicitar/exportar ITE/IEE y PRTR con geografía del inmueble. Revisar licencias, privacidad y calidad antes del matching. Solo si hay evidencia inequívoca se incorporará parcela; en otro caso, distrito o sin localización. Sin fuentes verificadas, no construir indicadores nuevos de conservación o ayudas ni un índice global.
