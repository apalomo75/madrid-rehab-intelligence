"""Pruebas REC sin red; proveedores y HTTP simulados explícitamente."""

import os
import subprocess
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab.rec_client import (
    BASE_URL,
    HttpProvider,
    LocalProvider,
    OfficialRedirects,
    Policy,
    RecError,
    Response,
    consult,
    official_url,
    validate_ndp,
)
from madrid_rehab.rec_real_audit import DEFAULT_HTML
from madrid_rehab.rec_view import confirmed_accesses

ALLOWED = Policy(True, "test_automation_only", "test_reuse_only")
ADDRESS = "CALLE EZEQUIEL PEÑALVER 8"


def access(ndp="11140360", ref="TEST_CP", status="confirmed_access_parcel"):
    return dict(
        ndp=ndp,
        confirmed_parcel_ref14=ref,
        link_status=status,
        municipality_code="28079",
        street="EZEQUIEL PEÑALVER",
        kind="CALLE",
        number_raw="8",
        qualifier_raw="",
    )


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.content = DEFAULT_HTML.read_bytes() if DEFAULT_HTML.exists() else None

    def query(self, content=None, **kwargs):
        if content is None and self.content is None:
            self.skipTest("HTML auténtico privado ausente")
        return consult(
            "11140360",
            ADDRESS,
            policy=ALLOWED,
            provider=lambda _: Response(self.content if content is None else content),
            **kwargs,
        )

    def assert_code(self, code, function):
        with self.assertRaises(RecError) as ctx:
            function()
        self.assertEqual(ctx.exception.code, code)

    def test_ndp_and_safe_url(self):
        self.assertEqual(validate_ndp("11140360"), "11140360")
        self.assertEqual(official_url(), BASE_URL)
        self.assertEqual(official_url("11140360"), BASE_URL + "?opcion=6&origen=I&ndp=11140360")
        for ndp in ("1", "11140360&x=1", "１２３４５６７８", 11140360, None, "11140360\n"):
            with self.subTest(ndp=ndp):
                self.assert_code(
                    "invalid_ndp",
                    lambda: official_url(ndp) if ndp is not None else validate_ndp(ndp),
                )

    def test_default_and_permissions_fail_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(Policy.from_env().allowed)
        for policy in (Policy(), Policy(True), Policy(True, "a"), Policy(True, "a", "b", True)):
            provider = Mock()
            self.assert_code(
                "disabled", lambda: consult("11140360", ADDRESS, policy=policy, provider=provider)
            )
            provider.assert_not_called()

    def test_real_local_provider(self):
        if self.content is None:
            self.skipTest("HTML auténtico privado ausente")
        result = consult("11140360", ADDRESS, policy=ALLOWED, provider=LocalProvider(DEFAULT_HTML))
        self.assertEqual(result["origin"], "local_historical")
        self.assertEqual(len(result["inspections"]), 2)
        self.assertEqual(len(result["events"]), 5)
        self.assertEqual(result["inspections"][0]["opinion_raw"], "DESFAVORABLE")
        self.assertEqual(
            result["inspections"][1]["derived_state"], "archived_material_outcome_unknown"
        )
        self.assertNotIn("source_records", result)
        self.assert_code("identity", lambda: LocalProvider(DEFAULT_HTML)("11060354"))

    def test_bad_identity(self):
        if self.content is None:
            self.skipTest("HTML auténtico privado ausente")
        self.assert_code(
            "identity",
            lambda: self.query(
                self.content.replace(b"<body>", b'<body><input name="ndp" value="11060354">')
            ),
        )
        self.assert_code(
            "identity",
            lambda: consult(
                "11140360", "CALLE OTRA 1", policy=ALLOWED, provider=LocalProvider(DEFAULT_HTML)
            ),
        )

    def test_form_unexpected_incomplete_session(self):
        for code, content in [
            ("form", b"<html><form></form></html>"),
            ("unexpected_html", b"<html>otro</html>"),
            ("incomplete", b"<html><table>"),
            ("session", b"<html>Sesion caducada</html>"),
        ]:
            with self.subTest(code=code):
                self.assert_code(code, lambda: self.query(content))

    def test_parser_failure(self):
        self.assert_code("parser", lambda: self.query(parser=Mock(side_effect=ValueError("bad"))))

    def test_empty_inspections_is_valid_only_for_rec_layout(self):
        if self.content is None:
            self.skipTest("HTML auténtico privado ausente")
        import re

        text = self.content.decode("iso-8859-1")
        # Retener identificación y encabezado auténticos, retirar tablas de inspección/actuación.
        start = text.index("511/2026/12707")
        prefix = text[:start]
        prefix = prefix[: prefix.rfind("<table")]
        self.assertIn("Presentadas", prefix)
        result = self.query((prefix + "</body></html>").encode("iso-8859-1"))
        self.assertEqual(result["state"], "no_inspections")
        self.assertEqual(result["inspections"], [])
        self.assertTrue(re.search("DATOS DEL ACCESO", prefix))

    def test_http_codes(self):
        for status in (403, 429, 500):
            self.assert_code(
                "http",
                lambda: consult(
                    "11140360", ADDRESS, policy=ALLOWED, provider=lambda _: Response(b"", status)
                ),
            )
            with patch("madrid_rehab.rec_client.build_opener") as opener:
                opener.return_value.open.side_effect = HTTPError(
                    BASE_URL, status, "error", {}, None
                )
                self.assert_code("http", lambda: HttpProvider()("11140360"))

    def test_connection_and_timeout(self):
        for error, code in [
            (URLError("DNS"), "connection"),
            (TimeoutError(), "timeout"),
            (URLError(TimeoutError()), "timeout"),
        ]:
            with patch("madrid_rehab.rec_client.build_opener") as opener:
                opener.return_value.open.side_effect = error
                self.assert_code(code, lambda: HttpProvider()("11140360"))

    def test_redirect(self):
        handler = OfficialRedirects()
        req = Request(official_url("11140360"))
        self.assertEqual(
            handler.redirect_request(req, None, 302, "", {}, official_url("11140360")).full_url,
            official_url("11140360"),
        )
        self.assert_code(
            "redirect",
            lambda: handler.redirect_request(req, None, 302, "", {}, "https://example.com/"),
        )

    def test_no_html_tracked(self):
        tracked = subprocess.check_output(
            ["git", "ls-files", "data/raw/rec", "reports/rec_real"], text=True
        )
        self.assertEqual(tracked, "")
        self.assertEqual(
            subprocess.run(["git", "check-ignore", "-q", str(DEFAULT_HTML)]).returncode, 0
        )

    def test_size_mime_and_incomplete_inspection(self):
        self.assert_code("incomplete", lambda: self.query(b"x" * 2_000_001))
        self.assert_code(
            "unexpected_html",
            lambda: consult(
                "11140360",
                ADDRESS,
                policy=ALLOWED,
                provider=lambda _: Response(b"{}", content_type="application/json"),
            ),
        )
        if self.content is not None:
            self.assert_code(
                "incomplete", lambda: self.query(self.content.replace(b"05/12/2025", b""))
            )

    def test_http_provider_reads_bounded_and_uses_timeout(self):
        response = Mock()
        response.read.return_value = b"<html></html>"
        response.status = 200
        response.headers.get.return_value = None
        response.headers.get_content_type.return_value = "text/html"
        response.headers.get_content_charset.return_value = "iso-8859-1"
        with patch("madrid_rehab.rec_client.build_opener") as factory:
            factory.return_value.open.return_value.__enter__.return_value = response
            result = HttpProvider()("11140360")
            self.assertEqual(result.status, 200)
            response.read.assert_called_once_with(2_000_001)
            self.assertEqual(factory.return_value.open.call_args.kwargs["timeout"], 15)

    def test_offline_blocks_live(self):
        with patch.dict(
            os.environ,
            {
                "REC_LIVE_ENABLED": "true",
                "REC_AUTOMATION_EVIDENCE": "test",
                "REC_REUSE_EVIDENCE": "test",
                "MADRID_REHAB_OFFLINE": "1",
            },
        ):
            self.assertFalse(Policy.from_env().allowed)


