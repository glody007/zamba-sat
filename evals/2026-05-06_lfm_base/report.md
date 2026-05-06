# Evaluation report

- backend: `local`
- model: `LiquidAI/LFM2.5-VL-450M-GGUF`
- runs: `wide_window, wide_window_v2`
- split: `test`
- samples: 36
- timestamp: 20260506T090524Z

## Per-field accuracy

| Field | Correct | Accuracy |
|---|---|---|
| `valid_json` | 0/36 | 0.0% |
| `deforestation_detected` | 0/36 | 0.0% |
| `change_pattern` | 0/36 | 0.0% |
| `trajectory_confidence` | 0/36 | 0.0% |
| `severity` | 0/36 | 0.0% |
| `clearing_type` | 0/36 | 0.0% |
| `area_bucket_t1` | 0/36 | 0.0% |
| `area_bucket_t0` | 0/36 | 0.0% |
| `active_operation` | 0/36 | 0.0% |
| `active_machinery_visible` | 0/36 | 0.0% |
| `smoke_or_fire_visible` | 0/36 | 0.0% |
| `recent_road_construction` | 0/36 | 0.0% |
| `frame_quality` | 0/36 | 0.0% |

**Composite accuracy:** 0.0%

## Per-sample (change_pattern)

| Sample | GT pattern | Predicted | Match |
|---|---|---|---|
| `wide_window/test/kindu_drc/s00_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s01_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s02_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s03_t01` | expansion | — | ✗ |
| `wide_window/test/lusambo_drc/s00_t01` | expansion | — | ✗ |
| `wide_window/test/lusambo_drc/s01_t01` | expansion | — | ✗ |
| `wide_window/test/lusambo_drc/s02_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/lusambo_drc/s03_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s00_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s01_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s02_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s03_t01` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t03` | expansion | — | ✗ |
| `wide_window_v2/test/kindu_drc/s01_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s01_t03` | expansion | — | ✗ |
| `wide_window_v2/test/kindu_drc/s02_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s02_t03` | expansion | — | ✗ |
| `wide_window_v2/test/kindu_drc/s03_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s03_t03` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s00_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s00_t03` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s01_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s01_t03` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s02_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s02_t03` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s03_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s03_t03` | expansion | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s00_t02` | expansion | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s00_t03` | expansion | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s01_t02` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s01_t03` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t02` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t03` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t02` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t03` | stable | — | ✗ |
