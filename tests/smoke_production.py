"""Isolated production journeys, resource measurements and data access guard."""

import argparse
import json
import os
from pathlib import Path
import resource
import sqlite3
from time import perf_counter
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


from test_municipal_map_events import pick_first_parcel
from madrid_rehab import production_bundle as bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get("MADRID_REHAB_PUBLIC") == "1"
    assert bundle.active()
    rows, accesses = [], set()
    start = perf_counter()
    last = start
    root = bundle.root()
    parquet = pd.read_parquet
    sqlconnect = sqlite3.connect
    from madrid_rehab.commercial_data import load_fiche as original_fiche

    fiche_errors = []

    def guard(path):
        path = str(path)
        if path.startswith("file:"):
            from urllib.parse import unquote, urlparse

            path = unquote(urlparse(path).path)
        candidate = Path(path).resolve()
        assert candidate.is_relative_to(root), ("Data outside bundle", str(candidate))
        accesses.add(str(candidate.relative_to(root)))

    def read(path, *args, **kwargs):
        guard(path)
        return parquet(path, *args, **kwargs)

    def connect(path, *args, **kwargs):
        guard(path)
        return sqlconnect(path, *args, **kwargs)

    def load(*args, **kwargs):
        result = original_fiche(*args, **kwargs)
        fiche_errors.extend(result[2].items())
        return result

    def record(label, app=None):
        nonlocal last
        now = perf_counter()
        if app:
            assert not app.exception, [(e.message, e.stack_trace) for e in app.exception]
            assert not app.error, [e.value for e in app.error]
            assert not any("consulta fallida" in e.value for e in app.warning)
        assert not fiche_errors, fiche_errors
        rss = (
            int(
                next(
                    line.split()[1]
                    for line in Path("/proc/self/status").read_text().splitlines()
                    if line.startswith("VmRSS:")
                )
            )
            / 1024
        )
        rows.append(
            dict(
                stage=label,
                seconds=now - last,
                total_seconds=now - start,
                rss_mib=rss,
                peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            )
        )
        last = now

    with (
        patch("pandas.read_parquet", side_effect=read),
        patch("sqlite3.connect", side_effect=connect),
        patch("madrid_rehab.commercial_data.load_fiche", side_effect=load),
        patch(
            "madrid_rehab.commercial_data.grant_records",
            side_effect=AssertionError("Restricted PRTR"),
        ) as prtr,
    ):
        record("initial")
        app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=180).run()
        app.button(key="welcome_open_explore").click().run()
        record("startup_map", app)
        assert app.radio(key="language_selector").value == "ES"
        assert app.title[0].value == "Explorar inmuebles"
        assert len(app.selectbox(key="catalog_municipality").options) == 6
        assert len(app.selectbox(key="catalog_district").options) == 22
        assert app.metric[0].value == f"{bundle.metadata()['counts']['28079']:,}"
        assert app.checkbox(key="priority_28079_prtr").disabled
        assert not app.checkbox(key="priority_28079_rehabilita").disabled
        assert not any(x.key == "technical_navigation" for x in app.selectbox)
        assert not any(b.label == "Abrir ficha" for b in app.button)
        chart = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
        assert len(chart["layers"][0]["data"]["features"]) <= 500
        app.checkbox(key="priority_28079_rehabilita").check().run()
        assert app.metric[0].value == f"{bundle.metadata()['plan_confirmed_parcels']:,}"
        record("plan_filter", app)
        pick_first_parcel(app)
        assert app.session_state["fiche_identity"] is not None
        assert any("Subvención revisada" in e.value for e in app.markdown)
        record("plan_fiche", app)
        identity = app.session_state["fiche_identity"]
        app.radio(key="language_selector").set_value("EN").run()
        assert app.title[0].value == "Explore properties"
        assert app.session_state["fiche_identity"] == identity
        assert app.checkbox(key="priority_28079_rehabilita").value
        record("english", app)
        app.radio(key="language_selector").set_value("ES").run()
        next(b for b in app.button if b.label == "Cerrar ficha").click().run()
        assert app.checkbox(key="priority_28079_rehabilita").value
        record("return_preserves_filters", app)
        app.checkbox(key="priority_28079_energy").check().run()
        app.radio(key="priority_logic_28079").set_value("AND").run()
        record("AND", app)
        app.radio(key="priority_logic_28079").set_value("OR").run()
        record("OR", app)
        next(b for b in app.button if b.label == "Limpiar filtros").click().run()
        app.selectbox(key="catalog_district").set_value("07").run()
        record("district", app)
        app.checkbox(key="priority_28079_ite").check().run()
        record("ITE_order_mentions_only", app)
        app.checkbox(key="priority_28079_ite").uncheck().run()
        app.checkbox(key="priority_28079_energy").check().run()
        record("energy", app)
        for code in ["28065", "28092", "28074", "28007", "28005"]:
            app.selectbox(key="catalog_municipality").set_value(code).run()
            assert app.metric[0].value == f"{bundle.metadata()['counts'][code]:,}"
            pick_first_parcel(app)
            record("fiche_" + code, app)
        app.radio(key="city_navigation").set_value("Buscar por dirección").run()
        app.text_input(key="postal_street").set_value("CL BAILEN")
        app.text_input(key="postal_number").set_value("12")
        next(b for b in app.button if b.label == "Buscar").click().run()
        from madrid_rehab import commercial_catalog_store as store

        uid = store.search("28079", "CL BAILEN", "12")[0][0]["id"]
        app.selectbox(key="postal_result_choice").set_value(uid).run()
        next(b for b in app.button if b.label == "Abrir ficha del inmueble").click().run()
        record("postal_fiche", app)
        app.radio(key="city_navigation").set_value("Acerca del proyecto").run()
        record("about", app)
        prtr.assert_not_called()
    result = dict(
        checks=rows,
        data_reads=sorted(accesses),
        data_outside_bundle=False,
        fiche_errors=fiche_errors,
        prtr_calls=0,
        visual_validation=False,
        bundle=str(root),
        source=str(Path(__file__).resolve().parents[1]),
        package_bytes=sum(x.stat().st_size for x in root.rglob("*") if x.is_file()),
    )
    with args.output.open("x") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
