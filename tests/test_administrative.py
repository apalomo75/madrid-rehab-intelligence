"""Fixtures artificiales; nunca se incorporan a productos reales."""

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from madrid_rehab.administrative import (
    address,
    build_bridge,
    classify,
    code,
    date_parts,
    deduplicate,
    lookup_bridge,
    match_all,
    number,
    order_events,
    pdf_events,
    urban_events,
)
from madrid_rehab.administrative_io import csv, inventory, xlsx
from madrid_rehab.profiles import csv_export


def bridge_inputs():
    ndp = pd.DataFrame(
        {
            "COD_NDP": ["001", "002"],
            "COD_VIA": ["10", "10"],
            "VIA_NOMBRE_ACENTOS": ["ÁRBOL", "ÁRBOL"],
            "VIA_CLASE": ["CALLE"] * 2,
            "NUMERO": ["1", "2"],
            "CALIFICADOR": ["", ""],
            "DISTRITO": ["1"] * 2,
            "UTMX_ETRS": ["440000", "440010"],
            "UTMY_ETRS": ["4470000"] * 2,
            "CLASE_APP": ["NUMERO"] * 2,
        }
    )
    legacy = pd.DataFrame(
        {
            "Codigo de numero": ["1", "2"],
            "Parcela catastral del numero": ["1234567VK4712A", "1234568VK4712A"],
            "Codigo de via": ["10", "10"],
        }
    )
    cp = pd.DataFrame(
        {
            "parcel_ref14": ["1234567VK4712A", "1234568VK4712A"],
            "district_code": ["01", "01"],
            "geometry_wkt": [
                "POLYGON ((439999 4469999,440001 4469999,440001 4470001,439999 4470001,439999 4469999))",
                "POLYGON ((440009 4469999,440011 4469999,440011 4470001,440009 4470001,440009 4469999))",
            ],
        }
    )
    return ndp, legacy, cp


