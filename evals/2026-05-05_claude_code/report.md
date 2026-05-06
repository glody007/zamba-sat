# Evaluation report

- backend: `claude_code`
- model: `claude_code (manual)`
- runs: `wide_window, wide_window_v2`
- split: `test`
- samples: 36
- timestamp: 20260505T155432Z

## Per-field accuracy

| Field | Correct | Accuracy |
|---|---|---|
| `valid_json` | 36/36 | 100.0% |
| `deforestation_detected` | 35/36 | 97.2% |
| `change_pattern` | 32/36 | 88.9% |
| `trajectory_confidence` | 32/36 | 88.9% |
| `severity` | 35/36 | 97.2% |
| `clearing_type` | 35/36 | 97.2% |
| `area_bucket_t1` | 35/36 | 97.2% |
| `area_bucket_t0` | 35/36 | 97.2% |
| `active_operation` | 36/36 | 100.0% |
| `active_machinery_visible` | 36/36 | 100.0% |
| `smoke_or_fire_visible` | 36/36 | 100.0% |
| `recent_road_construction` | 36/36 | 100.0% |
| `frame_quality` | 35/36 | 97.2% |

**Composite accuracy:** 97.0%

## Per-sample (change_pattern)

| Sample | GT pattern | Predicted | Match |
|---|---|---|---|
| `wide_window/test/kindu_drc/s00_t01` | expansion | expansion | ✓ |
| `wide_window/test/kindu_drc/s01_t01` | expansion | expansion | ✓ |
| `wide_window/test/kindu_drc/s02_t01` | expansion | expansion | ✓ |
| `wide_window/test/kindu_drc/s03_t01` | expansion | expansion | ✓ |
| `wide_window/test/lusambo_drc/s00_t01` | expansion | expansion | ✓ |
| `wide_window/test/lusambo_drc/s01_t01` | expansion | expansion | ✓ |
| `wide_window/test/lusambo_drc/s02_t01` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window/test/lusambo_drc/s03_t01` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window/test/yangambi_drc/s00_t01` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window/test/yangambi_drc/s01_t01` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window/test/yangambi_drc/s02_t01` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window/test/yangambi_drc/s03_t01` | cloud_artifact | stable | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t02` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window_v2/test/kindu_drc/s00_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/kindu_drc/s01_t02` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window_v2/test/kindu_drc/s01_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/kindu_drc/s02_t02` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window_v2/test/kindu_drc/s02_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/kindu_drc/s03_t02` | cloud_artifact | cloud_artifact | ✓ |
| `wide_window_v2/test/kindu_drc/s03_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s00_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s00_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s01_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s01_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s02_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s02_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s03_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s03_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/yangambi_drc/s00_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/yangambi_drc/s00_t03` | expansion | cloud_artifact | ✗ |
| `wide_window_v2/test/yangambi_drc/s01_t02` | stable | stable | ✓ |
| `wide_window_v2/test/yangambi_drc/s01_t03` | stable | cloud_artifact | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t02` | stable | stable | ✓ |
| `wide_window_v2/test/yangambi_drc/s02_t03` | stable | cloud_artifact | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t02` | stable | stable | ✓ |
| `wide_window_v2/test/yangambi_drc/s03_t03` | stable | stable | ✓ |
