# Sesión 31 · Ámbito CEEE y exploración geográfica

## Evidencia disponible

Auditoría offline de `energy_certificates.parquet` regional y de los seis productos municipales del paquete `data/deployment/madrid_rehab_v1_02/`. No se modificaron fuentes, snapshots ni paquete. Resultados completos y ejemplos reales con identificador de contenido, registro y dirección original en `reports/session_31_improvements/scope_audit.json`.

| Ámbito documental | Regional | Paquete v1_02 |
| --- | ---: | ---: |
| Vivienda individual | 192.202 | 105.236 |
| Edificio completo | 30.929 | 25.488 |
| Local | 12.659 | 8.859 |
| No determinado | 344 | 188 |
| Total de contenidos canónicos | 236.134 | 139.771 |
| Porcentaje determinable | 99,8543 % | 99,8655 % |

Son contenidos canónicos distintos por `certificate_id`, no inmuebles únicos. El universo del paquete es de seis municipios, no toda la región. El porcentaje de ámbito reconocible incluye contenidos que pueden tener otras incidencias: no es porcentaje de certificados confirmados o vigentes.

`edif_tipo` es el campo original. El contrato existente `regional_energy.SCOPES` interpreta exactamente:

- `ViviendaIndividualEnBloque`: vivienda individual en bloque.
- `ViviendaUnifamiliar`: vivienda individual unifamiliar; no se reclasifica como bloque completo aunque físicamente pudiera ocupar un edificio.
- `BloqueDeViviendaCompleto`: edificio completo residencial declarado.
- `EdificioUsoTerciario`: edificio completo de uso terciario declarado; no implica uso residencial.
- `LocalUsoTerciario`: local.
- Cualquier otro literal: ámbito no determinado. Se conservan `Vivendas`, `Edificio terciario`, vacíos y valores anómalos sin interpretar por parecido.

El paquete ya conserva tanto `scope` como `edif_tipo`, fechas, calificaciones de consumo/emisiones y fuentes. La ficha conserva esos datos individuales y el resumen de letras por certificado; ningún promedio ni letra se atribuye a la parcela. El resumen de ámbitos cuenta una vez cada certificado utilizable. Los detalles conservan literalmente el tipo original.

## Cambios de interfaz y contrato

Un único selector «Certificación energética (CEEE)» sustituye al checkbox y al selector independiente: todos los inmuebles, cualquier certificado, edificio completo, vivienda individual y local u otro ámbito (incluye ámbito desconocido). «Todos los inmuebles» desactiva la evidencia CEEE como filtro. Los ámbitos específicos sustituyen la máscara CEEE antes de combinar OR/AND con las otras evidencias; no se aplican como intersección posterior. El control NextGenerationEU se oculta en público y los controles restantes se reparten sin huecos; las restricciones internas y Acerca del proyecto se conservan.

Se reutiliza la regla documental de la ficha: vínculo A, contenido de registro único y fecha no posterior a captura. Las membresías se deduplican por parcela/certificado. Una parcela puede aparecer en varias categorías, pero solo una vez en cada resultado. No se usa Catastro, número de viviendas ni multiplicidad para clasificar. Se leen únicamente cuatro columnas de certificados y tres de vínculos, con caché acotada a seis municipios e invalidación por producto/paquete. Sin dependencias adicionales ni nuevas descargas.

Municipio y distrito mantienen nombres oficiales. Se elimina el selector comercial de cuadrículas: ningún código «Zona 441:4469» aparece en él. Se conserva la paginación del mapa (500 geometrías máximo) y la lista sobre el conjunto filtrado. El mapa muestra su página, no todos los resultados simultáneamente. Las geometrías no cambian. Una selección que ya no cumple filtros se borra; la que sigue cumpliendo un cambio de distrito/ámbito se conserva.

Todos los textos nuevos usan claves estables en `i18n.py`; valores internos y claves de widgets no dependen del idioma. Español predeterminado, nombres oficiales sin traducir.

## Barrios: fuente identificada, integración pendiente

No se encontró un producto local validado de límites de barrios ni asignaciones de parcela a barrio; el paquete contiene distritos, no barrios. El GeoPackage regional municipal no sustituye esta capa. No se implementa un selector con nombres deducidos de cuadrículas.

