# Experiment Plan

## Objective

Improve CVDP code generation accuracy for `vllm-glm` while preserving a rigorous path for deciding whether model finetuning is necessary.

The core experimental opportunity is to avoid all-thinking codegen. Instead, use non-thinking as a stable first pass, then selectively apply thinking to failures.

## Phases

### Phase 0: Baseline Log Analysis

Use existing outputs only. Do not run long thinking experiments.

Goals:

- Count existing timeout, empty-content, parse, syntax, compile, and harness failures.
- Compare available thinking and non-thinking outputs.
- Identify smoke cases for targeted testing.

Known observations:

- Comprehension benefits from thinking: `76.95%` thinking vs `64.56%` non-thinking in current results.
- Codegen thinking currently has incomplete runs and visible `Request timed out` events.
- Codegen non-thinking appears more stable in logs, but full comparable composite reports are not yet available for the newer prefixes.

### Phase 1: Factory Hygiene

Modify `kimi_vllm_factory.py` only. Do not require live vLLM during this phase.

Scope:

- Category-specific thinking policy.
- Strict codegen prompt profile.
- Output sanitizer.
- Empty-content diagnostics and fallback behavior.
- `max_tokens` and timeout configuration by category/mode.
- Throughput-based timeout estimation.
- Generation stats logging for later analysis.

Expected effect:

- Reduce markdown fences, raw JSON/RTL parsing failures, empty final content, and module-name mismatches.
- Improve stability before any thinking or agentic feedback loop is evaluated.

### Phase 2: Non-Thinking First Pass

Run codegen with non-thinking and the improved factory.

Primary output:

```text
first_pass_result[id] = pass/fail + failure_type + generation_stats
```

Purpose:

- Establish the improved first-pass baseline.
- Extract failed IDs for targeted thinking retry.

### Phase 3: Failed-Subset Thinking Retry

Run thinking only on failed first-pass cases.

Initial budget should be moderate:

```text
max_tokens = 8192 or 12000
timeout = max_tokens / 30 * 1.3~1.5
```

Purpose:

- Measure thinking rescue rate without committing to expensive long-thinking sweeps.
- Determine whether thinking improves codegen when targeted.

### Phase 4: Thinking Failure Diagnosis Sweep

Run only on a small representative subset after Phase 3 shows a plausible signal.

Sweep levels:

| Experiment | max_tokens | Approx timeout at 30 tok/s, 1.5x | Purpose |
|---|---:|---:|---|
| T0 | 8192 | 410s | Short thinking |
| T1 | 12000 | 600s | Medium thinking |
| T2 | 16384 | 819s | Long-ish thinking |
| T3 | 24576 | 1229s | Long thinking |
| T4 | 32384 | 1619s | Current large-token upper range |

T3/T4 are expensive and should only be run after T0-T2 indicate that thinking is helping.

### Phase 5: Structured Failure-Log Repair

Evaluate whether thinking is more useful when given compile or harness failure feedback.

Protocol:

```text
non-thinking first-pass fail
  -> parse compile/harness log
  -> thinking repair prompt with structured failure report
  -> rerun harness
```

Purpose:

- Separate thinking-as-second-sample from thinking-as-reflector/repair.
- Determine whether ACE-style agentic feedback is more valuable than thinking alone.

### Phase 6: Residual Failure and Finetune Decision

Only after Phases 1-5, classify residual stable failures.

Finetuning is justified when failures remain stable after:

```text
prompt/env hygiene
output sanitizer
non-thinking first pass
thinking retry with adequate token/timeout
structured failure feedback
restart/parallel trajectory experiments, if implemented
```

Residual categories likely to justify finetuning:

- APB/AXI register semantics.
- CDC/glitch-free behavior.
- Pipeline latency alignment.
- Debug minimal patches.
- Lint/QoR-preserving transformations.

## Decision Criteria

```text
pass5 failure is not evidence for finetuning.
thinking failure is not evidence that thinking is ineffective.
timeout and max_tokens must be diagnosed separately.
finetuning is a residual-failure decision after feedback-loop ablations.
```
