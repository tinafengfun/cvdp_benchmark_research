# Full Funnel Failure Review: 2026-05-15

## 结论

本轮结果可以作为后续工作的 baseline。它不是 thinking run，而是 non-thinking first-pass 加 non-thinking feedback repair。`nohup` 中共有 `599` 次 `generation_stats`，其中 `thinking_enabled=True` 为 `0`，`thinking_enabled=False` 为 `599`，`reasoning_len > 0` 为 `0`。所有解析到的 generation `finish_reason` 为 `{'stop': 599}`，`retry_mode` 为 `{'none': 599}`。

本轮主要价值不是单一 pass rate，而是把 302 case 拆成 first-pass、repair rescue、compile/elab、timeout、model-output rejection 和 semantic residual。当前没有证据表明 residual 中还有 Docker network、cocotb empty logging 或 summary parser 这类 infra 假失败。

## 数据与 Artifact

- Dataset: `full_dataset/cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl`
- Run directory: `research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env`
- Raw result: `research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/raw_result.json`
- Benchmark report: `research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/report.txt`
- Repair summary: `research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env.summary.txt`
- Nohup log: `research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env.nohup.log`
- Failure CSV: `research_outputs/two_stage_thinking_codegen/reports/full_funnel_failure_cases_2026-05-15.csv`
- Failure JSON: `research_outputs/two_stage_thinking_codegen/reports/full_funnel_failure_cases_2026-05-15.json`

## Run 配置

```text
Model: vllm-glm
Workflow: non-agentic code generation
Threads: 4
First-pass thinking: false
Repair thinking: false
Repair enabled: true
Repair max attempts: 2
Targeted hints: true
Focused harness: true
Skip synth build: true
Cocotb empty-log sanitizer: true
DOCKER_TIMEOUT: 600
CVDP_REPAIR_DOCKER_TIMEOUT: 600
MODEL_TIMEOUT: 900
OSS_SIM_IMAGE: nvidia/cvdp-sim:v1.0.0
```

## 总体结果

```text
Total problems: 302
Passed problems: 188
Failed problems: 114
Problem pass rate: 62.25%
First pass: 131
Repair attempted: 169
Repair rescued: 57
Rollback count: 119
Returned best count: 96
Improved not rescued: 17
```

Benchmark `report.txt` 中记录：problem pass `188/302 = 62.25%`，test pass `223/342 = 65.20%`，easy `118/162 = 72.84%`，medium `70/140 = 50.00%`。

## Failure Class 分布

| 中文类别 | class | count | 补救方向 |
| --- | --- | --- | --- |
| 功能语义失败 | functional | 73 | 按近似程度分层：near-miss 用 focused harness + targeted invariant repair；zero-pass/大范围失败优先 agentic debug 或 pass@k；最后再判 finetune。 |
| 编译/展开失败 | compile_elab | 23 | 优先自动补救：做 compile/elab-only repair，向模型提供 iverilog 命令、顶层名、参数化实例和首个报错；这类通常比语义失败更可救。 |
| 仿真非终止/超时 | docker_timeout | 10 | 优先 agentic/debug：先定位 RTL 状态机/ready-valid/循环终止条件；不建议简单延长 timeout。可对少量 case 做 thinking/pass@k ablation。 |
| 功能+综合优化失败 | functional_and_synth_optimization | 6 | 拆开处理：先确认功能剩余失败，再单独给综合优化目标和 Yosys diff 做 repair；不要把 synth 优化失败混入功能能力判断。 |
| 模型输出被前置校验拒绝 | model_output_rejected | 2 | 优先自动补救：增加严格 module-name re-prompt 或允许一次 checker-specific retry；不需要 thinking。 |

## Difficulty 分布

| difficulty | failed cases | class breakdown |
| --- | --- | --- |
| easy | 44 | functional:32, compile_elab:7, docker_timeout:4, functional_and_synth_optimization:1 |
| medium | 70 | functional:41, compile_elab:16, docker_timeout:6, functional_and_synth_optimization:5, model_output_rejected:2 |

## Category 分布

| category | failed cases | class breakdown |
| --- | --- | --- |
| cid002 | 38 | functional:23, compile_elab:11, docker_timeout:3, model_output_rejected:1 |
| cid003 | 23 | functional:18, compile_elab:4, docker_timeout:1 |
| cid004 | 25 | functional:14, compile_elab:7, docker_timeout:3, model_output_rejected:1 |
| cid007 | 13 | functional:5, docker_timeout:2, functional_and_synth_optimization:6 |
| cid016 | 15 | functional:13, compile_elab:1, docker_timeout:1 |

