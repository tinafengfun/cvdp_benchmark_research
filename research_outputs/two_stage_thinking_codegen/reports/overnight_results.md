# 通宵批量处理结果

## 新 RESCUED（18个）

| Case | 类型 |
|------|------|
| 64b66b_decoder_0011 | functional |
| 64b66b_encoder_0009 | functional |
| 64b66b_encoder_0022 | functional+synth |
| Carry_Lookahead_Adder_0005 | functional |
| configurable_digital_low_pass_filter_0014 | functional |
| fan_controller_0008 | functional+synth |
| fsm_seq_detector_0023 | functional |
| load_store_unit_0009 | functional |
| manchester_enc_0005 | docker_timeout |
| matrix_multiplier_0007 | functional |
| matrix_multiplier_0010 | functional |
| modified_booth_mul_0005 | functional |
| perceptron_0006 | functional |
| sorter_0009 | functional |
| sorter_0031 | functional |
| sorter_0057 | functional+synth |
| sorter_0059 | docker_timeout |
| sprite_0004 | functional |

## 总计统计

| 类别 | 数量 |
|------|------|
| Baseline pass | 188 |
| Targeted hints rescue | 38 |
| Thinking mode rescue | 19 |
| Agentic self-debug rescue | 2 |
| Manual deep-dive rescue (本轮) | 3 |
| **Batch rescue（本轮）** | **18** |
| **投影 pass** | **188+38+19+2+3+18 = 268/302 = 88.7%** |
| 剩余未解决 | 34 |

## 剩余 34 个 case 状态
- tests_failing: 23（功能仿真失败，需要 deep 分析）
- sim_no_tests: 11（仿真未正常执行）
- compile_failed_no_fix: 1（fifo_to_axis — iverilog segfault）