class AccessTests(unittest.TestCase):
    def test_without_cp_and_ambiguous(self):
        for status in ("unmatched_access", "ambiguous_access_parcel", "candidate_access_parcel"):
            choices, ambiguous = confirmed_accesses(
                pd.DataFrame([access(status=status)]), "TEST_CP"
            )
            self.assertEqual(choices, [])
            self.assertTrue(ambiguous)

    def test_real_ambiguous_bridge_visible_without_confirmation(self):
        from madrid_rehab.conservation_view import parcel_evidence

        frame = parcel_evidence("0158902VK4705G", "rec_accesses")
        if frame is None:
            self.skipTest("Snapshot de conservación ausente")
        self.assertTrue(frame.ndp.eq("11006211").any())
        choices, ambiguous = confirmed_accesses(frame, "0158902VK4705G")
        self.assertTrue(ambiguous)
        self.assertNotIn("11006211", [c["ndp"] for c in choices])

    def test_multiple_and_conflicting_versions(self):
        choices, _ = confirmed_accesses(pd.DataFrame([access(), access("11060354")]), "TEST_CP")
        self.assertEqual(len(choices), 2)
        choices, ambiguous = confirmed_accesses(
            pd.DataFrame([access(), access(status="ambiguous_access_parcel")]), "TEST_CP"
        )
        self.assertEqual(choices, [])
        self.assertTrue(ambiguous)
        self.assertEqual(confirmed_accesses(pd.DataFrame([access()]), "TEST_CP", "28080")[0], [])


