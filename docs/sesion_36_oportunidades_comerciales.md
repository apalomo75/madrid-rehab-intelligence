# Sesión 36 · Oportunidades comerciales

Revisión del 17/11/2026 sobre v1.04 (`data/deployment/madrid_rehab_v1_04_candidate_01/`, base local de su archivo de distribución). No se modifica ni reconstruye el paquete. Cambios de presentación; revisión visual local pendiente.

## Entrega

| Funcionalidad | Datos realmente disponibles | Implementado | Pendiente y motivo | Actualizar paquete |
| --- | --- | --- | --- | --- |
| Libro del Edificio / proyectos | 899 P5 originales; 718 expedientes confirmados en 680 CP del paquete | Sección compacta ES/EN con etiqueta conjunta, P5, expediente, importe, estado y fuente; solo CP confirmada | Distinguir actuación en público requiere incorporar `subprograma`; elaboración efectiva no acreditada | No para etiqueta conjunta; sí para desglosar actuación |
| Filtro Libro / proyectos | P5 ya seleccionable dentro de NextGenerationEU | Se conserva selector P5, sin quinta casilla redundante | No se añade otro filtro que seleccione lo mismo | No |
| ITE/IEE desfavorable | Obligaciones, órdenes históricas y consultas individuales oficiales; sin producto de resultados reutilizable acreditado | Se mantienen distinciones y aviso de resultados no acreditados; sin filtro nuevo | Exportación autorizada con resultado individual, fecha, ámbito, identidad y subsanaciones | Solo si se integra una nueva fuente |
| Administradores | Directorio profesional colegial; sin cartera verificable comunidad–administrador | No se crean fichas vacías ni atribuciones | Relación autorizada con identidad de comunidad, vigencia, profesional y puente documental a CP | Solo si existe fuente integrable |
| Fechas | Fechas administrativas ISO y certificados ya incluidos | Presentación central ES `DD/MM/AAAA`, EN `DD Mon YYYY`; medianoche sin hora | Revisión visual de todas las pantallas, escritorio/móvil | No |

## Auditoría P5 reproducible

`tests/audit_session36.py` verifica SHA-256 original, expedientes, importes y estados contra el GeoJSON preservado. Resultado: `reports/session_36_opportunities/audit_01.json`.

- 7.532 expedientes originales; 899 P5 únicos: `pr5_Libro` 706, `pr5_Todo` 185, `pr5_Proyecto` 8. El original sí distingue modalidades; `Todo` agrupa libro/proyecto, sin acreditar entrega de ninguno.
- 718 expedientes P5 con relaciones confirmadas a CP aceptada: 719 relaciones y 680 referencias únicas en v1.04. Un expediente puede relacionarse con varias parcelas; no sumar importes por relación.
- Expedientes por municipio: Madrid 523, Móstoles 81, Alcalá de Henares 45, Alcorcón 40, Leganés 22, Getafe 7. Los restantes 181 P5 no tienen relación confirmada en este producto de seis municipios; no equivale a expediente falso ni ausencia de ayuda fuera del ámbito.
- Entre los 718 confirmados: 580 Libro, 130 Todo, 8 Proyecto, según cruce offline por expediente con el original. Este cruce es auditoría, no una consulta de la app a datos externos al paquete.
- Los 899 tienen importe y estado `APROBACIÓN CONCESIÓN`. No hay fecha individual de concesión/pago, documento entregado, justificante, aprobación del libro ni finalización. Actualización de fuente 20/07/2026 y captura 24/10/2026 no son fechas de concesión.
- El producto público conserva programa, estado, importe y fuente, pero omite `subprograma`. Se usa la etiqueta conjunta solicitada y se explica esa limitación. No se activa un nuevo ETL ni se aumenta cobertura.

