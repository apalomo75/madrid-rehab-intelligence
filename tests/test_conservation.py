"""Las fichas generadas en este módulo son SINTÉTICAS; nunca datos de producción."""

import hashlib
import json
import os
import unittest
from unittest.mock import patch

import pandas as pd

from madrid_rehab.conservation import (
    DEFAULT,
    access_links,
    build,
    evidence_profiles,
    investigation_signal,
    municipal_evidence,
    relation_level,
)
from madrid_rehab.rec import administrative_state, parse_rec


def fixture(rows, section="IEE"):
    return (
        "<h2>"
        + section
        + "</h2><table>"
        + "".join(
            "<tr><td>" + label + "</td><td colspan='3'>" + value + "</td></tr>"
            for label, value in rows
        )
        + "</table>"
    )


def parse(text, encoding="utf-8"):
    return parse_rec(
        text.encode(encoding), source_id="synthetic:test", observed_at="2026-10-24", synthetic=True
    )


class RecTests(unittest.TestCase):
    def inspection(
        self, opinion="DESFAVORABLE", status="Pendiente de subsanación de deficiencias", extra=()
    ):
        return parse(
            fixture(
                [
                    ("Expediente", "999/2020/00001"),
                    ("Tipo", "IEE"),
                    ("Dictamen", opinion),
                    ("Situación administrativa", status),
                    *extra,
                ]
            )
        )

    def test_multiple_cases_and_duplicate_identity(self):
        text = fixture([("Expediente", "999/2020/00001"), ("Dictamen", "FAVORABLE")], "ITE")
        r = parse(
            text
            + text
            + fixture([("Expediente", "999/2021/00002"), ("Dictamen", "DESFAVORABLE")], "IEE")
        )
        self.assertEqual(len(r["cases"]), 2)
        self.assertEqual(len(r["inspections"]), 2)
        self.assertEqual(len(r["relations"]), 2)

    def test_ite_favorable_and_unfavorable(self):
        for opinion, expected in [("FAVORABLE", "favorable"), ("DESFAVORABLE", "unknown")]:
            with self.subTest(opinion=opinion):
                r = parse(fixture([("Expediente", "999/2020/00001"), ("Dictamen", opinion)], "ITE"))
                self.assertEqual(r["inspections"][0]["derived_state"], expected)

    def test_iee_deficiency_literal_without_invented_taxonomy(self):
        r = self.inspection(extra=[("Causa", "Fachadas interiores y exteriores")])
        self.assertEqual(r["deficiencies"][0]["category"], "unmapped")
        self.assertEqual(r["inspections"][0]["derived_state"], "unfavorable_explicitly_pending")

    def test_iee_favorable(self):
        r = self.inspection(opinion="FAVORABLE", status="")
        self.assertEqual(r["inspections"][0]["derived_state"], "favorable")

    def test_archived_is_not_remediation(self):
        self.assertEqual(
            self.inspection(status="ARCHIVADO")["inspections"][0]["derived_state"],
            "archived_material_outcome_unknown",
        )

    def test_terminated_or_resolver_is_not_works_complete(self):
        for status in ["TERMINADO", "RESOLVER", "RESUELTO", "SUBSANACIÓN NO ACREDITADA"]:
            self.assertEqual(administrative_state("DESFAVORABLE", status), "unknown")

    def test_remediation_requires_explicit_affirmative_evidence(self):
        self.assertEqual(
            administrative_state("DESFAVORABLE", "", "DEFICIENCIAS SUBSANADAS"),
            "unfavorable_remediation_evidenced",
        )
        for literal in [
            "NO SUBSANADAS",
            "PENDIENTE DE ACREDITAR SUBSANACION",
            "NO CONSTA SUBSANACION ACREDITADA",
        ]:
            self.assertEqual(administrative_state("DESFAVORABLE", "", literal), "unknown")

    def test_negated_status_is_never_positive_evidence(self):
        for literal in [
            "NO PENDIENTE DE SUBSANACION",
            "NO CONSTA PENDIENTE DE SUBSANACION",
            "NO ARCHIVADO",
            "NO EN TRAMITACION",
        ]:
            self.assertEqual(administrative_state("DESFAVORABLE", literal), "unknown")

    def test_conflicting_state(self):
        self.assertEqual(
            administrative_state("FAVORABLE", "PENDIENTE DE SUBSANACIÓN"), "contradictory"
        )
        self.assertEqual(
            administrative_state(
                "DESFAVORABLE", "PENDIENTE DE SUBSANACIÓN", "SUBSANACION ACREDITADA"
            ),
            "contradictory",
        )

    def test_historical_order_and_coercive_fine(self):
        r = parse(
            fixture(
                [("Expediente", "999/2005/00001"), ("Fecha", "01/02/2005")], "Orden de ejecución"
            )
            + fixture(
                [
                    ("Expediente", "999/2024/00002"),
                    ("Fecha", "01/12/2024"),
                    ("Resolución", "Imposición de multa"),
                ],
                "Multa coercitiva",
            )
        )
        self.assertNotIn("inspections", r)
        self.assertEqual(
            [x["event_kind"] for x in r["events"]], ["execution_order", "coercive_fine"]
        )
        self.assertTrue(all(x["derived_state"] == "unknown" for x in r["events"]))

    def test_dates_retained_and_flagged(self):
        r = self.inspection(
            extra=[("Fecha de presentación", "01/01/2020"), ("Fecha del dictamen", "01/01/2027")]
        )
        row = r["inspections"][0]
        self.assertEqual(row["presentation_date"], "2020-01-01")
        self.assertIn("date_after_observation", row["quality_flags"])
        self.assertIn("requires_review", row["quality_flags"])

    def test_invalid_dates_not_repaired(self):
        row = self.inspection(extra=[("Fecha de presentación", "31/02/2020")])["inspections"][0]
        self.assertEqual(row["presentation_date"], "")
        self.assertIn("unparsed_date", row["quality_flags"])

    def test_antecedents(self):
        r = self.inspection(extra=[("Antecedentes", "999/2010/00002 y 999/2011/00003")])
        self.assertEqual(len(r["cases"]), 3)
        self.assertEqual(sum(x["relation"] == "antecedent" for x in r["relations"]), 2)

    def test_iso_latin_entities_and_hash(self):
        text = fixture(
            [
                ("Dirección", "CALLE SINTÉTICA &amp; PRUEBA, 1"),
                ("Expediente", "999/2020/00001"),
                ("Dictamen", "DESFAVORABLE"),
            ]
        )
        r = parse(text, "iso-8859-1")
        self.assertIn("SINTÉTICA & PRUEBA", r["accesses"][0]["address_raw"])
        self.assertEqual(r["source_records"][0]["encoding"], "iso-8859-1")
        self.assertEqual(
            r["source_records"][0]["source_sha256"],
            hashlib.sha256(text.encode("iso-8859-1")).hexdigest(),
        )

    def test_malformed_tags_and_empty_cells(self):
        r = parse(
            "<h2>ITE</h2><table><tr><td>Expediente<td>999/2020/00001<tr><td>Dictamen<td>FAVORABLE<tr><td>Alcance<td></table>"
        )
        self.assertEqual(r["inspections"][0]["opinion_raw"], "FAVORABLE")
        self.assertEqual(r["inspections"][0]["scope_raw"], "")

    def test_horizontal_repeated_headers_incomplete_row(self):
        header = "<tr><th>Expediente</th><th>Tipo</th><th>Dictamen</th></tr>"
        r = parse(
            "<table>"
            + header
            + "<tr><td>999/2020/00001</td><td>ITE</td><td>FAVORABLE</td></tr>"
            + header
            + "<tr><td>999/2021/00001</td><td>IEE</td></tr></table>"
        )
        self.assertEqual(len(r["inspections"]), 2)
        self.assertIn("incomplete_table_row", r["source_records"][0]["warnings"])

    def test_section_in_single_cell(self):
        r = parse(
            "<table><tr><td colspan='4'>ITE</td></tr><tr><td>Expediente</td><td>999/2020/00001</td></tr><tr><td>Dictamen</td><td>FAVORABLE</td></tr></table>"
        )
        self.assertEqual(r["inspections"][0]["inspection_type"], "ITE")

    def test_missing_sections_and_unknown_rows_preserved(self):
        r = parse("<table><tr><td>Dato futuro</td><td>valor</td></tr></table>")
        self.assertNotIn("inspections", r)
        self.assertIn("unrecognized_row", r["source_records"][0]["warnings"])
        self.assertEqual(r["source_records"][0]["rows"][0][1][1], "valor")

    def test_hidden_ndp_and_public_denied(self):
        r = parse(
            '<input name="ndp" value="99999999">'
            + fixture([("Expediente", "999/2020/00001"), ("Tipo", "ITE")])
        )
        self.assertEqual(r["accesses"][0]["ndp"], "99999999")
        self.assertFalse(r["inspections"][0]["public_exposure"])
        self.assertTrue(r["inspections"][0]["synthetic"])

    def test_no_exp_without_documentary_identity(self):
        r = parse(fixture([("Dictamen", "DESFAVORABLE")]))
        self.assertNotIn("inspections", r)


