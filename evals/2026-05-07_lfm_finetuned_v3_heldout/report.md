# Evaluation report

- backend: `local`
- model: `zamba-deforestation-v3-Q8_0`
- runs: `wide_window, wide_window_v2`
- split: `test`
- samples: 6
- timestamp: 20260507T160415Z

## Per-field accuracy

| Field | Correct | Accuracy |
|---|---|---|
| `valid_json` | 2/6 | 33.3% |
| `deforestation_detected` | 2/6 | 33.3% |
| `change_pattern` | 0/6 | 0.0% |
| `trajectory_confidence` | 2/6 | 33.3% |
| `severity` | 0/6 | 0.0% |
| `clearing_type` | 2/6 | 33.3% |
| `area_bucket_t1` | 2/6 | 33.3% |
| `area_bucket_t0` | 2/6 | 33.3% |
| `active_operation` | 2/6 | 33.3% |
| `active_machinery_visible` | 2/6 | 33.3% |
| `smoke_or_fire_visible` | 2/6 | 33.3% |
| `recent_road_construction` | 2/6 | 33.3% |
| `frame_quality` | 0/6 | 0.0% |

**Composite accuracy:** 25.6%

## Per-sample (change_pattern)

| Sample | GT pattern | Predicted | Match |
|---|---|---|---|
| `wide_window/test/kindu_drc/s00_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s03_t01` | expansion | — | ✗ |
| `wide_window_v2/test/kindu_drc/s02_t03` | expansion | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t03` | stable | expansion | ✗ |
| `wide_window_v2/train/yangambi_drc/s00_t01` | expansion | — | ✗ |
| `wide_window_v2/train/yangambi_drc/s03_t01` | stable | expansion | ✗ |