class NormalizationTests(unittest.TestCase):
    def test_accent_abbreviation_and_qualifier(self):
        self.assertEqual(address("Árbol", "001 a", kind="CL"), address("ARBOL", "1", "A", "CALLE"))
        self.assertEqual(code("001.0"), "1")

    def test_incomplete_and_range_never_exact(self):
        self.assertEqual(address("Árbol", "1-3"), "")
        self.assertEqual(number("1517"), ("1517", ""))

    def test_explicit_crs_conversion(self):
        from madrid_rehab.administrative import convert_coordinates

        lon, lat = convert_coordinates(440000, 4470000)
        self.assertTrue(-4 < lon < -3)
        self.assertTrue(40 < lat < 41)
        x, y = convert_coordinates(lon, lat, "EPSG:4326", "EPSG:25830")
        self.assertAlmostEqual(x, 440000, places=4)
        self.assertAlmostEqual(y, 4470000, places=4)

    def test_date_invalid(self):
        self.assertEqual(
            date_parts({"X - Año": "2025", "X - Mes": "febrero", "X - Día": "30"}, "X"), ""
        )
        self.assertEqual(
            date_parts({"X - Año": "2024", "X - Mes": "febrero", "X - Día": "29"}, "X"),
            "2024-02-29",
        )

    def test_residential_is_not_rehabilitation(self):
        self.assertEqual(classify("Licencia urbanística residencial"), "no determinada")
        self.assertEqual(classify("Declaración Responsable - Actividad"), "actividad")
        self.assertEqual(classify("Rehabilitación"), "rehabilitación")

    def test_declaration_license_states_separate(self):
        d = pd.DataFrame([{"Nº_EXPEDIENTE": "a", "TIPO": "Residencial"}])
        self.assertNotEqual(
            urban_events(d, "license", "a")[0]["event_type"],
            urban_events(d, "declaration", "a")[0]["event_type"],
        )

    def test_orders_across_years_remain_events(self):
        f = pd.DataFrame(
            [
                {
                    "AÑO": y,
                    "NÚMERO DE ORDEN": "1",
                    "EMPLAZAMIENTO PRINCIPAL": "ÁRBOL, 1",
                    "MOTIVO": "ORDEN",
                }
                for y in ["2024", "2025"]
            ]
        )
        b = build_bridge(*bridge_inputs())
        e = match_all(pd.DataFrame(order_events(f, "s")).fillna(""), b)
        out, _ = deduplicate(e)
        self.assertEqual(len(out), 2)
        self.assertEqual(out.event_id.nunique(), 2)

    def test_order_ordinal_reuse_does_not_merge_actions(self):
        f = pd.DataFrame(
            [
                {
                    "AÑO": "2025",
                    "NUMERO DE ORDEN": "140",
                    "MES": m,
                    "EMPLAZAMIENTO PRINCIPAL": a,
                    "MOTIVO": "ORDEN",
                }
                for m, a in [("3", "ÁRBOL, 1"), ("4", "ÁRBOL, 2")]
            ]
        )
        out, _ = deduplicate(
            match_all(pd.DataFrame(order_events(f, "s")).fillna(""), build_bridge(*bridge_inputs()))
        )
        self.assertEqual(out.event_id.nunique(), 2)
        self.assertFalse(out.identity_conflict.any())

    def test_modern_order_number_header(self):
        f = pd.DataFrame(
            [
                {
                    "AÑO": "2025",
                    "NUMERO DE ORDEN": "1",
                    "TIPO DE VÍA": "CALLE",
                    "NOMBRE VÍA (EMPLAZAMIENTO PRINCIPAL)": "ÁRBOL",
                    "Nº DE VÍA": "1",
                }
            ]
        )
        out = match_all(
            pd.DataFrame(order_events(f, "s")).fillna(""), build_bridge(*bridge_inputs())
        )
        self.assertEqual(out.iloc[0].match_status, "confirmed")

    def test_ndp_contradictory_address(self):
        f = pd.DataFrame([{"Nº_EXPEDIENTE": "a", "NDP": "1", "DIRECCION": "ÁRBOL", "Nº": "2"}])
        out = match_all(
            pd.DataFrame(urban_events(f, "license", "s")).fillna(""), build_bridge(*bridge_inputs())
        )
        self.assertEqual(out.iloc[0].match_status, "contradictory")
        self.assertEqual(out.iloc[0].parcel_ref14, "")

    def test_xlsx_csv_publications_not_double_counted(self):
        f = pd.DataFrame([{"Nº_EXPEDIENTE": "a", "TIPO": "Residencial", "NDP": "1"}])
        rows = urban_events(f, "license", "a.csv") + urban_events(f, "license", "a.xlsx")
        out, pubs = deduplicate(
            match_all(pd.DataFrame(rows).fillna(""), build_bridge(*bridge_inputs()))
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(len(pubs), 2)

    def test_conflicting_case_excluded(self):
        f = pd.DataFrame([{"Nº_EXPEDIENTE": "a", "NDP": n} for n in ["1", "2"]])
        out, _ = deduplicate(
            match_all(
                pd.DataFrame(urban_events(f, "license", "s")).fillna(""),
                build_bridge(*bridge_inputs()),
            )
        )
        self.assertTrue(out.match_status.eq("contradictory").all())
        self.assertTrue(out.parcel_ref14.eq("").all())


class BridgeTests(unittest.TestCase):
    def test_official_ndp_unique(self):
        b = build_bridge(*bridge_inputs())
        self.assertTrue(b.match_status.eq("confirmed").all())
        self.assertEqual(lookup_bridge(b, "ndp")["1"][1], "1234567VK4712A")

    def test_multiple_references(self):
        n, legacy, c = bridge_inputs()
        legacy = pd.concat(
            [
                legacy,
                pd.DataFrame(
                    [dict(legacy.iloc[0], **{"Parcela catastral del numero": "1234568VK4712A"})]
                ),
            ]
        )
        b = build_bridge(n, legacy, c)
        self.assertTrue(b.loc[b.ndp.eq("1"), "match_status"].eq("multiparcel").all())
        self.assertNotEqual(lookup_bridge(b, "ndp")["1"][0], "confirmed")

    def test_duplicate_cp(self):
        n, legacy, c = bridge_inputs()
        b = build_bridge(n, legacy, pd.concat([c, c.iloc[[0]]]))
        self.assertEqual(b.iloc[0].match_status, "ambiguous")

    def test_district_contradiction(self):
        n, legacy, c = bridge_inputs()
        c.loc[0, "district_code"] = "07"
        b = build_bridge(n, legacy, c)
        self.assertEqual(b.iloc[0].match_status, "contradictory")

    def test_reference_absent_is_candidate(self):
        n, legacy, c = bridge_inputs()
        b = build_bridge(n, legacy, c.iloc[[1]])
        self.assertEqual(b.iloc[0].match_status, "candidate")

    def test_invalid_reference(self):
        n, legacy, c = bridge_inputs()
        legacy.loc[0, "Parcela catastral del numero"] = "invalid"
        self.assertEqual(build_bridge(n, legacy, c).iloc[0].match_status, "unmatched")

    def test_spatial_disagreement_not_reassigned(self):
        n, legacy, c = bridge_inputs()
        n.loc[0, "UTMX_ETRS"] = "450000"
        b = build_bridge(n, legacy, c)
        self.assertEqual(b.iloc[0].match_status, "contradictory")
        self.assertEqual(b.iloc[0].parcel_ref14, "")

    def test_duplicate_official_address_ambiguous(self):
        n, legacy, c = bridge_inputs()
        n.loc[1, "NUMERO"] = "1"
        b = build_bridge(n, legacy, c)
        self.assertNotEqual(lookup_bridge(b, "address_key")["CALLE|ARBOL|1|"][0], "confirmed")


class ParserTests(unittest.TestCase):
    def test_csv_encoding(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "s.csv"
            p.write_bytes("VÍA;Nº\nÁRBOL;1\n".encode("cp1252"))
            d, enc = csv(p)
            self.assertEqual(d.iloc[0, 0], "ÁRBOL")
            self.assertEqual(enc, "cp1252")

    def test_xlsx_sparse_cells_and_formula_not_evaluated(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "s.xlsx"
            with ZipFile(p, "w") as z:
                z.writestr(
                    "xl/worksheets/sheet1.xml",
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>A</t></is></c><c r="B1" t="inlineStr"><is><t>B</t></is></c></row><row r="2"><c r="B2"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>',
                )
            d = next(iter(xlsx(p).values()))
            self.assertEqual(d.iloc[0].tolist(), ["", "2"])

    def test_pdf_text_and_anomaly(self):
        text = "Edificios presentar I.T.E. en 2025\n\fTipo Vía       Nombre de la Vía     Nº     C. Postal Año Insp.              Parcial/Total\nCALLE          ABARZUZA             1517   28033     2015\nDatos a fecha 24/10/2026"
        rows, _ = pdf_events(text, "fixture.pdf")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["year"], "2025")
        self.assertEqual(rows[0]["query_date"], "2026-10-24")
        self.assertIn("extraordinary_number", rows[0]["quality_flags"])
        self.assertIn("inspection_year_differs", rows[0]["quality_flags"])

    def test_inventory_hash_and_unknown_license(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            (p / "input").mkdir()
            (p / "input" / "s.csv").write_text("A;B\n1;2\n")
            items = inventory(p / "input", p / "reports")
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["records"], 1)
            self.assertEqual(len(items[0]["sha256"]), 64)
            self.assertIsNone(items[0]["license_verified"])

    def test_export_formulas(self):
        out = csv_export(pd.DataFrame({"x": ["=1+1", "@SUM(A1)", "+cmd", "-cmd"]})).decode(
            "utf-8-sig"
        )
        self.assertIn("'=1+1", out)
        self.assertIn("'@SUM", out)

    def test_real_inventory_grant_is_call_only(self):
        from madrid_rehab.administrative import DEFAULT

        p = DEFAULT / "manifest.json"
        if not p.exists():
            self.skipTest("producto real no generado")
        m = json.loads(p.read_text())
        self.assertEqual(m["grant_status"], "only_call_document_no_awards")
        self.assertNotIn("grant", m["sources"])


class AdministrativeViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from madrid_rehab.administrative import DEFAULT

        cls.root = DEFAULT.resolve()
        if not (cls.root / "manifest.json").exists():
            raise unittest.SkipTest("Captura real no disponible")

    def test_partition_columns_and_hash_tamper(self):
        import shutil
        from madrid_rehab.administrative_view import read_partition, token

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "districts" / "07").mkdir(parents=True)
            shutil.copyfile(self.root / "manifest.json", root / "manifest.json")
            path = root / "districts" / "07" / "events.parquet"
            shutil.copyfile(self.root / "districts" / "07" / "events.parquet", path)
            frame = read_partition(root, "07", token(root, "07"))
            self.assertNotIn("raw_json", frame)
            self.assertTrue(frame.district_code.eq("07").all())
            path.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "alterada"):
                read_partition(root, "07", token(root, "07"))

    def test_filter_empty_and_parcel_selection(self):
        from madrid_rehab.administrative_view import (
            filter_events,
            parcel_events,
            read_partition,
            token,
        )

        frame = read_partition(self.root, "07", token(self.root, "07"))
        self.assertTrue(filter_events(frame, {"event_type": []}).empty)
        chosen = filter_events(frame, {"event_type": ["license"], "match_status": ["confirmed"]})
        self.assertTrue(chosen.event_type.eq("license").all())
        ref = chosen.iloc[0].parcel_ref14
        selected = parcel_events(ref, "07")
        self.assertTrue(selected.parcel_ref14.eq(ref).all())
        self.assertTrue(selected.match_status.eq("confirmed").all())
        self.assertTrue(parcel_events("missing", "07").empty)

    def test_cache_avoids_parquet_reread(self):
        from unittest.mock import patch
        from madrid_rehab.administrative_view import cached_partition, token

        cached_partition.clear()
        signature = token(self.root, "07")
        cached_partition(str(self.root), "07", signature)
        with patch(
            "madrid_rehab.administrative_view.pd.read_parquet",
            side_effect=AssertionError("relectura"),
        ):
            cached_partition(str(self.root), "07", signature)

    def test_real_app_filters_empty_export_and_map(self):
        from streamlit.testing.v1 import AppTest

        script = """
from madrid_rehab.administrative_view import render_activity
render_activity('07')
"""
        app = AppTest.from_string(script, default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Exportar eventos" in d.label for d in app.get("download_button")))
        app.multiselect(key="admin_07event_type").set_value([]).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("No hay eventos" in info.value for info in app.info))

    def test_all_confirmed_references_unique_cp(self):
        from madrid_rehab.administrative import DEFAULT

        events = pd.read_parquet(DEFAULT / "events.parquet")
        cp = pd.read_parquet(
            "data/processed/session_2/parcels_audited.parquet", columns=["parcel_ref14"]
        )
        counts = cp.groupby("parcel_ref14").size()
        self.assertTrue(
            events.loc[events.match_status.eq("confirmed"), "parcel_ref14"].map(counts).eq(1).all()
        )
        self.assertTrue(
            events.loc[~events.match_status.eq("confirmed"), "parcel_ref14"].eq("").all()
        )
        self.assertEqual(events.event_version_id.nunique(), len(events))


