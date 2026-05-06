"""Convert labeled samples to leap-finetune VLM SFT JSONL.

Mirrors `prepare_wildfire.py` from the Liquid cookbook, adapted for our
two-frame RGB+SWIR change-detection task (4 images per sample).

Output layout:

    <output_dir>/
    ├── zamba_train.jsonl
    ├── zamba_test.jsonl
    └── images/
        └── <sample_id>__<frame>.png        # 4 per sample

Each JSONL row contains a `messages` array — user message has 4 image refs
plus the SYSTEM_PROMPT concatenated with the per-sample user text; assistant
message is the full XML-CoT response reconstructed from
`annotation_reasoning.txt` and `annotation.json`.

For Modal: upload `<output_dir>/` to a Modal volume and point the
`leap-finetune` config at it (set `image_root` to `images/`).

Usage:
    uv run scripts/prepare_finetune.py \\
        --runs wide_window wide_window_v2 \\
        --output data/finetune
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
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


def _process_run(
    run: str,
    out_jsonl: dict[str, list[dict]],
    images_dir: Path,
    skip_clouds: bool,
    counters: dict[str, int],
) -> None:
    """Walk one run dir and append rows to out_jsonl[split]."""
    run_dir = RUNS_DIR / run
    if not run_dir.is_dir():
        print(f"skip: {run_dir} (missing)")
        return
    for ann_path in sorted(run_dir.glob("*/*/*/annotation.json")):
        sd = ann_path.parent
        split = sd.parts[-3]   # train | test
        location_id = sd.parts[-2]
        sample_dir_name = sd.name   # sNN_tNN
        sample_id = f"{run}__{split}__{location_id}__{sample_dir_name}"

        annotation = json.loads(ann_path.read_text())
        if skip_clouds and annotation.get("change_pattern") == "cloud_artifact":
            counters["skipped_clouds"] += 1
            continue

        reasoning_path = sd / "annotation_reasoning.txt"
        if not reasoning_path.exists():
            counters["missing_reasoning"] += 1
            continue
        reasoning_text = reasoning_path.read_text()

        meta = json.loads((sd / "metadata.json").read_text())
        user_text = render_user_text(
            lat=meta["tile_lat"], lon=meta["tile_lon"],
            region_name=meta.get("location_name", ""),
            date_t1=meta["actual_t1_datetime"],
            date_t0=meta["actual_t0_datetime"],
        )
        assistant_text = _render_xml_cot(reasoning_text, annotation)

        # Copy 4 PNGs into images/ with flattened filenames.
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

        row = _make_row(sample_id, frame_filenames, user_text, assistant_text)
        out_jsonl[split].append(row)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", nargs="+", required=True,
                   help="Run directory names under data/runs/")
    p.add_argument("--output", type=Path, default=Path("data/finetune"))
    p.add_argument("--skip-clouds", action="store_true",
                   help="Drop cloud_artifact samples (recommended for SFT — they "
                        "are noise, not signal).")
    args = p.parse_args()

    out_dir: Path = args.output
    images_dir = out_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    out_jsonl: dict[str, list[dict]] = {"train": [], "test": []}
    counters = {"skipped_clouds": 0, "missing_reasoning": 0}
    for run in args.runs:
        _process_run(run, out_jsonl, images_dir, args.skip_clouds, counters)

    for split, rows in out_jsonl.items():
        path = out_dir / f"zamba_{split}.jsonl"
        with path.open("w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        print(f"wrote {path}: {len(rows)} rows")
    print(f"images/: {len(list(images_dir.glob('*.png')))} PNGs")
    if counters["skipped_clouds"]:
        print(f"skipped {counters['skipped_clouds']} cloud_artifact samples (--skip-clouds)")
    if counters["missing_reasoning"]:
        print(f"WARN: {counters['missing_reasoning']} samples missing annotation_reasoning.txt")


if __name__ == "__main__":
    main()
