"""Public PRTR release journey, real programme counts and isolated data reads."""

import argparse
import json
import os
from pathlib import Path
import resource
import sqlite3
from time import perf_counter
from unittest.mock import patch
from urllib.parse import unquote, urlparse

import pandas as pd
from streamlit.testing.v1 import AppTest


from test_municipal_map_events import pick_first_parcel
from madrid_rehab import production_bundle as bundle, public_prtr as prtr
from madrid_rehab import commercial_filters as filters


def run(output):
    if output.exists():
        raise FileExistsError("New report required")
    assert os.environ.get("MADRID_REHAB_PUBLIC") == "1"
    assert bundle.allowed_prtr()
    root = bundle.root()
    meta = bundle.metadata()
    rows = bundle.read(prtr.PRODUCT)
    assert (rows.expediente_id.nunique(), rows.parcel_ref14.nunique()) == (5046, 4378)
    accesses, stages, errors = set(), [], []
    original_read, original_connect = pd.read_parquet, sqlite3.connect
    from madrid_rehab.commercial_data import load_fiche as original_fiche

    def guard(path):
        raw = str(path)
        candidate = Path(unquote(urlparse(raw).path) if raw.startswith("file:") else raw).resolve()
        assert candidate.is_relative_to(root), raw
        accesses.add(str(candidate.relative_to(root)))

    def read(path, *args, **kwargs):
        guard(path)
        return original_read(path, *args, **kwargs)

    def connect(path, *args, **kwargs):
        guard(path)
        return original_connect(path, *args, **kwargs)

    def fiche(*args, **kwargs):
        result = original_fiche(*args, **kwargs)
        errors.extend(result[2].items())
        return result

    started = perf_counter()

    def record(stage, app):
        assert not app.exception, [e.message for e in app.exception]
        assert not app.error, [e.value for e in app.error]
        assert not errors, errors
        stages.append(
            dict(
                stage=stage,
                elapsed_seconds=perf_counter() - started,
                peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            )
        )

    combinations = 0
    with (
        patch("pandas.read_parquet", side_effect=read),
        patch("sqlite3.connect", side_effect=connect),
        patch("madrid_rehab.commercial_data.load_fiche", side_effect=fiche),
    ):
        for code in meta["counts"]:
            for program in prtr.PROGRAMS:
                expected_rows = rows[rows.municipality_code.eq(code)]
                if program != "any":
                    expected_rows = expected_rows[expected_rows.programa.eq(program)]
                expected = set(expected_rows.parcel_ref14)
                selected = filters.query(code, ["prtr"], prtr_program=program)
                assert set(selected.parcel_ref14) == expected, (code, program)
                for other in ("energy", "ite", "rehabilita"):
                    other_refs = set(filters.query(code, [other]).parcel_ref14)
                    for logic in ("AND", "OR"):
                        result = filters.query(code, ["prtr", other], logic, prtr_program=program)
                        assert set(result.parcel_ref14) == (
                            expected & other_refs if logic == "AND" else expected | other_refs
                        )
                        combinations += 1
        app = AppTest.from_string(
            "from madrid_rehab.i18n import language_selector\nlanguage_selector()\n"
            "from madrid_rehab.commercial_catalog_view import render\nrender()",
            default_timeout=180,
        ).run()
        record("public_initial", app)
        assert not app.checkbox(key="priority_28079_prtr").disabled
        app.checkbox(key="priority_28079_prtr").check().run()
        assert app.metric[0].value == "3,300"
        record("public_all_prtr", app)
        assert not any(box.key == "prtr_program_28079" for box in app.selectbox)
        # Parcel chosen through the real public filtered list, then read its complete evidence.
        pick_first_parcel(app)
        record("public_fiche", app)
        identity = app.session_state["fiche_identity"]
        assert identity is not None
        assert any("PRTR" in m.value for m in app.markdown)
        app.radio(key="language_selector").set_value("EN").run()
        record("public_fiche_en", app)
        assert app.session_state["fiche_identity"] == identity
        assert not any(box.key == "prtr_program_28079" for box in app.selectbox)
        next(b for b in app.button if b.label == "Close property record").click().run()
        record("public_return", app)
        assert app.metric[0].value == "3,300"
        app.radio(key="language_selector").set_value("ES").run()
        app.checkbox(key="priority_28079_rehabilita").check().run()
        app.radio(key="priority_logic_28079").set_value("AND").run()
        record("public_and_plan", app)
        app.radio(key="priority_logic_28079").set_value("OR").run()
        record("public_or_plan", app)
        next(b for b in app.button if b.label == "Limpiar filtros").click().run()
        record("public_reset", app)
        assert app.metric[0].value == "113,550"
        # Verify a genuine multi-case parcel is deduplicated per case in its public fiche.
        ref = (
            rows[rows.municipality_code.eq("28079")]
            .groupby("parcel_ref14")
            .expediente_id.nunique()
            .idxmax()
        )
        from madrid_rehab.commercial_data import grant_records

        actual = grant_records("28079", ref)
        assert len(actual) > 1 and not actual.expediente_id.duplicated().any()
    assert meta["policy"]["ite_iee_pdfs"] is False
    assert all("session_11_final_03" not in p for p in accesses)
    report = dict(
        passed=True,
        release_id=meta["release_id"],
        authorization=meta["prtr_authorization"]["status"],
        documentary_verified=meta["prtr_authorization"]["documentary_verified"],
        confirmed_cases=5046,
        confirmed_parcels=4378,
        combinations=combinations,
        stages=stages,
        accessed_files=sorted(accesses),
        fiche_errors=errors,
        multi_case_parcel=ref,
        multi_case_count=len(actual),
        cloud_memory_measured=False,
        webgl_validated=False,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in {"stages", "accessed_files"}}, indent=2
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
