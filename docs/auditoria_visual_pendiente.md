# Auditoría funcional y revisión visual pendiente — sesión 15

**Estado: revisión real de navegador bloqueada por permisos del entorno; aceptación visual humana pendiente.** No hay capturas satisfactorias de sesión 15. AppTest verifica estado/elementos Python, no WebGL, contraste, disposición ni clic real.

Se intentó el servidor Streamlit en `127.0.0.1:8512`: fallo al crear socket, `PermissionError: [Errno 1] Operation not permitted`. Se intentó Chromium instalado: termina con `sandbox_host_linux.cc`, operación no permitida. No se alteraron permisos ni se intentó superar el bloqueo. Registro Chromium: `reports/session_15/browser_01/browser.json`, estado `blocked_or_failed`, cero casos ejecutados. Ambos fallos son locales y no diagnostican el portal REC.

## Inventario funcional revisado

| Flujo existente | Comprobación de esta sesión | Revisión de navegador |
|---|---|---|
| Entrada app.py → city_app | Código y AppTest; demo opcional y vuelta a Analista | Pendiente |
| Madrid → distrito → zona → parcela | Arquitectura conservada; regresión suite histórica | Pendiente clic/mapa/WebGL |
| Regional → municipio | Selector de límites y cobertura; sin CP no inventa fichas | Pendiente |
| Cinco pilotos parciales | Consulta real selectiva en nueva demo y pruebas de las cinco particiones | Pendiente |
| Energía, administración, PRTR | Ficha nueva conjunta; vistas analíticas previas conservadas | Pendiente lectura/jerarquía visual |
| Filtros | CEEE, PRTR, E/F/G, órdenes; selección expresa | Pendiente interacción y tiempos reales |
| Público | Sin lecturas de evidencia nueva; sin casos que revelen PRTR | Pendiente inspección visual y descargas históricas |
| Exportación nueva | HTML reducido; escape y exclusión de evidencia probados | Pendiente abrir/imprimir en navegador |

Se detectó dispersión de fichas y terminología técnica en vistas previas. La demo ofrece seis apartados en español y evita consumo/emisiones sin unidades, duplicación de cartas técnicas y términos de riesgo. El modo Analista mantiene tablas de auditoría y etiquetas originales. Se corrigió «No constan inspecciones» por la ausencia explícita de resultado integrado; no se confunde con un dictamen favorable.

La vista regional Analista histórica usa el contrato de particiones completas; el producto parcial no debe pasarse a ese lector mediante override. La nueva demo lee explícitamente la captura parcial aceptada y sus cuarentenas permanecen intactas. No se ha hecho un rediseño de navegación histórica.

## Procedimiento Ubuntu

Iniciar el comando de `demo_uci.md`; en otra terminal:

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src \
  .venv/bin/python tests/browser_session15.py \
  --output-dir reports/session_15/browser_ubuntu_01
```

Si faltan dependencias de navegador, instalación opcional ya declarada:

```bash
.venv/bin/python -m pip install -r requirements-browser.lock
PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser .venv/bin/python -m playwright install chromium
```

El script comprueba navegación de tres casos y descarga HTML; guarda capturas solo tras aserciones. Un fallo devuelve 2 y conserva diagnóstico. Aun si pasa, la revisión humana sigue pendiente.

## Lista humana de aceptación

- Portada legible a 100% y proyector; unidades/denominadores comprensibles.
- Casos Madrid, Alcalá y Getafe: seis pestañas, geometría visible, textos sin recortes y fechas correctas.
- Madrid Analista: 21 distritos, vuelta a municipio, zona/celda y selección sobre mapa; celdas no se presentan como barrios.
- Cinco pilotos: selección explícita y cobertura parcial; no atribuir BU a CP sin relación.
- La Acebeda sin CP; parcela sin CEEE y parcela sin conservación muestran desconocido/ausencia de fuente.
- Búsqueda libre cambia municipio sin arrastrar RC anterior; candidatos no se autoseleccionan.
- Modo público: ningún detalle PRTR/REC/energía protegida, incluidos exportadores históricos.
- HTML descargado: abrir sin conexión, comprobar escape, fuentes y advertencias; sin IDs/importes PRTR ni datos personales.
- Medir arranque, portada, municipio, ficha y descarga; comprobar memoria del servidor y consola, además del benchmark Python.

No declarar MVP visualmente aceptado hasta completar y fechar esta lista. El bloqueo no se reporta como validación exitosa.
