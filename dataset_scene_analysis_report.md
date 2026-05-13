# CVDP Dataset Scene Analysis Report

本报告基于 `full_dataset/` 下的 CVDP v1.1.0 数据集，以及当前已有结果目录：

- `work_codegen_v110`
- `work_comprehension_v110_thinking`

报告重点不是 JSONL 格式，而是数据集的场景设计思想：为什么要设计这些 case、每类任务测什么能力、agentic 与 non-agentic 的差别，以及如何借鉴这些设计构造自己的硬件 benchmark。

## 1. 总体设计思想

CVDP 的核心不是按 Verilog 语法点来分类，而是按硬件工程工作流来分类。

它关注的问题不是：

```text
模型会不会写 always_ff / assign / case
```

而是：

```text
模型能否完成一个真实硬件工程师会遇到的任务。
```

因此，CVDP 覆盖了以下能力：

| 能力大类 | 目标 |
|---|---|
| RTL 生成 | 根据规格、上下文或 skeleton 生成可验证 RTL |
| RTL 修改 | 在已有代码基础上安全增加功能或改变行为 |
| 模块复用与集成 | 读懂多个已有模块并写 top-level glue logic |
| Debug | 根据失败现象定位 bug 并最小化修复 |
| Lint / QoR | 不改变功能的前提下提升代码质量、面积、综合友好性 |
| Verification | 生成 stimulus、checker、scoreboard、assertion |
| Code comprehension | 从 RTL/testbench 中理解设计意图和验证意图 |
| Agentic workflow | 在 repo 里读文件、改文件、运行工具、迭代修复 |

## 2. v1.1.0 数据集规模

`full_dataset/` 中 v1.1.0 的主要文件如下。

| 文件 | 数量 | 覆盖内容 |
|---|---:|---|
| `cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl` | 302 | RTL 生成、修改、lint/QoR、debug |
| `cvdp_v1.1.0_nonagentic_code_generation_commercial.jsonl` | 187 | testbench stimulus、checker、SVA assertion |
| `cvdp_v1.1.0_nonagentic_code_comprehension.jsonl` | 123 | RTL/testbench 理解、spec 对应、问答 |
| `cvdp_v1.1.0_agentic_code_generation_no_commercial.jsonl` | 92 | repo 内 RTL 生成、修改、集成、debug |
| `cvdp_v1.1.0_agentic_code_generation_commercial.jsonl` | 68 | repo 内 verification/assertion/testbench |

合计：772 条本地 v1.1.0 样例。

## 3. Agentic 与 Non-Agentic 的本质差异

Agentic 与 non-agentic 的差别不是文件格式，而是目标能力不同。

| 维度 | Non-Agentic | Agentic |
|---|---|---|
| 输入方式 | 一次性给 prompt 和必要上下文 | 给 mini repo，让 agent 自己探索文件 |
| 任务形态 | 单轮模型回答 | 多步读文件、改文件、运行工具 |
| 难度范围 | easy / medium 为主 | easy / medium / hard 都有 |
| 主要测试 | 模型单次理解和生成能力 | 工程流程能力 |
| 典型任务 | 根据 spec 生成一个模块 | 在 repo 中实现、修改、集成或 debug |
| 评价重点 | 输出是否通过 harness | 最终 repo 是否被正确修改 |
| 类比 | 面试题、Copilot 单次补全 | 工程师接一个 issue |

### 3.1 Non-Agentic 适合测什么

Non-agentic 更适合测模型本身的单次能力。

适合场景：

- 单模块 RTL 生成
- 局部补全
- 简单修改
- lint/QoR 改写
- RTL/spec correspondence
- testbench/test plan correspondence
- 单轮设计问答

优点：

- 成本低
- 容易批量评估
- 结果更容易归因到模型能力
- 不受 agent 工具策略影响

缺点：

- 不测文件探索能力
- 不测工具使用能力
- 不测多轮迭代修复
- 不自然覆盖大型 repo 任务

### 3.2 Agentic 适合测什么

Agentic 更适合测真实工程流程能力。

适合场景：

- 多文件修改
- 模块复用和集成
- repo 内 debug
- 需要查看 docs/spec/testbench 的任务
- 需要运行仿真或 lint 的任务
- checker / assertion / verification 增强

Agentic 任务测试的能力包括：

| 能力 | 为什么重要 |
|---|---|
| 文件定位 | 真实工程中不会把所有信息都塞进 prompt |
| 多文件一致修改 | RTL、top、testbench、docs 之间常有关联 |
| repo 结构理解 | 工程师需要知道该改哪个文件 |
| 工具使用 | 仿真/lint 是硬件开发核心反馈来源 |
| 失败后迭代 | 第一次 patch 往往不会直接过 |
| patch 控制 | 真实工程要求最小改动，不破坏无关代码 |
| 模块集成 | SoC/RTL 开发大量是 glue logic 和 IP reuse |

