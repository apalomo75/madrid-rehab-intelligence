# Corrección de navegación regional

El indicador contaba Madrid de forma histórica y buscaba los cinco pilotos en
`data/processed/cadastre/session_12_2_pilot_01/`. Los productos realmente aceptados
están en `data/processed/cadastre/session_12_2_partial_validated_01/`. Cambiar solo
la ruta no bastaba: el lector regional anterior exige `validated` y otro número
de versión; estas particiones tienen contrato `partial-cadastre-v1`, estado
`partial_validated`, BU independiente y ninguna relación BU–CP creada.

El visor admite ahora explícitamente ambos contratos sin relajar el lector
histórico de ingesta. Verifica hashes de originales, productos y manifiesto
municipal registrado por el padre; identidad INE, estado aceptado, geometría
utilizable y recuentos. Solo lee `cp.parquet` y `bu.parquet` para cartografía.
Nunca muestra `*_all` o `*_quarantine` como objetos aceptados. La firma de caché
incluye el manifiesto padre. La validación fallida impide activar ese municipio.

| Municipio INE | CP aceptados | BU aceptados |
|---|---:|---:|
| Getafe 28065 | 16.149 | 93.014 |
| Móstoles 28092 | 8.980 | 56.591 |
| Leganés 28074 | 10.541 | 59.506 |
| Alcorcón 28007 | 5.734 | 37.595 |
| Alcalá de Henares 28005 | 13.037 | 86.040 |
| Madrid 28079 (histórico) | 141.244 | 124.395 utilizables |

Madrid conserva 124.396 filas BU históricas, una no utilizable; las parcelas
representan 140.595 referencias distintas. No se ha cambiado su contrato ni su
visor, sus accesos NDP o su consulta REC.

## Productos consumidos

- CP/BU piloto y relaciones PRTR: `data/processed/cadastre/session_12_2_partial_validated_01/`.
- CEEE: `data/processed/energy/session_13_final_03/`; sus entradas CP coinciden
  por hash con `cp_all` del producto parcial (el matcher excluye cuarentena).
- Límites: `data/processed/territory/session_12_1_final_01/`.
- Inventario: `data/processed/territory/session_12_final_01/`.
- Fuente de concesiones: `data/processed/grants/session_11_final_03/`.
- Madrid: `data/processed/session_7_final/` y originales auditados de
  `data/processed/session_2/` según el contrato municipal existente.

Se conservan los overrides de entorno. Un override catastral antiguo puede
mostrar menos municipios; no se sustituyen silenciosamente sus productos. No se
escribe ningún puntero `active_prtr.json` ni se modifica un snapshot histórico.
El snapshot territorial PRTR `session_12_1_final_02` sigue como respaldo histórico;
la ruta parcial contiene los vínculos documentales actualizados de los pilotos.
Los códigos de carpeta son INE revisados por el plan de cinco pilotos, no una
conversión numérica general desde códigos Catastro (Madrid es 28900 en ATOM).

## Interacción y límites

La navegación lateral se llama «Comunidad de Madrid · Municipios y cobertura».
El selector «Cambiar municipio · código INE» distingue disponibilidad CP/BU de
cobertura territorial. Cambiar municipio limpia la parcela y la selección del
mapa. RC14 permite búsqueda textual en el selector; pulsar una parcela del mapa
abre su selección. El mapa limita la ventana a 1.500 parcelas y avisa del recorte.
BU se puede consultar como cartografía municipal independiente (hasta 1.500
objetos), sin atribuir objetos a parcelas ni interpretarlos como edificios
físicos. Las fichas conservan ámbitos CEEE y estados PRTR confirmados/candidatos.

Los cinco pilotos muestran siempre cobertura parcial, no Catastro completo.
Los 173 municipios restantes conservan límites, energía y estadísticas PRTR
cuando existen, con aviso de ausencia de Catastro individual integrado.
No tener vínculos en estas fuentes no demuestra ausencia de certificados o ayudas.
Protecciones de exposición pública intactas.

## Validación y ejecución

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_regional_navigation.py -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
MADRID_REHAB_OFFLINE=1 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

La prueba nueva usa productos reales, verifica los cinco parcelarios y cuarentena,
compatibilidad energética y vínculos PRTR, y ejecuta Streamlit AppTest para los
seis municipios con CP/BU y cada uno de los otros 173. No sustituye una revisión
visual del navegador. El intento de iniciar servidor en este entorno ha quedado
bloqueado por `PermissionError: [Errno 1] Operation not permitted` al crear el
socket. No se ha realizado ninguna consulta REC en red ni descarga catastral.

Resultado final: **453 pruebas de unittest superadas**, Ruff y `git diff --check`
correctos. Las 22 pruebas focalizadas de REC/NDP también pasan. Evidencias en
`reports/correccion_navegacion_regional_20261026_01/` (regresión completa,
navegación, selección cartográfica, REC/NDP y protección pública).
