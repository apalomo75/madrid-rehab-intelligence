"""Public snapshot integrity, delivery and source restrictions."""

import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from madrid_rehab import production_bundle as bundle
from madrid_rehab.bundle_delivery import unpack, _download, pack
from madrid_rehab.ingest import digest


class ProductionBundleTests(unittest.TestCase):
    def test_pinned_delivery_and_cache_identity(self):
        class Response(io.BytesIO):
            def geturl(self):
                return "https://example.invalid/runtime.tar.gz"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            self.snapshot(source)
            archive = root / "runtime.tar.gz"
            checksum = pack(source, archive)
            target = root / "delivered"
            with patch("urllib.request.urlopen", return_value=Response(archive.read_bytes())):
                _download("https://example.invalid/runtime.tar.gz", checksum, str(target))
            self.assertEqual((target / ".delivery_sha256").read_text().strip(), checksum)
            self.assertEqual(digest(source / "rows.parquet"), digest(target / "rows.parquet"))
            with patch("urllib.request.urlopen") as fetch:
                with self.assertRaises(ValueError):
                    _download("https://example.invalid/other.tar.gz", "0" * 64, str(target))
                fetch.assert_not_called()

    def snapshot(self, root):
        pd.DataFrame({"id": ["one", "two"], "value": [1, 2]}).to_parquet(
            root / "rows.parquet", index=False
        )
        meta = {
            "version": bundle.VERSION,
            "policy": {"prtr": False, "rehabilita": True},
            "files": {"rows.parquet": {"sha256": digest(root / "rows.parquet")}},
        }
        (root / "manifest.json").write_text(json.dumps(meta))
        return meta

    def test_integrity_and_selective_read(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ, {"MADRID_REHAB_BUNDLE_DIR": directory, "MADRID_REHAB_PUBLIC": "1"}
            ),
        ):
            root = Path(directory)
            self.snapshot(root)
            self.assertEqual(
                bundle.read("rows.parquet", [("id", "==", "two")], ["value"]).value.tolist(), [2]
            )
            (root / "rows.parquet").write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                bundle.metadata()
        bundle._verify.cache_clear()

    def test_missing_file_never_falls_back(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ, {"MADRID_REHAB_BUNDLE_DIR": directory, "MADRID_REHAB_PUBLIC": "1"}
            ),
        ):
            root = Path(directory)
            self.snapshot(root)
            (root / "rows.parquet").unlink()
            with self.assertRaises(FileNotFoundError):
                bundle.metadata()

    def test_explicit_public_and_policy_required(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ, {"MADRID_REHAB_BUNDLE_DIR": directory, "MADRID_REHAB_PUBLIC": "0"}
            ),
        ):
            root = Path(directory)
            meta = self.snapshot(root)
            with self.assertRaises(ValueError):
                bundle.metadata()
            os.environ["MADRID_REHAB_PUBLIC"] = "1"
            meta["policy"]["prtr"] = True
            (root / "manifest.json").write_text(json.dumps(meta))
            with self.assertRaises(ValueError):
                bundle.metadata()

    def test_unknown_file_and_parent_paths_rejected(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ, {"MADRID_REHAB_BUNDLE_DIR": directory, "MADRID_REHAB_PUBLIC": "1"}
            ),
        ):
            root = Path(directory)
            self.snapshot(root)
            with self.assertRaises(FileNotFoundError):
                bundle.read("unlisted.parquet")
            with self.assertRaises(ValueError):
                bundle.key("../outside")

    def test_archive_rejects_traversal_and_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, name in enumerate(("../escape", "/absolute", "link")):
                archive = root / f"{index}.tar"
                with tarfile.open(archive, "w") as out:
                    item = tarfile.TarInfo(name)
                    if name == "link":
                        item.type = tarfile.SYMTYPE
                        item.linkname = "../outside"
                    out.addfile(item, io.BytesIO())
                with self.assertRaises(ValueError):
                    unpack(archive, root / f"target{index}")
                self.assertFalse((root / f"target{index}").exists())

    def test_delivery_requires_https_and_checksum_without_network(self):
        with patch("urllib.request.urlopen") as fetch:
            with self.assertRaises(ValueError):
                _download("http://example.invalid/data", "a" * 64, "/tmp/not-used")
            with self.assertRaises(ValueError):
                _download("https://example.invalid/data", "bad", "/tmp/not-used")
            fetch.assert_not_called()

    def test_plan_permission_does_not_open_prtr(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ, {"MADRID_REHAB_BUNDLE_DIR": directory, "MADRID_REHAB_PUBLIC": "1"}
            ),
        ):
            self.snapshot(Path(directory))
            from madrid_rehab.commercial_filters import restricted

            self.assertEqual(restricted(), {"prtr"})
            from madrid_rehab.municipal_fiche import render_prtr

            with (
                patch("madrid_rehab.municipal_fiche.st"),
                patch("madrid_rehab.commercial_data.grant_records") as query,
            ):
                render_prtr("28079", "0010510VK4701A")
            query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
