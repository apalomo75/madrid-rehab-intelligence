"""Bounded map for a documentary confirmed parcel, without geocoding."""

import math

from . import demo
from .i18n import t, ui as st
from .municipal_navigation import object_source


def parcel_frame(code, ref):
    root, relative = object_source(code, "cp")
    frame = demo.read(root, relative, [("parcel_ref14", "==", ref)])
    return frame[frame.usable_geometry & frame.parcel_ref14.eq(ref)].copy()


def selected_deck(frame, ref):
    import pydeck as pdk
    import shapely as sh
    from pyproj import Transformer
    from shapely.ops import transform
    from .regional_view import geometry_deck

    deck = geometry_deck(frame, "parcel_ref14", selected=ref, preserve_geometry=True)
    project = Transformer.from_crs(25830, 4326, always_xy=True).transform
    geom = transform(
        project,
        sh.union_all(sh.from_wkt(frame.loc[frame.parcel_ref14.eq(ref), "geometry_wkt"].to_numpy())),
    )
    west, south, east, north = geom.bounds
    center = geom.centroid
    # Conservative fit for a narrow mobile viewport as well as desktop.
    span = max(east - west, (north - south) / max(0.1, math.cos(math.radians(center.y))), 0.00005)
    zoom = max(3, min(19, math.log2(360 / span) - 1.5))
    deck.initial_view_state = pdk.ViewState(latitude=center.y, longitude=center.x, zoom=zoom)
    return deck


def render(code, ref, key):
    frame = parcel_frame(code, ref)
    if frame.empty:
        st.info(t("ux.no_geometry"))
        return
    st.pydeck_chart(selected_deck(frame, ref), key=key, height=420)
