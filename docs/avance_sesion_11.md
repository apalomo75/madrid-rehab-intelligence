# Avance de sesión 11

Trabajo sobre el estado limpio de Git indicado por el usuario. Sin commits ni push. El SHA del original PRTR se registra en el manifiesto y la documentación; no se modificaron originales ni capturas municipales anteriores.

| Fase | Resultado |
| --- | --- |
| A | Lectura de documentación y módulos existentes, baseline de 229 pruebas correcto; original real de 7.532 features auditado, hash y estructura verificados. |
| B | Normalización de todos los expedientes, modalidades P5, fechas ausentes explícitas, céntimos exactos, campos originales y cola de calidad. |
| C | Matching exacto contra CP municipal auditado, unicidad y distancia; ambiguos y referencias no integradas preservados. |
| D | Servicio oficial IDEM localizado; descarga bloqueada por DNS. Registro disponible de Madrid y contrato/configuración regional implementados. Catálogo oficial completo pendiente. |
| E | Madrid confirmado mediante CP y contraste de dirección. Resto preservado como pendiente; no se declara clasificación exhaustiva ni cobertura confirmada de otros municipios. |
| F | Relaciones con órdenes, licencias, declaraciones y obligaciones ITE/IEE, contexto CEEE y antigüedad, sin fusionar expedientes ni causalidad. |
| G | Agregados por programa, municipio/calidad y distrito; perfiles P3, P5 proyecto, energía y coexistencias administrativas. |
| H | Pestaña PRTR municipal/distrital, filtros, tabla y CSV seguro; ficha CP con multiplicidad y estado de relaciones. |
| I | Navegación separada «Comunidad de Madrid — Subvenciones» con agregados, calidad y filtros; sin polígonos o fichas regionales ficticias. Comparación exhaustiva municipal pendiente de límites/catálogo. |
| J | unittest/AppTest, Ruff, reproducción, integridad y benchmarks; informes bajo `reports/session_11/`. Validación visual real pendiente. |

Captura activa `data/processed/grants/session_11_final_03/`. Se conservan todos los intentos anteriores para auditoría; `session_11` es un checkpoint previo a corregir etiquetas PR1→P1, y otros checkpoints ensayaron reglas de referencia. No deben usarse como producto vigente. La versión final admite hojas urbanas alfanuméricas y no cambia los validadores ni datos históricos.

Incidencia de informes: al comparar rendimiento se ejecutó `tests/benchmark_session71.py`, que tiene ruta fija y regeneró `reports/session_7_1/benchmark.json`. No se sobrescribieron datasets anteriores; el informe histórico no se presenta como preservado byte a byte. Se añadió `tests/benchmark_grants.py` con rechazo de salida existente y ruta explícita para las nuevas comparaciones. El log de aquella medición queda en `reports/session_11/original_view_benchmark.log`.

## Navegación y comprobación manual pendiente

```bash
PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

1. Abrir Madrid capital y pestaña «Subvenciones PRTR». Contrastar suma e identidades, programas, modalidades P5, importes y CSV. Filtrar a cero y restablecer.
2. Entrar en Chamberí y otros distritos, probar filtros constructivos y selección CP/BU existente; confirmar que las subvenciones P4 no se describen como ayudas al edificio completo.
3. Seleccionar parcela con concesión y revisar expedientes múltiples, fuente, estado de concesión y relación catastral. Contrastar con los eventos y certificados independientes, sin inferir misma obra.
4. Elegir navegación regional. Verificar aviso de límites/catálogo pendientes, conservación del total regional y ausencia de fichas CP fuera de Madrid. No interpretar pendientes como municipios externos confirmados.
5. Reiniciar con `MADRID_REHAB_PUBLIC=1`: no debe aparecer detalle ni exportación PRTR. Reiniciar con `MADRID_REHAB_OFFLINE=1` para regresión del visor base sin teselas.
6. Revisar clic real, legibilidad, scroll, mapas anteriores y descarga CSV en navegador. AppTest valida lógica y construcción, no sustituye esa aceptación visual.

Licencia no verificada, límites/catálogo regional y diccionario de variables censales son bloqueos de cobertura/procedencia. No bloquean la conservación y análisis local de los 7.532 expedientes. La sesión no se presenta como clasificación completa de los 179 municipios ni como validación visual completa.

## Cierre verificable

252 pruebas de suite completa correctas; Ruff correcto. Las 23 específicas se repitieron sobre la captura final con referencias alfanuméricas. Diez Parquet y manifiesto reproducidos idénticos; original intacto y 57 salidas de sesiones 7/10 verificadas contra sus manifiestos. Streamlit no pudo abrir socket: `PermissionError: [Errno 1] Operation not permitted` en `reports/session_11/server_attempt.log`. **Validación visual bloqueada**, no declarada correcta.

Resultado territorial: 3.805 expedientes Madrid confirmados, 3.809 relaciones en 3.300 RC14 CP. Otros 3.727 expedientes íntegros pendientes de clasificación. Solo un municipio oficialmente identificado en la integración actual; no se puede informar todavía un número de municipios externos cubiertos con garantías.

Importe Madrid confirmado: 126.328.673,63 €; total regional de la captura: 315.527.338,99 €. Incidencias de fuente en 51 expedientes, más tres relaciones CP ambiguas. No hay recuento confirmado de expedientes de otros municipios: los 3.727 pendientes se conservan íntegros, incluidos los que podrían seguir correspondiendo a Madrid. El agregado regional no se presenta como importe de Madrid capital.
