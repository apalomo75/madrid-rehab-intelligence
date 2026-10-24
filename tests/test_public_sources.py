"""Fixtures artificiales derivados de columnas públicas; nunca son datos analíticos."""

import io
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from madrid_rehab.official_sources import acquire, SOURCES
from madrid_rehab.public_events import (
    normalize_reviewed_events,
    normalize_urban_2019,
    URBAN_COLUMNS,
)
from madrid_rehab.events import match_events


class Response(io.BytesIO):
    status = 200

    def __init__(self, body, source="urban_2019", length=None, mime=None):
        super().__init__(body)
        self.source = source
        self.headers = {
            "Content-Length": str(len(body) if length is None else length),
            "Content-Type": mime or SOURCES[source]["mime"],
        }

    def geturl(self):
        return SOURCES[self.source]["url"]


class AcquisitionTests(unittest.TestCase):
    def test_complete_trace_and_idempotence(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []

            def opener(request, timeout):
                calls.append(request.full_url)
                return Response(b"No orden;Distrito\n1;Chamberi\n")

            first = acquire("urban_2019", folder, opener)
            self.assertTrue(first["complete"])
            self.assertEqual(len(first["sha256"]), 64)
            self.assertEqual(acquire("urban_2019", folder, opener), first)
            self.assertEqual(len(calls), 1)
            Path(folder, "urban_2019.csv").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                acquire("urban_2019", folder, opener)

    def test_incomplete_empty_html_and_mime_rejected(self):
        for body, length, mime in [
            (b"short", 100, None),
            (b"", 0, None),
            (b"<html>error</html>", None, None),
            (b"error", None, "text/html"),
        ]:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as folder:
                result = acquire(
                    "urban_2019", folder, lambda *a, **k: Response(body, length=length, mime=mime)
                )
                self.assertFalse(result["complete"])
                self.assertFalse(Path(folder, "urban_2019.csv").exists())
                self.assertFalse(Path(folder, "urban_2019.csv.json").exists())

    def test_truncated_xlsx_not_saved_as_original(self):
        with tempfile.TemporaryDirectory() as folder:
            result = acquire(
                "urban_2026", folder, lambda *a, **k: Response(b"PK-truncated", source="urban_2026")
            )
            self.assertFalse(result["complete"])
            self.assertFalse(Path(folder, "urban_2026.xlsx").exists())

    def test_error_trace_and_no_repeat(self):
        def blocked(*args, **kwargs):
            raise OSError("DNS blocked fixture")

        with tempfile.TemporaryDirectory() as folder:
            result = acquire("urban_2019", folder, blocked)
            self.assertEqual(result["error_type"], "OSError")
            self.assertIn("captured_at", result)
            with self.assertRaises(FileExistsError):
                acquire("urban_2019", folder, blocked)

    def test_schema_is_document_not_awards(self):
        body = json.dumps({"openapi": "3.0.0", "paths": {}}).encode()
        with tempfile.TemporaryDirectory() as folder:
            result = acquire(
                "bdns_schema", folder, lambda *a, **k: Response(body, source="bdns_schema")
            )
            self.assertTrue(result["complete"])
            self.assertNotIn("rows", result)


class PublicContractTests(unittest.TestCase):
    def urban(self):
        return pd.DataFrame(
            [
                dict(
                    zip(
                        URBAN_COLUMNS,
                        ["001", "CALLE", "FIXTURE", "Chamberí", "7", "FIXTURE", "2", "2019"],
                    )
                )
            ]
        )

    def canonical(self):
        return pd.DataFrame(
            [
                {
                    "event_id": "FIXTURE-1",
                    "authority": "FIXTURE",
                    "source_url": "https://datos.madrid.es/",
                    "extracted_at": "2026-10-23",
                    "inspection_type": "ITE",
                    "reference_raw": "1234567VK4713S",
                    "inspection_date": "invalid",
                    "phase": "award",
                    "amount": "123.45",
                    "location_role": "subsidized_property",
                    "beneficiary": "DO NOT EXPORT",
                }
            ]
        )

    def test_urban_is_only_district_no_geometry_or_property(self):
        frame = self.urban().assign(beneficiary="DO NOT EXPORT")
        result = normalize_urban_2019(frame, "fixture_capture")
        self.assertEqual(result.district_code.tolist(), ["07"])
        self.assertEqual(result.spatial_precision.tolist(), ["district"])
        self.assertTrue(result.parcel_ref14.isna().all())
        self.assertNotIn("beneficiary", result)
        self.assertNotIn("Calle", result)
        self.assertEqual(result.temporal_precision.tolist(), ["month"])

    def test_schema_changes_fail_explicitly(self):
        with self.assertRaises(ValueError):
            normalize_urban_2019(self.urban().drop(columns="Mes"), "fixture")

    def test_duplicate_rows_and_conflicting_ids(self):
        frame = self.urban()
        self.assertEqual(len(normalize_urban_2019(pd.concat([frame, frame]), "fixture")), 1)
        other = frame.copy()
        other["Mes"] = "3"
        with self.assertRaises(ValueError):
            normalize_urban_2019(pd.concat([frame, other]), "fixture")

    def test_invalid_dates_and_districts(self):
        for month in ["13", "1.5", "invalid", None]:
            result = normalize_urban_2019(self.urban().assign(Mes=month), "fixture")
            self.assertTrue(result.date_invalid.iloc[0])
            self.assertTrue(pd.isna(result.month.iloc[0]))
        result = normalize_urban_2019(self.urban().assign(**{"Codigo Distrito": "99"}), "fixture")
        self.assertEqual(result.spatial_precision.iloc[0], "unlocated")

    def test_empty_sources(self):
        result = normalize_urban_2019(pd.DataFrame(columns=URBAN_COLUMNS), "fixture")
        self.assertTrue(result.empty)
        for kind in ["ite_iee", "urban_inspection", "grant_call", "grant_award", "grant_phase"]:
            self.assertTrue(normalize_reviewed_events(pd.DataFrame(), kind, "fixture", "v1").empty)

    def test_compatible_canonical_and_optional_fields(self):
        result = normalize_reviewed_events(self.canonical(), "ite_iee", "fixture", "v1")
        self.assertNotIn("beneficiary", result)
        self.assertTrue(result.inspection_date_invalid.iloc[0])
        self.assertEqual(result.validation_status.iloc[0], "normalized_requires_review")
        self.assertEqual(result.capture_id.iloc[0], "fixture")
        parcels = pd.DataFrame({"parcel_ref14": ["1234567VK4713S"], "district_code": ["07"]})
        matched = match_events(result, parcels, "inspection")
        self.assertEqual(matched.match_status.iloc[0], "confirmed")
        self.assertEqual(matched.match_level.iloc[0], "parcel")

    def test_types_and_administrative_phases_separate(self):
        frame = self.canonical()
        with self.assertRaises(ValueError):
            normalize_reviewed_events(frame, "urban_inspection", "fixture", "v1")
        with self.assertRaises(ValueError):
            normalize_reviewed_events(frame, "grant_call", "fixture", "v1")
        with self.assertRaises(ValueError):
            normalize_reviewed_events(frame, "grant_phase", "fixture", "v1")
        award = normalize_reviewed_events(frame, "grant_award", "fixture", "v1")
        self.assertEqual(award.phase.iloc[0], "award")
        with self.assertRaises(ValueError):
            normalize_reviewed_events(frame.assign(amount="inf"), "grant_award", "fixture", "v1")
        with self.assertRaises(ValueError):
            normalize_reviewed_events(frame, "grant_award", "", "v1")


class EffectiveAuditTests(unittest.TestCase):
    @unittest.skipUnless(
        Path("data/processed/session_7_final/manifest.json").exists(), "Requiere datos reales"
    )
    def test_no_event_scenario_reproducible_and_unknown_coverage(self):
        from madrid_rehab.integration_audit import audit_existing_capture

        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / "first", Path(folder) / "second"
            a = audit_existing_capture("data/processed/session_7_final", first)
            b = audit_existing_capture("data/processed/session_7_final", second)
            self.assertEqual(a, b)
            self.assertEqual(a["new_verified_records_integrated"], 0)
            coverage = pd.read_parquet(first / "source_coverage_by_district.parquet")
            self.assertEqual(len(coverage), 21)
            self.assertTrue(coverage.ite_iee_records_observed.isna().all())
            self.assertEqual(int(coverage.parcels.sum()) + 38, 140595)
            self.assertEqual(
                (first / "source_coverage_by_district.parquet").read_bytes(),
                (second / "source_coverage_by_district.parquet").read_bytes(),
            )
            with self.assertRaises(FileExistsError):
                audit_existing_capture("data/processed/session_7_final", first)
