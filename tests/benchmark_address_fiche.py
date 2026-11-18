"""Measure complete server-side commercial fiche render with real sampled addresses.

AppTest measures Python/Streamlit execution, not browser painting or WebGL.
"""

import argparse
from pathlib import Path
import time

from streamlit.testing.v1 import AppTest

from madrid_rehab import address_search as a


def run_ms(call):
    start = time.perf_counter()
    app = call()
    duration = (time.perf_counter() - start) * 1000
    if app.exception:
        raise RuntimeError([e.value for e in app.exception])
    return app, duration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=a.REPORT / "fiche_render_benchmark.json")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    with a.connect() as db:
        count = db.execute("SELECT COUNT(*) FROM addresses WHERE status='confirmed'").fetchone()[0]
        samples = [
            dict(
                db.execute(
                    "SELECT * FROM addresses WHERE status='confirmed' ORDER BY id LIMIT 1 OFFSET ?",
                    (offset,),
                ).fetchone()
            )
            for offset in [0, count // 2, count - 1]
        ]
    app, initial_ms = run_ms(
        lambda: (
            AppTest.from_file("src/madrid_rehab/app.py", default_timeout=120)
            .run()
            .button(key="welcome_open_address")
            .click()
            .run()
        )
    )
    cases = []
    for row in samples:
        app.text_input(key="postal_street").set_value(row["kind"] + " " + row["street"])
        app.text_input(key="postal_number").set_value(row["number"])
        app.text_input(key="postal_complement").set_value(row["complement"])
        app, search_ms = run_ms(
            lambda: next(b for b in app.button if b.label == "Buscar").click().run()
        )
        app.selectbox(key="postal_result_choice").set_value(row["id"]).run()
        app, first_ms = run_ms(
            lambda: next(b for b in app.button if b.label == "Abrir ficha del inmueble")
            .click()
            .run()
        )
        identity = app.session_state["fiche_identity"]
        app, cached_ms = run_ms(app.run)
        cases.append(
            dict(
                address=row["original"],
                source_id=row["id"],
                identity=identity,
                search_rerun_ms=search_ms,
                first_complete_fiche_ms=first_ms,
                second_complete_fiche_ms=cached_ms,
                sections=[t.label for t in app.tabs],
            )
        )
        next(b for b in app.button if b.label == "Volver a los resultados").click().run()
    a.write_json(
        args.output,
        dict(
            validation="server_side_AppTest_not_visual",
            sampling="first_middle_last_confirmed_ID_no_evidence_filter",
            initial_app_ms=initial_ms,
            cases=cases,
        ),
    )


if __name__ == "__main__":
    main()