class ConservationRulesTests(unittest.TestCase):
    def bridge(self, rows):
        return pd.DataFrame(
            rows, columns=["ndp", "match_status", "parcel_ref14", "parcel_candidate"]
        )

    def cp(self, refs=("A",), usable=True):
        return pd.DataFrame(dict(parcel_ref14=refs, usable_geometry=usable, topology_valid=True))

    def test_multiple_accesses_one_parcel(self):
        b = self.bridge([("1", "confirmed", "A", "A"), ("2", "confirmed", "A", "A")])
        r = access_links(b, self.cp())
        self.assertEqual(r.confirmed_parcel_ref14.tolist(), ["A", "A"])
        self.assertFalse(r.physical_building_link.any())

    def test_one_access_multiple_candidates(self):
        b = self.bridge([("1", "multiparcel", "", "A"), ("1", "multiparcel", "", "B")])
        r = access_links(b, self.cp(("A", "B")))
        self.assertTrue(r.link_status.eq("ambiguous_access_parcel").all())
        self.assertEqual(set(r.parcel_candidate), {"A", "B"})

    def test_missing_cp_quarantine_and_duplicate_cp(self):
        b = self.bridge([("1", "confirmed", "A", "A")])
        for cp in [
            self.cp(("B",)),
            self.cp(usable=False),
            self.cp(("A", "A")),
            self.cp().assign(quarantined=True),
        ]:
            with self.subTest(cp=cp.to_dict()):
                r = access_links(b, cp)
                self.assertEqual(r.link_status.iloc[0], "ambiguous_access_parcel")
                self.assertEqual(r.confirmed_parcel_ref14.iloc[0], "")

    def test_unmatched_ambiguous_and_candidate(self):
        b = self.bridge(
            [("1", "unmatched", "", ""), ("2", "ambiguous", "", "A"), ("3", "candidate", "", "A")]
        )
        self.assertEqual(
            access_links(b, self.cp()).link_status.tolist(),
            ["unmatched_access", "ambiguous_access_parcel", "candidate_access_parcel"],
        )

    def test_conflicting_access_versions_not_promoted(self):
        b = self.bridge([("1", "confirmed", "A", "A"), ("1", "unmatched", "", "")])
        self.assertTrue(access_links(b, self.cp()).link_status.eq("ambiguous_access_parcel").all())

    def test_case_matching_does_not_use_parcel(self):
        rec = dict(case_reference="999/2020/00001", authority="Madrid", ndp="1", parcel_ref14="A")
        event = dict(original_id="999/2020/00001", authority="Madrid", ndp="1")
        self.assertEqual(relation_level(rec, event), "B_exact_case_and_access")
        self.assertEqual(relation_level(rec, dict(event, ndp="")), "A_exact_case")
        self.assertEqual(relation_level(rec, dict(event, ndp="2")), "D_contradiction")
        self.assertEqual(
            relation_level(rec, dict(event, original_id="3")), "C_possible_administrative_relation"
        )
        self.assertEqual(relation_level(rec, dict(original_id="3", parcel_ref14="A")), "unrelated")

    def test_ordinal_order_is_not_case(self):
        self.assertEqual(
            relation_level(
                dict(case_reference="1", authority="Madrid"),
                dict(original_id="1", authority="Madrid"),
            ),
            "unrelated",
        )

    def test_explainable_profile_rules(self):
        self.assertEqual(
            investigation_signal("unfavorable_remediation_evidenced", True), "resolved_evidence"
        )
        self.assertEqual(
            investigation_signal("unfavorable_explicitly_pending"), "pending_at_source_observation"
        )
        self.assertEqual(
            investigation_signal("unknown", True), "historical_evidence_current_state_unknown"
        )
        self.assertEqual(investigation_signal("contradictory"), "review_conflict")

    def test_obligation_is_not_unfavorable_inspection(self):
        e = pd.DataFrame(
            dict(event_type=["ite_pending", "order"], description=["", "ACTA DE ITE DESFAVORABLE"])
        )
        r = municipal_evidence(e)
        self.assertTrue(r.inspection_outcome.eq("unknown").all())
        self.assertEqual(r.indirect_unfavorable_mention.tolist(), [False, True])

    def test_profile_deduplicates_events_and_keeps_unknown(self):
        e = pd.DataFrame(
            dict(
                event_type=["order"] * 2,
                description=[""] * 2,
                event_id=["a"] * 2,
                match_status=["confirmed"] * 2,
                parcel_ref14=["A"] * 2,
                date=["2018-01"] * 2,
                query_date=[""] * 2,
            )
        )
        c = pd.DataFrame(
            dict(
                municipality_code=["28079"],
                parcel_ref14=["A"],
                certificate_count=[2],
                grant_case_count=[1],
            )
        )
        r = evidence_profiles(municipal_evidence(e), c).iloc[0]
        self.assertEqual(r.historical_order_count, 1)
        self.assertEqual(r.inspection_count, 0)
        self.assertEqual(r.certificate_count, 2)
        self.assertEqual(r.remediation_status, "unknown")
        self.assertEqual(r.latest_source_observation, "")