## 补救优先级

| bucket | count | classes |
| --- | --- | --- |
| agentic_debug | 10 | docker_timeout |
| agentic_or_passk | 47 | functional |
| cheap_reprompt | 2 | model_output_rejected |
| compile_repair | 23 | compile_elab |
| near_miss_repair | 5 | functional |
| semantic_repair_or_passk | 21 | functional |
| split_functional_synth | 6 | functional_and_synth_optimization |

建议优先级：

1. `model_output_rejected`: 成本最低，先做 checker-specific re-prompt 或 module-name fix retry。
2. `compile_repair`: 高可补救，加入 compile/elab-only repair loop，通常比语义修复更确定。
3. `near_miss_repair`: 已通过大多数 tests，适合 focused harness invariant repair 或小规模 thinking/pass@k。
4. `split_functional_synth`: 功能和综合优化拆开处理，避免把 synth objective 当成纯功能失败。
5. `agentic_debug`: timeout、zero-pass 大型语义失败、复杂协议类，优先 agentic debug。

## Timeout Cases

这 10 个不是 Docker/network timeout。日志无 `get-pip.py`、`pypi.org`、Docker build network failure、cocotb empty logging crash 或 parser crash。9 个进入 cocotb；`perf_counters_0001` 进入 pytest runner 并使用本地 cached image。`sorter_0003` 已单线程 `DOCKER_TIMEOUT=1200` 复核，仍 timeout，repair attempt 也非终止。

| case_id | reason | primary_log |
| --- | --- | --- |
| cvdp_copilot_axi_alu_0001 | timeout after partial functional failure: assert 0 == 9 | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_axi_alu/reports/1.txt |
| cvdp_copilot_binary_search_tree_sorting_0001 | entered cocotb/pytest then timed out without completing current test | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_binary_search_tree_sorting/reports/1.txt |
| cvdp_copilot_binary_search_tree_sorting_0014 | timeout after partial functional failure: assert 5 == 4 | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_binary_search_tree_sorting/reports/14_repair_2.txt |
| cvdp_copilot_elevator_control_0033 | entered cocotb/pytest then timed out without completing current test | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_elevator_control/reports/33_sanity.txt |
| cvdp_copilot_gcd_0009 | timeout after partial functional failure: assert LogicArray('00000', Range(4, 'downto', 0)) == 1 | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_gcd/reports/9_repair_1.txt |
| cvdp_copilot_gcd_0023 | timeout after partial functional failure: assert 4 == 3 | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_gcd/reports/23_repair_2.txt |
| cvdp_copilot_ir_receiver_0001 | entered cocotb/pytest then timed out without completing current test | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_ir_receiver/reports/1.txt |
| cvdp_copilot_perf_counters_0001 | pytest runner started then timed out before cocotb progress | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_perf_counters/reports/1.txt |
| cvdp_copilot_sorter_0003 | entered cocotb/pytest then timed out without completing current test | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_sorter/reports/3.txt |
| cvdp_copilot_sorter_0059 | entered cocotb/pytest then timed out without completing current test | /mnt/disk9/tianfeng/cvdp/cvdp_benchmark/research_outputs/two_stage_thinking_codegen/runs/full_codegen_t4_funnel_fixed_env/cvdp_copilot_sorter/reports/59_sanity.txt |

## Model Output Rejected

这两个 case 没有进入 harness，也没有 repair。它们是 module-name checker 拒绝，属于 cheap retry 候选，不应当计入语义能力失败。

| case_id | reason |
| --- | --- |
| cvdp_copilot_axis_border_gen_0014 | Generated RTL module-name check failed: expected one of ['axis_border_gen_with_resize'], but found modules ['axis_image_border_gen_with_resizer', 'axis_image_resizer'] |
| cvdp_copilot_bus_arbiter_0004 | Generated RTL module-name check failed: expected one of ['bus_arbiter'], but found modules ['cvdp_copilot_bus_arbiter'] |

## Near-Miss Functional/Synth Residuals

以下 case best pass ratio >= 80%，最适合作为下一阶段自动补救起点。完整列表见 CSV。

