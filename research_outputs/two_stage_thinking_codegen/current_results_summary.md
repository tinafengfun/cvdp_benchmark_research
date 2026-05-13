# Current Result Summary

This note extracts the existing local CVDP results from `work_*` directories. It intentionally separates complete benchmark runs from smoke/incomplete runs, and separates model-output failures from benchmark/harness/runtime issues.

## Complete Runs Used

| Directory | Dataset | Samples | Problems/sample | Status | Notes |
|---|---|---:|---:|---|---|
| `work_codegen_v110` | `full_dataset/cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl` | 5 | 302 | complete | Composite report exists; an earlier interrupted attempt is visible in `run.log`, but the later rerun completed all 5 samples. |
| `work_comprehension_v110` | `full_dataset/cvdp_v1.1.0_nonagentic_code_comprehension.jsonl` | 5 | 123 | complete | Baseline run; category `cid009`/`cid010` scoring appears broken or misconfigured in this run and is treated separately. |
| `work_comprehension_v110_thinking` | `full_dataset/cvdp_v1.1.0_nonagentic_code_comprehension.jsonl` | 5 | 123 | complete | Thinking-enabled comprehension run. |
| `work_comprehension_v110_nonthinking` | `full_dataset/cvdp_v1.1.0_nonagentic_code_comprehension.jsonl` | 5 | 123 | complete | Non-thinking comprehension run. |

## Incomplete or Smoke Runs

| Directory | Observed content | Classification | Use in analysis |
|---|---|---|---|
| `work_codegen_v110_thinking` | `sample_1/` exists, no `raw_result.json`, no composite report; `run.log` stops after sample 1 startup. | incomplete | Do not use as full thinking-codegen evidence. |
| `work_codegen_v110_nonthinking` | `sample_1/` exists, no `raw_result.json`, no composite report; `run.log` stops after sample 1 startup. | incomplete | Do not use as full non-thinking-codegen evidence. |
| `work_vllm_passatk` | 5 samples, 1 problem/sample, example dataset. | smoke | Useful only for pipeline smoke, not CVDP v1.1.0 full-result claims. |
| `work_golden`, `work_vllm`, `work_vllm_single` | No usable full composite result. | incomplete/empty | Exclude from aggregate claims. |

## Codegen Full Result

Source: `work_codegen_v110/composite_report.txt` and per-sample `raw_result.json` files.

| Metric | Value |
|---|---:|
| Dataset size | 302 problems |
| Samples | 5 |
| Mean problem pass rate | 41.79% |
| StdDev | 0.54% |
| Mean passed problems | 126.2 / 302 |
| Mean failed problems | 175.8 / 302 |
| Easy pass rate | 53.95% |
| Medium pass rate | 27.71% |

Per-sample pass rates:

| Sample | Passed / Total | Pass rate |
|---|---:|---:|
| 1 | 129 / 302 | 42.72% |
| 2 | 125 / 302 | 41.39% |
| 3 | 125 / 302 | 41.39% |
| 4 | 126 / 302 | 41.72% |
| 5 | 126 / 302 | 41.72% |

Per-category mean problem pass rates:

| CID | Scene | Passed / Total | Pass rate |
|---|---|---:|---:|
| `cid002` | RTL completion | 35.8 / 94 | 38.09% |
| `cid003` | Spec-to-RTL | 33.6 / 78 | 43.08% |
| `cid004` | RTL modification | 26.2 / 55 | 47.64% |
| `cid007` | Lint/QoR | 15.0 / 40 | 37.50% |
| `cid016` | Debugging | 15.6 / 35 | 44.57% |

Pass-count distribution across 5 samples:

| Pass count | Problems | Dataset share |
|---|---:|---:|
| 0 / 5 | 157 | 51.99% |
| 1 / 5 | 7 | 2.32% |
| 2 / 5 | 12 | 3.97% |
| 3 / 5 | 14 | 4.64% |
| 4 / 5 | 2 | 0.66% |
| 5 / 5 | 110 | 36.42% |

Codegen failure bucket extraction from `raw_result.json` and report logs, counted over 5 samples. These counts are not the same as the composite mean because they aggregate all sample attempts.

