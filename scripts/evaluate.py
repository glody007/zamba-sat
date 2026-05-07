"""Evaluate model predictions against ground-truth annotations.

Mirrors the wildfire-prevention cookbook's evaluate.py:

  - Loads a split (default: test) from the local labeled runs.
  - Runs predictions via one of three backends (anthropic / local / claude_code).
  - Scores each prediction field-by-field against the ground-truth JSON.
  - Writes evals/<timestamp>/{report.md, results.json, meta.json}.

Backends:

    --backend anthropic   Call Anthropic API (claude-opus-4-7) — costs money
    --backend local       POST to a llama.cpp / OpenAI-compatible server
    --backend claude_code Score pre-written predictions in --predictions-dir
                          (Claude in this conversation can produce them)

Examples:

    # Anthropic oracle baseline (label-noise upper bound)
    ANTHROPIC_API_KEY=... uv run scripts/evaluate.py \\
        --backend anthropic --runs wide_window_v2 wide_window --split test

    # Local llama.cpp server hosting fine-tuned LFM
    uv run scripts/evaluate.py --backend local \\
        --server-url http://localhost:8000 --model lfm-deforestation-q8 \\
        --runs wide_window_v2 wide_window --split test

    # Score predictions Claude Code wrote in conversation
    uv run scripts/evaluate.py --backend claude_code \\
        --predictions-dir evals/2026-05-05_claude/predictions \\
        --runs wide_window_v2 wide_window --split test
"""

from __future__ import annotations

import argparse
import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from zamba_sat.labeling import SYSTEM_PROMPT, render_user_text
from zamba_sat.schema import parse_response


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "data" / "runs"
EVALS_DIR = REPO_ROOT / "evals"


# Fields scored. Order matters for report column order.
EVAL_FIELDS: list[str] = [
    "valid_json",
    "deforestation_detected",
    "change_pattern",
    "trajectory_confidence",
    "severity",
    "clearing_type",
    "area_bucket_t1",
    "area_bucket_t0",
    "active_operation",
    "active_machinery_visible",
    "smoke_or_fire_visible",
    "recent_road_construction",
    "frame_quality",
]


@dataclass
class Sample:
    sample_id: str           # "<run>/<split>/<location>/<sNN_tNN>"
    run: str
    split: str
    location_id: str
    location_name: str
    tile_lon: float
    tile_lat: float
    date_t1: str
    date_t0: str
    rgb_t1_path: Path
    swir_t1_path: Path
    rgb_t0_path: Path
    swir_t0_path: Path
    ground_truth: dict


@dataclass
class SampleResult:
    sample_id: str
    predicted: dict | None
    ground_truth: dict
    field_matches: dict[str, bool]
    error: str | None = None


def load_samples(
    runs: list[str],
    split: str,
    splits_file: Path | None = None,
) -> list[Sample]:
    """Load test/train samples from `data/runs/`.

    By default, walks `data/runs/<run>/<split>/...` (the directory-based
    split). When `splits_file` is provided, walks both train and test dirs
    and filters by membership in `splits_file[split]` — needed when prep
    used a stratified re-split (e.g. with --skip-clouds).
    """
    membership: set[str] | None = None
    if splits_file is not None and splits_file.exists():
        data = json.loads(splits_file.read_text())
        # splits.json keys (from prep) are "{run}__{dir_split}__{location}__{sNN}"
        membership = set(data.get(split, []))

    samples: list[Sample] = []
    for run in runs:
        run_dir = RUNS_DIR / run
        if not run_dir.is_dir():
            print(f"skip: {run_dir} (missing)")
            continue
        # If using splits_file, we need to scan both dir-splits since the
        # logical split no longer matches the dir layout.
        glob_pat = "*/*/*/annotation.json" if membership is not None else f"{split}/*/*/annotation.json"
        for ann_path in sorted(run_dir.glob(glob_pat)):
            sd = ann_path.parent
            dir_split = sd.parts[-3]
            location = sd.parent.name
            sample_basename = sd.name

            if membership is not None:
                key = f"{run}__{dir_split}__{location}__{sample_basename}"
                if key not in membership:
                    continue

            meta = json.loads((sd / "metadata.json").read_text())
            gt = json.loads(ann_path.read_text())
            samples.append(Sample(
                sample_id=f"{run}/{dir_split}/{location}/{sample_basename}",
                run=run,
                split=dir_split,
                location_id=location,
                location_name=meta.get("location_name", ""),
                tile_lon=float(meta["tile_lon"]),
                tile_lat=float(meta["tile_lat"]),
                date_t1=meta["actual_t1_datetime"],
                date_t0=meta["actual_t0_datetime"],
                rgb_t1_path=sd / "rgb_t1.png",
                swir_t1_path=sd / "swir_t1.png",
                rgb_t0_path=sd / "rgb_t0.png",
                swir_t0_path=sd / "swir_t0.png",
                ground_truth=gt,
            ))
    return samples


