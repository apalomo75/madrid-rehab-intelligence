# Fuentes de subvenciones — auditoría 23/10/2026

No se han obtenido concesiones reales. No se asocia ningún importe ni ayuda a parcelas del piloto.

| Responsable / nombre | URL / endpoint | Formato / granularidad | Cobertura y fecha | Viabilidad y condiciones |
| --- | --- | --- | --- | --- |
| Comunidad · Ayudas a las actuaciones de rehabilitación energética de edificios residenciales y viviendas — PRTR | https://www.comunidad.madrid/vivienda/ayudas-actuaciones-rehabilitacion-energetica-edificios-residenciales-viviendas-prtr | Página informativa con enlace al visor; no dataset | Comunidad, programas 1/3/4/5; actualización del visor anunciada 20/07/2026 | La página acredita existencia del visor, no campos exportables ni licencia |
| Visor enlazado oficialmente · Visor de concesiones | https://visorrehabilitaprtrmadrid.coam.org/ | Visor; exportación no comprobada | Misma cobertura anunciada | HTTP 403 con herramienta web, DNS con Python. No inferir esquema ni RC |
| IGAE · Sistema Nacional de Publicidad de Subvenciones y Ayudas Públicas | https://www.infosubvenciones.es/bdnstrans/doc/swagger | API REST / exportaciones; convocatorias y concesiones separadas | España; actualización por registro, no comprobada para ayudas del piloto | OpenAPI verificado; no se obtuvo muestra. Identidad de beneficiario no localiza inmueble |
| IGAE · OpenAPI SNPSAP v1.1.0 | https://www.infosubvenciones.es/bdnstrans/estaticos/doc/snpsap-api.json | JSON documental; `/concesiones/busqueda`, `/concesiones/exportar` | Fecha de actualización del esquema no indicada | Base documentada `https://www.infosubvenciones.es/bdnstrans/api`; alternativas oficiales en el esquema |
| Ayuntamiento · Subvenciones Plan Rehabilita 2026 | https://transforma.madrid.es/rehabilitacion/ | Información y trámites; no concesiones estructuradas obtenidas | Madrid, programa anual | No convertir presupuesto de convocatoria en importe concedido |

Intentos acotados: consulta `.../api/concesiones/busqueda?page=0&pageSize=1&vpd=GE` en dominios infosubvenciones.es y subvenciones.gob.es: herramienta web devuelve inaccesible; Python devuelve error DNS. Visor COAM: 403, alternativa Python DNS. No se insiste ni se descargan beneficiarios masivamente. Evidencia técnica en `reports/session_6/source_attempts.json`.

El [manual oficial API](https://www.subvenciones.gob.es/bdnstrans/estaticos/ayuda/AYUDA%20-%20Sistema%20Nacional%20de%20Publicidad%20de%20Subvenciones%20y%20Ayudas%20P%C3%BAblicas%20v2023.pdf) remite a las [condiciones de reutilización](https://www.infosubvenciones.es/bdnstrans/GE/es/avisolegal). La documentación de una API no verifica automáticamente la licencia de cada publicación ni la localización del inmueble. Pendiente revisar condiciones antes de importar datos, filtrar programas y municipio, confirmar expedientes y fases y eliminar datos personales innecesarios.

Campos deseados aún no comprobados en registros reales: programa, concedente, fecha, estado, cuantía/moneda, expediente, dirección del inmueble, RC, barrio/distrito. Alternativa implementada: adaptador canónico local con niveles A/B/C, resumen de concesiones consistente y exclusión de conflictos. No se generan agregados territoriales sin registros reales.
