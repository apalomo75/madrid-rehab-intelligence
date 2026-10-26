# Validación local de una ficha REC auténtica — 26/10/2026

Se completó el contraste de los bytes aportados por el usuario, sin nuevas consultas REC. La integración es un producto local independiente: no modifica snapshots ni activa cobertura del visor. El HTML y sus derivados completos están ignorados por Git y no se publican.

SHA-256: `22c9f480465abf5fb8dd0a6f19f21512418105fc0254df674c3463e556be7b9f` (34.475 bytes).
Original aportado: `/tmp/rec-test/ficha.html`. Copia privada persistente: `data/raw/rec/real_11140360_01/ficha.html`. Codificación ISO-8859-1: texto legible y declaración Content-Type en el HTML; existe además un meta UTF-8 contradictorio. No se conservan cabeceras HTTP. GET y HTTP 200 son evidencia comunicada por el usuario desde Ubuntu, no una captura de red reproducida por este proceso. La hora exacta de captura es desconocida; 26/10/2026 es fecha de revisión local.

La solicitud aportada usa `SGiteCons?opcion=6&origen=I&ndp=11140360`. El HTML no contiene el NDP como campo: `request_access_link.json` distingue esa procedencia de los datos leídos en la respuesta. El puente oficial auditado se filtra por NDP, conserva su hash y concuerda en calle, número y vía. No se infiere el NDP solamente por texto de dirección.

## Resultado y contraste

El parser anterior producía cero inspecciones y perdía expedientes y tablas. Se corrigieron las etiquetas reales, la normalización ordinal y de puntos, I.E.E., los encabezados horizontales, la fecha de resolución, la relación explícita de seguimiento y el literal pendiente de subsanación. El formato es `rec-local-v2`.

El resultado contiene un acceso, seis expedientes identificados, dos inspecciones y cinco actuaciones. La actuación sin expediente conserva identificador de registro propio y `case_id` vacío. No se adjudica al expediente de la fila anterior. La relación ITE–seguimiento es explícita y separada; la multa no se vincula a una orden cuyo antecedente está vacío.

Informe privado completo: `reports/rec_real/review_02/informe.md`. `result.json` conserva entidades, fechas originales e ISO, bloques y filas originales; `field_checks.json` contiene los 67 campos con sección e índice de fila (base cero). El auditor comprueba cada literal contra su celda y la multiplicidad de cada campo contra las entidades de salida; el tipo I.E.E. se conserva en el bloque y se normaliza a IEE. Las pruebas fijan hash, expedientes, dictámenes, fechas, causas, situaciones y actuaciones contra la ficha real. La revisión de las 22 filas de datos/tablas no deja campos tabulares sin mapear.

No se interpreta como dato ausente inventado: causa vacía de ITE, estados «-», antecedentes vacíos/«-», subsanación «-» y expediente vacío de la actuación de 2003. No hay fecha separada de dictamen ni de subsanación acreditada. No se deduce cronología del año del expediente: presentación de diciembre de 2025 y expediente de 2026 se conservan literalmente. Los textos de planeamiento/protección y el código B se preservan sin crear taxonomía ni diagnóstico. Archivo, terminación, resolución y multa no acreditan obras ejecutadas.

El puente de `session_10_final_01` confirma concordancia con la vía 285300, número 8, distrito 21. Conserva `28900M01100041`, estado `unmatched`, cero filas CP y ninguna referencia CP confirmada. No hay relación con edificio físico.

## Automatización y reutilización, por separado

Se revisó exclusivamente documentación oficial, sin consultar otra ficha ni el endpoint REC. El [aviso legal municipal enlazado por el propio HTML](https://www.madrid.es/portales/munimadrid/avisoLegal.html) permite reutilización de información municipal con atribución, con exclusiones para multimedia y contenidos firmados de terceros. No demuestra que todos los datos REC estén incluidos en ese régimen; tampoco concede acceso automatizado, API, límites ni consulta masiva. La ficha tiene carácter informativo, no certificado. No se aplica al REC municipal el aviso del registro autonómico.

Automatización REC: no acreditada. Reutilización específica de ficha/derivados REC: pendiente de confirmar alcance, titularidad y condiciones. El original y derivados permanecen privados (`public_exposure=False`). Antes de otras consultas automatizadas se necesita acreditar canal y permiso, límites y condiciones; antes de redistribuir, revisar el alcance de reutilización. No se ha enviado ninguna solicitud institucional.

Para otras respuestas obtenidas por consulta individual autorizada: preservar bytes en directorio nuevo ignorado, método/parámetros, cabeceras no sensibles, instante y hash; indicar por separado NDP de solicitud y NDP efectivamente visible; comparar cada tabla con sus entidades antes de marcarla validada. Revisar variantes de formato, fechas y expedientes independientes. Nunca heredar la validación de este único hash a otras fichas ni resolver CP ambiguas por proximidad.

## Reproducción sin red

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.rec_real_audit --output-dir reports/rec_real/replay_nuevo
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_rec_real.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_conservation.py -v
.venv/bin/ruff check src tests
```

El directorio de salida debe ser nuevo. El test real se omite expresamente si falta el HTML privado; un hash diferente falla. `MADRID_REHAB_REC_REAL_HTML` permite indicar otra ubicación del mismo original. No se incluye un cliente de red.
