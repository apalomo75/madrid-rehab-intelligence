"""Real offline navigation regression against preserved local products."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import shapely as sh
from streamlit.testing.v1 import AppTest
from navigation_support import technical_app

from madrid_rehab.regional_view import (
    integrated_codes,
    partition_path,
    partition_info,
    token,
    parcel_index,
    parcel_objects,
    map_parcels,
)

PILOTS = ("28065", "28092", "28074", "28007", "28005")


class RegionalNavigation(unittest.TestCase):
    def test_real_accepted_partitions_and_map(self):
        self.assertEqual(integrated_codes(), set(PILOTS) | {"28079"})
        for code in PILOTS:
            with self.subTest(code=code):
                root = partition_path(code)
                sig = token(root)
                info = partition_info(str(root), sig)
                refs = parcel_index(str(root), sig)
                self.assertEqual(len(refs), info["cp_rows"])
                cp = parcel_objects(str(root), sig, refs.iloc[0].parcel_ref14, "cp")
                self.assertTrue(cp.selection_status.eq("accepted").all())
                center = sh.from_wkt(cp.geometry_wkt.iloc[0]).representative_point()
                nearby, _ = map_parcels(str(root), sig, center.x, center.y, 17)
                self.assertFalse(nearby.empty)
                quarantine = pd.read_parquet(root / "cp_quarantine.parquet")
                self.assertFalse(set(refs.parcel_ref14) & set(quarantine.parcel_ref14.dropna()))

    def test_map_selection_opens_parcel_and_municipality_clears_it(self):
        from madrid_rehab.regional_view import parcel_map_changed, municipality_changed

        state = {
            "regional-map": {
                "selection": {
                    "objects": {"regional-geometries": [{"properties": {"id": "0014501VK4601S"}}]}
                }
            }
        }
        with patch("madrid_rehab.regional_view.st.session_state", state):
            parcel_map_changed()
        self.assertEqual(state["regional_parcel"], "0014501VK4601S")
        municipality_changed(state, "28092")
        self.assertNotIn("regional_parcel", state)
        self.assertNotIn("regional-map", state)

    def test_evidence_products_use_same_cp_snapshot(self):
        from madrid_rehab.energy_view import root_path
        from madrid_rehab.ingest import digest
        from madrid_rehab.regional_view import regional_root_path

        energy = json.loads((root_path() / "manifest.json").read_text())
        self.assertEqual(regional_root_path(), partition_path(PILOTS[0]).parent)
        for code in PILOTS:
            path = partition_path(code) / "cp_all.parquet"
            self.assertEqual(energy["inputs"][str(path)], digest(path))

    def test_actual_entry_madrid_regional_and_return(self):
        app = technical_app("Comunidad de Madrid · Municipios y cobertura")
        self.assertFalse(app.exception)
        next(x for x in app.selectbox if x.key == "regional_municipality").set_value("28079").run()
        next(
            x for x in app.button if x.label == "Abrir fichas de Madrid capital · NDP y REC"
        ).click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="technical_navigation").value, "Madrid capital")
        self.assertTrue(any("Madrid capital" in x.value for x in app.title))

    def test_real_streamlit_selector_excludes_unintegrated(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "app.py"
            path.write_text(
                "from madrid_rehab.regional_view import render_regional\nrender_regional()"
            )
            app = AppTest.from_file(str(path), default_timeout=120).run()
            self.assertFalse(app.exception)
            selector = next(x for x in app.selectbox if x.key == "regional_municipality")
            self.assertEqual(len(selector.options), 6)
            for code in [*PILOTS, "28079"]:
                with self.subTest(code=code):
                    next(x for x in app.selectbox if x.key == "regional_municipality").set_value(
                        code
                    ).run()
                    self.assertFalse(app.exception)
                    self.assertFalse(app.error, [x.value for x in app.error])
                    self.assertTrue(any(x.label == "Zona de exploración" for x in app.selectbox))
                    self.assertTrue(any(x.label == "Limpiar selección" for x in app.button))


if __name__ == "__main__":
    unittest.main()
