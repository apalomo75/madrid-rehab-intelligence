# Calidad del matching de eventos

Estado efectivo: sin registros nuevos, sin matching ejecutado de fuentes de sesión 8. No hay precisión, recall ni porcentaje de éxito medibles. Las pruebas artificiales verifican reglas, no rendimiento sobre expedientes reales.

## Contrato conservador vigente

`events.match_events` conserva ID/organismo, referencia literal y normalizada, dirección literal/normalizada, URL, fecha de extracción y estado administrativo. Confirma **parcela** solo ante RC explícita con una única fila CP; varias CP quedan ambiguas. Dirección sin padrón validado queda candidata. Para ayudas exige `location_role=subsidized_property`; beneficiario u órgano no localizan la actuación. No se confirma edificio físico por RC14.

`territory.event_territories` distingue territorio declarado de verificado. `event_features.load_event_snapshot` verifica manifiesto, tipo, hash del producto, filas y misma captura CP. Los agregados existentes solo usan parcela confirmada y única; concesiones se concilian globalmente por organismo/programa/expediente, excluyendo discrepancias de importe, moneda, fecha o localización. Pagos no se suman a concesiones. Varias publicaciones consistentes no multiplican euros.

`public_events` añade tipo de evento, captura/versión y estado `normalized_requires_review`. No autoriza importación por sí solo. El adaptador de inspección urbanística 2019 produce distrito declarado válido o sin localización, nunca parcela. No debe pasarse al agregador de ITE/IEE. La fecha mensual no se convierte en un día ficticio.

## Revisión obligatoria de una futura captura

| Evidencia disponible | Tratamiento |
| --- | --- |
| RC válida y contrastada, CP única y municipio concordante | Posible vínculo confirmado en parcela, conservar corte temporal |
| Identificador oficial con equivalencia documentada | Adaptador y control de equivalencia pendientes |
| Dirección única tras nomenclátor oficial y comprobaciones | Candidato revisable; automatización todavía no implementada |
| Coordenada con CRS/precisión y prueba espacial | Candidato revisable; matching espacial de eventos pendiente |
| Solo distrito oficial de la actuación | Agregado territorial, sin punto de parcela |
| Calle sin portal, beneficiario u órgano concedente | No forzar vínculo al inmueble |

Para cada captura medir registros, identidad/duplicados/conflictos, fechas, importes y moneda, geografía disponible, RC contrastadas, direcciones completas, fuera de municipio, fronteras, ambiguos y no vinculables. Reportar por separado precisión administrativa, espacial y temporal. No confundir «no se pudo localizar» con «no existe». Direcciones duplicadas, múltiples edificios/RC, cambios de estado y publicaciones históricas requieren conservar evidencia sin elegir primera fila. No se ha implementado geocodificación ni una regla de proximidad automática.

La auditoría municipal existente detecta RC con multiplicidad y fronteras; no debe eliminarse ese control para aumentar coincidencias. La deduplicación entre PRTR y BDNS necesita una equivalencia de expediente verificada: pendiente por falta de registros. No sumas a parcela cuando hay incertidumbre de inmueble o ámbito vivienda/edificio.
