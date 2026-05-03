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
  emits an XML chain-of-thought (`<frame_descriptions>`, `<change_analysis>`,
  `<final_pattern>`, `<json>`). The JSON block is validated against a
  Pydantic schema covering `change_pattern`, `severity`, `clearing_type`,
  area buckets, and `frame_quality` flags.

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