La fuente oficial localizada es [Barrios municipales de Madrid, Geoportal municipal](https://servpub.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=422fa235-762b-11e9-861d-ecb1d753f6e8), cuyo catálogo describe 131 barrios, y [Límites administrativos actuales](https://datos.madrid.es/dataset/900012-0-limites-administrativos-mapas/information). Se consultaron metadatos, sin descargar geometrías. Cobertura local verificable de barrios en esta sesión: ninguna; no debe confundirse con inexistencia de fuente oficial.

Trabajo mínimo para un próximo producto separado:

1. Capturar la capa oficial de barrios con fecha, licencia, CRS, URL y SHA-256, sin sobrescribir originales.
2. Validar 131 identidades únicas, geometrías válidas, nombres y pertenencia oficial a los 21 distritos; comprobar solapes y huecos contra el municipio.
3. Cruzar geometrías CP completas en CRS métrico con polígonos oficiales, preservando áreas de intersección y todas las incidencias.
4. Propuesta de regla pendiente de validar: barrio de mayor área de intersección positiva; empate numérico o conflicto con distrito verificado queda sin asignar. Contactos de borde de área cero no asignan. Una sola fila por CP; conservar todos los cruces como auditoría y no resolver empates por nombre/código.
5. Probar parcelas interiores, cruces, contactos, empates, ausencia de duplicados y consistencia de filtros/mapa/lista; empaquetar catálogo barrio/distrito y asignación CP con hashes del CP activo.

No se afirma validación espacial ni pruebas de límites de barrios: falta la capa. El recorrido Chamberí → Gaztambide requiere ese futuro producto. Carabanchel → Plan Rehabilita y distrito → ámbito CEEE sí utilizan evidencia actual.

## Producción y revisión

CEEE y retirada del control de cuadrículas son compatibles con el paquete actual: solo requieren futura actualización del código tras revisión, sin reconstrucción automática del paquete. Para barrios hará falta un nuevo Release de datos con las dos tablas verificadas y manifiesto; `v1_02` debe seguir funcionando sin ellas. No se cambió el generador ni se activó un producto futuro. No se tocaron PRTR ni reglas/importes de Plan Rehabilita.

Prueba AppTest pública real sobre `v1_02`: base Madrid 113.543 parcelas autorizadas por ese paquete, filtro edificio completo 18.953, Chamberí 421; abrir ficha y volver a lista sin excepción. No confundir con la membresía histórica local de 153.929 CP. Evidencia en `apptest_public.txt`.

Ruff y pruebas focalizadas: registros en el directorio de informes. AppTest comprueba estado y eventos, no WebGL ni disposición visual. Chromium no está disponible en `/tmp/madrid-rehab-browser`; revisión visual del propietario pendiente. No se ha publicado, hecho commit/push ni reconstruido el paquete.

## Validación reproducible

Ejecutar con `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session31.py -v`. Incluye pruebas sintéticas de ámbitos y cuarentena y AppTest contra el paquete real (se omite explícitamente si el paquete no existe). La prueba cambia ES → EN conservando ámbito, distrito y ficha; cambia después a otro distrito y verifica que la selección incompatible desaparezca. Las seis columnas normalizadas `scope` del paquete se contrastaron con el mapa exacto de `edif_tipo`, sin discrepancias.

Comandos de regresión focalizada: sustituir el patrón anterior por `test_commercial_fiche.py`, `test_commercial_filters.py`, `test_i18n.py`, `test_session30_ux.py` y `test_production_bundle.py`. Lint: `.venv/bin/ruff check src tests`. No se ejecutó de nuevo la suite general.

Resultado final: 46 pruebas focalizadas superadas (3 nuevas de sesión 31, 14 ficha, 5 filtros, 10 i18n, 6 UX y 8 paquete). Ruff sin incidencias. `validation.json` resume las verificaciones y sus límites. La auditoría de ámbitos puede reproducirse desde la raíz con `PYTHONPATH=src .venv/bin/python reports/session_31_improvements/audit_scopes.py`; reproduce únicamente ese informe, sin escribir productos de datos.


## Ajustes finales de interfaz

Las listas usaban un texto genérico cuando faltaba etiqueta en el índice postal autorizado. Ahora muestran la dirección documentada cuando está disponible y, en otro caso, la referencia catastral completa junto al municipio. La referencia también acompaña las etiquetas con dirección para distinguir parcelas que comparten literal postal. No se buscan direcciones en fuentes de otro ámbito ni se deducen barrios.

El resumen CEEE distingue singular/plural y presenta fechas ISO como «3 de febrero de 2024» / «3 February 2024». Las tablas ampliadas mantienen fechas y valores originales. Las opciones CEEE tienen etiquetas de lenguaje común en ES/EN; el detalle original y la advertencia de ámbito se conservan.

Revisión local con el paquete existente, sin reconstrucción:

```bash
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_02 MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512
```

Abrir http://127.0.0.1:8512 y comprobar las cinco opciones CEEE con OR/AND y Plan Rehabilita/ITE, distrito, paginación, selección mapa/lista, retorno de ficha, búsqueda y cambio ES/EN. Confirmar que PRTR no aparece como control público y que certificados individuales conservan su ámbito. La estructura 65/35 se mantiene. Intento final de navegador: `reports/session_31_improvements/final_ui_browser_01/browser.json`, bloqueado por ausencia de Chromium. AppTest no acredita WebGL ni revisión visual.

Validación de ajustes finales: 66 pruebas distintas superadas (incluida la repetición de las seis UX tras actualizar una expectativa de etiqueta antigua), Ruff y diff check correctos. Registros en `reports/session_31_improvements/final_ui_validation_01/`. Los resultados de 46 pruebas descritos arriba corresponden a la revisión anterior.