## 4. 场景分类总览

| CID | 场景 | 主要 split | 设计目标 |
|---|---|---|---|
| cid002 | RTL Code Completion | non-agentic | 补全已有 skeleton 中缺失的 RTL |
| cid003 | Spec to RTL | non-agentic / agentic | 根据规格生成完整 RTL |
| cid004 | RTL Code Modification | non-agentic / agentic | 修改已有设计并保持兼容 |
| cid005 | Module Reuse / Integration | agentic | 集成已有 IP，写 top-level glue logic |
| cid006 | RTL / Spec Correspondence | non-agentic comprehension | 从 RTL 找对应 spec 功能块 |
| cid007 | Code Improvement / Lint / QoR | non-agentic | 不改功能前提下提升代码质量 |
| cid008 | Testbench / Test Plan Correspondence | non-agentic comprehension | 从 testbench 找验证意图对应实现 |
| cid009 | RTL Q&A | non-agentic comprehension | 解释 RTL 行为、corner case、控制逻辑 |
| cid010 | Testbench Q&A | non-agentic comprehension | 解释 testbench 验证策略 |
| cid012 | Testbench Stimulus Generation | commercial / agentic | 生成覆盖充分的 stimulus |
| cid013 | Testbench Checker Generation | commercial / agentic | 生成 checker、reference model、scoreboard |
| cid014 | Assertion Generation | commercial / agentic | 写 SVA/时序属性/协议断言 |
| cid016 | Debugging / Bug Fixing | non-agentic / agentic | 根据失败行为修 bug |

## 5. 每个 CID 的设计目的、样例与场景价值

### 5.1 cid002: RTL Code Completion

代表样例：

```text
cvdp_copilot_64b66b_decoder_0001
```

任务内容：

- 补全一个 64b/66b decoder。
- 输入是 66-bit word。
- 输出 64-bit decoded data。
- 需要解析 2-bit sync header。
- 只支持 data encoding，unsupported control encoding 输出 0 或 invalid 状态。

为什么设计这个 case：

- 工程中经常不是从零写模块，而是补全已有 skeleton。
- 这种任务要求模型理解已有端口、已有代码结构、注释和缺失逻辑。
- 比纯 spec-to-code 更接近 Copilot 补全场景。

主要考察能力：

- bit slicing
- default handling
- invalid path
- 保持原模块接口
- 局部逻辑补全而不重写整个文件

模型常见失败：

- sync header 判断写反
- 宽度错误
- 忽略 unsupported control encoding
- 引入不必要状态机
- 改坏已有 skeleton

已有结果：

```text
work_codegen_v110 cid002: 38.09%
```

结论：

这类任务表面简单，但失败率很高。它适合构造基础但有区分度的 RTL 生成数据。

### 5.2 cid003: RTL Spec to Code

Non-agentic 代表样例：

```text
cvdp_copilot_16qam_mapper_0001
```

任务内容：

- 根据自然语言规格实现 QAM16 mapper with interpolation。
- 需要把 input bits 映射到 I/Q symbol。
- 需要计算相邻 symbol 间的 interpolation。

Agentic 代表样例：

```text
cvdp_agentic_PCIe_endpoint_0001
```

任务内容：

- 在 repo 中实现 PCIe endpoint。
- 需要处理 TLP decode、DMA interface、MSI-X interrupt 和 FSM。

为什么设计这个场景：

- 这是最基础的 spec-to-implementation 能力。
- 硬件工程中大量任务是从自然语言 spec 写 RTL。
- Agentic 版本进一步测试模型能否读 docs、找文件、输出到正确路径。

Non-agentic 的设计重点：

- 测模型单次从规格生成 RTL 的能力。
- prompt 提供最小 oracle context，不考检索。

Agentic 的设计重点：

- 测 agent 是否能阅读 repo。
- 测是否能把文档、已有接口、测试要求关联起来。
- 测是否能处理多文件或复杂目录结构。

主要考察能力：

- 规格理解
- FSM 设计
- 协议时序
- datapath 实现
- reset/valid/done 行为

已有结果：

```text
work_codegen_v110 cid003: 43.08%
```

结论：

spec-to-RTL 是必须有的基础场景，但如果 dataset 只有这类，会过度偏向“写新模块”，不能充分覆盖真实工程。

### 5.3 cid004: RTL Code Modification

代表样例：

```text
cvdp_agentic_AES_encryption_decryption_0009
```

