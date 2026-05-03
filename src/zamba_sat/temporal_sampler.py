"""Temporal and spatial tile generation.

Mirrors the wildfire-prevention cookbook approach: bin-center placement of
timestamps within [start, end], and a centered N-tile spatial grid around
each location, then a temporal cutoff to assign train/test splits.

The 2-frame extension is in `pair_for_t0`: given a current `t0`, it returns
the matching `t1 = t0 - offset_days`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# 1 degree of latitude ≈ 111.32 km. Longitude spacing depends on latitude.
_KM_PER_DEG_LAT = 111.32


@dataclass(frozen=True)
class TileCoord:
    """A spatial sub-tile derived from a Location center."""

    lon: float
    lat: float


@dataclass(frozen=True)
class TimestampPair:
    """A temporal sample: t1 (older) and t0 (current), both ISO-8601 UTC."""

    t1: str
    t0: str


def spatial_grid(
    center_lon: float,
    center_lat: float,
    n_tiles: int,
    size_km: float,
) -> list[TileCoord]:
    """Return `n_tiles` tiles arranged in a centered square grid.

    `n_tiles` must be a perfect square (1, 4, 9, 16, ...). The grid is row-
    major from the top-left, with tiles spaced `size_km` apart center-to-center.
    """
    side = int(math.isqrt(n_tiles))
    if side * side != n_tiles:
        raise ValueError(f"n_tiles must be a perfect square, got {n_tiles}")

    deg_per_km_lat = 1.0 / _KM_PER_DEG_LAT
    deg_per_km_lon = 1.0 / (_KM_PER_DEG_LAT * math.cos(math.radians(center_lat)))

    offset = (side - 1) / 2.0
    coords: list[TileCoord] = []
    # Row 0 = top (north), so row index decreases lat as it grows.
    for row in range(side):
        for col in range(side):
            d_lat = (offset - row) * size_km * deg_per_km_lat
            d_lon = (col - offset) * size_km * deg_per_km_lon
            coords.append(
                TileCoord(lon=center_lon + d_lon, lat=center_lat + d_lat)
            )
    return coords


def temporal_t0_dates(
    start: datetime,
    end: datetime,
    n_samples: int,
    t1_offset_days: int = 30,
) -> list[datetime]:
    """Pick `n_samples` evenly-spaced t0 dates within [start + offset, end].

    Bin-center placement: the first t0 is offset from the start so that t1
    (= t0 - offset_days) is still inside the window. Edges of the window
    are avoided to dodge boundary effects.
    """
    if n_samples <= 0:
        return []
    earliest_t0 = start + timedelta(days=t1_offset_days)
    if earliest_t0 >= end:
        raise ValueError(
            f"window [{start.date()}, {end.date()}] is too short for "
            f"t1_offset_days={t1_offset_days}"
        )
    span_seconds = (end - earliest_t0).total_seconds()
    bin_width = span_seconds / n_samples
    return [
        earliest_t0 + timedelta(seconds=bin_width * (i + 0.5))
        for i in range(n_samples)
    ]


def pair_for_t0(t0: datetime, t1_offset_days: int = 30) -> TimestampPair:
    t1 = t0 - timedelta(days=t1_offset_days)
    return TimestampPair(t1=_iso(t1), t0=_iso(t0))


def train_test_cutoff(
    start: datetime,
    end: datetime,
    test_ratio: float,
) -> datetime:
    """Cutoff date such that timestamps before it are train, on/after are test."""
    if not 0.0 <= test_ratio < 1.0:
        raise ValueError(f"test_ratio must be in [0, 1), got {test_ratio}")
    duration = end - start
    return start + duration * (1.0 - test_ratio)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