SCRIPT = """
import pandas as pd
import streamlit as st
from madrid_rehab.rec_view import render_rec_parcel
from madrid_rehab.rec_client import RecError
row = dict(ndp="11140360", confirmed_parcel_ref14="TEST_CP", link_status="confirmed_access_parcel", municipality_code="28079", street="EZEQUIEL PEÑALVER", kind="CALLE", number_raw="8", qualifier_raw="")
def loader(*args):
    return pd.DataFrame([row])
def query(ndp, address, **kwargs):
    st.session_state["calls"] = st.session_state.get("calls", 0) + 1
    if st.session_state.get("fail"):
        raise RecError("timeout", "Timeout al consultar REC")
    from madrid_rehab.rec_client import consult, LocalProvider
    from madrid_rehab.rec_real_audit import DEFAULT_HTML
    return consult(ndp, address, provider=LocalProvider(DEFAULT_HTML), **kwargs)
render_rec_parcel("TEST_CP", loader=loader, query=query)
"""


class InterfaceTests(unittest.TestCase):
    def test_disabled_external_and_no_automatic_queries(self):
        with patch.dict(os.environ, {"REC_LIVE_ENABLED": "false", "MADRID_REHAB_PUBLIC": "0"}):
            app = AppTest.from_string(SCRIPT).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("link_button")), 1)
            self.assertTrue(app.button[0].disabled)
            self.assertNotIn("calls", app.session_state)
            self.assertIsNone(app.selectbox[0].value)

    def test_no_access_uses_general_url_and_multiple_requires_selection(self):
        with patch.dict(os.environ, {"REC_LIVE_ENABLED": "false", "MADRID_REHAB_PUBLIC": "0"}):
            app = AppTest.from_string(
                SCRIPT.replace("return pd.DataFrame([row])", "return pd.DataFrame()")
            ).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.get("link_button")[0].proto.url, BASE_URL)
            self.assertTrue(any("No se ha identificado" in i.value for i in app.info))
            app = AppTest.from_string(
                SCRIPT.replace(
                    "return pd.DataFrame([row])",
                    "return pd.DataFrame([row, dict(row, ndp='11060354', number_raw='10')])",
                )
            ).run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.selectbox[0].value)
            self.assertEqual(len(app.selectbox[0].options), 2)
            self.assertNotIn("calls", app.session_state)
            app.selectbox[0].select("11060354").run()
            self.assertIn("ndp=11060354", app.get("link_button")[0].proto.url)
            self.assertNotIn("calls", app.session_state)

    def test_success_failure_and_invalidation(self):
        if not DEFAULT_HTML.exists():
            self.skipTest("HTML auténtico privado ausente")
        with patch.dict(
            os.environ,
            {
                "REC_LIVE_ENABLED": "true",
                "REC_AUTOMATION_EVIDENCE": "test",
                "REC_REUSE_EVIDENCE": "test",
                "MADRID_REHAB_PUBLIC": "0",
            },
        ):
            app = AppTest.from_string(SCRIPT).run()
            self.assertNotIn("calls", app.session_state)
            app.selectbox[0].select("11140360").run()
            self.assertNotIn("calls", app.session_state)
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["calls"], 1)
            self.assertEqual(len(app.dataframe), 2)
            self.assertEqual(len(app.get("link_button")), 1)
            app.session_state["fail"] = True
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.error), 1)
            self.assertEqual(len(app.dataframe), 0)
            self.assertEqual(len(app.get("link_button")), 1)
            with patch(
                "madrid_rehab.rec_view.time.monotonic",
                return_value=app.session_state["rec_last_query"]["at"] + 301,
            ):
                app.run()
                self.assertNotIn("rec_last_query", app.session_state)
            app.selectbox[0].set_value(None).run()
            self.assertNotIn("rec_last_query", app.session_state)

    def test_public_no_loader(self):
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            app = AppTest.from_string(
                SCRIPT.replace(
                    "return pd.DataFrame([row])", 'raise AssertionError("must not load")'
                )
            ).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.selectbox), 0)
            self.assertEqual(len(app.get("link_button")), 1)
            self.assertTrue(app.button[0].disabled)