| case_id | class | best | reason |
| --- | --- | --- | --- |
| cvdp_copilot_64b66b_decoder_0011 | functional | 8/10 | assert 18374403900871474942 == 506381209866536711 |
| cvdp_copilot_cont_adder_0042 | functional | 8/9 | assert subprocess.run(cmd, shell=True).returncode == 0, "Linting return errors." |
| cvdp_copilot_fsm_seq_detector_0023 | functional | 5/6 | assert Logic('0') == 1 |
| cvdp_copilot_gcd_0045 | functional_and_synth_optimization | 18/19 | assert error == 0, "Error to remove previous synth log." |
| cvdp_copilot_ping_pong_buffer_0001 | functional | 5/6 | assert Logic('0') != Logic('0') |
| cvdp_copilot_sigma_delta_audio_0007 | functional | 10/11 | assert subprocess.run(cmd, shell=True).returncode == 0, "Linting return errors." |
| cvdp_copilot_sorter_0057 | functional_and_synth_optimization | 34/35 | assert error == 0, "Error to remove previous synth log." |

## 是否已经上 thinking

没有。本轮所有模型调用均为 non-thinking：

```text
generation_stats_count: 599
thinking_true_count: 0
thinking_false_count: 599
reasoning_nonzero_count: 0
finish_reason_counts: {'stop': 599}
retry_mode_counts: {'none': 599}
```

因此本轮结果不能回答 thinking 是否能救 residual。下一步如果要测试 thinking，应只在 residual 子集上做 ablation，不建议直接全量开 thinking。此前 live diagnostic 已看到 codegen thinking 可能出现 `finish_reason=length`、`content_len=0`、大量 reasoning token 的风险。

## Failure Case 明细

