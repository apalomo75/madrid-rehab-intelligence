"""Deployment preflight regressions; no real datasets or authorization changes."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from madrid_rehab.deployment import preflight


class DeploymentTests(unittest.TestCase):
    def test_catalogue_query_closes_connection(self):
        from madrid_rehab.commercial_catalog_store import _parcel_index

        _parcel_index.cache_clear()
        with (
            patch("madrid_rehab.commercial_catalog_store.sqlite3.connect") as connect,
            patch("madrid_rehab.commercial_catalog_store.pd.read_sql_query"),
        ):
            _parcel_index("/tmp/catalogue-test", (), "28079", "public", (), None)
        connect.return_value.close.assert_called_once()
        _parcel_index.cache_clear()

    def test_public_technical_fiche_never_retrieves_prtr(self):
        from madrid_rehab.municipal_fiche import render_prtr

        with (
            patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "1"}),
            patch("madrid_rehab.municipal_fiche.st"),
            patch("madrid_rehab.commercial_data.grant_records") as grants,
        ):
            render_prtr("28079", "0010510VK4701A")
        grants.assert_not_called()

    def test_clean_checkout_is_explicitly_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            report = preflight(directory, Path("catalog"))
            self.assertFalse(report["catalogue_dependencies_present"])
            self.assertEqual(report["missing"], ["catalog/manifest.json"])
            self.assertFalse(report["publication_authorized"])

    def test_inputs_are_required_even_when_output_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "catalog").mkdir()
            (root / "catalog/db").write_bytes(b"db")
            (root / "catalog/manifest.json").write_text(
                json.dumps({"inputs": {"data/source": "hash"}, "outputs": {"db": "hash"}})
            )
            self.assertEqual(preflight(root, Path("catalog"))["missing"], ["data/source"])
            (root / "data").mkdir()
            (root / "data/source").write_bytes(b"source")
            report = preflight(root, Path("catalog"))
            self.assertTrue(report["catalogue_dependencies_present"])
            self.assertFalse(report["publication_authorized"])

    def test_nonportable_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "catalog").mkdir()
            for name in ["/mnt/c/private", "../private"]:
                (root / "catalog/manifest.json").write_text(
                    json.dumps({"inputs": {name: "hash"}, "outputs": {}})
                )
                with self.assertRaises(ValueError):
                    preflight(root, Path("catalog"))
