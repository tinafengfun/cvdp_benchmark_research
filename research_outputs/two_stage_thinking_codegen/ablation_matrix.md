# Ablation Matrix

The study uses multiple ablation axes. The goal is to attribute improvements to specific interventions rather than reporting a single end-to-end number.

## A Axis: Factory Hygiene

| Experiment | Change | Purpose |
|---|---|---|
| A0 | Current `kimi_vllm_factory.py` | Baseline |
| A1 | Strict codegen prompt | Test prompt-only effect |
| A2 | A1 + output sanitizer | Test markdown/JSON/noise cleanup |
| A3 | A2 + category-specific thinking policy | Test automatic thinking selection |
| A4 | A3 + empty-content fallback/diagnostics | Test robustness to thinking empty final content |
| A5 | A4 + module-name light check | Test root-module mismatch reduction |
| A6 | A5 + per-category max_tokens/timeout | Test cost/stability tuning |

## B Axis: Thinking Strategy

| Experiment | First pass | Second pass | Purpose |
|---|---|---|---|
| B0 | Non-thinking | None | Stable codegen baseline |
| B1 | Thinking | None | All-thinking comparison |
| B2 | Non-thinking | Thinking retry on failed cases, no failure log | Test thinking as second sample |
| B3 | Non-thinking | Thinking retry with structured failure log | Test thinking as repair/reflector |
| B4 | Non-thinking | Multi-trajectory retry | Test pass@k-like rescue |

## T Axis: Thinking Token/Timeout Sweep

Run T sweeps only on a small failed subset, not the full dataset.

| Experiment | max_tokens | Timeout target | Purpose |
|---|---:|---:|---|
| T0 | 8192 | ~410s | Short thinking |
| T1 | 12000 | ~600s | Medium thinking |
| T2 | 16384 | ~819s | Longer thinking |
| T3 | 24576 | ~1229s | Expensive long thinking |
| T4 | 32384 | ~1619s | Current large-token upper range |

Timeout target assumes 30 tokens/s/request and 1.5x margin.

## C Axis: Runner-Level Agentic Feedback

These are out of scope for `kimi_vllm_factory.py` alone, but are required for high-accuracy ACE-style experiments.

| Experiment | Change | Purpose |
|---|---|---|
| C0 | Factory-only | Establish hygiene baseline |
| C1 | C0 + compile retry | Test compiler feedback |
| C2 | C1 + harness feedback retry | Test functional feedback |
| C3 | C2 + Reflector | Diagnose root cause before retry |
| C4 | C3 + Coordinator/history | Avoid repeated failed fixes |
| C5 | C4 + restart | Escape stalled trajectories |
| C6 | C5 + parallel trajectories | Improve time-to-first-success |

## Priority Runs

Initial low-cost sequence:

```text
A0+B0
A4+B0
A4+B1
A4+B2 with T0/T1 on failed subset
```

Then, if thinking rescue is nontrivial:

```text
A6+B2 with T2 on representative failed subset
A6+B3 with structured failure feedback
```

Long sweeps:

```text
A6+B2 with T3/T4 only on selected case studies
```
