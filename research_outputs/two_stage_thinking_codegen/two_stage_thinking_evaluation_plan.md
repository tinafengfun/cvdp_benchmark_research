# Two-Stage Thinking Evaluation Plan

## Strategy

Use non-thinking as the default codegen path, then retry only failed cases with thinking.

```text
Stage 1: non-thinking first pass
Stage 2: thinking retry on failed subset
Final result: pass if either stage passes
```

This is intentionally different from running all codegen with thinking. It tests whether thinking provides marginal rescue value where non-thinking fails, while avoiding unnecessary timeout and token cost on cases already solved by non-thinking.

## Stage 1: Non-Thinking First Pass

Recommended environment:

```text
VLLM_THINKING_POLICY=auto
VLLM_CODEGEN_ENABLE_THINKING=false
VLLM_PROMPT_PROFILE=strict_codegen
VLLM_SANITIZE_OUTPUT=true
VLLM_CHECK_MODULE_NAME=true
VLLM_MAX_TOKENS_CODEGEN_NONTHINKING=8192
VLLM_AUTO_TIMEOUT=true
VLLM_THROUGHPUT_TOKENS_PER_SEC=30
VLLM_TIMEOUT_MARGIN=1.5
```

Goals:

- Minimize timeouts.
- Reduce empty final content.
- Reduce markdown-fence and parse failures.
- Produce a reliable first-pass failure subset.

## Stage 2: Thinking Retry on Failed Cases

Recommended initial environment:

```text
VLLM_ENABLE_THINKING=true
VLLM_PROMPT_PROFILE=strict_codegen_thinking
VLLM_MAX_TOKENS_CODEGEN_THINKING=8192 or 12000
VLLM_AUTO_TIMEOUT=true
VLLM_THROUGHPUT_TOKENS_PER_SEC=30
VLLM_TIMEOUT_MARGIN=1.5
```

Prompt contract:

```text
Think internally if needed, but final answer must contain only compilable RTL.
Do not include reasoning, markdown fences, comments outside RTL, or explanations.
```

Merge rule:

```text
if first_pass[id] == pass:
    final[id] = pass_nonthinking
elif thinking_retry[id] == pass:
    final[id] = pass_thinking_rescue
else:
    final[id] = fail_residual
```

## Why Failed-Only Thinking Retry

Failed-only retry supports a clean causal question:

```text
Does thinking rescue cases that non-thinking could not solve?
```

It avoids conflating that question with:

- All-thinking timeout behavior.
- More samples/pass@k effects.
- Prompt/sanitizer changes.
- Failure-feedback repair.

## Low-Score Definition

For codegen, there is no fractional score by default. The trigger is binary failure.

Retry candidates:

| First-pass outcome | Thinking retry priority |
|---|---|
| Harness fail | High |
| Compile/elaboration fail | Medium/high |
| Syntax fail | Medium; compile retry may be cheaper |
| Parse fail | Medium; sanitizer/fallback first |
| Empty output | Medium; diagnose thinking/content separately |
| Timeout | Low for thinking retry; first diagnose timeout budget |
| Pass | Do not retry |

For n=5 first-pass runs, priority can be based on pass count:

| First-pass pass count | Retry priority |
|---:|---|
| 0/5 | Highest |
| 1/5 or 2/5 | Optional |
| 3/5 or 4/5 | Low |
| 5/5 | None |

## Primary Metrics

```text
first_pass_rate = first_pass_passed / total
thinking_retry_rate = thinking_retry_passed / first_pass_failed
thinking_rescue_rate = rescued_by_thinking / first_pass_failed
final_two_stage_rate = (first_pass_passed + rescued_by_thinking) / total
extra_cost_per_rescue = thinking_retry_cost / rescued_by_thinking
```

## Interpretation

| Result | Interpretation | Next action |
|---|---|---|
| High first-pass gain | Prompt/env/sanitizer helped | Keep factory hygiene |
| Low all-thinking, high non-thinking | Thinking should not be default codegen mode | Use failed-only thinking retry |
| High thinking rescue | Thinking is useful as targeted second pass | Keep two-stage strategy |
| Low thinking rescue, high feedback repair | Failure feedback matters more than thinking itself | Build agentic loop |
| Low rescue even with feedback | Residual model capability issue | Consider finetune candidates |
