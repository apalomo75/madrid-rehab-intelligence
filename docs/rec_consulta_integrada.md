# Sesión 15.1 — Consulta integrada ITE/IEE por NDP

## Estado y arquitectura

La ficha existente incorpora «ITE / IEE — Registro municipal». La consulta HTTP permanece **deshabilitada**: no están acreditadas las condiciones específicas de automatización y reutilización REC. No se realizaron consultas REC durante el desarrollo. Base local revisada: commit `ebe1e36`, con cambios previos de las sesiones 15 y validación real sin commit; se conservaron esos cambios.

Componentes nuevos:

- `rec_client.py`: validación NDP, URL oficial, política explícita, proveedor HTTP y proveedor local independiente, validación de respuesta y errores tipados.
- `rec_view.py`: selección de portal, dos botones independientes, estado temporal, representación de inspecciones y actuaciones.
- `tests/test_rec_client.py`: pruebas unitarias sin red y pruebas de interacción Streamlit AppTest.

Se amplía `conservation_view.py`, invocado por `administrative_view.render_parcel_events` en las fichas municipales existentes. `regional_view.py` presenta la misma sección: fuera de Madrid no utiliza COD_NDP municipal y ofrece la consulta general. Se actualiza una aserción obsoleta de `test_conservation.py`. No cambia la navegación, ni integra REC en exportaciones, demos o productos de otras fuentes. No se modifica el parser validado ni los snapshots anteriores.

## Identificación y callejero

Se usa `conservation_view.parcel_evidence(ref, "rec_accesses", municipality)`, con comprobaciones existentes de política, hash del producto y correspondencia del CP municipal. El producto consulta el puente completo `conservation_parcel_links.parquet` por referencia confirmada o candidata, para hacer visibles también las ambigüedades que las particiones históricas de accesos confirmados excluyen. El producto procede del puente documental callejero–Catastro auditado; `access_links` comprueba globalmente duplicidades/conflictos y disponibilidad/calidad de CP antes de particionarlo.

Solo se ofrecen NDP de ocho dígitos ASCII, de Madrid 28079, con `link_status=confirmed_access_parcel`, `confirmed_parcel_ref14` igual a la selección y dirección oficial completa. Versiones contradictorias del mismo NDP o diferentes direcciones se rechazan. Las relaciones candidatas/ambiguas se anuncian y no habilitan consulta. No se buscan vecinos ni se recupera una referencia por proximidad.

El selector comienza vacío, incluso si solo hay un acceso. Cada opción contiene dirección, número, NDP y calidad. Se muestran municipio e identificador catastral. Con varios accesos el usuario debe elegir expresamente. Sin NDP se muestra «No se ha identificado un acceso municipal suficientemente verificado» y el botón oficial abre el buscador general.

El NDP 11140360 coincide con el callejero, pero su CP sigue sin confirmar. No aparece como acceso de una parcela atribuida automáticamente. El uso de ese NDP con un CP ficticio en AppTest es exclusivamente una fixture de interfaz, sin escritura de datos ni relación real: las pruebas de conservación verifican por separado el estado real `unmatched_access`.

## URLs y consulta externa permanente

`official_url` acepta únicamente NDP validado y construye parámetros con `urlencode`:

`https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons?opcion=6&origen=I&ndp=<NDP>`

Sin selección, usa `https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons`.

«Abrir ficha oficial del REC» es un `st.link_button`, que abre una pestaña nueva. Está fuera del bloque de petición y no depende de caché o éxito. Sigue visible con consulta deshabilitada, errores, respuesta sin inspecciones y resultados correctos. El enlace externo nunca se presenta como una consulta integrada.

## Habilitación y permisos

El valor predeterminado es `REC_LIVE_ENABLED=false`. La política requiere simultáneamente:

