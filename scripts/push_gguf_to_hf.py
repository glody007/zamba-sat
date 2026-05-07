"""Push a fine-tuned GGUF model pair to a HuggingFace model repository.

Mirrors `wildfire-prevention/scripts/push_gguf_to_hf.py` from the Liquid
cookbook. Uploads the backbone GGUF and mmproj GGUF produced by
quantize.py, plus a model card so end users can reproduce eval results
without fine-tuning.

Usage:
    uv run scripts/push_gguf_to_hf.py \\
        --backbone ./outputs/zamba-deforestation-v2-Q8_0.gguf \\
        --mmproj   ./outputs/mmproj-zamba-deforestation-v2-Q8_0.gguf \\
        --repo     glody007/zamba-deforestation-detector

    # Private repo
    uv run scripts/push_gguf_to_hf.py \\
        --backbone ./outputs/zamba-deforestation-v2-Q8_0.gguf \\
        --mmproj   ./outputs/mmproj-zamba-deforestation-v2-Q8_0.gguf \\
        --repo     glody007/zamba-deforestation-detector \\
        --private
"""

import argparse
import sys
from pathlib import Path


MODEL_CARD_TEMPLATE = """\
---
base_model: LiquidAI/LFM2.5-VL-450M
language:
- en
license: other
tags:
- gguf
- vlm
- deforestation
- satellite
- sentinel-2
- congo-basin
- earth-observation
---

# zamba-deforestation-detector — LFM2.5-VL-450M (GGUF)

Fine-tuned from [LiquidAI/LFM2.5-VL-450M](https://huggingface.co/LiquidAI/LFM2.5-VL-450M)
on simulated Sentinel-2 RGB+SWIR change-detection pairs over the Congo
Basin (DRC), to flag near-real-time forest clearing on a 90-day window.
Companion to the [`zamba-sat`](https://github.com/glody007/zamba-sat)
repo, built for the AI in Space hackathon (DPhi Space × Liquid AI).

Given **four** images per sample — RGB(t-1), SWIR(t-1), RGB(t-0),
SWIR(t-0) — and a small text block (lat/lon, dates, region name), the
model emits a chain-of-thought followed by a JSON change-detection
record:

```json
{{
  "change_pattern": "expansion",     // expansion | stable | clearing | regrowth | cloud_artifact
  "trajectory_confidence": "medium", // low | medium | high
  "active_operation": false,
  "active_machinery_visible": false,
  "smoke_or_fire_visible": false,
  "recent_road_construction": false,
  "frame_quality": ["good", "good"]
}}
```

The full XML chain-of-thought wraps the JSON with `<frame_descriptions>`,
`<change_analysis>`, `<final_pattern>`, and `<json>` blocks — see the
[`zamba-sat` README](https://github.com/glody007/zamba-sat#xml-cot)
for the schema.

## Eval results

Evaluated on the held-out subset of the
[`glody007/zamba-sat-congo-deforestation`](https://huggingface.co/datasets/glody007/zamba-sat-congo-deforestation)
dataset (90-day window, `wide_window` + `wide_window_v2` runs). Ground
truth from `claude-opus-4-7`.

| field | LFM2.5-VL-450M (base, Q8_0) | LFM2.5-VL-450M Q8_0 (fine-tuned, this model) |
|---|---|---|
| valid_json | 0% | 67% |
| change_pattern (expansion / stable / cloud_artifact) | 0% | 50% |
| trajectory_confidence | 0% | 67% |
| **composite (13 fields)** | **0.0%** | **38.5%** |

Held-out test set is small (N=6) — the headline movement is the base
model emitting placeholder prose vs the fine-tune emitting
schema-compliant JSON with correct expansion/stable discrimination.
The base-model 0% is on the dir-test (N=36); see
[zamba-sat/evals/EXPERIMENTS.md](https://github.com/glody007/zamba-sat/blob/main/evals/EXPERIMENTS.md)
for the full experiment log including v1 (cloud-class collapse) and v3
(overfitting boundary).

## Files

Running inference with a VLM in llama.cpp requires two GGUF files:

| file | description |
|---|---|
| `{backbone_name}` | Language model backbone (Q8_0) |
| `{mmproj_name}` | Vision tower + multimodal projector (F16) |

## Usage

### llama-server

```bash
llama-server \\
    -m {backbone_name} \\
    --mmproj {mmproj_name} \\
    --jinja --port 8000
```

### Reproduce eval results

Clone [`zamba-sat`](https://github.com/glody007/zamba-sat) and run:

```bash
git clone https://github.com/glody007/zamba-sat
cd zamba-sat
uv sync

# (1) Re-prep the dataset locally — same stratified split used for training.
uv run scripts/prepare_finetune.py \\
    --runs wide_window wide_window_v2 \\
    --output data/finetune \\
    --skip-clouds

# (2) Eval the fine-tune behind llama-server (started in another shell with
# the GGUFs from this repo).
uv run scripts/evaluate.py --backend local \\
    --server-url http://localhost:8000 \\
    --model zamba-deforestation-Q8_0 \\
    --runs wide_window wide_window_v2 --split test \\
    --splits-file data/finetune/splits.json
```

## Training details

- **Base:** `LiquidAI/LFM2.5-VL-450M`
- **Method:** full SFT (no LoRA), via `leap-finetune` on Modal H100×1
- **Data:** 24 stratified train rows after `--skip-clouds`
  (17 expansion + 7 stable); held-out test = 6 rows (4 expansion + 2 stable)
- **Hyperparameters:** 5 effective epochs / 12 grad steps,
  effective batch size 8 (2 × 4 grad accum), LR `2e-5`, cosine,
  warmup 0.03, seed 42

This is the **v2** checkpoint, which on internal evals beat both v1
(cloud-class collapse from training without `--skip-clouds`) and v3
(overfit at 8 ep / ~25 grad steps). v2 is the apparent sweet spot given
the dataset size; the next step before further training is to collect
more `stable` labels.
"""


