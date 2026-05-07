# Evaluation report

- backend: `local`
- model: `zamba-deforestation-v2-Q8_0`
- runs: `wide_window, wide_window_v2`
- split: `test`
- samples: 36
- timestamp: 20260507T152321Z

## Per-field accuracy

| Field | Correct | Accuracy |
|---|---|---|
| `valid_json` | 16/36 | 44.4% |
| `deforestation_detected` | 4/36 | 11.1% |
| `change_pattern` | 11/36 | 30.6% |
| `trajectory_confidence` | 12/36 | 33.3% |
| `severity` | 7/36 | 19.4% |
| `clearing_type` | 3/36 | 8.3% |
| `area_bucket_t1` | 3/36 | 8.3% |
| `area_bucket_t0` | 3/36 | 8.3% |
| `active_operation` | 16/36 | 44.4% |
| `active_machinery_visible` | 16/36 | 44.4% |
| `smoke_or_fire_visible` | 16/36 | 44.4% |
| `recent_road_construction` | 16/36 | 44.4% |
| `frame_quality` | 12/36 | 33.3% |

**Composite accuracy:** 28.8%

## Per-sample (change_pattern)

| Sample | GT pattern | Predicted | Match |
|---|---|---|---|
| `wide_window/test/kindu_drc/s00_t01` | expansion | expansion | ✓ |
| `wide_window/test/kindu_drc/s01_t01` | expansion | expansion | ✓ |
| `wide_window/test/kindu_drc/s02_t01` | expansion | expansion | ✓ |
| `wide_window/test/kindu_drc/s03_t01` | expansion | expansion | ✓ |
| `wide_window/test/lusambo_drc/s00_t01` | expansion | expansion | ✓ |
| `wide_window/test/lusambo_drc/s01_t01` | expansion | — | ✗ |
| `wide_window/test/lusambo_drc/s02_t01` | cloud_artifact | expansion | ✗ |
| `wide_window/test/lusambo_drc/s03_t01` | cloud_artifact | expansion | ✗ |
| `wide_window/test/yangambi_drc/s00_t01` | cloud_artifact | expansion | ✗ |
| `wide_window/test/yangambi_drc/s01_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s02_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s03_t01` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t03` | expansion | stable | ✗ |
| `wide_window_v2/test/kindu_drc/s01_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s01_t03` | expansion | — | ✗ |
| `wide_window_v2/test/kindu_drc/s02_t02` | cloud_artifact | stable | ✗ |
| `wide_window_v2/test/kindu_drc/s02_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/kindu_drc/s03_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s03_t03` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s00_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s00_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s01_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s01_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s02_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s02_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s03_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s03_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/yangambi_drc/s00_t02` | expansion | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s00_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/yangambi_drc/s01_t02` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s01_t03` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t02` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t03` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t02` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t03` | stable | — | ✗ |
