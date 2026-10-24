# Calidad municipal — sesión 7

Los totales describen la captura local, no todos los fenómenos del parque inmobiliario. Una fila CP, una referencia RC14, un objeto BU, un inmueble RC20 y un edificio físico son unidades distintas. Se mantienen los estados fuente y se añade `analytic_status` a los enlaces, sin corregirlos silenciosamente.

## Universos y denominadores

- Fuente CP: 141.244 filas geométricas, 140.595 referencias. 216 referencias repetidas; 23 con filas en más de un distrito. No se elige la primera fila.
- Universo analítico: una fila por RC14. 140.557 referencias asignadas a distrito; 38 residuales. Las referencias con varias CP del mismo distrito conservan ese contexto territorial, pero la identidad CP sigue ambigua y no admite confirmación energética analítica.
- BU: 124.396 objetos, 124.395 con geometría utilizable. 124.392 con distrito espacial; cuatro sin asignación. Siete BU no tienen RC presente en CP. Se conservan en la auditoría; un BU no prueba edificio físico independiente.
- CEEE: 115.664 versiones de registro. Estados del registro: 113.072 confirmed, seis candidate, 66 ambiguous y 2.520 unmatched. El denominador de estos estados es 115.664, no el número de enlaces ni BU. Los seis registros parcialmente resueltos no se promocionan a confirmados.
- Evidencia analítica: 113.072 registros únicos y 113.082 pares registro/parcela (10 asociaciones adicionales por referencias múltiples). 51.860 referencias tienen al menos un registro confirmado. Veinte registros confirmados no tienen letra A–G interpretable; se conservan como información vinculada, no como letra cero.

La captura municipal CEEE procede de recursos 2025–2026, filtrados por el literal normalizado `edif_muni=MADRID`. La auditoría volvió a comprobar las 115.664 filas originales y que sus `record_id` se conservan en sesión 2. No se hallaron etiquetas de otro municipio en CP/BU ni literales de otro municipio en CEEE; las geometrías no asignadas no se reclasifican como otro municipio sin evidencia administrativa.

## Territorio y reconciliación

Se reproduce la asignación espacial de todas las geometrías contra los 21 límites oficiales locales: punto interior (`point_on_surface`) y prueba de pertenencia. Un punto en límite compartido se marca ambiguo; un punto fuera queda sin distrito. Cruces de superficie >0,01 m² se registran aparte (105 CP y diez BU) sin recortar ni duplicar la unidad. Hay 15 filas CP sin distrito. Una RC con filas en varios distritos o asignaciones incompletas queda residual en el modelo analítico.

Los totales por los 21 distritos más los residuales reconcilian CP, RC, BU, pares registro/parcela y parcelas con evidencia. En esta captura: 113.070 registros confirmados en distritos y dos solo en parcelas sin distrito; 51.858 parcelas con evidencia en distritos y dos residuales. No hay registros confirmados que pertenezcan a más de un distrito en esta captura. El código y tests contemplan ese caso: la suma de pertenencias distritales puede superar el número municipal de registros únicos. No sumar porcentajes, medianas ni distribuciones sin definir denominador.

`bu_spatial` asigna por geometría propia; `bu_by_parcel` usa contexto RC. Son medidas diferentes, especialmente en fronteras o referencias ambiguas; no se fuerzan a coincidir. La tabla de cobertura identifica ambas. La portada usa BU espaciales y referencia RC como universo analítico, y expone el residuo.

## Cruces y perfiles

Solo se incorporan al perfil enlaces con registro y referencia confirmados, RC globalmente única en CP y sin conflicto de código administrativo. Identidades contradictorias, claves vacías, enlaces huérfanos y estados contradictorios abortan con error. `analytic_status` distingue confirmed/candidate/ambiguous/unmatched/rejected; este último identifica un enlace declarado confirmado excluido por controles globales. Los motivos originales se conservan.

Las proporciones E/F/G usan solo letras A–G. Nulo no se convierte en cero. Los recuentos cero significan cero enlaces observados, no ausencia real de certificación. Registros se deduplican por `record_id`; pares, por registro/RC; agregados por grupo deduplican registro/grupo. Se conservan versiones de un código administrativo, sin elegir vigencia por orden de fila.

Perfiles: sin registros, sin letra interpretable, muestra escasa (1–2 letras), E/F/G en ≥75% de ≥3 registros y otras distribuciones. Son etiquetas de evidencia, no de necesidad. Se mantienen avisos por CP ambigua, varios BU, ámbitos heterogéneos, pocas letras y fecha desconocida. Sensibilidad: pesos 0/0,25/0,5/0,75/1 y mínimos 1/3/5/10, con población elegible explícita. No hay IPR global.

La malla es métrica de 500 m EPSG:25830, no barrio. Análisis usa punto de referencia CP única. Dibujo usa esa celda cuando está disponible y, en su ausencia, punto interior de la geometría. La asignación estadística por punto CP y la espacial por geometría se distinguen. Grupos <20 parcelas o <5 con letras ocultan proporciones comparativas, conservando tamaños. Esto no garantiza representatividad: la captura administrativa tiene sesgos de cobertura.

## Regresión y controles

Chamberí conserva 3.790 referencias, 3.761 identidades BU y 5.105 registros CEEE. Se comprueban las 47 columnas históricas compartidas de `session_6_audited`, además de identidad de registros y BU, con error si divergen. Columnas anuales municipales adicionales no alteran esas variables. Las 142 pruebas anteriores siguen ejecutándose; dos helpers AppTest invocan explícitamente el piloto histórico, manteniendo todas sus aserciones. Se añaden pruebas del acceso municipal real, lectura selectiva, caché, límites, multiparcela, estados, selección CP/BU, filtros y recorrido de los 21 distritos.

SHA-256 antes/después sobre entradas y manifiestos; hashes de salidas y código principal. El replay compara todos los Parquet, CSV estadísticos y JSON deterministas, excluyendo duraciones. Datos y reports permanecen ignorados por Git. No hay eventos oficiales reales ITE/IEE/ayudas ni registros sintéticos en productos.
