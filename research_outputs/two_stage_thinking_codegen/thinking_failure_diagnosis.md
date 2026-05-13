# Thinking Failure Diagnosis

Thinking-mode failures must not be treated as a single category. A thinking run can fail because of request timeout, insufficient `max_tokens`, empty final content, parser/sanitizer behavior, or true RTL functional failure.

## Failure Taxonomy

| Failure type | Observable signal | Likely cause | Action |
|---|---|---|---|
| Request timeout | API raises `Request timed out`; duration near timeout | Timeout too low, queueing, slow throughput, long prompt/generation | Increase timeout or reduce max_tokens/concurrency |
| Token exhaustion | `finish_reason == length`; content incomplete | `max_tokens` too low | Increase max_tokens and timeout proportionally |
| Empty final content | `content_len == 0`, `reasoning_len > 0` | Model spent tokens in reasoning and did not emit final answer, or chat template behavior | Retry non-thinking or increase token budget in controlled sweep |
| Parser-empty | raw content non-empty, parsed result empty | Sanitizer/parser issue | Fix sanitizer/parser, do not attribute to model |
| Markdown/format pollution | raw content contains fences/explanations | Output-contract failure | Sanitize and harden prompt |
| Harness failure | compilable output but tests fail | RTL behavior issue | Feed structured failure log; later consider finetune only if residual |

## Required Generation Stats

Every model call should log these fields when possible:

| Field | Description |
|---|---|
| `thinking_enabled` | Whether thinking was requested |
| `category` | CVDP category number |
| `max_tokens` | Request max token budget |
| `timeout_s` | Request timeout |
| `duration_s` | Wall-clock request time |
| `finish_reason` | API finish reason if available |
| `content_len` | Final answer character length |
| `reasoning_len` | Reasoning content character length |
| `error_type` | timeout, empty_content, parse_fail, etc. |
| `retry_mode` | none, nonthinking_fallback, longer_timeout, larger_max_tokens |

## Timeout Estimation

Assume approximate decoding throughput:

```text
throughput = 30 tokens/s/request
timeout = max_tokens / throughput * margin
margin = 1.3 to 1.5
```

Table:

| max_tokens | Raw time at 30 tok/s | 1.3x timeout | 1.5x timeout |
|---:|---:|---:|---:|
| 4096 | 136s | 178s | 205s |
| 8192 | 273s | 355s | 410s |
| 12000 | 400s | 520s | 600s |
| 16384 | 546s | 710s | 819s |
| 24576 | 819s | 1065s | 1229s |
| 32384 | 1080s | 1403s | 1619s |

Important caveats:

- Throughput may drop below 30 tokens/s/request under concurrency or long prompt prefill.
- vLLM queueing time is not captured by pure decode throughput estimates.
- Large thinking sweeps should be run only after shorter sweeps show value.

## Diagnosis Rules

```text
if API timeout and duration_s ~= timeout_s:
    classify as timeout_budget_or_queueing

elif finish_reason == "length":
    classify as max_tokens_exhausted

elif content_len == 0 and reasoning_len > 0:
    classify as empty_final_after_reasoning

elif raw_content_len > 0 and parsed_content_len == 0:
    classify as parser_or_sanitizer_failure

elif compile_or_harness_fail:
    classify as RTL_failure
```

## Long Thinking Sweep Policy

Long thinking experiments are expensive and must be deferred.

Run order:

1. First test non-thinking first pass.
2. Then failed-subset thinking retry at 8192 or 12000 max tokens.
3. Only if rescue signal exists, test 16384.
4. Only on representative cases, test 24576 and 32384.

Do not run full-dataset long thinking sweeps without a prior rescue signal.