任务内容：

- 把已有 AES-128 encryption module 改成 AES-256 encryption。
- 需要理解原 key expansion、round logic、接口宽度变化。

另一个样例：

```text
cvdp_agentic_barrel_shifter_0002
```

任务内容：

- 给已有 barrel shifter 增加 arithmetic shift mode。
- 保持原有 logical shift 行为。

为什么设计这个场景：

- 真实工程更常见的是修改已有代码，而不是从零写。
- 模型需要理解原实现，然后做局部、安全、兼容的修改。
- 这是检验“工程可用性”的关键场景。

主要考察能力：

- 读懂已有 RTL
- 控制修改范围
- 接口兼容
- 不破坏旧功能
- 多文件一致性

模型常见失败：

- patch 过大
- 新功能实现了但旧功能坏了
- 接口改了但 testbench/top 没同步
- 参数传播不完整
- key schedule / round count / mode handling 错误

已有结果：

```text
work_codegen_v110 cid004: 47.64%
```

结论：

这是当前 no-commercial codegen 中表现最好的类别，说明已有代码上下文能帮助模型。但仍有超过一半失败，说明安全修改仍然困难。

### 5.4 cid005: Module Reuse / Integration

代表样例：

```text
cvdp_agentic_64b66b_codec_0001
```

任务内容：

- 实现 64b/66b top-level codec。
- 集成 data encoder、control encoder 和 combined decoder。
- 写 data/control path 的 glue logic。

另一个样例：

```text
cvdp_agentic_uart_0001
```

任务内容：

- 集成 `uart_tx`、`uart_rx`、`baud_gen`、`cdc_sync` 等 submodule。
- 实现完整 UART system。

为什么设计这个场景：

- 真实 SoC/RTL 工作大量是集成已有 IP。
- 难点不在单个 always block，而在接口语义、控制协调和 glue logic。
- 这类任务天然适合 agentic，因为需要探索多个文件。

主要考察能力：

- 读懂多个 submodule 的端口和行为
- 连接 clock/reset/control/data
- 设计 top-level FSM 或 mux/demux
- 处理 valid/ready/enable
- 保持模块边界清晰

模型常见失败：

- 端口接错
- control/data path 混淆
- reset polarity 错
- 忽略 backpressure
- top-level 只实例化但没有 glue logic

结论：

如果你要构造 agent benchmark，这类场景优先级非常高。

### 5.5 cid006: RTL / Spec Correspondence

代表样例：

```text
cvdp_copilot_binary_to_BCD_0017
```

任务内容：

- 从 `binary_to_bcd.sv` 中找出 check-and-add-3 操作对应代码块。

另一个样例：

```text
cvdp_copilot_axi_stream_downscale_0005
```

任务内容：

- 从 `axis_resize.sv` 中找出把大 slave transaction 拆成多个 master transaction 的代码。

为什么设计这个场景：

- 工程师经常需要 review 代码，确认某段 spec 是否真的实现。
- 这是 code reading + semantic alignment，而不是生成。
- 它能测模型是否真的理解 RTL 的功能块。

主要考察能力：

- 从自然语言 spec 映射到 RTL block
- 精确定位相关代码
- 区分核心逻辑和周边 glue logic
- 理解算法实现形态

模型常见失败：

- 返回过多无关代码
- 找到相似但不对应的 block
- 忽略功能分散在多个 always/task 中
- 只按关键词匹配，不理解语义

已有结果：

```text
work_comprehension_v110_thinking cid006: 70.47%
```

结论：

这是很好的 comprehension 场景，比普通 Q&A 更有区分度。

### 5.6 cid007: Code Improvement / Lint / QoR

代表样例：

```text
cvdp_copilot_IIR_filter_0019
```

任务内容：

- 对 IIR filter 做 lint cleanup。
- 修 unused parameter、width mismatch、simulation/synthesis warning。

另一个样例：

```text
cvdp_copilot_64b66b_encoder_0022
```

任务内容：

- 做 area optimization。
- 减少 cells/wires，同时保持原功能。

为什么设计这个场景：

- 工程代码不是功能通过就结束。
- lint clean、综合质量、面积、QoR 都是实际交付标准。
- 这类任务要求模型理解“非功能性约束”。

主要考察能力：

- 不改变功能的代码重构
- width/sign 修复
- multi-driver 修复
- latch 避免
- 面积优化
- synthesis-friendly RTL

模型常见失败：

- 为了消 warning 改坏功能
- 删除必要逻辑
- 优化不等价
- 引入 latch
- 只做表面修改，没有改善 QoR

已有结果：

```text
work_codegen_v110 cid007: 37.50%
```

