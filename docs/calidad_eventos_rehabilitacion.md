# Calidad de eventos y análisis de rehabilitación

El universo de observación son los archivos efectivamente aportados. Sus recuentos no representan toda la actividad administrativa de Madrid. La ausencia de eventos no significa ausencia de actuaciones, ayudas o necesidad.

La identidad catastral es de parcela CP. Una parcela puede contener varios BU, portales y expedientes; un NDP no equivale a edificio. La dirección normaliza acentos, espacios, abreviaturas explícitas, números y calificadores. No elimina partículas ni aplica similitud aproximada para aumentar cobertura.

La confirmación requiere un puente oficial inequívoco a una sola fila CP. Varias referencias para un NDP se conservan como multiparcela; varias filas CP son ambiguas. Conflictos de vía, dirección del NDP, distrito o distancia mayor de 100 m a la geometría referida se revisan. Este umbral es un control de discrepancia conservador, no una regla de confirmación por proximidad. Coordenadas ETRS89 se contrastan directamente con CP EPSG:25830; las coordenadas antiguas de Guía Urbana no se mezclan con ETRS89.

En órdenes antiguas sin tipo de vía, numeraciones múltiples o direcciones incompletas, no se fuerza identificación. Las consultas PDF conservan el literal de números extraordinarios, nulos y años de inspección discordantes; se excluyen de parcelas confirmadas y entran en `review_queue.parquet`. Los nulos repetidos no identifican edificios diferentes: las publicaciones se conservan, pero no permiten contar obligaciones físicas distintas.

| Indicador | Numerador | Denominador | Fecha y grano | Limitación |
| --- | --- | --- | --- | --- |
| Éxito de vinculación | Versiones con confirmed | Versiones normalizadas por fuente | Corte de archivos aportados; versión | No mide precisión física ni exhaustividad |
| Actividad anual | IDs distintos por tipo/año | No es una tasa | Resolución, alta, registro u obligación según fuente | Periodos no equivalentes |
| Parcelas con eventos | RC14 distintas confirmadas | Universo CP si se informa cobertura | Parcela y captura CP declarada | No edificios afectados |
| Repetición | Parcelas con más de un ID | Parcelas vinculadas del filtro | Historial observado | No prueba persistencia del problema |
| Contexto constructivo | Eventos/parcelas vinculados por periodo BU | Eventos/parcelas con periodo conocido, separado de desconocidos | Captura municipal sesión 7 | Antigüedad no es conservación |
| Contexto energético | CEEE observados por ámbito/letra en parcelas vinculadas | Registros CEEE con letra válida | Captura CEEE; parcela | Certificados de vivienda no califican edificio |
| Obligaciones pendientes | Filas/identidades ITE/IEE según consulta | Consulta aportada, cobertura desconocida | Obligación 2025/2026, consulta 24/10/2026 | Sin resultados ni infracción inferida |
| Ayudas | No calculable | Cobertura de concesiones desconocida | Solo convocatoria disponible | Presupuesto no es importe concedido |

Los perfiles conservan todas las dimensiones anteriores y añaden recuentos observados; no hay índice global ni recomendaciones comerciales. Las combinaciones descriptivas se consultan por parcela y fuente. Una licencia concedida no prueba inicio, finalización ni ausencia de otras obras. Una orden registrada no acredita daños actuales; una obligación pendiente no equivale a resultado desfavorable. No se infiere financiación privada ni voluntad de contratación.

Las fechas/licencias de reutilización desconocidas quedan nulas en los manifiestos. La interfaz es local; verificación de condiciones de reutilización pendiente antes de cualquier publicación. No se ha autorizado publicación ni commits.
