"""Parcel set semantics independent of certificate/case multiplicity."""

import unittest

import pandas as pd

from madrid_rehab.commercial_filters import combine, inspection_rows, context_key


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.index = pd.DataFrame(
            [
                dict(parcel_ref14="a", energy=True, prtr=True, rehabilita=False),
                dict(parcel_ref14="b", energy=True, prtr=False, rehabilita=True),
                dict(parcel_ref14="c", energy=False, prtr=False, rehabilita=False),
            ]
        )

    def test_combinations(self):
        self.assertEqual(len(combine(self.index)), 3)
        self.assertEqual(len(combine(self.index, ["energy"])), 2)
        self.assertEqual(len(combine(self.index, ["prtr", "rehabilita"])), 2)
        self.assertEqual(len(combine(self.index, ["prtr", "rehabilita"], "AND")), 0)
        self.assertEqual(len(combine(self.index, ["energy", "prtr"], "AND")), 1)
        self.assertEqual(len(combine(self.index, ["ite"], ite_refs=["c"])), 1)

    def test_public_restricted(self):
        self.assertTrue(combine(self.index, ["prtr"], public=True).empty)
        self.assertEqual(len(combine(self.index, ["energy", "prtr"], public=True)), 2)
        self.assertTrue(combine(self.index, ["energy", "prtr"], "AND", public=True).empty)

    def test_unique_and_context(self):
        self.assertEqual(len(combine(pd.concat([self.index, self.index]))), 3)
        self.assertEqual(
            context_key(["prtr", "energy"], "OR"), context_key(["energy", "prtr"], "OR")
        )
        with self.assertRaises(ValueError):
            combine(self.index, ["license"])

    def test_inspection_specificity(self):
        rows = pd.DataFrame(
            [
                dict(
                    event_type=kind,
                    description="ITE DESFAVORABLE",
                    indirect_unfavorable_mention=mention,
                    date="2020-01-01",
                    match_status=status,
                    identity_conflict=False,
                    is_conservation_evidence=True,
                    parcel_ref14=str(n),
                )
                for n, (kind, mention, status) in enumerate(
                    [
                        ("license", True, "confirmed"),
                        ("declaration", True, "confirmed"),
                        ("order", False, "confirmed"),
                        ("order", True, "confirmed"),
                        ("ite_pending", False, "confirmed"),
                        ("iee_pending", False, "candidate"),
                    ]
                )
            ]
        )
        self.assertEqual(set(inspection_rows(rows).parcel_ref14), {"3", "4"})

    def test_public_catalog_flag_does_not_authorize_grants(self):
        import os
        from unittest.mock import patch
        from madrid_rehab.commercial_data import load_fiche

        with (
            patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}),
            patch("madrid_rehab.commercial_data.grant_records") as grants,
            patch("madrid_rehab.plan_rehabilita_store.parcel_records") as municipal,
        ):
            model, tables, _, _ = load_fiche(
                "28065", "Getafe", "test", pd.DataFrame(), public_catalog=True
            )
        grants.assert_not_called()
        municipal.assert_not_called()
        self.assertFalse(model.grants or model.municipal_grants)
        self.assertTrue(tables["grants"].empty and tables["municipal_grants"].empty)