结论：

这是高区分度场景。自建 dataset 时应该保留这类任务，因为它很接近真实工程质量要求。

### 5.7 cid008: Testbench / Test Plan Correspondence

代表样例：

```text
cvdp_copilot_MSHR_0005
```

任务内容：

- 从 `tb_cache_mshr` stimulus generator 中找出保证 finalize request index 已被 allocated 的 6 个代码块。

另一个样例：

```text
cvdp_copilot_axi_tap_0007
```

任务内容：

- 找出 AXI4-Lite TAP testbench 中 address decode 和 routing verification 的相关代码块。

为什么设计这个场景：

- 验证工程的关键是理解 testbench 在测什么。
- testbench 的意图经常分散在 task、monitor、scoreboard、random constraint 中。
- 这比 RTL/spec correspondence 更难，因为 verification code 更过程化。

主要考察能力：

- 理解 test plan
- 理解 testbench task/function
- 找 stimulus 与 checker 的对应关系
- 识别 verification intent

模型常见失败：

- 返回 stimulus，而不是 checker
- 找到初始化代码而非验证代码
- 忽略 random constraint
- 不理解 scoreboard 延迟对齐

已有结果：

```text
work_comprehension_v110_thinking cid008: 62.85%
```

结论：

这是 comprehension 中最难的一类，也是自建 dataset 最值得重点投入的理解类场景。

### 5.8 cid009: RTL Question & Answer

代表样例：

```text
cvdp_copilot_apb_gpio_0011
```

任务内容：

- 分析 `reg_gpio_dir` 和 `module_active` 如何控制 GPIO 双向行为。
- 解释 power-down、reset 条件和潜在限制。

另一个样例：

```text
cvdp_copilot_cascaded_adder_0019
```

任务内容：

- 分析 pipeline register 配置为何不一定总是提升性能。

为什么设计这个场景：

- 工程师需要解释设计行为，不只是写代码。
- 这类任务测试模型是否能把 RTL 转化成设计级解释。

主要考察能力：

- 控制逻辑解释
- corner case 分析
- reset/power-down 语义
- pipeline / latency / throughput tradeoff

模型常见失败：

- 只复述代码
- 忽略 corner case
- 对时序行为解释不准确
- 没指出潜在限制

已有结果：

```text
work_comprehension_v110_thinking cid009: 87.06%
```

结论：

模型普遍擅长这类问答。它有价值，但区分度不如 cid006/cid008。

### 5.9 cid010: Testbench Question & Answer

代表样例：

```text
cvdp_copilot_apb_gpio_0012
```

任务内容：

- 解释 testbench 如何通过 `apb_write` 和 `apb_read` 验证 Direction Control Register。

另一个样例：

```text
cvdp_copilot_barrel_shifter_0059
```

任务内容：

- 解释 `mask` 信号为何让 mode=11 的验证更复杂，以及 testbench 如何验证正确性。

为什么设计这个场景：

- 验证工程师需要解释 testbench 的策略和覆盖意图。
- 它测试模型是否理解 verification flow，而不是只理解 RTL。

主要考察能力：

- testbench 流程理解
- task 交互理解
- checker/monitor 语义
- coverage intent

已有结果：

```text
work_comprehension_v110_thinking cid010: 87.92%
```

结论：

当前模型表现很强。若要提高区分度，应把问题设计成：找覆盖漏洞、分析 false positive/false negative、解释 checker 不充分之处。

### 5.10 cid012: Testbench Stimulus Generation

代表样例：

```text
cvdp_agentic_direct_map_cache_0005
```

任务内容：

- 为 direct-map cache 写 testbench stimulus。
- 覆盖 read/write、compare/non-compare、forced miss 等场景。

另一个样例：

```text
cvdp_agentic_async_fifo_compute_ram_application_0004
```

任务内容：

- 为 async FIFO 写双时钟域 stimulus。

为什么设计这个场景：

- 验证第一步是生成有效且有覆盖意义的激励。
- 这不是随机喂输入，而是要知道哪些 corner case 必须覆盖。

主要考察能力：

- reset/init sequence
- 时钟生成
- handshake 合法性
- corner case 覆盖
- constrained stimulus

模型常见失败：

- stimulus 不合法
- 没有覆盖 corner case
- 没有处理 reset
- 双时钟域时序错误
- cache/FIFO 状态覆盖不足

结论：

这是 verification 类核心场景。论文中 verification 类整体显著难于普通 RTL generation。

### 5.11 cid013: Testbench Checker Generation

代表样例：

```text
cvdp_agentic_alu_0007
```

任务内容：

