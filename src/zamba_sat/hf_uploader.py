"""HuggingFace Hub uploader (stub)."""

from __future__ import annotations

from pathlib import Path


def push_run_to_hf(run_dir: Path, dataset_name: str) -> None:
    """Push a generated run to HF Hub in leap-finetune VLM SFT format.

    TODO: implement. Mirror the wildfire-prevention cookbook's tabular format
    (string-only columns: region, timestamp, split, rgb_t1_path, swir_t1_path,
    rgb_t0_path, swir_t0_path, output) plus a separate images/ upload.
    """
    raise NotImplementedError(
        f"hf_uploader stub. run_dir={run_dir}, dataset_name={dataset_name}"
    )