- `REC_LIVE_ENABLED=true`, decidido explícitamente por el operador después de revisar permisos.
- `REC_AUTOMATION_EVIDENCE`: referencia al documento que acredita automatización para esta finalidad.
- `REC_REUSE_EVIDENCE`: referencia que acredita el tratamiento y visualización previstos, incluida memoria temporal.
- Modo privado y sin `MADRID_REHAB_OFFLINE=1`.

Las referencias son una declaración administrativa del operador, no una verificación automática de autenticidad o suficiencia jurídica. No se han configurado permisos reales. La conectividad nunca habilita nada. El modo público impide cargar accesos, consultar y mostrar resultados; conserva el enlace general oficial. No se crea una excepción pública a las protecciones existentes.

Automatización específica REC: **no acreditada**. Reutilización específica REC: **pendiente de confirmar alcance y condiciones**. La revisión del aviso general municipal de la sesión anterior no basta para activar este módulo. Véase `docs/rec_real.md`. Este desarrollo no vuelve a consultar documentación externa ni fichas individuales.

## Cliente y parser

Una sola petición GET, únicamente después del clic y para el portal seleccionado. El proveedor usa urllib de la biblioteca estándar, timeout de socket de 15 segundos y lectura máxima de 2.000.000 bytes. No hay reintentos, concurrencia, precarga, enumeración, cliente de cookies ni uso de proxies del entorno. Las redirecciones ordinarias están limitadas a tres y al mismo endpoint HTTPS oficial; se rechaza otro NDP explícito en la URL de destino. Redirecciones a otros endpoints requieren revisión y no se siguen.

Valida HTTP 200, tipo HTML, tamaño y longitud cuando está disponible, codificación, cierre HTML, sección de acceso y errores conocidos de sesión. Usa el charset HTTP o ISO-8859-1 por defecto. No ejecuta JavaScript. Un formulario sin resultados no es una inspección vacía válida.

`rec.parse_rec` mantiene expedientes independientes, fechas literales e ISO, dictámenes, causas, alcance, dependencias, actuaciones y relaciones de seguimiento/antecedentes. Las inspecciones incompletas o advertencias del parser bloquean la representación como éxito. La dirección se contrasta conservadoramente con el callejero: solo se toleran diferencias de partículas DE/DEL/LA/LAS/LOS. Otras abreviaturas pueden exigir revisión humana. Si el HTML contiene NDP se compara; si no, se declara que el NDP procede de la solicitud y solo se pudo contrastar la dirección. No se afirma confirmación independiente de NDP en un HTML que no lo contiene.

No es un validador general de todas las variantes del portal. Un formato desconocido debe revisarse con bytes legítimamente obtenidos antes de ampliarlo. La falta de inspecciones solo se admite en una respuesta identificada como ficha REC y con sección de presentadas reconocida.

## Estados e interfaz

Estados diferenciados: deshabilitada, sin NDP confirmado, acceso ambiguo, sin inspecciones en la respuesta consultada, conexión inaccesible, timeout, HTTP no satisfactorio (con código), HTML inesperado, formulario, sesión, respuesta incompleta, error de parser, identidad incompatible y éxito. Una conexión fallida no se convierte en ausencia de ITE ni en resultado favorable.

Se representan dirección, NDP, fecha UTC de consulta, fuente y calidad de vinculación. Para cada inspección: expediente, tipo, presentación, dictamen, alcance, causa, situación y dependencia. El historial mantiene filas independientes, resoluciones, seguimiento, antecedentes, multas y la actuación sin expediente. Se muestran literales y se advierte que archivo/terminación no acreditan subsanación. No se declara estado físico actual ni se extienden deficiencias a edificios compartiendo parcela.

Advertencia permanente: «Información orientativa procedente del REC municipal; no constituye una certificación oficial».

## Memoria y almacenamiento

