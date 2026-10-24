# Fuentes ITE/IEE — auditoría 23/10/2026

No se han obtenido registros reales ni se ha encontrado una exportación masiva verificable en esta auditoría. Esto no implica que no exista. La búsqueda en el catálogo municipal no identificó un dataset descargable adecuado; los resultados condujeron a servicios de consulta. No se automatizan formularios ni se extraen datos de propietarios/técnicos.

| Responsable / nombre exacto | URL oficial y acceso | Formato / granularidad | Cobertura / actualización | Integración / condiciones |
| --- | --- | --- | --- | --- |
| Ayuntamiento · Consulta del Registro de Edificios y Construcciones | https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons | HTML, formulario por ubicación/expediente; sin exportación verificada | Madrid; periodo y actualización desconocidos | Dirección/expediente requieren validación; RC no comprobada. Licencia de descarga no verificada |
| Ayuntamiento · Listado de Edificios Pendientes de Presentar I.T.E./I.E.E. | https://servpub.madrid.es/GITEP_WBINFORME/SGiteInforme | HTML, formulario | Madrid; cobertura temporal no comprobada | Obligación de presentar no equivale a inspección desfavorable. Sin descarga ni licencia verificadas |
| Comunidad · Informe de Evaluación de Edificios | https://www.comunidad.madrid/vivienda/informe-evaluacion-edificios | Página informativa, no dataset | Comunidad de Madrid; actualización no identificada | Describe remisión municipal al registro, no acredita acceso a registros |
| Comunidad · RIEECM | https://www.rieecm.es/portal/home | Consulta individual por número de registro | Comunidad de Madrid; fechas no verificadas | No se ha acreditado exportación ni licencia; no usar como API |

La [sede municipal sobre consulta ITE](https://sede.madrid.es/portal/site/tramites/menuitem.62876cb64654a55e2dbd7003a8a409a0/?vgnextchannel=92e637c190180210VgnVCM100000c90da8c0RCRD&vgnextfmt=d&vgnextoid=8fe1b4173fd61110VgnVCM2000000c205a0aRCRD) diferencia resultados consultables de información de propiedad, técnicos y expedientes que exige interés legítimo. No se incorpora esa información personal.

Evidencia: páginas consultadas mediante herramienta web; HTTP HTML accesible en ambos formularios. El acceso HTTP desde Python falla por DNS (registro en `reports/session_6/source_attempts.json`). No se han enviado solicitudes externas. Alternativa: contrato CSV canónico, validación, normalización y matching probados con fixtures exclusivamente en tests. Pendiente: exportación oficial con RC, tipo/fecha/resultado, estado y subsanación; confirmar licencia y corte temporal antes de importar.
