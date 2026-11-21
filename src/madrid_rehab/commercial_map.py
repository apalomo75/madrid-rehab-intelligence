"""Commercial cadastral polygons and camera, without geocoding or simplification."""

import math

import pydeck as pdk
import shapely as sh
from pyproj import Transformer

from . import demo
from .i18n import t, ui as st
from .municipal_navigation import object_source

PROJECT = Transformer.from_crs(25830, 4326, always_xy=True)
GEOMETRY_COLUMNS = ["parcel_ref14", "usable_geometry", "geometry_wkt"]


def parcel_frame(code, ref):
    root, relative = object_source(code, "cp")
    frame = demo.read(root, relative, [("parcel_ref14", "==", ref)], columns=GEOMETRY_COLUMNS)
    return frame[frame.usable_geometry & frame.parcel_ref14.eq(ref)].copy()


def parcel_deck(frame, ref="", *, focus=False):
    geometries = sh.transform(
        sh.from_wkt(frame.geometry_wkt.to_numpy()), PROJECT.transform, interleaved=False
    )
    features = [
        {
            "type": "Feature",
            "geometry": sh.geometry.mapping(geometry),
            "properties": {"unit_id": parcel, "selected": parcel == ref},
        }
        for parcel, geometry in zip(frame.parcel_ref14, geometries, strict=True)
    ]
    extent = geometries[frame.parcel_ref14.eq(ref)] if focus else geometries
    west, south, east, north = sh.total_bounds(extent)
    lat = (south + north) / 2
    # A 256 px fit with padding also covers the 320 px layout.
    span = max(east - west, (north - south) / math.cos(math.radians(lat)), 0.00005)
    zoom = max(3, min(19, math.log2(360 / span) - 1.45))
    return pdk.Deck(
        layers=[
            pdk.Layer(
                "GeoJsonLayer",
                {"type": "FeatureCollection", "features": features},
                id="commercial-parcels",
                pickable=True,
                get_fill_color="properties.selected ? [244, 206, 99, 145] : [225, 181, 63, 105]",
                get_line_color="properties.selected ? [255, 231, 151] : [235, 193, 81]",
                get_line_width="properties.selected ? 3 : 1",
                line_width_units="pixels",
                line_width_min_pixels=1,
            )
        ],
        initial_view_state=pdk.ViewState(latitude=lat, longitude=(west + east) / 2, zoom=zoom),
        map_style=None,
        tooltip=False,
    )


def selected_deck(frame, ref):
    return parcel_deck(frame, ref, focus=True)


def render(code, ref, key):
    frame = parcel_frame(code, ref)
    if frame.empty:
        st.info(t("ux.no_geometry"))
        return
    st.pydeck_chart(selected_deck(frame, ref), key=key, height=420)
