# Sesión 33 · NextGenerationEU en producción

## Entrega

Nueva versión `data/deployment/madrid_rehab_v1_03/`, generada a partir de `madrid_rehab_prtr_candidate_02`, sin descargar registros ni repetir ETL/matching. `v1_02`, ambos candidatos y los snapshots originales se conservan.

El propietario confirma que dispone de autorización de reutilización y solicita su incorporación pública. El manifiesto registra `prtr_authorization.status=owner_confirmed`, `basis=project_owner_communication` y `documentary_verified=false`. **No se afirma que se haya examinado una licencia ni se exige adjuntarla.** No se empaquetan documentos personales, credenciales ni la conversación; solo una anotación genérica de procedencia de la autorización.

El estado pendiente documentado en S32 queda superado para esta nueva release por la comunicación del propietario; se conservan esos informes históricos. No se realizó otra investigación jurídica. El candidato pendiente sigue sin activarse; la nueva release sí está habilitada.

## Datos y comportamiento

- 5.046 expedientes distintos, 4.378 parcelas y 5.072 relaciones confirmadas. Todos los registros PRTR proceden del producto selectivo existente; no se incluyen candidatos ambiguos, conflictos ni expedientes sin vínculo confirmado.
- Filtro público «Ayudas NextGenerationEU»: todas las ayudas confirmadas, programas 1/3/4/5; misma selección por parcela para contador, mapa y lista, combinada con CEEE, ITE/IEE y Plan Rehabilita mediante AND/OR.
- La ficha muestra todos los expedientes confirmados de la parcela, con programa, importe concedido, situación administrativa y dirección si constan, referencia y fuente. Deduplica cada expediente, no suma importes por relación ni infiere pagos o ejecución. Filtrar un programa no elimina otras evidencias legítimas de la ficha seleccionada.
- Se preservan navegación, traducciones ES/EN y disposición mapa/ficha 65/35. No se modificó el diseño CEEE.
- Publicación limitada al contenido del paquete. No se habilitan padrones PDF ITE/IEE ni otras fuentes restringidas. Las lecturas del recorrido público probado permanecen dentro del bundle, sin recurrir a datos privados del equipo.

| Municipio | Expedientes | Parcelas PRTR |
| --- | ---: | ---: |
| Madrid | 3.805 | 3.300 |
| Alcalá de Henares | 229 | 208 |
| Alcorcón | 287 | 244 |
| Getafe | 165 | 151 |
| Leganés | 234 | 198 |
| Móstoles | 326 | 277 |

Madrid: contador PRTR total 3.300; por programa P1=116, P3=483, P4=2.333, P5=491. Las categorías se solapan. Catálogo completo nuevo: 152.773 parcelas, 113.550 en Madrid; conserva las exclusiones administrativas de v1_02.

## Reproducir y revisar

Instalación de desarrollo: `.venv/bin/python -m pip install -r requirements.lock`. No hay dependencias nuevas. Producción Python 3.13: `python -m pip install -r requirements.txt`.

Crear otra release requiere siempre una salida nueva y la opción explícita que registra la comunicación del propietario:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.public_prtr --owner-confirmed --candidate data/deployment/madrid_rehab_prtr_candidate_02 --output-dir data/deployment/replay_prtr_nuevo --release-id replay_prtr_nuevo --decision-date 2026-11-17
```

Verificar el paquete entregado y abrirlo localmente en modo público:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.bundle_delivery verify --bundle-dir data/deployment/madrid_rehab_v1_03
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_03 MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Revisar filtros y sus combinaciones, cada programa, distritos, selección y retorno, ficha con varias ayudas, ES/EN y mapa en navegador. La aplicación Cloud tendrá que usar el código de esta entrega; **subir solo el archivo de datos no actualiza el código remoto**.

Pruebas y auditoría repetibles, informes siempre nuevos:

```bash
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_public_prtr.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_public_prtr.py --candidate data/deployment/madrid_rehab_v1_03 --output reports/session_33_prtr/revision_nueva/integrity.json
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_03 MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 PYTHONPATH=src .venv/bin/python tests/smoke_public_prtr.py --output reports/session_33_prtr/revision_nueva/smoke.json
```

## GitHub Releases y Streamlit Cloud · comandos para el propietario

**No se han ejecutado comandos de publicación.** Revisar primero los cambios y publicar el código aprobado por el procedimiento habitual del propietario; no se ha hecho commit ni push. Seleccionar luego el SHA remoto que contenga esta integración. No usar un commit antiguo: puede rechazar un paquete con PRTR o no ofrecer los controles.

El archivo preparado es `data/deployment/madrid_rehab_v1_03.tar.gz`, con su SHA en `reports/session_33_prtr/delivery.json` y `config/deployment_public_prtr.toml.example`. Verificarlo localmente:

```bash
sha256sum data/deployment/madrid_rehab_v1_03.tar.gz
```

Para volver a generar un archivo, elegir una ruta de salida nueva (el empaquetador rechaza sobrescrituras):

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.bundle_delivery pack --bundle-dir data/deployment/madrid_rehab_v1_03 --output data/deployment/madrid_rehab_v1_03_revision.tar.gz
```

