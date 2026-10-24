"""Mediciones reales locales; AppTest no equivale a navegador ni ingesta regional."""

import argparse
import json
import resource
import tempfile
import time
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from madrid_rehab.regional_cadastre import DEFAULT
from madrid_rehab.regional_grants import DEFAULT as GRANTS
from madrid_rehab.regional_view import load_decisions, load_inventory, token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Usar informe nuevo")
    report = {}

    def measure(name, fn):
        started = time.perf_counter()
        result = fn()
        report[name] = time.perf_counter() - started
        return result

    load_inventory.clear()
    load_decisions.clear()
    measure("inventory_cold_seconds", lambda: load_inventory(str(DEFAULT), token(DEFAULT)))
    measure("inventory_cached_seconds", lambda: load_inventory(str(DEFAULT), token(DEFAULT)))
    measure("prtr_decisions_cold_seconds", lambda: load_decisions(str(GRANTS), token(GRANTS)))
    with tempfile.TemporaryDirectory() as temp:
        app_path = Path(temp) / "app.py"
        app_path.write_text(
            "from madrid_rehab.regional_view import render_regional\nrender_regional()"
        )
        app = measure(
            "regional_apptest_initial_seconds",
            lambda: AppTest.from_file(str(app_path), default_timeout=60).run(),
        )
        if app.exception:
            raise RuntimeError(str(app.exception))
        for code in ["28065", "28900", "28092"]:
            measure(f"select_{code}_seconds", lambda: app.selectbox[0].set_value(code).run())
            if app.exception:
                raise RuntimeError(str(app.exception))
    report["regional_apptest_peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    cp_path = Path("data/processed/session_2/parcels_audited.parquet")
    bu_path = Path("data/processed/session_1/edificios_madrid.parquet")
    cp = measure("madrid_cp_full_read_seconds", lambda: pd.read_parquet(cp_path))
    report["madrid_cp_rows"] = len(cp)
    ref = cp.parcel_ref14.iloc[0]
    measure(
        "madrid_parcel_filtered_read_seconds",
        lambda: pd.read_parquet(cp_path, filters=[("parcel_ref14", "==", ref)]),
    )
    del cp
    if bu_path.exists():
        bu = measure("madrid_bu_full_read_seconds", lambda: pd.read_parquet(bu_path))
        report["madrid_bu_objects"] = len(bu)
        del bu
    report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report["regional_cp_bu_ingestion_benchmark"] = "blocked_network_no_real_pilot"
    report["visual_validation"] = "AppTest_only_not_browser"
    report["product_bytes"] = {
        str(p): p.stat().st_size
        for base in [DEFAULT, GRANTS]
        for p in base.glob("*")
        if p.is_file()
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
