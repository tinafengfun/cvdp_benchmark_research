# Stage 2 Compile/Elab Inspection: 2026-05-17

Source CSV:

```text
research_outputs/two_stage_thinking_codegen/reports/stage2_compile_elab_inspection_2026-05-17.csv
```

Inspected residual set: 17 cases that remained `compile_elab` after the Stage 2 compile-focused repair pass.

Stage 2 context:

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

## Summary

Corrected root-cause clusters:

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

Interpretation: a third generic compile-focused rerun is unlikely to be efficient. The remaining failures have specific signatures that should be attacked with deterministic cleanup or narrow hints.

## Cheap Deterministic Targets

### Line-prefix prose

Cases:

```text
cvdp_copilot_car_parking_management_0015
cvdp_copilot_manchester_enc_0005
```

Evidence:

```text
/code/rtl/car_parking_system.sv:1: syntax error
car_parking_system.sv line 1 contains naked prose before the module declaration

/code/rtl/manchester_encoder.sv:2: syntax error
manchester_encoder.sv line 1 contains a stray "module" before the real module declaration
```

Next action: add or pilot a pre-harness sanitizer that removes non-Verilog prose before the first real module declaration. This should be opt-in or scoped to generated RTL cleanup, with no semantic rewrite.

### Top/module naming mismatch

Cases:

```text
cvdp_copilot_bus_arbiter_0004
cvdp_copilot_sequencial_binary_to_one_hot_decoder_0001
```

Evidence:

```text
cvdp_copilot_bus_arbiter_0004: RTL declares bus_arbiter, but harness invokes cvdp_copilot_bus_arbiter from cvdp_copilot_bus_arbiter.sv
cvdp_copilot_sequencial_binary_to_one_hot_decoder_0001: RTL uses sequencial spelling, but harness invokes sequential spelling
```

Next action: use exact expected top-module hints or a targeted module/file-name retry. For the misspelling case, distinguish model error from harness spelling before counting it as model capability.

### Specific construct rewrites

Cases:

```text
cvdp_copilot_barrel_shifter_0058
cvdp_copilot_gaussian_rounding_div_0005
cvdp_copilot_fifo_to_axis_0001
```

Evidence:

```text
cvdp_copilot_barrel_shifter_0058: generated RTL uses a SystemVerilog inside expression on an Icarus path
cvdp_copilot_gaussian_rounding_div_0005: variables such as D4, D12, D14, D18, and D20 have multiple drivers
cvdp_copilot_fifo_to_axis_0001: iverilog/vvp exits with status 139
```

Next action: pilot one narrow hint per signature. Prefer an Icarus-compatible syntax rewrite for `inside`, a single-driver cleanup for the divider, and direct RTL inspection for the simulator crash before rerun.

## Parameterized Generate/Width Failures

Cases:

```text
cvdp_copilot_axi_register_0001
cvdp_copilot_interrupt_controller_0014
cvdp_copilot_interrupt_controller_0017
cvdp_copilot_interrupt_controller_0019
```

Evidence examples:

```text
axi_register: parameter combinations include ADDR_WIDTH=12, DATA_WIDTH=8
interrupt_controller_0014: NUM_INTERRUPTS=1
interrupt_controller_0017: STARVATION_THRESHOLD=5
interrupt_controller_0019: NUM_INTERRUPTS=8
```

Next action: use parameter/generate/indexing-specific repair. These are not good candidates for prose cleanup or top-name retry.

## Syntax/Compatibility Residuals

Cases:

```text
cvdp_copilot_elevator_control_0006
cvdp_copilot_elevator_control_0009
cvdp_copilot_elevator_control_0026
```

Evidence:

```text
/code/rtl/elevator_control_system.sv:1: syntax error
```

Next action: inspect exact generated RTL per case before rerun. The three cases share a harness/log path pattern, so do not assume the same generated text without checking each source.

## Wrapped Compile Errors Needing Sim Log

Cases:

```text
cvdp_copilot_8x3_priority_encoder_0013
cvdp_copilot_hebbian_rule_0017
cvdp_copilot_sync_serial_communication_0001
```

Evidence:

```text
subprocess.CalledProcessError from iverilog, but the high-level report does not include the first actionable compiler diagnostic
```

Next action: open the corresponding `sim.log` if present or rerun one case with verbose compile capture. Do not use another blind compile-focused repair until the first iverilog diagnostic is available.

## Recommended Pilot Order

1. `cvdp_copilot_car_parking_management_0015`: deterministic line-1 prose cleanup.
2. `cvdp_copilot_manchester_enc_0005`: deterministic stray-token cleanup.
3. `cvdp_copilot_bus_arbiter_0004`: exact top-module/file-name hint.
4. `cvdp_copilot_barrel_shifter_0058`: Icarus-compatible rewrite for `inside`.
5. `cvdp_copilot_gaussian_rounding_div_0005`: single-driver cleanup if direct RTL inspection confirms the listed signals.

## Decision

Stage 2 generic compile-focused repair is complete for this residual bucket. Continue with targeted pilots only. Track direct rescues separately from useful reclassifications, and keep all targeted repair behavior opt-in.
