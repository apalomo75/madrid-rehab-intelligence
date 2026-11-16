"""Small private municipal catalogue; no financial sums by parcel or map location."""

from .i18n import ui as st

from . import demo
from .plan_rehabilita_store import catalogue


def render(*, show_map=True):
    st.title("Plan Rehabilita · Ayuntamiento de Madrid")
    if not demo.private():
        st.info(
            "Consulta local deshabilitada en modo público: licencia y redistribución no acreditadas."
        )
        return
    try:
        cases, links, actions = catalogue()
    except (OSError, ValueError, KeyError) as exc:
        st.error("No se puede verificar el producto municipal.")
        with st.expander("Detalle de fuente"):
            st.text(str(exc))
        return
    st.caption(
        "Expedientes únicos de SUB_TOTAL_XY. Las otras capas describen componentes, no ayudas adicionales. No equivale a edificios físicos, pagos ni obras ejecutadas."
    )
    cols = st.columns(3)
    districts = cols[0].multiselect(
        "Distrito", sorted(cases.district_original.unique()), key="rehabilita_district"
    )
    calls = cols[1].multiselect("Convocatoria", sorted(cases.call.unique()), key="rehabilita_call")
    categories = cols[2].multiselect(
        "Tipo de actuación · componente fuente",
        sorted(actions.category.unique()),
        key="rehabilita_action",
    )
    if districts:
        cases = cases[cases.district_original.isin(districts)]
    if calls:
        cases = cases[cases.call.isin(calls)]
    if categories:
        cases = cases[cases.case_id.isin(actions.loc[actions.category.isin(categories), "case_id"])]
    detail = cases.merge(
        links[["case_id", "link_class", "link_reason", "parcel_ref14"]],
        on="case_id",
        validate="one_to_one",
    )
    a, b, c = st.columns(3)
    a.metric("Expedientes del filtro", len(detail))
    b.metric("Expedientes con CP confirmada", int(detail.link_class.eq("A").sum()))
    c.metric(
        "CP distintas confirmadas", detail.loc[detail.link_class.eq("A"), "parcel_ref14"].nunique()
    )
    st.caption(
        "Localización = punto de fuente; confirmación = dirección exacta, un acceso y una CP aceptada. Las coincidencias B/C permanecen pendientes y no se atribuyen como ayudas de una parcela."
    )
    if detail.empty:
        st.info("No hay expedientes para estos filtros.")
        return
    st.dataframe(
        detail[
            [
                "case_id",
                "original_address",
                "district_original",
                "call",
                "dwellings",
                "TOT_PRES_P_cents",
                "SUB_AYTO_R_cents",
                "BOAM_C",
                "BOCM_C",
                "FECHA_ACTU",
                "link_class",
                "link_reason",
                "parcel_ref14",
            ]
        ].rename(
            columns={
                "SUB_AYTO_R_cents": "Subvención revisada · céntimos por expediente",
                "TOT_PRES_P_cents": "Presupuesto protegible · céntimos por expediente",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    confirmed = detail[detail.link_class.eq("A")]
    if show_map and not confirmed.empty:
        import pydeck as pdk
        from pyproj import Transformer

        points = (
            confirmed[["case_id", "parcel_ref14", "point_x", "point_y"]].dropna().head(500).copy()
        )
        transformer = Transformer.from_crs(25830, 4326, always_xy=True)
        points["longitude"], points["latitude"] = transformer.transform(
            points.point_x.to_numpy(), points.point_y.to_numpy()
        )
        st.caption(
            f"Mapa: {len(points)} puntos de expedientes confirmados, máximo 500. Varios puntos pueden referirse a la misma CP; no son edificios distintos."
        )
        st.pydeck_chart(
            pdk.Deck(
                layers=[
                    pdk.Layer(
                        "ScatterplotLayer",
                        points,
                        get_position="[longitude, latitude]",
                        get_radius=35,
                        get_fill_color=[24, 110, 150, 180],
                        pickable=True,
                    )
                ],
                initial_view_state=pdk.ViewState(latitude=40.4168, longitude=-3.7038, zoom=10),
                tooltip={"text": "Expediente {case_id}\nParcela {parcel_ref14}"},
                map_style=None,
            )
        )
        selected = st.selectbox(
            "Expediente con parcela confirmada", sorted(confirmed.case_id), key="rehabilita_case"
        )
        ref = confirmed.set_index("case_id").loc[selected, "parcel_ref14"]
        if st.button("Consultar ficha vinculada", key="rehabilita_open"):
            st.session_state.rehabilita_open_ref = ref
        if st.session_state.get("rehabilita_open_ref") == ref:
            from .municipal_fiche import render_fiche

            render_fiche("28079", "Madrid", ref)
    st.caption(
        "Datos aportados por usuario; captura original y licencia no verificadas. FECHA_ACTU es actualización, BOAM_C/BOCM_C son campos de publicación. No se conoce aquí el estado individual de pago o ejecución. PRTR se conserva como programa independiente."
    )
