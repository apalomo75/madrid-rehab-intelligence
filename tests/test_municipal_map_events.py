"""Real deck specs -> serialized widget event -> registered callback -> rerun.

This complements AppTest's missing WebGL mouse support; it does not verify picking.
"""

import json
import os
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from madrid_rehab.municipal_fiche import SECTIONS
from madrid_rehab.municipal_navigation import (
    apply_map_event,
    covered_municipalities,
    object_index,
    selected_object,
)


def send_chart_event(app, identifier):
    charts = app.get("deck_gl_json_chart")
    assert len(charts) == 1, "Exactly one main chart expected"
    chart = charts[0].proto
    layer = json.loads(chart.json)["layers"][0]
    assert layer["pickable"]
    features = layer["data"]["features"]
    position, feature = next(
        (i, f) for i, f in enumerate(features) if f["properties"]["unit_id"] == identifier
    )
    states = app._tree.get_widget_states()
    widget = states.widgets.add()
    widget.id = chart.id
    widget.string_value = json.dumps(
        {"selection": {"indices": {layer["id"]: [position]}, "objects": {layer["id"]: [feature]}}}
    )
    app._run(states)
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]


class MapEventTests(unittest.TestCase):
    def make_app(self):
        return AppTest.from_string(
            """import streamlit as st
from madrid_rehab.municipal_navigation import covered_municipalities, render_explorer, render_territories
towns = covered_municipalities().set_index("municipality_code")
code = st.selectbox("Municipio", towns.index.tolist(), key="town",
    on_change=lambda: st.session_state.update(municipal_show_territories=False))
st.button("Municipios", on_click=lambda: st.session_state.update(municipal_show_territories=True))
if st.session_state.get("municipal_show_territories"):
    render_territories("town")
else:
    render_explorer(code, towns.loc[code, "name"])
""",
            default_timeout=90,
        ).run()

    def assert_fiche(self, app, identifier):
        self.assertTrue(any(identifier in h.value for h in app.subheader))
        self.assertEqual(tuple(t.label for t in app.tabs), SECTIONS)
        self.assertEqual(app.text_input[0].value, identifier)

    def test_six_event_journeys_cp_bu_clear_return_and_municipality(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}):
            app = self.make_app()
            for code in covered_municipalities().municipality_code:
                with self.subTest(code=code):
                    next(b for b in app.button if b.label == "Municipios").click().run()
                    send_chart_event(app, code)
                    self.assertEqual(app.selectbox(key="town").value, code)
                    self.assertFalse(app.subheader)
                    for kind in ["cp", "bu"]:
                        if kind == "bu":
                            app.radio[0].set_value("Objetos BU independientes").run()
                        index = object_index(code, kind)
                        zone = index.groupby("zone").size().idxmax()
                        send_chart_event(app, zone)
                        features = json.loads(app.get("deck_gl_json_chart")[0].proto.json)[
                            "layers"
                        ][0]["data"]["features"]
                        refs = [f["properties"]["unit_id"] for f in features]
                        self.assertLessEqual(len(refs), 500)
                        for ref in refs[:2]:
                            send_chart_event(app, ref)
                            self.assert_fiche(app, ref)
                        ref = refs[0]
                        next(b for b in app.button if b.label == "Limpiar selección").click().run()
                        self.assertFalse(app.subheader)
                        send_chart_event(app, ref)
                        self.assert_fiche(app, ref)
                        pages = next(s for s in app.selectbox if s.label == "Página de objetos")
                        if len(pages.options) > 1:
                            pages.set_value(1).run()
                            self.assertFalse(app.subheader)
                            new_features = json.loads(app.get("deck_gl_json_chart")[0].proto.json)[
                                "layers"
                            ][0]["data"]["features"]
                            self.assertFalse(
                                set(refs) & {f["properties"]["unit_id"] for f in new_features}
                            )
                        next(
                            b for b in app.button if b.label == "Volver a cuadrículas"
                        ).click().run()
                        self.assertFalse(app.subheader)
                        self.assertEqual(
                            next(
                                s for s in app.selectbox if s.label == "Zona de exploración"
                            ).value,
                            "Vista general",
                        )

    def test_alcala_real_references_search_click_and_reselect(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}):
            app = self.make_app()
            app.selectbox(key="town").set_value("28005").run()
            index = object_index("28005", "cp")
            for ref in ["8727902VK6882N", "4731501VK6843S"]:
                cp = selected_object("28005", ref, "cp")
                self.assertEqual(len(cp), 1)
                self.assertEqual(cp.iloc[0].municipality_code, "28005")
                self.assertEqual(cp.iloc[0].selection_status, "accepted")
                self.assertTrue(cp.iloc[0].usable_geometry)
                zone = index.loc[index.parcel_ref14.eq(ref), "zone"].item()
                app.text_input[0].set_value(ref).run()
                self.assert_fiche(app, ref)
                self.assertEqual(
                    next(s for s in app.selectbox if s.label == "Zona de exploración").value, zone
                )
                next(b for b in app.button if b.label == "Limpiar selección").click().run()
                send_chart_event(app, ref)
                self.assert_fiche(app, ref)
                self.assertEqual(app.session_state["municipal_28005__cp_selected"], ref)

    def test_reject_stale_context_and_invisible_objects(self):
        state = {"municipal_active_context": ("28005", "p"), "p_selected": "old"}
        event = {
            "selection": {"objects": {"regional-geometries": [{"properties": {"unit_id": "new"}}]}}
        }
        apply_map_event(state, event, ["new"], "28065", "p", "zone")
        self.assertEqual(state["p_selected"], "old")
        apply_map_event(state, event, ["other"], "28005", "p", "zone")
        self.assertEqual(state["p_selected"], "old")

    def test_empty_coverage_has_message_and_no_blank_chart(self):
        import pandas as pd

        with patch("madrid_rehab.municipal_navigation.object_index", return_value=pd.DataFrame()):
            app = self.make_app()
            self.assertFalse(app.exception)
            self.assertFalse(app.get("deck_gl_json_chart"))
            self.assertTrue(any("No disponible" in item.value for item in app.info))

    def test_invalid_search_is_explicit(self):
        app = self.make_app()
        app.text_input[0].set_value("NO_EXISTE").run()
        self.assertTrue(app.error)
        self.assertFalse(app.subheader)
