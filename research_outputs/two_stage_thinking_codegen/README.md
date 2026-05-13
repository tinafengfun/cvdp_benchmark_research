# Two-Stage Thinking Codegen Study

This directory contains the research plan, experimental protocol, and expected artifacts for improving `vllm-glm` on CVDP code generation with a two-stage thinking strategy.

## Goal

Evaluate whether code generation should use a two-stage strategy:

```text
Stage 1: non-thinking codegen first pass
Stage 2: thinking retry only on failed or low-confidence cases
```

The study must separate improvements from prompt/env hygiene, output sanitization, thinking mode, failure feedback, and eventual finetuning.

## Research Questions

1. Is non-thinking the better default first-pass mode for CVDP codegen?
2. Can thinking rescue cases that fail in non-thinking mode?
3. When thinking fails, is the cause timeout, `max_tokens`, empty final content, parsing, or true RTL failure?
4. How much improvement comes from prompt/env/sanitizer changes versus thinking itself?
5. Does structured failure feedback matter more than thinking mode alone?
6. Which residual failures, after feedback-loop experiments, justify finetuning?

## Directory Contents

| File | Purpose |
|---|---|
| `experiment_plan.md` | Overall research phases and decision logic |
| `two_stage_thinking_evaluation_plan.md` | Main two-stage non-thinking/thinking protocol |
| `thinking_failure_diagnosis.md` | Timeout, max-token, empty-content, parser, and harness failure taxonomy |
| `ablation_matrix.md` | A/B/C/T ablation groups |
| `metrics_and_reporting.md` | Metric definitions and reporting formulas |
| `current_results_summary.md` | Extracted complete codegen/comprehension results and incomplete-run inventory |
| `dataset_subsets.md` | Smoke, failed, rescued, residual, and finetune-candidate subset definitions |
| `runbook.md` | Commands and execution order |
| `result_schema.md` | JSON/CSV schema for reproducible experiment logging |
| `notes/` | Case notes, log excerpts, and paper-draft observations |

## Current Default Hypothesis

```text
Codegen should default to non-thinking for stability and cost.
Thinking should be evaluated as a targeted second-pass rescue strategy.
Thinking failures must be diagnosed before concluding that thinking is ineffective.
Finetuning should only be considered after prompt/env hygiene and agentic feedback-loop ablations.
```
