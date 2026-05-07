# Evaluation report

- backend: `local`
- model: `zamba-deforestation-v2-Q8_0`
- runs: `wide_window, wide_window_v2`
- split: `test`
- samples: 36
- timestamp: 20260507T182952Z

## Per-field accuracy

| Field | Correct | Accuracy |
|---|---|---|
| `valid_json` | 22/36 | 61.1% |
| `change_pattern` | 11/36 | 30.6% |
| `trajectory_confidence` | 14/36 | 38.9% |
| `active_operation` | 22/36 | 61.1% |
| `active_machinery_visible` | 22/36 | 61.1% |
| `smoke_or_fire_visible` | 22/36 | 61.1% |
| `recent_road_construction` | 22/36 | 61.1% |
| `frame_quality` | 9/36 | 25.0% |

**Composite accuracy:** 50.0%

## Per-sample (change_pattern)

| Sample | GT pattern | Predicted | Match |
|---|---|---|---|
| `wide_window/test/kindu_drc/s00_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s01_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s02_t01` | expansion | — | ✗ |
| `wide_window/test/kindu_drc/s03_t01` | expansion | — | ✗ |
| `wide_window/test/lusambo_drc/s00_t01` | expansion | — | ✗ |
| `wide_window/test/lusambo_drc/s01_t01` | expansion | expansion | ✓ |
| `wide_window/test/lusambo_drc/s02_t01` | cloud_artifact | stable | ✗ |
| `wide_window/test/lusambo_drc/s03_t01` | cloud_artifact | — | ✗ |
| `wide_window/test/yangambi_drc/s00_t01` | cloud_artifact | expansion | ✗ |
| `wide_window/test/yangambi_drc/s01_t01` | cloud_artifact | stable | ✗ |
| `wide_window/test/yangambi_drc/s02_t01` | cloud_artifact | expansion | ✗ |
| `wide_window/test/yangambi_drc/s03_t01` | cloud_artifact | expansion | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t02` | cloud_artifact | — | ✗ |
| `wide_window_v2/test/kindu_drc/s00_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/kindu_drc/s01_t02` | cloud_artifact | expansion | ✗ |
| `wide_window_v2/test/kindu_drc/s01_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/kindu_drc/s02_t02` | cloud_artifact | expansion | ✗ |
| `wide_window_v2/test/kindu_drc/s02_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/kindu_drc/s03_t02` | cloud_artifact | expansion | ✗ |
| `wide_window_v2/test/kindu_drc/s03_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s00_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s00_t03` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s01_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s01_t03` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s02_t02` | expansion | expansion | ✓ |
| `wide_window_v2/test/lusambo_drc/s02_t03` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s03_t02` | expansion | — | ✗ |
| `wide_window_v2/test/lusambo_drc/s03_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/yangambi_drc/s00_t02` | expansion | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s00_t03` | expansion | expansion | ✓ |
| `wide_window_v2/test/yangambi_drc/s01_t02` | stable | stable | ✓ |
| `wide_window_v2/test/yangambi_drc/s01_t03` | stable | stable | ✓ |
| `wide_window_v2/test/yangambi_drc/s02_t02` | stable | — | ✗ |
| `wide_window_v2/test/yangambi_drc/s02_t03` | stable | expansion | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t02` | stable | expansion | ✗ |
| `wide_window_v2/test/yangambi_drc/s03_t03` | stable | expansion | ✗ |
