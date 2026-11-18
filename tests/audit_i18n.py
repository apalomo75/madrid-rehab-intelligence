"""Capture real public UI strings in both modes; no browser/network/data mutation."""

import argparse
import json
import os
from pathlib import Path
import re
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from madrid_rehab.i18n import MESSAGES


TYPES = (
    "title",
    "subheader",
    "markdown",
    "caption",
    "info",
    "warning",
    "error",
    "success",
    "button",
    "checkbox",
    "selectbox",
    "multiselect",
    "radio",
    "expander",
    "tabs",
    "text_input",
)


def capture(app):
    result = []
    for kind in TYPES:
        for item in getattr(app, kind):
            value = getattr(item, "label", getattr(item, "value", ""))
            result.append(dict(kind=kind, text=value))
            if hasattr(item, "options"):
                result.extend(dict(kind=kind + "_option", text=text) for text in item.options)
    return result


def leftovers(items):
    # Three-word authored Spanish phrases, excluding unchanged official names.
    phrases = {
        m["es"].strip()
        for m in MESSAGES.values()
        if m["es"] != m["en"]
        and len(m["es"].split()) >= 3
        and len(m["es"]) < 180
        and not m["es"].startswith(("{", "\n"))
    }
    result = set()
    for item in items:
        text = str(item["text"])
        if text.startswith("<style>"):
            continue
        if re.match(
            r"^(?:Área |Ficha |Página |Consulta |Información |Dirección |Sin registros)", text
        ):
            result.add(text)
        for phrase in phrases:
            if phrase in text and re.search(
                r"\b(?:de|del|la|las|los|sin|con|no|por|en|una|un|al|el|ni)\b",
                phrase,
                flags=re.IGNORECASE,
            ):
                result.add(text)
    return sorted(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = []
    for public in ["0", "1"]:
        with patch.dict(
            os.environ,
            {"MADRID_REHAB_PUBLIC": public, "MADRID_REHAB_DEV": "0", "MADRID_REHAB_DEMO": "0"},
        ):
            app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=180).run()
            app.button(key="welcome_open_explore").click().run()
            assert not app.exception
            app.radio(key="language_selector").set_value("EN").run()
            for evidence in ["energy", "ite", "rehabilita", "prtr"]:
                if app.checkbox(key="priority_28079_" + evidence).disabled:
                    continue
                app.checkbox(key="priority_28079_" + evidence).check().run()
                next(b for b in app.button if b.label == "View details").click().run()
                assert not app.exception
                items = capture(app)
                records.append(
                    dict(
                        public=public,
                        route="explore_fiche",
                        filter=evidence,
                        identity=app.session_state["fiche_identity"],
                        items=items,
                        leftovers=leftovers(items),
                    )
                )
                next(b for b in app.button if b.label == "Clear filters").click().run()
            app.selectbox(key="catalog_municipality").set_value("28065").run()
            next(b for b in app.button if b.label == "View details").click().run()
            assert not app.exception
            items = capture(app)
            records.append(
                dict(public=public, route="pilot_fiche", items=items, leftovers=leftovers(items))
            )
            for route in ["Buscar por dirección", "Acerca del proyecto"]:
                app.radio(key="city_navigation").set_value(route).run()
                assert not app.exception
                items = capture(app)
                records.append(
                    dict(public=public, route=route, items=items, leftovers=leftovers(items))
                )
    result = dict(
        visual_validation=False,
        records=records,
        untranslated_ui_strings=sorted({s for r in records for s in r["leftovers"]}),
    )
    (args.output_dir / "ui_strings.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )
    print(json.dumps(result["untranslated_ui_strings"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
