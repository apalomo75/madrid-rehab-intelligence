# Sesión 4 — ITE/IEE

Implementado `events.py`: contrato normalizado, historial por eventos, originales preservados, fecha analizable y bandera de fecha inválida, resultado literal y normalizado conservador, procedencia obligatoria, Parquet y manifiesto con hashes. Se rechazan eventos con identidad repetida contradictoria; repeticiones exactas se deduplican.

No hay datos reales integrados ni métricas de cobertura ITE. La [auditoría de fuentes](fuentes_ite_iee.md) distingue formularios de datasets. El visor indica indisponibilidad y no dibuja inspecciones ficticias.

Entrada CSV canónica: `event_id,authority,source_url,extracted_at,reference_raw,address_raw,administrative_id,administrative_status,quality_notes,inspection_type,inspection_date,result_raw,remediation_date`. Campos no disponibles son nulos. `event_id` debe identificar el evento dentro del organismo, no simplemente el inmueble; fechas ISO recomendadas. Nunca incluir nombres personales en campos libres. Solo FAVORABLE y DESFAVORABLE tienen normalización explícita; otros valores quedan unknown con original intacto. El tipo no se adivina y el estado administrativo no se deriva del resultado.

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.events inspection --input /ruta/ite_canonico.csv --output-dir data/processed/session_4_importacion_01
```

Debe prepararse el CSV desde una fuente autorizada y contrastada; no hay adaptador específico al formulario municipal. Matching: RC con formato admitido y una fila CP única confirma exclusivamente parcela. Varias CP producen ambiguous. Dirección sin referencia verificable produce candidate para revisión; no representa una coincidencia concreta ni se incorpora al análisis. Sin evidencia, unmatched. No hay padrón compartido de direcciones/IDs oficiales validado y no se inventa.

Una subsanación nula es desconocida. Resultado histórico desfavorable no indica deficiencia pendiente. Pruebas: normalización, fechas, historial, procedencia, duplicados, ambigüedad y dirección incompleta en `test_sessions456.py`. Próximo paso: obtener exportación oficial y revisar un subconjunto con licencia, esquema y evidencia de parcela.

Extensión v2: una captura canónica revisada puede pasarse a `analytics --inspections-dir /ruta/captura`. Se exige hash CP idéntico a la sesión 2 de entrada, manifiesto y Parquet íntegros. La agregación mantiene eventos y última fecha/resultado histórico; empate de fecha con resultados diferentes es `ambiguous_history`. No se deduce estado pendiente y la subsanación no documentada permanece nula. Solo probado con fixtures temporales; no hay registros reales integrados.
