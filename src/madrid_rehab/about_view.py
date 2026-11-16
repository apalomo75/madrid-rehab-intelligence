"""Owner-provided presentation and progressive disclosure of methodology."""

from .i18n import ui as st


def render():
    st.title("Acerca de Madrid Rehab Intelligence")
    st.subheader("Conoce mejor los edificios de tu ciudad")
    st.info("Esta es una primera versión experimental: un primer prototipo o boceto funcional.")
    st.markdown("""
**Madrid Rehab Intelligence** es un proyecto personal que nace con una idea sencilla: reunir en un mismo lugar información pública sobre edificios para que sea más fácil conocer sus características y explorar posibles actuaciones de rehabilitación.

Actualmente, la herramienta permite consultar información sobre edificios y parcelas de Madrid y otros cinco municipios de la Comunidad de Madrid.

Puedes encontrar datos sobre su antigüedad, características constructivas, eficiencia energética, inspecciones y antecedentes administrativos, así como determinadas ayudas públicas relacionadas con la rehabilitación.
""")
    with st.expander("Un proyecto que acaba de empezar", expanded=True):
        st.markdown("""
Madrid Rehab Intelligence todavía está en una fase inicial de desarrollo. Lo que ves es un primer prototipo, pensado para demostrar lo que se puede conseguir combinando distintas fuentes de información.

La idea es seguir mejorándolo poco a poco: incorporar nuevos datos, ampliar la cobertura geográfica, facilitar las búsquedas y desarrollar herramientas que ayuden a comprender mejor la situación de los edificios.

Queremos que, con el tiempo, sea cada vez más fácil encontrar información útil sin tener que consultar numerosas páginas y registros por separado.
""")
    with st.expander("¿Qué puedes hacer actualmente?"):
        st.markdown("""
- **Explorar un mapa:** descubrir inmuebles sobre los que existe información disponible.
- **Consultar sus características:** conocer datos constructivos documentados.
- **Examinar su información energética:** consultar certificados energéticos vinculados.
- **Investigar antecedentes:** encontrar obligaciones de inspección y otros registros administrativos disponibles.
- **Consultar ayudas públicas:** identificar expedientes de rehabilitación relacionados con las parcelas.

La disponibilidad de estas funciones puede variar según el municipio y las fuentes autorizadas para su consulta.
""")
    with st.expander("¿De dónde procede la información? Fuentes y metodología"):
        st.markdown("""
Utilizamos información procedente de organismos públicos como la Dirección General del Catastro, la Comunidad de Madrid y el Ayuntamiento de Madrid.

Cada fuente tiene su propia cobertura, fecha de actualización y limitaciones. Puedes consultar su procedencia en las fichas.

- [Dirección General del Catastro](https://www.catastro.hacienda.gob.es/): productos INSPIRE; se deben aplicar las condiciones del producto de origen.
- CEEE · Comunidad de Madrid: CC BY 4.0 según el catálogo local. Los certificados conservan su ámbito documental.
- Conservación y callejero · Ayuntamiento de Madrid: obligaciones y antecedentes disponibles; no hay resultados reales de inspecciones integrados.
- PRTR · visor de rehabilitación de la Comunidad de Madrid alojado en COAM; Plan Rehabilita · Ayuntamiento de Madrid, captura local facilitada por el usuario. Licencia y procedencia de reutilización pendientes de verificar; consulta bloqueada en modo público.

Los vínculos ambiguos no se convierten en confirmaciones. Los importes pertenecen a expedientes únicos y no se suman por parcela.
""")
    with st.expander("Cobertura de Comunidad de Madrid"):
        st.markdown("""
El mapa comercial incluye Madrid, Getafe, Móstoles, Leganés, Alcorcón y Alcalá de Henares. La cobertura catastral de los cinco últimos es parcial.

La búsqueda por dirección está disponible para Madrid capital; no es una búsqueda postal completa de los otros cinco municipios. Madrid utiliza las asignaciones distritales del producto procesado, sin inferir distritos por proximidad. Las parcelas sin asignación fiable se conservan en «Todos los distritos».

La cobertura varía por fuente. Plan Rehabilita corresponde a Madrid y la fuente de conservación no está integrada en los otros cinco municipios. Ausencia de datos no significa ausencia de ayudas o antecedentes.
""")
    with st.expander("Algunas cosas importantes que debes saber", expanded=True):
        st.markdown("""
Los datos pueden estar incompletos o desactualizados, y no todos los edificios disponen de la misma información.

Además, una parcela catastral puede contener varios edificios o accesos. Un certificado energético de una vivienda no describe necesariamente todo el edificio, y una subvención concedida no significa que las obras hayan terminado.

**La herramienta no determina si un edificio necesita rehabilitación.** Su objetivo es facilitar la consulta y el análisis inicial de información disponible.

Para tomar decisiones concretas, siempre será necesario contrastar los datos con documentación actualizada y fuentes oficiales.
""")
    with st.expander("¿Qué queremos mejorar próximamente?"):
        st.markdown("""
Nuestro objetivo es incorporar progresivamente:

- Más información sobre edificios y su estado de conservación.
- Nuevas fuentes de certificados energéticos e inspecciones.
- Información adicional sobre programas de ayudas.
- Más municipios y mejores herramientas de búsqueda.
- Mapas, filtros y fichas cada vez más claros y útiles.

**Esto es solo el principio.** Madrid Rehab Intelligence seguirá evolucionando a medida que encontremos nuevas fuentes de información y formas más útiles de conectarlas.
""")
    st.caption(
        "Proyecto personal e independiente, en fase experimental. No constituye una certificación técnica de los inmuebles ni está afiliado oficialmente a las administraciones que publican los datos."
    )
