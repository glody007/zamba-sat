"""HTTPX-based client for the SimSat Sentinel-2 endpoint.

SimSat returns the PNG image bytes as the response body and stuffs the
acquisition metadata into a `sentinel_metadata` HTTP response header
(JSON-encoded). When no Sentinel-2 image is available for the requested
location/time it returns a 4xx, which we surface as ``ImageUnavailable``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Sequence

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def _is_retryable(exc: BaseException) -> bool:
    """Retry on transport errors and 5xx responses; never retry on 4xx."""
    if isinstance(exc, (httpx.TransportError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False

DEFAULT_BASE_URL = os.environ.get("SIMSAT_BASE_URL", "http://localhost:9005")

# Per the wildfire-prevention cookbook (validated band combo for vegetation
# stress / clearing detection in tropical forest).
RGB_BANDS: tuple[str, ...] = ("red", "green", "blue")
SWIR_BANDS: tuple[str, ...] = ("swir16", "nir08", "red")


class ImageUnavailable(Exception):
    """SimSat has no Sentinel-2 image for this (lon, lat, timestamp)."""


@dataclass(frozen=True)
class SentinelImage:
    """A single fetched image plus its acquisition metadata."""

    bands: tuple[str, ...]
    png_bytes: bytes
    cloud_cover: float
    datetime: str           # actual Sentinel-2 acquisition timestamp (ISO-8601)
    source: str             # "sentinel-2a" | "sentinel-2b" | "sentinel-2c"
    footprint: list[float]  # [lon_min, lat_min, lon_max, lat_max]
    size_km: float


class SimSatClient:
    """Thin wrapper around SimSat's `/data/image/sentinel` endpoint."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SimSatClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1.5, min=2, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def fetch(
        self,
        lon: float,
        lat: float,
        timestamp: str,
        bands: Sequence[str],
        size_km: float = 10.0,
        window_seconds: int = 864000,
    ) -> SentinelImage:
        """Fetch a Sentinel-2 image for the given location, time, and band set."""
        params: list[tuple[str, object]] = [
            ("lon", lon),
            ("lat", lat),
            ("timestamp", timestamp),
            ("size_km", size_km),
            ("return_type", "png"),
            ("window_seconds", window_seconds),
        ] + [("spectral_bands", b) for b in bands]

        url = f"{self.base_url}/data/image/sentinel"
        response = self._client.get(url, params=params)

        if response.status_code in (400, 404):
            raise ImageUnavailable(
                f"SimSat returned {response.status_code} for "
                f"lon={lon}, lat={lat}, ts={timestamp}, bands={list(bands)}"
            )
        response.raise_for_status()

        meta_header = response.headers.get("sentinel_metadata")
        if not meta_header:
            raise RuntimeError("SimSat response missing sentinel_metadata header")
        metadata = json.loads(meta_header)
        if not metadata.get("image_available", False):
            raise ImageUnavailable(
                f"image_available=False for lon={lon}, lat={lat}, ts={timestamp}"
            )

        return SentinelImage(
            bands=tuple(bands),
            png_bytes=response.content,
            cloud_cover=float(metadata.get("cloud_cover", 0.0)),
            datetime=str(metadata["datetime"]),
            source=str(metadata.get("source", "unknown")),
            footprint=list(metadata.get("footprint", [])),
            size_km=float(metadata.get("size_km", size_km)),
        )

    def fetch_rgb(self, lon: float, lat: float, timestamp: str, size_km: float = 10.0) -> SentinelImage:
        return self.fetch(lon, lat, timestamp, RGB_BANDS, size_km=size_km)

    def fetch_swir(self, lon: float, lat: float, timestamp: str, size_km: float = 10.0) -> SentinelImage:
        return self.fetch(lon, lat, timestamp, SWIR_BANDS, size_km=size_km)
