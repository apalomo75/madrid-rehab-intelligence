"""Recovery regressions: exact documentary identity and certificate scope."""

import unittest
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import pandas as pd

from madrid_rehab.commercial_fiche import build_model
from madrid_rehab.madrid_recovery import same_documentary_identity


class RecoveryTests(unittest.TestCase):
    def test_uncovered_source_is_not_zero_occurrence_rate(self):
        from madrid_rehab.data_recovery_audit import qualify_metric

        row = qualify_metric(
            dict(municipality_code="28065", field="conservation", numerator=0, coverage_percent=0)
        )
        self.assertIsNone(row["coverage_percent"])
        self.assertEqual(row["source_coverage"], "not_integrated")

    def test_documentary_mismatch_never_recovers(self):
        record = dict(
            building_id="BU",
            source_feature_type="Building",
            documentary_references=[dict(reference_state="explicit", cp_reference_original="CP")],
            external_references=["CP"],
        )
        old = dict(building_id="BU", parcel_ref14="CP")
        self.assertTrue(same_documentary_identity(record, old))
        for mutation in [
            dict(source_feature_type="BuildingPart"),
            dict(external_references=["OTHER"]),
            dict(documentary_references=[]),
            dict(building_id="OTHER"),
        ]:
            self.assertFalse(same_documentary_identity({**record, **mutation}, old))

    def test_quantities_reach_certificate_without_becoming_building_attributes(self):
        energy = pd.DataFrame(
            [
                dict(
                    certificate_id="one",
                    link_level="A",
                    identity_status="unique_registration_content",
                    date_after_capture=False,
                    consumption_rating="E",
                    emissions_rating="E",
                    scope="individual_unit",
                    observation_date="2025-01-01",
                    source_id="local",
                    consumption_value=123.5,
                    consumption_unit="unit_unverified",
                    emissions_value=25,
                    emissions_unit="unit_unverified",
                    area_value=72,
                    area_unit="unit_unverified",
                    consumption_status="observed",
                    emissions_status="observed",
                    area_status="observed",
                )
            ]
        )
        model = build_model(
            "28079",
            "Madrid",
            "CP",
            "cp",
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            energy,
            pd.DataFrame(),
            pd.DataFrame(),
        )
        self.assertEqual(model.energy[0].value["Consumo declarado"], 123.5)
        self.assertEqual(model.energy[0].value["Superficie certificada"], 72)
        self.assertEqual(model.energy[0].scope, "individual_unit")
        self.assertTrue(all(e.value is None for e in model.characteristics))
        energy.loc[0, "consumption_status"] = "suspect"
        suspect = build_model(
            "28079",
            "Madrid",
            "CP",
            "cp",
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            energy,
            pd.DataFrame(),
            pd.DataFrame(),
        )
        self.assertIsNone(suspect.energy[0].value["Consumo declarado"])


class RealRecoveryTests(unittest.TestCase):
    def test_incompatible_city_override_blocks_old_attributes(self):
        from madrid_rehab.madrid_recovery import DEFAULT, supplement

        if not DEFAULT.exists():
            self.skipTest("Session 22 derived local product absent")
        rows = pd.DataFrame(
            [dict(building_id="ES.SDGC.BU.9377401VK3797G", parcel_ref14="9377401VK3797G")]
        )
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "manifest.json").write_text(
                json.dumps(
                    {"inputs": {"buildings_audited": "changed", "parcels_audited": "changed"}}
                )
            )
            with patch.dict(os.environ, {"MADRID_REHAB_SESSION7_DIR": directory}):
                with self.assertRaisesRegex(ValueError, "active municipal"):
                    supplement(rows)

    def test_moncloa_surface_same_object_and_mismatch_blocked(self):
        from madrid_rehab.madrid_recovery import DEFAULT, supplement

        if not DEFAULT.exists():
            self.skipTest("Session 22 derived local product absent")
        rows = pd.DataFrame(
            [
                dict(
                    building_id="ES.SDGC.BU.9377401VK3797G",
                    parcel_ref14="9377401VK3797G",
                    dwellings_raw="14",
                )
            ]
        )
        recovered = supplement(rows)
        self.assertEqual(recovered.iloc[0].recovered_official_area, "5346")
        self.assertEqual(recovered.iloc[0].dwellings_raw, "14")
        self.assertEqual(len(recovered), 1)
        self.assertNotIn("recovered_floors_above", recovered)
        self.assertEqual(recovered.iloc[0].source_feature_type, "Building")
        rows.loc[0, "parcel_ref14"] = "8781605VK4788B"
        with self.assertRaisesRegex(ValueError, "CP mismatch"):
            supplement(rows)

    def test_america_does_not_acquire_another_building(self):
        from madrid_rehab.madrid_recovery import DEFAULT, supplement

        if not DEFAULT.exists():
            self.skipTest("Session 22 derived local product absent")
        rows = pd.DataFrame(
            [dict(building_id="ES.SDGC.BU.8781605VK4788B", parcel_ref14="8781605VK4788B")]
        )
        recovered = supplement(rows)
        self.assertTrue(recovered.recovered_official_area.isna().all())


if __name__ == "__main__":
    unittest.main()
