"""Measure Streamlit Python reruns; never claims real-browser timing."""

import argparse
import json
import os
import resource
import time
from pathlib import Path

from streamlit.testing.v1 import AppTest

from madrid_rehab.demo import CASES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    os.environ["MADRID_REHAB_DEMO"] = "1"
    os.environ["MADRID_REHAB_OFFLINE"] = "1"
    os.environ["MADRID_REHAB_PUBLIC"] = "0"
    start = time.perf_counter()
    app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=45).run()
    if app.exception:
        raise AssertionError(app.exception)
    result = {
        "measurement": "AppTest Python execution only; excludes server startup, browser rendering, WebGL and user perceived latency",
        "homepage_s": time.perf_counter() - start,
        "cases": [],
    }
    for title in CASES:
        start = time.perf_counter()
        app.selectbox[0].select(title).run()
        if app.exception:
            raise AssertionError(app.exception)
        result["cases"].append(
            {"case": title, "select_and_unified_fiche_s": time.perf_counter() - start}
        )
    result["peak_process_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    result["real_server_startup"] = "blocked_socket_permissions"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
