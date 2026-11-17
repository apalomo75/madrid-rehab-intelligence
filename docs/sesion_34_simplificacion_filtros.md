# Simplificación final de filtros y fichas · revisión local v1_03

Cambio de interfaz sobre `data/deployment/madrid_rehab_v1_03/` existente. No se reconstruye ni modifica el paquete, PRTR, snapshots ni sus recuentos.

- Cuatro filtros de evidencias en una fila de escritorio. «Solo CEEE» incorpora un botón de ajustes compacto con nombre accesible «Filtrar por tipo de certificado» y selector dentro de un popover cerrado inicialmente. Los contenedores de Streamlit conservan su adaptación móvil.
- Cualquier certificado, edificio completo, vivienda individual, local u otros ámbitos y ámbito no determinado. Elegir un ámbito concreto activa CEEE; desmarcarlo o limpiar filtros vuelve a «Cualquier certificado». Desconocido se consulta por separado de local; no se infiere ámbito desde CP/BU.
- NextGenerationEU público consulta todos los programas confirmados y no presenta selector de programa. La API y la consulta privada por programa permanecen disponibles; las fichas conservan códigos y programas originales por expediente.
- Tabla CEEE por ámbito con certificados documentales únicos utilizables y distribuciones independientes de letras de consumo/emisiones. Sin filas vacías ni letra única agregada. Una aclaración contextual para los certificados individuales distingue certificado de vivienda y de calificación del edificio. Identificadores, fechas, magnitudes y fuentes permanecen en los detalles.
- Municipio/distrito en dos columnas, mapa/ficha 65/35; mismas identidades y conjunto filtrado para contador, mapa y lista. Se conservan OR/AND, páginas, navegación y traducciones ES/EN.

## Validación

Informes nuevos: `reports/session_34_filter_simplification/review_01/`. Ruff correcto; 41 pruebas focalizadas correctas (38 regresiones y 3 pruebas nuevas), más smoke público de 180 combinaciones.

```bash
.venv/bin/ruff check src tests
PYTHONPATH=src:tests .venv/bin/python -m unittest test_filter_simplification test_commercial_filters test_filter_navigation test_session30_ux test_i18n test_public_prtr test_session31 -v
```

Las pruebas incluyen activación/desactivación, todos los ámbitos y reinicio, CEEE+PRTR con OR/AND y ámbito concreto, traducción, regreso a la lista, conservación de páginas y contadores. Madrid con solo NextGenerationEU: **3.300 parcelas**. Ribadavia 12 (`0006712VK4800E`, ejemplo de Ribadavia 12 / Sinesio Delgado 42): **5 certificados de vivienda individual, consumo E (5), emisiones E (5)**. También se valida una parcela real con varios ámbitos y una regresión de distribuciones de letras múltiples, duplicados y relaciones no utilizables.

El smoke público comprueba 180 combinaciones de API y el recorrido público sin selector de programa, expedientes, ES/EN y retorno. Resultado en `smoke.json`: 5.046 expedientes, 4.378 parcelas PRTR, sin errores de ficha ni lecturas fuera del paquete. La capacidad de consultar programas por API no añade controles públicos.

## Revisión visual local

```bash
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_03 MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512 --server.headless true
```

URL: http://127.0.0.1:8512. Revisar alineación de filtros e icono, apertura/cierre de ajustes, tabla en panel de ficha, tamaños de escritorio/móvil y ES/EN. Chromium no está instalado: revisión visual/WebGL pendiente; AppTest y salud HTTP no la acreditan. Sin commit, push, despliegue ni publicación.
