# Sesión 26 · navegación comercial del MVP

La entrada normal tiene tres opciones: **Explorar inmuebles**, **Buscar por dirección** y **Acerca del proyecto**. El texto de presentación procede del propietario, con aclaraciones de cobertura, atribución y restricciones. Es una primera versión experimental e independiente, sin diagnóstico técnico.

## Funciones reubicadas

| Función anterior | Acceso actual |
| --- | --- |
| Mapa comercial | Explorar inmuebles |
| Buscador comercial | Buscar por dirección |
| Exploración municipal | Mapa comercial compartido; exploración técnica íntegra en desarrollo |
| Consulta técnica de direcciones | Desplegable de desarrollo |
| Madrid capital histórico | Desplegable de desarrollo |
| Cobertura regional histórica | Desplegable de desarrollo; explicación de cobertura en Acerca |
| Plan Rehabilita | Casilla del mapa y desplegable «Ver expedientes de Plan Rehabilita» |

Para habilitar herramientas secundarias locales: `MADRID_REHAB_DEV=1`. Aparecen en un desplegable separado de las tres entradas. Se ignora ese indicador en modo público. No es autenticación ni autorización de publicación. El modo demo histórico continúa disponible mediante su indicador explícito.

Los expedientes reutilizan el lector y la vista existentes, con distrito, convocatoria y tipo de actuación. La consulta secundaria no genera otro mapa ni ETL. Sus filtros se aplican al conjunto de expedientes de esa vista, independientemente del filtro de parcelas del mapa principal. No suma importes y conserva los vínculos A/B/C. Plan Rehabilita y PRTR permanecen deshabilitados en público; el desplegable explica la restricción sin recuperar expedientes.

## Geografía y coherencia

Madrid muestra los 21 nombres distritales y «Todos los distritos». Se usan los códigos ya documentados de `parcels_audited.parquet`, autenticados por el lector existente, y los nombres del producto municipal S7. `parcel_territories` exige concordancia de todas las filas de una referencia. No hay nuevas asignaciones por distancia ni reprocesado geométrico. Las referencias no asignadas permanecen en el conjunto general y no se incorporan arbitrariamente a un distrito. Se conserva la semántica histórica de asignación; una parcela que cruza un límite no equivale a una construcción contenida íntegramente en él.

Los otros cinco municipios utilizan su ámbito municipal y cobertura parcial aceptada, sin inventar barrios. Municipio → distrito → cuatro casillas → OR/AND → contador → mapa → lista → ficha. El contador mide parcelas distintas, con aclaración visible sobre edificios físicos. Se mantiene la lógica y las restricciones de la sesión 25.

El mismo índice filtrado alimenta contador, páginas de mapa y lista. Cada página cartográfica carga hasta 500 geometrías originales, proyectadas para visualización sin simplificación; la lista permite recorrer todo el conjunto en páginas de diez. Las páginas cartográficas y de lista son independientes y sus alcances se explican. No se promete dibujar todas las parcelas simultáneamente. Las áreas codificadas siguen disponibles exclusivamente en el desplegable avanzado «Explorar una zona del mapa»; no son barrios. Los identificadores y claves internas se conservan.

Cambiar distrito o combinación restablece selección y páginas del contexto activo; conserva las casillas. Abrir ficha y volver conserva distrito, municipio, filtros y páginas. Cambiar de apartado y regresar también conserva el contexto comercial mediante una copia selectiva de estado, excluyendo botones y eventos cartográficos. La ficha mantiene su navegación documental y detalles técnicos sin propagar datos de parcela a construcciones.

La asignación por referencia se cachea por firma de fuentes verificadas. No se recalcula Catastro ni se carga una ficha para contar resultados.

## Validación

Instalación, servidor y suite mantienen los comandos de README y AGENTS. Pruebas focalizadas:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session26_navigation.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_filter_navigation.py -v
PYTHONPATH=src .venv/bin/python tests/benchmark_session26_navigation.py --output reports/session_26_navigation/replay_nuevo.json
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Informes en `reports/session_26_navigation/`. El benchmark exige salida nueva, reconcilia distritos y filtros en seis municipios y ambos modos, y verifica hashes canónicos. Las pruebas AppTest cubren los tres apartados, búsqueda Madrid, persistencia, cambio de distrito, seis municipios, accesos secundarios y bloqueo público. Comprueban el JSON cartográfico y un evento serializado contra las identidades de la lista; no acreditan clic físico ni WebGL. Se adaptan las regresiones históricas para usar el acceso técnico explícito, conservando sus comprobaciones de datos.

Ejemplo real comprobado: Madrid → Carabanchel → Solo Plan Rehabilita: **153 parcelas**. El mapa de esa selección contiene exactamente esas 153 identidades; la primera página de lista contiene diez del mismo conjunto.

## Incidencias para el 20/11/2026

- Chromium ausente en la ruta configurada: validación visual bloqueada, registrada en `browser_status.json`. Falta revisión real en ordenador y móvil, incluyendo WebGL, legibilidad, retorno y selección.
- Licencia/procedencia PRTR y Plan Rehabilita pendientes; su exposición pública sigue bloqueada. No hay autorización de despliegue ni redistribución.
- Cobertura postal solo Madrid; cobertura catastral parcial en los otros cinco municipios. Las fuentes no integradas no permiten inferir tasas cero.
- No se incorporan fuentes, pipelines, dependencias ni municipios. Se preservan originales, snapshots y trabajo pendiente de S25. No se realiza commit, push ni publicación.

Los resultados definitivos de Ruff, formato y la única ejecución de suite general se recogen en `validation_summary.json` al cierre.

## Resultado de cierre

Ruff global, formato de los 18 archivos Python de esta intervención y `git diff --check`: correctos. Reconciliación: 84 combinaciones reales; 87 archivos canónicos verificados por hash tras las pruebas. Comprobación adicional: pasar de una ficha Getafe a ITE/IEE sin cobertura integrada deja contador cero, sin mapa, lista ni identidad de ficha obsoleta; no se interpreta como tasa cero.

La única suite general ejecutó **556 pruebas en 731,158 segundos y detectó dos regresiones**: pérdida del argumento de apertura directa `initial_ref` y atribución esperada fuera del nuevo flujo. Se conservó ese resultado original en `full_suite.log`. Después se restauró el argumento (incluida navegación CP/BU), se añadió «Fuentes y alcance» al pie del mapa y se limpió la identidad de ficha también ante conjuntos vacíos.

Validación posterior sobre el código final: **23 pruebas satisfactorias** (15 catálogo, 6 navegación S26, 2 navegación de filtros S25), con registros finales independientes. Las otras pruebas focalizadas históricas sumaron 17 de Madrid y 5 regionales satisfactorias. La suite general no se repitió, siguiendo la instrucción de una sola ejecución; por tanto, no se presenta como una suite general final íntegramente satisfactoria. `validation_summary.json` distingue ambas fases y registra hashes del código final.

La revisión visual permanece bloqueada por Chromium ausente. Los permisos pendientes siguen impidiendo la publicación. HEAD permanece en `d1aa6d8`, sin commit ni push.
