"""Reproduce the three real demonstrations and verify historical product hashes."""

import argparse
import json
import resource
import time
from datetime import datetime, timezone
from pathlib import Path

from . import demo
from .ingest import digest


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    checked = {}
    roots = [
        demo.TERRITORY,
        demo.CADASTRE,
        demo.ENERGY,
        demo.CONSERVATION,
        Path("data/processed/session_7_final"),
        Path("data/processed/administrative_events/session_10_final_01"),
        Path("data/processed/grants/session_11_final_03"),
        Path("data/processed/grants/regional/session_12_1_final_02"),
    ]
    for root in roots:
        manifests = [
            root
            / (
                "grant_source_manifest.json"
                if root.name == "session_11_final_03"
                else "manifest.json"
            )
        ]
        if root.name == "session_7_final":
            manifests += sorted((root / "districts").glob("*/manifest.json"))
        for manifest in manifests:
            data = json.loads(manifest.read_text())
            checked[str(manifest)] = digest(manifest)
            for relative, expected in data.get("outputs", {}).items():
                if not isinstance(expected, str) or len(expected) != 64:
                    raise ValueError("Unexpected manifest output: " + str(manifest))
                path = manifest.parent / relative
                if digest(path) != expected:
                    raise ValueError("Historical output changed: " + str(path))
                checked[str(path)] = expected
    integrity_s = time.perf_counter() - started
    cases = []
    for title, (code, ref) in demo.CASES.items():
        start = time.perf_counter()
        cp = demo.parcel(code, ref)
        cert, events, accesses, joint = demo.evidence(code, ref)
        cold = time.perf_counter() - start
        start = time.perf_counter()
        demo.parcel(code, ref)
        demo.evidence(code, ref)
        warm = time.perf_counter() - start
        if len(cp) != 1 or cert.empty:
            raise ValueError("Demonstration case missing")
        start = time.perf_counter()
        document = demo.export_html(code, title, ref, cp)
        export_s = time.perf_counter() - start
        (output / f"{code}_{ref}.html").write_text(document)
        cases.append(
            {
                "title": title,
                "municipality_code": code,
                "parcel_ref14": ref,
                "certificate_count": len(cert),
                "energy": cert[
                    ["observation_date", "scope", "consumption_rating", "emissions_rating"]
                ].to_dict("records"),
                "conservation_events": int(events.is_conservation_evidence.sum())
                if not events.empty
                else 0,
                "administrative_events": len(events),
                "accesses": accesses[["ndp", "street", "number_raw", "link_status"]].to_dict(
                    "records"
                )
                if not accesses.empty
                else [],
                "grant_case_count": int(joint.grant_case_count.max()) if not joint.empty else 0,
                "real_rec_inspections": 0,
                "cold_query_s": cold,
                "warm_query_s": warm,
                "export_s": export_s,
                "physical_building_confirmed": False,
            }
        )
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "base_commit": "ebe1e36",
        "cases": cases,
        "integrity_products": len(checked),
        "integrity_seconds": integrity_s,
        "process_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "measurement": "Python selective reads and hashes; excludes Streamlit server, browser, WebGL and native interactive timing",
        "browser": "blocked_socket_and_chromium_permissions",
        "rec": "B_public_individual_documented_ndp_post_unverified",
        "public_export": "identification_only_no_restricted_evidence",
    }
    (output / "audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str)
    )
    (output / "historical_integrity.json").write_text(json.dumps(checked, indent=2))
    manifest = {
        "created_at": report["observed_at"],
        "inputs": {
            str(
                p
                / (
                    "grant_source_manifest.json"
                    if p.name == "session_11_final_03"
                    else "manifest.json"
                )
            ): digest(
                p
                / (
                    "grant_source_manifest.json"
                    if p.name == "session_11_final_03"
                    else "manifest.json"
                )
            )
            for p in roots
        },
        "outputs": {p.name: digest(p) for p in output.iterdir() if p.is_file()},
        "private_local_artifacts": True,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
