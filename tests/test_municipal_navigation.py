"""Six real municipal products: complete paging, selection and shared UI."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from madrid_rehab import demo
from madrid_rehab.municipal_fiche import SECTIONS
from madrid_rehab.municipal_navigation import (
    PAGE_SIZE,
    covered_municipalities,
    parcel_index,
    picked,
    zone_page,
    object_index,
    selected_object,
)


class MunicipalNavigationTests(unittest.TestCase):
    def test_real_coverage_and_exhaustive_spatial_pages(self):
        towns = covered_municipalities()
        self.assertEqual(
            set(towns.municipality_code), {"28079", "28065", "28092", "28074", "28007", "28005"}
        )
        self.assertEqual(len(demo.municipalities()), 179)
        for code in towns.municipality_code:
            with self.subTest(code=code):
                index = parcel_index(code)
                visited = []
                for zone, group in index.groupby("zone"):
                    for page in range((len(group) + PAGE_SIZE - 1) // PAGE_SIZE):
                        refs = zone_page(index, zone, page)
                        self.assertLessEqual(len(refs), PAGE_SIZE)
                        visited.extend(refs)
                self.assertEqual(len(visited), len(set(visited)))
                self.assertEqual(set(visited), set(index.parcel_ref14))
                shuffled = index.sample(frac=1, random_state=42)
                zone = index.zone.iloc[-1]
                self.assertEqual(zone_page(index, zone, 0), zone_page(shuffled, zone, 0))
                with self.assertRaises(ValueError):
                    zone_page(index, zone, -1)

    def test_normal_entry_uses_shared_explorer_and_six_readable_names(self):
        with patch.dict(os.environ, {"MADRID_REHAB_DEMO": "0", "MADRID_REHAB_PUBLIC": "1"}):
            app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=90).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.radio(key="city_navigation").value, "Mapa comercial")
            app.radio(key="city_navigation").set_value("Explorar municipios").run()
            selector = next(x for x in app.selectbox if x.label == "Municipio")
            self.assertEqual(
                set(selector.options),
                {"Madrid", "Getafe", "Móstoles", "Leganés", "Alcorcón", "Alcalá de Henares"},
            )
            self.assertTrue(any(x.label == "Zona de exploración" for x in app.selectbox))

    def test_map_identity_allowlist(self):
        def event(ref):
            return {
                "selection": {
                    "objects": {"regional-geometries": [{"properties": {"unit_id": ref}}]}
                }
            }

        self.assertEqual(picked(event("accepted"), ["accepted"]), "accepted")
        self.assertIsNone(picked(event("quarantine"), ["accepted"]))
        self.assertIsNone(picked({}, ["accepted"]))

    def test_shared_six_municipal_controls_fiche_and_reset(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}),
        ):
            path = Path(temp) / "app.py"
            path.write_text("""from madrid_rehab.municipal_navigation import covered_municipalities, render_explorer
import streamlit as st
towns = covered_municipalities().set_index("municipality_code")
code = st.selectbox("Municipio", towns.index.tolist(), format_func=lambda c: towns.loc[c, "name"])
render_explorer(code, towns.loc[code, "name"])
""")
            app = AppTest.from_file(str(path), default_timeout=90).run()
            for code in covered_municipalities().municipality_code:
                with self.subTest(code=code):
                    app.selectbox[0].set_value(code).run()
                    index = parcel_index(code)
                    # Visit a distant cell rather than the initial file rows.
                    zone = index.zone.iloc[-1]
                    next(x for x in app.selectbox if x.label == "Zona de exploración").set_value(
                        zone
                    ).run()
                    refs = zone_page(index, zone, 0)
                    ref = picked(
                        {
                            "selection": {
                                "objects": {
                                    "regional-geometries": [{"properties": {"unit_id": refs[-1]}}]
                                }
                            }
                        },
                        refs,
                    )
                    app.text_input[0].set_value(ref).run()
                    self.assertFalse(app.exception)
                    self.assertFalse(app.error)
                    self.assertTrue(any(ref in x.value for x in app.subheader))
                    self.assertEqual(tuple(x.label for x in app.tabs), SECTIONS)
                    self.assertTrue(any(x.label == "Página de objetos" for x in app.selectbox))
                    previous_epoch = app.session_state[f"municipal_{code}__cp_map_epoch"]
                    next(x for x in app.button if x.label == "Limpiar selección").click().run()
                    self.assertFalse(app.exception)
                    self.assertEqual(app.text_input[0].value, "")
                    self.assertEqual(
                        app.session_state[f"municipal_{code}__cp_map_epoch"], previous_epoch + 1
                    )
                    self.assertFalse(app.subheader)
                    next(x for x in app.radio if x.label == "Objetos catastrales").set_value(
                        "Objetos BU independientes"
                    ).run()
                    bu_index = object_index(code, "bu")
                    identifier = bu_index.parcel_ref14.iloc[-1]
                    app.text_input[0].set_value(identifier).run()
                    self.assertFalse(app.exception)
                    self.assertFalse(app.error)
                    self.assertEqual(tuple(x.label for x in app.tabs), SECTIONS)
                    self.assertFalse(selected_object(code, identifier, "bu").empty)
                    if code != "28079":
                        self.assertTrue(
                            any("Relaciones documentales CP–BU" in x.value for x in app.markdown)
                        )
                        self.assertFalse(app.get("link_button"))