| Bucket | Failed problem-attempts | Failed test-attempts | Interpretation |
|---|---:|---:|---|
| RTL functional/simulation failure | 719 | 719 | Model output compiled or ran far enough to fail behavioral checks, or failed normal simulation/test expectations. |
| RTL lint failure | 40 | 40 | `cid007` lint-oriented failures. |
| Harness timeout/killed | 75 | 75 | Runtime/system/harness instability; should not be counted as pure model RTL inability. |
| Harness or missing log | 45 | 45 | `Failed to execute objective harness` or missing report log; should be triaged before model conclusions. |

Codegen harness-separated view:

| Group | Failed problem-attempts | Share of failed problem-attempts |
|---|---:|---:|
| Model-output/code-quality failures | 759 | 86.35% |
| Harness/runtime/missing-log affected | 120 | 13.65% |

Important implication: codegen remains weak even after separating harness issues, but about 14% of failed problem-attempts in the current extraction are benchmark/harness/runtime affected and should not be treated as direct finetuning signal.

## Comprehension Full Results

Comprehension uses score-based metrics for categories marked with `*` in the benchmark reports. The benchmark's composite rate is the authoritative summary for score-based comparison.

| Run | Mean pass/score rate | StdDev | Easy | Medium | Notes |
|---|---:|---:|---:|---:|---|
| `work_comprehension_v110` | 23.53% | 0.56% | 29.65% | 12.14% | Baseline run; `cid009`/`cid010` are 0.00%, likely judge/config failure rather than model-only failure. |
| `work_comprehension_v110_thinking` | 76.95% | 0.89% | 81.86% | 67.81% | Best complete comprehension result. |
| `work_comprehension_v110_nonthinking` | 64.56% | 0.58% | 69.47% | 55.42% | Stronger than baseline, weaker than thinking. |

Per-category composite score rates:

| Run | `cid006` | `cid008` | `cid009` | `cid010` |
|---|---:|---:|---:|---:|
| `work_comprehension_v110` | 60.34% | 29.04% | 0.00% | 0.00% |
| `work_comprehension_v110_thinking` | 70.47% | 62.85% | 87.06% | 87.92% |
| `work_comprehension_v110_nonthinking` | 59.71% | 32.42% | 81.18% | 85.00% |

Thinking vs non-thinking comprehension delta:

| Slice | Thinking | Non-thinking | Delta |
|---|---:|---:|---:|
| Overall | 76.95% | 64.56% | +12.39 pp |
| Easy | 81.86% | 69.47% | +12.39 pp |
| Medium | 67.81% | 55.42% | +12.39 pp |
| `cid006` | 70.47% | 59.71% | +10.76 pp |
| `cid008` | 62.85% | 32.42% | +30.43 pp |
| `cid009` | 87.06% | 81.18% | +5.88 pp |
| `cid010` | 87.92% | 85.00% | +2.92 pp |

Comprehension failure buckets from per-sample `raw_result.json`, counted over all 5 samples. These are attempt-level buckets; score-based composite rates above remain the primary reported metric.

| Run | Text similarity below threshold | LLM judge score below threshold | Model/judge/API error | Empty output |
|---|---:|---:|---:|---:|
| `work_comprehension_v110` | 146 problem-attempts | 0 | 300 problem-attempts | 0 |
| `work_comprehension_v110_thinking` | 78 problem-attempts | 25 problem-attempts | 0 | 5 problem-attempts |
| `work_comprehension_v110_nonthinking` | 150 problem-attempts | 38 problem-attempts | 0 | 0 |

The `work_comprehension_v110` baseline has 300 problem-attempts in `cid009`/`cid010` classified as model/judge/API error because all `cid009` and `cid010` attempts scored 0 while later complete runs scored normally. Treat that baseline as configuration-contaminated for those subjective-judge categories.

## Research Consequences

- Use `work_codegen_v110` as the current complete codegen baseline, but do not claim it is thinking or non-thinking controlled unless the exact environment from that run is recovered.
- Do not use `work_codegen_v110_thinking` or `work_codegen_v110_nonthinking` as complete codegen ablations; both are incomplete.
- For comprehension, thinking is clearly better than non-thinking on the complete controlled runs: `76.95%` vs `64.56%`.
- Codegen failure analysis should separate 120 harness/runtime/missing-log failed problem-attempts from 759 model-output/code-quality failed problem-attempts.
- Finetuning candidates should be drawn from residual model-output failures after excluding harness/runtime/missing-log cases and after prompt/sanitizer/feedback-loop ablations.
