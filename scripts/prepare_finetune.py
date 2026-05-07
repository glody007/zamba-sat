"""Convert labeled samples to leap-finetune VLM SFT JSONL.

Mirrors `prepare_wildfire.py` from the Liquid cookbook, adapted for our
two-frame RGB+SWIR change-detection task (4 images per sample).

Output layout:

    <output_dir>/
    ├── zamba_train.jsonl
    ├── zamba_test.jsonl
    ├── splits.json                           # logical split assignment
    └── images/
        └── <sample_id>__<frame>.png          # 4 per sample

Each JSONL row contains a `messages` array — user message has 4 image refs
plus the SYSTEM_PROMPT concatenated with the per-sample user text; assistant
message is the full XML-CoT response reconstructed from
`annotation_reasoning.txt` and `annotation.json`.

By default we honor the `data/runs/<run>/{train,test}/` directory split.
With `--skip-clouds` (recommended), the dir-split breaks because expansion
samples cluster in the test side — so we pool all non-cloud samples,
stratified-shuffle by `change_pattern` with `--seed`, and split by
`--train-frac`. `splits.json` records the resulting assignment so
`evaluate.py` can score on the same test set.

For Modal: upload `<output_dir>/` to a Modal volume and point the
`leap-finetune` config at it (set `image_root` to `images/`).

Usage:
    uv run scripts/prepare_finetune.py \\
        --runs wide_window wide_window_v2 \\
        --output data/finetune \\
        --skip-clouds
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path

from zamba_sat.labeling import SYSTEM_PROMPT, render_user_text


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "data" / "runs"

FRAME_NAMES = ("rgb_t1", "swir_t1", "rgb_t0", "swir_t0")

# Sections we expect in annotation_reasoning.txt, written as `# section_name`.
SECTION_TAGS = ("frame_descriptions", "change_analysis", "final_pattern")


def _parse_reasoning_sections(text: str) -> dict[str, str]:
    """Split a reasoning .txt file (markdown-section headers) into a dict."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^#\s+([a-z_]+)\s*$", line.strip())
        if m and m.group(1) in SECTION_TAGS:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1)
            buf = []
        else:
            if current is not None:
                buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def _render_xml_cot(reasoning_text: str, annotation: dict) -> str:
    """Reconstruct the XML chain-of-thought response the model is trained to emit."""
    sections = _parse_reasoning_sections(reasoning_text)
    parts = []
    for tag in SECTION_TAGS:
        body = sections.get(tag, "").strip()
        parts.append(f"<{tag}>\n{body}\n</{tag}>")
    parts.append("<json>\n" + json.dumps(annotation, indent=2) + "\n</json>")
    return "\n\n".join(parts)


def _make_row(
    sample_id: str,
    frame_filenames: dict[str, str],
    user_text: str,
    assistant_text: str,
) -> dict:
    """Build one leap-finetune JSONL row."""
    return {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": frame_filenames["rgb_t1"]},
                    {"type": "image", "image": frame_filenames["swir_t1"]},
                    {"type": "image", "image": frame_filenames["rgb_t0"]},
                    {"type": "image", "image": frame_filenames["swir_t0"]},
                    {"type": "text", "text": SYSTEM_PROMPT + "\n\n" + user_text},
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": assistant_text}],
            },
        ],
        "sample_id": sample_id,
    }


def _discover_samples(
    runs: list[str],
    skip_clouds: bool,
    counters: dict[str, int],
) -> list[dict]:
    """Walk run dirs and return one record per usable sample.

    Each record has: sample_id, dir_split (from filesystem), change_pattern,
    annotation, reasoning_text, meta. The `dir_split` is the original
    train/test from the directory layout — callers may keep it (default
    behavior) or override via stratified shuffle (when --skip-clouds).
    """
    out: list[dict] = []
    for run in runs:
        run_dir = RUNS_DIR / run
        if not run_dir.is_dir():
            print(f"skip: {run_dir} (missing)")
            continue
        for ann_path in sorted(run_dir.glob("*/*/*/annotation.json")):
            sd = ann_path.parent
            dir_split = sd.parts[-3]   # train | test
            location_id = sd.parts[-2]
            sample_dir_name = sd.name   # sNN_tNN
            sample_id = f"{run}__{dir_split}__{location_id}__{sample_dir_name}"

            annotation = json.loads(ann_path.read_text())
            if skip_clouds and annotation.get("change_pattern") == "cloud_artifact":
                counters["skipped_clouds"] += 1
                continue

            reasoning_path = sd / "annotation_reasoning.txt"
            if not reasoning_path.exists():
                counters["missing_reasoning"] += 1
                continue
            out.append({
                "sample_id": sample_id,
                "dir_split": dir_split,
                "change_pattern": annotation.get("change_pattern"),
                "annotation": annotation,
                "reasoning_text": reasoning_path.read_text(),
                "meta": json.loads((sd / "metadata.json").read_text()),
                "sample_dir": sd,
            })
    return out


