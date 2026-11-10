"""Isolated six-request maximum probe of official nonprotected cadastral data.

No production reader imports this client. No requests in tests or app rendering.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET

BASE = (
    "https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/rest/Consulta_DNPRC"
)
SAMPLE = ("8781605VK4788B", "9377401VK3797G", "0000602VK4800A", "9540103VK3794B")
LIMIT = 524288


def parse_response(body, requested):
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise ValueError("Unsafe XML")
    root = ET.fromstring(body)
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    if any(e.tag.lower() in {"titular", "titulares", "nif", "valorcatastral"} for e in root.iter()):
        raise ValueError("Unexpected protected fields")
    errors = [
        dict(code=e.findtext("cod"), description=e.findtext("des")) for e in root.findall(".//err")
    ]
    properties = []
    for node in root.findall(".//rcdnp"):
        rc = node.find("rc")
        if rc is not None:
            identifier = "".join(rc.findtext(k, "") for k in ("pc1", "pc2", "car", "cc1", "cc2"))
            if not identifier.startswith(requested[:14]):
                raise ValueError("Unrelated cadastral identity")
            properties.append(identifier)
    bi = root.find(".//bico/bi")
    detail = None
    if bi is not None:
        rc = bi.find("idbi/rc")
        identifier = (
            "".join(rc.findtext(k, "") for k in ("pc1", "pc2", "car", "cc1", "cc2"))
            if rc is not None
            else ""
        )
        if not (
            (len(requested) == 20 and identifier == requested)
            or (len(requested) == 14 and len(identifier) == 20 and identifier.startswith(requested))
        ):
            raise ValueError("Detail is not the requested property")
        detail = dict(
            property_ref20=identifier,
            scope="individual_cadastral_property_not_BU",
            use=bi.findtext("debi/luso"),
            area=bi.findtext("debi/sfc"),
            declared_age=bi.findtext("debi/ant"),
            address=bi.findtext("ldt"),
            construction_units=[
                dict(
                    use=n.findtext("lcd"),
                    area=n.findtext("dfcons/stl"),
                    floor=n.findtext("dt/lourb/loint/pt"),
                )
                for n in root.findall(".//lcons/cons")
            ],
        )
    return dict(
        errors=errors,
        properties=properties,
        detail=detail,
        control={e.tag: e.text for e in root.findall("./control/*")},
    )


def probe(output, references=SAMPLE):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    if not 1 <= len(references) <= 4:
        raise ValueError("At most four input references")
    queue = list(references)
    events, details = [], 0
    for index in range(6):
        if not queue:
            break
        ref = queue.pop(0)
        if not re.fullmatch(r"[A-Z0-9]{14}|[A-Z0-9]{20}", ref):
            raise ValueError("Invalid reference")
        url = (
            BASE
            + "?"
            + urllib.parse.urlencode(dict(Provincia="MADRID", Municipio="MADRID", RefCat=ref))
        )
        event = dict(reference=ref, url=url, queried_at=datetime.now(timezone.utc).isoformat())
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "MadridRehabIntelligence/bounded-research"}
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                final = urllib.parse.urlsplit(response.geturl())
                if final.scheme != "https" or final.hostname != "ovc.catastro.meh.es":
                    raise ValueError("Unexpected redirect")
                body = response.read(LIMIT + 1)
                if len(body) > LIMIT:
                    raise ValueError("Response limit exceeded")
                parsed = parse_response(body, ref)
                name = ref + ".xml"
                (output / name).write_bytes(body)
                event.update(
                    http_status=response.status,
                    bytes=len(body),
                    sha256=hashlib.sha256(body).hexdigest(),
                    raw=name,
                    parsed=parsed,
                )
                if len(ref) == 14 and parsed["properties"] and details < 2:
                    # One documented unit per priority parcel; never enumerate the entire property list.
                    queue.append(sorted(set(parsed["properties"]))[0])
                    details += 1
        except Exception as exc:
            event.update(error=type(exc).__name__ + ": " + str(exc))
        events.append(event)
        time.sleep(1)
    (output / "manifest.json").write_text(
        json.dumps(
            dict(
                endpoint=BASE,
                max_requests=6,
                actual_requests=len(events),
                events=events,
                production_enabled=False,
                regional_coverage_claim=False,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    return events


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--references", nargs="+", choices=SAMPLE, default=SAMPLE)
    args = parser.parse_args()
    probe(args.output_dir, args.references)
