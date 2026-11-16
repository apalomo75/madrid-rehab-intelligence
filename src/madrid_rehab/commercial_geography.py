"""Reuse authenticated district assignments; never infer geography from proximity."""

from functools import lru_cache

from . import demo, commercial_catalog_store as store
from .data_recovery_audit import CITY
from .territory import parcel_territories


def district_names():
    rows = demo.read(CITY, "districts.parquet", columns=["district_code", "district_name"])
    return rows.sort_values("district_code").set_index("district_code").district_name.to_dict()


def district_index():
    store.metadata()
    return _district_index(store.signature(store.root_path()))


@lru_cache(maxsize=4)
def _district_index(token):
    rows = demo.read(
        demo.CITY, "parcels_audited.parquet", columns=["parcel_ref14", "district_code"]
    )
    return parcel_territories(rows)


def restrict(index, district):
    if district == "all":
        return index
    rows = district_index()
    refs = rows.loc[
        rows.district_assignment.eq("assigned") & rows.district_code.eq(district), "parcel_ref14"
    ]
    return index[index.parcel_ref14.isin(refs)].reset_index(drop=True)
