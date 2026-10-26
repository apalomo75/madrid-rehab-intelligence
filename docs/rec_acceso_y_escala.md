# REC y RIEECM: acceso y escalado — 26/10/2026

**Estado B: consulta individual pública documentada; ingesta automatizada y reutilización no acreditadas.** El acceso HTTP desde este sandbox presenta además un bloqueo técnico DNS. Cero dictámenes reales incorporados. No se considera resuelta la integración por disponer de parser.

## Evidencia y consulta municipal

La [consulta municipal](https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons) muestra un formulario por expediente, registro o vía y advierte que la información no es certificado. La [Sede](https://sede.madrid.es/portal/site/tramites/menuitem.62876cb64654a55e2dbd7003a8a409a0/?vgnextoid=8fe1b4173fd61110VgnVCM2000000c205a0aRCRD) documenta la distinción entre resultados públicos e información personal o expedientes en tramitación sujetos a interés legítimo. No se accedió a estos últimos.

La [FAQ oficial](https://www.madrid.es/portales/munimadrid/es/Inicio/Vivienda-urbanismo-y-obras/Preguntas-frecuentes-sobre-Inspeccion-Tecnica-de-Edificios-ITE-/?vgnextchannel=593e31d3b28fe410VgnVCM1000000b205a0aRCRD&vgnextfmt=default&vgnextoid=3e0c3d77f8b06310VgnVCM1000000b205a0aRCRD) explica que subsanar una orden no transforma el dictamen original en favorable: la subsanación se anota en el expediente relacionado. Esta distinción debe preservarse en cualquier futura importación. Contacto técnico publicado: ite@madrid.es; información ciudadana: 010.

| Aspecto | Verificado en esta sesión |
|---|---|
| Entrada pública | GET mediante herramienta web, formulario informativo visible |
| POST `opcion=6&origen=I&ndp=11140360` | Observación previa del usuario; **no reproducido** |
| GET equivalente al POST | No demostrado; no probado como sustituto |
| Campos reales HTML/name, action | No disponibles en bytes; representación web no permite certificarlos |
| Cookies indispensables / sesión ausente | Desconocidas; no se reutilizaron cookies del usuario |
| Redirecciones, JavaScript obligatorio, controles | No determinados para ficha individual |
| ISO-8859-1 | Hipótesis previa compatible con texto mal decodificado; no confirmación de cabecera |
| Variaciones de fichas | No verificables sin HTML real |
| Autorización automatizada | No acreditada; no se lanzó POST ni enumeración |
| Parser | 20 pruebas REC sintéticas dentro de las 40 de conservación; no validación real |

No se solicitó el expediente manual `511/2026/12707` ni se materializó su supuesto resultado. Tampoco se almacena como acta la descripción aportada por el usuario.

## Diagnóstico preciso y reproducción fuera del sandbox

`socket.getaddrinfo` falla para `servpub.madrid.es` y `www.rieecm.es`: `gaierror -3 Temporary failure in name resolution`. El GET urllib municipal falla en la misma fase. **No hubo conexión TLS ni respuesta HTTP**, por tanto no se atribuye error HTTP, de sesión o de parser al Ayuntamiento. La herramienta web es una vía distinta y puede leer documentación; esto no proporciona cookies ni respuesta POST al proceso Python.

Manifiesto local: `data/raw/rec/session_15_diagnostic_01/manifest.json`, fecha UTC, URL, método GET, cero parámetros, HTTP nulo, cero consultas de registros. No hay HTML que hashear.

En Ubuntu, ejecutar una única comprobación de la portada, con salida nueva:

```bash
PYTHONPATH=src .venv/bin/python -m madrid_rehab.rec_diagnostic \
  --output-dir data/raw/rec/session_15_ubuntu_01
```

El comando no consulta NDP, no envía POST, no sigue redirecciones, usa sesión propia en memoria y no guarda valores de cookies ni tokens. Máximo 20 segundos y 2 MB. Guarda bytes y SHA-256 solamente si recibe la portada; permisos 0700/0600. Código 2 indica fallo; no se interpreta como portal caído. Si devuelve una redirección, debe revisarse manualmente. No convertir el comando en bucle.

Para confirmar el patrón individual, el siguiente paso es abrir el formulario oficial en el navegador del usuario, introducir la dirección y revisar la solicitud ordinaria en Herramientas de desarrollo → Red, únicamente para esa consulta pública. Confirmar método, nombres de campos, secuencia, charset y respuesta, sin compartir cookies ni tokens. Ante CAPTCHA, autenticación o contenido reservado, detenerse. La observación manual no autoriza automatización posterior.

Si se obtiene legítimamente HTML real, mantenerlo bajo `data/raw/rec/` (ignorado), con método, parámetros no sensibles, fecha, HTTP, URL final y SHA-256. Ejecutar `parse_rec(bytes, source_id=..., observed_at=..., synthetic=False, encoding=...)` de `madrid_rehab.rec`. Antes de importar, comparar expediente, tipo, presentación, dictamen, literal de deficiencias y subsanación con sección/celda original. Registrar cada campo como lectura confirmada, parser pendiente o desconocido. La futura ficha de verificación deberá incluir hash y ubicación de evidencia; actualmente **no existe ninguna ficha de verificación real**.

## NDP y CP

La evidencia local histórica de callejero contrasta `11140360` con Ezequiel Peñalver 8, vía 285300 y distrito 21. El puente mantiene `28900M01100041`; no es RC urbana aceptada por el normalizador vigente. Resultado: dirección concordante, **sin CP confirmada**. No se modifica el normalizador ni se fabrica una relación. Un acceso con varios candidatos debe conservarlos y solicitar selección; ninguno adquiere confirmación por ser el primero.

## Registro autonómico

| Componente | Estado |
|---|---|
| [Información técnica regional](https://www.comunidad.madrid/vivienda/informe-evaluacion-edificios) | Disponible; documentación, no extracto poblacional |
| [RIEECM](https://www.rieecm.es/portal/home) | Consulta individual indexada por municipio/dirección o registro; apertura directa dio timeout |
| Dataset IEE | Pendiente: el [catálogo oficial](https://www.comunidad.madrid/gobierno/datos-abiertos) aún lo anuncia entre próximos conjuntos |
| API, descarga con RC y resultados | No verificables; ninguna acreditada |
| Cobertura regional exhaustiva | No verificada; depende de remisión municipal |
| Estadísticas | Portal indexado anuncia sección; no se obtuvo extracto agregado ni licencia |
| Reutilización de informes/notas | Restringida o requiere autorización; no se presume abierta |

El [proyecto presupuestario 2026](https://www.comunidad.madrid/sites/default/files/doc/hacienda/2026-proyecto-libro-16-transportes.pdf) describe colaboración para integrar el registro en datos abiertos condicionada a mejoras del volcado municipal. Es planificación, no prueba de publicación. La comprobación actual del catálogo mantiene esa diferencia.

El [aviso legal RIEECM](https://www.rieecm.es/portal/home/aviso_legal) restringe reproducción/distribución comercial sin autorización y distingue uso personal privado. Documenta cookies CAKEPHP y edificios-seleccionados: **son del portal regional, no del REC municipal**. Contacto publicado `inforiee@madrid.org`; órgano regional: Dirección General de Vivienda y Rehabilitación, según [trámite oficial](https://sede.comunidad.madrid/comunicaciones-declaraciones/tramite-previo-evaluacion-edificios). No se envió comunicación.

## Escenarios sostenibles

| Escenario | Evidencia actual | Diseño futuro, sujeto a autorización |
|---|---|---|
| A, descarga oficial | No acreditada | Importar extractos versionados, licencia y hashes; validar esquema, fechas, identidad y bajas |
| B, API documentada | No acreditada | Límites oficiales, caché, trazabilidad, backoff documentado, sin superar controles |
| C, convenio | Solicitud pendiente de envío autorizado | Extractos mínimos periódicos, sin propietarios ni técnicos; canal seguro y revisión de permisos |
| D, consulta individual | Servicio público documentado; patrón NDP sin verificar | Enlace al formulario, consulta humana puntual; sin recolector |
| E, sin acceso reutilizable | Estado operativo de la integración | Mantener antecedentes administrativos y resultado pendiente de consulta |

Más de 200.000 accesos no justifican 200.000 consultas. La unidad del extracto debe separar acceso, parcela, edificio, inspección y actuaciones. Los estados posteriores deben ser eventos fechados, sin sobrescribir dictámenes históricos. Identidades ambiguas y CP en cuarentena permanecen fuera de confirmación. Ningún escenario autoriza ejecución automática en esta sesión.

## Borrador de solicitud institucional — NO ENVIADO

A los responsables del REC municipal y del Registro autonómico IEE:

Solicito información sobre la disponibilidad de un extracto reutilizable o API autorizada para investigación territorial de conservación, accesibilidad y rehabilitación energética. El proyecto personal Madrid Rehab Intelligence integra evidencia pública y no actúa en nombre de UCI ni de otra entidad. Su finalidad es facilitar estudios explicables y detectar información pendiente, sin diagnóstico físico ni evaluación crediticia.

Se solicita, en la medida legalmente accesible: identificador técnico de registro/expediente, municipio, NDP donde exista, referencia catastral documentada, identificador de edificio si lo hubiera, tipo y alcance ITE/IEE, fecha de presentación y evaluación, dictamen, categorías objetivas de deficiencias, actuaciones y fechas de subsanación acreditada, fecha de actualización y cobertura conocida. También sería útil un extracto agregado por municipio y periodo si el detalle no puede facilitarse.

No se solicitan nombres, DNI, contactos, propietarios, técnicos, firmas ni documentos personales. Rogamos indicar campos públicos/restringidos, licencia, condiciones para análisis privado y demostración a terceros, redistribución de derivados, periodicidad, límites de acceso y canal autorizado. No se iniciará consulta por lotes sin autorización explícita. Agradeceríamos conocer el estado de la anunciada integración regional en datos abiertos y un interlocutor técnico para validar identidades y semántica temporal.
