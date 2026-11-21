"""Public clean-install journeys. AppTest is not browser/WebGL validation."""

import argparse
import json
import os
from pathlib import Path
import resource
import time
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from test_municipal_map_events import pick_first_parcel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get("MADRID_REHAB_PUBLIC") == "1"
    rows = []
    start = time.perf_counter()

    def check(app, label):
        assert not app.exception, [(x.message, x.stack_trace) for x in app.exception]
        assert not app.error, [x.value for x in app.error]
        assert not any("consulta fallida" in x.value for x in app.warning), [
            x.value for x in app.warning
        ]
        rows.append(
            dict(
                check=label,
                seconds=time.perf_counter() - start,
                peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            )
        )

    with (
        patch(
            "madrid_rehab.commercial_data.grant_records", side_effect=AssertionError("PRTR read")
        ),
        patch(
            "madrid_rehab.plan_rehabilita_store.parcel_records",
            side_effect=AssertionError("Rehabilita read"),
        ),
    ):
        app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=180).run()
        app.button(key="welcome_open_explore").click().run()
        check(app, "startup")
        assert app.radio(key="language_selector").value == "ES"
        assert app.title[0].value == "Explorar inmuebles"
        assert app.metric[0].value == "114,706"
        assert app.checkbox(key="priority_28079_prtr").disabled
        assert app.checkbox(key="priority_28079_rehabilita").disabled
        assert not any(s.key == "technical_navigation" for s in app.selectbox)
        assert len(app.get("deck_gl_json_chart")) == 1
        assert not any(b.label == "Abrir ficha" for b in app.button)
        check(app, "ES count/list/map payload/restricted filters")
        app.radio(key="language_selector").set_value("EN").run()
        assert app.title[0].value == "Explore properties"
        check(app, "EN")
        app.radio(key="language_selector").set_value("ES").run()
        app.selectbox(key="catalog_district").set_value("07").run()
        app.checkbox(key="priority_28079_energy").check().run()
        check(app, "district and public energy filter")
        pick_first_parcel(app)
        assert app.session_state["fiche_identity"] is not None
        check(app, "Madrid fiche")
        for code in ["28065", "28092", "28074", "28007", "28005"]:
            app.selectbox(key="catalog_municipality").set_value(code).run()
            check(app, "municipality " + code)
            pick_first_parcel(app)
            assert app.session_state["fiche_identity"][0] == code
            check(app, "pilot fiche " + code)
        app.radio(key="city_navigation").set_value("Buscar por dirección").run()
        app.text_input(key="postal_street").set_value("CL BAILEN")
        app.text_input(key="postal_number").set_value("12")
        next(b for b in app.button if b.label == "Buscar").click().run()
        from madrid_rehab import commercial_catalog_store as store

        uid = store.search("28079", "CL BAILEN", "12")[0][0]["id"]
        app.selectbox(key="postal_result_choice").set_value(uid).run()
        next(b for b in app.button if b.label == "Abrir ficha del inmueble").click().run()
        assert app.session_state["fiche_identity"][0] == "28079"
        check(app, "postal search and fiche")
        app.radio(key="city_navigation").set_value("Acerca del proyecto").run()
        check(app, "about")
    result = dict(
        public=True,
        browser_visual_validation=False,
        checks=rows,
        restricted_fiche_retrieval_called=False,
        cwd=str(Path.cwd()),
        madrid_rehab_module=__import__("madrid_rehab").__file__,
    )
    with args.output.open("x") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
