# Sesión 11 — PRTR real local

Pipeline ejecutable, productos auditados y vistas implementadas. **Clasificación regional exhaustiva pendiente**: el acceso al WFS oficial falla por DNS. No se descargó Catastro fuera de Madrid ni se generaron límites aproximados. No hay commits, push ni publicación.

## Fuente y captura

Original: `data/raw/subvenciones/prtr/concesiones_prtr_20261024.geojson`, 5,767,407 bytes. API de origen: [https://visorrehabilitaprtrmadrid.coam.org/api/main.cgi?method=resum&pr=all](https://visorrehabilitaprtrmadrid.coam.org/api/main.cgi?method=resum&pr=all). SHA-256: `03b6273b8a9c2f53e2fdc211c44fe495176d44aaa4727f7714ac43d4623adc36`. Se conserva sin modificar. CRS84 (longitud, latitud); FeatureCollection de puntos. No se consultaron expedientes individuales ni se repitió la descarga PRTR.

Actualización indicada por el visor en la entrega: **20/07/2026**, no contenida dentro del GeoJSON y no verificada independientemente debido al bloqueo de acceso. Descarga declarada: **24/10/2026**. No hay fecha de concesión, pago, expediente ni publicación dentro de los campos del GeoJSON; el año del identificador no sustituye estas fechas. `fecha_disponible`, `fecha_concesion` y `fecha_pago` permanecen nulas.

## Reconciliación

| Programa | Expedientes / 7.532 | Importe concedido (€) |
| --- | --- | --- |
| P1 | 364 | 68,107,496.98 |
| P3 | 1380 | 229,790,531.46 |
| P4 | 4889 | 12,232,015.84 |
| P5 | 899 | 5,397,294.71 |


Total: **315,527,338.99 €**. Céntimos enteros calculados con Decimal; la cantidad original y `raw_json` permanecen disponibles localmente. Ninguna tabla de relaciones contiene importes. No hay reparto arbitrario entre parcelas o distritos.

| Indicador | Recuento | Unidad |
| --- | --- | --- |
| Originales | 7532 | features |
| Identidades | 7532 | expedientes |
| Referencias distintas | 6604 | RC14 con formato admitido; no confirmación regional |
| Relaciones | 7561 | expediente–RC14 |
| Multiparcela | 12 | expedientes con varias RC14 distintas |
| Lista refs con varios elementos | 19 | expedientes, incluye inválidos y repetidos |
| Viviendas declaradas | 72693 | suma por expediente, no viviendas únicas |
| Madrid confirmado | 3805 | expedientes |
| Pendientes territoriales | 3727 | expedientes; no equivale a otros municipios |
| Relaciones CP confirmadas | 3809 | relaciones |
| RC14 CP confirmadas | 3300 | parcelas |


P5 conserva 706 `pr5_Libro`, 185 `pr5_Todo` y 8 `pr5_Proyecto`. P1 corresponde a barrio, P3 a edificio, P4 a vivienda y P5 a libro/proyecto según el [RD 853/2021](https://boe.es/buscar/act.php?id=BOE-A-2021-16233). Programa no identifica tipología física ni confirma ejecución.

## Productos

Captura vigente: `data/processed/grants/session_11_final_03/`. `grants.parquet` contiene una fila por feature, identidad y atributos originales serializados; `grant_parcel_links.parquet` separa relaciones; `grant_municipality_links.parquet` conserva asignación y calidad; `grant_quality.parquet` conserva incidencias; `grant_source_manifest.json` conserva procedencia, correspondencia de campos, SHA de fuente/CP, salidas y recuentos. Tablas de resumen por programa, municipio/calidad y distrito. `grant_parcel_profiles.parquet` añade contexto CEEE y constructivo; `grant_administrative_cooccurrences.parquet` mantiene relaciones con eventos anteriores sin fusionar identidades ni importes.

CP contrastado: `58cab278022f53df6470aef79b81c8b66363fe82426be679cc49b298b05940ff`. Se verifica contra el manifiesto municipal. Únicamente una fila CP, geometría utilizable y distancia ≤100 m permiten confirmar una relación explícita. El umbral se usa para revisión, nunca para buscar o sustituir RC por cercanía. Referencias con varias filas CP quedan ambiguas. El nombre Madrid de la dirección se contrasta como señal de coherencia, no como fundamento único de confirmación. No existe confirmación regional de parcelas ajenas a la captura municipal.

## Reproducción

Sin dependencias nuevas, instalación `.venv/bin/python -m pip install -r requirements.lock`. Ejecutar desde la raíz; cada salida debe ser nueva:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.grants --output-dir data/processed/grants/replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_grants.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python tests/benchmark_grants.py --output reports/session_11/benchmark_nuevo.json
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

`MADRID_REHAB_GRANTS_DIR` permite otra captura íntegra con el mismo CP municipal. `MADRID_REHAB_PUBLIC=1` desactiva exposición PRTR, incluida la ficha y exportación. Uso local por defecto, sin permiso de redistribución inferido.

## Validación y rendimiento

Baseline: 229 pruebas correctas en 169,953 s. Suite completa: **252 pruebas correctas en 211,143 s**, incluidas 23 nuevas unittest/AppTest; evidencia final en `reports/session_11/final_tests.log`. Tiempos de esta captura: parsing 0.381 s; normalización 0.905 s; matching/asignación 28.433 s; analítica/escritura 1.114 s; total 30.833 s; RSS máxima aproximada 653.4 MiB. Las lecturas de CP y asignación están incluidas en matching. Medidas Python, no latencia de navegador ni concurrencia garantizada.

Ver [calidad](calidad_subvenciones_prtr.md), [licencia](licencia_datos_prtr.md), [arquitectura regional](arquitectura_regional.md) y [avance/validación](avance_sesion_11.md).

Reproducción final: los diez Parquet y el manifiesto son idénticos byte a byte en `session_11_final_replay_01`; original PRTR intacto. El replay tardó 19,051 s (ejecución inicial concurrente con pruebas: 30,833 s). Integridad de 10 salidas municipales y 47 administrativas anteriores contrastada con sus manifiestos, sin discrepancias; no equivale a inventario previo de todos los archivos ignorados. Evidencias `reports/session_11/reproducibility.json` y `protected_integrity.json`.

Benchmark de vista: carga regional 0,0737 s, selección Chamberí 0,00158 s, filtro 0,00235 s, memoria de DataFrames 9,36 MiB. Carga de detalle previo de Chamberí 0,1159 s en la misma medición; tareas diferentes, no equivalentes a renderizado ni a una mejora causal. `reports/session_11/final_view_benchmark.json`.
