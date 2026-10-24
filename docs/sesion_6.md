# Sesión 6 — análisis real y visor

Ejecución offline sobre sesión 2: **3.790 parcelas** de Chamberí; **3.760** con periodo constructivo; **2.105** con registros energéticos confirmados, todas ellas con contexto constructivo; **30** sin ninguna de esas dos dimensiones. Conservación y ayudas: desconocidas, no cero. Estas cifras tienen como denominador el universo de parcelas CP del distrito, no los 3.761 BU dibujables ni los 5.105 registros CEEE localizados del piloto anterior.

Implementado dataset y auditoría en `analytics.py`; comparador de sensibilidad separado; estadísticas descriptivas por periodo constructivo. [Modelo y denominadores](modelo_analitico.md), [decisión de índice](indice_rehabilitacion.md). La salida de sesión 6 y su replay tienen tablas idénticas verificadas con `assert_frame_equal`. No se modifica sesión 1/2 ni originales.

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.analytics
# Siempre nueva salida:
PYTHONPATH=src .venv/bin/python -m madrid_rehab.analytics --output-dir data/processed/session_6_replay_02
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_sessions456.py -v
```

Visor: pestaña «Rehabilitación e ITE/ayudas» con cobertura, tabla filtrable por evidencia/RC14, distribución de dimensiones y exportación CSV no personal. Mensajes explícitos para fuentes no integradas. El perfil incluye parcelas sin evidencia y verifica hashes de sus productos antes de mostrarlos. No se alteran controles ni selección del mapa. `MADRID_REHAB_SESSION6_DIR` permite seleccionar otra salida.

Las pruebas Python/AppTest no acreditan renderizado ni clic en navegador. La aceptación manual anterior del usuario sigue siendo evidencia del visor previo, no de esta ampliación. Las validaciones y bloqueos actuales se recogen en [avance nocturno](avance_nocturno.md).

## Descripción por periodo constructivo

| Año más antiguo del agregado | Parcelas | Con registros CEEE confirmados | Mediana de proporción observada E/F/G |
| --- | ---: | ---: | ---: |
| Hasta 1940 | 1.230 | 677 | 1,00 |
| 1941–1960 | 1.391 | 777 | 1,00 |
| 1961–1980 | 786 | 476 | 0,75 |
| 1981–2000 | 247 | 131 | 0,75 |
| 2001–2026 | 106 | 44 | 0,619 |

Otras 30 parcelas no tienen periodo disponible. La mediana usa proporciones calculables por parcela, sin ponderarlas por número de registros ni imputar las parcelas sin letras. No representa fracción de edificios ineficientes. Diferencias entre periodos pueden reflejar composición de ámbitos, cantidad de observaciones y selección administrativa; no identifican causalidad ni ahorro potencial. Fuente reproducible: `construction_periods.csv`.

Rendimiento observado: pipeline completo aproximadamente 4,28 s, incluida lectura municipal y hashes; no es benchmark universal. Benchmark anterior ejecutado de nuevo: carga 0,29 s, filtros 0,38–0,43 s y preparación cartográfica 0,31–0,86 s. No mide fluidez del navegador.

## Profundización autónoma

Entrega vigente: [auditoría de Chamberí](auditoria_analitica_chamberi.md), motor v2 y visor ampliado. Salida por defecto `data/processed/session_6_audited/`; v1 y checkpoints se conservan. Reconciliadas todas las columnas comunes con v1: cifras iguales. Nuevas comprobaciones protegen futuras capturas ante duplicidades contradictorias, ambigüedad fuera del piloto, fechas y nulos. Perfiles descriptivos y 20 escenarios de sensibilidad; exploración con filtros AND, ordenación, CSV seguro, explicación individual, gráficos interactivos y malla métrica. Caché evita relecturas Parquet. Integración opcional de eventos revisados, sin activar datos ficticios. Validación y comandos actualizados en README y seguimiento.