- 已有 ALU stimulus testbench。
- 增加 reference function 和 output checker。

另一个样例：

```text
cvdp_agentic_64b66b_codec_0007
```

任务内容：

- 为 64b/66b codec testbench 增加 checker。
- 覆盖 data-only、control、mixed-mode、invalid input。

为什么设计这个场景：

- Verification 的核心不是输入，而是判断输出对不对。
- Checker/scoreboard 比 stimulus 更难。
- 论文中 cid013 是最低分、最难类别之一。

主要考察能力：

- reference model
- expected/actual comparison
- latency alignment
- scoreboard
- coverage
- procedural SystemVerilog

模型常见失败：

- reference model 本身错误
- checker 与 DUT 犯同样错误
- 比较时机错
- 延迟对齐错
- 只检查部分字段
- SV 语法错误

结论：

如果你要构造高区分度硬件 benchmark，cid013 是最值得投入的场景之一。

### 5.12 cid014: Assertion Generation

代表样例：

```text
cvdp_agentic_axi4lite_to_pcie_config_0005
```

任务内容：

- 给 AXI4-Lite to PCIe config bridge 添加 SVA。
- 验证 `awready`、`wready`、`arready` 等握手时序。

另一个样例：

```text
cvdp_agentic_axis_to_uart_0013
```

任务内容：

- 给 hierarchical UART / AXI-Stream design 添加 assertions。

为什么设计这个场景：

- SVA 是高级 verification 能力。
- 它要求模型理解 temporal property，而不是只写组合/时序逻辑。
- 语法正确不代表 assertion 有验证价值。

主要考察能力：

- concurrent assertion
- clocking / reset disable
- implication 时序
- protocol property
- bounded latency
- safety / liveness 区分

模型常见失败：

- assertion 放错位置
- reset 条件错
- `|->` / `|=>` 用错
- property 太强导致 false fail
- property 太弱没有价值
- immediate/concurrent assertion 混用

结论：

这是非常适合 agentic benchmark 的高难场景。

### 5.13 cid016: Debugging / Bug Fixing

代表样例：

```text
cvdp_agentic_barrel_shifter_0001
```

任务内容：

- 给定失败行为：输入 `00100100`，shift=1，left_right=1。
- 期望输出 `01001000`，实际输出 `00010010`。
- 修 barrel shifter 方向逻辑。

另一个样例：

```text
cvdp_agentic_axis_broadcaster_0001
```

任务内容：

- 修 AXI Stream broadcaster 在 backpressure 下的数据转发错误。

为什么设计这个场景：

- 真实工程中 debug 比从零写模块更常见。
- 模型必须从失败现象反推 bug，而不是照 spec 生成。
- Agentic debug 还可以测试是否会读 test、跑仿真、迭代修复。

主要考察能力：

- bug localization
- 最小 patch
- 协议理解
- 回归风险控制
- 从 test failure 反推设计错误

模型常见失败：

- 只改 test，不改 RTL
- hard-code 某个失败 case
- 修一个 case 破坏其他 case
- 没理解 valid/ready/backpressure
- patch 范围过大

已有结果：

```text
work_codegen_v110 cid016: 44.57%
```

结论：

debug 类任务非常贴近工程实际，是自建 dataset 的高价值方向。

## 6. 结合已有结果的难点分析

当前本地已有完整结果主要有：

| 结果目录 | 数据集 | 模型 | 总体结果 |
|---|---|---|---:|
| `work_codegen_v110` | non-agentic codegen no-commercial | `vllm-glm` | 41.79% |
| `work_comprehension_v110_thinking` | non-agentic comprehension | `vllm-glm thinking` | 76.95% |

### 6.1 Codegen 类结果

| CID | 场景 | 结果 | 解读 |
|---|---|---:|---|
| cid002 | Code completion | 38.09% | 局部补全并不简单，容易错接口/宽度/默认分支 |
| cid003 | Spec to RTL | 43.08% | 基础生成能力中等偏好 |
| cid004 | Code modification | 47.64% | 已有代码上下文对模型帮助较大 |
| cid007 | Lint/QoR improvement | 37.50% | 很难做到不改功能的安全优化 |
| cid016 | Debugging | 44.57% | 简单 bug 可修，复杂协议 bug 仍难 |

难度差异：

| Difficulty | 结果 |
|---|---:|
| Easy | 53.95% |
| Medium | 27.71% |

结论：

- Medium 任务是主要分水岭。
- 模型不是简单语法不行，而是复杂状态、协议、corner case 和工程约束不稳。
- `cid007` 和 `cid002` 是当前 no-commercial codegen 中最弱的类别。

### 6.2 Comprehension 类结果