La ficha deduplica P5 por expediente y solo presenta `Quality.PARCEL` en CP; excluye relaciones ambiguas y BU. P5 pasa a su sección específica para evitar repetir sus importes en el resumen PRTR general. La atribución PRTR y los permisos del paquete permanecen vigentes. No acredita comunidad identificada, documento elaborado, pago ni obra ejecutada.

## Investigación oficial ITE/IEE

Búsqueda de páginas oficiales y registros regionales, sin consultas a edificios, POST ni extracción de formularios. No es una prueba de inexistencia de bases internas. No se ha localizado durante esta revisión una descarga/API de resultados individuales con contrato de reutilización suficiente. Se distingue obligación → presentación → dictamen favorable/desfavorable → subsanación; una orden puede tener otros motivos y no sustituye el dictamen.

| Ámbito | Evidencia oficial revisada | Falta para integrar |
| --- | --- | --- |
| Madrid | [Consulta del resultado ITE](https://sede.madrid.es/portal/site/tramites/menuitem.62876cb64654a55e2dbd7003a8a409a0/?vgnextoid=8fe1b4173fd61110VgnVCM2000000c205a0aRCRD): consulta individual favorable/desfavorable. [FAQ REC](https://www.madrid.es/portales/munimadrid/es/Inicio/El-Ayuntamiento/Preguntas-mas-frecuentes-del-Registro-de-Edificios-y-Construcciones-REC-?vgnextoid=ab11f32bea3f4410VgnVCM1000000b205a0aRCRD) distingue órdenes y otros antecedentes | Exportación autorizada reutilizable, identificadores documentales y fechas/rectificaciones; consulta pública individual no autoriza recopilación masiva |
| Getafe | [Preguntas de Urbanismo](https://getafe.es/delegaciones/urbanismo/urbanismo-y-obras-publicas/actuaciones/preguntas-frecuentes-en-materia-de-licencias-de-obra-y-actividades/12/): presentación por registro; [visor EMSV](https://visorpublicoemsv.emsvgetafe.org/) a escala edificio, página sin contenido legible en esta revisión | No se verifica esquema/exportación de resultados ni licencia del visor; no atribuirle dictámenes sin comprobar |
| Alcorcón | [Listado IEE 2026](https://www.ayto-alcorcon.es/es/node/15795) y [2024](https://www.ayto-alcorcon.es/es/node/8733): obligaciones, no resultados | Dictámenes individuales autorizados, fecha y estado de subsanación |
| Alcalá de Henares | [Página municipal ITE](https://urbanismo.ayto-alcaladehenares.es/inspeccion-tecnica-de-edificios/): régimen de inspección y periodicidad | No se localiza exportación de resultados con vínculo verificable/licencia |
| Leganés | Búsquedas dirigidas al dominio municipal no devuelven conjunto individual pertinente. Se revisa la vía regional RIEECM aplicable al municipio | Descarga municipal/regional autorizada; cobertura y resultados no verificados, no tasa cero |
| Móstoles | Búsqueda municipal devuelve documentación administrativa y tasas, sin conjunto verificable de resultados; vía regional aplicable | Igual: resultados, ámbito, identificadores y permiso; no se usa normativa ni tasas como evidencia individual |

[Comunidad de Madrid · IEE](https://www.comunidad.madrid/vivienda/informe-evaluacion-edificios) describe la presentación municipal y remisión al registro regional. [RIEECM](https://www.rieecm.es/portal/home) permite buscar por municipio/dirección/número o registro y descargar nota informativa: es una vía para revisión individual, sin exportación masiva ni permiso suficiente verificados aquí. No se enviaron búsquedas ni se descargaron notas de edificios.

Próximo paso documental: solicitar a titulares exportación de referencia catastral/identificador estable, fecha de presentación, dictamen, alcance, subsanaciones y condiciones de reutilización comercial, excluyendo datos personales innecesarios. No se envió ninguna solicitud. El filtro ITE/IEE existente conserva su semántica de menciones documentadas, nunca se renombra como desfavorable.

## Administradores de fincas

[CAFMadrid](https://cafmadrid.es/) y su [nota oficial del buscador](https://cafmadrid.es/wp-content/uploads/2025/01/Ndp-Nueva-web.pdf) documentan búsqueda de profesionales, incluida localización por código postal. Un despacho o profesional en una zona no prueba mandato de una comunidad concreta. No se verifica exportación autorizada de carteras, identificador comunitario, relación vigente, dirección comunitaria ni referencia catastral. Los contactos profesionales de un directorio tampoco autorizan su redistribución o atribución a parcelas.

No se desarrolla piloto: faltan simultáneamente relación verificable y reutilización acreditada. Un futuro piloto necesitaría comunidad identificada independientemente de CP/BU, administrador/despacho y contacto profesional autorizado, fechas de mandato, dirección de comunidad, puente documental no ambiguo a CP y licencia/base de publicación. No se usan UCI, contactos privados ni proximidad geográfica para inferir administradores.

## Fechas y continuidad

`i18n.present_dates` centraliza la presentación y `readable_date` delega en ella. El adaptador de vistas públicas lo aplica al texto renderizado y a columnas de fechas/periodos de tablas, sobre copias; no modifica fuentes, modelos, índices, hashes, valores internos de selectores o cachés. Fechas ISO válidas y medianoche pierden hora; horas distintas de cero se conservan en textos sin contexto temporal y consultas/capturas por posible relevancia. En columnas administrativas y resumen de certificados se omiten también horas distintas de cero; los valores originales se conservan. Se conservan cadenas desconocidas, años, identificadores y URLs. EN usa meses abreviados explícitos, independiente de la configuración regional del sistema.

Se mantienen Municipio → Distrito → Barrio, cuatro filtros, OR/AND, mapa/ficha 65/35, paginación y búsqueda. Pantallas históricas de desarrollo siguen fuera del alcance público. Sin fuentes nuevas, cambio de permiso ni paquete candidato nuevo.

## Validación y revisión local

```bash
.venv/bin/ruff check src tests
PYTHONPATH=src:tests .venv/bin/python -m unittest test_session36 test_i18n test_session31 test_public_prtr test_filter_simplification test_neighborhoods test_session30_ux test_commercial_filters test_filter_navigation -q
PYTHONPATH=src .venv/bin/python tests/audit_session36.py --output reports/session_36_opportunities/audit_nuevo.json
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_04_candidate_01 MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Auditoría siempre con nueva salida. Revisión pendiente: P5 en CP confirmada, ausencia en BU/ambiguos, ES/EN, fechas de certificados y expedientes en resumen/desplegables, mapa y controles escritorio/móvil. AppTest no valida WebGL. Sin commit, push, despliegue ni publicación.


Validación ejecutada: Ruff y `git diff --check` correctos; 52 pruebas del conjunto focalizado inicial superadas; tras ajustar el formato del resumen, 11 pruebas P5/fechas/CEEE superadas, y 7 pruebas finales de sesión 36 (incluida ficha P5 real ES/EN, datetime administrativo y preservación del original). El grupo i18n pasó además sus 14 pruebas con sesión 36 inicial. No se ejecutó la suite completa.

`reports/session_36_opportunities/navigation_01.json`: benchmark público v1.04 correcto en 29,97 s, RSS máximo 436,70 MiB. Los Rosales 904, Gaztambide 555, CEEE+PRTR 348 OR / 18 AND; primera/intermedia/última página, límite 500, ES/EN y guard de lecturas dentro del bundle. Son mediciones locales, no garantías de Cloud.

`reports/session_36_opportunities/browser_check_01/browser.json`: **validación visual bloqueada** por ausencia del ejecutable Chromium. No se descargó navegador. No valida WebGL ni móvil; revisión del propietario pendiente. Los registros de pruebas se conservan en el mismo directorio de informes. Los cambios previos del propietario en documentación/autorización PRTR y configuraciones se conservan sin alterarlos.
