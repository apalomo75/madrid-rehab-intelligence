# Sesión 5 — subvenciones

Implementado contrato local en `events.py`, separado por fases (`call`, `application`, `award`, `payment`, `justification`, `executed`, `unknown`). No se infieren transiciones. `executed` exige URL de evidencia explícita; la validación semántica de esa evidencia requiere revisión del importador. Estados originales se conservan. Ningún registro real obtenido: véase [auditoría](fuentes_subvenciones.md).

Entrada: campos comunes de sesión 4, más `case_id,program,phase,resolution_date,amount,currency,location_role,district_code,neighborhood,execution_evidence_url`. Importe decimal canónico (punto, sin miles), desconocido nulo. La moneda no se presupone. Columnas ajenas al contrato, incluidos nombres de beneficiarios, se descartan; los campos libres requieren revisión para no incorporar datos personales.

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.events grant --input /ruta/ayudas_canonicas.csv --output-dir data/processed/session_5_importacion_01
```

Solo `location_role=subsidized_property` permite confirmar RC de inmueble subvencionado. Beneficiario no confirma parcela aunque declare RC. A=parcela confirmada; B=barrio/distrito aportado, sin confirmación de inmueble; C=no geolocalizable. Los territorios del CSV deben ser revisados contra nomenclátor antes de usarlos en mapas. Candidatos y ambiguos no se dibujan como concesiones confirmadas.

`grant_summary` cuenta únicamente fase award, deduplica por organismo/programa/expediente y excluye casos publicados con importes, monedas o localización contradictorios. Expedientes sin identidad quedan separados, no se suman. Solo suma EUR conocido, con denominador explícito; cero publicaciones conocidas no se transforma en cero euros. Los pagos no se suman con concesiones. Una concesión no demuestra ejecución. Tests cubren republicaciones, conflictos, fases, importes y dirección del beneficiario.

Pendiente: adaptador específico a exportación oficial, revisión legal y semántica, conciliación temporal de resoluciones, agregados territoriales y conexión opcional de eventos reales al perfil. Las fases 4/5 no son una integración terminada; se entrega infraestructura verificable sin datos fabricados.

Extensión v2: `analytics --grants-dir /ruta/captura` agrega únicamente concesiones de inmueble confirmadas, tras conciliar globalmente expedientes; discrepancias de localización, resolución, importe o moneda se excluyen. Captura y versión CP se verifican por hash. Nuevos controles rechazan importes infinitos y evidencia de ejecución vacía; `amount_raw` conserva literal. No se activó esta opción sobre datos reales. La revisión de licencia, localización y fases sigue siendo previa a la importación.
