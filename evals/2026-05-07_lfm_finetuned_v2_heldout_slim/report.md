# Evaluation report

- backend: `local`
- model: `zamba-deforestation-v2-Q8_0`
- runs: `wide_window, wide_window_v2`
- split: `test`
- samples: 6
- timestamp: 20260507T182840Z

## Per-field accuracy

| Field | Correct | Accuracy |
|---|---|---|
| `valid_json` | 3/6 | 50.0% |
| `change_pattern` | 1/6 | 16.7% |
| `trajectory_confidence` | 3/6 | 50.0% |
| `active_operation` | 3/6 | 50.0% |
| `active_machinery_visible` | 3/6 | 50.0% |
| `smoke_or_fire_visible` | 3/6 | 50.0% |
| `recent_road_construction` | 3/6 | 50.0% |
| `frame_quality` | 1/6 | 16.7% |

**Composite accuracy:** 41.7%

## Per-sample (change_pattern)

| Sample | GT pattern | Predicted | Match |
|---|---|---|---|
| `wide_window/test/kindu_drc/s00_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s03_t01` | expansion | — | ✗ |
| `wide_window_v2/test/kindu_drc/s02_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/yangambi_drc/s02_t03` | stable | expansion | ✗ |
| `wide_window_v2/train/yangambi_drc/s00_t01` | expansion | — | ✗ |
| `wide_window_v2/train/yangambi_drc/s03_t01` | stable | expansion | ✗ |