| CID | 场景 | 结果 | 解读 |
|---|---|---:|---|
| cid006 | RTL/spec correspondence | 70.47% | 精确定位 RTL 功能块仍有难度 |
| cid008 | TB/test plan correspondence | 62.85% | 最难，verification intent 分散且过程化 |
| cid009 | RTL Q&A | 87.06% | 模型强项，区分度较低 |
| cid010 | TB Q&A | 87.92% | 模型强项，但需更难问题提高区分度 |

结论：

- Q&A 类普遍高分。
- Correspondence 类更有区分度。
- 如果自建 comprehension 数据集，应少做泛泛问答，多做定位、对应、覆盖漏洞分析。

## 7. 自建数据集的场景设计方法论

### 7.1 从硬件主题出发，而不是从题目出发

先选真实硬件主题：

| 主题 | 适合派生任务 |
|---|---|
| FIFO / async FIFO | CDC、full/empty、overflow、checker、assertion |
| AXI / APB / AXI-Stream | protocol、backpressure、address decode、SVA |
| UART / SPI / I2C | FSM、baud、parity、testbench |
| Cache / MSHR | outstanding request、replacement、ordering |
| AES / DES | bit-accurate、round logic、mode change |
| FIR / IIR / QAM | fixed-point、overflow、mapping |
| FSM controller | reset、illegal state、sequence detection |
| register bank / memory | byte enable、read/write hazard、APB access |

### 7.2 同一主题派生一组任务

以 async FIFO 为例：

| CID 风格 | 任务 |
|---|---|
| cid003 | 根据 spec 实现 async FIFO |
| cid004 | 增加 almost_full / almost_empty |
| cid007 | 修 CDC/lint warning |
| cid012 | 写双时钟 stimulus |
| cid013 | 写 scoreboard 检查读写顺序 |
| cid014 | 写 SVA 验证 full/empty/gray pointer |
| cid016 | 修 full/empty off-by-one bug |
| cid006 | 找 RTL 中 gray pointer sync 逻辑 |
| cid010 | 解释 testbench 如何避免 race |

这样一个主题可以形成一组互相关联的 benchmark，不是孤立题目。

### 7.3 每个 case 都要有明确失败模式

设计 case 时要先回答：

| 问题 | 示例 |
|---|---|
| 这个 case 测什么能力？ | backpressure 下 valid/ready 是否保持 |
| 模型常犯什么错？ | ready low 时仍推进 data |
| harness 如何抓错？ | 随机 stall + scoreboard |
| 为什么真实？ | AXI-Stream 模块都需要处理 backpressure |
| 和其他 case 差异是什么？ | 不是 data transform，而是协议时序 |

### 7.4 推荐场景优先级

| 优先级 | 场景 | 原因 |
|---|---|---|
| P0 | Debug | 最贴近真实工程，容易设计失败现象 |
| P0 | Module reuse | agentic 高价值，多文件、多接口 |
| P0 | Checker generation | 论文显示非常难，区分度高 |
| P0 | Assertion generation | 高级 verification 能力，模型常错 |
| P1 | Code modification | 真实工程常见，测兼容性 |
| P1 | Lint/QoR | 测工程质量，不只是功能 |
| P1 | Spec-to-RTL | 基础能力，必须有 |
| P2 | Code completion | 成本低，但要避免变语法题 |
| P2 | Correspondence | 理解类高价值 |
| P3 | 简单 Q&A | 可少量保留，区分度较低 |

### 7.5 推荐数据集比例

如果目标是通用硬件 LLM：

| 类型 | 建议比例 |
|---|---:|
| Non-agentic | 60% |
| Agentic | 40% |
| Codegen | 45% |
| Modification / Debug | 25% |
| Verification | 20% |
| Comprehension | 10% |

如果目标是硬件 agent：

| 类型 | 建议比例 |
|---|---:|
| Agentic | 60% |
| Non-agentic | 40% |
| Multi-file integration/debug | 35% |
| Verification/checker/assertion | 35% |
| Single-turn generation | 20% |
| Comprehension | 10% |

### 7.6 应避免的坑

| 坑 | 后果 |
|---|---|
| 只考语法 | 模型很快饱和，区分度低 |
| 题目太开放 | 难以自动验证 |
| 没有 corner case | happy path 通过但工程无意义 |
| prompt 很长但没有重点 | 测到的是上下文处理，不是硬件能力 |
| 只做 spec-to-code | 覆盖不了真实工程工作流 |
| checker 太弱 | 错误 RTL 也能通过 |
| reference 不稳定 | 结果不可解释 |
| 没有失败分类 | 后续无法知道模型为什么失败 |

