# Sesión 27 · español predeterminado e inglés opcional

La aplicación inicia en **español (ES)**. El selector **ES | EN**, situado al principio de la barra lateral, cambia el idioma durante la sesión. Este comportamiento aplica el cambio definitivo de requisitos del propietario: el inglés no es el idioma inicial.

## Arquitectura

`src/madrid_rehab/i18n.py` centraliza mensajes ES/EN, claves estables y `t(key, **kwargs)`. La alternativa ante una traducción inglesa ausente es el texto español; una clave desconocida no produce una excepción. Las plantillas admiten variables y especificadores numéricos de Python. No se consultan traductores externos ni se descargan recursos.

Las claves semánticas incluyen `nav.explore`, `nav.address`, `nav.about`, `explore.count` y `filters.*`. Los mensajes de compatibilidad tienen claves `message.*`, `additional.*`, `error.*`, `export.*` y `template.*`, asignadas una vez: no se deben renumerar al añadir traducciones. El diccionario conserva como origen los textos españoles de las sesiones anteriores.

Un adaptador Streamlit acotado (`ui`) traduce únicamente las llamadas de presentación de los componentes públicos. No modifica globalmente Streamlit. Los componentes mantienen los textos españoles actuales y no contienen condicionales de idioma repetidos. El adaptador resuelve mensajes y plantillas por el catálogo central, formatea etiquetas y copia tablas antes de traducir encabezados y campos de presentación conocidos. No aplica traducción general palabra por palabra a direcciones o textos de fuentes.

El modelo comercial, las reglas de evidencia, columnas canónicas, índices, lectores, argumentos de callbacks, cachés de datos y valores de selección permanecen independientes del idioma. Los valores originales de fuente, direcciones, nombres propios, fechas, cantidades y referencias se conservan. Los nombres de columnas internas se mantienen en las vistas de registros originales; los encabezados destinados al usuario se traducen en la copia de presentación. Los estados y advertencias redactados por la aplicación sí se traducen.

La exportación HTML de identificación existente traduce solo su presentación y el atributo `lang`. Conserva la misma lista permitida de datos: no añade CEEE, ayudas, inspecciones ni evidencias pendientes de redistribución.

## Estado y navegación

El idioma se guarda por sesión en `i18n_language`; el selector usa `language_selector`. No hay una preferencia global entre usuarios. Sin selección explícita se utiliza ES.

Las tres opciones de navegación conservan sus valores internos históricos; únicamente cambia su etiqueta visible. Por ejemplo, el mismo valor interno `Explorar inmuebles` se presenta como **Explore properties** en EN. No se migran ni reinterpretan identificadores de selección.

Los widgets conservan sus claves existentes. Los controles que no tenían una reciben una clave determinista independiente del idioma. Antes de cambiar idioma se conserva el estado de los widgets de valor registrados y se restaura antes de construirlos con su nueva etiqueta; no se restauran botones ni eventos de mapa. Los formateadores fijan las etiquetas de cada renderizado, para no depender del contexto de sesión cuando Streamlit los invoca después.

Se preservan municipio, distrito, casillas, OR/AND, parcela, páginas de mapa y lista, consulta postal, resultado elegido y navegación entre parcela y construcción. Cambiar de idioma no ejecuta callbacks de limpieza, no activa botones y no habilita consultas REC.

## Cobertura

- Tres entradas principales y contenido completo de Acerca del proyecto, con versión inglesa natural y explicación de Catastro, CEEE, ITE/IEE y PRTR.
- Mapa comercial: controles, filtros, OR/AND, contador, áreas avanzadas, paginación, lista, fuentes, avisos y estados vacíos.
- Fichas comerciales: estructura, calidad, recomendaciones, ámbitos, límites de interpretación y tablas de evidencia.
- Detalles técnicos accesibles desde la ficha: pestañas y controles constructivos, energía, conservación, REC y procedencia.
- Buscador postal: campos, resultados, paginación, errores, apertura y retorno. Las direcciones oficiales permanecen en español.
- Consulta secundaria de expedientes Plan Rehabilita cuando ya está autorizada en modo local, incluidos convocatoria y tipo de actuación. Los valores internos de esos filtros no cambian.
- Exportación HTML de identificación ya existente.

