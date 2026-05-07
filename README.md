# zamba-sat

Congo Basin deforestation detection — data generation and labeling pipeline
for the **AI in Space** hackathon (DPhi Space × Liquid AI).

## Problem

The Congo Basin is the second-largest tropical rainforest on Earth and one of
the planet's largest terrestrial carbon sinks. It is also under sustained
pressure from logging-road expansion, slash-and-burn agriculture, artisanal
mining, and infrastructure encroachment along park boundaries. Manual
satellite review by rangers and analysts does not scale to the area or the
revisit cadence needed to catch clearings while they are still small enough
to act on.

We want a small vision-language model that can run **on board a satellite**
(target: Liquid `LFM2.5-VL-450M`) and emit a structured deforestation
annotation directly from a pair of Sentinel-2 acquisitions, so only the
relevant frames and labels need to be downlinked. That requires a labeled
dataset of Congo Basin two-frame change pairs that the small model can be
fine-tuned on.

## Approach

Two-frame temporal change detection over fixed Congo Basin sites:

- For each (location, spatial sub-tile, temporal sample) we fetch four
  Sentinel-2 frames via [SimSat](https://github.com/DPhi-Space/SimSat):

  | frame | bands | role |
  |---|---|---|
  | `rgb_t1.png`  | B4-B3-B2 (red, green, blue)         | natural colour, ~30 days ago |
  | `swir_t1.png` | B11-B8A-B4 (swir16, nir08, red)     | vegetation moisture, ~30 days ago |
  | `rgb_t0.png`  | B4-B3-B2                            | natural colour, current |
  | `swir_t0.png` | B11-B8A-B4                          | vegetation moisture, current |

  RGB shows what a human sees; SWIR makes vegetation moisture and bare/burnt
  ground pop, which is what catches recent clearings under partial haze.

### What the model sees

Two real samples from `dry_season/salonga_north_drc`. Each row is one
(location, sub-tile, temporal-sample) — four frames, one label.

**Stable forest** (`change_pattern: stable`) — `dry_season/salonga_north_drc/s02_t00`

| RGB t-1 (~30 d ago) | RGB t-0 (now) | SWIR t-1 | SWIR t-0 |
|---|---|---|---|
| ![](docs/examples/stable_rgb_t1.png) | ![](docs/examples/stable_rgb_t0.png) | ![](docs/examples/stable_swir_t1.png) | ![](docs/examples/stable_swir_t0.png) |

t-1 RGB is uniform dark-green canopy. t-0 RGB looks dark and partly water-like
under haze, but SWIR t-0 shows the same bright-green vegetation texture as
SWIR t-1 — that confirmation across bands is exactly why we fetch both.

**Agricultural expansion** (`change_pattern: expansion`) — `yangambi_dry/yangambi_drc/s00_t01`

| RGB t-1 | RGB t-0 | SWIR t-1 | SWIR t-0 |
|---|---|---|---|
| ![](docs/examples/expansion_rgb_t1.png) | ![](docs/examples/expansion_rgb_t0.png) | ![](docs/examples/expansion_swir_t1.png) | ![](docs/examples/expansion_swir_t0.png) |

This is the off-park frontier near Yangambi. RGB shows a fragmented
forest-agriculture mosaic in both frames; the brown/tan patches look broadly
similar to a casual eye. SWIR is the tell — the orange/red bare-earth
signal is visibly more extensive and contiguous in t-0 than t-1, especially
on the right and lower portions of the frame. Diffuse blob-shaped expansion
consistent with smallholder slash-and-burn continuing into the dry season.
This is exactly the kind of positive label the on-board model needs to
learn to flag.

**Cloud-blocked frame** (`change_pattern: cloud_artifact`) — `dry_season/salonga_north_drc/s03_t01`

| RGB t-1 | RGB t-0 | SWIR t-1 | SWIR t-0 |
|---|---|---|---|
| ![](docs/examples/cloud_rgb_t1.png) | ![](docs/examples/cloud_rgb_t0.png) | ![](docs/examples/cloud_swir_t1.png) | ![](docs/examples/cloud_swir_t0.png) |

t-1 is clean forest, t-0 is solid cloud. The conservative rule says: do not
guess. Label `cloud_artifact` and exclude from positive/negative training
signal. Roughly half of Congo Basin acquisitions look like this even in the
dry season.

- A larger oracle VLM (Claude `claude-opus-4-7`) reads the four frames and
  emits an **XML chain-of-thought** — reasoning split into named sections
  wrapped in tags, so each part is parseable and auditable rather than
  buried in prose:

  ```xml
  <frame_descriptions>
  Frame t-1: ...one sentence describing land cover...
  Frame t-0: ...same...
  </frame_descriptions>

  <change_analysis>
  ...did anything change? what? where in the frame?...
  </change_analysis>

  <final_pattern>
  Pattern: stable | clearing | expansion | regrowth | cloud_artifact
  Reasoning: ...one sentence...
  </final_pattern>

  <json>
  { "deforestation_detected": false, "change_pattern": "stable", ... }
  </json>
  ```

  Why this format over plain JSON:
    - **Forces grounding before classification.** The model must describe
      each frame and analyse the change *before* picking a label, which
      stops small VLMs from jumping to a guess.
    - **Per-section debuggability.** When a label looks wrong, the
      `<frame_descriptions>` and `<change_analysis>` sections survive in
      `annotation_reasoning.txt` so we can tell whether the model misread
      the imagery or picked the wrong category.
    - **Strict parser = clean dataset.** `src/zamba_sat/schema.py::parse_response`
      extracts each tag, validates the `<json>` block against a Pydantic
      schema (`change_pattern`, `severity`, `clearing_type`, area buckets,
      `frame_quality`), and rejects responses that don't conform.

  The tradeoff: a base un-fine-tuned 450M VLM can't follow this format
  reliably. The whole point of fine-tuning is to teach it to.

- Sampling is deliberate, not random: an `NxN` spatial grid centred on each
  location, bin-centre temporal placement across the configured window, and
  a train/test split via temporal cutoff to avoid Sentinel-2 5-day-revisit
  leakage between splits.

- The labeled dataset is then formatted for `leap-finetune` and used to
  supervise the small on-board VLM.

The hard part is **not** the modeling — it is producing a Congo-specific
labeled set that does not collapse to `cloud_artifact` (year-round haze) or
`stable` (interior-of-park bias). Site choice, dry-season targeting, and a
prompt that explicitly warns against false positives (cloud, dry-season
colour shift, tile boundaries, swamp flooding) are doing most of the work.

## Status

### Dataset

Labeled v0 is published at:

**https://huggingface.co/datasets/glody007/zamba-sat-congo-deforestation**

**72 labeled samples**, all on a single 90-day temporal window
(`t1 → t0 = 90 days`). Distribution: **21 expansion / 9 stable / 42
cloud_artifact**. Sites: Yangambi (DRC, smallholder agricultural mosaic),
Kindu (Maniema, GFW-cited 2024 top-3 deforestation province), Lusambo
(Sankuru, GFW-cited 2024 top-2). Each row carries the four frames as
`Image()` columns plus metadata, the full annotation JSON, and the
chain-of-thought reasoning.

The dataset is uniform-window-only by design: 30-day samples produced
mostly cloud / stable labels because individual clearings are too small
to register at 30-day cadence on 10 km tiles. The 90-day window catches
accumulated dry-season change at all three sites. Earlier 30-day
exploration runs are kept locally under `data/runs/` but are not part of
the published dataset.

```python
from datasets import load_dataset
ds = load_dataset("glody007/zamba-sat-congo-deforestation")
```

### Done

- [x] SimSat client with 5xx retry / 4xx → `ImageUnavailable` and structured
      `SentinelImage` (metadata parsed from response header).
- [x] Spatial grid + bin-centre temporal sampler + train/test temporal split.
- [x] Pydantic schema with strict `Literal` enums and XML-section parser.
- [x] Congo-specific oracle prompt (clearing signatures, false-positive
      warnings, structured CoT).
- [x] Generation CLI with cloud-cover retry (shifts target date back 5 days
      on >60% cloud, max 3 attempts) and concurrency knob.
- [x] Validation script (`check_samples.py`) reporting completeness and
      pattern distribution.
- [x] 6 configured Congo Basin sites — 5 protected areas plus 1 off-park
      frontier (`yangambi_drc`) chosen to surface positive labels.
- [x] Three labeled runs landed: `smoke_test` (8/8, all `cloud_artifact` —
      wet-season blanket), `dry_season` (6/8 fetched, 3 `stable` + 3
      `cloud_artifact`), `lope_dry` (8/8 fetched, mostly cloud-saturated —
      not worth labeling).
- [x] Tests for the schema parser (5 cases passing).

### Next

- [ ] **Fine-tune `LFM2.5-VL-450M`** on the labeled JSONL via `leap-finetune`.
      Everything upstream of this step is now in place; the fine-tune is the
      remaining work.

## Prerequisites

- `uv` (Python ≥ 3.11)
- Docker (to run SimSat)
- Anthropic API key — **only if** you use the `--label` flag. The default
  workflow leaves labeling to a separate step.

## Setup

```bash
# 1. Clone and start SimSat in a separate terminal
git clone https://github.com/DPhi-Space/SimSat.git
cd SimSat && MAPBOX_ACCESS_TOKEN=dummy docker compose up

# 2. Open http://localhost:8000, set start time to e.g. 2026-04-15T12:00:00Z,
#    and click Start.

# 3. In this repo:
uv sync
cp .env.example .env   # only edit if you plan to use --label
```

## Generate samples

Small validation run (4 samples, 1 location):

```bash
uv run scripts/generate_samples.py \
    --start-date 2025-09-01 --end-date 2026-04-01 \
    --location salonga_north_drc \
    --n-temporal-samples 2 --n-spatial-tiles 4 \
    --size-km 10.0
```

Full run across all configured locations:

```bash
uv run scripts/generate_samples.py \
    --start-date 2025-06-01 --end-date 2026-04-01 \
    --n-temporal-samples 8 --n-spatial-tiles 4 \
    --size-km 10.0 --concurrency 3
```

Output lands in `data/runs/<run_name>/{train,test}/<location_id>/<sNN_tNN>/`
with `rgb_t1.png swir_t1.png rgb_t0.png swir_t0.png metadata.json` per sample.

## Labeling

Two paths produce the same `annotation.json` schema; pick one.

### Option A — Claude in this repo's conversation (free)

```bash
uv run scripts/label_pending.py    # list sample dirs without annotation.json
```

Then in your Claude Code session, ask Claude to read each pending sample's
4 PNGs and write `annotation.json` per the prompt in `src/zamba_sat/labeling.py`.

### Option B — Anthropic API (costs money)

```bash
export ANTHROPIC_API_KEY=sk-...
uv run scripts/generate_samples.py ... --label
```

Either path validates output against the Pydantic schema in
`src/zamba_sat/schema.py`. Schema violations raise rather than write a
half-baked annotation.

## Validate a run

```bash
uv run scripts/check_samples.py            # most recent run
uv run scripts/check_samples.py dry_season
```

Reports per-run sample counts, completeness, label coverage, and the
distribution of `change_pattern` values.

## Evaluation

`scripts/evaluate.py` runs a model against the labeled test split and
scores its predictions field-by-field against the ground-truth JSON. Three
backends, same scoring path:

| Backend | What it is | When to use |
|---|---|---|
| `anthropic` | Calls `claude-opus-4-7` via the Anthropic API | Oracle re-labeling baseline (label-noise upper bound). Costs money. |
| `local` | POSTs to an OpenAI-compatible `/v1/chat/completions` server (e.g. llama.cpp serving the fine-tuned `LFM2.5-VL-450M` GGUF) | Deployment target — measures how well the small on-board model matches the oracle. |
| `claude_code` | Reads pre-written predictions from `--predictions-dir` | Lets Claude in-conversation produce predictions for free, then scores them. |

What gets scored (13 fields per sample):

```
valid_json, deforestation_detected, change_pattern,
trajectory_confidence, severity, clearing_type,
area_bucket_t1, area_bucket_t0,
active_operation, active_machinery_visible,
smoke_or_fire_visible, recent_road_construction,
frame_quality   # set-equality; others are exact match
```

Each run writes `evals/<timestamp>/`:

```
report.md      # per-field accuracy table + per-sample change_pattern column
results.json   # per-sample predictions and field-match flags
meta.json      # backend, model, runs, split, n_samples, timestamp
```

### Examples

```bash
# Oracle baseline — Anthropic re-labels its own annotations
ANTHROPIC_API_KEY=sk-... uv run scripts/evaluate.py \
    --backend anthropic \
    --runs wide_window wide_window_v2 --split test

# Fine-tuned LFM behind a llama.cpp server
uv run scripts/evaluate.py --backend local \
    --server-url http://localhost:8000 \
    --model lfm2-vl-450m-deforestation-q8 \
    --runs wide_window wide_window_v2 --split test

# Score predictions Claude wrote in this conversation
uv run scripts/evaluate.py --backend claude_code \
    --predictions-dir evals/2026-05-05_claude/predictions \
    --runs wide_window wide_window_v2 --split test
```

The published 90-day dataset has **36 test samples** across Yangambi,
Kindu, and Lusambo. Anthropic-vs-Anthropic agreement gives you the ceiling
the fine-tuned LFM should aspire to.

### Results so far

| Run | Backend | Model | Test set | Composite | `valid_json` | `change_pattern` | Report |
|---|---|---|---|---|---|---|---|
| 2026-05-05 | `claude_code` | Claude Opus 4.7 (in-session) | dir-test (36) | **96.6%** | 100% | 100% | [report](evals/2026-05-05_claude_code/report.md) |
| 2026-05-06 | `local`       | `LFM2.5-VL-450M` (no fine-tune) | dir-test (36) | **0.0%** | 0% | 0% | [report](evals/2026-05-06_lfm_base/report.md) |
| 2026-05-07 | `local`       | v1 — full SFT, 4.5 ep, no `--skip-clouds` (36 train) | dir-test (36) | **44.4%** | 72% | 17% | [report](evals/2026-05-07_lfm_finetuned/report.md) |
| 2026-05-07 | `local`       | v2 — full SFT, 4 ep, `--skip-clouds` + stratified (24 train) | dir-test (36)¹ | **28.8%** | 44% | 31% | [report](evals/2026-05-07_lfm_finetuned_v2_dirtest/report.md) |
| 2026-05-07 | `local`       | v2 — same checkpoint                                            | held-out (6)² | **38.5%** | 67% | **50%** | [report](evals/2026-05-07_lfm_finetuned_v2_heldout/report.md) |

¹ *Not directly comparable to v1: stratified re-split moved many original-dir-test samples into v2's train set (data leakage on dir-test).*
² *6-sample honest held-out from `data/finetune/splits.json`; this is the only test set v2 truly didn't see.*

**Remark on v1 (no `--skip-clouds`).** Big structural win: `valid_json`
went 0% → 72% — the base model was emitting prose with placeholder text
and no `<json>` block; the fine-tune learned the XML-CoT + JSON schema.
But `change_pattern` is only 17% because v1 class-collapsed onto
`cloud_artifact`: of 36 train rows, ~32 were `cloud_artifact`, so the
model learned "when in doubt, say cloud." For uncertain inputs it
sometimes degenerated into a self-similar JSON loop like
`{"cloud_artifact_confidence_range_range": …}`.

**Remark on v2 (`--skip-clouds` + stratified split).** The headline
movement is `change_pattern`: **17% → 50%** on the honest held-out test
(3/3 expansion samples called correctly; misses on 2 parse-fails and
1 stable→expansion). The composite drop is real but mostly from `valid_json`
sliding 72% → 67% — v2 is undertrained (only 12 grad steps over 4 epochs
on 24 rows) and emits inconsistent JSON: it picks `change_pattern: expansion`
correctly but writes `deforestation_detected: false` in the same block,
or skips `severity`/`clearing_type` entirely. Fields that depend on
parseable JSON (`severity`, `clearing_type`, `area_bucket_*`) are 0% on
held-out; the change-detection signal itself is real and learning.

Next iteration: more grad steps. Either bump `num_train_epochs` to ~10
or drop `gradient_accumulation_steps` to 2 (effective batch 4, ~30 steps
over 5 epochs). Goal: stabilise the JSON schema while preserving the
expansion/stable discrimination.

## Fine-tuning

We follow the Liquid `leap-finetune` workflow. Step 1 happens in this
repo; steps 2–4 happen on Modal (or any GPU host).

### 1. Convert labeled samples to leap-finetune JSONL

```bash
uv run scripts/prepare_finetune.py \
    --runs wide_window wide_window_v2 \
    --output data/finetune
```

Outputs:

```
data/finetune/
├── zamba_train.jsonl     # 36 rows, one per train sample
├── zamba_test.jsonl      # 36 rows, one per test sample
└── images/               # 288 PNGs (4 per sample, flattened filenames)
```

Each JSONL row's `messages` array follows the leap-finetune VLM SFT format:

- `user.content[0..3]`: four `{"type":"image","image":"<filename>"}` blocks for `rgb_t1`, `swir_t1`, `rgb_t0`, `swir_t0`
- `user.content[4]`: `{"type":"text","text":"<SYSTEM_PROMPT>\n\n<per-sample user text>"}`
- `assistant.content[0]`: `{"type":"text","text":"<XML-CoT response>"}` reconstructed from `annotation_reasoning.txt` + `annotation.json`

Use `--skip-clouds` to drop `cloud_artifact` rows (42 of 72) and train
only on the 30 signal samples.

### 2. Upload to Modal volume + run leap-finetune

Config: [`configs/zamba_finetune_modal.yaml`](configs/zamba_finetune_modal.yaml).
Mirrors `wildfire-prevention/configs/wildfire_finetune_modal.yaml` —
`vlm_sft` over `LFM2.5-VL-450M`, full fine-tune (LoRA off), 5 epochs,
H100×1 on Modal, eval block pointed at our test JSONL.

```bash
# 1. Create the Modal volume and upload the prepared data
modal volume create zamba-deforestation
modal volume put zamba-deforestation data/finetune /outputs/data/zamba

# 2. Kick off training
leap-finetune train --config configs/zamba_finetune_modal.yaml
```

Outputs (checkpoints, eval metrics, logs) land in
`/outputs/zamba-deforestation/<run-id>/` on the volume. Pull a checkpoint
back with `modal volume get zamba-deforestation <path>`.

### 3. Quantize to GGUF and push to HF

After training, convert the LoRA-merged checkpoint to GGUF (Q8_0 to
match our baseline eval) and push to a new HF model repo.

### 4. Re-evaluate against base baseline

Spin up `llama-server` against the fine-tuned GGUF and re-run:

```bash
uv run scripts/evaluate.py --backend local \
    --server-url http://localhost:8080 \
    --model glody007/zamba-deforestation-detector \
    --runs wide_window wide_window_v2 --split test
```

The composite-accuracy delta from the 0% LFM-base baseline in
`evals/2026-05-06_lfm_base/report.md` is the headline result.

## Tests

```bash
uv run pytest
```

## Project layout

```
zamba-sat/
├── configs/
│   ├── locations.yaml           # 6 Congo Basin sites (5 parks + 1 frontier)
│   └── data_generation.yaml     # default sampling params
├── src/zamba_sat/
│   ├── locations.py             # YAML loader + filtering
│   ├── simsat_client.py         # httpx client, RGB+SWIR helpers
│   ├── temporal_sampler.py      # spatial grid, t0 dates, t1=t0-30d
│   ├── schema.py                # Pydantic + XML response parser
│   ├── labeling.py              # SYSTEM_PROMPT + Anthropic client
│   ├── overlays.py              # WDPA stub
│   └── hf_uploader.py           # HF push stub
├── scripts/
│   ├── generate_samples.py      # main entry — fetch + (optional) label
│   ├── label_pending.py         # list samples missing annotation.json
│   ├── check_samples.py         # run validation
│   ├── evaluate.py              # score predictions vs ground truth
│   ├── upload_to_hf.py          # push labeled runs to HuggingFace
│   └── prepare_finetune.py      # leap-finetune JSONL stub
└── tests/
    └── test_schema.py
```

## Caveats

- SimSat's Sentinel API is slow. Concurrency=3 is a safe default.
- Sentinel-2 has 5-day revisit at the equator; with `t1_offset_days=30` you
  should get distinct acquisitions, but adjacent samples may overlap.
- The Congo Basin is cloud-blanketed most of the year. Target the dry season
  (roughly June–September) to get usable frames, and even then expect a
  meaningful fraction of `cloud_artifact` labels.
- The labeler can mistake dry-season canopy colour shift for clearing. The
  system prompt warns against this; test runs should include some dry-season
  tiles to verify it sticks.
- WDPA / `in_protected_zone` is currently a stub.
