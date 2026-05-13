# Metrics and Reporting

## Core Codegen Metrics

| Metric | Formula | Purpose |
|---|---|---|
| First-pass pass rate | `first_pass_passed / total` | Non-thinking baseline quality |
| Thinking retry rate | `thinking_retry_passed / first_pass_failed` | Retry subset success |
| Thinking rescue rate | `rescued_by_thinking / first_pass_failed` | Marginal value of thinking |
| Final two-stage pass rate | `(first_pass_passed + rescued_by_thinking) / total` | End-to-end two-stage result |
| Residual failure rate | `residual_failed / total` | Remaining finetune/agentic candidates |
| Extra cost per rescue | `thinking_retry_cost / rescued_by_thinking` | Efficiency of second pass |

## Failure Metrics

| Metric | Purpose |
|---|---|
| `timeout_count` | Detect timeout budget or service congestion |
| `empty_final_content_count` | Detect thinking/content emission issues |
| `parse_failure_count` | Measure sanitizer/parser impact |
| `syntax_failure_count` | Measure prompt/style impact |
| `compile_elaboration_failure_count` | Measure tool-compatibility impact |
| `module_mismatch_count` | Measure signature enforcement impact |
| `harness_failure_count` | Separate true RTL behavior failures |

## Thinking Diagnostics Metrics

| Metric | Purpose |
|---|---|
| `avg_duration_s` | Runtime cost |
| `avg_content_len` | Final answer emission behavior |
| `avg_reasoning_len` | Thinking token/length behavior proxy |
| `finish_reason_length_count` | Token exhaustion signal |
| `timeout_near_budget_count` | Timeout diagnosis |
| `empty_content_with_reasoning_count` | Reasoning consumed output budget or failed final emission |

## Per-CID Reporting

Report all core metrics by category:

```text
cid002 code completion
cid003 spec-to-RTL
cid004 code modification
cid007 lint/QoR
cid016 debug
```

This matters because thinking may be useful for cid004/cid016 but harmful for cid002/cid007.

## Recommended Tables for Paper Drafts

### Table 1: Baseline vs Factory Hygiene

| Config | Overall | cid002 | cid003 | cid004 | cid007 | cid016 | Timeout | Parse Fail | Compile Fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|

### Table 2: Thinking Strategy Ablation

| Config | First-pass | Retry subset | Rescued | Final two-stage | Extra cost | Timeout |
|---|---:|---:|---:|---:|---:|---:|

### Table 3: Thinking Token Sweep

| max_tokens | timeout | Retry pass | Empty content | Timeout | finish_reason=length | Avg duration |
|---:|---:|---:|---:|---:|---:|---:|

### Table 4: Residual Failure Taxonomy

| Failure class | Count | Representative cases | Next action |
|---|---:|---|---|

## Statistical Notes

- For small smoke sets, report raw counts, not only percentages.
- For n=5 runs, report both per-sample mean pass rate and unique-rescue coverage.
- Keep binary codegen pass/fail separate from score-based comprehension metrics.
- Do not compare two-stage pass rate directly to pass@1 without noting the extra inference budget.