def make_model_card(backbone_name: str, mmproj_name: str) -> str:
    return MODEL_CARD_TEMPLATE.format(
        backbone_name=backbone_name,
        mmproj_name=mmproj_name,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push a fine-tuned GGUF model pair to HuggingFace."
    )
    parser.add_argument("--backbone", required=True, metavar="PATH",
                        help="Path to the backbone GGUF file.")
    parser.add_argument("--mmproj", required=True, metavar="PATH",
                        help="Path to the mmproj GGUF file.")
    parser.add_argument("--repo", required=True, metavar="REPO_ID",
                        help="HuggingFace model repo to create/push to "
                             "(e.g. glody007/zamba-deforestation-detector).")
    parser.add_argument("--private", action="store_true",
                        help="Create the repo as private (default: public).")
    args = parser.parse_args()

    backbone = Path(args.backbone)
    mmproj = Path(args.mmproj)

    for path in (backbone, mmproj):
        if not path.is_file():
            print(f"File not found: {path}")
            sys.exit(1)

    from huggingface_hub import HfApi

    api = HfApi()

    print(f"Creating repo: {args.repo} ...")
    api.create_repo(repo_id=args.repo, repo_type="model",
                    private=args.private, exist_ok=True)

    print(f"Uploading backbone: {backbone.name} ...")
    api.upload_file(
        path_or_fileobj=str(backbone),
        path_in_repo=backbone.name,
        repo_id=args.repo,
        repo_type="model",
    )

    print(f"Uploading mmproj: {mmproj.name} ...")
    api.upload_file(
        path_or_fileobj=str(mmproj),
        path_in_repo=mmproj.name,
        repo_id=args.repo,
        repo_type="model",
    )

    print("Uploading model card ...")
    card = make_model_card(backbone.name, mmproj.name)
    api.upload_file(
        path_or_fileobj=card.encode(),
        path_in_repo="README.md",
        repo_id=args.repo,
        repo_type="model",
    )

    print()
    print(f"Done. Model at https://huggingface.co/{args.repo}")


if __name__ == "__main__":
    main()
