"""WDPA protected-area overlay (stub).

Placeholder until we wire up the actual WDPA polygons. Real implementation
should load the WDPA shapefile/geopackage and do a point-in-polygon test.
For now we return False so downstream code has a stable signature.
"""

from __future__ import annotations


def in_protected_zone(lon: float, lat: float) -> bool:
    """Return True iff the point falls inside a WDPA protected area.

    TODO: wire WDPA via geopandas + shapely. Today's behaviour: always False.
    """
    _ = (lon, lat)
    return False
