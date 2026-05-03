"""Loader for the monitored locations defined in configs/locations.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import yaml

_DEFAULT_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "locations.yaml"
)


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    lat: float
    lon: float
    notes: str = ""


def load_locations(path: Path | None = None) -> list[Location]:
    """Read locations.yaml and return parsed Location objects."""
    yaml_path = path or _DEFAULT_PATH
    with yaml_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    items = raw.get("locations", [])
    return [
        Location(
            id=item["id"],
            name=item["name"],
            lat=float(item["lat"]),
            lon=float(item["lon"]),
            notes=item.get("notes", ""),
        )
        for item in items
    ]


def by_id(locations: list[Location]) -> dict[str, Location]:
    return {loc.id: loc for loc in locations}


def iter_filtered(
    locations: list[Location],
    only: list[str] | None = None,
) -> Iterator[Location]:
    """Yield locations whose id is in `only`, or all if `only` is None."""
    if only is None:
        yield from locations
        return
    seen = set()
    index = by_id(locations)
    for wanted in only:
        if wanted not in index:
            raise KeyError(f"unknown location id: {wanted}")
        if wanted in seen:
            continue
        seen.add(wanted)
        yield index[wanted]