@unittest.skipUnless(
    (DEFAULT / "manifest.json").exists(), "Producto real de sesión 14 no disponible"
)
class RealConservationTests(unittest.TestCase):
    def test_ndp_exists_matches_and_missing(self):
        d = pd.read_parquet(DEFAULT / "conservation_accesses.parquet")
        r = d[d.COD_NDP.eq("11140360")].iloc[0]
        self.assertEqual(
            (r.VIA_NOMBRE_ACENTOS, r.NUMERO, r.DISTRITO, r.COD_VIA),
            ("EZEQUIEL PEÑALVER", "8", "21", "285300"),
        )
        self.assertEqual(r.UTMX_ETRS, "453035,95")
        self.assertTrue(d[d.COD_NDP.eq("NONEXISTENT")].empty)
        b = pd.read_parquet(
            DEFAULT / "conservation_parcel_links.parquet", filters=[("ndp", "==", "11140360")]
        )
        self.assertTrue(b.link_status.eq("unmatched_access").all())

    def test_all_products_hashes_and_previous_identifiers(self):
        m = json.loads((DEFAULT / "manifest.json").read_text())
        from madrid_rehab.ingest import digest

        for relative, expected in m["outputs"].items():
            self.assertEqual(digest(DEFAULT / relative), expected)
        self.assertEqual(m["counts"]["municipal_events_reused"], 124175)
        self.assertEqual(m["counts"]["execution_orders"], 3935)
        self.assertEqual(m["counts"]["real_inspections"], 0)
        self.assertEqual(m["counts"]["source_identity_duplicates"], 0)

    def test_public_mode_does_not_read_rec_or_profiles(self):
        from madrid_rehab.conservation_view import parcel_evidence, render_conservation_parcel

        with patch.dict(os.environ, MADRID_REHAB_PUBLIC="1"):
            with patch("madrid_rehab.conservation_view.read_verified") as reader:
                self.assertIsNone(parcel_evidence("8238105VK3783G"))
                render_conservation_parcel("8238105VK3783G")
                reader.assert_not_called()

    def test_region_no_ndp_reuse_and_no_cp(self):
        from madrid_rehab.conservation_view import parcel_evidence

        self.assertIsNone(parcel_evidence("8238105VK3783G", municipality="28065"))
        self.assertTrue(parcel_evidence("0000000ZZ0000Z").empty)

    def test_real_regional_and_energy_prtr_reconciliation(self):
        from madrid_rehab.conservation import ENERGY

        coverage = pd.read_parquet(DEFAULT / "conservation_regional_coverage.parquet")
        self.assertEqual(coverage.municipality_code.nunique(), 179)
        self.assertTrue(coverage.individual_inspection_coverage.eq("no_individual_coverage").all())
        profiles = pd.read_parquet(DEFAULT / "conservation_evidence_profile.parquet")
        historical = pd.read_parquet(ENERGY / "energy_grants_summary.parquet")
        common = profiles.merge(
            historical[historical.municipality_code.eq("28079")],
            on=["municipality_code", "parcel_ref14"],
            suffixes=("_new", "_old"),
        )
        self.assertTrue(common.certificate_count_new.eq(common.certificate_count_old).all())
        self.assertTrue(common.grant_case_count_new.eq(common.grant_case_count_old).all())
        cases = pd.read_parquet(DEFAULT / "conservation_grant_cases.parquet")
        self.assertTrue(cases.expediente_id.is_unique)
        self.assertNotIn("importe_centimos", profiles)
        self.assertTrue(profiles.inspection_count.eq(0).all())

    def test_real_21_districts_preserved(self):
        d = pd.read_parquet(
            DEFAULT / "conservation_events.parquet", columns=["district_code", "event_id"]
        )
        self.assertEqual(set(d.district_code) - {""}, {f"{x:02}" for x in range(1, 22)})
        self.assertEqual(d.event_id.nunique(), 124175)

    def test_cached_query_does_not_reread_parquet(self):
        from madrid_rehab.conservation_view import parcel_evidence, read_verified

        read_verified.clear()
        parcel_evidence("8238105VK3783G")
        with patch(
            "madrid_rehab.conservation_view.pd.read_parquet",
            side_effect=AssertionError("relectura"),
        ):
            parcel_evidence("8238105VK3783G")

    def test_apptest_real_conservation_filters(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_string(
            'from madrid_rehab.administrative_view import render_activity\nrender_activity("07")'
        ).run(timeout=30)
        self.assertFalse(app.exception)
        app.multiselect(key="admin_07conservation_event_type").set_value([]).run(timeout=30)
        self.assertFalse(app.exception)

    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError):
            build(DEFAULT)

    def test_real_apptest_parcel_and_empty(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_string(
            'from madrid_rehab.conservation_view import render_conservation_parcel\nimport streamlit as st\nref=st.text_input("Parcela", "8238105VK3783G")\nrender_conservation_parcel(ref)'
        )
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("No constan inspecciones" in i.value for i in app.info))
        app.text_input[0].set_value("0000000ZZ0000Z").run(timeout=30)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