Con GitHub CLI autenticado, introducir el SHA **real del código revisado y ya remoto**. Los siguientes comandos crean primero un borrador con el archivo; no hacer público hasta revisar sus notas y contenido:

```bash
read -r -p 'SHA remoto del código revisado: ' REVIEWED_COMMIT
gh release create madrid-rehab-v1.03 data/deployment/madrid_rehab_v1_03.tar.gz data/deployment/madrid_rehab_v1_03.sha256 --repo apalomo75/madrid-rehab-intelligence --target "$REVIEWED_COMMIT" --title 'Madrid Rehab Intelligence v1.03 · NextGenerationEU' --notes-file docs/release_v1_03.md --draft
```

Una vez revisado el borrador, publicarlo manualmente:

```bash
gh release edit madrid-rehab-v1.03 --repo apalomo75/madrid-rehab-intelligence --draft=false
```

La URL esperada del asset publicado en un repositorio público es:
`https://github.com/apalomo75/madrid-rehab-intelligence/releases/download/madrid-rehab-v1.03/madrid_rehab_v1_03.tar.gz`.
Un borrador o repositorio privado no proporciona descarga pública sin credenciales: no poner tokens en la URL ni en el paquete. La descarga de producción requiere HTTPS accesible sin autenticación y SHA fijado. La URL no se ha materializado ni comprobado porque no se ha publicado.

En Streamlit Community Cloud → aplicación → Settings → Secrets, reemplazar las variables de bundle por el contenido de `config/deployment_public_prtr.toml.example`, manteniendo las demás claves privadas fuera de este repositorio. Usar la rama/commit revisado, Python 3.13 y entrada `src/madrid_rehab/app.py`. No reutilizar `cloud_v1_02`: la caché debe tener ruta nueva. Guardar los secretos y reiniciar manualmente la aplicación después de actualizar el código y publicar el asset.

La URL y SHA corresponden a este archivo exacto. Si se vuelve a empaquetar, usar el SHA que imprima el comando para ese archivo. Volver a probar contador Madrid 3.300, cada programa, mapa/ficha, retorno y ES/EN en Cloud; revisar memoria y concurrencia en el servicio real.

## Validación local y límites

`reports/session_33_prtr/smoke_public_01.json`: recorrido público real mediante Streamlit AppTest, usando v1_03 sin simular permisos; 180 combinaciones públicas verificadas en seis municipios, todos los programas, ficha, ES/EN, retorno, AND/OR y limpieza. El guard de lecturas comprueba que no se consulta ningún Parquet/SQLite externo al paquete. También verifica varias ayudas en la misma parcela sin duplicar expedientes y mantiene cerrados los padrones PDF.

`reports/session_33_prtr/integrity_01.json`: hashes, integridad de v1_02, conservación de los otros productos, recuentos y geometrías de todas las parcelas PRTR. La release solo añade el permiso comunicado en el manifiesto respecto al candidato; sus productos autenticados se copian sin transformación.

Memoria máxima observada en el recorrido AppTest local: aproximadamente 464 MiB. No equivale a memoria/concurrencia medida en Cloud. AppTest no valida WebGL ni la interacción física del navegador. No se ha desplegado ni subido el archivo.

Archivo final: 356.299.346 bytes. SHA-256: `cd600739c59ed6aa4ba7ce68967337d049fd88880d875066da27d0978d932b74`. Se adjunta `data/deployment/madrid_rehab_v1_03.sha256` como comprobación independiente de descarga.

Resultado final focalizado: **60 pruebas superadas**, Ruff y `git diff --check` correctos. Registros por módulo en `reports/session_33_prtr/validation_01/`; resumen `reports/session_33_prtr/final_summary.json`. No se ejecutó la suite general completa.
