# Evaluation report

- backend: `local`
- model: `zamba-deforestation-v3-Q8_0`
- runs: `wide_window, wide_window_v2`
- split: `test`
- samples: 36
- timestamp: 20260507T160241Z

## Per-field accuracy

| Field | Correct | Accuracy |
|---|---|---|
| `valid_json` | 21/36 | 58.3% |
| `deforestation_detected` | 16/36 | 44.4% |
| `change_pattern` | 12/36 | 33.3% |
| `trajectory_confidence` | 14/36 | 38.9% |
| `severity` | 4/36 | 11.1% |
| `clearing_type` | 16/36 | 44.4% |
| `area_bucket_t1` | 4/36 | 11.1% |
| `area_bucket_t0` | 13/36 | 36.1% |
| `active_operation` | 21/36 | 58.3% |
| `active_machinery_visible` | 21/36 | 58.3% |
| `smoke_or_fire_visible` | 21/36 | 58.3% |
| `recent_road_construction` | 21/36 | 58.3% |
| `frame_quality` | 12/36 | 33.3% |

**Composite accuracy:** 41.9%

## Per-sample (change_pattern)

| Sample | GT pattern | Predicted | Match |
|---|---|---|---|
| `wide_window/test/kindu_drc/s00_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s01_t01` | expansion | expansion | ✓ |
| `wide_window/test/kindu_drc/s02_t01` | expansion | expansion | ✓ |
| `wide_window/test/kindu_drc/s03_t01` | expansion | — | ✗ |
| `wide_window/test/lusambo_drc/s00_t01` | expansion | expansion | ✓ |
| `wide_window/test/lusambo_drc/s01_t01` | expansion | expansion | ✓ |
| `wide_window/test/lusambo_drc/s02_t01` | cloud_artifact | expansion | ✗ |
| `wide_window/test/lusambo_drc/s03_t01` | cloud_artifact | expansion | ✗ |
| `wide_window/test/yangambi_drc/s00_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s01_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s02_t01` | cloud_artifact | expansion | ✗ |
| `wide_window/test/yangambi_drc/s03_t01` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t02` | cloud_artifact | expansion | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t03` | expansion | — | ✗ |
| `wide_window_v2/test/kindu_drc/s01_t02` | cloud_artifact | expansion | ✗ |
| `wide_window_v2/test/kindu_drc/s01_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/kindu_drc/s02_t02` | cloud_artifact | expansion | ✗ |
| `wide_window_v2/test/kindu_drc/s02_t03` | expansion | — | ✗ |
| `wide_window_v2/test/kindu_drc/s03_t02` | cloud_artifact | expansion | ✗ |
| `wide_window_v2/test/kindu_drc/s03_t03` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s00_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s00_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s01_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s01_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s02_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s02_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s03_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s03_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/yangambi_drc/s00_t02` | expansion | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s00_t03` | expansion | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s01_t02` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s01_t03` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t02` | stable | expansion | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t03` | stable | expansion | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t02` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t03` | stable | — | ✗ |
