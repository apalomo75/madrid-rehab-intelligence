# Avance de sesión 12

**Entrega parcial por bloqueo de red. No se declara completada la expansión regional.** Hay componentes ejecutables, productos reales de inventario/reconciliación y pruebas; faltan catálogo INE completo, límites oficiales completos, clasificación espacial real y piloto CP/BU externo.

- Auditoría inicial: 16 rutas con cambios de sesión 11, copia de protección en `/tmp/madrid_rehab_session12_initial/`, 1.718 archivos de originales/productos protegidos por SHA-256. Ninguno cambió según auditoría final (`reports/session_12/audit_verified/quality.json`). No commits, push, publicación ni descarte de cambios.
- Baseline: 252 pruebas, 177,042 s, correctas. Primera suite ampliada: 285 pruebas, 185,740 s, correctas. Las pruebas de la sesión 12 se ampliaron después a 36; suite ampliada de 288 pruebas correcta (230,536 s). Segunda comprobación completa: **288 pruebas correctas en 217,314 s**, en `reports/session_12/full_tests_verified.log`; las 36 específicas del último ajuste territorial pasaron en 29,432 s (`regional_tests_release.log`). Ruff correcto (`ruff_release.log`).
- 179 entradas oficiales de cada feed ATOM recuperadas de originales existentes, identidad catastral conservada. Los rectángulos de cobertura no se usan como límites.
- Fuentes INE/IDEM/IGN localizadas y contrastadas mediante web; Python falla DNS. 13 HEAD de acceso, incluidos diez recursos CP/BU piloto: bloqueados. No se descargaron datos ficticios ni se hicieron cientos de peticiones.
- Pipeline municipal CP/BU configurable, validación estricta, publicación atómica, reanudación por originales/particiones verificables y lotes máximos de cinco. Pruebas de la rama CP/BU externa y mapa con fixtures sintéticas expresamente identificadas.
- PRTR: 7.532 expedientes, importe 315.527.338,99 € reconciliado sin duplicación. Madrid: 3.805 expedientes, 3.809 relaciones confirmadas, 3.300 parcelas. Tres relaciones ambiguas preservadas. Pendientes territoriales: 3.727, sin atribuir a otros municipios por texto.
- Visor: menú de 179 recursos municipales, cobertura desigual visible, filtros PRTR, importes legibles, tabla principal reducida y modo técnico. Con límites/particiones validados puede habilitar la rama INE–mapa municipal–CP–BU; actualmente los municipios externos muestran pendientes. Madrid conserva sus 21 distritos y funciones.
- Medición real inicial: AppTest regional 1,804 s; cambios municipales 0,032–0,109 s. CP completo Madrid 0,802 s, BU 0,717 s, consulta CP por referencia 0,435 s. RSS conjunto 827.628 KiB (~808 MiB), incluyendo lecturas completas históricas. Medición final (con suite concurrente): apertura 3,140 s, cambios 0,048–0,205 s, RSS regional AppTest 233.624 KiB (~228 MiB); CP/BU completos 1,359/1,066 s, RSS conjunto 851.612 KiB (~832 MiB). Informe separado en `benchmark_final.json`; no confundir con benchmark de ingesta externa inexistente.
- CEEE auditado por chunks sin expansión: registros de otros literales municipales ya existen; faltan identidad INE, deduplicación y contraste catastral. No se trasladan letras de viviendas a edificios.
- Licencia IGN CC BY 4.0 verificada en documentación enlazada; IDEM específica pendiente; DGC condiciones propias con restricciones para originales; PRTR sin licencia verificada. Uso local; `MADRID_REHAB_PUBLIC=1` desactiva detalle/exportación PRTR.

## Navegador bloqueado y comprobación pendiente

El intento de arrancar Streamlit terminó con `PermissionError: [Errno 1] Operation not permitted` al abrir socket (`reports/session_12/server_attempt.log`). **Validación visual en navegador bloqueada.** AppTest comprueba construcción y navegación, sin acreditar clics reales, legibilidad o descargas del navegador.

```bash
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512 --server.headless true \
  --browser.gatherUsageStats false
```

Comprobar manualmente: Madrid y sus distritos, mapas CP/BU y fichas anteriores; menú autonómico y selección de Getafe/Móstoles/Madrid; mensajes de pendientes sin cero ayudas; filtros por programa/importe/cobertura, selección vacía y recuperación; formatos de importes y modo técnico; CSV local seguro; reinicio público sin PRTR; reinicio offline sin teselas externas. Tras conseguir límites y piloto, validar en navegador la rama de mapas municipales externos que aquí solo se ejercitó con fixtures.

## Pendientes de aceptación y sesión 13

Conseguir capturas oficiales INE/límites y correspondencias revisadas; ejecutar piloto real y auditar conflictos de los 7.532 PRTR; medir tiempos/bytes/RSS del piloto antes de escalar. No afirmar 179 municipios con CP/BU. Para sesión 13: expansión CEEE por identidad municipal y CP particionado, ámbitos conservados y deduplicación, cuando estas dependencias territoriales estén resueltas. No hay ranking comercial ni recomendaciones de financiación.
