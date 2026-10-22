# Ingesta municipal reproducible

La sesión 1 descarga los recursos oficiales CEEE 2025 y 2026 publicados por la Comunidad de Madrid y los paquetes ATOM CP/BU de Madrid municipio. Se distinguen el código INE 28079 y el código catastral 28900. Los ficheros se descubren desde los catálogos, sin construir consultas individuales por inmueble.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
PYTHONPATH=src .venv/bin/python -m madrid_rehab.ingest \
  --raw-dir data/raw/session_1 --output-dir data/processed/session_1
```

Los originales, feeds y metadatos HTTP quedan en `data/raw/session_1/`; los Parquet, métricas y `informe_ingesta.md`, en `data/processed/session_1/`. Ambos directorios están excluidos de Git. Cada descarga se escribe primero en `.part` y se publica tras comprobar longitud; la caché exige coincidencia SHA-256 y URL. Límite de 160 MiB por recurso y 320 MiB de tráfico por ejecución; archivos GML descomprimidos limitados a 2 GiB. Se mantienen los límites anteriores de la CLI de muestras. La descarga municipal completa está autorizada por la sesión 1 y no necesita consultas por referencia.

Reproducción sin red, usando otro directorio de salida:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.ingest --offline \
  --raw-dir data/raw/session_1 --output-dir data/processed/session_1_replay
```

Las salidas completadas no se sobrescriben. Para una captura nueva, elegir directorios nuevos tanto de originales como de procesados; reutilizar los originales reproduce la captura anterior, no actualiza las fuentes. Una descarga que exceda los límites falla explícitamente; debe configurarse una captura WFS por ámbito geográfico antes de continuar. En esta sesión los paquetes municipales caben dentro de los límites.

## Contrato de las tablas

- `certificados_madrid.parquet`: una fila por contenido fuente distinto de Madrid capital, con todas las columnas originales, identificador SHA-256, fecha derivada, ámbito declarado normalizado, referencias a parcelas y estados de enlace. `source_occurrences`, `source_years` y `source_urls` conservan la multiplicidad de filas técnicas. El manifiesto contiene hashes y fechas de todos los originales.
- `parcelas_madrid.parquet`: identificador oficial y registro único por posición en el original, RC14, punto de referencia, geometría WKT métrica, CRS, validez topológica, ámbito, fecha del feed y procedencia.
- `edificios_madrid.parquet`: identificador oficial BU y registro único por posición en el original, referencia de parcela, geometría WKT, CRS, construcción y uso cuando disponibles, calidad y procedencia. BU es un agregado catastral; no se identifica automáticamente con un bloque físico.

Parquet convencional, no GeoParquet. Para leer:

```python
from pathlib import Path
import pandas as pd

root = Path('data/processed/session_1')
certificados = pd.read_parquet(root / 'certificados_madrid.parquet')
parcelas = pd.read_parquet(root / 'parcelas_madrid.parquet')
edificios = pd.read_parquet(root / 'edificios_madrid.parquet')
print(len(certificados), len(parcelas), len(edificios))
```

## Criterios semánticos y calidad

La deduplicación compara todas las columnas originales y elimina solo contenido idéntico. Conserva certificados sucesivos sobre la misma referencia y versiones diferentes del mismo código. El identificador representa una versión de fila, no garantiza un certificado administrativo distinto. La lectura detecta UTF-8 o ISO-8859-1 conservando los originales sin sustitución de caracteres; el CSV 2025 incluye bytes incompatibles con Windows-1252. Las fechas o números no convertibles se conservan en su campo original y dan nulo en el derivado.

El mapa revisado `config/sample.json` se basa en el campo oficial `edif_tipo` («Tipo de edificio o parte del edificio certificado») y el análisis de `docs/analisis_run_002.md`: ViviendaIndividualEnBloque y ViviendaUnifamiliar → dwelling; BloqueDeViviendaCompleto → whole_building; LocalUsoTerciario → building_part. Valores nuevos quedan unknown. No se usa `edif_tiporeg` para deducir cobertura.

Los identificadores catastrales repetidos se conservan y señalan; cada fila tiene además `record_id` único, derivado del hash del original y su posición. No se confunde unicidad de registro con unicidad de parcela. El número declarado en la cabecera GML se compara con los elementos efectivamente leídos; las discrepancias se informan y no se ocultan eliminando filas. Los ZIP se consumen hasta el final, verificando CRC durante la descompresión.

Shapely comprueba topología sin reparar geometrías. PyProj transforma los puntos CP de EPSG:25830 a EPSG:4326 con `always_xy=True` y comprueba una envolvente amplia de Madrid; no es una validación de precisión posicional. No se atribuye letra energética a los objetos BU. El enlace por RC14 confirma parcela, no inmueble RC20 ni bloque físico. Las referencias no admitidas por el patrón urbano se conservan para revisión.

## Fuentes y reutilización

- [Registro CEEE, catálogo oficial](https://datos.comunidad.madrid/dataset/registro_certificados_eficiencia_energetica).
- [ATOM edificios, provincia 28](https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/28/ES.SDGC.bu.atom_28.xml).
- [ATOM parcelas, provincia 28](https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/28/ES.SDGC.CP.atom_28.xml).

Atribución: Comunidad de Madrid y Dirección General del Catastro, Ministerio de Hacienda. Las condiciones y fechas publicadas se conservan en `ingestion_metrics.json`; los feeds catastrales permiten uso gratuito con mención del autor y propietario. 2026 es un recurso del año en curso según la captura; no debe presentarse como anualidad cerrada.
