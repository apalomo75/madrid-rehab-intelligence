"""PRTR release gating, confirmed selection and programme combinations."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd


from test_municipal_map_events import pick_first_parcel
from madrid_rehab import public_prtr as prtr, commercial_filters as filters
from madrid_rehab import production_bundle as bundle
from madrid_rehab.bundle_delivery import pack
from madrid_rehab.commercial_fiche import build_model, Quality
from madrid_rehab.ingest import digest
from madrid_rehab.i18n import MESSAGES


class PublicPrtrTests(unittest.TestCase):
    def rows(self):
        links = pd.DataFrame(
            {
                "expediente_id": ["one", "one", "two", "candidate", "conflict"],
                "parcel_ref14": ["a", "b", "a", "c", "d"],
                "municipality_code": ["28079"] * 5,
                "geographic_municipality_code": ["28079"] * 5,
                "match_status": [
                    "confirmed",
                    "confirmed",
                    "confirmed_historical_madrid",
                    "ambiguous",
                    "confirmed",
                ],
                "territorial_conflict": [False, False, False, False, True],
            }
        )
        grants = pd.DataFrame(
            {
                "expediente_id": ["one", "two", "candidate", "conflict"],
                "programa": ["P3", "P4", "P1", "P5"],
                "identity_conflict": [False] * 4,
                "importe_concedido": [100, 200, 300, 400],
                "direccion": ["documentary address"] * 4,
                "etapa_administrativa": ["source state"] * 4,
            }
        )
        return prtr.select(links, grants)

    def test_confirmed_only_and_amount_per_case(self):
        rows = self.rows()
        self.assertEqual(len(rows), 3)
        self.assertEqual(set(rows.expediente_id), {"one", "two"})
        model = build_model(
            "28079",
            "Madrid",
            "a",
            "cp",
            *[pd.DataFrame()] * 4,
            rows[rows.parcel_ref14.eq("a")],
            pd.DataFrame(),
        )
        self.assertEqual(len(model.grants), 2)
        self.assertTrue(all(e.quality == Quality.PARCEL for e in model.grants))
        self.assertEqual(sum(e.value["Concesión del expediente (€)"] for e in model.grants), 300)
        self.assertEqual(model.grants[0].value["Parcela vinculada"], "a")

    def test_programmes_or_and_and_reader(self):
        rows = self.rows()
        index = pd.DataFrame(
            {
                "parcel_ref14": ["a", "b", "c"],
                "energy": [False, True, True],
                "prtr": [True, True, False],
                "rehabilita": [False, False, True],
            }
        )
        with (
            patch.object(bundle, "active", return_value=True),
            patch.object(bundle, "allowed_prtr", return_value=True),
            patch.object(bundle, "allowed_plan", return_value=True),
            patch.object(bundle, "signature", return_value=("fixture",)),
            patch.object(
                bundle,
                "read",
                side_effect=lambda path, filters=None, columns=None: rows
                if columns is None
                else rows[columns],
            ),
        ):
            prtr._programme_refs.cache_clear()
            self.assertEqual(prtr.program_refs("28079", "P3"), {"a", "b"})
            self.assertEqual(prtr.program_refs("28079", "P4"), {"a"})
            self.assertEqual(prtr.program_refs("28079", "P5"), set())
            with (
                patch.object(filters.store, "parcel_index", return_value=index),
                patch.object(filters.store, "mode", return_value="public"),
                patch.object(filters, "inspection_refs", return_value=set()),
            ):
                self.assertEqual(
                    set(
                        filters.query(
                            "28079", ["prtr", "energy"], "OR", prtr_program="P4"
                        ).parcel_ref14
                    ),
                    {"a", "b", "c"},
                )
                self.assertEqual(
                    set(
                        filters.query(
                            "28079", ["prtr", "energy"], "AND", prtr_program="P3"
                        ).parcel_ref14
                    ),
                    {"b"},
                )
        prtr._programme_refs.cache_clear()
        with self.assertRaises(ValueError):
            prtr.program_refs("28079", "P2")

    def test_pending_blocks_runtime_and_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            meta = {
                "version": bundle.VERSION,
                "policy": {"prtr": True, "rehabilita": True},
                "release_status": "authorization_pending",
                "files": {},
            }
            (root / "manifest.json").write_text(json.dumps(meta))
            with patch.dict(os.environ, MADRID_REHAB_PUBLIC="1", MADRID_REHAB_BUNDLE_DIR=str(root)):
                with self.assertRaisesRegex(ValueError, "authorization"):
                    bundle.metadata()
            archive = root.parent / (root.name + ".tar.gz")
            with self.assertRaises(ValueError):
                pack(root, archive)
            self.assertFalse(archive.exists())

    def test_authorization_evidence_is_hash_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "proof.txt").write_text("Synthetic authorization fixture; not real permission")
            pd.DataFrame({"id": ["fixture"]}).to_parquet(root / "rows.parquet")
            meta = {
                "version": bundle.VERSION,
                "policy": {"prtr": True, "rehabilita": True},
                "release_status": "authorized",
                "prtr_authorization": {
                    "status": "verified",
                    "rights_holder": "TEST FIXTURE",
                    "dataset_sha256": prtr.ORIGINAL_SHA256,
                    "source_url": prtr.API_URL,
                    "decision_date": "2026-11-17",
                    "terms": "Synthetic test only",
                    "evidence_file": "proof.txt",
                    "scope": [
                        "derived_records",
                        "locations",
                        "amounts",
                        "cadastral_links",
                        "public_web",
                    ],
                    "attribution": "TEST FIXTURE",
                },
                "files": {
                    "proof.txt": {"sha256": digest(root / "proof.txt")},
                    prtr.PRODUCT: {"sha256": digest(root / "rows.parquet")},
                },
            }
            (root / "prtr").mkdir()
            (root / prtr.PRODUCT).write_bytes((root / "rows.parquet").read_bytes())
            (root / "manifest.json").write_text(json.dumps(meta))
            with patch.dict(os.environ, MADRID_REHAB_PUBLIC="1", MADRID_REHAB_BUNDLE_DIR=str(root)):
                self.assertTrue(bundle.allowed_prtr())
                (root / "proof.txt").write_text("tampered")
                with self.assertRaises(ValueError):
                    bundle.metadata()

    def test_public_runtime_reads_only_packaged_confirmed_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "prtr").mkdir()
            rows = self.rows()
            rows.to_parquet(root / prtr.PRODUCT, index=False)
            (root / "proof.txt").write_text("Synthetic permission for synthetic data only")
            meta = {
                "version": bundle.VERSION,
                "policy": {"prtr": True, "rehabilita": True},
                "release_status": "authorized",
                "prtr_authorization": {
                    "status": "verified",
                    "rights_holder": "TEST ONLY",
                    "dataset_sha256": prtr.ORIGINAL_SHA256,
                    "source_url": prtr.API_URL,
                    "decision_date": "2026-11-17",
                    "terms": "Fixture only",
                    "evidence_file": "proof.txt",
                    "attribution": "TEST ONLY",
                    "scope": [
                        "derived_records",
                        "locations",
                        "amounts",
                        "cadastral_links",
                        "public_web",
                    ],
                },
                "files": {
                    name: {"sha256": digest(root / name)} for name in ("proof.txt", prtr.PRODUCT)
                },
            }
            (root / "manifest.json").write_text(json.dumps(meta))
            with patch.dict(os.environ, MADRID_REHAB_PUBLIC="1", MADRID_REHAB_BUNDLE_DIR=str(root)):
                from madrid_rehab.commercial_data import grant_records

                self.assertEqual(prtr.program_refs("28079", "P4"), {"a"})
                self.assertEqual(prtr.program_refs("28005", "any"), set())
                self.assertEqual(set(grant_records("28079", "a").expediente_id), {"one", "two"})
                self.assertEqual(set(grant_records("28079", "b").expediente_id), {"one"})
                self.assertTrue(grant_records("28079", "c").empty)

    def test_translations_complete(self):
        for key in [
            "programme",
            "any",
            "P1",
            "P3",
            "P4",
            "P5",
            "state",
            "address",
            "parcel",
            "source",
        ]:
            self.assertEqual(set(MESSAGES["prtr." + key]), {"es", "en"})

    @unittest.skipUnless(prtr.LINKS.exists(), "Real immutable products unavailable")
    def test_real_confirmed_counts(self):
        rows = prtr.select(
            pd.read_parquet(prtr.LINKS / "grant_parcel_links.parquet"),
            pd.read_parquet(prtr.GRANTS / "grants.parquet"),
        )
        self.assertEqual(
            (len(rows), rows.expediente_id.nunique(), rows.parcel_ref14.nunique()),
            (5072, 5046, 4378),
        )
        self.assertEqual(
            rows.groupby("municipality_code").parcel_ref14.nunique().to_dict(),
            {"28079": 3300, "28005": 208, "28007": 244, "28065": 151, "28074": 198, "28092": 277},
        )


class PrtrInterfaceTests(unittest.TestCase):
    @unittest.skipUnless(prtr.LINKS.exists(), "Real immutable products unavailable")
    def test_local_programme_language_fiche_and_return(self):
        from streamlit.testing.v1 import AppTest

        with patch.dict(os.environ, {"MADRID_REHAB_PUBLIC": "0", "MADRID_REHAB_BUNDLE_DIR": ""}):
            app = AppTest.from_string(
                "from madrid_rehab.i18n import language_selector\nlanguage_selector()\n"
                "from madrid_rehab.commercial_catalog_view import render\nrender()",
                default_timeout=180,
            ).run()
            app.checkbox(key="priority_28079_prtr").check().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value, "3,300")
            app.selectbox(key="prtr_program_28079").set_value("P4").run()
            self.assertEqual(app.metric[0].value, "2,333")
            pick_first_parcel(app)
            self.assertFalse(app.exception)
            self.assertTrue(any("PRTR" in m.value for m in app.markdown))
            identity = app.session_state["fiche_identity"]
            app.radio(key="language_selector").set_value("EN").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key="prtr_program_28079").value, "P4")
            self.assertEqual(app.selectbox(key="prtr_program_28079").label, "Grant programme")
            self.assertEqual(app.session_state["fiche_identity"], identity)
            next(b for b in app.button if b.label == "Close property record").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value, "2,333")


class PrtrReleaseTests(unittest.TestCase):
    def test_authorize_requires_review_and_creates_new_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            (candidate / "prtr").mkdir(parents=True)
            (candidate / prtr.PRODUCT).write_text("synthetic fixture only")
            meta = {
                "version": bundle.VERSION,
                "policy": {"prtr": True, "rehabilita": True},
                "release_status": "authorization_pending",
                "files": {prtr.PRODUCT: {"sha256": digest(candidate / prtr.PRODUCT)}},
            }
            (candidate / "manifest.json").write_text(json.dumps(meta))
            document = root / "document.txt"
            document.write_text("SYNTHETIC AUTHORIZATION, TEST DATA ONLY")
            proof = {
                "status": "verified",
                "owner_reviewed": False,
                "document_sha256": digest(document),
                "rights_holder": "TEST FIXTURE",
                "dataset_sha256": prtr.ORIGINAL_SHA256,
                "source_url": prtr.API_URL,
                "decision_date": "2026-11-17",
                "terms": "Test only",
                "scope": [
                    "derived_records",
                    "locations",
                    "amounts",
                    "cadastral_links",
                    "public_web",
                ],
                "attribution": "TEST ONLY",
            }
            evidence = root / "proof.json"
            evidence.write_text(json.dumps(proof))
            with self.assertRaises(ValueError):
                prtr.authorize(candidate, root / "release", evidence, document)
            self.assertFalse((root / "release").exists())
            proof["owner_reviewed"] = True
            evidence.write_text(json.dumps(proof))
            prtr.authorize(candidate, root / "release", evidence, document)
            prtr.validate_release(json.loads((root / "release/manifest.json").read_text()))
            self.assertEqual(
                json.loads((candidate / "manifest.json").read_text())["release_status"],
                "authorization_pending",
            )
            with self.assertRaises(FileExistsError):
                prtr.authorize(candidate, root / "release", evidence, document)


class OwnerConfirmedPrtrTests(unittest.TestCase):
    def test_owner_communication_does_not_require_personal_document(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            (candidate / "prtr").mkdir(parents=True)
            pd.DataFrame({"id": ["fixture"]}).to_parquet(candidate / prtr.PRODUCT)
            (candidate / "personal.txt").write_text("DO NOT COPY")
            meta = {
                "version": bundle.VERSION,
                "release_status": "authorization_pending",
                "policy": {"prtr": True, "rehabilita": True},
                "files": {prtr.PRODUCT: {"sha256": digest(candidate / prtr.PRODUCT)}},
            }
            (candidate / "manifest.json").write_text(json.dumps(meta))
            output = root / "release"
            prtr.release_from_owner(candidate, output, "test-release", "2026-11-17")
            self.assertFalse((output / "personal.txt").exists())
            with patch.dict(
                os.environ, MADRID_REHAB_PUBLIC="1", MADRID_REHAB_BUNDLE_DIR=str(output)
            ):
                self.assertTrue(bundle.allowed_prtr())
                proof = bundle.metadata()["prtr_authorization"]
                self.assertEqual(proof["status"], "owner_confirmed")
                self.assertFalse(proof["documentary_verified"])
                self.assertNotIn("evidence_file", proof)
            with self.assertRaises(FileExistsError):
                prtr.release_from_owner(candidate, output, "test-release", "2026-11-17")
            meta = json.loads((output / "manifest.json").read_text())
            meta["prtr_authorization"]["documentary_verified"] = True
            with self.assertRaises(ValueError):
                prtr.validate_release(meta)
            (candidate / prtr.PRODUCT).write_text("tampered")
            with self.assertRaises(ValueError):
                prtr.release_from_owner(candidate, root / "bad", "test-release", "2026-11-17")
            self.assertFalse((root / "bad").exists())
