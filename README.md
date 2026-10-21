# Madrid Rehab Intelligence

Proyecto de plataforma pública para explorar el potencial de rehabilitación residencial en Madrid.

**Estado al 21/10/2026:** primer pipeline Catastro–certificados energéticos implementado y probado offline. La descarga real está bloqueada por resolución DNS: no hay observaciones oficiales integradas ni distrito piloto seleccionado con evidencia. Los dos Parquet de la primera ejecución están vacíos y documentan el contrato de salida.

## Ejecutar

Desde la raíz, con Python >=3.11 y acceso al índice de paquetes:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m madrid_rehab.cli \
  --raw-dir data/raw/run_002 \
  --output-dir data/processed/run_002 \
  --report-dir reports/run_002
```

En este entorno `.venv` hereda Pandas/PyArrow preexistentes mediante `--system-site-packages`; no se modificaron instalaciones globales. Los detalles y limitaciones de instalación figuran en la [guía del pipeline](docs/pipeline.md).

La muestra tiene un máximo de 30 filas CEEE, cinco referencias, 20 peticiones y 5 MiB por ejecución. No descarga ZIP municipales. Se conservan originales, errores, configuración y hashes. Una ejecución sin filas devuelve código 2; usar un directorio de informes nuevo para cada ejecución.

## Pruebas

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

25 pruebas offline con datos sintéticos: límites HTTP, RC, ámbitos, ambigüedad y Parquet. No representan precisión ni cobertura de las fuentes reales.

## Organización y reglas de integración

- `src/madrid_rehab/`: adaptadores, normalización, cruce, informes y CLI.
- `tests/`: pruebas con ejemplos sintéticos; `config/`: límites y fuente candidata.
- `data/raw/` y `data/processed/`: artefactos locales excluidos de Git.
- `reports/first_run/`: evidencia de la ejecución bloqueada.
- `docs/`: investigación, arquitectura, ejecución y resultados.

Se distinguen parcela RC14, inmueble RC20 y objetos BU. Las direcciones no fuerzan coincidencias. El ámbito energético original se conserva; su catálogo normalizado queda pendiente de contraste. Una vivienda no transfiere su letra al edificio y un punto de parcela no cuenta como bloque identificado.

Usera, Chamberí y Carabanchel son candidatos a comparar por disponibilidad y calidad, sin usar subvenciones. No hay todavía datos para seleccionar uno de forma fundada.

## Documentación

| Documento | Contenido |
| --- | --- |
| [Guía del pipeline](docs/pipeline.md) | Instalación, límites, reproducción y métricas |
| [Resultados](docs/resultados_pipeline.md) | Cifras reales, bloqueo, validación y pendientes |
| [Fuentes](docs/fuentes_datos.md) | Accesos, variables, granularidad y licencias |
| [Viabilidad](docs/viabilidad.md) | Riesgos y criterios de decisión |
| [Arquitectura](docs/arquitectura.md) | Diseño general y alcance implementado |
| [Plan](docs/plan_desarrollo.md) | Fases y autorización vigente |
| [AGENTS.md](AGENTS.md) | Instrucciones de contribución |

No se han incorporado ITE/IEE, órdenes, subvenciones, Streamlit ni mapa. El siguiente paso es obtener la muestra oficial desde un entorno con acceso HTTPS y contrastar sus esquemas. Cualquier descarga grande requiere estimación y aprobación previa.