No hay caché persistente, HTML persistido por el cliente, tokens, cookies, descarga ni exportación. La interfaz conserva como máximo la última respuesta estructurada o error en `st.session_state`, con TTL de 300 segundos comprobado en cada render. Al cambiar parcela, municipio, acceso o política, se invalida. En sesiones inactivas, la eliminación física depende del siguiente render o del cierre de sesión; nunca se vuelve a mostrar una entrada caducada. Antes de consultar se borra el resultado previo, por lo que un error nunca se sustituye silenciosamente por datos anteriores.

Se descartan las filas/bloques completos del parser antes de guardar el resultado temporal. Las pruebas no escriben nuevos HTML. La evidencia auténtica histórica conservada y autorizada en la sesión anterior sigue bajo `data/`/`reports/` ignorados; no es una caché operativa nueva ni se carga en la aplicación como supuesto resultado actual.

## Reproducción local y validación

El proveedor `LocalProvider` se inyecta exclusivamente en pruebas Python, separado de `HttpProvider`, sin selector ni configuración que lo active en la aplicación. Su resultado indica `local_historical`; la interfaz lo marca «Captura local histórica de prueba; no es una consulta actual al REC».

La prueba auténtica usa `data/raw/rec/real_11140360_01/ficha.html`, preservado a partir de `/tmp/rec-test/ficha.html`; SHA-256 `22c9f480465abf5fb8dd0a6f19f21512418105fc0254df674c3463e556be7b9f`. La validación previa de 67 campos se conserva en `tests/test_rec_real.py` y `reports/rec_real/review_02/`. El flujo nuevo comprueba dos inspecciones, cinco actuaciones, dictamen desfavorable, archivo histórico y procedencia local. Si falta el HTML privado las pruebas que lo necesitan se omiten explícitamente; las demás comprobaciones no se omiten por ese motivo.

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_rec_client.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_rec_real.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_conservation.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check src tests
```

AppTest verifica selección vacía, cero consultas al abrir/seleccionar, botones tras éxito/error, resultado auténtico local, invalidación, caducidad y modo público. No sustituye una revisión visual en navegador ni una prueba real de conectividad. El acceso HTTP real, las redirecciones reales y variantes de sesión del servicio no se han probado; los errores HTTP/conexión se simulan sin red.

Ejecutar la aplicación normal, manteniendo REC deshabilitado:

```bash
REC_LIVE_ENABLED=false PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Antes de habilitar solicitudes reales: acreditar automatización individual para esta finalidad y límites del servicio; acreditar reutilización y memoria temporal; registrar las referencias de aprobación; revisar privacidad, ámbito y vigencia; acordar una consulta individual seleccionada para contrastar cabeceras, redirecciones e identidad real. No ejecutar lotes ni adoptar el éxito de una ficha como permiso general. El módulo debe permanecer deshabilitado mientras estos puntos estén pendientes.

## Resultado de la entrega

Validación final del 26/10/2026: **448 pruebas de la suite completa, todas correctas** (260,960 s), incluidas 21 del componente nuevo, la prueba auténtica de 67 campos y 40 de conservación. Ruff y el formato de los seis módulos/pruebas afectados pasan. Los hashes del original temporal y de la copia privada coinciden; Git ignora el HTML y sus derivados históricos.

Se comprobaron conexión, timeout, HTTP 403/429/500, redirección permitida/rechazada, sesión caducada, formulario, HTML inesperado/incompleto, MIME/tamaño, identificación incompatible y fallo del parser. AppTest verifica los dos botones tras fallo y éxito, ausencia de consultas automáticas, selección múltiple, ausencia de acceso, caducidad y modo público. La regresión completa cubre las fichas existentes y comprobaciones de integridad de productos históricos.

Pendientes: acreditar automatización y reutilización específicas; realizar la primera comprobación HTTP autorizada de este cliente y una revisión visual en navegador. AppTest no se presenta como validación visual en Chromium. El módulo **debe permanecer deshabilitado**. No se han realizado commits, push, publicación ni cambios en snapshots históricos.
