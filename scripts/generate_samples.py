"""Generate deforestation samples across spatial and temporal tiles.

For each (location, spatial_tile, t0_date), fetches:
    rgb_t1.png, swir_t1.png, rgb_t0.png, swir_t0.png

and saves a sidecar metadata.json. Labeling is OFF by default — produced
samples are picked up later either by ``scripts/label_pending.py`` (Claude-
in-conversation) or by passing ``--label`` (Anthropic API, costs money).

Usage:
    uv run scripts/generate_samples.py \\
        --start-date 2025-09-01 --end-date 2026-04-01 \\
        --location salonga_north_drc \\
        --n-temporal-samples 2 --n-spatial-tiles 4 \\
        --size-km 10.0
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# Allow running as `uv run scripts/generate_samples.py` without installing.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tqdm import tqdm

from zamba_sat.locations import Location, iter_filtered, load_locations
from zamba_sat.simsat_client import (
    ImageUnavailable,
    SentinelImage,
    SimSatClient,
)
from zamba_sat.temporal_sampler import (
    TileCoord,
    TimestampPair,
    pair_for_t0,
    spatial_grid,
    temporal_t0_dates,
    train_test_cutoff,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "runs"


@dataclass
class TileTask:
    location_id: str
    location_name: str
    spatial_idx: int
    temporal_idx: int
    tile: TileCoord
    pair: TimestampPair
    split: str  # "train" | "test"

    @property
    def key(self) -> str:
        return f"s{self.spatial_idx:02d}_t{self.temporal_idx:02d}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start-date", required=True)
    p.add_argument("--end-date", required=True)
    p.add_argument("--n-temporal-samples", type=int, default=1)
    p.add_argument("--n-spatial-tiles", type=int, default=1, help="must be perfect square")
    p.add_argument("--size-km", type=float, default=10.0)
    p.add_argument("--t1-offset-days", type=int, default=30)
    p.add_argument("--window-seconds", type=int, default=864000)
    p.add_argument("--max-cloud-cover", type=float, default=60.0)
    p.add_argument("--cloud-retry-shift-days", type=int, default=5)
    p.add_argument("--cloud-retries", type=int, default=2)
    p.add_argument("--test-ratio", type=float, default=0.2)
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--location", action="append", default=None,
                   help="Location id; repeat to add more. Default: all locations.")
    p.add_argument("--label", action="store_true",
                   help="Also run Anthropic-API labeling now. Default: skip "
                        "(annotation.json is filled in later).")
    p.add_argument("--run-name", default=None,
                   help="Override the timestamped run dir name.")
    return p.parse_args()


def _build_tasks(
    locations: list[Location],
    *,
    start: datetime,
    end: datetime,
    n_temporal_samples: int,
    n_spatial_tiles: int,
    size_km: float,
    t1_offset_days: int,
    test_ratio: float,
) -> list[TileTask]:
    cutoff = train_test_cutoff(start, end, test_ratio)
    tasks: list[TileTask] = []

    for loc in locations:
        tiles = spatial_grid(loc.lon, loc.lat, n_spatial_tiles, size_km)
        t0_dates = temporal_t0_dates(start, end, n_temporal_samples, t1_offset_days)
        for ti, t0 in enumerate(t0_dates):
            pair = pair_for_t0(t0, t1_offset_days=t1_offset_days)
            split = "test" if t0 >= cutoff else "train"
            for si, tile in enumerate(tiles):
                tasks.append(
                    TileTask(
                        location_id=loc.id,
                        location_name=loc.name,
                        spatial_idx=si,
                        temporal_idx=ti,
                        tile=tile,
                        pair=pair,
                        split=split,
                    )
                )
    return tasks


def _fetch_pair_with_cloud_retry(
    client: SimSatClient,
    task: TileTask,
    *,
    size_km: float,
    max_cloud_cover: float,
    retries: int,
    shift_days: int,
) -> tuple[SentinelImage, SentinelImage, SentinelImage, SentinelImage]:
    """Fetch (rgb_t1, swir_t1, rgb_t0, swir_t0). Retry with shifted dates if cloudy."""
    pair = task.pair
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            rgb_t1 = client.fetch_rgb(task.tile.lon, task.tile.lat, pair.t1, size_km=size_km)
            swir_t1 = client.fetch_swir(task.tile.lon, task.tile.lat, pair.t1, size_km=size_km)
            rgb_t0 = client.fetch_rgb(task.tile.lon, task.tile.lat, pair.t0, size_km=size_km)
            swir_t0 = client.fetch_swir(task.tile.lon, task.tile.lat, pair.t0, size_km=size_km)
        except ImageUnavailable as exc:
            raise  # no point shifting if the catalogue has nothing here
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2 * (attempt + 1))
            continue

        worst_cloud = max(rgb_t1.cloud_cover, rgb_t0.cloud_cover)
        if worst_cloud <= max_cloud_cover:
            return rgb_t1, swir_t1, rgb_t0, swir_t0

        if attempt == retries:
            return rgb_t1, swir_t1, rgb_t0, swir_t0  # accept best effort

        # Shift both ends back by shift_days and retry.
        shifted = _shift_pair(pair, days=-shift_days)
        tqdm.write(
            f"[{task.location_id}/{task.key}] cloud_cover={worst_cloud:.1f}% > "
            f"{max_cloud_cover:.0f}%, shifting {shift_days}d earlier and retrying"
        )
        pair = shifted

    if last_error is not None:
        raise last_error
    raise RuntimeError("unreachable")


def _shift_pair(pair: TimestampPair, *, days: int) -> TimestampPair:
    from datetime import timedelta as _td
    t1 = datetime.strptime(pair.t1, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    t0 = datetime.strptime(pair.t0, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    t1 += _td(days=days)
    t0 += _td(days=days)
    return TimestampPair(
        t1=t1.strftime("%Y-%m-%dT%H:%M:%SZ"),
        t0=t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def _process_task(
    client: SimSatClient,
    task: TileTask,
    run_dir: Path,
    *,
    size_km: float,
    max_cloud_cover: float,
    cloud_retries: int,
    cloud_retry_shift_days: int,
) -> dict | None:
    sample_dir = run_dir / task.split / task.location_id / task.key
    sample_dir.mkdir(parents=True, exist_ok=True)

    try:
        rgb_t1, swir_t1, rgb_t0, swir_t0 = _fetch_pair_with_cloud_retry(
            client, task,
            size_km=size_km,
            max_cloud_cover=max_cloud_cover,
            retries=cloud_retries,
            shift_days=cloud_retry_shift_days,
        )
    except ImageUnavailable as exc:
        tqdm.write(f"[{task.location_id}/{task.key}] SKIP: {exc}")
        # Leave a marker so re-runs don't re-attempt unless cleaned.
        (sample_dir / "_unavailable.txt").write_text(str(exc))
        return None

    (sample_dir / "rgb_t1.png").write_bytes(rgb_t1.png_bytes)
    (sample_dir / "swir_t1.png").write_bytes(swir_t1.png_bytes)
    (sample_dir / "rgb_t0.png").write_bytes(rgb_t0.png_bytes)
    (sample_dir / "swir_t0.png").write_bytes(swir_t0.png_bytes)

    metadata = {
        "location_id": task.location_id,
        "location_name": task.location_name,
        "split": task.split,
        "spatial_idx": task.spatial_idx,
        "temporal_idx": task.temporal_idx,
        "tile_lon": task.tile.lon,
        "tile_lat": task.tile.lat,
        "size_km": size_km,
        "requested_t1": task.pair.t1,
        "requested_t0": task.pair.t0,
        "actual_t1_datetime": rgb_t1.datetime,
        "actual_t0_datetime": rgb_t0.datetime,
        "cloud_cover_t1_rgb": rgb_t1.cloud_cover,
        "cloud_cover_t0_rgb": rgb_t0.cloud_cover,
        "source_t1": rgb_t1.source,
        "source_t0": rgb_t0.source,
        "footprint_t0": rgb_t0.footprint,
    }
    (sample_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def main() -> None:
    args = parse_args()

    start = datetime.fromisoformat(args.start_date).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end_date).replace(tzinfo=timezone.utc)

    locations = list(iter_filtered(load_locations(), only=args.location))
    print(f"Locations: {[loc.id for loc in locations]}")

    tasks = _build_tasks(
        locations,
        start=start,
        end=end,
        n_temporal_samples=args.n_temporal_samples,
        n_spatial_tiles=args.n_spatial_tiles,
        size_km=args.size_km,
        t1_offset_days=args.t1_offset_days,
        test_ratio=args.test_ratio,
    )
    print(f"Total tasks: {len(tasks)}")

    run_name = args.run_name or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = DATA_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_name": run_name,
                "args": {k: v for k, v in vars(args).items()},
                "n_tasks": len(tasks),
                "locations": [asdict(loc) for loc in locations],
            },
            indent=2,
        )
    )
    print(f"Run dir: {run_dir}")

    completed: list[dict] = []
    with SimSatClient() as client:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {
                pool.submit(
                    _process_task,
                    client, task, run_dir,
                    size_km=args.size_km,
                    max_cloud_cover=args.max_cloud_cover,
                    cloud_retries=args.cloud_retries,
                    cloud_retry_shift_days=args.cloud_retry_shift_days,
                ): task
                for task in tasks
            }
            for fut in tqdm(as_completed(futures), total=len(futures), desc="fetch"):
                task = futures[fut]
                try:
                    result = fut.result()
                except Exception as exc:  # noqa: BLE001
                    tqdm.write(f"[{task.location_id}/{task.key}] ERROR: {exc}")
                    continue
                if result is not None:
                    completed.append(result)

    print(f"Done. {len(completed)}/{len(tasks)} samples fetched into {run_dir}")

    if args.label:
        print("--label flag set: running Anthropic-API labeling pass")
        _label_run_via_api(run_dir)


def _label_run_via_api(run_dir: Path) -> None:
    """Walk the run directory and produce annotation.json for every sample."""
    from zamba_sat.labeling import label_via_api  # lazy import

    for metadata_path in run_dir.rglob("metadata.json"):
        sample_dir = metadata_path.parent
        if (sample_dir / "annotation.json").exists():
            continue
        meta = json.loads(metadata_path.read_text())
        try:
            parsed = label_via_api(
                rgb_t1=(sample_dir / "rgb_t1.png").read_bytes(),
                swir_t1=(sample_dir / "swir_t1.png").read_bytes(),
                rgb_t0=(sample_dir / "rgb_t0.png").read_bytes(),
                swir_t0=(sample_dir / "swir_t0.png").read_bytes(),
                lat=meta["tile_lat"],
                lon=meta["tile_lon"],
                region_name=meta["location_name"],
                date_t1=meta["actual_t1_datetime"],
                date_t0=meta["actual_t0_datetime"],
            )
        except Exception as exc:  # noqa: BLE001
            tqdm.write(f"[{sample_dir.name}] LABEL ERROR: {exc}")
            continue
        (sample_dir / "annotation.json").write_text(
            parsed.annotation.model_dump_json(indent=2)
        )
        (sample_dir / "annotation_reasoning.txt").write_text(
            f"# frame_descriptions\n{parsed.frame_descriptions}\n\n"
            f"# change_analysis\n{parsed.change_analysis}\n\n"
            f"# final_pattern\n{parsed.final_pattern}\n"
        )


if __name__ == "__main__":
    main()
