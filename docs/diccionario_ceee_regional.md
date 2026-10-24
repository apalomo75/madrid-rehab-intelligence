# Diccionario observado CEEE — sesión 13

Los dos recursos tienen las mismas 86 columnas originales. Este inventario describe nombres y uso de las variables, sin sustituir un diccionario oficial no disponible localmente. Las unidades no se presuponen. `column_profiles.json` en la auditoría contiene ausencias, cardinalidades y valores frecuentes por fichero; `source_inventory.json` conserva las categorías municipales, ámbitos y letras completas.

| Columna original | Interpretación y tratamiento |
| --- | --- |
| `edif_tiporeg` | Tipo de inscripción: existente, terminado, etc.; no es ámbito completo/unidad. |
| `edif_codreg` | Identificador de inscripción declarado; puede repetirse con contenido distinto. |
| `edif_direc` | Dirección literal; puede incluir puerta o vivienda. Uso local. |
| `edif_muni` | Municipio literal; puede contener errores, direcciones o valores ajenos. |
| `edif_codpost` | Código postal declarado; no se convierte en INE. |
| `edif_prov` | Provincia declarada; Madrid provincia no prueba Madrid municipio. |
| `edif_zonaclim` | Zona climática declarada. |
| `edif_año` | Año o período constructivo literal; no siempre numérico. |
| `edif_norma` | Normativa declarada. |
| `edif_refcat` | Una o varias referencias catastrales; admite formatos no soportados. |
| `edif_tipo` | Ámbito/tipología declarada; reglas explícitas del manifiesto. |
| `edif_proced` | Procedimiento/software declarado; puede variar metodología. |
| `edif_fecha` | Fecha declarada: semántica emisión/registro no verificada. |
| `edif_superf` | Superficie declarada; valor original, unidad sin verificar. |
| `edif_compac` | Característica declarada del inmueble/sistema; se conserva literalmente, sin inferencia de unidad. |
| `edif_calef` | Característica declarada del inmueble/sistema; se conserva literalmente, sin inferencia de unidad. |
| `edif_refrig` | Característica declarada del inmueble/sistema; se conserva literalmente, sin inferencia de unidad. |
| `edif_acrist` | Característica declarada del inmueble/sistema; se conserva literalmente, sin inferencia de unidad. |
| `edif_acs` | Característica declarada del inmueble/sistema; se conserva literalmente, sin inferencia de unidad. |
| `calefac_nombre` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `calefac_tipo` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `calefac_potenc` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `calefac_rendim` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `calefac_vector` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `calefac_modo` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `refrig_nombre` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `refrig_tipo` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `refrig_potenc` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `refrig_rendim` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `refrig_vector` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `refrig_modo` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `acs_nombre` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `acs_tipo` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `acs_potencnom` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `acs_rendim` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `acs_vector` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `acs_modo` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `acs_potenctot` | Descripción/parámetro de equipo térmico declarado; se conserva literalmente, incluidos centinelas. |
| `termica_nombre` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `termica_calef` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `termica_refrig` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `termica_acscons` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `termica_acsdem` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `elec_nombre` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `elec_energia` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `elec_reduglobal` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `elec_reduco2` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `elec_demglobal` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `elec_demcalef` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `elec_demrefrig` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `elec_demacs` | Descripción/indicador de contribución térmica o eléctrica declarado; no se interpreta como rehabilitación. |
| `final_global` | Indicador de energía final declarado por servicio; se conserva sin normalización de unidades. |
| `final_calef` | Indicador de energía final declarado por servicio; se conserva sin normalización de unidades. |
| `final_refrig` | Indicador de energía final declarado por servicio; se conserva sin normalización de unidades. |
| `final_acs` | Indicador de energía final declarado por servicio; se conserva sin normalización de unidades. |
| `final_ilu` | Indicador de energía final declarado por servicio; se conserva sin normalización de unidades. |
| `norenov_global` | Indicador global no renovable original; unidad sin verificar. |
| `norenov_calef` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_refrig` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_acs` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_ilu` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_co2global` | Indicador global de emisiones original; unidad sin verificar. |
| `norenov_co2calef` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_co2refrig` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_co2acs` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_co2ilu` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_co2elec` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_co2otros` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_co2electot` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `norenov_co2otrostot` | Indicador no renovable/emisiones desglosado; se conserva, no se mezcla con indicadores globales ni totales. |
| `cal_caleflimite` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_refriglimite` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_calefdem` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_refrigdem` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_norenovlimite` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_norenovglobal` | Letra global observada de energía primaria no renovable. |
| `cal_norenovcalef` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_norenovrefrig` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_norenovacs` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_norenovilu` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_co2limite` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_co2global` | Letra global observada de emisiones. |
| `cal_co2calef` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_co2refrig` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_co2acs` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |
| `cal_co2ilu` | Variable de calificación/límite por servicio según el nombre; se conserva literalmente, sin comparaciones de unidades no verificadas. |

Las columnas añadidas separan procedencia (`source_id`, `source_row`), identidad de contenido (`certificate_id`), identidad de inscripción (`identity_status`), municipio y su estado, ámbito conservador, fecha parseada y anomalías, letras A–G y valores numéricos con estado y unidad no verificada. Cada vínculo conserva referencia original, tipo, transformación, estado de checksum, nivel y motivo. Ninguna de estas variables acredita por sí sola identidad BU o vigencia.
