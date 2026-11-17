# Sesión 32 · NextGenerationEU preparado para publicación condicionada

## Decisión operativa

**Caso B: falta acreditar autorización específica.** Se ha implementado el recorrido de producción para PRTR y creado un candidato local no distribuible. No se ha hecho commit, push, subida, descarga de registros ni despliegue. No se ha enviado la solicitud de autorización.

La evidencia institucional y el canal concreto están en [licencia PRTR](licencia_datos_prtr.md); solicitud lista en [solicitud de reutilización](solicitud_reutilizacion_prtr.md). No se ha encontrado una licencia que cubra expresamente el GeoJSON de la API. El responsable jurídico/licenciante del dataset sigue pendiente de confirmación entre Comunidad de Madrid y COAM; no confundir el responsable del sitio de la Oficina COAM con la titularidad del dataset del visor.

## Productos preparados

Candidato final local: `data/deployment/madrid_rehab_prtr_candidate_02/`. El `_01` es una preparación intermedia conservada, no activar ni distribuir. Ambos están bloqueados. **`madrid_rehab_v1_02` permanece intacto**: los hashes de todos sus archivos se han contrastado.

Se copia el paquete público existente, sin repetir ETL ni matching. Única fuente añadida: producto selectivo `prtr/confirmed.parquet`, 368.874 bytes, 5.072 relaciones confirmadas, 5.046 expedientes únicos y 4.378 parcelas. Los 7.532 expedientes originales siguen preservados en S11; los no vinculados no se incorporan al mapa público.

Se conservan programa, identificador, importe y céntimos originales, estado administrativo original, dirección, referencias originales, coordenadas del punto de fuente, referencia de parcela confirmada, calidad de vínculo, fila fuente, hash de origen, fechas disponibles y enlace al visor. No se inventan enlaces individuales que la fuente no proporciona. No se incorporan `raw_json`, renta ni contexto censal. Los polígonos del mapa proceden de los productos catastrales ya incluidos.

| Municipio | Expedientes confirmados | Parcelas PRTR | Catálogo candidato |
| --- | ---: | ---: | ---: |
| Madrid | 3.805 | 3.300 | 113.550 |
| Alcalá de Henares | 229 | 208 | 9.460 |
| Alcorcón | 287 | 244 | 3.008 |
| Getafe | 165 | 151 | 13.339 |
| Leganés | 234 | 198 | 6.597 |
| Móstoles | 326 | 277 | 6.819 |

El catálogo candidato totaliza 152.773 parcelas. No vuelve a las 153.929 del catálogo S24: conserva las exclusiones administrativas del paquete público. Añadir PRTR no autoriza los padrones PDF ITE/IEE ni otras fuentes. Ninguna familia de datos del paquete base cambia de bytes salvo la base SQLite, donde se añaden membresías PRTR y se actualizan admisión y búsqueda sobre referencias documentales existentes.

## Código e interfaz

- `public_prtr.select()` reutiliza exclusivamente relaciones `confirmed`/`confirmed_historical_madrid`, sin contradicción territorial ni conflicto de expediente. `program_refs()` genera los conjuntos por programa; `records()` recupera selectivamente la ficha en el bundle, sin fallback a archivos privados.
- `commercial_filters.query(..., prtr_program="any")` sustituye la máscara PRTR antes de AND/OR, igual que el ámbito CEEE. Municipio, distrito, contador, lista y mapa comparten el DataFrame resultante. Una selección incompatible se limpia al cambiar programa.
- `commercial_explorer.render()` restaura «Ayudas NextGenerationEU». En un paquete sin permiso permanece visible deshabilitado. Cuando se active con permiso, ofrece cualquier ayuda o programas 1/3/4/5. Se conservan el mapa y panel 65/35.
- `commercial_data.load_fiche()` consulta PRTR público únicamente si `production_bundle.allowed_prtr()` lo permite. `commercial_fiche.build_model()` agrupa por expediente. `commercial_view.render()` muestra programa, expediente, importe, estado, dirección, parcela y enlace de procedencia. Un mismo expediente en varias parcelas conserva el importe íntegro por expediente; no hay sumas por vínculo ni se infiere pago o ejecución.
- Nuevas etiquetas ES/EN en `i18n.py`, valores internos estables. Las direcciones, referencias y estados originales no se traducen.
- `production_bundle` exige una autorización documentada y con hash para paquetes PRTR. `bundle_delivery.pack()` rechaza el candidato pendiente incluso si se llama directamente. El formato y uso de `v1_02` siguen funcionando.

## Revisión y reproducción ahora

