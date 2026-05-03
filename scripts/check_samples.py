"""Validate a generated run: schema checks, image presence, summary stats."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from zamba_sat.schema import DeforestationAnnotation

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "runs"


def main() -> None:
    if len(sys.argv) > 1:
        run_dir = DATA_DIR / sys.argv[1]
    else:
        runs = sorted([p for p in DATA_DIR.iterdir() if p.is_dir()])
        if not runs:
            raise SystemExit("no runs found")
        run_dir = runs[-1]

    print(f"Checking {run_dir}")
    expected_files = {"rgb_t1.png", "swir_t1.png", "rgb_t0.png", "swir_t0.png", "metadata.json"}

    n_total = 0
    n_complete = 0
    n_labeled = 0
    schema_errors: list[str] = []
    pattern_counts: Counter[str] = Counter()

    for meta in sorted(run_dir.rglob("metadata.json")):
        sample_dir = meta.parent
        n_total += 1
        present = {p.name for p in sample_dir.iterdir()}
        if expected_files.issubset(present):
            n_complete += 1
        ann_path = sample_dir / "annotation.json"
        if ann_path.exists():
            n_labeled += 1
            try:
                ann = DeforestationAnnotation.model_validate_json(ann_path.read_text())
                pattern_counts[ann.change_pattern] += 1
            except Exception as exc:  # noqa: BLE001
                schema_errors.append(f"{sample_dir}: {exc}")

    print(f"Samples: {n_total}")
    print(f"Complete (4 PNGs + metadata): {n_complete}")
    print(f"Labeled (annotation.json present): {n_labeled}")
    if pattern_counts:
        print("change_pattern distribution:")
        for k, v in pattern_counts.most_common():
            print(f"  {k}: {v}")
    if schema_errors:
        print(f"\nSchema errors ({len(schema_errors)}):")
        for err in schema_errors:
            print(f"  {err}")


if __name__ == "__main__":
    main()