def _stratified_split(
    samples: list[dict],
    train_frac: float,
    seed: int,
) -> dict[str, list[dict]]:
    """Stratified shuffle/split by `change_pattern`."""
    by_class: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by_class[s["change_pattern"] or "_unknown"].append(s)

    rng = random.Random(seed)
    train: list[dict] = []
    test: list[dict] = []
    for cls in sorted(by_class):
        rows = by_class[cls][:]
        rng.shuffle(rows)
        n_train = round(len(rows) * train_frac)
        # Guarantee at least 1 train and 1 test per class when possible.
        if len(rows) >= 2:
            n_train = max(1, min(n_train, len(rows) - 1))
        train.extend(rows[:n_train])
        test.extend(rows[n_train:])
    return {"train": train, "test": test}


def _emit_rows(
    samples: list[dict],
    images_dir: Path,
) -> tuple[list[dict], list[str]]:
    """Copy images and build JSONL rows for a list of samples."""
    rows: list[dict] = []
    sample_ids: list[str] = []
    for s in samples:
        sd: Path = s["sample_dir"]
        sample_id: str = s["sample_id"]

        frame_filenames: dict[str, str] = {}
        for f in FRAME_NAMES:
            src = sd / f"{f}.png"
            if not src.exists():
                continue
            dst_name = f"{sample_id}__{f}.png"
            shutil.copy2(src, images_dir / dst_name)
            frame_filenames[f] = dst_name
        if len(frame_filenames) != 4:
            print(f"  WARN missing frames for {sample_id}, got {list(frame_filenames)}")
            continue

        m = s["meta"]
        user_text = render_user_text(
            lat=m["tile_lat"], lon=m["tile_lon"],
            region_name=m.get("location_name", ""),
            date_t1=m["actual_t1_datetime"],
            date_t0=m["actual_t0_datetime"],
        )
        assistant_text = _render_xml_cot(s["reasoning_text"], s["annotation"])
        rows.append(_make_row(sample_id, frame_filenames, user_text, assistant_text))
        sample_ids.append(sample_id)
    return rows, sample_ids


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", nargs="+", required=True,
                   help="Run directory names under data/runs/")
    p.add_argument("--output", type=Path, default=Path("data/finetune"))
    p.add_argument("--skip-clouds", action="store_true",
                   help="Drop cloud_artifact samples (recommended for SFT — they "
                        "are noise, not signal). Triggers a stratified re-split.")
    p.add_argument("--seed", type=int, default=42,
                   help="RNG seed for stratified shuffle (only used with --skip-clouds).")
    p.add_argument("--train-frac", type=float, default=0.8,
                   help="Train fraction for stratified split (only used with --skip-clouds).")
    args = p.parse_args()

    out_dir: Path = args.output
    images_dir = out_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    counters = {"skipped_clouds": 0, "missing_reasoning": 0}
    samples = _discover_samples(args.runs, args.skip_clouds, counters)

    if args.skip_clouds:
        # The original dir-split clusters expansion in test; restratify.
        splits = _stratified_split(samples, args.train_frac, args.seed)
        split_meta = {"strategy": "stratified", "seed": args.seed,
                      "train_frac": args.train_frac, "skip_clouds": True}
    else:
        splits = {"train": [], "test": []}
        for s in samples:
            splits[s["dir_split"]].append(s)
        split_meta = {"strategy": "directory", "skip_clouds": False}

    splits_record: dict[str, list[str]] = {"train": [], "test": []}
    for split, sample_list in splits.items():
        rows, ids = _emit_rows(sample_list, images_dir)
        path = out_dir / f"zamba_{split}.jsonl"
        with path.open("w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        print(f"wrote {path}: {len(rows)} rows")
        splits_record[split] = ids

    # Per-class breakdown (helpful when validating the split).
    for split, sample_list in splits.items():
        cnt: dict[str, int] = defaultdict(int)
        for s in sample_list:
            cnt[s["change_pattern"] or "_unknown"] += 1
        print(f"  {split} class counts: {dict(cnt)}")

    splits_path = out_dir / "splits.json"
    splits_path.write_text(json.dumps({**split_meta, **splits_record}, indent=2))
    print(f"wrote {splits_path}")

    print(f"images/: {len(list(images_dir.glob('*.png')))} PNGs")
    if counters["skipped_clouds"]:
        print(f"skipped {counters['skipped_clouds']} cloud_artifact samples (--skip-clouds)")
    if counters["missing_reasoning"]:
        print(f"WARN: {counters['missing_reasoning']} samples missing annotation_reasoning.txt")


if __name__ == "__main__":
    main()
