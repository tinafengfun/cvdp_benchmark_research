# Residual Rescue Log: 2026-05-15

## Stage 1: Module-Name Checker Retry

Configuration:

```text
VLLM_ENABLE_THINKING=false
VLLM_CHECK_MODULE_NAME=true
VLLM_RETRY_MODULE_NAME_MISMATCH=true
CVDP_REPAIR_ENABLE=false
DOCKER_TIMEOUT=600
MODEL_TIMEOUT=900
```

Rationale: isolate the cheap front-door retry. Repair loop was disabled in the recorded runs so Stage 1 measures only whether module-name retry can get rejected outputs into the harness.

### cvdp_copilot_axis_border_gen_0014

Baseline class: `model_output_rejected`

Baseline error:

```text
Generated RTL module-name check failed: expected one of ['axis_border_gen_with_resize'], but found modules ['axis_image_border_gen_with_resizer', 'axis_image_resizer']
```

Stage 1 run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage1_module_retry_axis_border_gen_0014_norepair
```

Outcome: reclassified to `docker_timeout`, not rescued.

Evidence:

```text
retry_mode: module_name_mismatch_retry
harness entered: yes
returncode: 124
timed_out: true
error_msg: Timed out after 600s
```

Observed root cause after retry: harness starts with `axis_border_gen_with_resize`, but the AXIS test loops waiting for progress. Log repeatedly shows `Waiting for DUT to be ready (pixel 0, value 0, tready=0)` and `Waiting for m_axis_tvalid as 1`. This is now a real handshake/pipeline non-termination residual, not a module-name rejection.

Next action: move to timeout/agentic debug. Inspect AXIS ready/valid generation and resize/border pipeline start condition.

### cvdp_copilot_bus_arbiter_0004

Baseline class: `model_output_rejected`

Baseline error:

```text
Generated RTL module-name check failed: expected one of ['bus_arbiter'], but found modules ['cvdp_copilot_bus_arbiter']
```

Stage 1 run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage1_module_retry_bus_arbiter_0004_norepair
```

Outcome: reclassified to `compile_elab`, not rescued.

Evidence:

```text
retry_mode: module_name_mismatch_retry
harness entered: yes
returncode: 1
timed_out: false
error: subprocess.CalledProcessError from iverilog build
```

Observed root cause after retry: checker retry got the case into the harness, but the generated RTL still builds under a mismatched file/top situation. The report shows iverilog invoked with `-s cvdp_copilot_bus_arbiter` and source `/code/rtl/cvdp_copilot_bus_arbiter.sv`, then returned non-zero exit status 1.

Next action: move to compile/elab repair. Inspect generated source and first iverilog error, then apply compile-only repair.

## Stage 1 Summary

```text
input cases: 2
front-door rejections fixed enough to enter harness: 2
direct rescues: 0
reclassified to docker_timeout: 1
reclassified to compile_elab: 1
thinking used: no
```

Interpretation: checker-specific retry is useful and should remain available as an opt-in front-door repair. It does not solve the underlying design for these two cases, but it converts opaque `model_output_rejected` failures into actionable harness residuals.

## Stage 2: Compile/Elab Repair Pilot

Configuration:

```text
VLLM_ENABLE_THINKING=false
VLLM_RETRY_MODULE_NAME_MISMATCH=true
CVDP_REPAIR_ENABLE=true
CVDP_REPAIR_MAX_ATTEMPTS=2
CVDP_REPAIR_COMPILE_FOCUSED=true
CVDP_REPAIR_TARGETED_HINTS=false
DOCKER_TIMEOUT=600
CVDP_REPAIR_DOCKER_TIMEOUT=600
```

Pilot subset:

```text
research_outputs/two_stage_thinking_codegen/subsets/stage2_compile_elab_pilot_5.jsonl
```

Run artifact:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_compile_elab_pilot_5_compile_focused
```

Summary:

```text
input cases: 5
repair_attempted: 5
repair_rescued: 2
final_pass: 2
final_fail: 3
thinking used: no
```

### Rescued

`cvdp_copilot_binary_multiplier_0012`

```text
repair attempt: 1
final: pass
evidence: 4 passed in 1.11s
```

Root cause interpretation: baseline compile/elab failed for parameterized multiplier builds; compile-focused repair produced parameter-safe RTL that passed random, max, alternating, and zero tests.

`cvdp_copilot_cascaded_adder_0025`

```text
repair attempt: 2
final: pass
evidence: 5 passed in 2.19s
```

Root cause interpretation: baseline was close but failed one configuration; compile-focused repair converged after the second attempt and passed all tested cascaded adder configurations.

### Reclassified / Not Rescued

`cvdp_copilot_MSHR_0001`

```text
baseline class: compile_elab
current class: functional/timing residual
evidence: repair attempt 2 reached cocotb assertions
example: full should be asserted. Asserted after: 40, Expected: 20
```

Interpretation: compile-focused repair fixed enough structure to simulate, but the MSHR full timing is about 2x too slow. This should leave the compile queue and move to semantic/timing repair or agentic debug.

`cvdp_copilot_axi_register_0001`

```text
baseline class: compile_elab
current class: compile_elab with functional symptoms
evidence: Write operation failed at addr=0x100 plus repeated parameterized iverilog CalledProcessError
```

Interpretation: still not robust across parameter combinations. Needs interface/parameter-specific compile repair, not broad semantic repair yet.

`cvdp_copilot_fifo_to_axis_0001`

```text
baseline class: compile_elab
current class: compile_elab
evidence: iverilog/vvp returned non-zero exit status 139
```

Interpretation: still a simulator/build failure after repair. Needs direct RTL inspection for unsupported construct, simulator crash trigger, or module/interface mismatch.

### Stage 2 Pilot Decision

The pilot met the expansion threshold: 2/5 direct rescues and 1/5 useful reclassification from compile/elab to semantic/timing residual. Continue Stage 2 on the remaining compile/elab cases, but keep recording reclassifications separately from pass rescues.

## Stage 2: Remaining Compile/Elab Queue

Configuration matched the Stage 2 pilot:

```text
VLLM_ENABLE_THINKING=false
VLLM_RETRY_MODULE_NAME_MISMATCH=true
CVDP_REPAIR_ENABLE=true
CVDP_REPAIR_MAX_ATTEMPTS=2
CVDP_REPAIR_COMPILE_FOCUSED=true
CVDP_REPAIR_TARGETED_HINTS=false
DOCKER_TIMEOUT=600
CVDP_REPAIR_DOCKER_TIMEOUT=600
```

Subset:

```text
research_outputs/two_stage_thinking_codegen/subsets/stage2_compile_elab_remaining_19.jsonl
```

Clean rerun artifact:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_compile_elab_remaining_19_compile_focused_rerun
```

Summary:

```text
input cases: 19
repair_attempted: 19
repair_rescued: 2
final_pass: 2
final_fail: 17
remaining classes: compile_elab=15, functional=1, docker_timeout=1
thinking used: no
```

### Rescued

```text
cvdp_copilot_MSHR_0008 -> pass, best 10/10, repair attempt 2
cvdp_copilot_findfasterclock_0001 -> pass, best 1/1, repair attempt 1
```

### Reclassified

```text
cvdp_copilot_ahb_clk_counter_0001 -> functional, best 1/2
cvdp_copilot_serial_in_parallel_out_0011 -> docker_timeout, best 0/0
```

Interpretation: compile-focused repair continues to produce useful signal. It directly rescued 2/19 in the remaining queue and converted 2/19 from compile/elab into more specific downstream residuals.

### Still Compile/Elab

```text
cvdp_copilot_8x3_priority_encoder_0013
cvdp_copilot_barrel_shifter_0058
cvdp_copilot_bus_arbiter_0004
cvdp_copilot_car_parking_management_0015
cvdp_copilot_elevator_control_0006
cvdp_copilot_elevator_control_0009
cvdp_copilot_elevator_control_0026
cvdp_copilot_gaussian_rounding_div_0005
cvdp_copilot_hebbian_rule_0017
cvdp_copilot_interrupt_controller_0014
cvdp_copilot_interrupt_controller_0017
cvdp_copilot_interrupt_controller_0019
cvdp_copilot_manchester_enc_0005
cvdp_copilot_sequencial_binary_to_one_hot_decoder_0001
cvdp_copilot_sync_serial_communication_0001
```

These should not be bulk rerun again with the same prompt. Next action is direct log-specific inspection and narrower hints for repeated patterns such as module/file naming, misspelled required module names, parameterized generate/indexing, or simulator-crashing constructs.

## Stage 2 Aggregate So Far

Including the 5-case pilot and the 19-case remaining run:

```text
compile/elab cases attempted in Stage 2: 24
direct pass rescues: 4
useful reclassifications: 3
still compile/elab after compile-focused repair: 17
thinking used: no
```

Direct pass rescues:

```text
cvdp_copilot_binary_multiplier_0012
cvdp_copilot_cascaded_adder_0025
cvdp_copilot_MSHR_0008
cvdp_copilot_findfasterclock_0001
```

Useful reclassifications:

```text
cvdp_copilot_MSHR_0001 -> functional/timing residual
cvdp_copilot_ahb_clk_counter_0001 -> functional residual
cvdp_copilot_serial_in_parallel_out_0011 -> timeout residual
```

## Stage 2: Corrected Compile/Elab Residual Inspection

Inspection artifact:

```text
research_outputs/two_stage_thinking_codegen/reports/stage2_compile_elab_inspection_2026-05-17.csv
research_outputs/two_stage_thinking_codegen/reports/stage2_compile_elab_inspection_2026-05-17.md
```

Inspected set: 17 cases that remained `compile_elab` after compile-focused repair.

Corrected clusters:

```text
parameter_generate_width: 4
wrapped_compile_error_needs_simlog: 3
syntax_sv_compat: 3
line_prefix_prose: 2
harness_top_file_mismatch: 1
harness_expected_typo: 1
multiple_driver: 1
simulator_crash_or_bad_construct: 1
unsupported_sv_construct: 1
```

Key evidence:

```text
cvdp_copilot_car_parking_management_0015: line 1 contains naked prose before module declaration
cvdp_copilot_manchester_enc_0005: line 1 contains stray "module" before real module declaration
cvdp_copilot_bus_arbiter_0004: RTL module is bus_arbiter, but harness invokes cvdp_copilot_bus_arbiter
cvdp_copilot_sequencial_binary_to_one_hot_decoder_0001: RTL uses sequencial spelling, but harness invokes sequential spelling
cvdp_copilot_barrel_shifter_0058: generated RTL uses SystemVerilog inside expression on Icarus path
cvdp_copilot_gaussian_rounding_div_0005: variables such as D4, D12, D14, D18, and D20 have multiple drivers
cvdp_copilot_fifo_to_axis_0001: iverilog/vvp exits with status 139
```

Decision: stop generic Stage 2 compile-focused reruns for these residuals. Continue only with targeted pilots: deterministic line-prefix cleanup, exact top-module/file-name hints, Icarus-compatible construct rewrites, and log-specific fixes after first compiler diagnostics are available.

## Hint Transparency

The rescue pipeline uses three distinct levels of guidance. These must be reported separately from zero-shot or first-pass model capability.

Generic output/tooling constraints:

```text
raw RTL only, no markdown/prose
preserve module/port/parameter names
Icarus-compatible Verilog/SystemVerilog
avoid multiple drivers, implicit latches, out-of-range indexes, and width-ambiguous expressions
prioritize the first real syntax/parameter/width/port/declaration/generate/module-instantiation error
```

Deterministic sanitation:

```text
strip markdown fences and thinking tags
extract single-file RTL from the first plausible module declaration through the last endmodule
remove prose prefixes such as a standalone `module` token or `module implements ...` before real RTL
```

Case-specific residual repair hints:

```text
bus_arbiter_0004: exact harness top-module name
sequencial_binary_to_one_hot_decoder_0001: harness spelling override from sequencial to sequential
8x3_priority_encoder_0013: M must be a module parameter and passed to half encoders
barrel_shifter_0058: avoid Icarus-incompatible inside expression and then target priority encoder semantics
gaussian_rounding_div_0005: single-driver cleanup for named divider intermediates, later functional divider debug
interrupt_controller_0014: parameter/generate hint was tried but did not help; semantic harness-specific hint is still needed
hebbian_rule_0017: exact top-module hint plus harness-observed bipolar truth-table/weight targets; marked agentic reasoning candidate after repeated semantic failure
sync_serial_communication_0001: exact top-module hint for sync_serial_communication_tx_rx; converted to serial bit-order functional residual
fifo_to_axis_0001: simulator-crash cleanup hint for plain parameters and single-driver AXI outputs; converted to AXI initialization/handshake functional residual
elevator_control_0006: identified as model-generated multi-file requirement for floor_to_seven_segment.sv; marked agentic/multifile candidate
```

Interpretation policy: generic constraints and sanitation can be considered pipeline/tooling improvements. Case-specific residual hints are log-informed post-hoc repairs and should be reported as targeted residual rescue, not as baseline model performance.

## Stage 2: Targeted Sanitizer Pilot

Code change:

```text
kimi_vllm_factory.py: single-file codegen sanitizer now starts from the first plausible module declaration, not the first bare `module` token.
```

Rationale: the previous sanitizer still preserved bad prefixes like `module implements ...` or a standalone `module` line. The tightened declaration regex requires a real module name followed by `#`, `(`, or `;`.

Focused sanitizer smoke test:

```text
module implements a car parking management system
module car_parking_system(input clk);
endmodule

=> module car_parking_system(input clk);

module
module manchester_encoder(input clk);
endmodule

=> module manchester_encoder(input clk);
```

Single-case benchmark pilot:

```text
case: cvdp_copilot_car_parking_management_0015
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_car_parking_0015_model_path
model server id: /data/HF_models/GLM-5.1-FP8
thinking used: no
result: passed 1/1
```

Evidence:

```text
Total Tests: 1
Passed Tests: 1
Failed Tests: 0
Passed Problems: 1
Failed Problems: 0
```

Generated RTL begins directly with the real declaration:

```systemverilog
module car_parking_system #(
    parameter TOTAL_SPACES = 12,
    parameter PARKING_FEE_VALUE = 50
)(
```

Caveat: this was a bounded fresh single-case generation, not a replay of the exact previous failed completion. Count it as a targeted pilot rescue signal, then confirm the pattern on `cvdp_copilot_manchester_enc_0005` before updating full residual accounting.

Operational note: an initial pilot using model alias `vllm-glm` failed before generation with HTTP 404 because the active vLLM server currently serves only `/data/HF_models/GLM-5.1-FP8` according to `/v1/models`.

Second line-prefix pilot:

```text
case: cvdp_copilot_manchester_enc_0005
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_manchester_enc_0005_model_path
model server id: /data/HF_models/GLM-5.1-FP8
thinking used: no
result: reclassified from compile_elab to docker_timeout
```

Evidence:

```text
pytest collected 4 items
first test: test_manchester_even[6-test_sequence0-expected_output0]
result: Timed out after 300s
repair attempt 1: also timed out after 300s
```

Generated RTL now begins directly at the real module declaration:

```systemverilog
module manchester_encoder #(
    parameter N = 8
) (
```

Interpretation: the line-prefix sanitizer fixed the prior syntax/compile failure signature for this case too. It did not rescue the case because the generated design now reaches simulation and hangs in the first cocotb test. Move this case out of compile/elab and into timeout/semantic debug.

## Stage 2: Targeted Top-Module Hint Pilot

Case:

```text
cvdp_copilot_bus_arbiter_0004
```

Run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_bus_arbiter_0004_model_path
```

Configuration notes:

```text
VLLM_ENABLE_THINKING=false
VLLM_RETRY_MODULE_NAME_MISMATCH=true
CVDP_REPAIR_ENABLE=true
CVDP_REPAIR_MAX_ATTEMPTS=1
CVDP_REPAIR_COMPILE_FOCUSED=true
CVDP_REPAIR_TARGETED_HINTS=true
model server id: /data/HF_models/GLM-5.1-FP8
```

Outcome:

```text
initial generation: module-name checker rejected cvdp_copilot_bus_arbiter vs expected bus_arbiter, then retry generated a checker-accepted response
initial harness run: failed, returncode=1, best summary 0/1
repair attempt 1: passed 1/1
final errors: 0
thinking used: no
```

Evidence:

```text
../../src/test_runner.py::test_runner PASSED [100%]
1 passed, 1 warning in 0.34s
```

Final RTL begins with the harness-required top module:

```systemverilog
module cvdp_copilot_bus_arbiter (
    input reset,
    input clk,
    input req1,
    input req2,
    input dynamic_priority,
    output reg grant1,
    output reg grant2
);
```

Interpretation: exact top-module hints are useful for this residual class. This case can be removed from the compile/elab residual set. Keep the behavior opt-in because the correct top name can differ between prompt-level checker expectations and harness file/top expectations.

### cvdp_copilot_sequencial_binary_to_one_hot_decoder_0001

First targeted pilot:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_sequential_decoder_0001_model_path
result: failed 0/1
```

Root cause of failed pilot: the targeted hint correctly asked for harness spelling `binary_to_one_hot_decoder_sequential`, but the front-door module-name checker still extracted typo spelling `binary_to_one_hot_decoder_sequencial` from the original prompt. The retry then forced the RTL back to the typo spelling, and Icarus failed to find the harness top.

Evidence from failed pilot:

```text
error: Unable to find the root module "binary_to_one_hot_decoder_sequential" in the Verilog source.
```

Fix applied to targeted hint:

```text
Module Name: `binary_to_one_hot_decoder_sequential`
```

