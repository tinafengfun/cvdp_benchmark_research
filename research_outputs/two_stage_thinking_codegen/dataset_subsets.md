# Dataset Subsets

## Smoke Set

Use a small set of representative cases to validate the factory and two-stage strategy before running full benchmarks.

| Case | Category | Purpose |
|---|---|---|
| `cvdp_copilot_axi_alu_0001` | cid016 | Markdown fence / raw RTL sanitizer |
| `cvdp_copilot_axis_border_gen_0014` | cid002 | Root module mismatch |
| `cvdp_copilot_8x3_priority_encoder_0001` | cid003 | Verilog `wire` procedural assignment |
| `cvdp_copilot_axi_stream_upscale_0001` | cid003 | Icarus syntax compatibility |
| `cvdp_copilot_16qam_mapper_0001` | cid003 | Chained part-select / parameterized slicing |
| `cvdp_copilot_arithmetic_progression_generator_0003` | cid002 | Width formula and `$clog2` |
| `cvdp_copilot_apb_gpio_0001` | cid003 | APB register and interrupt behavior |
| `cvdp_copilot_GFCM_0001` | cid003 | CDC/glitch-free clock switching |
| `cvdp_copilot_gcd_0023` | cid004 | Modification preserving internal signal names |
| `cvdp_copilot_Carry_Lookahead_Adder_0005` | cid016 | Pipeline debug and latency alignment |
| `cvdp_copilot_IIR_filter_0019` | cid007 | Lint/QoR after sanity pass |

## Failed Subset

Definition:

```text
failed_subset = {id | first_pass_result[id] == fail}
```

For n=5 first-pass runs, define priority subsets:

```text
failed_0of5 = {id | pass_count == 0}
low_pass_1or2of5 = {id | pass_count in {1, 2}}
unstable_3or4of5 = {id | pass_count in {3, 4}}
stable_pass_5of5 = {id | pass_count == 5}
```

Recommended retry priority:

1. `failed_0of5`
2. `low_pass_1or2of5`
3. Selected cases from `unstable_3or4of5` only if studying variance

## Rescued Subset

Definition:

```text
rescued_by_thinking = {id | first_pass_fail and thinking_retry_pass}
```

This subset is evidence that thinking has targeted value.

## Residual Subset

Definition:

```text
residual_failed = {id | first_pass_fail and thinking_retry_fail}
```

Residual failures should be further classified by cause:

- timeout or max_tokens issue
- parser/sanitizer issue
- syntax/compile issue
- harness functional issue
- lint/QoR issue

Only residual functional failures after sufficient feedback-loop experiments should become finetune candidates.

## Finetune Candidate Set

Definition:

```text
finetune_candidates = residual_failed_after_feedback_loop
```

Inclusion criteria:

- Not explained by timeout or `max_tokens`.
- Not explained by parser/sanitizer.
- Not fixed by compile/harness feedback retry.
- Stable across multiple attempts.
- Represents a reusable hardware capability gap.

Expected categories:

- APB/AXI register files and side effects.
- Ready/valid protocols.
- CDC/glitch-free control.
- Pipeline latency and valid/done alignment.
- Minimal patch debugging.
- Lint/QoR-preserving rewrite.
