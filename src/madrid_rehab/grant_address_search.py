"""Partial address lookup over the authorized PRTR case literals in the public bundle."""

from collections import defaultdict
from functools import lru_cache
import json
import re

from . import address_search as postal, commercial_catalog_store as catalog
from . import production_bundle as bundle, public_prtr

NUMBERED = re.compile(r"([A-Z]+) (.+?) (\d+)")
ARTICLES = re.compile(r"^(.+?) (DE LA|DE LOS|DE LAS|DEL|DE|LA|LOS|LAS|EL)$")


@lru_cache(maxsize=5)
def _index(code, token):
    rows = bundle.read(
        public_prtr.PRODUCT,
        [("municipality_code", "==", code)],
        [
            "direccion",
            "parcel_ref14",
            "referencia_catastral",
            "referencias_adicionales",
            "match_status",
        ],
    )
    admitted = set(catalog.parcel_index(code).parcel_ref14)
    aliases = defaultdict(set)
    municipality = " " + postal.normalize(postal.NAMES[code]) + " (MADRID)"
    for row in rows.itertuples(index=False):
        if (
            row.match_status not in public_prtr.CONFIRMED
            or row.parcel_ref14 not in admitted
            or row.referencia_catastral != row.parcel_ref14
            or json.loads(row.referencias_adicionales) != [row.parcel_ref14]
        ):
            continue
        address = postal.normalize(row.direccion)
        if not address.endswith(municipality):
            continue
        match = NUMBERED.fullmatch(address.removesuffix(municipality))
        if not match:
            continue
        kind, street, number = match.groups()
        # Internal digits may be part of a street name or an address range.
        # Keep only the literals whose single house number is unambiguous.
        if any(char.isdigit() for char in street) or not street.replace(" ", "").isalpha():
            continue
        names = {street}
        article = ARTICLES.fullmatch(street)
        if article:
            names.add(f"{article[2]} {article[1]}")
        for name in names:
            for alias in {name, postal.street_key(f"{kind} {name}")}:
                aliases[alias].add((postal.number_key(number), row.parcel_ref14, row.direccion))
    result = {}
    for alias, matches in aliases.items():
        by_number = defaultdict(dict)
        for number, ref, original in sorted(matches):
            by_number[number].setdefault(ref, original)
        result[alias] = {
            number: next(iter(refs.items())) for number, refs in by_number.items() if len(refs) == 1
        }
    return result


def index(code):
    if code not in postal.NAMES or code == "28079" or not bundle.allowed_prtr():
        return {}
    return _index(code, bundle.signature())


def search(code, street, number="", complement="", *, offset=0):
    alias, num, extra = postal.parse_query(street, number, complement)
    numbers = index(code).get(alias, {}) if not extra else {}
    matches = sorted(
        ((ref, original) for value, (ref, original) in numbers.items() if not num or num == value),
        key=lambda row: (row[1], row[0]),
    )
    return [
        {"id": f"{ref}:{original}", "original": original, "reference": ref}
        for ref, original in matches[offset : offset + 100]
    ], len(matches)
