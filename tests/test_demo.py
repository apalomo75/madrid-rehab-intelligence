"""Real snapshot integration and regression tests; no synthetic data in demo."""

import os
import socket
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab import demo
from madrid_rehab.rec_diagnostic import Forms, classify, diagnose, query_allowed


class RecDiagnosticTests(unittest.TestCase):
    def test_permission_required(self):
        self.assertFalse(query_allowed(public_information=True, automation_permission=False))
        self.assertTrue(query_allowed(public_information=True, automation_permission=True))
        self.assertFalse(
            query_allowed(public_information=True, automation_permission=True, challenge=True)
        )
        self.assertFalse(
            query_allowed(public_information=True, automation_permission=True, authenticated=True)
        )

    def test_dns_tls_http_distinguished(self):
        import ssl

        self.assertEqual(classify(urllib.error.URLError(socket.gaierror(-3, "DNS"))), "dns_failure")
        self.assertEqual(classify(urllib.error.URLError(ssl.SSLError("TLS"))), "tls_failure")
        self.assertEqual(
            classify(urllib.error.HTTPError("url", 403, "Forbidden", {}, None)), "http_error"
        )
        self.assertEqual(
            classify(urllib.error.HTTPError("url", 302, "Redirect", {}, None)), "redirect_stopped"
        )

    def test_missing_session_not_guessed(self):
        parser = Forms()
        parser.feed('<form method="post"><input name="ndp"><input name="token" value="SECRET">')
        self.assertEqual(parser.forms[0]["method"], "POST")
        self.assertNotIn("SECRET", str(parser.forms))
        parser.feed("<tr><td>incomplete")
        self.assertEqual(parser.forms[0]["fields"][0]["name"], "ndp")

    def test_dns_manifest_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "capture"
            with patch(
                "urllib.request.OpenerDirector.open",
                side_effect=urllib.error.URLError(socket.gaierror(-3, "DNS")),
            ):
                report = diagnose(out)
            self.assertEqual(report["record_queries"], 0)
            self.assertEqual(report["status"], "dns_failure")
            self.assertIsNone(report["http_status"])
            with self.assertRaises(FileExistsError):
                diagnose(out)


@unittest.skipUnless((demo.ENERGY / "manifest.json").exists(), "Real snapshots unavailable")
class DemoTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0", "MADRID_REHAB_DEMO": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_three_real_cases(self):
        for _, (code, ref) in demo.CASES.items():
            with self.subTest(code=code):
                cp = demo.parcel(code, ref)
                self.assertEqual(len(cp), 1)
                cert, events, accesses, joint = demo.evidence(code, ref)
                self.assertGreater(len(cert), 0)
                if code == "28079":
                    self.assertTrue(events.event_type.eq("order").any())
                    self.assertFalse(accesses.empty)
                if code == "28005":
                    self.assertGreater(joint.grant_case_count.max(), 0)

    def test_all_pilot_partitions(self):
        for code in ["28005", "28007", "28065", "28074", "28092"]:
            root, rel = demo.cp_source(code)
            refs = demo.read(root, rel, columns=["parcel_ref14"])
            self.assertFalse(demo.parcel(code, refs.iloc[0].parcel_ref14).empty)

    def test_municipality_without_cp(self):
        self.assertEqual(len(demo.municipalities()), 179)
        self.assertTrue(demo.parcel("28001", "0010510VK4701A").empty)

    def test_absent_reference(self):
        self.assertTrue(demo.parcel("28079", "0000000ZZ0000Z").empty)

    def test_empty_energy_and_conservation(self):
        cert, events, _, _ = demo.evidence("28065", "0000000ZZ0000Z")
        self.assertTrue(cert.empty)
        self.assertTrue(events.empty)

    def test_public_does_not_read_evidence(self):
        with (
            patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}),
            patch.object(demo, "read", side_effect=AssertionError("Read forbidden")),
        ):
            self.assertTrue(all(x.empty for x in demo.evidence("28079", "0010510VK4701A")))
            self.assertEqual(demo.research_refs("28079", "CEEE y PRTR"), [])

    def test_export_excludes_restricted_content_in_both_modes(self):
        cp = demo.parcel("28079", "0010510VK4701A")
        for mode in ["0", "1"]:
            with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": mode}):
                document = demo.export_html(
                    "28079",
                    "<script>X</script>",
                    "0010510VK4701A",
                    cp,
                    cert=pd.DataFrame({"secret": ["SECRET_CEEE"]}),
                    events="SECRET_REC",
                    grants="SECRET_PRTR",
                )
                self.assertNotIn("<script>", document)
                for secret in ["SECRET_CEEE", "SECRET_REC", "SECRET_PRTR"]:
                    self.assertNotIn(secret, document)
                self.assertIn("no certificación oficial", document)
        with self.assertRaises(ValueError):
            demo.export_html("28079", "Madrid", "unknown", pd.DataFrame())

    def test_research_cases_no_arbitrary_rank(self):
        self.assertIn("0015301VK7801N", demo.research_refs("28005", "CEEE y PRTR"))
        self.assertIn("0010510VK4701A", demo.research_refs("28079", "Órdenes históricas (Madrid)"))
        self.assertEqual(demo.research_refs("28065", "Órdenes históricas (Madrid)"), [])

    def test_apptest_cases_and_public(self):
        app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=45).run()
        self.assertFalse(app.exception)
        for case, (_, ref) in demo.CASES.items():
            app.selectbox[0].select(case).run()
            self.assertFalse(app.exception)
            self.assertTrue(any(ref in x.value for x in app.subheader))
            self.assertEqual(len(app.tabs), 6)
        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}):
            app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=45).run()
            app.text_input[0].set_value("0010510VK4701A").run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Información protegida" in x.value for x in app.caption))

    def test_apptest_no_cp_and_analyst(self):
        app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=45).run()
        self.assertEqual(len(app.selectbox[1].options), 6)
        app.selectbox[1].select("28065").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Cobertura catastral parcial" in x.value for x in app.caption))
        app.sidebar.radio[0].set_value("Analista").run()
        app.radio(key="city_navigation").set_value("Madrid capital").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Madrid capital" in x.value for x in app.title))