# --- backends ---

def predict_anthropic(sample: Sample, model: str) -> dict | None:
    from zamba_sat.labeling import label_via_api
    try:
        parsed = label_via_api(
            rgb_t1=sample.rgb_t1_path.read_bytes(),
            swir_t1=sample.swir_t1_path.read_bytes(),
            rgb_t0=sample.rgb_t0_path.read_bytes(),
            swir_t0=sample.swir_t0_path.read_bytes(),
            lat=sample.tile_lat,
            lon=sample.tile_lon,
            region_name=sample.location_name,
            date_t1=sample.date_t1,
            date_t0=sample.date_t0,
            model=model,
        )
        return parsed.annotation.model_dump()
    except Exception as e:
        return {"_error": str(e)}


def predict_local(sample: Sample, server_url: str, model: str) -> dict | None:
    """POST to an OpenAI-compatible /v1/chat/completions endpoint."""
    import httpx

    def b64(p: Path) -> str:
        return base64.standard_b64encode(p.read_bytes()).decode()

    user_text = render_user_text(
        lat=sample.tile_lat, lon=sample.tile_lon,
        region_name=sample.location_name,
        date_t1=sample.date_t1, date_t0=sample.date_t0,
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64(sample.rgb_t1_path)}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64(sample.swir_t1_path)}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64(sample.rgb_t0_path)}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64(sample.swir_t0_path)}"}},
                    {"type": "text", "text": user_text},
                ],
            },
        ],
        "max_tokens": 1024,
        "temperature": 0.0,
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(f"{server_url.rstrip('/')}/v1/chat/completions", json=payload)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
        return parse_response(raw).annotation.model_dump()
    except Exception as e:
        return {"_error": str(e)}


def predict_claude_code(sample: Sample, predictions_dir: Path) -> dict | None:
    """Read a pre-written prediction file.

    Looks for predictions in two layouts (in order):
      <dir>/<run>/<split>/<location>/<sNN_tNN>/annotation.json   (matches sample_id)
      <dir>/<run>/<location>/<sNN_tNN>/annotation.json           (legacy, no split level)
    """
    full = predictions_dir / sample.sample_id / "annotation.json"
    if full.exists():
        return json.loads(full.read_text())
    legacy = predictions_dir / sample.run / sample.location_id / Path(sample.sample_id).name / "annotation.json"
    if legacy.exists():
        return json.loads(legacy.read_text())
    return {"_error": f"prediction missing at {full} or {legacy}"}


# --- scoring ---

def score(predicted: dict | None, ground_truth: dict) -> dict[str, bool]:
    matches: dict[str, bool] = {}

    if predicted is None or "_error" in (predicted or {}):
        matches["valid_json"] = False
        for f in EVAL_FIELDS[1:]:
            matches[f] = False
        return matches

    matches["valid_json"] = True
    for f in EVAL_FIELDS[1:]:
        gt = ground_truth.get(f)
        pr = predicted.get(f)
        if f == "frame_quality":
            matches[f] = sorted(gt or []) == sorted(pr or [])
        else:
            matches[f] = gt == pr
    return matches


