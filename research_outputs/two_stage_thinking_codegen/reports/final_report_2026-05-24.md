# CVDP Benchmark 302-Case Residual Rescue — 最终报告

## 总体统计

| 指标 | 数值 |
|------|------|
| 全量 dataset | 302 cases |
| Baseline pass（non-thinking codegen） | 188/302（62.3%） |
| + Targeted hints rescue | 38（+12.6%） |
| + Thinking mode rescue | 19（+6.3%） |
| + Agentic self-debug rescue | 2（+0.7%） |
| **合计 rescued** | **59（+19.5%）** |
| **投影 pass** | **247/302 = 81.8%** |
| 剩余 non-rescued | 55（18.2%） |

## 各方案成功率

| 方案 | 尝试数 | 成功数 | 成功率 |
|------|--------|--------|--------|
| Targeted hints（手动分析+hint） | ~114 | 38 | ~33% |
| Thinking mode（64KB, vLLM-GLM） | ~55 | 19 | 35% |
| Agentic self-debug（执行反馈循环） | 10 | 2 | 20% |

## 剩余 55 个 Non-rescued 分析

### 按推荐处理方式

| 分类 | 数量 | 占比 | 说明 |
|------|------|------|------|
| thinking_pilot（未尝试过思考模式） | 35 | 64% | 还可继续用 thinking 尝试 |
| deep_fsm_timing（已试thinking失败） | 6 | 11% | 需要 agentic 重写 |
| compile_persistent（编译问题） | 6 | 11% | 需针对性 compile 修复 |
| thinking_regression_compile | 6 | 11% | thinking 导致编译退化 |
| unfixable（跳过） | 2 | 4% | 模型知识边界/仿真不终止 |

### 按 bucket/类型

| 类型 | 数量 | Case 举例 |
|------|------|-----------|
| 窄 timing/FSM（可继续 thinking） | 35 | elevator_control, gaussian_div, interrupt_controller... |
| Deep FSM timing（需 agentic） | 6 | fifo_to_axis, skid_buffer, sync_serial, vending_machine... |
| Compile/elab（需 compile repair） | 3 | MSHR_0001, interrupt_controller_0019, serial_in_parallel |
| Lint（需手工清理） | 3 | cont_adder, sigma_delta, hill_cipher |
| QoR（需架构级重写） | 3 | sorter_0057/0059, fan_controller |
| Agentic/pass@k | 3 | 64b66b_encoder_0022, aes_key_expansion, elevator_0033 |
| Finetune | 1 | axis_border_gen_0014 |
| Skip | 1 | manchester_enc_0005 |

## 深度分析 6 个 Case 的发现

### 1. digital_stopwatch_0001
- **问题**: 测试时序期望与标准计数器行为不匹配
- **尝试**: 5种不同实现，全部失败
- **结论**: 无法通过简单 RTL 修复

### 2. hebbian_rule_0012
- **问题**: 原始 RTL 使用硬编码训练序列，忽略外部 a/b 输入
- **修复**: 外部 a/b 采样 + 修正 targets → **权重计算 100% 正确**
- **遗留**: 测试 FSM 微码 bug（非训练问题）

### 3. pipeline_mac_0017
- **修复**: Agentic+Thinking 第 5 轮成功 🎉
- **根因**: valid_out cycle 偏移

### 4. register_file_2R1W_0006
- **问题**: BIST 触发信号 `bist_start` 未被测试驱动
- **修复**: 改为 `test_mode` 触发
- **遗留**: 后 BIST 写 0xA5A5A5A5 读回 0x1F（地址 MUX 问题）

### 5. ir_receiver_0005
- **发现的4个bug**:
  1. bit_count 阈值 31 → 应改为 11（12位NEC协议）
  2. frame_space 阈值 449 → 应改为 399（40ms测试间隔）
  3. 首下降沿被误捕获为 bit 0
  4. decoding 状态 failed 条件与 started 冲突
- **修复**: 1+2+3 已应用，4 仍需调整

### 6. binary_search_tree_sorting_0014
- **修复**: Agentic self-debug 第 1 轮成功 🎉

## 关键结论

1. **Thinking mode 有效但有限**: 35% rescue 率，最适合窄 timing/FSM 问题
2. **Agentic self-debug 有潜力**: 20% rescue 率，需要更多轮次（5轮不够）
3. **Deep FSM timing 是最难点**: 6个 case 在 thinking + targeted + agentic 都失败
4. **剩余 55 个中 35 个未尝试 thinking**: 可以继续跑完
5. **模型知识边界**: axis_border_gen 和 manchester_enc 基本无解
