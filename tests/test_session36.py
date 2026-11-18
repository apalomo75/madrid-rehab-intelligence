"""Documentary P5 selection and date presentation regressions."""

from types import SimpleNamespace
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from madrid_rehab import commercial_filters as filters, i18n, public_prtr
from madrid_rehab import production_bundle as bundle
from madrid_rehab.commercial_fiche import Quality
from madrid_rehab.commercial_view import p5_records


class Session36Tests(unittest.TestCase):
    def test_dates_es_en(self):
        for lang, expected in [("es", "14/04/2026"), ("en", "14 Apr 2026")]:
            for value in ["2026-04-14", "2026-04-14T00:00:00", "2026-04-14T00:00:00Z"]:
                self.assertEqual(i18n.present_dates(value, lang=lang), expected)
        for value in [
            "2026-02-30",
            "2026-04-14T10:35:19Z",
            "https://source/2026-04-14",
            "EXP-2026-04-14",
            "Sin fecha",
        ]:
            self.assertEqual(i18n.present_dates(value, lang="es"), value)

    def test_datetime_column(self):
        original = pd.DataFrame({"Fecha administrativa": pd.to_datetime(["2026-04-14 12:30:00"])})
        with patch.object(i18n, "language", return_value="es"):
            self.assertEqual(i18n.localize_frame(original).iloc[0, 0], "14/04/2026")
        self.assertEqual(original.iloc[0, 0].hour, 12)

    def test_administrative_time_not_relevant(self):
        self.assertEqual(
            i18n.present_dates("2026-04-14T15:30:00", lang="es", preserve_time=False), "14/04/2026"
        )

    def test_frames_preserve_originals(self):
        original = pd.DataFrame(
            {"Fecha declarada": ["2025-06-17T00:00:00"], "Referencia": ["2025-06-17"]}
        )
        for lang, expected in [("es", "17/06/2025"), ("en", "17 Jun 2025")]:
            with patch.object(i18n, "language", return_value=lang):
                result = i18n.localize_frame(original)
                self.assertEqual(result.iloc[0, 0], expected)
                self.assertEqual(result.iloc[0, 1], "2025-06-17")
        self.assertEqual(original.iloc[0, 0], "2025-06-17T00:00:00")

    def test_p5_confirmed_cp_only(self):
        def evidence(key, program, quality):
            return SimpleNamespace(entity_id=key, value={"Programa": program}, quality=quality)

        good = evidence("real", "P5", Quality.PARCEL)
        model = SimpleNamespace(
            kind="cp",
            grants=[
                good,
                good,
                evidence("bad", "P5", Quality.AMBIGUOUS),
                evidence("other", "P3", Quality.PARCEL),
            ],
        )
        self.assertEqual(p5_records(model), [good])
        model.kind = "bu"
        self.assertEqual(p5_records(model), [])

    def test_p5_caution_both_languages(self):
        for lang in ("es", "en"):
            text = i18n.MESSAGES["p5.scope"][lang]
            self.assertIn("no acredita" if lang == "es" else "does not establish", text)


