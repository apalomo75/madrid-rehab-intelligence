# Auditoría del puente callejero–Catastro

Se procesan los cuatro CSV reales. `213605-0` describe vías por distrito; `213605-3` añade barrio y rangos; ambos tienen 11.113 filas y no son tablas de portales. `213605-4` tiene 214.676 filas NDP, códigos de vía, número, calificador, clase de numeración y coordenadas ED/ETRS. `200075-1` tiene 215.618 filas con código de número, código de vía y referencia de parcela. Su grano y sus versiones son diferentes: no se concatenan como fuentes independientes.

El enlace oficial usa COD_NDP/Código de número. El puente exterior conserva 216.061 filas y 215.663 NDP únicos; 476 filas pertenecen a códigos repetidos. No se han encontrado varias referencias diferentes para un mismo NDP en esta captura. Se conservan duplicidades y contradicciones de dirección. Hay 35.785 referencias con varios NDP y 24 claves de dirección con varias referencias; una dirección no identifica necesariamente una parcela.

| Control | Numerador | Denominador |
| --- | ---: | ---: |
| Filas confirmadas en CP | 207.648 | 216.061 filas puente |
| Referencia presente en CP (incluye conflictos) | 208.368 | 216.061 |
| Referencia válida ausente de CP | 116 | 216.061 |
| Literal no vacío con formato no admitido | 3.961 | 216.061 |
| Contradictorias | 493 | 216.061 |
| Varias filas CP | 243 | 216.061 |
| Candidatas | 116 | 216.061 |
| Sin correspondencia | 7.561 | 216.061 |
| Coordenadas ETRS disponibles | 214.676 | 216.061 |
| Distancia a geometría CP contrastable | 207.601 | 216.061 |
| Distancia superior a 100 metros | 1 | 207.601 contrastables |

Las cifras se refieren a filas, salvo NDP únicos y referencias expresamente indicados. No deben sumarse categorías de controles superpuestos.

Se comparan ETRS89 UTM30 y CP EPSG:25830, sin mezclar coordenadas de Guía Urbana/ED. La mediana y percentiles 90/99 de distancia a la geometría referida son 0 m; el máximo es 162,87 m. Caer dentro de una parcela apoya concordancia geográfica, pero no confirma edificio. La relación explícita se verifica contra una fila CP única; una distancia pequeña por sí sola nunca confirma nada. Los conflictos de código de vía, dirección NDP o distrito bloquean la confirmación. Un salto de 100 m es un umbral de revisión conservador, no una tolerancia usada para encontrar parcela.

Catastro: fecha de fuente 21/08/2026, captura 22/10/2026 19:27:14 UTC. Fecha de corte del callejero desconocida; mtime 24/10/2026 no acredita actualidad de los datos. No puede calcularse un desfase temporal exacto entre capturas. Permanecen referencias ausentes, formatos no admitidos y cambios posibles de numeración que requieren contraste oficial individual.

## Muestras territoriales

La validación cruzada automática conserva dirección, NDP, RC original, referencia CP, distrito y distancia para casos de cada estado. Los ficheros `cross_validation_XX.csv` tienen hasta diez filas por estado. No se presentan como inspección manual independiente ni como estimación estadística de precisión.

| Distrito | Filas del puente | Confirmadas | Con coordenadas contrastables |
| --- | ---: | ---: | ---: |
| 01 | 10177 | 10113 | 10113 |
| 07 | 5470 | 5433 | 5433 |
| 06 | 11178 | 11075 | 11074 |
| 11 | 15116 | 15013 | 14961 |
| 03 | 3761 | 3718 | 3718 |
| 19 | 8882 | 8722 | 8515 |

Centro 01, Chamberí 07, Tetuán 06, Carabanchel 11, Retiro 03 y Vicálvaro 19. Los denominadores son todas las filas asignadas al distrito por el puente; los conflictos conservan distrito candidato.

## Ejemplos reproducibles

- `candidate`: NDP 11009166, dirección CALLE JESÚS GOLDERO 2 , RC literal `1211820VK4711A`, filas CP 0, distrito declarado 02, distrito CP .
- `ambiguous`: NDP 11006211, dirección CALLE SAN BERNARDO 91 , RC literal `0158902VK4705G`, filas CP 2, distrito declarado 01, distrito CP .
- `contradictory`: NDP 11056909, dirección CALLE CAROLI 4 , RC literal `3590501VK3739B`, filas CP 1, distrito declarado 09, distrito CP 09.
- `unmatched`: NDP 11001956, dirección CALLE MIRA EL SOL 25 , RC literal ``, filas CP 0, distrito declarado 01, distrito CP .

Para reproducir: generar una captura con `python -m madrid_rehab.administrative` según la guía de sesión 10 y filtrar `ndp_bridge.parquet` por NDP/estado. `bridge_audit.json`, `bridge_districts.csv` y `bridge_review_examples.parquet` están bajo el directorio de informes elegido.

El cruce administrativo verifica además la dirección suministrada junto al NDP: 5.323 discrepancias literales entre licencias/declaraciones y el callejero quedan para revisión. Ejemplo: declaración `350/2023/00014`, NDP `20172698`, literal «CL ARTURO SORIA 90», candidata `5476114VK4757E`; véase `ndp_address_disagreements.parquet` del auditor para el número/calificador oficial. Las variaciones podrían ser errores, cambios de dirección o portales internos: no se resuelven con similitud textual.

Las órdenes 2018–2023 tienen esquemas de emplazamiento libre, con omisiones de tipo, número o listas. Quedan sin confirmación automática; desde 2024 el esquema estructurado permite 1.091 vínculos de 1.210 órdenes modernas con datos. No se transforma un rango de portales en múltiples eventos sin evidencia explícita.