## 8. 题目正确性与质量保障

CVDP 的题目正确性不是靠自然语言描述本身保证，而是靠 reference solution、harness、专家 review 和版本修复共同保证。

### 8.1 什么叫“题目是对的”

对 code generation 类任务，一个题目至少要满足：

| 要求 | 含义 |
|---|---|
| 规格可执行 | prompt/spec 能推出明确行为，不依赖出题人隐含理解 |
| reference solution 通过 | golden/reference RTL 能通过同一个 harness |
| harness 能抓错 | 常见错误实现不能轻易通过测试 |
| 工具链稳定 | verilator/yosys/cocotb/xcelium 等版本和命令固定 |
| 输出约束明确 | 模型知道应该写哪个模块、接口、文件或代码片段 |

对 comprehension 类任务，一个题目至少要满足：

| 要求 | 含义 |
|---|---|
| source context 足够 | 被问到的 RTL/testbench 信息确实在上下文中 |
| reference answer 可比对 | golden answer 覆盖关键语义点 |
| 评分标准稳定 | BLEU/ROUGE 或 LLM judge rubric 不随意变化 |
| 问题不歧义 | 不允许多个互相矛盾的合理答案 |

因此，不能把 CVDP 的题目理解成“绝对数学证明正确”。更准确的说法是：它是经过硬件专家、reference solution、自动 harness 和版本迭代校准过的 benchmark。

### 8.2 CVDP 已体现的 QA 机制

从 `full_dataset/CHANGELOG` 可以看出，CVDP 不是一次性冻结的静态题库，而是在持续修正数据和 harness。

| 机制 | 作用 |
|---|---|
| SME review | 硬件领域专家检查题目、答案、场景合理性 |
| Golden/reference solution | 用已知正确实现验证 harness 可运行 |
| Harness sanity check | 确认标准答案能 pass，明显错误能 fail |
| LLM-based filtering | 过滤过易、过难、歧义或质量差的数据点 |
| CHANGELOG 修复 | 记录 datapoint、harness、工具版本的修正 |

已知版本修复包括 datapoint 重新校准、harness 修复、商业工具版本固定、commercial/no-commercial split 调整。这说明题库质量有工程 QA，但也说明任何硬件 benchmark 都需要版本化和回归验证。

### 8.3 自建题库的正确性检查清单

如果自己构造 dataset，建议每个 case 都走下面流程：

1. 写自然语言 spec、接口约束、输出要求。
2. 写 reference/golden solution。
3. 写 harness，包括 happy path、corner case、随机测试或形式/静态检查。
4. 运行 golden，必须通过。
5. 准备 2 到 5 个 broken baseline，必须失败。
6. 人工检查 prompt 是否歧义，尤其是 reset、valid/ready、overflow、latency、tie-breaking。
7. 固定工具版本和命令行。
8. 记录 category、difficulty、expected failure modes。
9. 每次改 harness 后重跑 golden 和 broken baseline。
10. 用 CHANGELOG 记录题目、harness、工具版本变更。

最关键的一点是：不要只证明 golden 能过，还要证明错误实现不能过。否则 benchmark 只是在测模型能否取巧通过弱测试。

## 9. 评价机制：不同 CID 的 Oracle

CVDP 的评分不是所有题都用同一种 oracle。code generation 主要是客观工具/harness，comprehension 则混合使用文本相似度和 LLM judge。

| CID | 场景 | 主要 oracle | 分数形态 |
|---|---|---|---|
| cid002 | RTL code completion | docker harness + RTL tests | binary pass/fail |
| cid003 | spec to RTL | docker harness + RTL tests | binary pass/fail |
| cid004 | RTL code modification | docker harness + regression tests | binary pass/fail |
| cid005 | module reuse/integration | agentic repo harness | binary pass/fail |
| cid006 | RTL/spec correspondence | BLEU/ROUGE，report 主要聚合 BLEU | fractional score |
| cid007 | lint/QoR/code improvement | harness、lint、synthesis-oriented checks | binary pass/fail |
| cid008 | testbench/test plan correspondence | BLEU/ROUGE，report 主要聚合 BLEU | fractional score |
| cid009 | RTL Q&A | LLM judge | fractional score |
| cid010 | testbench Q&A | LLM judge | fractional score |
| cid012 | testbench stimulus generation | simulation/commercial verification harness | binary pass/fail |
| cid013 | checker generation | simulation/commercial verification harness | binary pass/fail |
| cid014 | assertion generation | SVA/formal/simulation harness | binary pass/fail |
| cid016 | debugging/bug fixing | failing test becomes passing regression | binary pass/fail |

### 9.1 Code Generation 如何评分

