"""Real multi-cell identities and partial-source failures through widget callbacks."""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import test_municipal_map_events as events
from madrid_rehab.municipal_fiche import SECTIONS
from madrid_rehab.municipal_navigation import (
    covered_municipalities,
    object_index,
    resolve_object,
    zone_page,
)


class FicheResilienceTests(unittest.TestCase):
    def test_real_multicell_objects(self):
        results = []
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0"}):
            app = events.MapEventTests().make_app()
            for code in covered_municipalities().municipality_code:
                app.selectbox(key="town").set_value(code).run()
                for kind in ("cp", "bu"):
                    app.radio[0].set_value(
                        "Parcelas" if kind == "cp" else "Objetos BU independientes"
                    ).run()
                    index = object_index(code, kind)
                    zones = index.groupby("zone").size().sort_values(ascending=False).index[:2]
                    refs = [zone_page(index, zone, 0)[0] for zone in zones]
                    if code == "28005" and kind == "cp":
                        refs = ["8727902VK6882N", "4731501VK6843S"]
                    if code == "28079" and kind == "cp":
                        refs[0] = "0010510VK4701A"
                    for ref in refs:
                        with self.subTest(code=code, kind=kind, ref=ref):
                            status, frame = resolve_object(code, ref, kind)
                            self.assertEqual(len(frame), 1, status)
                            self.assertTrue(frame.iloc[0].usable_geometry)
                            zone = index.loc[index.parcel_ref14.eq(ref), "zone"].item()
                            next(
                                s for s in app.selectbox if s.label == "Zona de exploración"
                            ).set_value(zone).run()
                            group = index[index.zone.eq(zone)].parcel_ref14.tolist()
                            page = group.index(ref) // 500
                            next(
                                s for s in app.selectbox if s.label == "Página de objetos"
                            ).set_value(page).run()
                            events.send_chart_event(app, ref)
                            self.assertEqual(
                                tuple(app.session_state["fiche_identity"]), (code, kind, ref)
                            )
                            self.assertEqual(tuple(t.label for t in app.tabs), SECTIONS)
                            self.assertTrue(any(ref in h.value for h in app.subheader))
                            self.assertTrue(any(ref in m.value for m in app.markdown))
                            results.append(
                                dict(
                                    code=code,
                                    kind=kind,
                                    identifier=ref,
                                    zone=zone,
                                    page=page,
                                    reader=status,
                                    sections=list(app.session_state["fiche_sections"]),
                                )
                            )
        Path("reports/session_16/real_cases.json").write_text(json.dumps(results, indent=2))

    def test_auxiliary_failures_preserve_current_identity_and_all_sections(self):
        app = events.MapEventTests().make_app()
        app.selectbox(key="town").set_value("28079").run()
        for target in (
            "madrid_rehab.conservation_view.parcel_evidence",
            "madrid_rehab.energy_view.render_energy_parcel",
            "madrid_rehab.municipal_fiche.render_prtr",
            "madrid_rehab.cadastral_identity.construction_records",
        ):
            with (
                self.subTest(target=target),
                patch(target, side_effect=OSError("injected source failure")),
            ):
                app.text_input[0].set_value("0010510VK4701A").run()
                self.assertFalse(app.exception)
                self.assertTrue(any("0010510VK4701A" in h.value for h in app.subheader))
                self.assertEqual(tuple(t.label for t in app.tabs), SECTIONS)
                self.assertTrue(app.warning)
                other = object_index("28079", "cp").parcel_ref14.iloc[-1]
                app.text_input[0].set_value(other).run()
                self.assertEqual(tuple(app.session_state["fiche_identity"]), ("28079", "cp", other))
                self.assertFalse(any("0010510VK4701A" in h.value for h in app.subheader))
                next(b for b in app.button if b.label == "Limpiar selección").click().run()
                self.assertIsNone(app.session_state["fiche_identity"])
                self.assertFalse(app.subheader)

    def test_missing_sources_and_debug_are_explicit(self):
        with patch.dict(os.environ, {"MADRID_REHAB_DEBUG_SELECTION": "1"}):
            app = events.MapEventTests().make_app()
            app.selectbox(key="town").set_value("28079").run()
            with (
                patch(
                    "madrid_rehab.energy_view.root_path",
                    return_value=Path("/tmp/absent-session16-energy"),
                ),
                patch("madrid_rehab.grants_view.read_view", return_value=None),
            ):
                app.text_input[0].set_value("0010510VK4701A").run()
                self.assertFalse(app.exception)
                self.assertEqual(len(app.tabs), 6)
                self.assertTrue(app.subheader)
                self.assertTrue(
                    any(e.label == "Diagnóstico técnico de selección" for e in app.expander)
                )

    def test_reader_never_collapses_ambiguity_and_rejects_wrong_municipality(self):
        _, frame = resolve_object("28005", "8727902VK6882N", "cp")
        import pandas as pd

        with patch("madrid_rehab.demo.read", return_value=pd.concat([frame, frame])):
            self.assertEqual(
                resolve_object("28005", "8727902VK6882N", "cp")[0], "referencia ambigua"
            )
        with patch("madrid_rehab.demo.read", return_value=frame):
            self.assertEqual(
                resolve_object("28065", "8727902VK6882N", "cp")[0], "incompatibilidad municipal"
            )
        self.assertEqual(resolve_object("28005", "invalid", "cp")[0], "identificador inválido")
        with patch("madrid_rehab.demo.read", side_effect=OSError("unreadable")):
            self.assertEqual(resolve_object("28005", "8727902VK6882N", "cp")[0], "error de lectura")
