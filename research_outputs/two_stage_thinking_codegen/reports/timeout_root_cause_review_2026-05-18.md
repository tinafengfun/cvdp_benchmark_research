# Timeout Root-Cause Review: 2026-05-18

Scope: timeout cases from `full_codegen_t4_funnel_fixed_env` plus timeout reclassifications observed during Stage 1/2 targeted residual repair.

Method: artifact-only review. No blind reruns were performed. Classification is based on `report.txt`, per-case harness logs, cocotb progress, and visible RTL/harness source where needed.

## Summary

```text
full-run docker_timeout cases: 10
clear infra failures found: 0
likely DUT/model non-termination or harness wait caused by bad RTL: 9
parameter/test-runtime explosion caused by generated/default RTL parameter: 1
additional residual-repair timeout/reclassifications reviewed: 5
```

Conclusion: these should not be counted as Docker/network/image infra failures. They are mostly valid model residuals in the timeout/agentic-debug bucket. The useful next step is targeted semantic/agentic debug per case, not increasing Docker timeout globally.

## Full-Run Timeout Cases

| case_id | evidence | classification | reason |
| --- | --- | --- | --- |
| `cvdp_copilot_axi_alu_0001` | entered cocotb, failed burst write assertion, then timed out in later AXI test | model RTL non-termination after functional failure | Harness reached VPI/cocotb and reported `Expected 0x9, Got 0x0`; timeout happened after a real behavioral failure, not during infra setup. |
| `cvdp_copilot_binary_search_tree_sorting_0001` | entered cocotb test `test_bst_sorter`, printed `Running Test: Random 0`, then timed out | model RTL non-termination | Test started and waited for sorter/search-tree progress that did not complete. |
| `cvdp_copilot_binary_search_tree_sorting_0014` | some parameter tests passed, one latency assertion failed, later parameter timed out | model RTL semantic/timing plus non-termination | Evidence includes `Latency incorrect. Got: 4, Expected: 5` before timeout. |
| `cvdp_copilot_elevator_control_0033` | entered sparse-request cocotb test, printed target floors, then waited for floor 3 until timeout | model RTL state-machine non-progress | Elevator did not reach requested floor; no infra setup failure. |
| `cvdp_copilot_gcd_0009` | entered cocotb, first GCD assertion failed, stress test timed out | model RTL semantic plus non-termination | Evidence includes `Expected 1, got 0` before timeout. |
| `cvdp_copilot_gcd_0023` | entered cocotb, latency assertion failed, stress test timed out | model RTL semantic/timing plus non-termination | Evidence includes `Latency mismatch for A=0, B=0. Expected 3, got 4`. |
| `cvdp_copilot_ir_receiver_0001` | entered cocotb `test_ir_receiver`, then timed out | likely model RTL protocol non-progress | VPI/cocotb initialized; first IR receive test did not complete. |
| `cvdp_copilot_perf_counters_0001` | Docker build completed, pytest collected, then timed out; harness overflow loop uses default `CNT_W=32` | parameter/runtime explosion from RTL default/harness interaction | `test_perf_counters_overflow` loops `2**CNT_W - 1`; generated RTL default `CNT_W=32`, so test is effectively non-terminating. This is not Docker infra. |
| `cvdp_copilot_sorter_0003` | entered cocotb sorter test, printed first input `[0, 1, 2, 3]`, then timed out | model RTL sorter non-progress | Sorter engine did not complete the first transaction. |
| `cvdp_copilot_sorter_0059` | entered cocotb sorter sanity test, printed first input `[0, 1, 2, 3]`, then timed out | model RTL sorter non-progress | Same pattern as sorter_0003; not infra. |

## Additional Timeout Reclassifications

| case_id | source run | classification | reason |
| --- | --- | --- | --- |
| `cvdp_copilot_axis_border_gen_0014` | `stage1_module_retry_axis_border_gen_0014_norepair` | AXIS ready/valid deadlock | Harness compiled and ran; log repeats `tready=0` and `Waiting for m_axis_tvalid as 1`. |
| `cvdp_copilot_serial_in_parallel_out_0011` | `stage2_compile_elab_remaining_19_compile_focused_rerun` | model RTL/test handshake non-termination | Compile-focused repair entered cocotb `test_sipo`; timed out after test start. |
| `cvdp_copilot_manchester_enc_0005` | `stage2_targeted_pilot_manchester_enc_0005_model_path` | model RTL/test non-termination after sanitizer | Syntax issue was bypassed; pytest collected 4 tests and first `test_manchester_even` never completed. |
| `cvdp_copilot_elevator_control_0009` | `stage2_targeted_pilot_elevator_control_0009_semantic_hint` | repair-induced semantic non-termination | Repair compiled and started cocotb, then timed out after `Requesting floor 3`; not infra. |
| `cvdp_copilot_elevator_control_0009` initial sanitized run | `stage2_targeted_pilot_elevator_control_0009_model_path` | functional, not timeout | The sanitized initial run builds and fails an overload recovery assertion. The timeout only appears in the semantic repair attempt. |

## Infra Check

No reviewed timeout shows these infra signatures:

```text
Docker network creation failure
image pull/build hang before pytest
license-network wait
EDA tool license wait
missing Docker daemon
container start failure before test collection
```

Common observed signatures instead:

```text
pytest collected tests
Icarus/VPI initialized
cocotb started a named test
test printed DUT-specific progress
assertion failed before later timeout
or harness waits indefinitely for DUT valid/ready/done/floor/sorted output
```

## Recommendation

Keep these in `agentic_debug` / semantic timeout buckets. Do not globally increase `DOCKER_TIMEOUT` as a score-fixing strategy.

Prioritize only case-specific debug:

```text
AXIS/image cases: ready/valid and output-valid generation
sorter/BST cases: done/valid completion and bounded operation counters
GCD cases: start/done protocol, latency, and stress-test convergence
elevator cases: request latching/current-floor movement and door/open recovery
perf_counters: parameter default or harness parameterization; avoid 2**32 overflow loop
```