Code generation 路径大致是：

```text
模型输出代码 -> 写入临时 repo/UUT -> 运行 docker harness -> 收集 tests -> 生成 report
```

对二元任务，最终判定很严格：

```text
所有 required tests 通过 -> problem pass
任一 required test 失败 -> problem fail
```

这类指标的优点是客观、可复现、接近真实硬件开发。缺点是 harness 的强弱会直接决定 benchmark 的可信度：如果 corner case 不够，错误实现也可能 pass。

### 9.2 Comprehension 如何评分

Comprehension 分两类：

| CID | 方法 | 解释 |
|---|---|---|
| cid006/cid008 | BLEU/ROUGE | 衡量模型回答与 reference answer 的文本/片段重合度 |
| cid009/cid010 | LLM judge | 让 judge model 按 relevance、semantic similarity、completeness、correctness、style/format 给 `0.0` 到 `1.0` 分 |

在当前实现里，cid006、cid008、cid009、cid010 属于 score-based category。report 不把它们简单转成 pass/fail，而是把分数按 fractional problem 计入汇总。

也就是说，如果一个 cid009 问题的平均 judge score 是 `0.8`，它在 report 中近似贡献：

```text
Passed Problems += 0.8
Failed Problems += 0.2
```

这类指标适合看趋势和相对比较，不应解释成形式验证意义上的“正确”。尤其是 LLM judge 类任务，结果依赖 judge 模型、rubric 和 prompt 稳定性。

### 9.3 Report 与 Composite Report 如何生成

单次运行会生成 sample report，例如：

```text
work_xxx/sample_1/report.json
```

`run_reporter.py` 会把 JSON report 渲染成可读文本，按 category、difficulty、overall 汇总。

多 sample 运行由 `run_samples.py -n 5 -k 1` 组织，最后生成：

```text
work_xxx/composite_report.json
work_xxx/composite_report.txt
```

对 binary codegen category，当前 composite 结果的直观含义更接近 expected pass@1：一个题 5 次中通过 `c` 次时，贡献约为 `c / 5`。这和文本里“A problem passes if it passes in at least 1 out of 5 samples”的表述容易混淆，解读报告时应以 JSON 中实际聚合值为准。

对 score-based comprehension category，composite 主要是把多个 sample 的分数取平均。

## 10. 对当前已有结果的解读

当前两个结果目录的性质不同，不能直接混成一个 overall benchmark 结论。

| 结果目录 | 数据集 | 任务性质 | 主要结论 |
|---|---|---|---|
| `work_codegen_v110` | no-commercial code generation, 302 problems, 5 samples | 客观 harness pass/fail | 平均 pass rate `41.79%`，说明 GLM 在 RTL 生成/修改/debug 上仍有大量失败 |
| `work_comprehension_v110_thinking` | code comprehension, 123 problems, 5 samples | BLEU/ROUGE + LLM judge fractional score | 平均 `76.95%`，说明理解类任务明显高于生成类任务 |

Codegen 各类结果：

| CID | 场景 | 当前结果 |
|---|---|---:|
| cid002 | RTL completion | `38.09%` |
| cid003 | spec to RTL | `43.08%` |
| cid004 | RTL modification | `47.64%` |
| cid007 | lint/QoR improvement | `37.50%` |
| cid016 | debugging | `44.57%` |

Comprehension 各类结果：

| CID | 场景 | 当前结果 |
|---|---|---:|
| cid006 | RTL/spec correspondence | `70.47%` |
| cid008 | testbench/test plan correspondence | `62.85%` |
| cid009 | RTL Q&A | `87.06%` |
| cid010 | testbench Q&A | `87.92%` |

这个结果符合硬件 benchmark 的常见规律：理解和解释代码通常比生成能通过真实 harness 的 RTL 更容易；verification/testbench correspondence 比一般 RTL Q&A 更难，因为它要求理解测试意图、覆盖点和 checker 逻辑。

## 11. 最终建议

如果要构造自己的硬件 benchmark，不要从格式开始，而要从场景矩阵开始。

推荐路线：

1. 选 8 到 12 个真实硬件主题。
2. 每个主题派生 6 到 10 个任务。
3. 每个任务明确能力目标和失败模式。
4. Non-agentic 用来测单轮模型能力。
5. Agentic 用来测多文件、多步骤、工具使用和 repo 操作能力。
6. Verification、checker、assertion、debug 是最有区分度的方向。
7. 简单 Q&A 可以保留，但不要作为主要部分。

一句话总结：

```text
CVDP 的精髓是用真实硬件工程动作组织 benchmark：
写代码、改代码、集成模块、修 bug、写验证、理解验证。
```
