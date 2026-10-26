# Demostración local: Madrid Rehab Intelligence

Proyecto personal independiente, sin datos internos, conexiones corporativas, logos ni atribución de titularidad a UCI. Esta guía prepara una conversación sobre utilidad y límites de la información; no presupone permiso para redistribuir PRTR o REC.

## Ejecución

Desde `/home/apalo/madrid-rehab-intelligence`, con snapshots locales existentes:

```bash
.venv/bin/python -m pip install -r requirements.lock
MADRID_REHAB_DEMO=1 MADRID_REHAB_OFFLINE=1 PYTHONPATH=src \
  .venv/bin/python -m streamlit run src/madrid_rehab/app.py \
  --server.address 127.0.0.1 --server.port 8512 --server.headless true \
  --browser.gatherUsageStats false
```

Abrir `http://127.0.0.1:8512`. Sin compilación ni dependencias nuevas. El arranque no necesita REC ni otros servicios web. El mapa muestra geometría sin teselas externas. Mantener escucha local. El selector lateral permite volver al modo Analista existente; sin variable DEMO la entrada histórica no cambia.

Para probar la versión pública: añadir `MADRID_REHAB_PUBLIC=1`. Protege energía regional, PRTR y conservación; solo queda identificación catastral. No significa que se haya aprobado publicar el sitio.

## Guion de cinco minutos

1. Mostrar portada, unidades y denominadores: parcelas, contenidos CEEE y expedientes son entidades distintas.
2. Seleccionar un caso real o municipio y RC14. No hay autocompletado ficticio ni selección implícita de candidato ambiguo.
3. Abrir Identificación: geometría CP y, para Madrid, acceso documental. El año constructivo no está acreditado en esta ficha.
4. Energía: contrastar letras, fecha y ámbito. Conservación: separar órdenes históricas, obligación de presentar e inspección real no disponible.
5. Ayudas e Investigación: coexistencia de fuentes sin atribuir causalidad, pagos ni obras. Abrir fuente oficial; exportar HTML limitado y explicar sus exclusiones.

El buscador operativo prioriza municipio y referencia exacta; no implementa dirección regional ni clic de selección sobre el mapa en modo demo. El visor Analista conserva sus mapas interactivos distritales. Los filtros de candidatos permiten CEEE, coexistencia con PRTR, letras E/F/G y órdenes históricas de Madrid, sin score ni ordenación comercial. Requieren seleccionar expresamente la referencia; se vuelve a comprobar CP antes de abrir la ficha.

## Tres casos comprobados contra snapshots

Los detalles locales completos y hashes están en `reports/session_15/audit_02/`. No distribuir ese directorio como si toda su información tuviera licencia revisada.

| Caso | Referencia / municipio | Evidencia real | Límite principal |
|---|---|---|---|
| Madrid | `0010510VK4701A`, `28079` | 4 contenidos CEEE individuales D/E y 2 órdenes históricas; acceso NDP 11084612, Marcelo Usera 90 | Sin dictamen REC ni confirmación de edificio; sin PRTR vinculada en esta captura |
| Alcalá de Henares | `0015301VK7801N`, `28005` | 1 contenido CEEE declarado edificio completo, G consumo/F emisiones, 04/12/2024; 1 expediente PRTR vinculado; CP aceptada | Ámbito declarado no confirma BU; dirección no verificada en esta ficha; sin conservación integrada |
| Getafe | `0036104VK4603N`, `28065` | 2 contenidos CEEE declarados edificio completo A/A, 28/01 y 23/02/2026; CP aceptada | Cobertura municipal parcial; no se acredita que sean renovaciones de un mismo edificio; sin PRTR vinculada ni conservación integrada |

Madrid se seleccionó para ilustrar antecedentes sin diagnóstico actual. Alcalá muestra coexistencia documental de energía y ayuda. Getafe muestra que cobertura catastral y observaciones energéticas también incluyen letras A: la herramienta no presupone necesidad de rehabilitación.

Para cada uno: «Caso real de demostración» → nombre del caso → ficha autocompletada → seis pestañas → «Fuentes y exportación». Alternativa: «Búsqueda libre» → municipio → referencia de la tabla. En público los accesos rápidos con señales PRTR se ocultan; introducir municipio/RC manualmente.

Las relaciones energéticas son nivel A y CP única aceptada; se conservan relaciones dudosas en sus productos históricos. No hay vínculos físicos BU nuevos. Madrid conserva acceso–parcela documental; fuera de Madrid no se traslada NDP.

## Ausencias y cobertura

- Elegir La Acebeda (`28001`) prueba municipio con límite territorial y sin CP integrada: no se fabrican parcelas.
- Una referencia inexistente devuelve ausencia/ambigüedad/cuarentena y no abre ficha.
- Sin certificados o antecedentes, se informa ausencia en fuentes, nunca estado favorable.
- La nueva ficha usa Madrid y los cinco pilotos parciales de sesión 12.2; el visor regional Analista histórico exige particiones de su contrato original. No confundir ambos contratos ni activar el snapshot parcial como cobertura completa. No cambiar variables para hacer pasar una partición parcial por validada completa.

## Exportación

HTML autónomo con identificación, municipio, RC, fuente, fecha de generación, advertencias e información no disponible. **Es una ficha reducida**: no exporta energía, conservación ni ayudas, ni siquiera en modo privado, mientras no se revise la redistribución específica. Sin PDF nuevo. La vista local puede explorar más información que el documento descargable; el contexto privado no autoriza compartirla.

## Qué falta antes de enseñarlo

Ejecutar en Ubuntu, revisar las capturas y completar `auditoria_visual_pendiente.md`. Para presentación a terceros, revisar `licencias_demo.md`; la convivencia PRTR se usa en la validación local, pero no se considera autorizada su redistribución comercial. Puede mostrarse el modo público reducido mientras se resuelven esos permisos. No se requiere acceso corporativo. No hay commits, push ni despliegue.
