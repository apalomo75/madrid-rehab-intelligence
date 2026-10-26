"""Regresión con bytes auténticos locales; nunca incluye el HTML en Git."""

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from madrid_rehab.rec_real_audit import DEFAULT_HTML, REAL_SHA256, audit


class RealRecTests(unittest.TestCase):
    def test_authentic_response_and_all_fields(self):
        html = Path(os.environ.get("MADRID_REHAB_REC_REAL_HTML", str(DEFAULT_HTML)))
        if not html.exists():
            self.skipTest("HTML auténtico privado ausente; no es validación real")
        self.assertEqual(hashlib.sha256(html.read_bytes()).hexdigest(), REAL_SHA256)
        with tempfile.TemporaryDirectory() as tmp:
            r = audit(html, Path(tmp) / "audit")
        self.assertEqual(len(r["cases"]), 6)
        self.assertEqual(len(r["inspections"]), 2)
        self.assertEqual(len(r["events"]), 5)
        self.assertEqual(r["source_records"][0]["warnings"], [])
        iee, ite = r["inspections"]
        self.assertEqual(
            (
                iee["case_reference"],
                iee["inspection_type"],
                iee["presentation_date"],
                iee["registration_raw"],
                iee["opinion_raw"],
                iee["scope_raw"],
                iee["status_raw"],
                iee["department_raw"],
            ),
            (
                "511/2026/12707",
                "IEE",
                "2025-12-05",
                "20252104910",
                "DESFAVORABLE",
                "TOTAL",
                "Pendiente subsanación deficiencias",
                "Unidad Técnica II",
            ),
        )
        self.assertEqual(
            iee["deficiency_raw"],
            "[B - ESTADO DE FACHADAS INTERIORES, EXTERIORES, MEDIANERAS Y OTROS ELEMENTOS]",
        )
        self.assertEqual(iee["derived_state"], "unfavorable_explicitly_pending")
        self.assertEqual(
            (
                ite["case_reference"],
                ite["presentation_date"],
                ite["registration_raw"],
                ite["inspection_type"],
                ite["opinion_raw"],
                ite["scope_raw"],
                ite["status_raw"],
                ite["deficiency_raw"],
                ite["followup_case_raw"],
            ),
            (
                "711/2015/14240",
                "2015-05-07",
                "20150465367",
                "ITE",
                "DESFAVORABLE",
                "TOTAL",
                "ARCHIVADO",
                "",
                "711/2012/23569",
            ),
        )
        self.assertEqual(ite["derived_state"], "archived_material_outcome_unknown")
        self.assertEqual(
            [(e["case_reference"], e["resolution_date"], e["resolution_raw"]) for e in r["events"]],
            [
                ("711/2012/23569", "2019-06-14", "Resolver"),
                ("121/2003/00111", "2004-04-16", "ÓRDENES URBANÍSTICAS"),
                ("121/2002/02727", "2015-10-23", "ARCHIVAR"),
                ("", "2003-04-25", "ÓRDENES URBANÍSTICAS"),
                ("711/2023/11801", "2024-12-10", "Imponer Multa"),
            ],
        )
        self.assertEqual(r["events"][-1]["event_kind"], "coercive_fine")
        self.assertTrue(any(x["relation"] == "execution_followup" for x in r["relations"]))
        self.assertNotIn("ndp", r["accesses"][0])
        self.assertTrue(all(not x["public_exposure"] for x in r["inspections"]))
