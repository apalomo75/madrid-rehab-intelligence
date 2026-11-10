"""Inspect existing pilot GML AD declarations without querying the URLs."""

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from madrid_rehab import address_search as a, enriched_cadastre as enriched
from madrid_rehab.ingest import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=a.REPORT / "raw_ad_audit.json")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    records = []
    for code in sorted(set(a.NAMES) - {"28079"}):
        manifest = enriched.metadata(code)
        raw = Path("data/raw/cadastre/session_12_2_capture_01") / code / "bu.zip"
        sha = digest(raw)
        if sha != manifest["inputs"][str(raw)]:
            raise ValueError("ZIP original incompatible: " + code)
        item = dict(
            municipality=code,
            raw_zip=str(raw),
            sha256=sha,
            members=[],
            address_declarations=0,
            declarations_with_href=0,
            declarations_with_text=0,
            declarations_with_children=0,
            embedded_address_features=0,
        )
        with zipfile.ZipFile(raw) as archive:
            for name in archive.namelist():
                if not name.lower().endswith(".gml"):
                    continue
                item["members"].append(name)
                with archive.open(name) as stream:
                    for _, element in ET.iterparse(stream, events=("end",)):
                        local = element.tag.rsplit("}", 1)[-1]
                        if local == "addresses":
                            item["address_declarations"] += 1
                            item["declarations_with_href"] += bool(
                                element.get("{http://www.w3.org/1999/xlink}href")
                            )
                            item["declarations_with_text"] += bool((element.text or "").strip())
                            item["declarations_with_children"] += bool(len(element))
                        if local == "Address":
                            item["embedded_address_features"] += 1
                        element.clear()
        records.append(item)
    a.write_json(
        args.output,
        dict(
            scope="All BU GML members, including source-only objects; not a postal census",
            network_requests=0,
            municipalities=records,
        ),
    )


if __name__ == "__main__":
    main()
