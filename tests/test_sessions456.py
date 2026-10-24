"""Fixtures sintéticos exclusivamente en memoria."""

import unittest
import tempfile
import subprocess
import os
from pathlib import Path
import sys

import pandas as pd

from madrid_rehab.analytics import coverage, exploratory_score, parcel_features
from madrid_rehab.analysis_view import filter_profile
from madrid_rehab.events import grant_summary, match_events, normalize_events

RC = "1234567AB1234C"


def event(**kwargs):
    return dict(
        event_id="i1",
        authority="test",
        source_url="https://example.org",
        extracted_at="2026-01-01",
        reference_raw=RC,
        **kwargs,
    )


class EventTests(unittest.TestCase):
    def test_original_and_unknown_result(self):
        result = normalize_events(pd.DataFrame([event(result_raw="OTRO")]), "inspection")
        self.assertEqual(result.iloc[0].result_raw, "OTRO")
        self.assertEqual(result.iloc[0].result_normalized, "unknown")
        self.assertIsNone(result.iloc[0].remediation_date)

    def test_historical_events_remain_separate(self):
        rows = [
            event(result_raw="DESFAVORABLE"),
            {**event(result_raw="FAVORABLE"), "event_id": "i2"},
        ]
        self.assertEqual(len(normalize_events(pd.DataFrame(rows), "inspection")), 2)

    def test_duplicate_and_conflict(self):
        row = event()
        self.assertEqual(len(normalize_events(pd.DataFrame([row, row]), "inspection")), 1)
        with self.assertRaises(ValueError):
            normalize_events(pd.DataFrame([row, {**row, "result_raw": "FAVORABLE"}]), "inspection")

    def test_missing_provenance(self):
        with self.assertRaises(ValueError):
            normalize_events(pd.DataFrame([{"event_id": "a"}]), "inspection")

    def test_confirmed_ambiguous_missing(self):
        data = normalize_events(pd.DataFrame([event()]), "inspection")
        for refs, expected in [([RC], "confirmed"), ([RC, RC], "ambiguous"), ([], "unmatched")]:
            result = match_events(data, pd.DataFrame({"parcel_ref14": refs}), "inspection")
            self.assertEqual(result.iloc[0].match_status, expected)

    def test_incomplete_address_is_only_candidate(self):
        row = {**event(address_raw="CALLE MAYOR"), "reference_raw": None}
        data = normalize_events(pd.DataFrame([row]), "inspection")
        result = match_events(data, pd.DataFrame({"parcel_ref14": [RC]}), "inspection")
        self.assertEqual(result.iloc[0].match_status, "candidate")

    def test_date_quality(self):
        data = normalize_events(pd.DataFrame([event(inspection_date="no-fecha")]), "inspection")
        self.assertTrue(data.iloc[0].inspection_date_invalid)
        self.assertEqual(data.iloc[0].inspection_date, "no-fecha")

    def test_beneficiary_address_cannot_match(self):
        data = normalize_events(
            pd.DataFrame([event(phase="award", amount="100", location_role="beneficiary")]), "grant"
        )
        result = match_events(data, pd.DataFrame({"parcel_ref14": [RC]}), "grant")
        self.assertEqual(result.iloc[0].location_level, "C")
        self.assertEqual(result.iloc[0].match_status, "unmatched")

    def test_grant_phases_and_privacy(self):
        rows = [
            event(phase="award", amount="100", beneficiary_name="PERSON"),
            {**event(phase="payment", amount="50"), "event_id": "p"},
        ]
        result = normalize_events(pd.DataFrame(rows), "grant")
        self.assertEqual(result.phase.tolist(), ["award", "payment"])
        self.assertNotIn("beneficiary_name", result)

    def test_execution_requires_evidence(self):
        with self.assertRaises(ValueError):
            normalize_events(pd.DataFrame([event(phase="executed")]), "grant")

    def test_invalid_amount(self):
        with self.assertRaises(ValueError):
            normalize_events(pd.DataFrame([event(amount="1.000,50")]), "grant")

    def test_grant_republications_not_summed(self):
        row = event(phase="award", amount="100", currency="EUR", program="P", case_id="X")
        rows = [
            row,
            {**row, "event_id": "other"},
            {**row, "event_id": "payment", "phase": "payment"},
        ]
        result = grant_summary(normalize_events(pd.DataFrame(rows), "grant"))
        self.assertEqual(result["unique_consistent_awards"], 1)
        self.assertEqual(result["known_eur_amount"], 100)

    def test_grant_conflicting_amounts_excluded(self):
        row = event(phase="award", amount="100", currency="EUR", program="P", case_id="X")
        rows = [row, {**row, "event_id": "other", "amount": "200"}]
        result = grant_summary(normalize_events(pd.DataFrame(rows), "grant"))
        self.assertEqual(result["conflicting_cases_excluded"], 1)
        self.assertIsNone(result["known_eur_amount"])


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.parcels = pd.DataFrame({"parcel_ref14": [RC, "other"], "district_code": ["07", "07"]})
        self.bu = pd.DataFrame(
            {
                "parcel_ref14": [RC, RC],
                "building_id": ["b1", "b2"],
                "construction_oldest_year": [1920, 1930],
                "construction_newest_year": [1940, 1950],
                "current_use": ["1_residential", "1_residential"],
            }
        )
        self.cert = pd.DataFrame(
            {
                "record_id": ["c"],
                "parcel_status": ["confirmed"],
                "cal_norenovglobal": ["F"],
                "certificate_date": ["2025-01-01"],
                "certificate_scope": ["dwelling"],
            }
        )
        self.links = pd.DataFrame(
            {
                "certificate_id": ["c", "c"],
                "parcel_ref14": [RC, RC],
                "parcel_status": ["confirmed", "confirmed"],
            }
        )
        self.result = parcel_features(self.parcels, self.bu, self.cert, self.links)

    def test_no_row_multiplication(self):
        self.assertEqual(len(self.result), 2)
        self.assertEqual(self.result.ceee_records_observed.sum(), 1)
        self.assertEqual(self.result.bu_count.sum(), 2)

    def test_missing_is_not_zero(self):
        row = self.result[self.result.parcel_ref14.eq("other")].iloc[0]
        self.assertTrue(pd.isna(row.ceee_efg_share_observed))
        self.assertFalse(row.global_ipr_eligible)
        self.assertEqual(coverage(self.result)["grant_available"], None)

    def test_score_eligibility(self):
        self.assertTrue(exploratory_score(self.result).isna().all())
        self.assertEqual(exploratory_score(self.result, minimum_records=1).notna().sum(), 1)

    def test_sensitivity(self):
        a = exploratory_score(self.result, 0, 1).iloc[0]
        b = exploratory_score(self.result, 1, 1).iloc[0]
        self.assertEqual(a, 100)
        self.assertEqual(b, 100)
        changed = self.result.copy()
        changed.loc[0, "construction_oldest_year"] = 2026
        self.assertEqual(exploratory_score(changed, 1, 1).iloc[0], 0)

    def test_invalid_weights(self):
        with self.assertRaises(ValueError):
            exploratory_score(self.result, 2)

    def test_unknown_grade_denominator(self):
        self.cert.loc[0, "cal_norenovglobal"] = None
        result = parcel_features(self.parcels, self.bu, self.cert, self.links)
        self.assertTrue(result.ceee_efg_share_observed.isna().all())

    def test_candidate_certificate_excluded(self):
        self.cert.loc[0, "parcel_status"] = "candidate"
        result = parcel_features(self.parcels, self.bu, self.cert, self.links)
        self.assertEqual(result.ceee_records_observed.sum(), 0)

    def test_filters(self):
        self.assertEqual(len(filter_profile(self.result, "Sin evidencia energética")), 1)
        self.assertEqual(len(filter_profile(self.result, query=RC)), 1)


class CLITests(unittest.TestCase):
    def test_canonical_inspection_and_grant_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parcels = root / "cp.parquet"
            pd.DataFrame({"parcel_ref14": [RC]}).to_parquet(parcels)
            for kind in ["inspection", "grant"]:
                source = root / (kind + ".csv")
                row = event()
                if kind == "grant":
                    row.update(
                        phase="award",
                        case_id="X",
                        program="P",
                        amount="100",
                        currency="EUR",
                        location_role="subsidized_property",
                    )
                pd.DataFrame([row]).to_csv(source, index=False)
                output = root / kind
                command = [
                    sys.executable,
                    "-m",
                    "madrid_rehab.events",
                    kind,
                    "--input",
                    str(source),
                    "--parcels",
                    str(parcels),
                    "--output-dir",
                    str(output),
                ]
                run = subprocess.run(
                    command,
                    env={**os.environ, "PYTHONPATH": "src"},
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                data = pd.read_parquet(output / "events.parquet")
                self.assertEqual(data.iloc[0].match_status, "confirmed")
                rerun = subprocess.run(
                    command,
                    env={**os.environ, "PYTHONPATH": "src"},
                    capture_output=True,
                    timeout=20,
                )
                self.assertNotEqual(rerun.returncode, 0)