def render_report(results: list[SampleResult], meta: dict) -> str:
    n = len(results)
    if n == 0:
        return "# Evaluation\n\nNo samples.\n"
    per_field_correct = {f: 0 for f in EVAL_FIELDS}
    for r in results:
        for f, ok in r.field_matches.items():
            if ok:
                per_field_correct[f] += 1

    lines = ["# Evaluation report", ""]
    lines.append(f"- backend: `{meta['backend']}`")
    lines.append(f"- model: `{meta.get('model','-')}`")
    lines.append(f"- runs: `{', '.join(meta['runs'])}`")
    lines.append(f"- split: `{meta['split']}`")
    lines.append(f"- samples: {n}")
    lines.append(f"- timestamp: {meta['timestamp']}")
    lines.append("")
    lines.append("## Per-field accuracy")
    lines.append("")
    lines.append("| Field | Correct | Accuracy |")
    lines.append("|---|---|---|")
    for f in EVAL_FIELDS:
        c = per_field_correct[f]
        lines.append(f"| `{f}` | {c}/{n} | {c/n*100:.1f}% |")
    composite = sum(per_field_correct.values()) / (len(EVAL_FIELDS) * n)
    lines.append(f"\n**Composite accuracy:** {composite*100:.1f}%")
    lines.append("")
    lines.append("## Per-sample (change_pattern)")
    lines.append("")
    lines.append("| Sample | GT pattern | Predicted | Match |")
    lines.append("|---|---|---|---|")
    for r in results:
        gt = r.ground_truth.get("change_pattern")
        pr = (r.predicted or {}).get("change_pattern", "—")
        ok = "✓" if r.field_matches.get("change_pattern") else "✗"
        lines.append(f"| `{r.sample_id}` | {gt} | {pr} | {ok} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backend", required=True, choices=["anthropic", "local", "claude_code"])
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--split", default="test", choices=["train", "test"])
    p.add_argument("--model", default="claude-opus-4-7")
    p.add_argument("--server-url", default="http://localhost:8000")
    p.add_argument("--predictions-dir", type=Path)
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--out-dir", type=Path)
    p.add_argument("--splits-file", type=Path,
                   help="Optional path to splits.json (e.g. data/finetune/splits.json) — "
                        "filter samples by logical split rather than dir-split. "
                        "Use when prep applied a stratified re-split (--skip-clouds). "
                        "Default: dir-based split, for apples-to-apples baseline comparison.")
    args = p.parse_args()

    samples = load_samples(args.runs, args.split, splits_file=args.splits_file)
    if not samples:
        raise SystemExit(f"no samples found for runs={args.runs} split={args.split}")
    print(f"Loaded {len(samples)} samples for evaluation")

    if args.backend == "claude_code" and args.predictions_dir is None:
        raise SystemExit("--predictions-dir is required for backend=claude_code")

    predict_fn: Callable[[Sample], dict | None]
    if args.backend == "anthropic":
        predict_fn = lambda s: predict_anthropic(s, args.model)
    elif args.backend == "local":
        predict_fn = lambda s: predict_local(s, args.server_url, args.model)
    else:  # claude_code
        predict_fn = lambda s: predict_claude_code(s, args.predictions_dir)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_dir or (EVALS_DIR / timestamp)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[SampleResult] = []
    if args.backend == "claude_code":
        # Sequential — no API calls.
        for s in samples:
            pred = predict_fn(s)
            results.append(SampleResult(
                sample_id=s.sample_id, predicted=pred,
                ground_truth=s.ground_truth, field_matches=score(pred, s.ground_truth),
                error=(pred or {}).get("_error"),
            ))
            print(f"  {s.sample_id}: {sum(results[-1].field_matches.values())}/{len(EVAL_FIELDS)}")
    else:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {pool.submit(predict_fn, s): s for s in samples}
            for fut in as_completed(futures):
                s = futures[fut]
                pred = fut.result()
                results.append(SampleResult(
                    sample_id=s.sample_id, predicted=pred,
                    ground_truth=s.ground_truth, field_matches=score(pred, s.ground_truth),
                    error=(pred or {}).get("_error"),
                ))
                print(f"  {s.sample_id}: {sum(results[-1].field_matches.values())}/{len(EVAL_FIELDS)}")

    results.sort(key=lambda r: r.sample_id)
    meta = {
        "backend": args.backend,
        "model": args.model if args.backend != "claude_code" else "claude_code (manual)",
        "runs": args.runs,
        "split": args.split,
        "n_samples": len(samples),
        "timestamp": timestamp,
    }

    (out_dir / "results.json").write_text(json.dumps(
        [asdict(r) for r in results], indent=2, default=str
    ))
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    (out_dir / "report.md").write_text(render_report(results, meta))

    print(f"\nReport written to {out_dir}/report.md")


if __name__ == "__main__":
    main()
