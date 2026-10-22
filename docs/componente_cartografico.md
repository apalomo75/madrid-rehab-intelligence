# Decisión del componente cartográfico · sesión 3

## Evidencia y alternativa elegida

El visor anterior usaba GeoJsonLayer, `on_select="ignore"` y claves distintas por filtro. La prueba de navegador anterior seleccionaba un identificador en un desplegable; no acreditaba clic sobre geometría. La documentación de [Streamlit 1.50](https://docs.streamlit.io/1.50.0/develop/api-reference/charts/st.pydeck_chart) ofrece eventos `on_select` y objetos seleccionados, y requiere identificadores de capa estables.

Se mantiene **Streamlit 1.50.0 / PyDeck 0.9.1**, sustituyendo la capa interactiva por PolygonLayer con datos planos. Cada miembro de un multipolígono conserva `building_id`; mantiene sus anillos interiores y no se convierte en edificio independiente. El límite distrital continúa en GeoJsonLayer sin selección. No se ha demostrado que GeoJsonLayer tenga un fallo intrínseco: la selección anterior estaba desactivada y la validación actual está bloqueada.

El evento se procesa en un callback **antes** de dibujar la ficha. Se extrae el ID del objeto, nunca un índice de la tabla, y se valida contra los IDs visibles. La selección propia en Session State persiste tras navegación; los contornos destacan todos los miembros del BU. Streamlit puede atenuar la opacidad de objetos no seleccionados; las categorías conservan sus colores.

Cada combinación de filtros y fondo tiene una clave derivada estable; cambiarla invalida los eventos del conjunto anterior. Los cambios de filtros pueden restablecer la vista, pero conservan la identidad seleccionada cuando sigue visible. El botón explícito incrementa una generación de mapa y borra la selección. No se modifica el estado de selección de PyDeck, que es de solo lectura.

Se evaluó Folium/Leaflet mediante [streamlit-folium](https://github.com/randyzwitch/streamlit-folium), que ofrece comunicación bidireccional. La instalación de `streamlit-folium==0.25.3` fue bloqueada por resolución DNS al índice; no se añadió una dependencia no instalada ni se sustituyó por recursos JS remotos que romperían el modo sin conexión. Una migración solo estaría justificada si las pruebas reales del componente nativo no fueran satisfactorias.

**Estado: implementación pendiente de aceptación real en navegador.** El sistema impide abrir sockets y lanzar Chromium. Las pruebas Python/AppTest no garantizan picking WebGL, alineación visual, persistencia visual o rendimiento del navegador. La decisión debe revisarse si `browser_session3.py` falla en un entorno con permisos.

## Fondo urbano y funcionamiento sin conexión

Un estilo MapLibre raster incrustado como URI `data:` solicita teselas estándar OSM en `https://tile.openstreetmap.org/{z}/{x}/{y}.png`. Mantiene el CRS de visualización EPSG:4326 de las geometrías; el motor proyecta ambas capas a Web Mercator. La alineación está implementada pero pendiente de inspección visual.

El modo sin conexión usa un estilo incrustado sin fuentes, teselas ni tipografías externas. Los recursos de PyDeck/Streamlit ya se sirven localmente. No hay petición al servicio cartográfico de Catastro, geocodificación ni cartografía regional masiva. `MADRID_REHAB_OFFLINE=1` desactiva el fondo externo desde el arranque.

La [política de teselas OSM](https://operations.osmfoundation.org/policies/tiles/) exige atribución, Referer del navegador, caché ordinaria y prohíbe descargas masivas/prefetch. La aplicación muestra atribución y enlace a [copyright OSM](https://www.openstreetmap.org/copyright); utiliza HTTPS, límite de fuente zoom 19, caché HTTP del navegador y ninguna función de precarga. El servicio externo es de disponibilidad no garantizada y recibe las solicitudes de la vista del navegador. El modo local sigue disponible cuando no hay red.

## Dependencias, licencias y rendimiento

No hay nuevas dependencias. Se conservan manifiesto y locks existentes: Streamlit y PyDeck (Apache-2.0), Playwright opcional (Apache-2.0). OSM incorpora datos sujetos a ODbL y su servicio tiene una política de uso adicional. Distritos: Ayuntamiento de Madrid, CC BY 4.0; CEEE/Catastro mantienen su procedencia y condiciones documentadas en `fuentes_datos.md`.

`benchmark_session3.py` mide carga, filtros, número de miembros y serialización sobre Chamberí real, sin escribir Parquet. El JSON de mapa mide aproximadamente 8–10 MB con el serializador actual; no se infiere fluidez del navegador de los tiempos Python. Se mantiene la simplificación de sesión 2 sin modificar geometrías originales. Las pruebas de navegador registrarán latencia real cuando puedan ejecutarse.
