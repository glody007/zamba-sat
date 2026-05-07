# Evaluation report

- backend: `local`
- model: `zamba-deforestation-Q8_0`
- runs: `wide_window, wide_window_v2`
- split: `test`
- samples: 36
- timestamp: 20260507T134656Z

## Per-field accuracy

| Field | Correct | Accuracy |
|---|---|---|
| `valid_json` | 26/36 | 72.2% |
| `deforestation_detected` | 11/36 | 30.6% |
| `change_pattern` | 6/36 | 16.7% |
| `trajectory_confidence` | 6/36 | 16.7% |
| `severity` | 11/36 | 30.6% |
| `clearing_type` | 11/36 | 30.6% |
| `area_bucket_t1` | 11/36 | 30.6% |
| `area_bucket_t0` | 11/36 | 30.6% |
| `active_operation` | 26/36 | 72.2% |
| `active_machinery_visible` | 26/36 | 72.2% |
| `smoke_or_fire_visible` | 26/36 | 72.2% |
| `recent_road_construction` | 26/36 | 72.2% |
| `frame_quality` | 11/36 | 30.6% |

**Composite accuracy:** 44.4%

## Per-sample (change_pattern)

| Sample | GT pattern | Predicted | Match |
|---|---|---|---|
| `wide_window/test/kindu_drc/s00_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s01_t01` | expansion | cloud_artifact | ✗ |
| `wide_window/test/kindu_drc/s02_t01` | expansion | cloud_artifact | ✗ |
| `wide_window/test/kindu_drc/s03_t01` | expansion | cloud_artifact | ✗ |
| `wide_window/test/lusambo_drc/s00_t01` | expansion | — | ✗ |
| `wide_window/test/lusambo_drc/s01_t01` | expansion | — | ✗ |
| `wide_window/test/lusambo_drc/s02_t01` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window/test/lusambo_drc/s03_t01` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window/test/yangambi_drc/s00_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s01_t01` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window/test/yangambi_drc/s02_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s03_t01` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window_v2/test/kindu_drc/s00_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t03` | expansion | — | ✗ |
| `wide_window_v2/test/kindu_drc/s01_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s01_t03` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/kindu_drc/s02_t02` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window_v2/test/kindu_drc/s02_t03` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/kindu_drc/s03_t02` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window_v2/test/kindu_drc/s03_t03` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/lusambo_drc/s00_t02` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/lusambo_drc/s00_t03` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/lusambo_drc/s01_t02` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/lusambo_drc/s01_t03` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/lusambo_drc/s02_t02` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/lusambo_drc/s02_t03` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/lusambo_drc/s03_t02` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/lusambo_drc/s03_t03` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/yangambi_drc/s00_t02` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/yangambi_drc/s00_t03` | expansion | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s01_t02` | stable | cloud_artifact | ✗ |
| `wide_window_v2/test/yangambi_drc/s01_t03` | stable | cloud_artifact | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t02` | stable | cloud_artifact | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t03` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t02` | stable | cloud_artifact | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t03` | stable | cloud_artifact | ✗ |