class RealP5PresentationTests(unittest.TestCase):
    root = Path("data/deployment/madrid_rehab_v1_04_candidate_01")

    def setUp(self):
        if not self.root.exists():
            self.skipTest("v1.04 bundle unavailable")
        env = patch.dict(
            os.environ,
            {
                "MADRID_REHAB_BUNDLE_DIR": str(self.root),
                "MADRID_REHAB_PUBLIC": "1",
                "MADRID_REHAB_OFFLINE": "1",
            },
        )
        env.start()
        self.addCleanup(env.stop)

    def test_real_v104_counts_and_combinations(self):
        rows = bundle.read(public_prtr.PRODUCT)
        p5 = rows[rows.programa.eq("P5") & rows.match_status.isin(public_prtr.CONFIRMED)]
        counts = {"28005": 43, "28007": 39, "28065": 7, "28074": 22, "28079": 491, "28092": 78}
        self.assertEqual(p5.groupby("municipality_code").parcel_ref14.nunique().to_dict(), counts)
        self.assertEqual(p5.expediente_id.nunique(), 718)

        def refs(code, selected, logic="OR", **kwargs):
            return set(filters.query(code, selected, logic, **kwargs).parcel_ref14)

        for code, count in counts.items():
            actual = refs(code, ["p5"])
            self.assertEqual(len(actual), count)
            self.assertEqual(actual, set(p5[p5.municipality_code.eq(code)].parcel_ref14))

        code = "28079"
        programme = refs(code, ["p5"])
        energy = refs(code, ["energy"])
        plan = refs(code, ["rehabilita"])
        self.assertLess(programme, refs(code, ["prtr"]))
        for logic, expected in [
            ("OR", programme | energy | plan),
            ("AND", programme & energy & plan),
        ]:
            self.assertEqual(refs(code, ["p5", "energy", "rehabilita"], logic), expected)
            self.assertEqual(
                refs(code, ["prtr", "p5", "energy", "rehabilita"], logic, prtr_program="P4"),
                expected,
            )

    def test_real_v104_filter_tooltip_and_navigation(self):
        from streamlit.testing.v1 import AppTest

        from test_municipal_map_events import send_chart_event

        app = AppTest.from_string(
            "from madrid_rehab.i18n import language_selector\nlanguage_selector()\n"
            "from madrid_rehab.commercial_explorer import render\nrender('28079', 'Madrid')",
            default_timeout=180,
        ).run()
        key = "priority_28079_p5"
        app.checkbox(key=key).check().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "491")
        self.assertEqual(app.checkbox(key=key).label, i18n.MESSAGES["filters.p5"]["es"])
        self.assertEqual(app.checkbox(key=key).proto.help, i18n.MESSAGES["filters.p5_help"]["es"])
        refs = set(filters.query("28079", ["p5"]).parcel_ref14)
        chart = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
        map_refs = {f["properties"]["unit_id"] for f in chart["layers"][0]["data"]["features"]}
        self.assertEqual(map_refs, refs)
        button = next(b for b in app.button if b.label == "Abrir ficha")
        ref = button.key.rsplit("_", 1)[1]
        self.assertIn(ref, refs)
        button.click().run()
        self.assertEqual(app.session_state["fiche_identity"], ("28079", "cp", ref))
        next(b for b in app.button if b.label == "Volver a la lista").click().run()
        send_chart_event(app, ref)
        self.assertEqual(app.session_state["fiche_identity"], ("28079", "cp", ref))
        app.checkbox(key="priority_28079_prtr").check().run()
        self.assertEqual(app.session_state["fiche_identity"], ("28079", "cp", ref))
        app.radio(key="language_selector").set_value("EN").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.checkbox(key=key).value)
        self.assertEqual(app.checkbox(key=key).label, i18n.MESSAGES["filters.p5"]["en"])
        self.assertEqual(app.checkbox(key=key).proto.help, i18n.MESSAGES["filters.p5_help"]["en"])
        self.assertIn(i18n.MESSAGES["filters.p5_with_prtr"]["en"], [c.value for c in app.caption])
        self.assertEqual(app.metric[0].value, "491")

    def test_real_v104_award_in_both_languages(self):
        from streamlit.testing.v1 import AppTest

        rows = bundle.read(public_prtr.PRODUCT)
        row = rows[rows.programa.eq("P5")].iloc[0]
        script = """
import pandas as pd
from madrid_rehab import i18n, public_prtr
from madrid_rehab.commercial_fiche import build_model
from madrid_rehab.commercial_view import render
import streamlit as st
st.session_state['i18n_language'] = LANG
records = public_prtr.records(CODE, REF)
model = build_model(CODE, 'Madrid', REF, 'cp', pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), records, pd.DataFrame())
render(model, {})
"""
        for lang in ("es", "en"):
            code = (
                f"LANG={lang!r}\nCODE={row.municipality_code!r}\nREF={row.parcel_ref14!r}\n"
                + script
            )
            app = AppTest.from_string(code, default_timeout=180).run()
            self.assertFalse(app.exception)
            content = "\n".join(str(e.value) for e in app.markdown)
            captions = "\n".join(str(e.value) for e in app.caption)
            self.assertIn(i18n.MESSAGES["p5.title"][lang], content)
            self.assertIn(i18n.MESSAGES["p5.scope"][lang], captions)
            self.assertEqual(content.count(row.expediente_id), 1)
            self.assertTrue(any("coam.org" in e.proto.url for e in app.get("link_button")))