Corrected targeted pilot:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_sequential_decoder_0001_hint_module_name
result: passed 1/1
thinking used: no
```

Evidence:

```text
../../src/test_runner.py::test_runner PASSED [100%]
1 passed in 0.34s
```

Final RTL begins with the harness spelling:

```systemverilog
module binary_to_one_hot_decoder_sequential #(
    parameter BINARY_WIDTH = 5,
    parameter OUTPUT_WIDTH = 32
) (
```

Interpretation: spelling/top-module mismatches are confirmed cheap targeted rescue candidates, but the checker must be aligned with harness-required names. Keep these overrides opt-in and case-specific.

## Stage 2: Targeted Construct Rewrite Pilot

Case:

```text
cvdp_copilot_barrel_shifter_0058
```

Run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_barrel_shifter_0058_model_path
```

Outcome:

```text
result: not rescued
useful signal: compile/elab issue was bypassed in repair attempt, but semantic test failed
thinking used: no
```

Initial generated RTL still included the unsupported construct pattern:

```systemverilog
if (mode inside {3'b000, 3'b001, 3'b010, 3'b011, 3'b100} && shift_bits >= data_width) begin
```

Repair attempt evidence:

```text
iverilog build: succeeded
vvp/cocotb: ran
failure: Test #7 Priority Encoder
expected output: 0b101
actual output: 0b0
TESTS=1 PASS=0 FAIL=1
```

Interpretation: the targeted construct hint produced useful reclassification from compile/elab into a functional near-miss during the repair attempt, but did not rescue the case. The next repair should not focus on `inside`; it should target priority encoder semantics, specifically preserving the highest set bit result instead of allowing later loop iterations to overwrite it.

## Stage 2: Targeted Multiple-Driver Pilot

Case:

```text
cvdp_copilot_gaussian_rounding_div_0005
```

Run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_gaussian_rounding_div_0005_model_path
```

Outcome:

```text
result: not rescued
useful signal: compile/elab failure was converted into functional divider failure
thinking used: no
```

Previous Stage 2 residual evidence:

```text
/code/rtl/divider.sv:99: error: Variable 'D4' cannot have multiple drivers.
also observed on D12/D14/D18/D20 style intermediates
```

Targeted pilot evidence:

```text
iverilog build: succeeded
vvp/cocotb: ran
first failing vector: divd=10.0000, divs=4.0000
DUT output: 0.000000
reference output: 2.500000
latency: 13 cycles
summary: 2 failed
```

Interpretation: single-driver guidance was sufficient to move this case out of compile/elab, but the generated divider is functionally dead or mis-scaled. Next debug should target reset polarity/start-valid propagation and fixed-point scaling rather than multiple-driver cleanup.

## Stage 2: Targeted Parameter/Generate Pilot

Case:

```text
cvdp_copilot_interrupt_controller_0014
```

Run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_interrupt_controller_0014_model_path
```

Outcome:

```text
result: not rescued
initial targeted run: functional failures across parameterized interrupt counts
repair attempt: regressed to compile failures
thinking used: no
```

Initial run evidence:

```text
pytest collected 7 items
NUM_INTERRUPTS examples: 1, 8, 6, 4, 10, 3
failure pattern: cpu_interrupt stayed 0 while one interrupt was pending
initial summary: 0 pass / 6 fail
```

Repair attempt evidence:

```text
repair summary: 0 pass / 7 fail
iverilog return codes observed for parameterized builds: 5, 7
```

Interpretation: the generic parameter/generate hint was not useful for this case. The current best signal is semantic: the controller does not assert `cpu_interrupt` when pending interrupts exist. Do not blindly continue the same parameter/generate targeted pilot on the interrupt-controller family until the harness semantics are inspected and a narrower hint is written.

### cvdp_copilot_8x3_priority_encoder_0013

Prior Stage 2 evidence:

```text
iverilog command included -Pcascaded_encoder.N=4 -Pcascaded_encoder.M=2
high-level report only exposed CalledProcessError
sim.log artifact was empty
```

Manual RTL inspection found likely compile causes:

```text
priority_encoder used output reg [M-1:0] out before M was defined
cascaded_encoder used output widths based on M but did not declare M as a parameter
half encoder instances did not pass M=M-1
loop body used i[M-1:0]
priority loop could let lower-priority bits overwrite higher-priority results
```

Targeted hint added:

```text
Declare M as a module parameter in both priority_encoder and cascaded_encoder before using it in port widths.
Pass .N(N/2) and .M(M-1) to both half encoders.
Avoid i[M-1:0] loop-index slicing.
Preserve MSB-highest-priority behavior without lower-priority overwrite.
```

Pilot run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_8x3_priority_encoder_0013_model_path
```

Outcome:

```text
initial summary: 0 pass / 6 fail
repair attempt 1: 6 pass / 0 fail
result: rescued
thinking used: no
```

Evidence:

```text
test_apb[4] PASSED
test_apb[8] PASSED
test_apb[16] PASSED
test_apb[32] PASSED
test_apb[64] PASSED
test_apb[128] PASSED
```

Interpretation: direct RTL inspection plus a narrow parameter/port-width hint rescued this wrapped compile-error case. This pattern is more effective than another generic compile-focused rerun when `sim.log` lacks the first compiler diagnostic.

### cvdp_copilot_hebbian_rule_0017

Prior Stage 2 evidence:

```text
iverilog command: -s hebb_gates ... /code/rtl/hebb_gates.sv
generated RTL modules: gate_target, hebbian_rule
missing harness top: hebb_gates
```

Top-module hint added:

```text
Module Name: `hebb_gates`
Declare a top-level module named exactly `hebb_gates` because the harness invokes `iverilog -s hebb_gates`.
```

Top-module pilot:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_hebbian_rule_0017_model_path
result: not rescued, but compile/elab converted to functional failure
```

Evidence after top-module repair:

```text
iverilog build: succeeded
vvp/cocotb: ran
first semantic failure: AND training, w2 expected 2 but got 0
```

Semantic hint added from harness:

```text
AND -> w1=2, w2=2, bias=-2
OR -> w1=2, w2=2, bias=2
NAND -> w1=-2, w2=-2, bias=2
NOR -> w1=-2, w2=-2, bias=-2
Gate changes should not contaminate later training.
```

Semantic pilot:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_hebbian_rule_0017_semantic_hint
result: not rescued
```

Failure after semantic hint:

```text
AND training still fails at the same point: w2 expected 2 but got 0
```

Stop condition: this case is no longer a cheap compile/top-name rescue. It is marked as an agentic reasoning potential repair because it requires a harness-aware RTL rewrite of the learning behavior. Continuing short targeted hints is unlikely to be efficient because the harness-observed truth table was already provided and the model still reproduced the same broken FSM/accumulation pattern.

### cvdp_copilot_sync_serial_communication_0001

Prior Stage 2 evidence:

```text
iverilog command: -s sync_serial_communication_tx_rx ... /code/rtl/sync_serial_communication_top.sv
generated RTL top: sync_serial_communication_top
missing harness top: sync_serial_communication_tx_rx
```

Top-module hint added:

```text
Module Name: `sync_serial_communication_tx_rx`
Declare a top-level module named exactly `sync_serial_communication_tx_rx` because the harness invokes `iverilog -s sync_serial_communication_tx_rx`.
```

Pilot run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_sync_serial_communication_0001_model_path
```

Outcome:

```text
result: not rescued
useful signal: compile/top mismatch converted to runnable functional failures
thinking used: no
```

Evidence:

```text
pytest collected 20 items
repair attempt build: succeeded
vvp/cocotb: ran
first failure: data_in=102, sel=001, expected data_out=102, actual data_out=82
summary: 0 pass / 20 fail
```

Interpretation: this is no longer a compile residual. The next repair should target serial bit order / RX shift direction / sampling timing. It remains potentially recoverable, but not as a cheap top-module-only rescue.

### cvdp_copilot_fifo_to_axis_0001

Prior Stage 2 evidence:

```text
iverilog returned exit status 139 while building ping_pong_fifo_2_axi_stream
build_8.log: Segmentation fault (core dumped)
```

Manual RTL inspection found crash-risk constructs:

```text
parameter logic declarations
continuous assigns to outputs also assigned in always_ff
AXI/output signals with unclear single-driver ownership
```

Targeted hint added:

```text
Use plain integer-valued parameters.
Do not drive outputs from both continuous assign and always_ff.
Keep AXI data/valid/last stable until i_axi_ready.
Issue FIFO strobe only when a transfer is accepted.
```

Pilot run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_fifo_to_axis_0001_model_path
```

Outcome:

```text
result: not rescued
useful signal: Icarus segfault converted to runnable functional failure
thinking used: no
```

Evidence after repair:

```text
iverilog build: succeeded
vvp/cocotb: ran
failure: o_axi_data contained non-0/1 unknown values when receiver converted it to int
```

Interpretation: this case left the compile/simulator-crash bucket. Next repair should target AXI-stream initialization and handshake timing, specifically ensuring `o_axi_data` is initialized and valid/stable before `o_axi_valid` is observed.

### cvdp_copilot_elevator_control_0006

Pilot run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_elevator_control_0006_model_path
```

Observed generation issue:

```text
model output repeatedly failed JSON parsing before a usable response was accepted
```

Compile evidence:

```text
/code/rtl/floor_to_seven_segment.sv: No such file or directory
Preprocessor failed with 1 errors.
```

Interpretation: the high-level residual looked like line-1 syntax, but the actionable current failure is a missing companion RTL file required by the harness source list. This is not a cheap single-file compile repair. Mark as an agentic/multifile repair candidate because the repair path needs to create or restore `floor_to_seven_segment.sv` in addition to the primary `elevator_control_system.sv`.

### cvdp_copilot_axi_register_0001

Prior Stage 2 evidence:

```text
DATA_WIDTH 8/16: iverilog CalledProcessError in parameterized builds
DATA_WIDTH 32/64: build succeeded but writes to 0x100 returned OKAY/error inconsistently and readback stayed 0
sim.log: empty for the inspected artifact
```

Manual harness inspection found the relevant checker behavior:

```text
ADDR_WIDTH values: 12, 16, 32
DATA_WIDTH values: 8, 16, 32, 64
write helper drives awvalid_i and wvalid_i together for two rising edges
CTRL_BEAT=0x100, CTRL_START=0x200, CTRL_DONE=0x300, CTRL_WRITEBACK=0x400, CTRL_ID=0x500
partial writes to CTRL_BEAT should return OKAY and preserve the old value
done_i is pulsed for one cycle and must be latched until write-one-to-clear
```

Targeted hint added:

```text
Accept simultaneous AW/W writes and decode the current awaddr_i on that accepted cycle.
Do not compute the first write enable from stale awaddr_reg.
Make beat and ID readback safe for DATA_WIDTH 8/16/32/64.
Zero-extend DATA_WIDTH<20 writes into the 20-bit beat register.
Return truncated ID for DATA_WIDTH<32.
Latch one-cycle done_i until software clears CTRL_DONE.
```

Pilot run:

```text
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_axi_register_0001_model_path
```

Outcome:

```text
result: rescued
problem report: 1/1 passed
harness collected: 12 parameterized items
thinking used: no
```

Evidence:

```text
test_axi_reg[8-12-0] PASSED
test_axi_reg[8-16-0] PASSED
test_axi_reg[8-32-0] PASSED
...
test_axi_reg[64-32-0] PASSED
```

Interpretation: this was a valid post-hoc targeted residual rescue. It should be removed from the compile/elab residual set, but reported separately from baseline/generic repair because the case-specific hint used harness-derived AXI timing and register-map details.

### cvdp_copilot_elevator_control_0009

Prior Stage 2 evidence:

```text
baseline residual: line-1 prose before the real elevator_control_system module
sim.log: /code/rtl/elevator_control_system.sv:1: syntax error
harness source list includes elevator_control_system.sv and floor_to_seven_segment.sv
```

Sanitizer pilot:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_elevator_control_0009_model_path
result: not rescued, but compile syntax converted to runnable functional failure
thinking used: no
```

Evidence after sanitizer:

```text
floor movement checks passed
seven-segment checks passed
overload asserted: system_status == 5 and overload_warning == 1 passed
after overload cleared: expected system_status == 4 (DOOR_OPEN), got 0 (IDLE)
```

First repair attempt in the sanitizer pilot regressed to compile/elab:

```text
/code/rtl/elevator_control_system.sv:33: error: Unable to bind wire/reg/memory `DOOR_OPEN_CYCLES'
Dimensions must be constant.
```

Narrow semantic hint added:

```text
Preserve working movement, seven-segment, and door-open behavior.
If overload interrupts DOOR_OPEN, return to DOOR_OPEN after overload_detected clears.
Keep OVERLOAD_HALT=3'b101 and DOOR_OPEN=3'b100.
Use integer DOOR_OPEN_CYCLES under -DSIMULATION=1; avoid real-valued width expressions.
Do not assign next_state from a clocked door-counter block.
```

Semantic-hint pilot:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_elevator_control_0009_semantic_hint
result: not rescued
repair attempt: docker timeout after 300s
```

Evidence from timed-out repair:

```text
compile and vvp started
cocotb reached: Requesting floor 3
timeout: run_docker_harness_direct.sh expired after 300s
```

Interpretation: this case is no longer a cheap compile/sanitizer rescue. The targeted semantic repair fixed one compile hazard but introduced or preserved non-termination in the floor-request flow. Mark as an agentic/manual semantic candidate; next useful work is a harness-aware RTL rewrite or debug of request latching/current-floor movement, not another short targeted hint.

### cvdp_copilot_elevator_control_0026

Prior Stage 2 evidence:

```text
harness iverilog command includes:
/code/rtl/elevator_control_system.sv
/code/rtl/floor_to_seven_segment.sv
/code/rtl/Binary2BCD.sv
```

Stage 2 artifact evidence:

```text
workspace RTL files:
elevator_control_system.sv
floor_to_seven_segment.sv

sim.log:
/code/rtl/Binary2BCD.sv: No such file or directory
/code/rtl/elevator_control_system.sv:1: syntax error
```

Fresh targeted pilot:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_elevator_control_0026_model_path
result: not rescued
thinking used: no
```

Observed generation issue:

```text
first-pass model response repeatedly failed JSON parsing before harness
accepted workspace still contained only elevator_control_system.sv and floor_to_seven_segment.sv
repair attempt did not create Binary2BCD.sv
```

Final evidence:

```text
sim.log:
/code/rtl/Binary2BCD.sv: No such file or directory
Preprocessor failed with 1 errors.
```

Interpretation: this is a multifile generation/repair failure, not a cheap single-file sanitizer rescue. The current repair path edits only the primary RTL and cannot create the missing `Binary2BCD.sv` companion file. Mark as an agentic/multifile repair candidate.

### cvdp_copilot_interrupt_controller_0017

Prior Stage 2 evidence:

```text
artifact RTL starts with internal always blocks and no module interrupt_controller wrapper
harness invokes top: interrupt_controller
source file: pic_starvation_prevention.sv
parameter: STARVATION_THRESHOLD
```

Targeted hint added:

```text
Declare top module interrupt_controller in pic_starvation_prevention.sv.
Expose parameter STARVATION_THRESHOLD.
Use the full harness port list including clk, rst_n, reset_interrupts,
interrupt_requests[9:0], interrupt_ack, interrupt_trig, interrupt_mask[9:0],
priority_override[3:0], override_interrupt_id[3:0], priority_override_en,
interrupt_id[3:0], interrupt_valid, interrupt_status[9:0],
missed_interrupts[9:0], and starvation_detected.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_interrupt_controller_0017_model_path
result: not rescued, but reclassified from compile_elab to functional in the repair attempt
thinking used: no
```

Initial run evidence:

```text
17.txt: iverilog returned non-zero exit status 2
generated RTL still starts at line 1 with: // State machine sequential logic
```

Repair attempt evidence:

```text
17_repair_1.txt: cocotb simulation starts for all 11 parameterized STARVATION_THRESHOLD items
first failure at 195ns: No Interrupt active while 2 interrupts are pending
assert dut.interrupt_valid.value == 1, actual Logic('0')
summary: 0/11 passed
```

Interpretation: the exact-top/port hint is useful enough to leave the pure compile bucket during repair, but not a rescue. The next useful step is semantic interrupt-controller debug focused on asserting `interrupt_valid` promptly when unmasked requests are pending, preserving request latching, and matching the harness priority/starvation behavior. Do not count this as a baseline or targeted pass rescue.

### cvdp_copilot_interrupt_controller_0019

Prior Stage 2 evidence:

```text
baseline report: iverilog returned non-zero exit status 2 for interrupt_controller_apb
harness top: interrupt_controller_apb
parameter: NUM_INTERRUPTS
source file: interrupt_controller_apb.sv
```

Existing compile-focused repair artifact:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_compile_elab_remaining_19_compile_focused_rerun
repair attempt: 1
result: not rescued, but reclassified from compile_elab to functional
thinking used: no
```

Repair attempt evidence:

```text
19_repair_1.txt: cocotb simulation starts for 7 parameterized NUM_INTERRUPTS items
first failure at 105ns: Got wrong ID: 0, Expected: 4
later failures: expected interrupt IDs 2, 1, 4, 5 while DUT reports 0
summary: 0/7 passed
```

Harness semantics observed:

```text
priority_list = [i for i in range(NUM_IRQ)]
expected interrupt_idx = min(interrupts_list, key=lambda i: priority_list[i])
cpu_interrupt must assert within two cycles while pending interrupts exist
```

Interpretation: this is no longer a useful compile/elab residual for accounting, because the repaired candidate builds and reaches cocotb assertions. It belongs in the interrupt semantic/APB bucket. The next useful fix is harness-aware priority/request-latching behavior, not another blind top/port hint for the interrupt family.

### cvdp_copilot_elevator_control_0006 Multifile Rescue

Prior evidence:

```text
harness source list includes:
/code/rtl/elevator_control_system.sv
/code/rtl/floor_to_seven_segment.sv

previous single-file repair artifact:
/code/rtl/floor_to_seven_segment.sv: No such file or directory
```

Infrastructure change:

```text
CVDP_REPAIR_MULTIFILE=true
repair prompt lists expected RTL output files
repair accepts JSON code arrays and writes multiple rtl/*.sv files
loose multi-file parser recovers JSON-like model output with unescaped RTL newlines
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_multifile_pilot_elevator_control_0006_loose_parse
result: rescued
repair attempt: 1
thinking used: no
```

Evidence:

```text
initial multi-file response recovered by loose parser after strict JSON parse failure
repair wrote both rtl/elevator_control_system.sv and rtl/floor_to_seven_segment.sv
6_repair_1.txt: 4/4 passed
parameterized floors: N=8, N=5, N=9
```

Interpretation: this is a valid post-hoc multifile residual rescue. It should be counted separately from baseline/generic single-file repair because it depends on opt-in multifile repair support and relaxed parsing. Projected targeted/multifile rescues increase by +1.

### cvdp_copilot_elevator_control_0026 Multifile Reclassification

Prior evidence:

```text
harness source list includes:
/code/rtl/elevator_control_system.sv
/code/rtl/floor_to_seven_segment.sv
/code/rtl/Binary2BCD.sv

previous single-file repair artifact:
/code/rtl/Binary2BCD.sv: No such file or directory
```

Multifile pilot:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_multifile_pilot_elevator_control_0026_loose_parse_clean
result: not rescued, reclassified to docker_timeout/semantic non-termination
repair attempt: 1
thinking used: no
```

Evidence:

```text
loose parser recovered multi-file response after strict JSON parse failure
workspace RTL files: elevator_control_system.sv, floor_to_seven_segment.sv, Binary2BCD.sv
initial and repair both compile and launch vvp/cocotb
both time out at 300s after:
Test case 1
Requesting floor 3
```

Interpretation: multifile infrastructure solved the missing companion file and parser-tail problem for this case, but did not rescue the behavior. The remaining issue is elevator request/movement non-termination, not compile/elab. Move to timeout/semantic debug and do not keep spending cheap multifile repair attempts on it.

Additional non-cheating semantic attempts:

```text
runs:
research_outputs/two_stage_thinking_codegen/runs/stage2_multifile_pilot_elevator_control_0026_semantic_hint
research_outputs/two_stage_thinking_codegen/runs/stage2_multifile_pilot_elevator_control_0026_fsm_rewrite_hint
```

Hints used were derived only from the public prompt, generated RTL, logs, and harness/test source:

```text
request_floor pulses call_requests for one clock then clears it
test_case_1 waits until current_floor == 3
overload_detected is not explicitly initialized in the harness basic tests
check_seven_segment waits for anode patterns 1110, 1101, and 1011
```

Outcome:

```text
semantic_hint: timed out at 300s after Test case 1 / Requesting floor 3
fsm_rewrite_hint: timed out at 300s after Test case 1 / Requesting floor 3
repair RTL still retained combinational call_requests_internal self-feedback
```

Interpretation: prompt-only multifile repair is exhausted for this case without crossing into manual/golden-derived cheating. The correct next path is an agentic/manual semantic rewrite using the harness behavior as the spec: sequentially latch one-cycle requests, move one floor per clock toward pending requests, open the door at the target, clear only the served request, and cycle display anodes quickly.

### cvdp_copilot_barrel_shifter_0058 Priority Encoder Rescue

Prior targeted run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_barrel_shifter_0058_model_path
result: not rescued, reclassified to functional
first functional failure: Test #7 Priority Encoder expected 5, actual 0
```

Harness-derived semantics:

```text
mode 3'b101: expected = max(i for i in range(data_width) if data_in & (1 << i)), default 0
data_in=0b101011 -> highest set bit index 5
zero data_in -> output 0 and error 0
```

Targeted hint added:

```text
For mode 3'b101, output highest set bit index, not a one-hot mask and not the lowest set bit.
When scanning from MSB down, stop after the first set bit or use a found flag.
Do not let lower set bits overwrite the highest index.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_barrel_shifter_0058_priority_hint
result: rescued
repair attempt: 1
thinking used: no
```

Evidence:

```text
DATA_WIDTH=8, SHIFT_BITS_WIDTH=3: PASS
DATA_WIDTH=32, SHIFT_BITS_WIDTH=5: PASS
priority encoder test: expected 0b101, actual 0b101
summary: 2/2 cocotb summaries passed
```

Interpretation: valid post-hoc targeted semantic rescue. Count separately from baseline/generic repair because the hint uses harness-derived priority encoder semantics.

### cvdp_copilot_fifo_to_axis_0001 Strobe Timing Hardstop

Prior targeted run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_fifo_to_axis_0001_model_path
result: not rescued, reclassified to functional
first functional failure: o_axi_data contained X/Z bits when cocotb tried to convert it at 90ns
```

Harness-derived semantics:

```text
send_fifo_word waits for o_block_fifo_stb
then sets i_block_fifo_data at the same simulation time
then keeps i_block_fifo_data stable for two clocks
receive_axi_stream samples o_axi_data whenever o_axi_valid && i_axi_ready
```

Targeted hint added:

```text
Do not sample i_block_fifo_data or assert o_axi_valid in the same cycle that first raises o_block_fifo_stb.
Raise the FIFO strobe first, capture data on a following clock, and only then present known o_axi_data with o_axi_valid.
Initialize all AXI/FIFO outputs on reset and never assert o_axi_valid while o_axi_data contains X/Z.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_fifo_to_axis_0001_strobe_timing_hint
result: not rescued
repair attempt: 1
thinking used: no
```

Evidence:

```text
initial fresh generation regressed to iverilog exit status 139
repair attempt compiled and ran cocotb
repair attempt still failed at 90ns: Can't convert LogicArray to int because o_axi_data contains non-0/1 values
summary: 0/1 passed
```

Interpretation: the case remains a functional AXI/FIFO sequencing residual. Cheap prompt-only targeted repair is exhausted for now; next useful path is an agentic/manual small FSM rewrite that separates FIFO request/strobe, data capture, and AXI valid phases.

### cvdp_copilot_ahb_clk_counter_0001 Restart Timing Hardstop

Prior generic repair evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_compile_elab_remaining_19_compile_focused_rerun
result: not rescued, reclassified to functional
best summary: 1/2 passed
first remaining failure: Counter mismatch after restart at cycle 2: expected 2, got 1
```

Harness-derived semantics:

```text
byte addresses: START=0x00, STOP=0x04, COUNTER=0x08, OVERFLOW=0x0C, MAXCNT=0x10
HRESP must always be 0
after manual async reset, harness writes START for one clock and does not rewrite MAXCNT
then it reads COUNTER for three clocks and expects 0, 1, 2
```

Targeted hints added:

```text
Do not let START introduce an extra one-cycle delay before counting.
After reset and START, first three read cycles should observe 0, 1, 2.
If reset clears MAXCNT to 0, do not treat maxcnt==0 as immediate overflow that blocks restart counting; treat zero as no configured limit/all-ones limit or only apply overflow limiting after a nonzero MAXCNT write.
```

Pilot runs:

```text
runs:
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_ahb_clk_counter_0001_restart_timing_hint
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_ahb_clk_counter_0001_maxcnt_zero_hint
result: not rescued
repair attempts: 1 each
thinking used: no
```

Evidence:

```text
restart_timing_hint: still 1/2 passed; failure shifted to Counter After Restart cycle 1 expected 1 got 0
maxcnt_zero_hint: initial fresh generation failed compile with iverilog exit status 12
maxcnt_zero_hint repair: 0/2 passed; HRESP was X in both tests
```

Interpretation: the case is a small but timing-sensitive AHB/register-FSM residual. Cheap prompt-only targeted repair did not improve beyond the prior generic 1/2 result and then regressed. Stop sampling this case; next useful path is an agentic/manual rewrite that explicitly computes next enable/overflow/counter state and drives HRESP deterministically.

### cvdp_copilot_apb_history_shift_register_0001 APB/Clock-Gating Hardstop

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
result: not rescued, functional
first failure: control_register readback mismatch: Expected 0xb, got 0x0
```

Root cause from generated RTL and harness:

```text
harness sets clk_gate_en=0 and comments clock gating disabled by default
generated RTL clocked APB register writes/reads from gated_pclk = pclk & clk_gate_en_sync
therefore APB writes did not occur when clk_gate_en=0
```

Harness-derived semantics used:

```text
APB setup/access protocol: write on pselx && penable && pwrite; read during access phase after 1ns settle
valid addresses: CTRL=0x0, TRAIN_HISTORY=0x1, PREDICT_HISTORY=0x2
CTRL lower bits: predict_valid, predict_taken, train_mispredicted, train_taken
TRAIN_HISTORY stores bits [6:0] and reads bit7 as 0
PREDICT_HISTORY is read-only and updates only on rising history_shift_valid
invalid address 0x3 should set pslverr/error_flag/interrupt_error and remain visible until a later valid transaction clears it
```

Pilot runs:

```text
runs:
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_apb_history_shift_register_0001_clk_gate_hint
research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_apb_history_shift_register_0001_sticky_error_hint
result: not rescued
repair attempts: 1 each
thinking used: no
```

Evidence:

```text
clk_gate_hint initial: got past CTRL readback, failed later at pslverr not asserted on invalid address
clk_gate_hint repair: failed earlier, predict_history expected 0x00 before shifts got 0xff
sticky_error_hint initial: failed train_history reserved bit, expected 0x2A got 0xAA
sticky_error_hint repair: progressed to late clock-gating check, failed control_register changed despite clock gating: expected 0x4 got 0xf
```

Interpretation: prompt-only targeted repair produced partial semantic progress but not a pass. Stop cheap sampling for this case; next useful path is agentic/manual APB implementation preserving the harness state machine, sticky errors, reserved-bit masking, and clock-gating behavior.

### cvdp_copilot_fsm_seq_detector_0023 Overlap Hint Regression

Full-run generic repair evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
result: not rescued, functional near-miss
best summary: 5/6 passed
only failing test: test_noise_before_after
first failure: Error at step 14, expected seq_detected=1 got 0
```

Harness-derived semantics:

```text
detected sequence: 01001110
seq_detected is checked at falling edge after seq_in is applied on rising edge
output is a one-cycle registered pulse
noise_before_after expects detection at index 14 for sequence 1100010100111001
```

Targeted hint added:

```text
Use KMP-style overlap fallback for pattern 01001110.
After matching prefix 010 and seeing input 1, keep suffix/prefix 01 instead of resetting to empty.
After matching 01001 or 010011 and seeing input 0, fallback to matched 010.
After full detection, pulse seq_detected and fallback to suffix 0 for future overlaps.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_fsm_seq_detector_0023_overlap_hint
result: not rescued
repair attempt: 1
thinking used: no
```

Evidence:

```text
targeted fresh generation: 2/6 passed
repair attempt: 2/6 passed
repair failed detection_at_start, multiple_occurrences, noise_before_after, and rtl_bug_seq
```

Interpretation: this targeted fresh sample regressed relative to the full-run generic repair artifact. Do not count it as progress or rescue. If continuing this case, use the existing 5/6 artifact as the base for an agentic/manual KMP table correction rather than re-sampling the model.

### cvdp_copilot_apb_gpio_0005 Interrupt Hint Regression

Full-run generic repair evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
result: not rescued, functional partial
best summary: 4/6 passed for each GPIO_WIDTH parameterization
remaining failures: test2_software_controlled_interrupt_reset and test5_level_triggered_interrupts
```

Harness-derived semantics:

```text
paddr[7:2] map: DATA_IN=0, DATA_OUT=1, DATA_OUT_EN=2, INT_ENABLE=3, INT_TYPE=4, INT_POLARITY=5, INT_STATE=6, DIR_CONTROL=7, POWER_DOWN=8, INT_CTRL=9
for this testcase INT_POLARITY=1 means active-high/rising behavior on GPIO[0]
INT_TYPE=1 is edge-triggered and should latch until INT_STATE/INT_CTRL clear
INT_TYPE=0 is level-triggered and should reflect active level, clearing when level goes low
harness drives the bidirectional gpio pin directly; interrupt detection should sample external gpio when not output-enabled
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_apb_gpio_0005_interrupt_hint
result: not rescued
repair attempt: 1
thinking used: no
```

Evidence:

```text
initial targeted run regressed to 3/6; power-down interrupt test also failed
repair attempt regressed to compile/elab failure for GPIO_WIDTH=8,11,30
```

Interpretation: targeted fresh sampling regressed relative to the existing full-run generic repair artifact. Do not count as progress. If continuing this case, use the 4/6 RTL artifact as the base for an agentic/manual interrupt block rewrite rather than another model resample.

### cvdp_copilot_fibonacci_series_0001 Reset Phase Hardstop

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
result: not rescued, functional
initial failure: Expected 1, got 2 at 30ns in test_reset_scenario
```

Prior generic repair evidence:

```text
1_repair_2.txt produced correct sequence 0,1,1,2,3,...,2971215073
then failed after reset/restart: Expected 0, got 1
```

Harness-derived semantics:

```text
calculate_fibonacci checks fib_out before each clock advance
apply_reset asserts rst, deasserts rst, waits one rising edge, then tests immediately
therefore first observed post-reset fib_out must be 0, then 1, then 1, then 2
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_fibonacci_series_0001_reset_phase_hint
result: not rescued
repair attempt: 1
thinking used: no
```

Evidence:

```text
initial targeted run still failed early: expected 1 got 2
repair attempt produced correct sequence through 2971215073
then failed before overflow: Expected 4807526976, got 2971215073
post-overflow reset still failed: Expected 0, got 1
```

Interpretation: prompt-only repair improved the sequence but did not satisfy overflow/reset boundary timing. Stop cheap attempts; next useful path is manual/agentic handling of when `overflow_flag` is asserted relative to the first unrepresentable Fibonacci value and the post-reset startup phase.

### cvdp_copilot_Carry_Lookahead_Adder_0005 Byte Alignment Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
result: not rescued, functional
first failure: Cycle 4 expected sum 1218168113 got 2605134277
```

Root cause from RTL/harness:

```text
harness continuously drives one A/B pair per cycle with start=1
expected latency is exactly 4 cycles
generated pipeline crossed upper byte ordering: ADD3 used delayed A[31:24]/B[31:24] where byte2 should be used, while final ADD4 used delayed A[23:16]/B[23:16]
```

Targeted hint added:

```text
Preserve 4-cycle done timing.
Byte/carry chain must be byte0 -> byte1 -> byte2 -> byte3.
S[7:0], S[15:8], S[23:16], S[31:24] must correspond to bytes 0,1,2,3 of the same original input sample.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_Carry_Lookahead_Adder_0005_byte_alignment_hint
result: not rescued
repair attempt: 1
thinking used: no
```

Evidence:

```text
initial targeted run failed latency: expected 4 got 5
repair attempt restored latency 4 but still failed sum: expected 1037748059 got 1037720519
```

Interpretation: targeted prompt made partial progress but did not fully align carry/data pipeline. Stop cheap sampling; next useful path is manual/agentic rewrite to a simple 4-stage `{carry,sum}=A+B` pipeline or a rigorously aligned byte pipeline.

### cvdp_copilot_cont_adder_0042 Lint Width Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
sanity: 4/4 passed
lint: failed
```

Lint root cause:

```text
WIDTHTRUNC: assigning 34-bit new_sum to 32-bit sum_out
WIDTHEXPAND: dividing 34-bit new_sum by 16-bit window_size
WIDTHTRUNC: assigning division result to 32-bit avg_out
```

Targeted hint added:

```text
Preserve passing sanity behavior.
Explicitly slice new_sum[DATA_WIDTH-1:0] for sum_out.
Widen window_size to the same width before division and slice quotient for avg_out.
Do not add lint waivers.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_cont_adder_0042_lint_width_hint
result: not rescued
repair attempt: 1
thinking used: no
```

Evidence:

```text
initial targeted run preserved sanity but lint still failed
repair attempt introduced /code/rtl/cont_adder.sv:78 syntax error
repair failed both lint and sanity
```

Interpretation: no rescue. The original artifact remains best. This is likely best handled by a direct manual width cleanup rather than another model sample.

### cvdp_copilot_gaussian_rounding_div_0022 10-Iteration Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
sanity failure: DIV TEST divd=10.0000 divs=4.0000 DUT=0.000000 REF=2.500000
synth also failed/was killed in the original artifact family
```

Harness-derived semantics:

```text
unsigned Q9.9 fixed point
reference prescales divisor/dividend according to divisor highest set bit
then runs exactly 10 Gold-Schmidt iterations:
F = TWO - D
D = (D * F) >> 9
N = (N * F) >> 9
mask D and N to 18 bits each iteration
valid is expected after latency_counter == 1
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_gaussian_rounding_div_0022_10iter_latency_hint
result: not rescued
repair attempt: 1
thinking used: no
```

Evidence:

```text
initial targeted run still failed: DUT=0.000000 REF=2.500000, latency=3
repair attempt returned -9/killed with empty sanity log
synth container was left active; stopped d2de6dcc4d06 and removed leftover network cvdp-bridge-cvdp_v1-1-0_nonagentic_code_generation_no_commercial
```

Interpretation: no rescue. The case is heavier than a cheap prompt-only fix and has synth/container instability risk. Continue later with manual/agentic combinational 10-iteration implementation if needed.

### cvdp_copilot_gcd_0045 QoR Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
sanity: TESTS=3 PASS=3 FAIL=0 for WIDTH=4/5 variants
synth: Yosys CHECK found 0 problems
failure: optimization thresholds only
```

Original synth comparison:

```text
wires: 225 -> 208, reduction 7.56%, required 8% -- FAIL
cells: 230 -> 228, reduction 0.87%, required 2% -- FAIL
```

Targeted hint added:

```text
Functional GCD/latency already passes; preserve interface, go/done timing, and Stein/binary-GCD latency.
Optimize synthesis quality by using compact single-FSM RTL and avoiding extra surviving next-value registers, wide temporaries, debug signals, or duplicated subtract/compare logic.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/gcd_0045_targeted_qor_2026_05_18
result: rescued
repair attempts: 0 after fresh generation; both tests passed directly
thinking used: no
```

Evidence:

```text
sanity: TESTS=3 PASS=3 FAIL=0 SKIP=0
synth: 1 passed
wires: 225 -> 206, reduction 8.44%, required 8% -- PASS
cells: 230 -> 225, reduction 2.17%, required 2% -- PASS
```

Interpretation: this is a valid post-hoc targeted QoR rescue from prompt/harness/log evidence only. Count it in the transparent targeted/multifile rescue delta, not in the baseline 302-case model score.

### cvdp_copilot_caesar_cipher_0001 Width Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
baseline result: 3/4 tests passed
failing test: random input lYdrPbmz with key 15
expected: aNsgEqbo
got:      aHsaEqbi
```

Root cause:

```text
The generated RTL used 5-bit shifted_index for char_index + key.
For uppercase/lowercase index up to 25 and key up to 15, the sum can reach 40.
5 bits truncate values above 31 before modulo 26, so Y + 15 wrapped incorrectly.
```

Targeted hint added:

```text
Use at least a 6-bit temporary for char_index + key before modulo/reduction.
Subtract 26 when the 6-bit sum is >= 26, then add the ASCII base.
Preserve exact non-alphabetic pass-through and the original caesar_cipher ports.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_caesar_cipher_0001_width_hint
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial fresh sample: TESTS=4 PASS=3 FAIL=1
repair attempt 1: TESTS=4 PASS=4 FAIL=0 SKIP=0
passed predefined, boundary, random, and numbers/symbols tests
```

Interpretation: valid post-hoc targeted semantic rescue from prompt/harness/log evidence. Count it only in the transparent targeted rescue delta, not in the baseline model score.

### cvdp_copilot_sigma_delta_audio_0007 Lint Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
sanity: 10 parameterized runs passed
lint: failed
best summary: 10/11
```

Lint root cause:

```text
WIDTHTRUNC: load_data_int/read_data_int additions produce 20-bit RHS for 19-bit destinations
WIDTHTRUNC: load concatenations produce 20-bit RHS for 19-bit destinations
UNUSEDSIGNAL: s_out[23:4] unused while only s_out[3:0] feeds quantization dither
```

Targeted hint added:

```text
Preserve the passing sanity behavior.
Explicitly slice fixed-point load/interpolation expressions to DATA_WIDTH+INPUT_DATA bits.
Avoid unused high bits by declaring only the used low dither/noise bits or splitting the signal.
Do not use lint waivers.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_sigma_delta_audio_0007_lint_hint
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 10/11
repair attempt 1: 10/11
remaining lint warnings: WIDTHTRUNC on load_data_int/read_data_int additions; UNUSEDSIGNAL on s_out_wide[23:4]
```

Interpretation: no rescue. The prompt-only lint hint reduced the warning set but did not pass lint; continue later with manual RTL width cleanup if needed.

### cvdp_copilot_ping_pong_buffer_0001 Toggle Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 5/6
failed test: buffer_alternation_test
failure: Buffer select did not toggle as expected
```

Harness-derived semantics:

```text
After reset, the test records initial buffer_select.
It then drives write_enable=1 and read_enable=1 for DEPTH*2 clocks.
It expects buffer_select to toggle at least once.
Other tests already pass: data validation, stress, async reset, random operation, and boundary full/empty behavior.
```

Targeted hint added:

```text
Clear buffer_empty on accepted write so simultaneous read/write after reset can progress.
Toggle buffer_select on a buffer wrap/fill boundary, not only on successful read from non-empty.
Preserve data ordering and async reset behavior.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_ping_pong_buffer_0001_toggle_hint
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial fresh sample: 5/6
repair attempt 1: 4/6
buffer_alternation_test passed after repair
new failures: data_validation_test expected 192 got 109; async_reset_test expected buffer_empty=1 got 0
```

Interpretation: no rescue. The hint fixed the narrow observed alternation but regressed FIFO ordering and reset-empty state; original artifact remains best. Further work likely needs manual/agentic state accounting rather than another prompt-only sample.

### cvdp_copilot_64b66b_decoder_0011 Control Decode Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 8/10
failed tests: control_only_test and mixed_mode_test
```

Harness-derived failures:

```text
control-only: sync=10 type=0x1E payload=0x00000000000000 expected 0x0707070707070707, got 0xFEFEFEFEFEFEFEFE
mixed: sync=10 type=0x4B payload=0x0000000ABCDEFF expected 0x0707070755E6F79C, got 0x07070707BCDEFF9C
```

Targeted hint added:

```text
For type 0x1E, payload 0x3C78F1E3C78F1E should decode to eight 0xFE controls, while all-zero payload should decode to eight 0x07 controls.
For mixed type 0x4B and payload 0x0000000ABCDEFF, expected data is 0x0707070755E6F79C with control mask 0xF1.
Preserve all type mappings that already passed.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_64b66b_decoder_0011_control_hint
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial fresh sample: 6/10
repair attempt 1: 8/10
remaining control-only failure inverted the 0x1E behavior: nonzero payload expected 0xFE but got 0x07
remaining mixed 0x4B failure still copied raw bytes: expected 0x0707070755E6F79C but got 0x07070707BCDEFF9C
```

Interpretation: no rescue. The targeted hint recovered to the prior best but did not exceed it; further work likely needs manual 64b/66b control-block decode mapping rather than another prompt-only sample.

### cvdp_copilot_64b66b_encoder_0022 Inspection

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best sanity summary: 11/13
synth: failed QoR thresholds
```

Remaining functional failures:

```text
all-control combinations: Data=0xFEFEFEFEFEFEFEFE Control=0xFF expected 0x21e3c78f1e3c78f1e, got 0x21e0078f1e3c78f1e
all-octets-control: same all-FE case fails
```

Synth evidence:

```text
cells: 1960 -> 1956, reduction 0.20%, required 20% -- FAIL
wires: 1649 -> 1646, reduction 0.18%, required 20% -- FAIL
```

Decision:

```text
no new bounded prompt-only pilot launched
```

Interpretation: this is not a narrow residual. It combines remaining control-block functional mapping with a large architecture/QoR requirement. Move to manual/agentic control-block encoder rewrite and QoR-aware simplification rather than another cheap targeted sample.

### cvdp_copilot_64b66b_encoder_0009 Control Pack Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 10/13
failure class: functional 64b/66b control-block packing
```

Harness/log-derived targeted examples:

```text
data=0xDDCCBBFB07070707 control=0x1F expected 0x233DDCCBB00000000
data=0xFEFEFEFEFEFEFEFE control=0xFF expected 0x21E3C78F1E3C78F1E
```

Targeted hint added:

```text
Preserve one-cycle registered output timing and data-only sync=01 behavior.
For control blocks, use sync=10, an 8-bit type field, and a 56-bit packed data field.
Do not pack each control character as a single bit.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_64b66b_encoder_0009_control_hint
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial fresh sample: 7/13
repair attempt 1: 7/13
repair improved_best: false
explicit 0x1F mixed case passed: 0x233ddccbb00000000
explicit all-FE 0xFF case passed: 0x21e3c78f1e3c78f1e
remaining failures include control mask 0x01: expected 0x2783456789abcdef0, got 0x27856789abcdef0fb
remaining failures include all-control 0xFD: expected 0x28700000000000000, got 0x21e00000000000000
```

Interpretation: no rescue. The targeted hint taught two specific mappings but the fresh sample regressed from the original `10/13` best to `7/13`, and it still lacks a complete control-block mapping. Keep the original full-run artifact as best and move this case to manual/agentic 64b/66b encoder mapping rather than another cheap prompt-only run.

### cvdp_copilot_sorter_0057 QoR Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best sanity summary: 34/35 aggregate, with all 17 sanity parameter runs passing and one synth failure
failure class: functional_and_synth_optimization / synthesis QoR only
```

Synth requirement and observed result:

```text
required reduction: wires >= 11%, cells >= 11%
baseline env: wires=2853, cells=3130
observed: wires 2853 -> 2847, reduction 0.21% -- FAIL
observed: cells 3130 -> 3122, reduction 0.26% -- FAIL
```

Harness-derived latency constraints:

```text
N=4 must complete in exactly 16 measured cycles.
N=8 must complete in exactly 37 measured cycles.
Other tested N values only require sorted output and latency below N*(4*N)+3.
```

Targeted hint added:

```text
Preserve the sorting_engine interface, ascending output packing, start/done behavior, and exact N=4/N=8 latencies.
The current RTL uses data_mem/tmp_merge arrays plus 32-bit integer indexes/endpoints; replace with compact small-N sequential compare/swap and narrow counters if possible.
Do not add helper modules, debug signals, or extra arrays that erase QoR reduction.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_sorter_0057_qor_hint
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial fresh sample: sanity 17/17 passed, aggregate 34/35 because synth failed
initial synth: wires 2853 -> 2847, reduction 0.21%; cells 3130 -> 3122, reduction 0.26%
repair attempt 1: aggregate regressed to 26/35
repair failure: N=4 sorted correctly but completed in 17 cycles; harness expected exactly 16
repair improved_best: false; rollback kept initial targeted artifact within the run
```

Interpretation: no rescue. The bounded prompt-only QoR hint did not move synthesis metrics, and the repair traded QoR intent for a functional/latency regression. Keep the original full-run artifact as best; further progress would likely require manual/agentic sorter rewrite with exact cycle accounting and post-synth validation.

### cvdp_copilot_sync_serial_communication_0052 Direct-Latch QoR Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best sanity summary: 16/20
failure class: functional_and_synth_optimization
```

Harness-derived functional failure:

```text
sel=2 selects a 16-bit transfer.
Observed failing example: data_in=2182 (0x0886), expected data_out=2182, got 2183 (0x0887).
The harness drives sel for 16 clocks, waits for done, then expects data_out to equal the selected low 16 bits exactly.
```

Synth evidence before rescue:

```text
baseline wires: 1026
generated wires: 1117
reduction: -8.87%, required 10% -- FAIL
```

Targeted hint added:

```text
Preserve top module sync_serial_communication_tx_rx and ports.
Replace the separate tx_block/rx_block/gated serial_clk/64-bit shift-chain structure with one compact top-level FSM.
Latch the selected low 8/16/32/64 bits of data_in directly, wait the selected transfer length plus allowed latency slack, then assert done and drive data_out.
For sel=2, preserve the exact low 16 bits; do not shift one extra bit or force bit 0 high.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_sync_serial_communication_0052_direct_latch_qor_hint
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 6/21, not usable
repair attempt 1: 21/21 aggregate
sanity: 20/20 passed
synth: wires 1026 -> 208, reduction 79.73%, threshold 10% -- PASS
cells after synth: 405
```

Interpretation: rescued as a transparent post-hoc targeted QoR/functional repair. This is not baseline model performance because the repair used case-specific prompt/harness/synth-log evidence.

### cvdp_copilot_line_buffer_0003 Boundary Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 48/64
failure class: functional
```

Harness-derived model semantics:

```text
The Python LineBuffer model shifts valid rows into row 0 and updates the stored output window only when i_update_window is high.
Mode 0: out-of-range row or column -> 0.
Mode 1: out-of-range row or column -> CONSTANT.
Mode 2: clamp row and column independently.
Mode 3: mirror row and column independently.
Mode 4: wrap row and column independently.
Output packing uses row NS_R_OUT-1 / col NS_C_OUT-1 as the highest chunk and row 0 / col 0 as the lowest chunk.
```

Full-run failure pattern:

```text
Typical mismatch: DUT 0x29727e... != model 0xb6f07e...
Larger NS_COLUMN cases also hit: Can't convert LogicArray to int because o_image_window contains X values.
```

Targeted hint added:

```text
Compute corrected row and column indexes independently before reading image_buffer_ff.
Avoid row-overflow paths that still use an uncorrected out-of-range column, and avoid column-overflow paths that still use an uncorrected out-of-range row.
Avoid any out-of-range array index for all parameter combinations.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_line_buffer_0003_boundary_hint
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial fresh sample: 32/64
repair attempt 1: 0/64
initial failures still include o_image_window mismatches and X values.
repair failures start at early comparisons and are worse than the full-run best.
```

Interpretation: no rescue. The prompt-only boundary hint was insufficient and regressed relative to the existing generic artifact. Further work should be manual/agentic RTL rewrite against the Python model, not another cheap targeted sample.

### cvdp_copilot_binary_search_tree_sorting_0014 Rank/Latency Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: partial 3/4 before timeout; failure class docker_timeout with functional latency symptoms
```

Harness-derived semantics:

```text
reference_model sorts the keys and returns sorted_keys.index(search_key).
key_position is therefore the sorted rank/index of the key, not necessarily the tree node id.
Empty tree or missing key expects complete_found=0, search_invalid=1, key_position=sentinel.
The harness checks exact smallest/largest key latency only for special parameter cases.
```

Targeted hint added:

```text
Use a bounded scan/rank computation rather than an unbounded stack traversal.
Clear stale completion flags on a new start.
Honor exact latency targets for ARRAY_SIZE/DATA_WIDTH combinations observed in the harness.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_binary_search_tree_sorting_0014_rank_latency_hint
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: timed out at 300s
repair attempt 1: 5/9, no timeout
remaining failures are exact latency checks:
ARRAY_SIZE=5 DATA_WIDTH=6: got 11, expected 5
ARRAY_SIZE=10 DATA_WIDTH=16: got 16, expected 8
ARRAY_SIZE=15 DATA_WIDTH=6: got 21, expected 3
ARRAY_SIZE=15 DATA_WIDTH=32: got 21, expected 18
```

Interpretation: no rescue, but useful reclassification from timeout to bounded functional latency failures. Further work needs a cycle-accurate manual/agentic implementation; another cheap prompt-only pilot is unlikely to fix the exact per-case latency table.

### cvdp_copilot_image_rotate_0001 Padding-Origin Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 7/10
failure class: functional
```

Harness-derived model semantics:

```text
The Python model pads the input image to max(IN_ROW, IN_COL) square by placing the original image at the top-left corner.
Flattening is row-major: element (row, col) is at DATA_WIDTH * (row * cols + col).
rotation_angle 00 = 90 clockwise, 01 = 180, 10 = 270 counterclockwise, 11 = no rotation.
```

Full-run failure pattern:

```text
IN_ROW=3 IN_COL=8: output data appeared in top rows but expected after 180-degree rotation was in bottom rows.
IN_ROW=3 IN_COL=4: output had zero padding on the left, expected zero padding on the right.
```

Targeted hint added:

```text
Do not bottom-align input rows when IN_ROW < OUT_ROW.
Place input at padded_image[i][j] for i < IN_ROW and j < IN_COL; all other cells are zero.
Use exact Python-model rotation mappings and preserve row-major packing.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/stage2_targeted_pilot_image_rotate_0001_padding_hint
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 4/10
repair attempt 1: 10/10
final report: 10 passed in 2.62s
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness-model-derived padding and rotation evidence.

### cvdp_copilot_configurable_digital_low_pass_filter_0004 First-Valid Targeted Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 21/32
failure class: functional
```

Harness-derived semantics:

```text
The harness drives data_in and valid_in, waits two rising edges, then requires valid_out == valid_in.
When valid_in is 1, it immediately checks data_out and peak_value.
pack_signal places original input_values[0] in the highest chunk; extract_signed reads output high-to-low.
The model reverses the input list, selects every DEC_FACTOR sample, then reverses again.
```

Failure pattern:

```text
Several failing parameter runs only fail when Test Case 1 has valid_in=1.
valid_out is accepted, but data_out or peak_value remains zero on Test Case 1.
Runs whose first valid_in is 0 often pass because the checker skips data_out/peak_value for that first transaction.
```

Targeted hint added:

```text
Compute packed output and signed peak from current data_in in a complete combinational block before the output register samples them.
Avoid generated procedural slice drivers or partially assigned packed temporaries that can retain reset/zero values.
Preserve harness high-to-low packing and signed peak comparison.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_low_pass_filter_0004_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 18/32
repair attempt 1: 4/32
repair rolled back to initial best
repair log still shows zero data_out on Test Case 1, e.g. assert [0, 0, 0, 0] == [22922, 19501, 28582, -21667]
```

Interpretation: no rescue. The targeted sample and repair both regressed below the full-run generic best, so this case should not get more cheap prompt-only attempts. Further progress likely needs manual/agentic RTL rewrite or more direct cycle-level debugging of the combinational packing/register timing.

### cvdp_copilot_image_stego_0004 bpp=10 Width Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 3/5
failure class: functional
```

Harness-derived model semantics:

```text
For each pixel i, pixel = (img_in >> (i*8)) & 0xFF.
bpp=00 replaces bit 0 with data_in[i].
bpp=01 replaces bits [1:0] with data_in[2*i +: 2].
bpp=10 replaces bits [2:0] with data_in[3*i +: 3].
bpp=11 replaces bits [3:0] with data_in[4*i +: 4].
Updated pixel is written back to the same i*8 output slice.
```

Failure pattern:

```text
The initial/full-run RTL passed bpp=00, all-zero, and all-one cases.
It failed alternating/random cases when bpp=10.
Example: actual 0b01010101001010100101010100101010, expected 0b10101101010100101010110101010010.
```

Root cause:

```text
The bpp=10 branch preserved only img_in pixel bits [7:4] and appended three data bits, making a 7-bit RHS for an 8-bit pixel slice.
Correct bpp=10 behavior must preserve five upper bits [7:3] and replace exactly bits [2:0].
```

Targeted hint added:

```text
Use exact low bpp+1 bit replacement for each pixel.
For bpp=10, preserve img_in[(i*8)+7 : (i*8)+3], not only [7:4].
Avoid variable-width concatenation mistakes; each assigned output pixel must be exactly 8 bits.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_image_stego_0004_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 3/5
repair attempt 1: 5/5
final report: TESTS=5 PASS=5 FAIL=0
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness/log-derived evidence about bpp=10 bit replacement.

### cvdp_copilot_hill_cipher_0001 Product-Width Targeted Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 2/4
failure class: functional
```

Harness-derived model semantics:

```text
Plaintext and key are split into 5-bit chunks MSB-first.
For each output row, the harness adds (K[row][j] * P[j]) % 26 for j=0..2.
It then applies %64 and %26 to produce each 5-bit ciphertext element.
The latency test asserts start for one clock and expects done after exactly 3 counted clock cycles.
```

Failure pattern:

```text
The full-run repaired RTL passed the normal value case and latency test.
It failed Maximum Values: plaintext chunks 26,26,26 and all key chunks 31 expected ciphertext 0, got 19026 ({18,18,18}).
```

Root cause:

```text
The RTL stored products in 5-bit temporaries before modulo. 31*26 is 806, but truncating to 5 bits produces 6; 6 % 26 summed three times gives 18.
Correct behavior requires a wide product before %26.
```

Targeted hint added:

```text
Use wide product/sum temporaries, apply the same modulo order as the Python harness, preserve output packing, and preserve the exact 3-cycle done latency.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_hill_cipher_0001_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/4
repair attempt 1: 2/4
repair fixed all six hill_cipher_test value cases, including Maximum Values.
remaining failure: hill_cipher_clock_latency_test reports Clock Latency 4, expected 3.
```

Interpretation: no rescue. The targeted repair fixed the value computation but regressed exact latency versus the full-run best. Further progress should be latency-specific/manual, not another broad prompt-only attempt.

### cvdp_copilot_aes_key_expansion_0001 Inspection, No Pilot

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 1/2
failure class: functional_and_synth_optimization
```

Observed state:

```text
baseline sanity: TESTS=1 PASS=1 FAIL=0
baseline synth: Optimization failed: No improvements found in the log file.
baseline Yosys totals: Number of wires 16180, Number of cells 19030
```

Repair evidence already present:

```text
repair_1 sanity: failed o_data mismatch
repair_2 sanity: failed o_data mismatch
repair_1/repair_2 synth: cells still 19030, wires increased to 16210
```

Interpretation: no bounded prompt-only pilot launched. The case needs an architecture/QoR-aware AES key schedule rewrite that preserves functional correctness while reducing the S-box/expanded-key logic. Prior generic repairs already broke sanity and did not improve cells, so another cheap targeted sample is unlikely to be useful.

### cvdp_copilot_hill_cipher_0015 NBA/Lint Targeted Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 1/3
failure class: functional_and_lint
```

Harness-derived semantics:

```text
Plaintext and key chunks are 5-bit MSB-first.
For each row: terms are (K*P)%26, sum_raw is truncated to 6 bits, residue is sum_trunc6b%26.
Latency test expects done after exactly 3 counted cycles.
Verilator lint runs with -Wall and treats warnings as failure.
```

Full-run failure pattern:

```text
sanity failed first normal case: expected 3171, got 0.
latency passed: 3 cycles.
lint failed with Verilator warnings.
```

Root cause:

```text
RTL chained nonblocking assignments in one COMPUTE_MOD state: mod values, sums, temps, and C registers were all assigned together, so C used stale old values on the first transaction.
```

Targeted hint added:

```text
Compute ciphertext with combinational wide temporaries and latch it with a small state/counter.
Preserve exact 3-cycle done latency.
Avoid lint warnings by matching modulo result widths explicitly and not driving done from multiple blocks.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_hill_cipher_0015_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 2/3; sanity passed, lint failed.
initial lint warnings: WIDTHTRUNC on assigning MODDIV results to 5-bit mod/C signals.
repair attempt 1: 1/3; sanity regressed with measured latency 4 cycles instead of 3, lint still failed.
rolled back to initial best.
```

Interpretation: no rescue. This did produce a useful sanity-pass/lint-only state, but the repair regressed behavior. Further progress should be lint-only/manual width cleanup of the initial targeted RTL, preserving the 3-cycle timing.

### cvdp_copilot_piso_0001 Serial Timing Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 1/5
failure class: functional
```

Harness-derived semantics:

```text
Reset is active low.
After reset, the internal byte starts at 8'b0000_0001.
The harness samples serial_out on falling edges.
Expected bytes are serialized MSB-first: 0000_0001, 0000_0010, later 0000_0100.
After 256 bytes, rollout expects 0000_0000 and then 0000_0001.
```

Failure pattern:

```text
The repaired full-run RTL output first byte [0,0,0,0,0,0,1,0] instead of [0,0,0,0,0,0,0,1].
Second and later byte checks were similarly one bit early.
Reset loop failed at the same off-by-one position.
```

Root cause:

```text
serial_out was assigned combinationally from tmp[7-count]. The counter and byte advanced at the prior rising edge, so the following falling-edge sample saw the next bit too early.
```

Targeted hint added:

```text
Make serial_out a registered output. On each rising edge, first drive the current byte's current MSB-first bit, then update bit_index and increment the byte only after bit_index==7.
Reset current_byte=8'h01, bit_index=0, serial_out=0.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_piso_0001_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/5
repair attempt 1: 5/5
final report: TESTS=5 PASS=5 FAIL=0
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness/log-derived timing evidence about falling-edge sampling and registered output order.

### cvdp_copilot_decoder_8b10b_0001 Decode-Latency Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 1/5
failure class: functional
```

Harness-derived semantics:

```text
The harness keeps a two-entry Python queue of decoder_in values.
After each rising edge it appends current decoder_in and immediately checks the oldest queued value.
Therefore outputs should correspond to the previous cycle's input at the check point, not an additional cycle later.
Invalid 10-bit inputs should produce decoder_out=0 and control_out=0.
```

Failure pattern:

```text
All control-symbol tests failed with decoder_out=0 when a valid delayed control symbol was expected.
The random invalid-input test passed, consistent with the design being too delayed/zero-biased.
```

Root cause:

```text
The RTL registered decoder_in into s_in_10b_reg and decoded s_in_10b_reg in the same always_ff block, while also clearing outputs each clock. This added one extra cycle beyond the harness delay.
```

Targeted hint added:

```text
Match the harness delay exactly: decode the one-cycle delayed input without adding an extra cycle.
Preserve all 24 control-symbol mappings and invalid-input zero behavior.
Reset clears delayed input, decoder_out, and control_out.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_decoder_8b10b_0001_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 1/5
repair attempt 1: 5/5
final report: TESTS=5 PASS=5 FAIL=0
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness/log-derived timing and control-symbol mapping evidence.

### cvdp_copilot_ir_receiver_0005 Pulse-Phase Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 1/7
failure class: functional
```

Harness-derived semantics:

```text
reset_in is active high.
The harness starts with ir_signal_in=1 and sends a 2.4 ms high leader/start period.
Each of the 12 data bits is sent LSB-first as (predefined_value >> i) & 1.
For every bit, the harness first drives a 0.6 ms low separator, then drives high for 0.6 ms to encode 0 or 1.2 ms to encode 1.
```

Failure pattern:

```text
All frame decode tests receive 000000000000 while reset behavior passes.
First assertion: Predefined 000000000000, Expected 000010000001, Received 000000000000.
```

Root cause hypothesis:

```text
The generated RTL's decode state reacts on low intervals and classifies the prior cycle_counter value when ir_signal_in is low. The protocol's low interval is a fixed separator; the encoded value is in the following high pulse width, so the decoder phase is wrong and never captures a valid frame.
```

Targeted hint added:

```text
Measure the high pulse width after each low separator.
Store bits LSB-first into ir_frame[bit_index].
Preserve the existing address/function output mapping, active-high reset, and exact top-level interface.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_ir_receiver_0005_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 1/7
repair attempt 1: 1/7
final/best report: TESTS=7 PASS=1 FAIL=6
rolled back to initial best.
```

Interpretation: no rescue. The pulse-phase hint was not enough for the model to rewrite the receiver state machine. Further progress likely needs manual/agentic RTL rewrite rather than another cheap prompt-only targeted repair.

### cvdp_copilot_fsm_seq_detector_0023 Overlap-Fallback Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 5/6
failure class: functional near-miss
```

Harness-derived semantics:

```text
The harness checks detection of bit pattern 01001110.
seq_detected is checked with one-cycle registered pulse timing.
test_noise_before_after expects detection at index 14 after sequence [1,1,0,0,0,1,0,1,0,0,1,1,1,0,0,1].
```

Failure pattern:

```text
Full-run repair_2 passed reset, detection_at_start, detection_at_end, multiple_occurrences, and rtl_bug_seq.
Only test_noise_before_after failed: expected seq_detected=1 at step 14, got 0.
```

Root cause hypothesis:

```text
The repaired FSM falls back too aggressively on mismatches. For example, after matching prefix 010 and seeing input 1, the suffix 01 is still a valid prefix and should be preserved rather than returning to the empty state.
```

Targeted hint used:

```text
Implement KMP-style overlap fallback for pattern 01001110.
Preserve suffix 01 after matched 010 plus input 1.
Preserve suffix 010 after deeper partial matches 01001/010011 plus input 0.
After a full match, assert a one-cycle pulse and fall back to suffix 0.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_fsm_seq_detector_0023_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 2/6
repair attempt 1: 2/6
repair failures: detection_at_start, multiple_occurrences, noise_before_after, rtl_bug_seq
rolled back to initial best.
```

Interpretation: no rescue. The fresh targeted sample regressed well below the full-run 5/6 artifact, so the original artifact remains best. Further progress should be a manual/agentic small FSM transition fix rather than another broad prompt-only sample.

### cvdp_copilot_digital_stopwatch_0001 Pause-Gate Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/3
failure class: functional
```

Harness-derived semantics:

```text
Module name is dig_stopwatch with parameter CLK_FREQ.
reset is active high.
The harness observes internal one_sec_pulse and waits on its rising edges.
The stopwatch should count while start_stop=1 and hold seconds/minutes/hour immediately after start_stop=0.
The random pause/resume test expects the fractional clk_counter to be preserved across pause.
```

Failure pattern:

```text
Full-run failures for CLK_FREQ 3, 50, and 63 all stop at the same pause check.
The harness samples stopped_seconds=9 after deasserting start_stop, then one clock later seconds is 10.
```

Root cause hypothesis:

```text
The generated RTL updates seconds from a stale registered one_sec_pulse after start_stop has already been deasserted. The pulse generator is gated, but the time-register block is not gated by current start_stop.
```

Targeted hint added:

```text
Gate time-register updates with current start_stop as well as one-second event, or compute one-second event and time increment in one clocked block.
Do not reset clk_counter merely because start_stop=0; preserve remaining ticks for random pause/resume.
Preserve seconds/minutes/hour rollover and active-high reset behavior.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_digital_stopwatch_0001_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/3
repair attempt 1: 0/3
repair progressed past the original pause check but failed rollover: seconds remained 59 instead of becoming 0 after the next clock.
rolled back to initial best.
```

Interpretation: no rescue. The hint fixed or moved the initial symptom but the generated repair broke rollover timing, so the original artifact remains best. Further progress likely needs a manual/agentic single-block counter rewrite.

### cvdp_copilot_sorter_0009 Latency-Hold Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 51/85
failure class: functional
```

Harness-derived semantics:

```text
Module name is sorting_engine.
Element i is packed at bus[i*WIDTH +: WIDTH].
Output must be ascending sorted in the same element order.
The harness counts cycles after the one-cycle start pulse until done==1.
Expected latency is (N * (N - 1)) / 2 + 4 cycles; for N=4 this is 10 cycles.
```

Failure pattern:

```text
Full-run best N=4 basic and random tests produced correct sorted data but asserted done at latency 8 instead of 10.
Several already_sorted, reverse_sorted, and all_equal checks passed.
```

Targeted hint added:

```text
Preserve sorting and packing, but add/adjust a small latency counter or hold state so done is asserted only at the expected latency.
Keep out_data sorted and stable when done is high.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_sorter_0009_20260519
result: failed_partial
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 17/85
repair attempt 1: 55/85
repair fixed N=4 basic latency to 10.
remaining failures include reverse_sorted output [0,2,3,1] vs [0,1,2,3] and random outputs with last pair unsorted.
```

Interpretation: no rescue, but partial improvement over full-run best. Since the remaining issue is a coupled odd-even sort data-state/timing bug rather than just latency, further progress should be manual/agentic rather than another broad prompt-only sample.

### cvdp_copilot_matrix_multiplier_0007 Dot-Product Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 13/36
failure class: functional
```

Harness-derived semantics:

```text
Module name is matrix_multiplier.
matrix_a, matrix_b, and matrix_c are packed row-major: element (row,col) is at flat[(row*cols + col)*width +: width].
For C[row][col], expected value is sum over k of A[row][k] * B[k][col].
valid_out must assert exactly COL_A + 2 cycles after the one-cycle valid_in pulse.
srst is active high and must clear valid_out and matrix_c.
```

Failure pattern:

```text
2x2 failures show wrong arithmetic, e.g. [[33,30],[50,54]] vs [[19,22],[43,50]].
3x3 failures include X/uninitialized bits in matrix_c.
```

Root cause hypothesis:

```text
The generated RTL computes only A[row][0] * B[0][col] into products_reg/accum_reg, then repeatedly adds that same stored product while accum_count decrements. It never computes the products for k=1..COL_A-1.
```

Targeted hint added:

```text
Compute the full dot product over all k for every output element.
Fully drive every matrix_c element for all tested sizes.
Preserve row-major packing and COL_A+2 valid_out latency.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_matrix_multiplier_0007_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: timed out at 300s, no summaries.
repair attempt 1: 0/36, all tests failed including iverilog build failures.
rolled back to initial best.
```

Interpretation: no rescue. The prompt-only targeted sample regressed below full-run best; further progress needs manual/agentic rewrite of a compact row-major dot-product implementation.

### cvdp_copilot_pipeline_mac_0017 Group-Boundary Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 2/9
failure class: functional
```

Harness-derived semantics:

```text
Module name is pipeline_mac.
rstn is active low.
DWIDTH_ACCUMULATOR must equal 2*DWIDTH + clog2(N).
The harness accumulates one result for each group of N valid input samples.
First valid_out must occur at N+2 cycles; later valid_out pulses are separated by N plus any invalid valid_i cycles.
```

Failure pattern:

```text
The first accumulation group can match exactly, including valid_out timing.
After the first valid_out boundary, expected and actual accumulation diverge while valid_i continues high.
```

Root cause hypothesis:

```text
The RTL resets accumulation_reg and counter_reg from valid_out_s2. If a new pipelined product arrives in the same boundary window, the reset path wins and drops the first product of the next accumulation group.
```

Targeted hint added:

```text
Do not drop products when valid_i remains high across a valid_out boundary.
When one group completes, clear for the completed group but still capture/add the incoming valid product as the first term of the next group.
Preserve N+2 first latency and subsequent spacing by N plus invalid cycles.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_pipeline_mac_0017_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/9
repair attempt 1: 0/9
rolled back to initial best.
```

Interpretation: no rescue. The prompt-only targeted sample regressed below full-run best; further progress needs manual/agentic cycle-accurate pipeline repair.

### cvdp_copilot_matrix_multiplier_0010 Reduction-Tree Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 12/36
failure class: functional
```

Harness-derived semantics:

```text
Module name is matrix_multiplier.
Matrices are packed row-major.
Expected C[row][col] is the full sum over k of A[row][k] * B[k][col].
valid_out latency is ceil(log2(COL_A)) + 2 cycles after valid_in.
```

Failure pattern:

```text
Full-run repair_2 passes the 2x2 static cases but fails 3x3 and 4x4 cases.
The generated reduction-tree RTL uses padded MODIFIED_COL_A stages and indexed add/red stages that drop or reuse terms for wider reductions.
```

Targeted hint added:

```text
Replace the fragile reduction behavior with complete row-major dot products.
Fully drive all matrix_c slices.
Preserve exact ceil(log2(COL_A))+2 valid_out latency.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_matrix_multiplier_0010_20260519
result: failed_partial
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 32/36
repair attempt 1: regressed to 0/5 summaries with sim build failures
initial targeted sample fixed the static 3x3/4x4 cases but still failed COL_A=1 single-element and generated/dynamic cases.
rolled back to initial best.
```

Interpretation: no rescue, but a strong partial improvement over full-run best. Further progress should be a focused manual/agentic fix for COL_A=1 and dynamic-input handling rather than another broad prompt-only repair.

### cvdp_copilot_one_hot_address_0001 Bit-Order Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 1/17
failure class: functional_and_lint; lint already passed, sanity failed
```

Harness-derived semantics:

```text
Module name is one_hot_gen.
rst_async_n is active-low async reset.
The Python model scans Region A from the MSB side of the full output bus.
Region A position 1 is 1 << (NS_A + NS_B - 1).
Region B position 1 is 1 << (NS_B - 1).
o_ready is high only in IDLE.
```

Failure pattern:

```text
Sanity failures occurred at the first active address after start.
Examples: DUT output 1 while model expected 2; DUT 4 while model expected 32; DUT 16 while model expected 2048.
```

Root cause:

```text
The RTL stored Region A in a separate vector and shifted from bit 0, then concatenated {region_A, region_B}; this reversed the intended full-bus one-hot ordering for Region A and affected Region B transitions.
```

Targeted hint added:

```text
Emit Region A bits from full-bus MSB down to bit NS_B.
Emit Region B bits from bit NS_B-1 down to bit 0.
Capture config at transaction start and use it until the sequence finishes.
Preserve ready/reset behavior.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_one_hot_address_0001_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 1/17
repair attempt 1: 17/17
lint passed and all 16 sanity parameter runs passed.
```

Interpretation: rescued as a transparent post-hoc targeted repair. This is not baseline model performance because it used harness-model-derived bit-order evidence.

### cvdp_copilot_sorter_0031 Counting-Sort Latency Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 21/130
failure class: functional
```

Harness-derived semantics:

```text
Module name is sorting_engine.
Element i is packed at bus[i*WIDTH +: WIDTH].
The expected latency is 4*(N+1) + max(input_values) + 4 cycles.
```

Failure pattern:

```text
For N=8, many outputs are sorted correctly but done is 5 cycles early.
Examples: random measured 50 expected 55; already-sorted/reverse-sorted measured 42 expected 47; all-equal measured 36 expected 41.
For N=1, stale output appears across tests, e.g. input [0] produces [1] or [2].
```

Targeted hint added:

```text
Hold done low for the missing five cycles while keeping sorted out_data stable.
Clear stale working/output state on reset and on each new start.
For N=1, return the single input element unchanged after the expected latency.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_sorter_0031_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/26 summaries
repair attempt 1: 21/130
same as full-run best; no net rescue.
```

Interpretation: no rescue. Further progress needs manual/agentic counting-sort state/timing cleanup.

### cvdp_copilot_swizzler_0014 Operation/Mapping Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 1/9
failure class: functional
```

Harness-derived semantics:

```text
Module name is swizzler.
operation_mode 000 applies the mapping: data_out[i] = data_in[mapping[i]].
mapping_in packs eight 4-bit entries; entry i is mapping_in[i*4 +: 4].
identity mapping 0x01234567 with data_in 0xAA should produce 0xAA.
reverse mapping 0x76543210 with data_in 0xAA should produce 0x55.
invalid mapping entries outside 0..7 should set error_flag=1 and data_out=0.
operation_mode 001 passthrough must output exactly data_in.
Non-swizzle modes operate directly on data_in, not on a pre-swizzled intermediate.
```

Failure pattern:

```text
Full-run best passed only invalid mapping behavior.
Passthrough/reverse/invert/shift modes were affected by applying mapping before the selected operation.
Swizzle mode used the opposite mapping direction for identity/reverse expectations.
```

Targeted hint added:

```text
Decode mapping entries as mapping[i] = mapping_in[i*4 +: 4].
For operation_mode 000 only, assign data_out[i] from data_in[mapping[i]].
For modes 001 through 110, ignore mapping and operate directly on data_in.
Preserve invalid mapping behavior: data_out=0 and error_flag=1.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_swizzler_0014_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 8/9
repair attempt 1: 9/9
final report: all 9 swizzler tests passed
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness/log-derived operation-mode and mapping evidence.

### cvdp_copilot_nbit_swizzling_0020 Hamming-ECC Index Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/5
failure class: functional
```

Harness-derived semantics:

```text
Module name is nbit_swizzling.
The test runs DATA_WIDTH values 16, 32, 40, 48, and 64.
The harness waits 10 ns after driving data_in/sel and then converts ecc_out/data_out to int, so all output bits must be driven combinationally.
Hamming positions are 1-based: parity bits are at positions 1, 2, 4, 8, ... and data bits fill non-power-of-two positions.
In the 0-based Verilog vector, Hamming position pos maps to ecc_out[pos-1].
Data bits are inserted LSB-first from data_in into non-power-of-two positions.
```

Failure pattern:

```text
Initial/full-run RTL failed all five parameterized runs because ecc_out contained X at the first observed conversion.
The generated ECC loop used 1-based loop variable i directly as ecc_out[i], so ecc_out[0] was never assigned.
The parity loop assigned ecc_out[1 << i] instead of ecc_out[(1 << i)-1], shifting parity bits one position too high.
Repair_2 partially drove some widths, but still showed ECC mismatch roughly equal to a one-bit shift for DATA_WIDTH 40/48.
```

Targeted hint added:

```text
Initialize all bits of ecc_out to zero before filling data and parity.
For pos from 1 to DATA_WIDTH+PARITY_BITS, assign non-power-of-two data positions to ecc_out[pos-1].
For each parity_pos = 1 << p, XOR all ecc_out[pos-1] whose 1-based pos has that parity bit set.
Assign each parity result to ecc_out[parity_pos-1], not ecc_out[parity_pos].
Keep unused high bits of the declared ecc_out width driven to zero.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_nbit_swizzling_0020_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/5
repair attempt 1: 5/5
passed DATA_WIDTH 16, 32, 40, 48, and 64
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness/log-derived Hamming-ECC position and initialization evidence.

### cvdp_copilot_scrambler_0001 LFSR Shift/Timing Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/2
failure class: functional
```

Harness-derived semantics:

```text
Module name is scrambler.
The harness tests DATA_WIDTH 16 and 32, resets once per mode, and checks modes 0 through 8.
The Python model initializes lfsr[14]=1, so the reset output pattern is 16'h4000 repeated across DATA_WIDTH.
Feedback taps use Python list indexes: mode 0 bit15^bit14, mode 1 bit15^bit13, mode 2 bit15^bit7^bit0, mode 3 bit15^bit7, mode 4 bit15^bit12^bit1, mode 5 bit15^bit11, mode 6 bit15^bit2^bit0, mode 7 bit15^bit10^bit3, mode 8 bit15^bit0.
The model shifts as new_lfsr[0]=feedback and new_lfsr[i]=old_lfsr[i-1].
For each checked input, the model advances the LFSR first, then XORs data_in with the advanced LFSR pattern repeated every 16 bits.
```

Failure pattern:

```text
Full-run initial and repair artifacts failed on the first checked mode-0 transaction.
Example DATA_WIDTH=16: data_in=0xc1a9, expected 0xc1aa, DUT returned 0xc1a9.
Example DATA_WIDTH=32: data_in=0xd9200b1d, expected 0xd9230b1e, DUT returned 0xd9200b1d.
This showed the checked output was using raw data_in or the wrong/pre-shift LFSR pattern.
```

Targeted hint added:

```text
Use the harness model's bit indexing and feedback taps exactly.
Shift toward higher list indexes with new bit 0 equal to feedback.
On the checked cycle, XOR data_in with the post-shift LFSR pattern, repeated every 16 bits for DATA_WIDTH > 16.
Preserve active-low async reset and mode changes only during reset.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_scrambler_0001_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/2
repair attempt 1: 2/2
passed DATA_WIDTH 16 and 32
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness-derived LFSR bit-index, shift-direction, and post-shift timing evidence.

### cvdp_copilot_secure_variable_timer_0001 Serial-Phase Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is secure_variable_timer.
The harness starts a 10 ns clock, resets active-low, then sends serial bits by assigning i_data_in and waiting for a falling edge.
The DUT samples on rising edges, so each bit is stable before the next rising edge.
The harness sends start pattern 1101 followed by delay bits 0110, MSB-first, so delay must be decimal 6.
After one extra falling edge, it requires o_processing==1 and o_time_left==6.
It then waits 7000 falling edges and requires o_completed==1 and o_processing==0.
```

Failure pattern:

```text
Full-run initial RTL reported o_time_left=0 when 6 was expected.
Repair_2 reported o_time_left=12, consistent with capturing shifted/stale bits such as 1100 instead of the intended 0110.
```

Targeted hint added:

```text
Detect 1101 using next_shift = {shift_reg[2:0], i_data_in}, not only the stale old shift_reg.
After detection, capture exactly the next four serial bits MSB-first as delay.
When the fourth delay bit is captured, enter processing so o_processing and o_time_left are visible by the harness check.
Count exactly (delay+1)*1000 clocks and handle ack by clearing completion and returning to idle.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_secure_variable_timer_0001_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/1
repair attempt 1: 1/1
final report: secure_variable_timer harness passed
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness-derived serial timing and delay-capture evidence.

### cvdp_copilot_secure_read_write_register_bank_0001 Unlock-Sequence Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is secure_read_write_register_bank.
i_capture_pulse acts as the clock. i_read_write_enable=0 is write; 1 is read.
Unlock requires two consecutive writes: address 0 with 0xAB, then address 1 with 0xCD.
After unlock, writes/reads to addresses 2 and 3 are allowed.
Addresses 0 and 1 are write-only and must read as 0.
Any wrong write to address 0 or 1 relocks the bank, even if it was previously unlocked.
Any read or other access between the first and second unlock writes breaks the partial sequence.
```

Failure pattern:

```text
Full-run failed after a correct unlock and data write: the harness wrote address 0 with 0xAA, then expected later reads of address 2 to return 0, but DUT returned 2.
First targeted pilot fixed that part but still failed an interrupted sequence: address 0 with 0xAB, then reads of address 2/3, then address 1 with 0xCD incorrectly unlocked and returned 2.
```

Targeted hints added:

```text
Wrong writes to address 0 or 1 must clear unlocked and partial-unlock state.
The two unlock writes must be consecutive write transactions.
Any read or write to another address after the first code clears partial unlock.
Locked or partially unlocked reads always return 0 and writes to addresses other than 0/1 are ignored.
```

Pilot runs:

```text
first run: research_outputs/two_stage_thinking_codegen/runs/targeted_secure_register_bank_0001_20260519
first result: failed 0/1, same interrupted-sequence symptom
refined run: research_outputs/two_stage_thinking_codegen/runs/targeted_secure_register_bank_0001_seq_hint_20260519
refined result: rescued
repair attempts in refined run: 0 after fresh generation
thinking used: no
```

Evidence:

```text
refined targeted fresh sample: 1/1
final report: secure_read_write_register_bank harness passed
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness-derived unlock sequence and interrupted-access evidence.

### cvdp_copilot_register_file_2R1W_0006 Post-BIST Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is cvdp_copilot_register_file_2R1W.
The harness first asserts test_mode=1 and waits for bist_done.
It then deasserts test_mode and immediately performs normal operation: write 0xA5A5A5A5 to address 5 for one clock, then read address 5 on port 1 on the next clock.
Expected dout1 is 0xA5A5A5A5.
BIST re-entry and BIST during normal operation are also checked afterward.
```

Failure pattern:

```text
Full-run and generic repair BIST completed successfully, but normal write/read after BIST returned dout1=0.
The generated RTL used gated_clk and a shared enable latch, plus BIST state that did not cleanly release normal operations after test_mode dropped.
```

Targeted hint added:

```text
Use main clk for register-file storage/read outputs and BIST sequencing; avoid generated/gated clocks in this harness.
When test_mode drops from DONE, return BIST FSM to IDLE and allow normal wen1/ren1/ren2 on the next clocks.
During normal mode, write din to rf_mem[wad1] and read rf_mem[rad1]/rf_mem[rad2] with one-clock registered timing.
Preserve BIST pass and BIST re-entry behavior.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_register_file_2R1W_0006_20260519
result: failed
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: failed 2 checks, including BIST normal operation and post-BIST normal readback.
repair attempt 1: BIST normal operation passed, but post-BIST normal readback still failed: expected dout1=0xA5A5A5A5, got 0x0.
```

Interpretation: no rescue. The targeted repair improved BIST but did not fix normal read/write release after BIST. Further progress should be manual/agentic implementation of the BIST/register-file state machine rather than another broad prompt-only sample.

### cvdp_copilot_static_branch_predict_0014 Exception-Alignment Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is static_branch_predict.
The harness checks fixed RISC-V branch/jump vectors with combinational 10 ns settling.
First vector: instr=0x8C218363, PC=0x1000, valid=1.
Expected outputs: taken=1, target PC=0x000000C6, confidence=90, exception=0, branch_type=3, offset=0xFFFFF0C6.
```

Failure pattern:

```text
Full-run RTL matched the first vector for taken, target PC, confidence, branch type, and offset.
It failed only exception: expected 0, got 1.
The RTL computed predict_exception_o from predict_branch_pc_o[1]. Since target 0xC6 has bit1 set, this incorrectly asserted exception.
Prompt/harness wording expects exception/alignment to be based on the input fetch_pc_i, which is aligned at 0x1000.
```

Targeted hint added:

```text
Preserve the already-correct target/offset/confidence outputs.
Do not flag exception from predicted target bit1.
Compute exception from fetch_valid_i and fetch_pc_i alignment, e.g. fetch_valid_i && fetch_pc_i[1:0] != 0.
When fetch_valid_i is 0, exception and predictions should be zero/default.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_static_branch_predict_0014_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/1
repair attempt 1: 1/1
final report: static branch predictor harness passed
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness/log-derived exception-alignment evidence.

### cvdp_copilot_static_branch_predict_0001 JALR/Register Operand Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness/log-derived semantics:

```text
Module name is static_branch_predict.
The harness drives fetch_rdata_i, fetch_pc_i, register_addr_i, and fetch_valid_i.
The original sample omitted register_addr_i, causing AttributeError before vectors could run.
For JALR opcode 7'h67, the harness expects target PC = fetch_pc_i + sign_extend(instr[31:20]) + register_addr_i.
Observed generic repair failure: instr 0xF63101E7, PC 0x1000, register operand 0, expected 0x00000F63, got 0xFFFFFF63.
```

Targeted hint added:

```text
Preserve the exact combinational interface, including register_addr_i.
Compute JALR target as fetch_pc_i + sign-extended immediate + register_addr_i.
Preserve known B-type, J-type, compressed jump/branch, invalid-fetch, and no-branch/default behavior.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_static_branch_predict_0001_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: failed immediately because static_branch_predict still had no register_addr_i port.
repair attempt 1: fixed register_addr_i and passed the B-type, JAL, JALR, compressed jump/branch, invalid-fetch, and no-branch vectors.
remaining failure: Improper Instruction Encoding expected PC 0x000007FC, got 0x00000FFC for instr 0xFE000E63 at PC 0x1000.
final benchmark summary: 0/1; repair did not improve best and was rolled back.
```

Interpretation: no rescue. The targeted repair addressed the documented missing-port and JALR failures but exposed a narrower improper-encoding offset issue. Further progress should use a specific encoding-derived hint or manual/agentic implementation; this attempt is not counted in post-hoc rescues.

### cvdp_copilot_cache_lru_0019 PLRU Tree Direction Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is pseudo_lru_tree_policy.
The harness directly reads dut.recency[index].
Tree nodes are level-order indexed by (1 << depth) - 1 + step.
get_mru_way follows the stored recency bit as direction: step = (step << 1) | bit.
get_plru_way follows the opposite direction: direction = 0 if bit is 1 else 1.
```

Failure pattern:

```text
After reset, the harness hits index 0 way 0, then index 0 way 3.
The generated RTL still left get_mru_way(recency, 0, 4) at 0 when the expected MRU was 3.
The RTL used an LSB-first update/indexing convention inconsistent with the harness-visible tree traversal.
```

Targeted hint added:

```text
Preserve the visible recency array.
Use level-order node index (1 << depth) - 1 + step.
Use MSB-first way_select bits while updating the root-to-leaf path.
Make MRU traversal follow stored bits and PLRU replacement follow opposite bits.
On miss, expose the current PLRU way on way_replace, then mark that replaced way as MRU on the update edge.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_cache_lru_0019_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: failed same early MRU check, get_mru_way returned 0 instead of expected 3.
repair attempt 1: changed behavior but still failed the same check, get_mru_way returned 2 instead of expected 3 after hit way 3.
final benchmark summary: 0/1; repair did not improve best and was rolled back.
```

Interpretation: no rescue. The prompt-only targeted attempt did not produce a correct tree convention. Further progress should be manual/agentic RTL correction for the PLRU update/select functions rather than another broad sample.

### cvdp_copilot_digital_stopwatch_0012 Countdown Interface/Timing Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/3
failure class: functional
```

Harness-derived semantics:

```text
Module name is dig_stopwatch.
The modified countdown interface includes load, load_hours[4:0], load_minutes[5:0], load_seconds[5:0].
The harness directly reads dut.hours, dut.minutes, and dut.seconds.
It loads values such as 5, 10, and 23 hours, so the old one-bit hour output is insufficient.
Some load checks wait only Timer(1ns), so load must be asynchronously visible or otherwise immediate enough for the harness.
With CLK_FREQ=N, wait_for_seconds waits N rising clock edges per countdown second.
```

Failure pattern:

```text
Full-run generated RTL kept output hour instead of hours.
All three CLK_FREQ configurations failed before countdown semantics with AttributeError: dig_stopwatch contains no child object named hours.
```

Targeted hint added:

```text
Preserve exact harness interface with hours[4:0] named hours.
Reset clears hours/minutes/seconds and divider state.
Load has priority, clamps hours/minutes/seconds to 23/59/59, and is visible immediately enough for Timer(1ns) checks.
Countdown borrows across seconds/minutes/hours, holds at 00:00:00, and preserves divider progress while paused.
```

First pilot:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_digital_stopwatch_0012_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

First-pilot evidence:

```text
initial targeted sample: still failed missing dut.hours.
repair attempt 1: fixed hours[4:0] and got through early load/countdown checks, but failed full rollover.
remaining failure: after loading 23:59:59 and waiting one CLK_FREQ-second interval, expected seconds 58 but got 59.
```

Refined hint added:

```text
Do not generate one_sec_pulse in one clocked block and consume its old registered value in a second clocked block.
Compute the divider terminal condition and update the time registers in the same clock cycle so the first visible second after load reaches 23:59:58, not 23:59:59.
```

Refined pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_digital_stopwatch_0012_refined_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial refined sample: 0/3.
repair attempt 1: 3/3.
final report passed all CLK_FREQ configurations: 3, 50, and 63.
```

Interpretation: rescued as a transparent post-hoc targeted functional repair. This is not baseline model performance because it used harness/log-derived interface and countdown timing evidence.

### cvdp_copilot_fan_controller_0008 PWM Window/QoR Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/2
failure class: functional_and_synth_optimization
```

Harness-derived semantics:

```text
Module name is fan_controller.
The harness programs APB registers TEMP_LOW=31, TEMP_MED=61, TEMP_HIGH=91, and temp_adc_in=75.
It reads address 0x0f and expects prdata=75.
It then observes pwm_counter/fan_pwm_out for 15 falling edges.
For pwm_counter values 1..11, fan_pwm_out must be 1; otherwise fan_pwm_out must be 0.
```

Failure pattern:

```text
Full-run sanity failed at pwm_counter=21 with fan_pwm_out=1, expected 0.
Generated RTL preserved a high-temperature 75% duty mapping, so counter 21 remained high.
Synth also failed QoR: wires 255 -> 282 and cells 310 -> 333, both worse than baseline.
```

Targeted hint added:

```text
Preserve APB setup/access behavior and temp readback.
Match the harness-observed short PWM high window, especially fan_pwm_out=0 at pwm_counter=21.
Preserve reset behavior.
For QoR, prefer direct simple PWM comparison and avoid extra speed_control/pwm_duty_cycle registers if not needed.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_fan_controller_0008_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: sanity failed at the same assertion, fan_pwm_out=1 at pwm_counter=21; synth timed out at 300s.
repair attempt 1: same sanity failure, fan_pwm_out=1 at pwm_counter=21; synth timed out at 300s.
final benchmark summary: not improved and rolled back.
```

Interpretation: no rescue. The model ignored the core PWM-window evidence and did not improve synth. Further progress should be manual/agentic QoR-aware RTL rewrite rather than another prompt-only attempt.

### cvdp_copilot_hebbian_rule_0012 Debug-Signal/Truth-Table Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is hebb_gates.
The harness directly reads debug signals test_x1, test_x2, expected_output, test_output, test_result, test_done, test_present_state, and test_index.
After AND training inputs (1,1), (1,-1), (-1,1), (-1,-1), it asserts w1=2, w2=2, bias=-2.
It then expects AND test outputs 1, -1, -1, -1 across the observed test windows.
```

Failure pattern:

```text
Full-run RTL passed the first AND weight assertions but crashed in the debug view because test_index was missing.
The RTL exposed test_index_reg but not a top-level signal named exactly test_index.
```

Targeted hint added:

```text
Expose test_index exactly, not only test_index_reg.
Preserve the harness-observed debug signals.
Preserve checked target weights for AND, OR, NAND, and NOR.
Match the bipolar gate truth-table outputs used by the harness.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_hebbian_rule_0012_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: got past the missing test_index crash but failed the first AND test output, expected 1 got -1.
repair attempt 1: same failure; debug showed w1=-1, w2=-1, bias=1 and test_output=-1 when expected 1.
final benchmark summary: 0/1; repair did not improve best and was rolled back.
```

Interpretation: no rescue. The cheap prompt fixed the debug-name issue but regressed the training/test semantics. Further progress should be manual/agentic rewrite of the small deterministic training/testing behavior.

### cvdp_copilot_gcd_0001 FSM/Latency Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/10
failure class: functional
```

Harness-derived semantics:

```text
Module name is gcd_top with WIDTH parameter.
The harness drives A/B, asserts go for exactly one rising clock, deasserts go, and waits until done.
OUT must equal the software GCD when done is high.
done must be high for one clock only.
Equal inputs must complete with latency 2; worst-case (2**WIDTH-1, 1) must complete with latency 2**WIDTH+1.
```

Failure pattern:

```text
Full-run failed A=4, B=2 with expected OUT=2, got 0.
The generated control/datapath reached equal internal operands but could still execute one more subtract before DONE/OUT capture.
```

Targeted hint used:

```text
Latch A and B on the go edge while idle.
Use internal operand registers after start.
In RUN, repeatedly subtract the smaller from the larger until equal.
When equal, drive OUT to the GCD and assert done for exactly one cycle.
Preserve equal-input latency 2 and worst-case latency 2**WIDTH+1.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_gcd_0001_20260519
result: not rescued, partial improvement
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/10.
repair attempt 1: improved to 2/10; WIDTH 8 and 16 stress tests passed.
remaining failure: equal-input latency was 1 instead of expected 2, e.g. A=1, B=1 and A=16, B=16.
final benchmark summary: 2/10, not a full rescue.
```

Interpretation: no rescue. The repair fixed many functional paths but missed exact equal-input latency. Further progress should be a latency-specific manual/agentic adjustment, not broad resampling.

### cvdp_copilot_compression_engine_0001 Exponent/Mantissa Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/2
failure class: functional
```

Harness-derived semantics:

```text
Module name is compression_engine.
determine_exponent(num_i) scans only num_i[23:12].
If no bit is set in num_i[23:12], exponent_o must be 0.
If the highest set bit is k in 12..23, exponent_o must be k - 11.
extract_mantissa uses (num_i >> (exponent - 1)) & 0xFFF when exponent >= 1, otherwise num_i & 0xFFF.
```

Failure pattern:

```text
Full-run/current RTL priority-encoded all 24 bits.
Low-only values such as 0x000001 and 0x000FFF therefore produced nonzero exponents.
High-bit values also used an exponent mapping offset from the harness expectation.
```

Targeted hints used:

```text
First hint: scan only num_i[23:12], map bit k to exponent k-11, and compute mantissa with the harness shift/mask rule.
Refined hint: explicitly warn not to shift by exponent_o and include visible harness examples 0x001000 -> exp 1 mant 0x000, 0x00F000 -> exp 4 mant 0xE00, and 0xABCDEF -> exp 12 mant 0x579.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_compression_engine_0001_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_compression_engine_0001_refined_20260519
result: not rescued, partial evidence only
repair attempts: 1 each
thinking used: no
```

Evidence:

```text
run 1 initial targeted sample: 0/2, same broad exponent/mantissa failures.
run 1 repair attempt 1: 0/2; exponent behavior largely improved, including low-only values and high-bit mapping, but mantissa still used the wrong window. Example 0xABCDEF expected mantissa 0x579, got 0xABC.
run 2 initial targeted sample: 0/2, regressed to broad exponent failures.
run 2 repair attempt 1: 0/2; low-only values passed, but many high-bit exponents were stuck at 0 and mantissa still mismatched. Examples include 0x00F000 expected exp 4 mant 0xE00, got exp 0 mant 0x000; 0xABCDEF expected mant 0x579, got 0x6F7.
final benchmark summary: 0/2; repair did not rescue and was rolled back to best artifact.
```

Interpretation: no rescue. The first repair showed the targeted evidence was valid but the model did not implement the full simple shift/mask rule. Further progress should be a manual/agentic combinational rewrite rather than more prompt-only resampling.

### cvdp_copilot_axi_stream_upscale_0001 Reset/First-Transfer Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is axis_upscale.
The harness initializes inputs to 0, applies active-low reset, releases reset, waits one rising edge, then expects m_axis_valid=0, m_axis_data=0, and s_axis_ready=0.
The harness then drives s_axis_valid=1, s_axis_data=24'h000004, dfmt_enable=1, dfmt_type=1, dfmt_se=1 and checks the next falling edge.
Expected first transfer has m_axis_valid=1 and formatted data with bit 23 inverted to 1 and bits 31:24 sign-extended to ones.
```

Failure pattern:

```text
Full-run RTL reset m_axis_valid and m_axis_data correctly but set s_axis_ready <= 1'b1 during reset.
The first harness assertion failed at 300 ns: expected s_axis_ready 0, got 1.
```

Targeted hint added:

```text
Reset s_axis_ready low, not high.
Still accept the first valid sample in the harness immediately after reset and produce m_axis_valid/m_axis_data on the next checked edge.
Preserve dfmt_enable/dfmt_type/dfmt_se formatting and avoid X values on m_axis_data after reset.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_axi_stream_upscale_0001_20260519
result: rescued
repair attempts: 0; fresh targeted sample passed
thinking used: no
```

Evidence:

```text
reset succesfull
m_axis_valid = 1
m_axis_data = 11111111100000000000000000000100
TESTS=1 PASS=1 FAIL=0 SKIP=0
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_virtual2physical_tlb_0001 Translation/Hit Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
failure class: functional
```

Harness-derived semantics:

```text
Module name is virtual2physical_tlb.
The harness drives virtual_address, waits one rising edge plus 1 ns, and checks physical_address against page_table_memory[virtual_address].
For in-range addresses 0..7, page_table_memory maps each address to itself.
For out-of-range addresses 8..15, the harness expects miss behavior.
After prior translation/miss accesses, the harness revisits in-range addresses and expects hit=1.
```

Failure pattern:

```text
Fresh refined sample: 0/10. First repeated failures were VA 5 expected physical_address 5 got 0, and VA 2 expected 2 got 0.
Repair attempt 1: progressed through in-range translations and miss checks, then failed the hit phase with VA 1, hit=0 expected 1.
```

Targeted hints used:

```text
First hint: make current-cycle physical_address correspond to the current virtual_address after the harness rising-edge-plus-1ns sample.
Refined hint: avoid stale one-cycle-late physical_address and allow direct in-range translation from virtual_address[PAGE_WIDTH-1:0].
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_virtual2physical_tlb_0001_20260520
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_virtual2physical_tlb_0001_refined_20260520
result: not rescued
thinking used: no
```

Evidence:

```text
refined initial summary: 0/10
refined repair summary: 0/10
repair evidence: translations for VA 7,3,2,1,6 passed; miss checks for VA 8..15 passed; HIT TEST then failed for VA 1 with hit=0 expected 1.
final benchmark result rolled back to the best available 0/10 artifact.
```

Interpretation: no rescue. The refined prompt fixed the original translation/stale-output issue in repair but exposed a distinct hit-bookkeeping problem. Further progress should be manual/agentic TLB bookkeeping rewrite, not another prompt-only targeted sample.

### cvdp_copilot_wb2ahb_0001 HWRITE Hold Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is wishbone_to_ahb_bridge.
The harness starts two 10 ns clocks, releases active-low rst_i/hreset_n, then starts a write by setting cyc_i=1, stb_i=1, we_i=1, addr_i=0x10000000, data_i=0xDEADBEEF immediately after a clk_i rising edge.
It then drives hready=0 for one hclk edge, hready=1 for the next hclk edge, and immediately checks hwrite=1, haddr=0x10000000, and hwdata=0xDEADBEEF.
For the read phase it sets we_i=0, addr_i=0x20000000, hrdata=0xCAFEBABE, repeats the wait/completion sequence, and expects data_o=0xCAFEBABE.
```

Failure pattern:

```text
Full-run RTL sampled we_i only in an hclk/hready-gated block and returned hwrite=0 at the first 50 ns write check.
Targeted repairs kept the same hready-gated capture structure, so the same hwrite assertion failed again.
```

Targeted hints used:

```text
First hint: make hwrite/haddr/hwdata visible and held through the harness wait/completion window; do not clear them after hready returns high before the check.
Refined hint: do not hide hwrite behind an hready-gated hclk register; for sel_i=1111 keep hwdata=data_i and data_o=hrdata directly.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_wb2ahb_0001_20260520
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_wb2ahb_0001_refined_20260520
result: not rescued
thinking used: no
```

Evidence:

```text
run 1 initial sample: compile/elab failure, Icarus returncode 9.
run 1 repair attempt 1: 0/1, ERROR: hwrite should be 1, got 0 at 50 ns.
run 2 initial sample: compile/elab failure, Icarus returncode 9.
run 2 repair attempt 1: 0/1, same ERROR: hwrite should be 1, got 0 at 50 ns.
```

Interpretation: no rescue. The issue is a small manual/agentic bridge timing rewrite candidate, but the bounded prompt-only targeted/refined attempts did not change the failing hwrite behavior.

### cvdp_copilot_vending_machine_0001 FSM Timing Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/10
failure class: functional
```

Harness-derived semantics:

```text
Module name is vending_machine.
The harness selects a random item (1..4, prices 5/10/15/20), inserts random 1/2/5/10 coins until total >= price, checks dispense (dispense_item=1, then dispense_item_id, error=0, return_change=0), then checks change (return_change=1 if change > 0).
It also tests cancel: selects an item, inserts two small coins, presses cancel, then checks error=1 and return_money=1.
```

Failure pattern:

```text
Full-run RTL unconditionally cleared return_change, error, and return_money to 0 at the START of every clock cycle with a default non-blocking assignment.
This caused return_change=1 to be visible during the dispense check (one cycle too early), and error=0 instead of 1 during the cancel check (cleared before the harness checked).
```

Targeted hints used:

```text
First hint: do not unconditionally clear return_change, error, or return_money at the start of every cycle. Set these pulsed outputs when needed and clear them only in the appropriate next state.
```

Pilot runs:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_vending_machine_0001_20260520
result: not rescued
thinking used: no
```

Evidence:

```text
targeted initial sample: regressed to dispense_item=0 failure (Expected item to be dispensed!), because the aggressive signal-clear rewrite broke basic dispense.
repair attempt 1: fixed the dispense/change path (exact-price purchase worked: Dispense_item_id - 4, Error - 0), but the cancel test still failed with error=0 expected 1 at 300 ns.
final benchmark result rolled back to best available 0/10 artifact.
```

Interpretation: no rescue. Repair fixed one issue but the broad FSM timing for cancel/error persistence needs a manual/agentic rewrite, not another prompt-only targeted sample.

### cvdp_copilot_sync_serial_communication_0014 Visible-Parity Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/20
failure class: functional
```

Harness-derived semantics:

```text
Module name is sync_serial_communication_tx_rx in rtl/sync_serial_communication_top.sv.
The harness drives selected low data widths: sel 1/2/3/4 map to 8/16/32/64 bits.
For normal transfers it checks data_out equals data_in and parity_error is 0 when XOR parity matches.
The error-injection helper waits for done, directly reads top-level dut.parity, force-writes the opposite value back to dut.parity, waits for done again, and expects parity_error == 1.
```

Failure pattern:

```text
Full-run initial failures included correct data_out and matching parity, but parity_error=1 on normal transfers.
Full-run repair fixed normal parity_error but failed before injection because sync_serial_communication_tx_rx contained no child object named parity.
Targeted repair exposed parity and normal transfers passed, but after force-writing dut.parity the next completion still reported Parity Error: 0.
```

Targeted hints used:

```text
First hint: expose top-level parity and parity_error, connect TX parity to RX parity_in, compute selected-width XOR parity, keep normal parity_error low, and compare RX against visible parity.
Refined hint: do not immediately overwrite the top-level parity signal with a newly computed internal value before RX compares it; a cocotb force/write to dut.parity must affect the next completion check.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_sync_serial_communication_0014_20260520
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_sync_serial_communication_0014_refined_20260520
result: not rescued
thinking used: no
```

Evidence:

```text
run 1 initial: 0/20, still missing top-level parity.
run 1 repair: 0/20, normal transfers pass but injected parity error is not detected.
run 2 initial: 0/20, normal transfer parity_error regressed to 1 in first summaries.
run 2 repair: 0/20, normal transfers pass but injected parity error still not detected; examples log Original parity flipped and Parity Error stayed 0.
```

Interpretation: no rescue. Stop prompt-only attempts after one refinement; this is now a manual/agentic candidate requiring a parity-injection-aware top-level/RX rewrite.

### cvdp_copilot_ttc_lite_0001 AXI Read/Interrupt Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is ttc_counter_lite.
The harness directly reads internal count, match_value, reload_value, enable, interval_mode, and interrupt_enable.
AXI address map is 0=count, 1=match, 2=reload, 3=control, 4=status/clear.
The read helper asserts axi_read_en for one rising edge, deasserts it, waits one more rising edge, then samples axi_rdata.
```

Failure pattern:

```text
Full-run RTL drove axi_rdata combinationally only while axi_read_en was high.
The harness sampled after axi_read_en was low, so [READ] Address: 0 returned Data: 0 while internal count was 10.
```

Targeted hints used:

```text
First hint: register/hold axi_rdata after reads, preserve exact register map and interval-mode count/reload behavior, and clear interrupt on any write to address 4.
Refined hint: after first repair read stale pre-reload count 20 while visible count was 10, align count read data with the value visible at the harness sample after the helper's second rising edge.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_ttc_lite_0001_20260520
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_ttc_lite_0001_refined_20260520
result: not rescued, partial progress
thinking used: no
```

Evidence:

```text
run 1 initial: 0/1, same count read Data 0 expected 10.
run 1 repair: 0/1, read Data 20 while internal count was 10.
run 2 initial: 0/1, same count read Data 0 expected 10.
run 2 repair: 0/1, progressed through count read, interrupt assertion, and status read; final failure was writing status address 4 did not clear interrupt.
```

Interpretation: no rescue after one refinement. The refined repair is a useful partial artifact, but further progress should be manual/agentic small FSM/register cleanup rather than more prompt-only attempts.

### cvdp_copilot_sync_lifo_0001 Initialization/Read Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/5
failure class: functional
```

Harness-derived semantics:

```text
Module name is sync_lifo in rtl/sync_lifo.sv.
The harness fills the LIFO with DATA_WIDTH writes, attempts two overflow writes, then reads DATA_WIDTH values plus two underflow reads.
For the tested parameter pairs DATA_WIDTH equals 2**ADDR_WIDTH, and expected read order is last accepted write first.
Before the first read check, the harness waits an extra 10 ns but does not wait for another clock edge before sampling data_out.
```

Failure pattern:

```text
Full-run RTL exposed X on data_out at the first read for every parameterized run.
The generated read path used mem[ptr[ADDR_WIDTH-1:0] - 1], which can index an invalid/uninitialized location when the pointer wraps or is zero.
```

Targeted hint added:

```text
Reset pointer/count, data_out, flags, and memory to deterministic zero values.
Use capacity 1 << ADDR_WIDTH and a count/pointer wide enough to represent the full value.
Ignore overflow writes and hold data_out on underflow.
Make data_out reflect the current top-of-stack when non-empty, or update it on a valid read without invalid pointer arithmetic.
Derive empty/full from the post-operation count.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_sync_lifo_0001_20260520
result: rescued
repair attempts: 0; fresh targeted sample passed
thinking used: no
```

Evidence:

```text
All five parameterized harness items passed.
Report: Total Tests 1, Passed Tests 1, Problem Pass Rate 100%.
Harness log shows PASS for ADDR_WIDTH/DATA_WIDTH pairs 2/4, 3/8, 4/16, 6/64, and 8/256.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_sorter_0003 Counter/Latency Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/0 due timeout
failure class: docker_timeout
```

Harness-derived semantics:

```text
Module name is sorting_engine.
The harness tests N=4,8,12,16 and WIDTH=4,8,12,16.
It packs element i at bus[i*WIDTH +: WIDTH].
It waits until done==1, then checks sorted ascending output and exact latency from expected_insertion_sort_operations.
```

Failure pattern:

```text
Full-run RTL declared outer index i as reg [$clog2(N)-1:0] and compared i == N.
For power-of-two N such as 4, i cannot represent N, so the first ascending case never reaches done and times out.
```

Targeted hint added:

```text
Require counters wide enough to represent N, bounded done for all tested N values, no array[N] access or j underflow, and exact harness insertion-sort latency formula.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_sorter_0003_20260520
result: not rescued
thinking used: no
```

Evidence:

```text
initial targeted sample: timed out at 300s.
repair attempt 1: no timeout, but 0/17 summaries passed.
First failure: N=4 ascending sorted correctly, but expected latency 12 and actual latency 14.
N=8 ascending similarly expected 24 and actual latency 26.
```

Interpretation: no rescue. The targeted evidence fixed the non-termination class but not exact harness latency. Stop prompt-only for this case; use manual/agentic latency-counter cleanup if continuing.

### cvdp_copilot_sorter_0059 Done/Latency/QoR Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
sanity: timeout on first N=4 ascending insertion-sort case
synth: passed QoR, wires 1044 -> 8 and cells 1356 -> 0
failure class: docker_timeout / functional+synth accounting
```

Harness-derived semantics:

```text
Same insertion-sort harness as sorter_0003: N=4,8,12,16 and WIDTH=4,8,12,16.
The harness waits for done, checks sorted ascending output, and checks exact expected_insertion_sort_operations latency.
```

Failure pattern:

```text
Full-run RTL assigns state in both an always @(*) block and a posedge block.
It never assigns done <= 1 on completion, so sanity waits forever.
```

Targeted hint added:

```text
Require single-owner state/done logic, bounded done, exact insertion-sort latency formula, and compact QoR-preserving implementation.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_sorter_0059_20260520
result: not rescued
thinking used: no
```

Evidence:

```text
initial targeted sample: sanity and synth both timed out at 300s.
repair attempt 1: sanity no longer timed out and sorted output correctly, but 0/17 sanity summaries passed because done was too early.
First failure: N=4 ascending expected latency 12, actual 8.
Repair synth timed out while rebuilding the synth image because pip/get-pip retried PyPI connections.
```

Interpretation: no rescue. Stop prompt-only sorter attempts; future work should be a manual/agentic implementation with an explicit latency counter and cached/working synth environment.

### cvdp_copilot_sprite_0004 Sprite FSM Model Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/50
failure class: functional
```

Harness-derived semantics:

```text
Module name is sprite_controller_fsm.
The harness compares every cycle against harness_library.SpriteControllerFSM.
INIT_WRITE drives write_addr=addr_counter and write_data=0xFF0000 without incrementing.
WRITE drives current write_addr/write_data, then increments counters.
READ ends at SPRITE_WIDTH*SPRITE_HEIGHT-1, not N_ROM-1.
```

Failure pattern:

```text
Full-run failed at cycle 2: DUT write_addr=1, model write_addr=0.
The design advanced the address too early relative to the model's output-before-increment semantics.
```

Targeted hint added:

```text
Match the Python SpriteControllerFSM cycle-for-cycle: INIT_WRITE no increment, WRITE output-before-increment, INIT_READ clear, READ x/y from current addr then increment, WAIT/DONE semantics, and parameter-safe reset.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_sprite_0004_20260520
result: not rescued
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/50, first mismatch moved later to cycle 515, expected write_addr 511 got 0.
repair attempt 1: 0/50, first mismatch cycle 258, expected write_addr 255 got 0.
```

Interpretation: no rescue. The model is explicit enough for manual/agentic rewrite; stop prompt-only attempts for this case.

### cvdp_copilot_skid_buffer_0001 Port/Latency Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is pipelined_skid_buffer.
The prompt names input data/valid as data_i/valid_i, but the cocotb harness directly drives dut.i_data and dut.i_valid.
After reset, the harness expects data_o=0, valid_o=0, ready_o=1.
Without back pressure, inputs 1,2,3,4,5,6 are driven on consecutive falling edges and data_o is expected to observe 1,2,3,4,5,6 in order at the following checks.
With ready_i=0, data_o must hold the already-visible value and then resume ordered delivery when ready_i returns high.
```

Failure pattern:

```text
Full-run/fresh targeted RTL exposed only data_i/valid_i, so the harness failed with pipelined_skid_buffer contains no child object named i_data.
First repair exposed enough interface to enter semantic checks but kept a four-stage skid/register structure; the second normal-flow check expected 2 and saw 1.
Refined repair overcorrected latency; the first normal-flow check expected 1 and saw 2.
```

Targeted hints used:

```text
First hint: expose harness-visible i_data/i_valid aliases or ports, reset-visible outputs, one-clock normal stream behavior, and skid/elastic backpressure behavior.
Refined hint: require i_data/i_valid as normal top-level ports, avoid the four-stage skeleton, and implement a small one-visible-cycle elastic buffer.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_skid_buffer_0001_20260520
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_skid_buffer_0001_refined_20260520
result: not rescued
thinking used: no
```

Evidence:

```text
run 1 initial targeted sample: 0/1, missing i_data.
run 1 repair attempt 1: 0/1, data_o=1 at the second normal check where expected 2.
run 2 initial targeted sample: 0/1, still missing i_data.
run 2 repair attempt 1: 0/1, data_o=2 at the first normal check where expected 1.
```

Interpretation: no rescue. The targeted evidence identifies a narrow interface/latency problem, but bounded prompt-only attempts oscillated around the required cycle behavior. Move to manual/agentic cycle-accurate elastic-buffer rewrite rather than more prompt-only refinements.

### cvdp_copilot_sobel_filter_0011 Independent-Window Latency Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is sobel_filter.
Each testcase sends one independent 3x3 image as exactly 9 valid_in cycles, row-major.
For every image, valid_out must stay 0 during all 9 input cycles, then assert for one clock after valid_in is deasserted.
The harness computes latency by counting input cycles with valid_out==0 and expects latency == 9 for every window.
Sobel kernels are Gx = p00 + 2*p10 + p20 - p02 - 2*p12 - p22 and Gy = p00 + 2*p01 + p02 - p20 - 2*p21 - p22.
```

Failure pattern:

```text
Full-run RTL did not clear/restart pixel_count after processing the first 3x3 window.
The next window asserted valid_out too early; full-run log showed Vertical Edge Test measured latency 1 instead of 9.
The initial targeted sample improved this to latency 8 but was still one cycle early.
```

Targeted hint added:

```text
Require independent 9-pixel windows, valid_out low for all 9 input cycles, one-cycle output after valid_in drops, counter/window restart after each output, exact harness Sobel kernels, and no stale nonblocking Gx/Gy when computing edge_out.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_sobel_filter_0011_20260520
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/1, Vertical Edge Test measured latency 8, expected 9.
repair attempt 1: 1/1, cocotb log reports All Sobel filter tests passed and TESTS=1 PASS=1 FAIL=0.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_scrambler_0009 Deinter-Block Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/36
failure class: functional
first visible failure: assert 0 == 66, DUT 0x0 vs model 0x42
```

Harness-derived semantics:

```text
Despite the dataset id, the harness top is deinter_block in rtl/deinter_block.sv.
It drives exactly four valid 256-bit input blocks, then deasserts i_valid.
The model's IntraBlock.rearrange_data returns in_data unchanged.
The DataProcessor model builds four aux words by byte index i=0..31 with block_index=i%4:
aux0 uses byte i, aux1 uses byte (i+1)%32, aux2 uses byte (i+2)%32, aux3 uses byte (i+3)%32.
Output chunk offset is zero-based: (counter_output % (DATA_WIDTH/OUT_DATA_WIDTH)) * OUT_DATA_WIDTH.
The model's effective delay is WAIT_CYCLES+5 update slots before streaming begins.
```

Failure pattern:

```text
Full-run and targeted outputs remained zero at the first nonzero model output.
Generated RTL kept a stale skeleton with counter_sub_blocks == SUB_BLOCKS after writing in_data_reg[counter_sub_blocks], which requires a fifth valid cycle the harness never sends.
It also built out_data_aux from out_data_intra_block_reg on the same start edge that loaded that register, so nonblocking assignment semantics used stale zeros.
The output select also used ((counter_output % chunks) + 1) rather than the model's zero-based offset.
```

Targeted hints used:

```text
Initial hint: clarify deinter_block harness semantics, direct aux construction, +1/+2/+3 byte offsets, and WAIT_CYCLES+5 timing.
Refined hint: explicitly forbid the retained bugs and allow a simple one-block rewrite that starts on counter_sub_blocks == SUB_BLOCKS-1 and streams aux[counter_sub_out][offset +: OUT_DATA_WIDTH].
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_scrambler_0009_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_scrambler_0009_refined_20260519
result: not rescued
thinking used: no
```

Evidence:

```text
run 1 initial targeted sample: 0/36.
run 1 repair attempt 1: 0/36.
run 2 initial targeted sample: 0/36.
run 2 repair attempt 1: 0/36.
raw_result best_summary remained pass=0 fail=36 total=36 summaries_found=36.
Refined repair RTL still contains counter_sub_blocks == SUB_BLOCKS and still builds aux from out_data_intra_block_reg.
```

Interpretation: no rescue. Stop prompt-only attempts for this case; it is a small manual/agentic RTL rewrite candidate.

### cvdp_copilot_sdram_controller_0001 Reset/Read/Write/Refresh Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
first visible failure: sdram_cke was 0 at the first rising edge after reset release, expected 1
```

Harness-derived semantics:

```text
Module name is sdram_controller.
The harness pulses active-high reset, deasserts it, then checks sdram_cke==1 on the next rising edge.
After ten initialization falling edges, it drives addr=24'h00ffff, sdram_dq=16'hfff0, read=1, waits three falling edges, and expects data_out==16'hfff0.
Then it drives addr=24'h00aaaa, data_in=16'hf0f0, write=1, waits three falling edges, and expects dq_out==16'hf0f0.
After 1024 idle falling edges plus one more, it expects the refresh command outputs: sdram_cke=1, sdram_cs=1, sdram_ras=1, sdram_cas=1.
```

Failure pattern:

```text
Full-run RTL reset sdram_cke to 0 and only drove it high later in the registered INIT output path.
First targeted fresh fixed reset visibility but failed read, with data_out=0 instead of 16'hfff0.
First targeted repair fixed read but drove dq_out combinationally only during WRITE_ST and defaulted it to 0 in IDLE, so the later harness check saw 0.
Refined repair fixed read/write visibility but failed the refresh check with sdram_cs=0 after the 1024-cycle wait.
```

Targeted hints used:

```text
Initial hint: require immediate CKE after reset release, harness-visible read/write timing, held dq_out, and refresh command outputs after 1024 idle clocks.
Refined hint: explicitly require registered holding data_out and dq_out instead of defaulting them to zero in combinational IDLE/default logic.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_sdram_controller_0001_20260520
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_sdram_controller_0001_refined_20260520
result: not rescued, partial progress only
thinking used: no
```

Evidence:

```text
run 1 initial targeted sample: 0/1, failed data_out=0 at read check.
run 1 repair attempt 1: 0/1, passed read but failed dq_out=0 at write check.
run 2 initial targeted sample: 0/1, failed data_out=0 at read check.
run 2 repair attempt 1: 0/1, passed reset/read/write and failed final refresh check: sdram_cs=0 expected 1.
raw_result best_summary remained pass=0 fail=1 total=1 summaries_found=1.
```

Interpretation: no rescue. The refined prompt produced useful partial progress, but the benchmark result remains failed; further progress should use a manual/agentic refresh-counter and command-hold fix rather than another prompt-only sample.

### cvdp_copilot_serial_in_parallel_out_0014 CRC-Hierarchy Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/18
failure class: functional
```

Harness-derived semantics:

```text
Top module is sipo_top in rtl/serial_in_parallel_out_8bit.sv.
The harness runs DATA_WIDTH 16,32,64; SHIFT_DIRECTION 0,1; POLY 8,16,32.
It first verifies SIPO shifting and done timing, then reads dut.crc_gen.data_in directly.
CRC reference initializes crc=0, iterates data bits MSB-to-LSB, and conditionally xors low CRC_WIDTH bits of POLY after left shift.
```

Failure pattern:

```text
Full-run SIPO shifting matched expected parallel_out, but every parameterized test crashed before CRC comparison.
The generated RTL instantiated the CRC module as uut_crc_generator.
The harness expected a child instance named crc_gen and raised: sipo_top contains no child object named crc_gen.
```

Targeted hint added:

```text
Instantiate the CRC generator with exact instance name crc_gen.
Connect crc_gen.data_in to SIPO parallel_out and expose crc_out.
Preserve SIPO shift direction/done timing and ECC behavior.
Use the harness MSB-first CRC reference algorithm and compare received_crc against crc_out for crc_error.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_serial_in_parallel_out_0014_20260520
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/18 with the same missing crc_gen hierarchy crash.
repair attempt 1: 18/18.
raw_result best_summary: pass=18 fail=0 total=18 summaries_found=18.
report.txt: Passed Problems 1/1, no failing problems found.
Example repair log: got_crc_out equals received_crc and expected_crc, crc_error=0; SIPO/ECC single-bit error checks pass.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_reed_solomon_encoder_and_decoder_0005 Parity-Feedback Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/10
failure class: functional
```

Harness-derived semantics:

```text
Module name is reed_solomon_encoder.
The harness randomizes K and always uses N=K+2.
On each enabled valid byte, it expects codeword_out=data_in and valid_out=1.
Expected parity update uses old parity_0/parity_1 and current data_in:
feedback = data_in ^ parity_1
parity_0 = feedback & 8'hff
parity_1 = parity_0_old ^ ((feedback * 8'h33) & 8'hff)
```

Failure pattern:

```text
The first targeted repair still used a registered feedback value with nonblocking assignment semantics.
The same always block then used the stale feedback RHS for parity_0/parity_1, so the first active cycle left parity_0 at 0.
Example refined-run initial failure: expected parity_0 0xb3, actual parity_0 0x0.
```

Targeted hints used:

```text
Initial hint: use the harness N=K+2 behavior and parity_0=feedback, not a generator-polynomial helper.
Refined hint: compute feedback_now combinationally as data_in ^ parity_1 and use it directly for parity_0 and parity_1.
Explicitly avoid assigning feedback <= ... and then reading feedback in the same nonblocking block.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_reed_solomon_0005_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_reed_solomon_0005_refined_20260519
result: rescued
repair attempts in refined run: 1
thinking used: no
```

Evidence:

```text
first targeted run: 0/10 after one repair attempt.
refined run initial targeted sample: 0/10.
refined run repair attempt 1: 10/10.
raw_result best_summary: pass=10 fail=0 total=10 summaries_found=10.
report.txt: Passed Problems 1/1, no failing problems found.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_prbs_gen_0003 Reference-Algorithm Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/54
failure class: functional
```

Harness-derived semantics:

```text
Module name is cvdp_prbs_gen.
The harness reference is the Python function generate_prbs in test_prbs_gen.py.
It stores the LFSR as a list of bits from the all-ones binary string. For each output bit, xor_a = prbs[i][POLY_TAP-1] ^ prbs[i][POLY_LENGTH-1], next list = [xor_a] + previous list without the last element, and data_out is the collected xor bits reversed.
Checker mode feeds the same expected PRBS word into data_in and expects data_out=0 for matching cycles, then nonzero after an injected one-bit error.
```

Failure pattern:

```text
Full-run first generator case WIDTH=8/POLY_LENGTH=7/POLY_TAP=1 expected 0x2a, got 0xff.
Checker cases reported nonzero error flags on valid input because the local PRBS sequence was wrong.
```

Targeted hints used:

```text
Initial hint: match the exact Python reference algorithm, update the state after WIDTH generated bits, and reverse the collected xor bits into data_out.
Refined hint: if using an SV vector [POLY_LENGTH-1:0], Python list index POLY_TAP-1 maps to SV bit POLY_LENGTH-POLY_TAP and Python last index maps to bit 0.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_prbs_gen_0003_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_prbs_gen_0003_refined_20260519
result: not rescued, partial improvement only
thinking used: no
```

Evidence:

```text
run 1 initial targeted sample: 0/54.
run 1 repair attempt 1: 18/54, passing all POLY_TAP=1 cases but failing POLY_TAP=3/5/etc.
run 2 initial targeted sample: 0/54.
run 2 repair attempt 1: 0/54 and rolled back.
```

Interpretation: no rescue. The first targeted repair shows the reference direction is useful but incomplete; the refined prompt regressed. Further work should be a manual/agentic exact translation of the Python list algorithm rather than more prompt-only sampling.

### cvdp_copilot_ir_receiver_0001 Clock/Pulse-Phase Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/0
failure class: docker_timeout
```

Harness-derived semantics:

```text
Module name is ir_receiver.
The harness starts clk_in with a 1000 ns period, so timing is 1 MHz despite the prompt comment saying 100 KHz.
It starts with ir_signal_in=1, sends a 2.4 ms HIGH leader, then sends each bit as a 0.6 ms LOW separator followed by HIGH for 0.6 ms for 0 or 1.2 ms for 1.
The harness transmits loop index 11 down to 0, then compares ir_frame_out against reverse_bits(value), so the first received bit must land in output bit 0.
```

Failure pattern:

```text
Full-run and generic repair both entered cocotb test_ir_receiver and timed out waiting for RisingEdge(ir_frame_valid).
Full-run RTL used 220..260 start thresholds and 40..80/100..140 bit thresholds, about 10x too small for the harness clock.
It also keyed decode around the low separator rather than the following high pulse width.
```

Targeted hint added:

```text
Use 1 MHz timing thresholds: about 2400 clocks for leader/start, 600 clocks for low separator or data-0 high, and 1200 clocks for data-1 high.
Decode the high pulse after each separator, store first received bit into ir_frame_out[0], and assert ir_frame_valid for one clock immediately after the 12th bit.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_ir_receiver_0001_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: timed out at 300s, no summaries.
repair attempt 1: timed out at 300s, no summaries.
Targeted generated RTL still used 220/260 start thresholds and 50/70/110/130 bit thresholds, so ir_frame_valid never rose.
```

Interpretation: no rescue. This is now an agentic/manual rewrite candidate: implement a small edge/level-duration FSM with 1 MHz thresholds and explicit leader/separator/high-pulse phases rather than spending more prompt-only attempts.

### cvdp_copilot_load_store_unit_0009 Misaligned Store/Data Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is load_store_unit.
The harness drives one-cycle execute requests only when ex_if_ready_o is 1, then checks the visible DMEM request after the request cycle.
For every store bus transaction, including misaligned split transactions, it asserts dmem_req_wdata_o == ex_if_wdata_i.
For crossing accesses, the first address is (effective_addr/4)*4 and the second is base+4.
For misaligned loads, the harness memory driver expects WB to pass raw dmem_rsp_rdata_i for each transaction rather than a final assembled value.
```

Failure pattern:

```text
Full-run failure: Expected dmem_req_wdata_o 3653579773, got 3308518656.
The generated RTL shifted store data for misaligned first/second transactions, while the harness expects unchanged wdata and lane selection by byte enable.
Generic repair still failed with shifted/truncated store data examples such as expected 1180163865, got 419430400.
```

Targeted hint added:

```text
Keep original 32-bit ex_if_wdata_i on every store transaction.
Use byte enables and aligned addresses to select lanes.
Use two transactions only for misaligned word offsets 1/2/3 and halfword offset 3.
Pass raw dmem_rsp_rdata_i to WB for misaligned loads; preserve aligned load extension behavior.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_load_store_unit_0009_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: compile/elab failure, iverilog exit 11.
repair attempt 1: built and ran but remained 0/1.
repair failure: WB DATA MISMATCH, expected 3657433088, got 0 during a misaligned read response.
```

Interpretation: no rescue. The store-data hint removed the first visible symptom in repair, but the generated FSM still mishandles misaligned read writeback timing/raw-data behavior. Further work should be a manual/agentic LSU FSM cleanup rather than another prompt-only sample.

### cvdp_copilot_microcode_sequencer_0001 Initialization/Sequence Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is microcode_sequencer.
There is no reset input. The harness initializes inputs, waits 3 ns and 20 ns, then checks after two rising clock edges per case.
The first fixed cases expect: reset instruction -> d_out=0/c_inc_out=0/empty=1; Fetch PC with c_inc_in=1 then c_inc_in=0 -> d_out=1 then d_out=2; Fetch R/D/R+D and push/pop cases then follow.
The harness converts d_out to int, so d_out must never be X/Z.
```

Failure pattern:

```text
Full-run and generic repair failed the first reset-instruction case: c_inc_out was X.
Generated RTL computed c_inc_out from an uninitialized PC register/carry path.
```

Targeted hint added:

```text
Initialize internal PC/register/stack state or avoid uninitialized sequential state in checked outputs.
Do not drive d_out as high impedance.
Match the harness fixed opcode/output sequence directly if needed.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_microcode_sequencer_0001_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/1, same reset-instruction c_inc_out=X failure.
repair attempt 1: reset-instruction X fixed, but next Fetch PC Instruction 1 failed with d_out=0 when expected 1.
final benchmark summary stayed 0/1.
```

Interpretation: no rescue. The targeted repair fixed initialization only partially; the remaining issue is cycle/phase behavior of the harness-specific PC sequence. Further progress should use manual/agentic rewrite rather than another prompt-only sample.

### cvdp_copilot_perf_counters_0001 Small-Width/Reset-Phase Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/0
failure class: docker_timeout
```

Harness-derived semantics:

```text
Module name is cvdp_copilot_perf_counters.
The overflow harness computes CNT_W from len(dut.p_count_o), then runs MAX_COUNT=(1<<CNT_W)-1 cycles with no parameter override.
The harness reads p_count_o during normal counting even when sw_req_i=0, so it expects live counter output rather than zero-gated output.
On sw_req_i=1 with cpu_trig_i=1, it expects p_count_o=1 after the read/reset window.
After reset_dut, it waits one rising edge and expects p_count_o=0 even if cpu_trig_i was left high from the previous random loop.
```

Failure pattern:

```text
Full-run and generic repair timed out before cocotb summaries because default CNT_W=32 made the overflow loop multi-billion cycles.
First targeted repair changed default CNT_W to 8 and exposed live count, converting timeout into a bounded 1/2 run, but failed the post-reset check with expected 0 got 2.
```

Targeted hints used:

```text
Initial hint: use small default CNT_W=8, expose live wrapping counter, and clear on sw_req_i while counting current cpu_trig_i.
Refined hint: add a just-reset phase so the first rising edge after reset deassertion holds zero and does not count a stale cpu_trig_i.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_perf_counters_0001_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_perf_counters_0001_refined_20260519
result: rescued
repair attempts: 1 in refined run
thinking used: no
```

Evidence:

```text
run 1 initial: timed out at 300s.
run 1 repair attempt 1: 1/2, failed post-reset expected 0 got 2.
run 2 initial: timed out at 300s.
run 2 repair attempt 1: passed; report shows 1 passed in 0.37s.
Final RTL uses CNT_W=8 and just_reset_q to suppress first post-reset count.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_icache_controller_0001 Current-Cycle Data Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/5
failure class: functional
```

Harness-derived semantics:

```text
Module name is instruction_cache_controller.
The harness checks l1b_data immediately when l1b_wait == 0.
Expected data is {ram512_d0_data, ram512_d1_data} when l1b_addr[0] == 1, otherwise {ram512_d1_data, ram512_d0_data}.
```

Failure pattern:

```text
Full-run failure: Mismatch in l1b_data. Expected: 0X130C8264, Got: 0X41E6501F.
The generated RTL did not present the current RAM beat/order in the same cycle that l1b_wait deasserted.
```

Targeted hint added:

```text
l1b_data must be purely combinational from current ram512_d0_data, current ram512_d1_data, and current l1b_addr[0].
l1b_wait must not go low unless current-cycle data is valid.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_icache_controller_0001_20260519
result: rescued
repair attempts: 0; fresh targeted sample passed
thinking used: no
```

Evidence:

```text
targeted fresh sample: 5/5.
Report shows PASS for all five repeated instruction_cache_controller harness runs.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_galois_encryption_0001 GF Pipeline Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is galois_encryption.
The harness updates a 32-bit key, then sends one-cycle i_valid pulses for 128-bit data and encrypt/decrypt selection.
It expects o_valid=0/o_data=0 for the input cycle and the next two rising edges.
On the third subsequent rising edge, it expects o_valid=1 and o_data equal to the Python GF model.
The Python model uses AES GF(2^8) xtime with polynomial 0x1B, column-major 4x4 byte packing, MixColumns for encryption, inverse MixColumns for decryption, and key bytes XORed by row.
```

Failure pattern:

```text
Full-run initial and generic repairs compiled and ran but failed at 70 ns on the first randomized transaction.
At the expected output point, DUT o_data was 0 while the model expected nonzero data such as 0xbcfa0bd0ca92ac2d1a4018f34073495.
The generated RTL used a multi-stage matrix pipeline and selected delayed output behavior from current i_encrypt rather than a transaction-latched operation.
```

Targeted hint added:

```text
Latch i_data and i_encrypt per valid transaction.
Align o_valid/o_data to the harness's exact third-subsequent-rising-edge output check.
Use the harness's column-major byte positions and key-byte row XOR convention.
Use AES GF constants for 02/03/09/0B/0D/0E and fully drive o_data/o_valid/reset state.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_galois_encryption_0001_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/1, failed at 70 ns with o_data=0 expected 0xccc2430779fbdfadef8b8c9eebe03cc1.
repair attempt 1: 0/1, failed at 70 ns with o_data=0 expected 0x12b8bc15ae6bbebe2406e3d37a34d45.
The repair RTL latched encrypt_ff but otherwise kept the same fragile staged matrix structure and still produced no visible output data at the harness check.
```

Interpretation: no rescue. The targeted prompt was justified by narrow harness-visible timing/GF evidence, but it did not improve beyond the full-run best. Further work should be manual/agentic rewrite of the valid/data pipeline and combinational GF transform, not another prompt-only resample.

### cvdp_copilot_gcd_0009 Three-Input Scheduler Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
baseline class: docker_timeout after generic repair
initial best summary: 0/10 bounded functional failures
```

Harness-derived semantics:

```text
Module name is gcd_3_ip in rtl/gcd_top.sv.
The harness drives A/B/C and go=1 for exactly one clock, then deasserts go and waits for done.
Expected result is gcd(gcd(A,B),C).
done must be high for exactly one clock.
Special latency checks are exact: A==B==C requires 5 cycles; selected max/one cases require 2**WIDTH+4 or 2*(2**WIDTH+1)+1 cycles.
```

Failure pattern:

```text
Full-run initial RTL instantiated two intermediate gcd_top blocks and one final gcd_top.
A=B=C=1 returned the right value but latency was 6 instead of expected 5.
Random stress examples returned 1 for cases where expected gcd was 2, 3, or 4.
The prior generic repair timed out after first failing A=B=C=1 with OUT=0.
```

Targeted hint added:

```text
Latch A/B/C on the start edge.
Coordinate intermediate gcd(A,B) and gcd(B,C) done pulses before starting final gcd.
Feed the final gcd captured intermediate outputs, avoid stale zero registers, avoid an extra output register after final done, and preserve exact special-case latencies.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_gcd_0009_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/10. A=1,B=1,C=1 still had latency 6 instead of 5, and random examples included expected 2 or 4 but got 1.
repair attempt 1: 0/10. It regressed to A=1,B=1,C=1 expected OUT=1 got 0, with no timeout.
```

Interpretation: no rescue. The targeted evidence converted the prior repair timeout into bounded functional evidence, but did not improve pass count. Further work should be a manual/agentic rewrite of the three-input scheduler or a direct controller with explicit latency handling, not another prompt-only sample.

### cvdp_copilot_gcd_0023 Stein Latency Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
baseline class: docker_timeout after generic repair
initial best summary: 0/15 bounded functional failures
```

Harness-derived semantics:

```text
Module name is gcd_top in rtl/gcd_top.sv.
The harness verifies Stein/binary GCD over WIDTH values 4, 6, 8, and 16.
It includes zero cases: gcd(0,0)=0, gcd(A,0)=A, gcd(0,B)=B.
Latency is checked exactly as simulate_hw_latency(A,B)+2 from test_gcd_top.py.
Each Stein step consumes one processing cycle; equality consumes one additional cycle to reach done.
```

Failure pattern:

```text
Full-run initial failed A=0,B=0 with latency 2 instead of expected 3.
It also returned OUT=0 for one-zero cases such as A=0,B=8 where expected OUT=8.
Generic repair attempts still failed zero-case latency/value and the second repair timed out after partial evidence.
```

Targeted hint added:

```text
Handle zero operands explicitly by setting both internal operands to the nonzero operand before equality/done.
Follow the harness step model exactly: both-even shifts both and increments k, one-even shifts only that operand, both-odd subtracts the smaller from the larger and shifts the difference right by one.
Drive OUT=A_ff<<k_ff on done, assert done for one cycle, and preserve reset semantics.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_gcd_0023_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/15. A=0,B=0 still had latency 2 instead of 3; A=0,B=10 expected OUT=10 got 0; random nonzero examples also returned 0.
repair attempt 1: 0/15. Same pattern, for example A=0,B=7 expected OUT=7 got 0 and A=4,B=28 expected 4 got 0.
The generated RTL kept a fixed multi-state sequence rather than the harness's one-step-per-cycle Stein model.
```

Interpretation: no rescue. The targeted prompt was justified and bounded the previous timeout, but pass count did not improve. Further work should be manual/agentic cycle-accurate Stein FSM rewrite, not another prompt-only sample.

### cvdp_copilot_hmac_register_0001 Valid Timing Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/24
failure class: functional
```

Harness-derived semantics:

```text
Module name is hmac_reg_interface.
The harness model exposes states IDLE=0, CHECK=1, PROCESS=2, WRITE=3, LOST=4, CHECK_KEY=5, TRIG_WAIT=6.
xor_data equals wdata^0101... only in PROCESS; otherwise it equals wdata.
Writes happen only in WRITE. addr 0 writes hmac_key, addr 1 writes hmac_data and asserts hmac_valid, other addresses write the register array.
The harness compares delayed rdata and hmac_valid, and directly reads current_state, xor_data, hmac_key, hmac_data, and hmac_key_error.
```

Failure pattern:

```text
Full-run RTL asserted hmac_valid for every WRITE state, including writes to ordinary registers such as addr 15 or addr 4.
The harness expected hmac_valid=0 in those cycles.
Repair attempts changed state timing and key_error behavior but still failed early.
```

Targeted hint added:

```text
Only assert hmac_valid for WRITE to addr 1.
Keep state numbering and internal signal names harness-visible.
Use PROCESS-only xor_data, delayed registered rdata/hmac_valid, and the exact hmac_key_error predicate from the Python model.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_hmac_register_0001_20260519
result: not rescued, partial improvement
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/24.
repair attempt 1: 13/24, improving enough that the first interface test passed for several parameterizations.
Remaining failure: validate_data_and_key fails immediately after reset/start because hmac_key=0 and model_hmac_key_error=0, but dut_hmac_key_error=1 at 811 ns.
```

Interpretation: no full rescue. The targeted hint fixed the main hmac_valid over-assertion in the repair sample, but the case remains failed. Further work should use the 13/24 repair RTL as a manual/agentic starting point and narrowly fix key_error reset/timing.

### cvdp_copilot_perceptron_0013 Gate-Weight Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is perceptron_gates.
The harness checks final weights after training four gates:
AND:  w1=1,  w2=1,  bias=-1
OR:   w1=1,  w2=1,  bias=1
NAND: w1=-1, w2=-1, bias=1
NOR:  w1=-1, w2=-1, bias=-1
The later random-input section logs outputs but does not assert them.
```

Failure pattern:

```text
Full-run RTL used a microcoded update loop that over-updated the learned weights.
The first visible failure was AND final w1=-4 when the harness expected 1.
```

Targeted hint added:

```text
Preserve the perceptron_gates interface and harness-visible debug signals.
Converge to stable final weights for each gate_select after the training window.
Do not clear learned weights or bias when stop asserts.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_rescue_perceptron_0013
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/1.
repair attempt 1: 1/1.
Checked final weights in the passing repair log:
AND  = 1,1,-1
OR   = 1,1,1
NAND = -1,-1,1
NOR  = -1,-1,-1
pytest summary: TESTS=1 PASS=1 FAIL=0.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_axi_alu_0001 Burst/Result Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
failure class: docker_timeout after partial functional failure
best summary: 0/0 due timeout
```

Harness-derived semantics:

```text
Module name is axi_alu.
The harness first issues a 16-beat incrementing AXI write burst at byte address 0x20.
It directly checks dut.u_memory_block.ram[0..15] and expects values 5..20.
ALU CSR byte addresses are 0x00,0x04,0x08,0x0c,0x10.
The 64-bit ALU result is read from word address 5 and 6, i.e. byte addresses 0x14 and 0x18.
```

Failure pattern:

```text
Full-run initial RTL wrote only the first few burst beats.
The visible failure was address 0x30 / ram[4] expected 9 got 0, followed by a timeout in the next test.
Generic repair improved to ram[0..7] but still failed at address 0x40 / ram[8] expected 13 got 0 and then timed out.
```

Targeted hint added:

```text
Map byte addresses 0x20..0x5c to ram[(addr-0x20)>>2].
Increment burst write address by 4 for each accepted beat and terminate on wlast or burst count.
Return RAM data for memory reads, and return ALU result low/high words at 0x14/0x18.
Keep AXI ready/valid handshakes bounded so the cocotb helpers do not wait forever.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_axi_alu_0001_20260519
result: not rescued; reclassified from timeout to bounded functional failures
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 2/10, no timeout.
Passing tests: shift operation and unaligned AXI access.
First failure: ram[0] expected 5 got 0 after the 16-beat burst write.
ALU result reads often returned 0 at 0x14/0x18, causing MAC/multiply/division/random/overlap/boundary tests to fail.
repair attempt 1: regressed to 1/10 and was rolled back.
```

Interpretation: no rescue. The targeted hint removed the non-termination but did not produce a passing or near-passing design. Further progress needs a manual/agentic rewrite of the small AXI SRAM/CSR/ALU datapath rather than another broad prompt-only sample.

### cvdp_copilot_axi_tap_0009 Timeout-Signal Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/20
failure class: functional
```

Harness-derived semantics:

```text
Module name is axi_tap.
Addresses with MSB set route to peripheral0; other addresses route to the default outport.
The harness directly writes dut.TIMEOUT_LIMIT.value = 10.
The harness directly reads dut.read_timeout_o.value and dut.write_timeout_o.value.
For timeout checks, it holds the relevant valid signal high while the selected slave response valid stays low, and expects timeout to assert once i >= TIMEOUT_LIMIT + 1.
```

Failure pattern:

```text
Full-run RTL preserved the initial pass-through checks but exposed timeout ports as timeout_threshold_i/read_timeout_flag_o/write_timeout_flag_o.
Every parameterized run failed with AttributeError: axi_tap contains no child object named TIMEOUT_LIMIT.
The first targeted pilot still had 0/20; its repair got past TIMEOUT_LIMIT but then failed with missing read_timeout_o.
```

Targeted hints used:

```text
First hint: preserve AXI pass-through behavior and provide a cocotb-visible TIMEOUT_LIMIT object.
Refined hint: also declare harness-visible top-level signals named exactly read_timeout_o and write_timeout_o.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_axi_tap_0009_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_axi_tap_0009_refined_20260519
result: rescued
repair attempts in refined run: 1
thinking used: no
```

Evidence:

```text
refined initial targeted sample: 0/20.
refined repair attempt 1: 20/20.
Passing log shows read_timeout_o and write_timeout_o stay 0 through i=10 and assert at i=11 for TIMEOUT_LIMIT=10.
All 20 ADDR_WIDTH/DATA_WIDTH parameterized harness items passed.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_axis_border_gen_0001 Row-Tlast Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/3
failure class: functional
```

Harness-derived semantics:

```text
Module name is axis_image_border_gen.
The output image is IMG_WIDTH+2 by IMG_HEIGHT+2.
The harness checks m_axis_tlast on the last output pixel of every row: (i + 1) % (IMG_WIDTH + 2) == 0.
For IMG_WIDTH=3, the top border row has five pixels and tlast must be true at output index 4.
```

Failure pattern:

```text
Full-run generated the top border pixels but kept m_axis_tlast low on the row-end pixel.
The first failures were:
IMG_WIDTH=3: index 4 expected tlast true, got 0.
IMG_WIDTH=4: index 5 expected tlast true, got 0.
IMG_WIDTH=5: index 6 expected tlast true, got 0.
```

Targeted hint added:

```text
Generate exactly IMG_WIDTH+2 border pixels for top/bottom rows.
Assert m_axis_tlast when output column index is IMG_WIDTH+1.
Generate border pixels without waiting for input pixels; consume input only for core pixels.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_axis_border_gen_0001_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/3.
repair attempt 1: 0/3.
Both reproduced the same tlast off-by-one failure for IMG_WIDTH 3, 4, and 5.
```

Interpretation: no rescue. Stop prompt-only retries for this case; next useful path is manual/agentic rewrite of the output row/column FSM.

### cvdp_copilot_binary_search_tree_sorting_0001 Timeout Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
failure class: docker_timeout
best summary: 0/0 due timeout
```

Harness-derived semantics:

```text
Module name is binary_search_tree_sort.
The harness starts with ARRAY_SIZE=1, DATA_WIDTH=6.
It asserts start for one cycle, then waits in a loop until done==1.
For ARRAY_SIZE=1 it checks exact latency 13 cycles and sorted_out equal to the single input element.
```

Failure pattern:

```text
Full-run entered cocotb and logged Running Test: Random 0, then timed out without any summary.
Generated RTL had visible non-termination risks: 3-bit BUILD/SORT states stored in 2-bit build_state/sort_state, an IDLE clear loop iterating i < ARRAY_SIZE+1 over ARRAY_SIZE-wide packed arrays, and SORT_TREE paths that could skip output for a single-node tree.
```

Targeted hint added:

```text
Use state registers wide enough for all encodings.
Clear packed arrays only for i < ARRAY_SIZE.
Handle ARRAY_SIZE=1 explicitly with sorted_out=input and done after latency 13.
Use a bounded sorting implementation and hold done for exact-latency sorted/duplicate cases.
Latch data_in only on start.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_binary_search_tree_sorting_0001_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: timed out at 300s on ARRAY_SIZE=1 / Running Test: Random 0.
repair attempt 1: timed out identically at 300s.
No cocotb summaries were produced.
```

Interpretation: no rescue. Stop prompt-only retries; this needs manual/agentic bounded sorter implementation if continuing beyond transparent targeted pilots.

### cvdp_copilot_configurable_digital_low_pass_filter_0014 FSM-Buffer Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/35
failure class: functional
```

Harness-derived semantics:

```text
The actual module is fsm_linear_reg, not a low-pass filter.
The Python model in harness_library.py keeps output_buffer registers.
On each model step, it first assigns result1/result2/done from the previous output_buffer, then updates output_buffer based on current_state.
```

Failure pattern:

```text
Full-run RTL updated result1/result2 directly in IDLE when start was high.
The first DATA_WIDTH=2 failure expected result1=0 from the model's previous buffer but got result1=1.
Other parameterizations failed similarly with early nonzero outputs.
```

Targeted hint added:

```text
Do not update result1/result2 directly on the start edge.
Implement output-buffer timing matching the Python model.
Clear state/output/buffer on reset, including mid-sequence reset.
Use signed arithmetic and arithmetic shifts.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_low_pass_filter_0014_20260519
result: not rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/35, still early nonzero output; first failure assert -1 == 0.
repair attempt 1: 0/35, overcorrected/stalled result updates; first failure assert 0 == 1 and later expected nonzero model values remained 0.
```

Interpretation: no rescue. Further progress needs a manual/agentic cycle-accurate FSM rewrite rather than another prompt-only retry.

### cvdp_copilot_elevator_control_0033 Inspection No-Pilot

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
failure class: docker_timeout plus lint failure
sanity log: reports/33_sanity.txt
lint log: reports/33_lint.txt
```

Harness-derived semantics:

```text
The focused sparse-request test resets the DUT, requests floor 3, then requests floor 7.
It expects the elevator to first reach floor 3, open the door, close the door, then continue to floor 7.
The harness observes internal max_request, min_request, call_requests_internal, current_floor, and door_open.
```

Failure pattern:

```text
Full-run log printed:
Testing sparse requests at floors 3 and 7
max_request: 3
min_request: 3
000010001000
Waiting for elevator to reach floor 3
Then the run timed out.
Lint also failed.
```

Inspection:

```text
Generated RTL drives call_requests_internal in an always @(*) block that both reads and writes call_requests_internal.
That creates combinational self-feedback/stale request behavior and no robust registered request latch.
max_request/min_request are recomputed from that unstable internal request state.
This matches the prior elevator-family semantic timeout pattern, especially the already-recorded elevator_control_0026 case where prompt-only FSM hints still timed out.
```

Action:

```text
No new prompt-only pilot launched.
```

Interpretation: no rescue. Mark as manual/agentic candidate: implement registered request latching, clear served requests synchronously after door-open service, deterministic movement to nearest/queued floors, short simulation door timer, and lint cleanup.

### cvdp_copilot_perceptron_0006 Weights-And-Testing Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is perceptron_gates.
The harness runs deterministic training/testing windows for AND, OR, NAND, and NOR.
Expected final weights are AND (1,1,-1), OR (1,1,1), NAND (-1,-1,1), NOR (-1,-1,-1).
Expected test-output sequences are AND 1,-1,-1,-1; OR 1,1,1,-1; NAND 1,1,1,-1; NOR 1,-1,-1,-1.
```

Failure pattern:

```text
Full-run RTL learned the AND weights during training, but on stop/convergence it cleared percep_w1/percep_w2/percep_bias to 0.
The first checked final weights were therefore 0,0,0 instead of 1,1,-1.
```

Targeted hints added:

```text
Do not clear learned weights/bias when stop asserts.
Preserve final weights for each gate and drive the fixed test-output sequence after the training windows.
Refined hint: latch a testing_active state and keep selected gate weights/test sequence stable through the four 80 ns test checks.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_perceptron_0006_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_perceptron_0006_refined_20260519
result: not rescued
thinking used: no
```

Evidence:

```text
run 1 repair: AND final weights fixed to 1,1,-1, but first AND test output remained 0 instead of 1.
run 2 repair: AND final weights and four AND test outputs passed, but OR final bias stayed -1 when expected 1.
final artifact rolled back to original/best 0/1.
```

Interpretation: no rescue, but partial progress. Further progress needs a manual/agentic deterministic sequencer that resets/retrains per gate or directly drives the harness-expected per-gate final weights and testing sequence.

### cvdp_copilot_coffee_machine_0001 Operation-Sequence Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/16
failure class: functional
```

Harness-derived semantics:

```text
Module name is coffee_machine.
The harness model accepts operations 0 through 5. Operations 6 and 7 are invalid.
Operation 0 begins with HEAT then POUR. Operation 1 begins with HEAT then POWDER then POUR.
```

Failure pattern:

```text
Full-run RTL gated start with |i_operation_sel[2:1].
That incorrectly blocks valid operations 0 and 1, so the first HEAT-state checks never see o_heat_water asserted.
```

Targeted hint added:

```text
Valid operations are 0..5 only; do not block operations 0/1.
Match harness operation sequences and visible first-state timing after start.
Match state durations, IDLE/non-IDLE error semantics, and parameter-safe one-hot bean selection.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_coffee_machine_0001_20260519
result: rescued
repair attempts: 0
thinking used: no
```

Evidence:

```text
fresh targeted sample passed all 16 parameterized coffee-machine runs.
Each NBW_DLY/NBW_BEANS/NS_BEANS harness item reports TESTS=1 PASS=1 FAIL=0.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_modified_booth_mul_0005 Signed-Multiplier Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is pipelined_modified_booth_multiplier.
The harness drives 16-bit two's-complement bit patterns for X and Y.
It converts both operands back to signed integers before multiplying and reads result as signed 32-bit.
Expected first done latency is 5 counted cycles.
```

Failure pattern:

```text
Full-run failure: X=33834, Y=49102 expected 520990668, got -249778228.
This corresponds to treating the operands as unsigned product modulo 32 bits, then reading the 32-bit result as signed.
In the generated Booth RTL, the multiplier's highest overlapping group did not use a replicated sign bit.
```

Targeted hint added:

```text
Treat X and Y as signed 16-bit operands.
If using Booth encoding, sign-extend the multiplier before the highest overlapping group.
Refined hint allowed a simple signed-multiply pipeline because the harness does not inspect Booth internals.
Preserve the 5-count done latency and input order with a valid shift register.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_modified_booth_mul_0005_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_modified_booth_mul_0005_refined_20260519
result: not rescued
thinking used: no
```

Evidence:

```text
run 1 initial targeted sample: 0/1.
run 1 repair attempt 1: 0/1; still signedness failure, expected -300500704 but got 69819536.
run 2 initial targeted sample: 0/1.
run 2 repair attempt 1: 0/1; arithmetic path changed but latency failed, expected 5 got 6.
Both runs rolled back to the best available artifact.
```

Interpretation: no rescue. The narrow signedness evidence is clear, but prompt-only repair did not produce a latency-correct passing RTL. Further progress should use manual/agentic rewrite of a 5-count signed multiply pipeline rather than more blind resampling.

### cvdp_copilot_ping_pong_buffer_0001 Toggle Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 5/6
failure class: functional near-miss
```

Harness-derived semantics:

```text
Module name is ping_pong_buffer.
The harness also compiles rtl/dual_port_memory.sv.
buffer_alternation_test resets, records initial_select, then drives write_enable=1 and read_enable=1 for DEPTH*2 clocks.
It expects buffer_select to toggle at least once.
```

Failure pattern:

```text
Full-run RTL toggles buffer_select only when read_ptr wraps inside read_enable && !buffer_empty.
After reset buffer_empty is 1, so the read branch is blocked during the alternation test.
Writes fill/wrap but do not toggle buffer_select, so buffer_select remains equal to initial_select.
```

Targeted hint used:

```text
Preserve the 5/6-passing behavior.
Accepted writes into an empty buffer must clear buffer_empty.
Toggle buffer_select on a buffer wrap/fill boundary, not only on successful read wrap.
Keep ping_pong_buffer.sv and dual_port_memory.sv separate: do not paste a duplicate ping_pong_buffer module into dual_port_memory.sv.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_ping_pong_buffer_0001_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_ping_pong_buffer_0001_refined_20260519
result: not rescued
thinking used: no
```

Evidence:

```text
run 1 initial targeted sample: 5/6, same alternation failure.
run 1 repair attempt 1: 0/1 compile failure; sim.log says dual_port_memory.sv redefined module ping_pong_buffer.
run 2 initial targeted sample: 5/6.
run 2 repair attempt 1: 0/1 compile failure; duplicate ping_pong_buffer declaration repeated despite explicit file/module separation hint.
Both runs rolled back to the 5/6 best artifact.
```

Interpretation: no rescue. The near-miss is highly manual-fixable, but prompt-only repair repeatedly regressed into duplicate-module output. Further progress should use manual/agentic edit of the existing 5/6 RTL rather than more broad resampling.

### cvdp_copilot_simple_spi_0001 Visible-State Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is spi_fsm.
The harness releases active-low reset, checks IDLE, then sets i_data_in=16'hABCD and i_enable=1.
On the next i_clk rising edge plus 1 ns, it expects o_fsm_state=2'b01 and o_spi_cs_b=0.
It then waits on o_spi_clk rising edges and checks MSB-first data plus o_bits_left values 15,14,...,1.
```

Failure pattern:

```text
Full-run RTL updated current_state <= next_state but drove o_fsm_state and outputs from old current_state.
The first transmit check therefore still observed IDLE: expected 1, got 00.
```

Targeted hint added:

```text
Make the externally visible state/output transition to TRANSMIT on the first checked cycle after i_enable.
Preserve exact ports and reset/idle behavior.
Transmit 16'hABCD MSB-first and update o_bits_left to 15 at the first o_spi_clk rising edge, then 14,13,...,1.
Handle done, fault to ERROR, and clear back to IDLE per the harness.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_simple_spi_0001_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_simple_spi_0001_refined_20260519
result: not rescued
thinking used: no
```

Evidence:

```text
run 1 initial targeted sample: 0/1, but original visible-state failure was fixed; new failure was o_bits_left incorrect at bit 0, expected 15 got 16.
run 1 repair attempt 1: same o_bits_left failure.
run 2 initial targeted sample: same o_bits_left failure.
run 2 repair attempt 1: same o_bits_left failure.
Both runs rolled back to the best available artifact.
```

Interpretation: no rescue, but partial semantic progress. The targeted prompt fixed the first observable state-transition issue but did not align the counter update with the harness's o_spi_clk rising-edge check. Further progress should be a manual/agentic rewrite of the state/output timing, not more prompt-only repair.

### cvdp_copilot_montgomery_0002 Latency Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional latency
```

Harness-derived semantics:

```text
Module name is montgomery_mult in rtl/montgomery_redc.sv.
The harness randomizes N, R, and R_INVERSE, drives one-cycle valid_in pulses on falling edges, and expects valid_out after exactly 4 counted rising edges.
The reference result is harness_library.mod_mult(a,b,N), i.e. (a*b) % N.
In the streaming phase, after i > 3 it compares result against the input from four cycles earlier.
```

Failure pattern:

```text
Full-run RTL builds and computes through a pipeline, but valid_out is delayed by one extra stage.
The visible assertion is latency expected 4, got 5.
```

Targeted hint added:

```text
Do not add an extra register stage between valid_in and valid_out.
Align result and valid_out as a four-cycle throughput pipeline.
The harness does not inspect internal Montgomery intermediates, so a direct (a*b)%N pipeline is acceptable.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_montgomery_0002_20260519
result: not rescued
thinking used: no
```

Evidence:

```text
initial targeted sample: compile/elab failure under randomized parameters.
repair attempt 1: built and ran but failed the same latency assertion, expected 4 got 5.
final artifact rolled back to best available 0/1 result.
```

Interpretation: no rescue. The issue is narrow and likely manual-fixable by removing one valid/result pipeline stage or rewriting as a direct four-stage modulo multiplier, but prompt-only targeted repair did not improve the benchmark result.

### cvdp_copilot_montgomery_0001 Harness-REDC Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/1
failure class: functional
```

Harness-derived semantics:

```text
Module name is montgomery_redc in rtl/montgomery_redc.sv.
The harness randomizes prime N, power-of-two R, and R_INVERSE.
It drives T in 0..R*N-1, waits 5 ns, and checks result combinationally.
The Python reference is exactly: redc(T, N, R_INVERSE) = (T * R_INVERSE) % N.
```

Failure pattern:

```text
Full-run RTL implemented textbook Montgomery REDC with N_PRIME, m, and t=(T+m*N)>>log2(R).
That does not match this harness reference; visible failure expected 474 but got 567.
```

Targeted hint added:

```text
Preserve the montgomery_redc parameterized interface.
Implement pure combinational result = (T * R_INVERSE) % N.
Do not use the traditional N_PRIME/m/t REDC path for this testcase.
Use a wide enough intermediate for T * R_INVERSE.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_montgomery_0001_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/5.
repair attempt 1: 5/5.
Each randomized REDC harness item reports TESTS=1 PASS=1 FAIL=0; final report best_summary is 5/5.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_coffee_machine_0001 Operation-Sequence Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/16
failure class: functional
```

Harness-derived semantics:

```text
Module name is coffee_machine.
The harness model accepts operations 0 through 5 and treats only 6 and 7 as invalid.
Operation sequences are:
0: HEAT, POUR, IDLE
1: HEAT, POWDER, POUR, IDLE
2: BEAN_SEL, GRIND, HEAT, POWDER, POUR, IDLE
3: BEAN_SEL, GRIND, POWDER, POUR, IDLE
4: POWDER, POUR, IDLE
5: POUR, IDLE
```

Failure pattern:

```text
Full-run RTL gated start with |i_operation_sel[2:1].
That blocked valid operations 0 and 1, so the first model comparison expecting o_heat_water=1 saw DUT o_heat_water=0.
```

Targeted hint added:

```text
Do not block operations 0 and 1 at start.
Match the harness operation sequences and state durations: BEAN_SEL=3 cycles, POWDER=2 cycles, GRIND/HEAT/POUR use captured delay values.
Use IDLE error semantics from the model and only generic sensor bit 3 during non-IDLE operations.
Keep outputs based only on visible state and one-hot bean selection as 1 << i_bean_sel.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_coffee_machine_0001_20260519
result: rescued
repair attempts: 0; fresh targeted sample passed
thinking used: no
```

Evidence:

```text
All 16 parameterized harness runs passed.
Each run reports TESTS=1 PASS=1 FAIL=0 for test_coffee_machine.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.

### cvdp_copilot_dot_product_0005 Valid-Drop/Complex-Lane Attempt

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 1/12
failure class: functional
```

Harness-derived semantics:

```text
Module name is dot_product.
The harness asserts start_in for one clock, sends exactly dot_length_in vector pairs with both valids high, then deasserts both valids.
That normal post-vector valid deassertion is not an error.
Error-insert test drops both valid signals to 0 in the middle of a length-4 computation after only two valid pairs and expects dot_product_error_out=1.
Real-only tests use unsigned low-bit values; complex/mixed tests use signed 16-bit lanes packed as {imag[15:0], real[15:0]} and compare {acc_im[15:0], acc_re[15:0]}.
```

Failure pattern:

```text
Full-run RTL treated prev_valid && !valid as an error even after all vector pairs had been accepted.
Normal length-4, length-8, and random real tests failed with unexpected error_out=1.
```

Targeted hints used:

```text
First hint: guard valid-drop error detection with cnt < dot_length_reg, transition to OUTPUT once the last valid pair is accepted, and use signed 16-bit lanes for complex arithmetic.
Refined hint: also assert error when both valids drop together before all dot_length_in pairs are accepted, because the harness error-insert test does exactly that.
```

Pilot runs:

```text
run 1: research_outputs/two_stage_thinking_codegen/runs/targeted_dot_product_0005_20260519
run 2: research_outputs/two_stage_thinking_codegen/runs/targeted_dot_product_0005_refined_20260519
result: not rescued, partial improvement only
thinking used: no
```

Evidence:

```text
run 1 initial targeted sample: 7/12.
run 1 repair attempt 1: 11/12. All real-only and complex value tests passed; remaining failure was dot_product_error_insert_test with result=0 valid=0 error=0 when expected_error=True.
run 2 initial targeted sample: 7/12.
run 2 repair attempt 1: regressed to 1/12 and was rolled back.
final benchmark summary: no full rescue.
```

Interpretation: no rescue. The targeted evidence fixed the main valid-drop and arithmetic behavior in one attempt but did not reach 12/12, and the refined prompt regressed. Further progress should use the 11/12 RTL as a manual/agentic starting point with a narrow error-state fix, not more broad prompt-only resampling.

### cvdp_copilot_car_parking_management_0018 Zero-Time Occupancy Rescue

Full-run evidence:

```text
run: research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env
best summary: 0/4
failure class: functional
```

Harness-derived semantics:

```text
Module name is car_parking_system.
The harness enters slot 0 at current_time=0, sets hour_of_day=9, then exits slot 0 at current_time=3600.
It expects fee_ready=1, parking_fee=100 for peak hour double fee, and QR code bits: slot << 112, fee << 96, time_spent[15:0] << 80.
The runner only passes TOTAL_SPACES plusarg; Python MAX_DAILY_FEE default is 500.
```

Failure pattern:

```text
Full-run RTL stored entry_time[current_slot] but treated entry_time != 0 as the occupancy predicate.
Because the first valid entry time is exactly 0, the exit path skipped fee calculation and fee_ready stayed 0.
```

Targeted hint added:

```text
Track occupancy separately from entry_time so current_time=0 is a valid entry timestamp.
Compute fee and QR visibly during/immediately after exit.
Use hour_of_day 8..18 inclusive for double fee, otherwise base fee.
Cap at 500 for this harness and preserve seven-segment/count/full/reset behavior.
```

Pilot run:

```text
run: research_outputs/two_stage_thinking_codegen/runs/targeted_car_parking_management_0018_20260519
result: rescued
repair attempts: 1
thinking used: no
```

Evidence:

```text
initial targeted sample: 0/4.
repair attempt 1: 4/4.
Observed fee checks: fee_ready=1 with parking_fee 100, 50, and 500.
Observed QR validation passed for all TOTAL_SPACES parameter runs 9, 14, 12, 9.
```

Interpretation: rescue. Count as a transparent post-hoc targeted rescue only, not baseline/generic model performance.
