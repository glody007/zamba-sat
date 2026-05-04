"""Push labeled runs under data/runs/ to a HuggingFace dataset repo.

Reads HF_TOKEN from env. Builds a DatasetDict with train/test splits, where
each row carries the four PNG frames as Image columns plus metadata,
annotation fields, and the chain-of-thought reasoning string.

Usage:
    HF_TOKEN=hf_xxx uv run scripts/upload_to_hf.py \\
        --repo-id glody007/zamba-sat-congo-deforestation \\
        --runs yangambi_dry frontiers_dry dry_season smoke_test
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from datasets import Dataset, DatasetDict, Features, Image, Sequence, Value
from huggingface_hub import HfApi


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "data" / "runs"


def _collect_records(run_names: list[str]) -> list[dict]:
    records: list[dict] = []
    for run_name in run_names:
        run_dir = RUNS_DIR / run_name
        if not run_dir.is_dir():
            print(f"skip: {run_dir} (not found)")
            continue
        for ann_path in sorted(run_dir.rglob("annotation.json")):
            sample_dir = ann_path.parent
            split = sample_dir.parts[-3]   # train | test
            location_id = sample_dir.parts[-2]
            sample_idx = sample_dir.name   # sNN_tNN

            metadata_path = sample_dir / "metadata.json"
            reasoning_path = sample_dir / "annotation_reasoning.txt"

            ann = json.loads(ann_path.read_text())
            meta = json.loads(metadata_path.read_text())
            reasoning = (
                reasoning_path.read_text() if reasoning_path.exists() else ""
            )

            records.append({
                "sample_id": f"{run_name}/{location_id}/{sample_idx}",
                "run_name": run_name,
                "split": split,
                "location_id": location_id,
                "location_name": meta.get("location_name", ""),
                "spatial_idx": int(meta["spatial_idx"]),
                "temporal_idx": int(meta["temporal_idx"]),
                "tile_lon": float(meta["tile_lon"]),
                "tile_lat": float(meta["tile_lat"]),
                "size_km": float(meta["size_km"]),
                "requested_t1": meta["requested_t1"],
                "requested_t0": meta["requested_t0"],
                "actual_t1_datetime": meta["actual_t1_datetime"],
                "actual_t0_datetime": meta["actual_t0_datetime"],
                "cloud_cover_t1_rgb": float(meta["cloud_cover_t1_rgb"]),
                "cloud_cover_t0_rgb": float(meta["cloud_cover_t0_rgb"]),
                "source_t1": meta.get("source_t1", ""),
                "source_t0": meta.get("source_t0", ""),
                "rgb_t1": str(sample_dir / "rgb_t1.png"),
                "swir_t1": str(sample_dir / "swir_t1.png"),
                "rgb_t0": str(sample_dir / "rgb_t0.png"),
                "swir_t0": str(sample_dir / "swir_t0.png"),
                "deforestation_detected": bool(ann["deforestation_detected"]),
                "change_pattern": ann["change_pattern"],
                "trajectory_confidence": ann["trajectory_confidence"],
                "severity": ann["severity"],
                "clearing_type": ann["clearing_type"],
                "area_bucket_t1": ann["area_bucket_t1"],
                "area_bucket_t0": ann["area_bucket_t0"],
                "active_operation": bool(ann["active_operation"]),
                "active_machinery_visible": bool(ann["active_machinery_visible"]),
                "smoke_or_fire_visible": bool(ann["smoke_or_fire_visible"]),
                "recent_road_construction": bool(ann["recent_road_construction"]),
                "frame_quality": list(ann["frame_quality"]),
                "annotation_json": json.dumps(ann),
                "reasoning": reasoning,
            })
    return records


def _features() -> Features:
    return Features({
        "sample_id": Value("string"),
        "run_name": Value("string"),
        "split": Value("string"),
        "location_id": Value("string"),
        "location_name": Value("string"),
        "spatial_idx": Value("int32"),
        "temporal_idx": Value("int32"),
        "tile_lon": Value("float64"),
        "tile_lat": Value("float64"),
        "size_km": Value("float32"),
        "requested_t1": Value("string"),
        "requested_t0": Value("string"),
        "actual_t1_datetime": Value("string"),
        "actual_t0_datetime": Value("string"),
        "cloud_cover_t1_rgb": Value("float32"),
        "cloud_cover_t0_rgb": Value("float32"),
        "source_t1": Value("string"),
        "source_t0": Value("string"),
        "rgb_t1": Image(),
        "swir_t1": Image(),
        "rgb_t0": Image(),
        "swir_t0": Image(),
        "deforestation_detected": Value("bool"),
        "change_pattern": Value("string"),
        "trajectory_confidence": Value("string"),
        "severity": Value("string"),
        "clearing_type": Value("string"),
        "area_bucket_t1": Value("string"),
        "area_bucket_t0": Value("string"),
        "active_operation": Value("bool"),
        "active_machinery_visible": Value("bool"),
        "smoke_or_fire_visible": Value("bool"),
        "recent_road_construction": Value("bool"),
        "frame_quality": Sequence(Value("string")),
        "annotation_json": Value("string"),
        "reasoning": Value("string"),
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--private", action="store_true", default=False)
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN")
    if not token and not args.dry_run:
        raise SystemExit("HF_TOKEN env var is required")

    records = _collect_records(args.runs)
    if not records:
        raise SystemExit("No labeled samples found")

    train = [r for r in records if r["split"] == "train"]
    test = [r for r in records if r["split"] == "test"]

    print(f"Collected {len(records)} samples: {len(train)} train, {len(test)} test")

    feats = _features()
    ds = DatasetDict({
        "train": Dataset.from_list(train, features=feats),
        "test": Dataset.from_list(test, features=feats),
    })

    print(ds)
    if args.dry_run:
        print("[dry-run] not pushing")
        return

    api = HfApi(token=token)
    api.create_repo(args.repo_id, repo_type="dataset", private=args.private, exist_ok=True)
    ds.push_to_hub(args.repo_id, token=token, private=args.private)
    print(f"Pushed → https://huggingface.co/datasets/{args.repo_id}")


if __name__ == "__main__":
    main()
