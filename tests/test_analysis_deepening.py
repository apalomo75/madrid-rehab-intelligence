"""Regresiones sintéticas de auditoría, perfiles, almacenamiento y extensión de eventos."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import test_sessions456 as fixtures
from madrid_rehab.analytics import exploratory_score, parcel_features
from madrid_rehab.analysis_audit import audit_analysis
from madrid_rehab.analysis_charts import (
    grade_distribution,
    construction_distribution,
    evidence_scatter,
)
from madrid_rehab.analysis_store import load_snapshot, snapshot_signature
from madrid_rehab.event_features import aggregate_event_features
from madrid_rehab.events import match_events, normalize_events, grant_summary
from madrid_rehab.ingest import digest
from madrid_rehab.profiles import (
    add_profiles,
    filter_parcels,
    group_comparison,
    csv_export,
    sensitivity_analysis,
    ENERGY_PROFILES,
)


class DeepAnalysisTests(unittest.TestCase):
    def setUp(self):
        case = fixtures.AnalyticsTests()
        case.setUp()
        self.cp, self.bu, self.cert, self.links = case.parcels, case.bu, case.cert, case.links
        self.features = case.result
        self.profile = add_profiles(self.features)

    def build(self):
        return parcel_features(self.cp, self.bu, self.cert, self.links)

    def test_conflicting_certificate_identity_rejected(self):
        self.cert = pd.concat([self.cert, self.cert.assign(cal_norenovglobal="A")])
        with self.assertRaisesRegex(ValueError, "contradictoria"):
            self.build()

    def test_identical_entity_republication_deduplicated(self):
        self.cert = pd.concat([self.cert, self.cert])
        self.bu = pd.concat([self.bu, self.bu])
        self.assertEqual(self.build().ceee_records_observed.sum(), 1)
        self.assertEqual(self.build().bu_count.sum(), 2)

    def test_conflicting_bu_identity_rejected(self):
        self.bu = pd.concat([self.bu, self.bu.assign(current_use="other")])
        with self.assertRaisesRegex(ValueError, "contradictoria"):
            self.build()

    def test_ambiguity_outside_pilot_not_hidden(self):
        self.cp = pd.concat([self.cp, self.cp.iloc[:1].assign(district_code="08")])
        result = self.build()
        self.assertEqual(result.iloc[0].cp_rows, 2)
        self.assertEqual(result.ceee_records_observed.sum(), 0)

    def test_missing_identity_rejected(self):
        self.cert.loc[0, "record_id"] = None
        with self.assertRaisesRegex(ValueError, "vacía"):
            self.build()

    def test_null_cp_reference_not_silently_dropped(self):
        self.cp.loc[0, "parcel_ref14"] = None
        with self.assertRaisesRegex(ValueError, "vacía"):
            self.build()

    def test_orphan_link_rejected(self):
        self.links.loc[0, "certificate_id"] = "does-not-exist"
        with self.assertRaisesRegex(ValueError, "inexistente"):
            self.build()

    def test_contradictory_link_states_rejected(self):
        self.links.loc[0, "parcel_status"] = "ambiguous"
        with self.assertRaisesRegex(ValueError, "contradictorios"):
            self.build()

    def test_missing_dates_counted_without_crash(self):
        self.cert.loc[0, "certificate_date"] = "invalid"
        result = self.build()
        self.assertTrue(result.ceee_first_date.isna().all())
        self.assertEqual(result.ceee_missing_date_count.sum(), 1)

    def test_dates_are_chronological(self):
        self.cert.loc[0, "certificate_date"] = "2026-1-2"
        self.cert = pd.concat(
            [self.cert, self.cert.assign(record_id="d", certificate_date="2026-01-10")]
        )
        self.links = pd.concat([self.links, self.links.iloc[:1].assign(certificate_id="d")])
        row = self.build().iloc[0]
        self.assertEqual(row.ceee_last_date.day, 10)
        self.assertEqual(row.ceee_first_date.day, 2)

    def test_inverted_construction_intervals_excluded(self):
        self.bu["construction_oldest_year"] = 2000
        self.bu["construction_newest_year"] = 1900
        result = self.build()
        self.assertTrue(result.construction_oldest_year.isna().all())
        self.assertEqual(result.construction_invalid_bu_count.sum(), 2)

    def test_out_of_range_and_fractional_years_excluded(self):
        self.bu["construction_oldest_year"] = [2027, 1920.5]
        self.assertTrue(self.build().construction_oldest_year.isna().all())

    def test_empty_universe_profiles_and_sensitivity(self):
        self.cp["district_code"] = "08"
        result = add_profiles(self.build())
        self.assertTrue(result.empty)
        summary = sensitivity_analysis(result, exploratory_score)
        self.assertEqual(summary.eligible_parcels.sum(), 0)
        self.assertTrue(summary.rank_correlation.isna().all())

    def test_administrative_code_reference_conflict_excluded(self):
        self.cert["edif_codreg"] = "code"
        self.cert["edif_refcat"] = "ref1"
        self.cert = pd.concat([self.cert, self.cert.assign(record_id="d", edif_refcat="ref2")])
        self.links = pd.concat([self.links, self.links.iloc[:1].assign(certificate_id="d")])
        self.assertEqual(self.build().ceee_records_observed.sum(), 0)

    def test_audit_detects_corrupted_denominator(self):
        bad = self.features.copy()
        bad.loc[0, "ceee_valid_grade_count"] = 100
        with self.assertRaisesRegex(ValueError, "Auditoría"):
            audit_analysis(self.cp, self.bu, self.cert, self.links, bad)

    def test_audit_reconciles_duplicate_links(self):
        report, _ = audit_analysis(self.cp, self.bu, self.cert, self.links, self.features)
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["source_rows"]["link_rows"], 2)
        self.assertEqual(report["source_rows"]["distinct_record_parcel_links"], 1)

    def test_combined_filters_and_empty_selection(self):
        result = filter_parcels(
            self.profile,
            "Con evidencia energética",
            periods=["Hasta 1940"],
            energy_profiles=[ENERGY_PROFILES[2]],
            residential_only=True,
            minimum_records=1,
        )
        self.assertEqual(len(result), 1)
        self.assertTrue(filter_parcels(self.profile, periods=[]).empty)
        self.assertTrue(filter_parcels(self.profile, query=".*").empty)

    def test_sort_has_stable_reference_tiebreaker_and_nulls_last(self):
        result = filter_parcels(self.profile, sort_by="ceee_efg_share_observed", ascending=False)
        self.assertEqual(result.iloc[0].parcel_ref14, fixtures.RC)
        self.assertTrue(pd.isna(result.iloc[-1].ceee_efg_share_observed))

    def test_invalid_filter_raises(self):
        with self.assertRaises(ValueError):
            filter_parcels(self.profile, sort_by="secret")
        with self.assertRaises(ValueError):
            filter_parcels(self.profile, minimum_records=-1)

    def test_small_groups_keep_denominators_but_hide_medians(self):
        result = group_comparison(self.profile)
        self.assertEqual(result.parcels.sum(), 2)
        self.assertTrue(result.median_parcel_efg_share.isna().all())
        self.assertFalse(result.comparison_eligible.any())

    def test_csv_formula_neutralized_without_changing_numeric_values(self):
        result = csv_export(
            pd.DataFrame(
                {"text": ["=SUM(A1)", " @cmd", "\t=evil", None], "amount": [-1, 0, 100, None]}
            )
        ).decode("utf-8-sig")
        self.assertIn("'=SUM(A1)", result)
        self.assertIn("' @cmd", result)
        self.assertIn("-1.0", result)

    def test_profile_is_not_need_diagnosis(self):
        self.assertEqual(self.profile.iloc[0].energy_profile, "Muestra escasa (1–2)")
        self.assertFalse(self.profile.global_ipr_eligible.any())
        self.assertEqual(add_profiles(self.features.iloc[:0]).shape[0], 0)

    def test_sensitivity_baseline_and_eligibility(self):
        data = self.features.copy()
        data.loc[0, "ceee_valid_grade_count"] = 5
        result = sensitivity_analysis(data, exploratory_score)
        baseline = result[(result.age_weight == 0.5) & (result.minimum_records == 3)].iloc[0]
        self.assertEqual(baseline.max_absolute_change, 0)
        self.assertEqual(result[result.minimum_records.eq(10)].eligible_parcels.sum(), 0)

    def test_chart_specs_and_no_duplicate_record_count(self):
        observations = pd.DataFrame(
            {
                "record_id": ["a", "a"],
                "cal_norenovglobal": ["F", "F"],
                "certificate_scope": ["dwelling", "dwelling"],
            }
        )
        chart = grade_distribution(observations).to_dict()
        rows = next(iter(chart["datasets"].values()))
        self.assertEqual(rows[0]["records"], 1)
        self.assertIn("params", chart)
        self.assertIn("encoding", construction_distribution(self.profile).to_dict())
        self.assertIn("params", evidence_scatter(self.profile).to_dict())

    def test_individual_explanation_preserves_unknowns(self):
        from madrid_rehab.profiles import explain_profile

        empty = self.profile[self.profile.parcel_ref14.eq("other")].iloc[0]
        explanation = explain_profile(empty)
        self.assertIn("desconocida", explanation["Evidencia energética"])
        self.assertIn("no confirma", explanation["Límite"])
        self.assertIn("no disponible", explanation["Contexto constructivo"])

    def test_pooled_and_parcel_median_have_different_denominators(self):
        # Cinco parcelas pequeñas EFG y una parcela con 100 letras A: ambos resúmenes difieren.
        frame = pd.concat([self.profile.iloc[:1]] * 6, ignore_index=True)
        frame["parcel_ref14"] = [f"p{i}" for i in range(6)]
        frame.loc[5, ["ceee_grade_F", "ceee_efg_share_observed"]] = 0
        frame.loc[5, "ceee_grade_A"] = 100
        frame.loc[5, "ceee_valid_grade_count"] = 100
        result = group_comparison(frame, minimum_parcels=1).iloc[0]
        self.assertEqual(result.median_parcel_efg_share, 1)
        self.assertAlmostEqual(result.pooled_efg_share, 5 / 105)

    def test_unknown_location_never_comparison_eligible(self):
        frame = pd.concat([self.profile.iloc[:1]] * 25, ignore_index=True)
        frame["parcel_ref14"] = [f"p{i}" for i in range(25)]
        frame["analysis_zone"] = None
        result = group_comparison(frame, "analysis_zone").iloc[0]
        self.assertFalse(result.comparison_eligible)
        self.assertTrue(pd.isna(result.pooled_efg_share))

    def test_grouped_records_deduplicate_multi_parcel_certificate(self):
        frame = pd.concat([self.profile.iloc[:1]] * 5, ignore_index=True)
        frame["parcel_ref14"] = [f"p{i}" for i in range(5)]
        observations = pd.DataFrame(
            {
                "parcel_ref14": frame.parcel_ref14,
                "record_id": ["c", "c", "a", "a", "a"],
                "cal_norenovglobal": ["F", "F", "A", "A", "A"],
            }
        )
        result = group_comparison(frame, minimum_parcels=1, observations=observations).iloc[0]
        self.assertEqual(result.pooled_grade_denominator, 2)
        self.assertEqual(result.pooled_efg_numerator, 1)
        self.assertEqual(result.pooled_efg_share, 0.5)
        self.assertEqual(result.pooled_unit, "unique_records_per_group")


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        case = fixtures.AnalyticsTests()
        case.setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        case.result.to_parquet(self.root / "parcel_features.parquet")
        (self.root / "coverage.json").write_text("{}")
        self.manifest = {
            "version": "session6-v1",
            "outputs": {
                name: digest(self.root / name)
                for name in ["parcel_features.parquet", "coverage.json"]
            },
        }
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))

    def test_v1_backwards_compatible(self):
        result = load_snapshot(self.root, snapshot_signature(self.root))
        self.assertEqual(len(result["parcel_features.parquet"]), 2)
        self.assertIn("energy_profile", result["parcel_features.parquet"])

    def test_changed_product_invalidates_signature_and_integrity(self):
        old = snapshot_signature(self.root)
        (self.root / "coverage.json").write_text('{"corrupted":true}')
        self.assertNotEqual(old, snapshot_signature(self.root))
        with self.assertRaises(ValueError):
            load_snapshot(self.root, snapshot_signature(self.root))

    def test_unknown_version_rejected(self):
        self.manifest["version"] = "future"
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))
        with self.assertRaises(ValueError):
            load_snapshot(self.root, snapshot_signature(self.root))

    def test_cache_prevents_repeated_parquet_reads(self):
        from madrid_rehab.analysis_view import cached_snapshot

        cached_snapshot.clear()
        with patch("madrid_rehab.analysis_store.pd.read_parquet", wraps=pd.read_parquet) as reader:
            a = cached_snapshot(str(self.root), snapshot_signature(self.root))
            a["parcel_features.parquet"].loc[0, "bu_count"] = 999
            b = cached_snapshot(str(self.root), snapshot_signature(self.root))
            self.assertEqual(reader.call_count, 1)
            self.assertNotEqual(b["parcel_features.parquet"].iloc[0].bu_count, 999)


class EventExtensionTests(unittest.TestCase):
    def setUp(self):
        case = fixtures.AnalyticsTests()
        case.setUp()
        self.features, self.cp = case.result, case.parcels

    def events(self, rows, kind):
        return match_events(normalize_events(pd.DataFrame(rows), kind), self.cp, kind)

    def test_absent_source_does_not_create_zeros(self):
        result = aggregate_event_features(self.features)
        self.assertNotIn("grant_awards_observed", result)
        self.assertTrue(result.grant_source_status.eq("not_integrated").all())

    def test_inspection_history_and_remediation_unknown(self):
        rows = [
            fixtures.event(inspection_date="2020-01-01", result_raw="DESFAVORABLE"),
            {
                **fixtures.event(inspection_date="2025-01-01", result_raw="FAVORABLE"),
                "event_id": "later",
            },
        ]
        result = aggregate_event_features(
            self.features, inspections=self.events(rows, "inspection")
        )
        row = result[result.parcel_ref14.eq(fixtures.RC)].iloc[0]
        self.assertEqual(row.inspection_records_observed, 2)
        self.assertEqual(row.inspection_last_historical_result, "favorable")
        self.assertTrue(pd.isna(row.inspection_remediation_documented))
        self.assertEqual(len(result), len(self.features))

    def test_same_date_conflicting_results_ambiguous(self):
        rows = [
            fixtures.event(inspection_date="2020-01-01", result_raw="DESFAVORABLE"),
            {
                **fixtures.event(inspection_date="2020-01-01", result_raw="FAVORABLE"),
                "event_id": "other",
            },
        ]
        result = aggregate_event_features(
            self.features, inspections=self.events(rows, "inspection")
        )
        self.assertIn("ambiguous_history", result.inspection_last_historical_result.tolist())

    def test_grant_phases_republications_and_unknown_amount(self):
        row = fixtures.event(
            phase="award",
            amount="100",
            program="P",
            case_id="X",
            currency="EUR",
            location_role="subsidized_property",
        )
        rows = [
            row,
            {**row, "event_id": "repeat"},
            {**row, "event_id": "payment", "phase": "payment"},
        ]
        result = aggregate_event_features(self.features, grants=self.events(rows, "grant"))
        self.assertEqual(result.grant_awards_observed.sum(), 1)
        self.assertEqual(result.grant_known_eur_awarded.sum(), 100)
        self.assertTrue(
            result.loc[result.parcel_ref14.eq("other"), "grant_known_eur_awarded"].isna().all()
        )

    def test_empty_reviewed_event_snapshot(self):
        events = self.events([], "inspection")
        result = aggregate_event_features(self.features, inspections=events)
        self.assertEqual(result.inspection_records_observed.sum(), 0)
        self.assertTrue(result.inspection_last_historical_result.isna().all())

    def test_infinite_amount_and_whitespace_evidence_rejected(self):
        for value in ["inf", "-inf", "NaN"]:
            with self.assertRaises(ValueError):
                normalize_events(pd.DataFrame([fixtures.event(amount=value)]), "grant")
        with self.assertRaises(ValueError):
            normalize_events(
                pd.DataFrame([fixtures.event(phase="executed", execution_evidence_url=" ")]),
                "grant",
            )

    def test_blank_case_not_counted_and_amount_literal_preserved(self):
        events = normalize_events(
            pd.DataFrame(
                [
                    fixtures.event(
                        phase="award", amount="100.00", case_id=" ", program="P", currency="EUR"
                    )
                ]
            ),
            "grant",
        )
        self.assertEqual(events.iloc[0].amount_raw, "100.00")
        self.assertEqual(grant_summary(events)["unique_consistent_awards"], 0)

    def test_invalid_provenance_rejected(self):
        for row in [
            {**fixtures.event(), "source_url": "javascript:alert(1)"},
            {**fixtures.event(), "extracted_at": "invalid"},
        ]:
            with self.assertRaises(ValueError):
                normalize_events(pd.DataFrame([row]), "inspection")


@unittest.skipUnless(
    Path("data/processed/session_6_v2/manifest.json").exists(), "Generar captura v2 real"
)
class AnalysisAppTests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest

        return AppTest.from_string(
            "from madrid_rehab.app import main\nmain()", default_timeout=60
        ).run()

    def test_combined_filters_sort_and_csv_presence(self):
        app = self.app()
        self.assertFalse(app.exception)
        next(w for w in app.selectbox if w.label == "Cobertura del perfil").set_value(
            "Con evidencia energética"
        ).run()
        next(w for w in app.multiselect if w.label == "Periodo constructivo").set_value(
            ["Hasta 1940"]
        ).run()
        next(
            w for w in app.number_input if w.label == "Mínimo de registros CEEE vinculados"
        ).set_value(5).run()
        next(w for w in app.selectbox if w.label == "Ordenar parcelas por").set_value(
            "Registros CEEE"
        ).run()
        next(w for w in app.checkbox if w.label == "Orden descendente").check().run()
        self.assertFalse(app.exception)
        table = next(d.value for d in app.dataframe if "energy_profile" in d.value)
        self.assertFalse(table.empty)
        self.assertTrue(table.construction_period.eq("Hasta 1940").all())
        self.assertTrue(table.ceee_records_observed.ge(5).all())
        self.assertTrue(table.ceee_records_observed.is_monotonic_decreasing)
        self.assertTrue(app.get("download_button"))
        next(w for w in app.selectbox if w.label == "Explicar una parcela").set_value(
            table.iloc[0].parcel_ref14
        ).run()
        self.assertFalse(app.exception)
        self.assertTrue(
            any("Localización en parcela; no confirma" in w.value for w in app.markdown)
        )

    def test_no_results_and_no_energy_states(self):
        app = self.app()
        next(w for w in app.selectbox if w.label == "Cobertura del perfil").set_value(
            "Sin evidencia energética"
        ).run()
        self.assertFalse(app.exception)
        table = next(d.value for d in app.dataframe if "energy_profile" in d.value)
        self.assertTrue(table.ceee_records_observed.eq(0).all())
        next(w for w in app.multiselect if w.label == "Periodo constructivo").set_value([]).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("No hay parcelas con esta combinación" in w.value for w in app.info))

    def test_zones_and_scope_filter(self):
        app = self.app()
        next(w for w in app.selectbox if w.label == "Comparar por").set_value("analysis_zone").run()
        zones = next(d.value for d in app.dataframe if "comparison_eligible" in d.value)
        self.assertEqual(zones.parcels.sum(), 3790)
        next(
            w for w in app.multiselect if w.label == "Ámbitos para los gráficos energéticos"
        ).set_value([]).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Sin registros energéticos" in w.value for w in app.info))


class ExtensionIntegrityTests(unittest.TestCase):
    def test_event_snapshot_cp_version_and_hashes(self):
        from madrid_rehab.event_features import load_event_snapshot

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pd.DataFrame({"event_id": ["x"]}).to_parquet(root / "events.parquet")
            metadata = {
                "kind": "inspection",
                "parcels_sha256": "cp",
                "rows": 1,
                "output_sha256": digest(root / "events.parquet"),
            }
            (root / "manifest.json").write_text(json.dumps(metadata))
            result, lineage = load_event_snapshot(root, "inspection", "cp")
            self.assertEqual(len(result), 1)
            self.assertIn("manifest_sha256", lineage)
            with self.assertRaises(ValueError):
                load_event_snapshot(root, "inspection", "different-cp")
            with self.assertRaises(ValueError):
                load_event_snapshot(root, "grant", "cp")
            pd.DataFrame({"event_id": ["tampered"]}).to_parquet(root / "events.parquet")
            with self.assertRaises(ValueError):
                load_event_snapshot(root, "inspection", "cp")

    def test_grant_cross_parcel_conflict_excluded_globally(self):
        case = fixtures.AnalyticsTests()
        case.setUp()
        row = fixtures.event(
            phase="award",
            amount="100",
            program="P",
            case_id="X",
            currency="EUR",
            location_role="subsidized_property",
        )
        events = normalize_events(
            pd.DataFrame([row, {**row, "event_id": "second", "reference_raw": "other"}]), "grant"
        )
        # Simula una revisión contradictoria: nunca se reparte el importe entre dos parcelas.
        events["parcel_ref14"] = [fixtures.RC, "other"]
        events["match_status"], events["match_level"] = "confirmed", "parcel"
        result = aggregate_event_features(case.result, grants=events)
        self.assertEqual(result.grant_awards_observed.sum(), 0)
        self.assertTrue(result.grant_known_eur_awarded.isna().all())

    def test_grant_resolution_conflict_not_selected_arbitrarily(self):
        row = fixtures.event(
            phase="award",
            amount="100",
            program="P",
            case_id="X",
            currency="EUR",
            resolution_date="2025-01-01",
        )
        rows = [row, {**row, "event_id": "another", "resolution_date": "2026-01-01"}]
        result = grant_summary(normalize_events(pd.DataFrame(rows), "grant"))
        self.assertEqual(result["unique_consistent_awards"], 0)

    def test_cli_analysis_with_optional_reviewed_events(self):
        import os
        import subprocess
        import sys

        case = fixtures.AnalyticsTests()
        case.setUp()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source"
            source.mkdir()
            names = [
                "parcels_audited",
                "buildings_audited",
                "certificates_integrated",
                "certificate_reference_links",
            ]
            outputs = {}
            for name, frame in zip(names, [case.parcels, case.bu, case.cert, case.links]):
                path = source / (name + ".parquet")
                frame.to_parquet(path)
                outputs[path.name] = {"sha256": digest(path)}
            (source / "quality_metrics.json").write_text(json.dumps({"outputs": outputs}))
            imports = root / "inspection"
            imports.mkdir()
            events = match_events(
                normalize_events(
                    pd.DataFrame(
                        [fixtures.event(inspection_date="2020-01-01", result_raw="DESFAVORABLE")]
                    ),
                    "inspection",
                ),
                case.parcels,
                "inspection",
            )
            path = imports / "events.parquet"
            events.to_parquet(path)
            metadata = {
                "kind": "inspection",
                "rows": 1,
                "parcels_sha256": outputs["parcels_audited.parquet"]["sha256"],
                "output_sha256": digest(path),
            }
            (imports / "manifest.json").write_text(json.dumps(metadata))
            target = root / "analysis"
            run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "madrid_rehab.analytics",
                    "--input-dir",
                    str(source),
                    "--output-dir",
                    str(target),
                    "--inspections-dir",
                    str(imports),
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            result = pd.read_parquet(target / "parcel_features.parquet")
            self.assertEqual(result.inspection_records_observed.sum(), 1)
            self.assertFalse(result.global_ipr_eligible.any())
            self.assertEqual(
                json.loads((target / "coverage.json").read_text())["inspection_available"], 1
            )
