# Fine-tune experiments

Detailed history of fine-tuning runs. The README shows only the current
deployed model (v2); this file is the full experiment log including
attempts that didn't ship.

## Full results table

| Run | Model | Test set | Composite | `valid_json` | `change_pattern` | Report |
|---|---|---|---|---|---|---|
| 2026-05-05 | Claude Opus 4.7 (in-session, `claude_code` backend) | dir-test (36) | **96.6%** | 100% | 100% | [report](2026-05-05_claude_code/report.md) |
| 2026-05-06 | `LFM2.5-VL-450M` (no fine-tune) | dir-test (36) | **0.0%** | 0% | 0% | [report](2026-05-06_lfm_base/report.md) |
| 2026-05-07 | v1 — full SFT, 4.5 ep, no `--skip-clouds` (36 train) | dir-test (36) | **44.4%** | 72% | 17% | [report](2026-05-07_lfm_finetuned/report.md) |
| 2026-05-07 | v2 — full SFT, 4 ep, `--skip-clouds` + stratified (24 train) | dir-test (36)¹ | **28.8%** | 44% | 31% | [report](2026-05-07_lfm_finetuned_v2_dirtest/report.md) |
| 2026-05-07 | v2 — same checkpoint                                            | held-out (6)² | **38.5%** | 67% | **50%** | [report](2026-05-07_lfm_finetuned_v2_heldout/report.md) |
| 2026-05-07 | v3 — full SFT, 8 ep, `--skip-clouds` + stratified (24 train) | dir-test (36)¹ | **41.9%** | 58% | 33% | [report](2026-05-07_lfm_finetuned_v3_dirtest/report.md) |
| 2026-05-07 | v3 — same checkpoint                                            | held-out (6)² | **25.6%** | 33% | 0% | [report](2026-05-07_lfm_finetuned_v3_heldout/report.md) |

¹ *Not directly comparable to v1: stratified re-split moved many original-dir-test samples into the train set (data leakage on dir-test). The dir-test gain v2→v3 reflects more memorisation, not better generalisation.*
² *6-sample honest held-out from `data/finetune/splits.json`; the only test set the post-v1 models truly didn't see. Statistical significance is weak at N=6.*

## v1 — no `--skip-clouds`

Big structural win: `valid_json` went 0% → 72% — the base model was
emitting prose with placeholder text and no `<json>` block; the fine-tune
learned the XML-CoT + JSON schema. But `change_pattern` is only 17%
because v1 class-collapsed onto `cloud_artifact`: of 36 train rows,
~32 were `cloud_artifact`, so the model learned "when in doubt, say
cloud." For uncertain inputs it sometimes degenerated into a self-similar
JSON loop like `{"cloud_artifact_confidence_range_range": …}`.

## v2 — `--skip-clouds` + stratified split (deployed)

The headline movement is `change_pattern`: **17% → 50%** on the honest
held-out test (3/3 expansion samples called correctly; misses on 2
parse-fails and 1 stable→expansion). The composite drop on held-out is
real but mostly from `valid_json` sliding 72% → 67% — v2 is undertrained
(only 12 grad steps over 4 epochs on 24 rows) and emits inconsistent
JSON: it picks `change_pattern: expansion` correctly but writes
`deforestation_detected: false` in the same block, or skips
`severity`/`clearing_type` entirely. The change-detection signal itself
is real and learning.

## v3 — 8 ep / ~25 grad steps

Doubling the training budget made v3 *better* on dir-test (28.8% → 41.9%,
valid_json 44% → 58%) but *worse* on the honest held-out (38.5% → 25.6%,
change_pattern 50% → 0%). This is overfitting: with 24 train rows, v3
memorised the train-set XML-CoT patterns, which paid off on the dir-test
(overlapping with train via the stratified split) but hurt generalisation
on the 6 truly unseen samples. v3 confidently misclassifies stable as
expansion and parse-fails on expansion samples it hasn't memorised.

## Conclusion

v2 is the apparent sweet spot among the three full-SFT runs. v3 is the
overfitting boundary; the right next move is collecting more non-cloud
labels (especially `stable` — only 7 in train) before training further.