Instalación de desarrollo: `.venv/bin/python -m pip install -r requirements.lock`. Sin nuevas dependencias.

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_public_prtr.py -v
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python tests/benchmark_public_prtr.py --candidate data/deployment/madrid_rehab_prtr_candidate_02 --output reports/session_32_prtr/revision_nueva/real_candidate.json
```

El benchmark crea un informe nuevo; rechaza sobrescritura. Para reproducir el candidato, siempre con nuevas rutas:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.public_prtr --base data/deployment/madrid_rehab_v1_02 --output-dir data/deployment/prtr_candidato_nuevo --report-dir reports/session_32_prtr/candidato_nuevo
```

La verificación de runtime y empaquetado **deben fallar ahora** para el candidato porque su autorización está pendiente. No cambiar PUBLIC=0, falsear permisos ni editar el manifiesto para revisarlo.

La interfaz se ha probado con AppTest local privado sobre fuentes reales y con pruebas unitarias del contrato público y fixtures sintéticas. El candidato real no se ha activado como público ni se ha generado un archivo de entrega. Las autorizaciones ficticias de las pruebas se limitan a datos sintéticos temporales.

## Activación futura, solo después de autorización real y revisión

1. Guardar la licencia o respuesta escrita competente como documento local. Revisar que cubra el recurso exacto y todos los campos/transformaciones previstos. Si limita campos o localización, adaptar el producto antes de autorizarlo.
2. Copiar `config/prtr_authorization.json.example` a una ruta local de trabajo. Completar titular, fecha, condiciones, atribución, SHA-256 del documento y ámbito real. Solo tras revisar la autorización, usar `status="verified"` y `owner_reviewed=true`. El código comprueba integridad y presencia de estos campos; **no sustituye la revisión jurídica del contenido**.
3. Crear una nueva versión sin sobrescribir candidato ni paquete anterior:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.public_prtr --candidate data/deployment/madrid_rehab_prtr_candidate_02 --authorization /ruta/autorizacion_revisada.json --document /ruta/respuesta_oficial.txt --output-dir data/deployment/madrid_rehab_prtr_release_nueva
PYTHONPATH=src .venv/bin/python -m madrid_rehab.bundle_delivery verify --bundle-dir data/deployment/madrid_rehab_prtr_release_nueva
```

4. Revisar el recorrido público local:

```bash
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_prtr_release_nueva MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Comprobar los seis municipios, cada programa, AND/OR, las fichas, cambio ES/EN, retorno y selección de mapa. Las cifras por municipio/programa y 180 combinaciones están en `reports/session_32_prtr/validation_01/real_candidate.json`.

5. Después de revisión y aprobación del propietario, empaquetar con ruta nueva:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.bundle_delivery pack --bundle-dir data/deployment/madrid_rehab_prtr_release_nueva --output data/deployment/madrid_rehab_prtr_release_nueva.tar.gz
```

El comando imprime el SHA-256 del archivo. Para Community Cloud, usar el mismo procedimiento S29, con código revisado y Python 3.13 (`python -m pip install -r requirements.txt`): subir únicamente el archivo autorizado a una URL HTTPS inmutable y configurar `MADRID_REHAB_BUNDLE_URL`, su SHA exacto en `MADRID_REHAB_BUNDLE_SHA256` y una ruta nueva en `MADRID_REHAB_BUNDLE_DIR`. Mantener PUBLIC=1, OFFLINE=1, DEV/DEMO/PILOT=0. No reutilizar la URL/SHA/ruta de caché de v1_02. No se ha realizado ninguna de estas acciones de publicación.

## Validación y límites

Informe real: `reports/session_32_prtr/validation_01/real_candidate.json`. Verifica 260 archivos, integridad del base, identidad de los otros productos, todas las geometrías PRTR utilizables y 180 combinaciones por conjuntos; las filas resultantes alimentan mapa/lista sin reglas paralelas. La ficha deduplica cada expediente y conserva todas las ayudas de la parcela, independientemente del programa que permitió encontrarla.

Medición offline del proceso auditor: 6,86 s, RSS máxima 402,39 MiB; DataFrame PRTR completo 7.079.251 bytes. Incluye verificación y lecturas del auditor: **no es consumo medido en Streamlit Cloud ni benchmark multiusuario**. En runtime se proyectan columnas para conjuntos y se leen fichas por municipio/parcela con cachés acotadas.

Pendientes reales: autorización específica; revisión visual WebGL; memoria y concurrencia en Cloud tras entrega autorizada. La falta de despliegue no se presenta como prueba superada. AppTest no valida navegador ni WebGL. Regresiones y Ruff: registros de `reports/session_32_prtr/validation_02/`; corrección de la traducción actualizada de Acerca y verificaciones finales en `validation_03/`.

Resultado final: **59 pruebas focalizadas distintas superadas**, Ruff y `git diff --check` correctos. Resumen consolidado `reports/session_32_prtr/validation_03/final_summary.json`. El propio candidato real rechaza tanto runtime público como creación de archivo por autorización pendiente; no se creó archivo de entrega. La regresión de traducción de Acerca detectada en `validation_02` está corregida y sus diez pruebas pasan en `validation_03`.