| case_id | cat | diff | class | best | bucket | reason |
| --- | --- | --- | --- | --- | --- | --- |
| cvdp_copilot_64b66b_decoder_0011 | cid002 | medium | functional | 8/10 | near_miss_repair | assert 18374403900871474942 == 506381209866536711 |
| cvdp_copilot_64b66b_encoder_0009 | cid004 | medium | functional | 10/13 | semantic_repair_or_passk | assert 40568425447074609920 == 40630856516737433600 |
| cvdp_copilot_64b66b_encoder_0022 | cid007 | medium | functional_and_synth_optimization | 11/14 | split_functional_synth | assert 39055348948860899102 == 39072237447463538462 |
| cvdp_copilot_8x3_priority_encoder_0013 | cid004 | easy | compile_elab | 0/6 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'cascaded_encoder', '-g2012', '-Pcascaded_encoder.N=4', '-Pcascaded_encoder.M=2', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/cascaded_encoder.v']' returned non-zero exit stat |
| cvdp_copilot_Carry_Lookahead_Adder_0005 | cid016 | easy | functional | 0/1 | agentic_or_passk | assert 2605134277 == 1218168113 |
| cvdp_copilot_MSHR_0001 | cid002 | medium | compile_elab | 0/10 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'cache_mshr', '-g2012', '-Pcache_mshr.MSHR_SIZE=4', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/cache_mshr.sv']' returned non-zero exit status 1. |
| cvdp_copilot_MSHR_0008 | cid002 | medium | compile_elab | 0/10 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'cache_mshr', '-g2012', '-Pcache_mshr.MSHR_SIZE=24', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/cache_mshr.sv']' returned non-zero exit status 2. |
| cvdp_copilot_aes_key_expansion_0001 | cid007 | medium | functional_and_synth_optimization | 1/2 | split_functional_synth | assert error == 0, "Error to remove previous synth log." |
| cvdp_copilot_ahb_clk_counter_0001 | cid002 | easy | compile_elab | 0/1 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'ahb_clock_counter', '-g2012', '-Pahb_clock_counter.ADDR_WIDTH=32', '-Pahb_clock_counter.DATA_WIDTH=32', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/ahb_clock_counter.sv']' re |
| cvdp_copilot_apb_gpio_0005 | cid004 | medium | functional | 12/18 | semantic_repair_or_passk | assert False |
| cvdp_copilot_apb_history_shift_register_0001 | cid003 | medium | functional | 0/1 | agentic_or_passk | assert 0 == 11 |
| cvdp_copilot_axi_alu_0001 | cid016 | medium | docker_timeout | 0/0 | agentic_debug | timeout after partial functional failure: assert 0 == 9 |
| cvdp_copilot_axi_register_0001 | cid003 | medium | compile_elab | 6/6 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'axi_register', '-g2012', '-Paxi_register.ADDR_WIDTH=12', '-Paxi_register.DATA_WIDTH=8', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/axi_register.sv']' returned non-zero exit  |
| cvdp_copilot_axi_stream_upscale_0001 | cid003 | easy | functional | 0/1 | agentic_or_passk | assert Logic('1') == 0 |
| cvdp_copilot_axi_tap_0009 | cid004 | medium | functional | 0/20 | agentic_or_passk | TESTS=1 PASS=0 FAIL=1 SKIP=0 |
| cvdp_copilot_axis_border_gen_0001 | cid002 | medium | functional | 0/3 | agentic_or_passk | assert Logic('0') == True |
| cvdp_copilot_axis_border_gen_0014 | cid002 | medium | model_output_rejected | 0/0 | cheap_reprompt | Generated RTL module-name check failed: expected one of ['axis_border_gen_with_resize'], but found modules ['axis_image_border_gen_with_resizer', 'axis_image_resizer'] |
| cvdp_copilot_barrel_shifter_0058 | cid004 | medium | compile_elab | 0/1 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'barrel_shifter', '-g2012', '-Pbarrel_shifter.data_width=8', '-Pbarrel_shifter.shift_bits_width=3', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/barrel_shifter.sv']' returned n |
| cvdp_copilot_binary_multiplier_0012 | cid004 | easy | compile_elab | 0/4 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'binary_multiplier', '-g2012', '-Pbinary_multiplier.WIDTH=25', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/binary_multiplier.sv']' returned non-zero exit status 2. |
| cvdp_copilot_binary_search_tree_sorting_0001 | cid002 | medium | docker_timeout | 0/0 | agentic_debug | entered cocotb/pytest then timed out without completing current test |
| cvdp_copilot_binary_search_tree_sorting_0014 | cid002 | medium | docker_timeout | 3/4 | agentic_debug | timeout after partial functional failure: assert 5 == 4 |
| cvdp_copilot_bus_arbiter_0004 | cid004 | medium | model_output_rejected | 0/0 | cheap_reprompt | Generated RTL module-name check failed: expected one of ['bus_arbiter'], but found modules ['cvdp_copilot_bus_arbiter'] |
| cvdp_copilot_cache_lru_0019 | cid002 | medium | functional | 0/1 | agentic_or_passk | assert 0 == 3 |
| cvdp_copilot_caesar_cipher_0001 | cid003 | easy | functional | 3/4 | semantic_repair_or_passk | assert 'aHsaEqbi' == 'aNsgEqbo' |
| cvdp_copilot_car_parking_management_0015 | cid004 | medium | compile_elab | 0/4 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'car_parking_system', '-g2012', '-DSIMULATION=1', '-Pcar_parking_system.TOTAL_SPACES=9', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/car_parking_system.sv']' returned non-zero |
| cvdp_copilot_car_parking_management_0018 | cid002 | medium | functional | 0/4 | agentic_or_passk | assert Logic('0') == 1 |
| cvdp_copilot_cascaded_adder_0025 | cid002 | medium | compile_elab | 4/4 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'cascaded_adder', '-g2012', '-Pcascaded_adder.IN_DATA_NS=4', '-Pcascaded_adder.IN_DATA_WIDTH=3', '-Pcascaded_adder.REG=1', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/cascaded |
| cvdp_copilot_coffee_machine_0001 | cid016 | medium | functional | 0/16 | agentic_or_passk | assert 0 == 1 |
| cvdp_copilot_compression_engine_0001 | cid002 | easy | functional | 0/2 | agentic_or_passk | assert False |
| cvdp_copilot_configurable_digital_low_pass_filter_0004 | cid003 | medium | functional | 21/32 | semantic_repair_or_passk | assert [0, 0, 0, 0, 0, 0, ...] == [15749, -7297, -24834, 15852, -6859, 28026, ...] |
| cvdp_copilot_configurable_digital_low_pass_filter_0014 | cid003 | easy | functional | 0/35 | agentic_or_passk | assert 1 == 0 |
| cvdp_copilot_cont_adder_0042 | cid007 | easy | functional | 8/9 | near_miss_repair | assert subprocess.run(cmd, shell=True).returncode == 0, "Linting return errors." |
| cvdp_copilot_decoder_8b10b_0001 | cid002 | easy | functional | 1/5 | semantic_repair_or_passk | assert '00000000' == '10011100' |
| cvdp_copilot_digital_stopwatch_0001 | cid003 | easy | functional | 0/3 | agentic_or_passk | assert 10 == 9 |
| cvdp_copilot_digital_stopwatch_0012 | cid004 | easy | functional | 0/3 | agentic_or_passk | assert dut.hours.value == 0, f"Initial hours is not 0! Got: {dut.hour.value}" |
| cvdp_copilot_dot_product_0005 | cid004 | medium | functional | 1/12 | semantic_repair_or_passk | assert (1/12) |
| cvdp_copilot_elevator_control_0006 | cid004 | easy | compile_elab | 0/4 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'elevator_control_system', '-g2012', '-DSIMULATION=1', '-Pelevator_control_system.N=8', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/elevator_control_system.sv', '/code/rtl/flo |
| cvdp_copilot_elevator_control_0009 | cid004 | medium | compile_elab | 0/4 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'elevator_control_system', '-g2012', '-DSIMULATION=1', '-Pelevator_control_system.N=8', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/elevator_control_system.sv', '/code/rtl/flo |
| cvdp_copilot_elevator_control_0026 | cid002 | medium | compile_elab | 0/4 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'elevator_control_system', '-g2012', '-DSIMULATION=1', '-Pelevator_control_system.N=12', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/elevator_control_system.sv', '/code/rtl/fl |
| cvdp_copilot_elevator_control_0033 | cid007 | medium | docker_timeout | 0/1 | agentic_debug | entered cocotb/pytest then timed out without completing current test |
| cvdp_copilot_fan_controller_0008 | cid007 | medium | functional_and_synth_optimization | 0/2 | split_functional_synth | assert Logic('1') == 0 |
| cvdp_copilot_fibonacci_series_0001 | cid003 | easy | functional | 0/2 | agentic_or_passk | assert 2 == 1 |
| cvdp_copilot_fifo_to_axis_0001 | cid002 | easy | compile_elab | 0/1 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'ping_pong_fifo_2_axi_stream', '-g2012', '-Pping_pong_fifo_2_axi_stream.DATA_WIDTH=8', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/ping_pong_fifo_2_axi_stream.sv']' returned n |
| cvdp_copilot_findfasterclock_0001 | cid002 | medium | compile_elab | 0/1 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'findfasterclock', '-g2012', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/findfasterclock.sv']' returned non-zero exit status 1. |
| cvdp_copilot_fsm_seq_detector_0023 | cid016 | easy | functional | 5/6 | near_miss_repair | assert Logic('0') == 1 |
| cvdp_copilot_galois_encryption_0001 | cid016 | medium | functional | 0/1 | agentic_or_passk | assert 0 == 15699573566928413898813171887891756181 |
| cvdp_copilot_gaussian_rounding_div_0005 | cid002 | medium | compile_elab | 0/2 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'divider', '-g2012', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/divider.sv']' returned non-zero exit status 30. |
| cvdp_copilot_gaussian_rounding_div_0022 | cid007 | medium | functional | 1/3 | semantic_repair_or_passk | assert 0.0 == 2.5 |
| cvdp_copilot_gcd_0001 | cid003 | easy | functional | 0/10 | agentic_or_passk | assert LogicArray('00000', Range(4, 'downto', 0)) == 2 |
| cvdp_copilot_gcd_0009 | cid004 | easy | docker_timeout | 0/0 | agentic_debug | timeout after partial functional failure: assert LogicArray('00000', Range(4, 'downto', 0)) == 1 |
| cvdp_copilot_gcd_0023 | cid004 | medium | docker_timeout | 0/0 | agentic_debug | timeout after partial functional failure: assert 4 == 3 |
| cvdp_copilot_gcd_0045 | cid007 | medium | functional_and_synth_optimization | 18/19 | split_functional_synth | assert error == 0, "Error to remove previous synth log." |
| cvdp_copilot_hebbian_rule_0012 | cid004 | medium | functional | 0/1 | agentic_or_passk | assert dut.w1.value.signed_integer == 2, f"Expected w1=2, but got {dut.w1.value}" |
| cvdp_copilot_hebbian_rule_0017 | cid003 | medium | compile_elab | 0/1 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'hebb_gates', '-g2012', '-s', 'cocotb_iverilog_dump', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/hebb_gates.sv', '/code/rundir/sim_build/cocotb_iverilog_dump.v']' returned no |
| cvdp_copilot_hill_cipher_0001 | cid003 | medium | functional | 2/4 | semantic_repair_or_passk | assert 19026 == 0 |
| cvdp_copilot_hill_cipher_0015 | cid007 | easy | functional | 1/3 | semantic_repair_or_passk | assert subprocess.run(cmd, shell=True).returncode == 0, "Linting return errors." |
| cvdp_copilot_hmac_register_0001 | cid002 | medium | functional | 0/24 | agentic_or_passk | assert 1 == 0 |
| cvdp_copilot_icache_controller_0001 | cid002 | medium | functional | 0/5 | agentic_or_passk | assert 1105612831 == 319586916 |
| cvdp_copilot_image_rotate_0001 | cid002 | easy | functional | 7/10 | semantic_repair_or_passk | assert [[12746, 40982, 4695, 4041, 48356, 37127, ...], [50449, 56572, 21044, 51022, 19437, 14034, ...], [10162, 64037, 50627, 35839, 338, 60590, ...], [0, 0, 0, 0, 0, 0, ...], [0, 0, 0, 0, 0, 0, ...], [0, 0, 0, 0, 0, 0, ...], ...] == [[0, 0, 0, 0, 0, 0, ...], [0, 0, 0, 0, 0, 0, . |
| cvdp_copilot_image_stego_0004 | cid016 | easy | functional | 3/5 | semantic_repair_or_passk | assert 1428837674 == 2907876690 |
| cvdp_copilot_interrupt_controller_0014 | cid002 | medium | compile_elab | 0/5 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'interrupt_controller', '-g2012', '-Pinterrupt_controller.NUM_INTERRUPTS=1', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/programmable_interrupt_controller.sv']' returned non-z |
| cvdp_copilot_interrupt_controller_0017 | cid002 | medium | compile_elab | 0/11 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'interrupt_controller', '-g2012', '-Pinterrupt_controller.STARVATION_THRESHOLD=5', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/pic_starvation_prevention.sv']' returned non-zer |
| cvdp_copilot_interrupt_controller_0019 | cid002 | medium | compile_elab | 0/7 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'interrupt_controller_apb', '-g2012', '-Pinterrupt_controller_apb.NUM_INTERRUPTS=8', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/interrupt_controller_apb.sv']' returned non-ze |
| cvdp_copilot_ir_receiver_0001 | cid002 | easy | docker_timeout | 0/0 | agentic_debug | entered cocotb/pytest then timed out without completing current test |
| cvdp_copilot_ir_receiver_0005 | cid002 | easy | functional | 1/7 | semantic_repair_or_passk | assert 0 == 129 |
| cvdp_copilot_line_buffer_0003 | cid016 | medium | functional | 48/64 | semantic_repair_or_passk | assert 12827301338928000567427988054 == 56617011311637570682870561366 |
| cvdp_copilot_load_store_unit_0009 | cid004 | medium | functional | 0/1 | agentic_or_passk | assert 3308518656 == 3653579773 |
| cvdp_copilot_manchester_enc_0005 | cid016 | easy | compile_elab | 0/4 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'manchester_encoder', '-g2012', '-Pmanchester_encoder.N=6', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/manchester_encoder.sv']' returned non-zero exit status 2. |
| cvdp_copilot_matrix_multiplier_0007 | cid004 | easy | functional | 13/36 | semantic_repair_or_passk | assert [[10, 12], [30, 36]] == [[19, 22], [43, 50]] |
| cvdp_copilot_matrix_multiplier_0010 | cid004 | medium | functional | 12/36 | semantic_repair_or_passk | assert [[21, 9, 18], [6, 15, 3], [66, 18, 57]] == [[30, 24, 18], [84, 69, 54], [138, 114, 90]] |
| cvdp_copilot_microcode_sequencer_0001 | cid003 | medium | functional | 0/1 | agentic_or_passk | assert Logic('X') == 0 |
| cvdp_copilot_modified_booth_mul_0005 | cid016 | easy | functional | 0/1 | agentic_or_passk | assert -249778228 == 520990668 |
| cvdp_copilot_montgomery_0001 | cid016 | easy | functional | 0/1 | agentic_or_passk | assert 567 == 474 |
| cvdp_copilot_montgomery_0002 | cid016 | easy | functional | 0/1 | agentic_or_passk | assert 5 == 4 |
| cvdp_copilot_nbit_swizzling_0020 | cid004 | easy | functional | 0/5 | agentic_or_passk | TESTS=1 PASS=0 FAIL=1 SKIP=0 |
| cvdp_copilot_one_hot_address_0001 | cid007 | easy | functional | 1/17 | semantic_repair_or_passk | assert 1 == 2 |
| cvdp_copilot_perceptron_0006 | cid004 | medium | functional | 0/1 | agentic_or_passk | assert dut.percep_w1.value.signed_integer == 1, f"Expected w1=1, but got {dut.percep_w1.value}" |
| cvdp_copilot_perceptron_0013 | cid002 | medium | functional | 0/1 | agentic_or_passk | assert dut.percep_w1.value.signed_integer == 1, f"Expected w1=1, but got {dut.percep_w1.value}" |
| cvdp_copilot_perf_counters_0001 | cid003 | easy | docker_timeout | 0/0 | agentic_debug | pytest runner started then timed out before cocotb progress |
| cvdp_copilot_ping_pong_buffer_0001 | cid002 | easy | functional | 5/6 | near_miss_repair | assert Logic('0') != Logic('0') |
| cvdp_copilot_pipeline_mac_0017 | cid002 | easy | functional | 2/9 | semantic_repair_or_passk | assert 0 == 1 |
| cvdp_copilot_piso_0001 | cid003 | easy | functional | 1/5 | semantic_repair_or_passk | assert [0, 0, 0, 0, 0, 0, ...] == [0, 0, 0, 0, 0, 0, ...] |
| cvdp_copilot_prbs_gen_0003 | cid003 | medium | functional | 0/54 | agentic_or_passk | assert 255 == 42 |
| cvdp_copilot_reed_solomon_encoder_and_decoder_0005 | cid002 | easy | functional | 0/10 | agentic_or_passk | assert '0x9a' == '0x1d' |
| cvdp_copilot_register_file_2R1W_0006 | cid004 | medium | functional | 0/1 | agentic_or_passk | assert 1 == 0 |
| cvdp_copilot_scrambler_0001 | cid016 | easy | functional | 0/2 | agentic_or_passk | assert 49577 == 49578 |
| cvdp_copilot_scrambler_0009 | cid016 | medium | functional | 0/36 | agentic_or_passk | assert 0 == 66 |
| cvdp_copilot_sdram_controller_0001 | cid002 | medium | functional | 0/1 | agentic_or_passk | assert Logic('0') == 1 |
| cvdp_copilot_secure_read_write_register_bank_0001 | cid003 | medium | functional | 0/1 | agentic_or_passk | assert LogicArray('00000010', Range(7, 'downto', 0)) == 0 |
| cvdp_copilot_secure_variable_timer_0001 | cid002 | easy | functional | 0/1 | agentic_or_passk | assert LogicArray('0000', Range(3, 'downto', 0)) == 6 |
| cvdp_copilot_sequencial_binary_to_one_hot_decoder_0001 | cid003 | easy | compile_elab | 0/1 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'binary_to_one_hot_decoder_sequential', '-g2012', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/binary_to_one_hot_decoder_sequential.v']' returned non-zero exit status 1. |
| cvdp_copilot_serial_in_parallel_out_0011 | cid004 | medium | compile_elab | 0/10 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'sipo_top', '-g2012', '-Psipo_top.DATA_WIDTH=4', '-Psipo_top.SHIFT_DIRECTION=0', '-Psipo_top.CODE_WIDTH=7', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/serial_in_parallel_out_ |
| cvdp_copilot_serial_in_parallel_out_0014 | cid004 | medium | functional | 0/18 | agentic_or_passk | TESTS=1 PASS=0 FAIL=1 SKIP=0 |
| cvdp_copilot_sigma_delta_audio_0007 | cid007 | easy | functional | 10/11 | near_miss_repair | assert subprocess.run(cmd, shell=True).returncode == 0, "Linting return errors." |
| cvdp_copilot_simple_spi_0001 | cid002 | medium | functional | 0/1 | agentic_or_passk | assert LogicArray('00', Range(1, 'downto', 0)) == 1 |
| cvdp_copilot_skid_buffer_0001 | cid002 | medium | functional | 0/1 | agentic_or_passk | TESTS=1 PASS=0 FAIL=1 SKIP=0 |
| cvdp_copilot_sobel_filter_0011 | cid016 | easy | functional | 0/1 | agentic_or_passk | assert 1 == 9 |
| cvdp_copilot_sorter_0003 | cid004 | medium | docker_timeout | 0/0 | agentic_debug | entered cocotb/pytest then timed out without completing current test |
| cvdp_copilot_sorter_0009 | cid002 | easy | functional | 51/85 | semantic_repair_or_passk | assert 13 == 10 |
| cvdp_copilot_sorter_0031 | cid002 | medium | functional | 21/130 | semantic_repair_or_passk | assert 55 == 53 |
| cvdp_copilot_sorter_0057 | cid007 | easy | functional_and_synth_optimization | 34/35 | split_functional_synth | assert error == 0, "Error to remove previous synth log." |
| cvdp_copilot_sorter_0059 | cid007 | easy | docker_timeout | 1/1 | agentic_debug | entered cocotb/pytest then timed out without completing current test |
| cvdp_copilot_sprite_0004 | cid002 | medium | functional | 0/50 | agentic_or_passk | assert 1 == 0 |
| cvdp_copilot_static_branch_predict_0001 | cid003 | medium | functional | 0/1 | agentic_or_passk | TESTS=1 PASS=0 FAIL=1 SKIP=0 |
| cvdp_copilot_static_branch_predict_0014 | cid002 | medium | functional | 0/1 | agentic_or_passk | assert Logic('1') == 0 |
| cvdp_copilot_swizzler_0014 | cid016 | medium | functional | 1/9 | semantic_repair_or_passk | assert 85 == 170 |
| cvdp_copilot_sync_lifo_0001 | cid003 | medium | functional | 0/5 | agentic_or_passk | TESTS=1 PASS=0 FAIL=1 SKIP=0 |
| cvdp_copilot_sync_serial_communication_0001 | cid003 | medium | compile_elab | 0/20 | compile_repair | subprocess.CalledProcessError: Command '['iverilog', '-o', '/code/rundir/sim_build/sim.vvp', '-s', 'sync_serial_communication_tx_rx', '-g2012', '-f', '/code/rundir/sim_build/cmds.f', '/code/rtl/sync_serial_communication_top.sv']' returned non-zero exit status 1. |
| cvdp_copilot_sync_serial_communication_0014 | cid004 | easy | functional | 0/20 | agentic_or_passk | assert Logic('1') == 0 |
| cvdp_copilot_sync_serial_communication_0052 | cid007 | medium | functional_and_synth_optimization | 16/21 | split_functional_synth | assert 2183 == LogicArray('0000000000000000000000000000000000000000000000000000100010000110', Range(63, 'downto', 0)) |
| cvdp_copilot_ttc_lite_0001 | cid003 | medium | functional | 0/1 | agentic_or_passk | assert 0 == 10 |
| cvdp_copilot_vending_machine_0001 | cid003 | medium | functional | 0/10 | agentic_or_passk | assert Logic('1') == 0 |
| cvdp_copilot_virtual2physical_tlb_0001 | cid002 | medium | functional | 0/10 | agentic_or_passk | assert 0 == 1 |
| cvdp_copilot_wb2ahb_0001 | cid003 | medium | functional | 0/1 | agentic_or_passk | assert Logic('0') == 1 |

## 下一步工作建议

Detailed execution plan:

```text
research_outputs/two_stage_thinking_codegen/residual_rescue_plan_2026-05-15.md
```

1. 先实现/运行 `model_output_rejected` 的 checker-specific retry，目标 2/2 cheap rescue。
2. 对 23 个 `compile_elab` 做 compile-only repair ablation，使用 iverilog 首个错误、顶层名、参数和 failing command。
3. 对 near-miss functional cases 做 focused invariant repair，优先 64b66b、GCD 0045、sorter 0057、sigma-delta、line-buffer、matrix multiplier 等 partial-pass cases。
4. 对 10 个 timeout 做 agentic debug，而不是继续延长 timeout。
5. 对剩余 zero-pass semantic failures 做 pass@k 和 small thinking ablation；thinking 只作为 controlled experiment，不作为默认 baseline。
6. 以上补救后仍失败的 residual 才进入 finetune candidate 池。