class AdministrativeProfileTests(unittest.TestCase):
    def test_real_profiles_preserve_denominators(self):
        path = Path(
            "data/processed/administrative_profiles/session_10_final_01/descriptive_profiles.parquet"
        )
        if not path.exists():
            self.skipTest("Perfil final no generado")
        profiles = pd.read_parquet(path)
        self.assertTrue(profiles.parcel_ref14.is_unique)
        selected = profiles[profiles.residential_before_1980_with_registered_order]
        self.assertTrue(selected.residential_bu_count.gt(0).all())
        self.assertTrue(selected.construction_oldest_year.lt(1980).all())
        self.assertTrue(selected.order_events_observed.gt(0).all())
        self.assertFalse(profiles.global_ipr_eligible.any())

    def test_input_manifest_integrity(self):
        from madrid_rehab.administrative import DEFAULT
        from madrid_rehab.ingest import digest

        if not (DEFAULT / "manifest.json").exists():
            self.skipTest("Captura final no generada")
        manifest = json.loads((DEFAULT / "manifest.json").read_text())
        self.assertEqual(manifest["input_manifest_sha256"], digest(DEFAULT / "input_manifest.json"))
        items = json.loads((DEFAULT / "input_manifest.json").read_text())
        self.assertEqual(len(items), 22)
        for item in items:
            self.assertEqual(digest(Path(item["raw_copy"])), item["sha256"])

    def test_real_event_map_constructs(self):
        from madrid_rehab.administrative import DEFAULT

        if not (DEFAULT / "manifest.json").exists():
            self.skipTest("Captura final no generada")
        from streamlit.testing.v1 import AppTest

        script = """
import pandas as pd
from madrid_rehab.administrative_view import render_activity
parcels = pd.read_parquet('data/processed/session_7_final/districts/07/map_parcels.parquet')
render_activity('07', parcels, parcels.iloc[0].map_zone)
"""
        app = AppTest.from_string(script, default_timeout=30).run()
        app.checkbox(key="admin_07map").check().run()
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
