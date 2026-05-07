# Evaluation report

- backend: `local`
- model: `zamba-deforestation-v2-Q8_0`
- runs: `wide_window, wide_window_v2`
- split: `test`
- samples: 6
- timestamp: 20260507T152544Z

## Per-field accuracy

| Field | Correct | Accuracy |
|---|---|---|
| `valid_json` | 4/6 | 66.7% |
| `deforestation_detected` | 0/6 | 0.0% |
| `change_pattern` | 3/6 | 50.0% |
| `trajectory_confidence` | 4/6 | 66.7% |
| `severity` | 0/6 | 0.0% |
| `clearing_type` | 0/6 | 0.0% |
| `area_bucket_t1` | 0/6 | 0.0% |
| `area_bucket_t0` | 0/6 | 0.0% |
| `active_operation` | 4/6 | 66.7% |
| `active_machinery_visible` | 4/6 | 66.7% |
| `smoke_or_fire_visible` | 4/6 | 66.7% |
| `recent_road_construction` | 4/6 | 66.7% |
| `frame_quality` | 3/6 | 50.0% |

**Composite accuracy:** 38.5%

## Per-sample (change_pattern)

| Sample | GT pattern | Predicted | Match |
|---|---|---|---|
| `wide_window/test/kindu_drc/s00_t01` | expansion | expansion | ✓ |
| `wide_window/test/kindu_drc/s03_t01` | expansion | expansion | ✓ |
| `wide_window_v2/test/kindu_drc/s02_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/yangambi_drc/s02_t03` | stable | — | ✗ |
| `wide_window_v2/train/yangambi_drc/s00_t01` | expansion | — | ✗ |
| `wide_window_v2/train/yangambi_drc/s03_t01` | stable | expansion | ✗ |