Se conservan los nombres oficiales Plan Rehabilita, Catastro, Comunidad de Madrid, Ayuntamiento de Madrid, PRTR y los municipios/distritos. Los registros originales y sus descripciones documentales no se reescriben para simular una fuente inglesa.

## Permisos y límites

No se cambian controles de publicación ni licencias. PRTR y Plan Rehabilita siguen bloqueados en modo público; se traducen también las explicaciones del bloqueo. El acceso técnico local sigue requiriendo el indicador de desarrollo y no se habilita en público. REC conserva sus permisos y clic explícito; no hay consultas nuevas.

Las pantallas históricas de Analista y del piloto, activadas expresamente mediante indicadores de desarrollo, no forman parte de la navegación pública y mantienen su interfaz histórica española. Las denominaciones internas y los valores originales de documentos se conservan incluso dentro de una interfaz inglesa. Esto se distingue de los mensajes y controles redactados por la aplicación.

La validación visual requiere un navegador disponible: AppTest, análisis de textos y eventos serializados no acreditan WebGL, diseño móvil ni interacción física.

## Reproducción y validación

Instalación, servidor y suite mantienen los comandos de README/AGENTS; no se añaden dependencias.

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_i18n.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session26_navigation.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_rec_client.py -v
PYTHONPATH=src .venv/bin/python tests/audit_i18n.py --output-dir reports/session_27_i18n/replay_nuevo
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

El auditor exige un directorio nuevo, recorre las rutas principales en EN en modo local y público y conserva los textos emitidos para revisión. Comprueba frases españolas redactadas por la aplicación, permitiendo nombres y direcciones oficiales. Es una comprobación de textos, no una prueba visual ni una traducción de documentos fuente. Las pruebas históricas siguen usando ES por defecto; la prueba que seleccionaba el modo demo por posición pasa a usar la clave estable `demo_mode`, porque el selector de idioma ocupa ahora el primer lugar.

Informes: `reports/session_27_i18n/`. El resumen de cierre distinguirá la ejecución única de suite general de cualquier corrección y comprobación focalizada posterior. Se preservan originales, snapshots y cambios pendientes de S25/S26. Sin commit, push ni publicación.

## Resultado de cierre

- Suite general, una única ejecución: **566 pruebas, OK, 1.223,456 segundos**. Se conserva la salida completa y el hash del código de esa fase.
- Pruebas focalizadas previas: 10 de i18n, 6 de navegación S26 y 21 de REC, todas correctas.
- Revisión posterior: se corrigió la etiqueta breve de área avanzada con una clave explícita, se tradujo el tipo de acceso en las etiquetas postales conservando su valor original y se evitó buscar traducciones para páginas numéricas. Las **10 pruebas posteriores pasan**, con comprobaciones reforzadas de áreas y resultados postales. No se repitió la suite general.
- Auditoría final reforzada: **12 recorridos locales/públicos, sin frases de interfaz pendientes detectadas**, incluidos rótulos cortos. El informe conserva los textos emitidos y distingue los valores originales de las fuentes.
- Ruff global y formato de 16 archivos Python: correctos. `git diff --check`: correcto.
- Verificación posterior a la suite: **87 archivos canónicos coinciden con sus hashes**. Sin nuevos datos, fuentes, índices ni permisos.
- Chromium ausente: validación visual bloqueada; falta revisión real de ordenador/móvil y WebGL. No se afirma validación visual a partir de AppTest.

El primer informe focalizado registra un problema de formateadores que consultaban el idioma fuera del contexto de la sesión; se corrigió fijando sus etiquetas durante cada renderizado. Se conservan esos informes iniciales como trazabilidad. `validation_summary.json` recoge el resultado definitivo, las fases de comprobación y los hashes del código final. HEAD continúa en `d1aa6d8`; sin commit, push ni publicación.
