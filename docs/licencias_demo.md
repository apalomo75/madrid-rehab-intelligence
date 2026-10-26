# Licencias, privacidad y exportación de demostración

Revisión técnica 26/10/2026, sin autorización de publicación. No constituye un dictamen jurídico. Los archivos reales siguen en `data/` y `reports/`, excluidos de Git.

| Fuente | Evidencia disponible | Pantalla local demo | Público y exportación nueva |
|---|---|---|---|
| Catastro INSPIRE | Metadatos y procedencia conservados; revisar condiciones de atribución antes de difusión externa | RC y geometría de CP aceptada | HTML reducido de identificación con atribución; no geometría redistribuida |
| Límites municipales | Licencia/fecha específica aún no verificadas en captura histórica | Selector municipal y cobertura | No se exporta geometría |
| CEEE regional | Catálogo local documenta CC BY 4.0; hay anomalías y límites de ámbito | Letras/fecha/ámbito, sin datos personales ni valores con unidades desconocidas | Se conserva cierre histórico de modo público; exportación nueva excluida por prudencia de revisión conjunta |
| PRTR | Reutilización no verificada | Coexistencia y número de expedientes, solo análisis local | Oculto; sin importes, IDs ni relaciones en HTML |
| Conservación administrativa | Órdenes con CC BY; puente/mezcla de fuentes no completamente revalidado para redistribución | Evidencia histórica selectiva | Oculto y excluido de HTML |
| REC | Consulta pública no equivale a permiso de extracción/redistribución | Enlace y ausencia de resultados integrados | Sin registros; sin resultados exportados |
| RIEECM | Aviso legal con restricciones comerciales | Ningún informe integrado | Ninguna reproducción |

El [aviso RIEECM](https://www.rieecm.es/portal/home/aviso_legal) exige autorización para reproducción/distribución comercial y describe uso personal privado; no se traslada una licencia del catálogo de datos abiertos a sus notas individuales. La [Sede municipal](https://sede.madrid.es/portal/site/tramites/menuitem.62876cb64654a55e2dbd7003a8a409a0/?vgnextoid=8fe1b4173fd61110VgnVCM2000000c205a0aRCRD) distingue resultados públicos y acceso sujeto a interés legítimo.

El exportador utiliza una lista positiva de campos: no serializa DataFrames completos. Escapa texto HTML y rechaza CP ausente/no única/no utilizable. Sus argumentos de evidencia no se incorporan al documento. Las pruebas introducen secretos sintéticos y comprueban su ausencia en ambos modos. La presentación pública también oculta los nombres de casos que revelaban coexistencia de PRTR.

No se han consultado propietarios, contactos ni expedientes internos. No hay funciones de prospección comercial ni scoring financiero. Las fichas locales de auditoría contienen direcciones públicas e identificadores técnicos necesarios; no se añadirán al repositorio. Una eventual autorización futura debe definir campos y usos, no limitarse a declarar que la web es pública.

Antes de una demo externa completa: acreditar redistribución PRTR, condiciones del puente de callejero y uso de límites; validar privacidad y atribución por campo; revisar HTML real descargado y las pantallas del modo elegido. Antes de publicación: auditar además los exportadores históricos del modo Analista. El cierre de la nueva ficha no sustituye esa auditoría completa.
