# Sesión 38 · Pantalla de bienvenida

La URL principal abre una portada bilingüe con la presentación del proyecto, el crédito «Desarrollado por Alejandro Palomo», el trabajo de integración de datos y una invitación a colaborar. La portada oculta la barra lateral y muestra su propio selector ES/EN. Las tres tarjetas abren las vistas existentes. «Inicio» vuelve a la portada desde la navegación lateral. Los bloques de datos y colaboración comparten una fila en escritorio y se apilan en pantallas estrechas.

La portada se renderiza antes de verificar o preparar el paquete de datos. Las vistas existentes siguen aplicando sus comprobaciones de acceso y usan el mismo paquete v1.04. El regreso a la exploración recupera filtros, parcela seleccionada y paginación. La búsqueda recupera los campos y la coincidencia seleccionada en la sesión.

La portada hereda el fondo del tema activo de Streamlit. Entre el hero oscuro y las tarjetas se muestra un SVG original e independiente del catálogo. La trama urbana se inspira en Madrid y las conexiones ilustran el concepto de capas de información pública. El pie identifica el dibujo como conceptual y el texto alternativo se muestra en español o inglés según el idioma activo.

## Revisión local

```bash
MADRID_REHAB_BUNDLE_DIR=data/deployment/madrid_rehab_v1_04_candidate_01 \
MADRID_REHAB_PUBLIC=1 MADRID_REHAB_OFFLINE=1 MADRID_REHAB_DEV=0 \
MADRID_REHAB_DEMO=0 MADRID_REHAB_PILOT=0 PYTHONPATH=src \
.venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512
```

```bash
.venv/bin/ruff check src tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_welcome.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_session26_navigation.py -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_i18n.py -v
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src \
.venv/bin/python tests/browser_session38.py --output-dir reports/session_38_welcome/browser_nuevo
```

La prueba de navegador requiere Chromium y el servidor local. Con el paquete v1.04 comprueba los destinos, la vuelta a Inicio y la persistencia del filtro P5. Genera capturas de la portada y comprueba que las tarjetas se apilan sin desbordamiento a 320 y 390 píxeles. También comprueba el fondo común con las tres vistas interiores, la altura de la ilustración en escritorio y sus etiquetas y descripción accesible en ambos idiomas.
