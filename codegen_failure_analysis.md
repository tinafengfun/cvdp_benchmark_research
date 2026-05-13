# Codegen Failure Analysis: vllm-glm on CVDP v1.1.0 No-Commercial

本报告分析 `work_codegen_v110` 中 `vllm-glm` 在 `cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl` 上的失败 case。

结论先行：模型的主要问题不是单纯“不会写 Verilog”，而是工程化 RTL 生成能力不稳定，集中体现在接口契约、工具兼容、参数位宽、时序/协议、修改定位、debug 最小修复和 lint/QoR 约束上。

## 1. 总体失败统计

数据集规模：302 个 codegen no-commercial case，5 samples。

按“每题 5 次 sample 中通过次数”粗分：

| 5 次中通过次数 | case 数量 | 含义 |
|---:|---:|---|
| 0 | 157 | 稳定失败，模型基本没有掌握该题能力点 |
| 1 | 7 | 偶尔生成正确，但不稳定 |
| 2 | 12 | 有一定概率正确，但可靠性不足 |
| 3 | 14 | 接近可用，但仍受采样影响 |
| 4 | 2 | 大多数通过 |
| 5 | 110 | 稳定通过 |

稳定失败 case 约 `157 / 302 = 52.0%`。这比整体 pass rate 更说明问题：不是只有随机 sample 质量波动，而是有一大批硬件能力点长期失败。

稳定失败按 CID 分布：

| CID | 场景 | 稳定失败数量 | 主要失败形态 |
|---|---|---:|---|
| cid002 | RTL completion | 55 | 接口/模块名不匹配、位宽参数错误、功能 corner case |
| cid003 | spec to RTL | 36 | 从零写模块时接口契约、协议语义、复杂状态机失败 |
| cid004 | RTL modification | 25 | 修改定位错误、改坏已有接口、延迟/时序不保持 |
| cid007 | lint/QoR improvement | 23 | 功能虽可能过，但 lint/sanity 双约束失败；部分环境/pip 问题需剔除 |
| cid016 | debugging | 18 | 修 bug 不最小、只改表面症状、时序/流水线 bug 未修对 |

稳定失败按机制粗分：

| 失败机制 | 代表问题 |
|---|---|
| syntax | 输出 markdown fence、非法 for-loop、always 块中声明不被工具接受 |
| compile/elaboration | root module 名不匹配、wire/reg/logic 类型错误、未知子模块、参数绑定失败、多驱动 |
| functional/test | 能编译但行为错，常见于协议、状态机、pipeline latency、位宽/overflow、reset |
| lint/QoR | sanity 过但 lint 失败，或改写破坏综合友好性 |
| no-log/env | 没有日志或工具安装失败，这类不完全等同模型能力失败，需要单独标注 |

## 2. 逐条代表 Case 分析

### 2.1 `cvdp_copilot_axi_alu_0001`，cid016，syntax

日志：

```text
/code/rtl/axi_alu.sv:1: warning: macro systemverilog undefined
/code/rtl/axi_alu.sv:1: syntax error
```

生成文件开头是：

```text
```systemverilog
module axi_alu (
```

失败机制：模型把 Markdown 代码块 fence 写进了 RTL 文件。

暴露能力短板：

- 输出格式约束执行失败。
- 没有区分“给人看的答案”和“会被工具直接编译的源文件”。
- Debug 类任务中，模型没有保持最小 patch，而是重新生成一大段代码并污染文件格式。

改进建议：

- 在解码后增加代码清洗，去掉 ```、```systemverilog 等 fence。
- prompt 中明确：“Do not include markdown fences. Output raw file content only.”
- 对 non-agentic codegen 增加 preflight compile；如果第一行含 ```，直接判为格式错误并重试。

### 2.2 `cvdp_copilot_axi_stream_upscale_0001`，cid003，syntax/tool compatibility

日志：

```text
/code/rtl/axis_upscale.sv:40: syntax error
/code/rtl/axis_upscale.sv:40: error: Malformed statement
```

关键代码：

```systemverilog
always_comb begin
    if (dfmt_enable) begin
        logic extend_bit;
        ...
        logic bit_23;
```

失败机制：在过程块中间声明局部变量，Icarus Verilog 对该写法兼容性差，导致编译失败。

暴露能力短板：

- SystemVerilog 写法不够工具兼容。
- 模型知道“语义上该声明临时变量”，但不知道 benchmark 工具链的可接受子集。
- 没有形成“先声明、后语句”的保守 RTL 风格。

改进建议：

- 针对 Icarus/Yosys/Verilator 建立 RTL style guide：过程块局部变量统一放在块开头，或提升到模块级。
- 训练/提示模型避免复杂 SV 语法，优先使用保守 Verilog-2005/SV subset。
- 在 harness 前加 `iverilog -g2012` 快速编译重试。

### 2.3 `cvdp_copilot_8x3_priority_encoder_0001`，cid003，compile/elaboration

日志：

```text
/code/rtl/priority_encoder.v:7: error: 'out' is not a valid l-value for a procedural assignment.
/code/rtl/priority_encoder.v:3:      : 'out' is declared here as a wire.
```

关键代码：

```verilog
module priority_encoder_8x3 (
    input  [7:0] in,
    output [2:0] out
);

always @(*) begin
    if (in[7]) out = 3'b111;
```

失败机制：Verilog 中 `output [2:0] out` 默认是 wire，不能在 `always` 中赋值。

暴露能力短板：

- 基础 Verilog 类型规则不稳定。
- 模型混用了 SystemVerilog `logic` 思维和 Verilog `.v` 文件语义。
- 没有根据文件后缀和 harness 编译模式选择正确声明方式。

改进建议：

- 输出 `.v` 文件时使用 `output reg [2:0] out`，或改成连续赋值。
- 训练集中加入大量 wire/reg/procedural assignment 负例。
- prompt 可要求：“For Verilog `.v`, procedural outputs must be declared `reg`.”

### 2.4 `cvdp_copilot_axis_border_gen_0014`，cid002，root module mismatch

日志：

```text
error: Unable to find the root module "axis_border_gen_with_resize" in the Verilog source.
```

实际生成：

```systemverilog
module axis_image_border_gen_with_resizer #(
```

失败机制：题目要求 root module `axis_border_gen_with_resize`，模型生成了相近但不同的模块名。

暴露能力短板：

- 接口契约不牢靠。
- 模型倾向语义改名，把名字“优化”成自己觉得更自然的形式。
- 对 benchmark 来说，模块名、端口名、参数名是硬约束，不是可改写文本。

改进建议：

- prompt 中把 module name、port list 作为不可修改 contract 单独列出。
- 生成后做静态检查：root module 是否存在，端口是否完全匹配。
- 对模型增加“copy exact signature before implementing body”的约束。

### 2.5 `cvdp_copilot_bcd_adder_0001`，cid002，index/width error

日志：

```text
/code/rtl/bcd_adder.sv:67: error: Index carry[3] is out of range.
```

失败机制：模型在层次化 BCD adder 中错误使用 carry 数组或单 bit carry，访问了不存在的 index。

暴露能力短板：

- 位宽和中间信号尺寸推导不稳定。
- 组合结构化设计中，模型能写出“像 adder 的代码”，但不能保证每一级 carry 链尺寸自洽。
- 对 hierarchical full-adder 结构的 wiring 校验不足。

改进建议：

- 训练模型在生成前写出 internal signal width table。
- 对 adder/multiplier/divider 类任务加入 automatic lint check。
- prompt 中要求所有 intermediate carry vector 宽度显式声明并覆盖每一级。

### 2.6 `cvdp_copilot_16qam_mapper_0001`，cid003，parameterized slicing failure

日志：

```text
/code/rtl/16qam_mapper.sv:27: error: All but the final index in a chain of indices must be a single value, not a range.
/code/rtl/16qam_mapper.sv:28: error: All but the final index in a chain of indices must be a single value, not a range.
```

关键代码：

```systemverilog
mapped_I[i] = map_2bit(bits[i*IN_WIDTH +: IN_WIDTH][IN_WIDTH-1 -: 2]);
mapped_Q[i] = map_2bit(bits[i*IN_WIDTH +: IN_WIDTH][1:0]);
```

失败机制：链式 part-select 先取 range 再对结果取 range，Icarus 不接受。

暴露能力短板：

- 参数化 bit slicing 的工具兼容性差。
- 对 packed vector 的合法切片方式掌握不稳。
- 能理解算法，但表达成可编译 RTL 失败。

改进建议：

- 避免链式切片，改用直接绝对索引，例如 `bits[i*IN_WIDTH + IN_WIDTH-1 -: 2]`。
- 建立“parameterized slicing patterns”训练模板。
- 编译失败重试时把具体 `sim.log` 反馈给模型，通常这类错误可自动修复。

### 2.7 `cvdp_copilot_arithmetic_progression_generator_0003`，cid002，parameter math off-by-one

日志：

```text
DATA_WIDTH= 6, SEQUENCE_LENGTH= 20, WIDTH_OUT_VAL=12
Wrong calculation of WIDTH_OUT_VAL
assert 12 == 11
```

生成逻辑：

```systemverilog
localparam WIDTH_OUT_VAL = DATA_WIDTH + $clog2(SEQUENCE_LENGTH) + 1;
```

失败机制：模型保守多加 1 bit，和 harness/reference 的精确宽度定义不一致。

暴露能力短板：

- 参数数学不能精确对齐题目 oracle。
- 模型倾向“避免 overflow 就多给一位”，但 benchmark 检查的是精确 `WIDTH_OUT_VAL`。
- 对 `$clog2` 和最大值位宽推导缺少严谨性。

改进建议：

- 对参数计算题要求模型先推导最大值公式，再给位宽公式。
- 用 few-shot 展示 `max_value = start + (N-1)*step` 的 bit length，而不是泛化为 `DATA_WIDTH + clog2(N) + 1`。
- harness 若要求精确位宽，prompt 应明确“do not over-provision width”。

### 2.8 `cvdp_copilot_apb_gpio_0001`，cid003，register map/protocol failure

日志摘录：

```text
FAIL: Data Output Register mismatch. Expected: 0xA5, Got: 0x00
FAIL: Output Enable Register mismatch. Expected: 0xFF, Got: 0x00
FAIL: Interrupt State Register mismatch. Expected: 0x55, Got: 0x00
```

失败机制：APB GPIO register writes 没有正确更新内部寄存器，GPIO output enable 和 interrupt state 也未按测试期望工作。

暴露能力短板：

- 总线协议和寄存器映射实现能力弱。
- 模型可能写了端口和框架，但没有完整实现 APB write/read handshake。
- interrupt level/edge/polarity/mask 这种硬件控制逻辑容易漏。

改进建议：

- 训练重点加入 APB/AHB/AXI-lite register block 模板。
- prompt 中把 address map、write enable 条件、read mux、reset value、side effect 单独列表。
- 生成后用 directed tests 先测 register write/read，再测 interrupt 组合逻辑。

### 2.9 `cvdp_copilot_GFCM_0001`，cid003，CDC/glitch-free switching failure

日志：

```text
Glitch detected, clkout is 1
assert Logic('1') == 0
```

失败机制：glitch-free clock mux 在 `sel` 切换时没有保证两个 clock gate 都关闭的安全窗口，导致输出 glitch。

暴露能力短板：

- CDC/时钟切换设计能力不足。
- 模型能写“两个 enable + mux”，但没有掌握异步时钟域之间 enable 同步、break-before-make、负边沿 gating 等关键技术。
- 这类问题不是语法问题，而是硬件设计经验问题。

改进建议：

- 对 CDC/glitch-free clock mux 提供专门模板或 library primitive。
- 训练中加入“错误 mux 会 glitch”的反例和 timing waveform。
- 对 clock/control 类任务，要求模型先描述安全切换状态机，再写 RTL。

### 2.10 `cvdp_copilot_gcd_0023`，cid004，modification breaks internal names

日志：

```text
/code/rtl/gcd_top.sv:189: error: Unable to bind wire/reg/memory `A' in `gcd_top.gcd_controlpath_inst'
/code/rtl/gcd_top.sv:210: error: Unable to bind wire/reg/memory `A_ff' in `gcd_top.gcd_controlpath_inst'
```

失败机制：修改已有 GCD 设计时，control path 引用了不存在或已被改名的 datapath 信号。

暴露能力短板：

- Code modification 不是从零生成；必须保持原模块内部接口一致。
- 模型改动过大，破坏 control/datapath 耦合关系。
- 对已有代码的名称依赖、层次引用、模块实例关系理解不足。

改进建议：

- 修改类任务提示模型“preserve all existing module boundaries and internal signal names unless required”。
- 训练 agentic/patch-style 修改，而不是整文件重写。
- 对 modification 任务先做 symbol table，再限制可改区域。

### 2.11 `cvdp_copilot_64b66b_encoder_0009`，cid004，protocol modification failure

日志特征：

```text
Expected: 0
```

生成代码中 control character encoding 存在明显宽度/语义问题，例如函数返回 `logic [6:0]`，但部分 case 赋 `4'b0000`。

失败机制：模型尝试扩展 64b/66b control encoding，但 type field、control character、sync word 规则没有完整对齐协议。

暴露能力短板：

- 协议编码类修改能力弱。
- 对 64b/66b 这样的标准编码，模型容易写近似逻辑而非精确规则。
- 修改任务中没有保持原有 data-only 行为和新增 control 行为的兼容。

改进建议：

- 对协议类任务提供 explicit truth table。
- 生成前要求列出每种 control pattern 的 expected output。
- 对 modification 任务跑 regression，确保旧功能不退化。

### 2.12 `cvdp_copilot_Carry_Lookahead_Adder_0005`，cid016，pipeline debug failure

日志：

```text
Cycle 4: Expected sum 1268269782, got 1268307522
```

失败机制：pipelined 32-bit adder 的 stage 对齐或 carry propagation 修复错误，导致指定 latency 下 sum 不匹配。

暴露能力短板：

- Debug 时没有准确定位 pipeline 寄存器和 carry chain 的错位。
- 可能只修了局部表达式，没有验证跨 stage 数据/控制同步。
- 对 latency contract 不敏感。

改进建议：

- Debug 类 prompt 中要求模型先定位 bug root cause，再输出最小 patch。
- 训练流水线问题：data path、valid/done、carry、latency 必须一起对齐。
- 使用 waveform-like trace 或 cycle table 作为反馈给模型重试。

### 2.13 `cvdp_copilot_hamming_code_tx_and_rx_0011`，cid004，loop syntax failure

日志：

```text
/code/rtl/hamming_rx.sv:43: syntax error
/code/rtl/hamming_rx.sv:43: error: Incomprehensible for loop.
```

失败机制：修改 Hamming decoder 时生成了非法 for-loop。

暴露能力短板：

- 参数化循环语法不稳。
- ECC/编码类任务中，模型常混合 algorithmic pseudo-code 和 synthesizable RTL。

改进建议：

- 要求所有 generate-for 使用 `genvar`，过程 for 使用 `int` 且放在合法 block 中。
- 对 ECC 类任务用固定 syndrome table 比动态复杂循环更稳。

### 2.14 `cvdp_copilot_IIR_filter_0019`，cid007，lint/QoR failure

sanity report 显示功能测试通过：

```text
TESTS=3 PASS=3 FAIL=0
```

但 lint report 失败：

```text
../../src/lint.py::test_lint FAILED
```

失败机制：cid007 不只是功能正确，还要求代码质量、lint、综合友好性。模型生成的 IIR filter 行为可通过 directed/random 测试，但不满足 lint 规则。

暴露能力短板：

- 模型优化目标偏功能，不懂 lint/QoR 约束。
- 可能存在 latch、未用信号、阻塞/非阻塞混用、宽度截断、组合环、不可综合写法等。

改进建议：

- cid007 prompt 中明确 lint rule priority。
- 引入 lint feedback 重试：功能通过但 lint fail 时只做结构性 cleanup。
- 训练模型区分 functional equivalence 和 implementation quality。

## 3. 模型能力短板归纳

### 3.1 输出契约不稳定

表现：markdown fence、模块名不匹配、端口名不匹配、root module 不存在。

影响：这类错误无需进入功能测试，直接编译失败。

改进：输出 raw RTL、签名锁定、静态 module/port checker、失败重试。

### 3.2 Verilog/SystemVerilog 工具链子集掌握不足

表现：wire procedural assignment、过程块中间声明、链式 part-select、非法 generate/for、多驱动。

影响：模型“看起来会写 SV”，但不一定能被 Icarus/Yosys/Verilator 接受。

改进：保守 RTL style guide，工具链定向微调，compile feedback loop。

### 3.3 参数化位宽和 `$clog2` 推导弱

表现：carry index 越界、WIDTH_OUT_VAL 多/少 1、part-select 越界、indefinite width。

影响：参数化 case 失败率高，尤其 DATA_WIDTH、SEQUENCE_LENGTH、latency 可变时。

改进：让模型显式输出 width table；训练最大值/位宽推导；用 lint 检查越界。

### 3.4 协议和寄存器行为不完整

表现：APB GPIO 写寄存器无效、interrupt/mask/polarity 漏实现、AXI-stream ready/valid 不正确。

影响：能生成外形，但状态机和 side effect 不完整。

改进：提供 address map/checklist；按 feature 分阶段生成；对总线协议加入模板库。

### 3.5 时序、CDC、pipeline latency 能力不足

表现：glitch-free mux 有 glitch、pipelined adder cycle mismatch、GCD latency mismatch、valid/done 对齐错误。

影响：这是真硬件能力短板，靠语法修复不能解决。

改进：训练 cycle-accurate reasoning；要求生成 latency table；引入 waveform/cycle trace 反馈。

### 3.6 修改和 debug 容易重写过度

表现：修改类 case 改坏内部信号名、接口、已有功能；debug 修 bug 不最小。

影响：cid004/cid016 失败反映模型不像工程师 patch，而像重新答题。

改进：使用 diff/patch 模式；限制改动范围；先 root-cause 后 patch；回归旧功能。

### 3.7 Lint/QoR 目标没有内化

表现：sanity pass 但 lint fail。

影响：模型能写“可跑”的 RTL，但不是高质量工程 RTL。

改进：lint rule-aware prompt，lint feedback retry，训练合成友好风格。

## 4. 改进优先级

### P0：先消灭非能力型低级失败

- 去 markdown fence。
- 检查 root module name。
- 检查端口列表。
- 运行 `iverilog -g2012` 预编译。
- 编译错误自动反馈重试一次。

这一步预期能回收大量 syntax/compile 类失败。

### P1：加入工具反馈闭环

非 agentic 单轮模型最大问题是没有看到编译/仿真反馈。建议改成：

```text
generate -> compile -> if compile fail, feed sim.log back -> regenerate
```

对 syntax、wire/reg、module mismatch、part-select 这类错误，一轮反馈通常很有效。

### P2：针对硬件弱项做专项训练/提示

- APB/AHB/AXI-lite register file。
- ready/valid streaming。
- parameterized width math。
- pipeline latency alignment。
- CDC/glitch-free clock mux。
- ECC/encoder/decoder syndrome logic。

### P3：对 modification/debug 使用 patch-first 策略

cid004/cid016 不应让模型自由重写整文件。更好的流程是：

```text
read original -> identify bug/required change -> list affected signals -> emit minimal patch -> run regression
```

### P4：把 cid007 拆成功能和质量两阶段

对 lint/QoR improvement：

```text
sanity functional pass -> lint pass -> optional QoR compare
```

模型改进时也应按这个顺序，不要为了 lint 改坏功能。

## 5. 下一步建议

如果要继续深入，建议按下面顺序逐条追：

1. 先处理 syntax/compile 类稳定失败，因为它们最容易通过工程 wrapper 回收。
2. 再分析 cid003/cid004 的功能失败，尤其 APB、AXI-stream、GCD、matrix、divider。
3. 最后分析 cid016 debug，因为需要对比原始 bug 和模型 patch，耗时最大但最能暴露工程能力。
4. cid007 中出现 `pip<26.1` 安装失败的 case 先标记为环境/工具问题，不要直接归因模型。

## 6. 改进方式：Prompt、约束、工具闭环还是 Finetune

这些失败不能用单一手段解决。正确策略是分层：先用工程 wrapper 和约束消灭低级失败，再用任务模板和工具反馈改善中等难度问题；只有当加入 agentic feedback loop 后仍稳定失败，才有较强证据说明需要 finetune 或 tool-use 训练来提升模型本身能力。

需要特别说明：`5/5 samples 全失败` 不是“必须 finetune”的充分证据。它只说明当前组合：

```text
当前模型 + 当前 prompt + 当前 non-agentic 单轮流程
```

没有解决该题。它可能是模型能力问题，也可能是输出格式、接口约束、没有 compile retry、没有 simulation feedback、没有 restart 或环境问题。因此，是否需要训练必须通过 ablation 判断，而不是只看 pass5 失败。

### 6.1 失败类型与推荐手段

| 失败类型 | 代表现象 | 推荐优先手段 | 是否需要 finetune |
|---|---|---|---|
| 输出格式错误 | ` ```systemverilog` 被写进 RTL 文件 | 输出清洗 + prompt 约束 | 不需要 |
| module/port 不匹配 | root module 找不到、端口名错误 | 静态签名检查 + retry | 通常不需要 |
| 基础语法/类型错误 | `wire` 在 `always` 中赋值、非法 for-loop | compile check + error feedback retry | 不一定 |
| 工具兼容问题 | Icarus 不接受链式 part-select、过程块中间声明 | 保守 RTL style prompt + compile retry | 不一定 |
| 参数位宽错误 | `$clog2` off-by-one、carry index 越界 | 位宽推导模板 + few-shot | 中等需要 |
| 协议/寄存器行为不完整 | APB GPIO register write/read、interrupt 失败 | 协议 checklist + directed feedback | 先做 agentic loop；残余失败再训练 |
| ready/valid / streaming 错误 | AXI-stream backpressure、latency 错 | 协议模板 + waveform/cycle trace | 先做 feedback loop；残余失败再训练 |
| CDC / clock mux 错误 | glitch-free mux 仍有 glitch | Reflector + CDC 模板 + restart | 如果 agentic loop 后仍不稳，再考虑训练 |
| pipeline/debug 错误 | cycle 4 expected/got mismatch | cycle table + patch-first workflow | 如果多轮 feedback 仍不稳，再考虑训练 |
| modification 改坏旧代码 | 内部信号名被改、旧行为退化 | diff/patch 约束 + regression | finetune 很有帮助，但不是第一步 |
| lint/QoR 失败 | sanity pass 但 lint fail | lint rule prompt + lint feedback | 可用 finetune 增强 |

### 6.2 短期：优先做 Prompt、约束和后处理

短期不要先 finetune。当前结果里大量失败属于“非硬件智能”问题，例如 markdown fence、module 名不匹配、端口不匹配、编译语法错误。这类问题用工程约束的收益最高。

推荐先加以下约束：

```text
Output raw RTL only. Do not include markdown fences.
Keep the exact module name and port list from the prompt.
Do not rename ports, parameters, or existing internal signals unless explicitly required.
Use conservative synthesizable SystemVerilog compatible with Icarus Verilog.
Declare procedural outputs as logic/reg.
Avoid declaring variables in the middle of procedural blocks.
Avoid chained part-selects; use direct indexed part-selects instead.
```

对 modification/debug 类任务，再加：

```text
Do not rewrite the whole module unless necessary.
Preserve existing behavior not related to the requested change.
First identify the minimal affected logic, then patch only that logic.
Keep latency, reset behavior, and valid/done timing unchanged unless requested.
```

这些 prompt 约束主要针对：

- `cvdp_copilot_axi_alu_0001` 的 markdown fence。
- `cvdp_copilot_axis_border_gen_0014` 的 root module mismatch。
- `cvdp_copilot_8x3_priority_encoder_0001` 的 `wire` procedural assignment。
- `cvdp_copilot_axi_stream_upscale_0001` 的过程块中间声明。
- `cvdp_copilot_16qam_mapper_0001` 的链式 part-select。

### 6.3 短期：必须加静态检查和 Compile Retry

比单纯加 prompt 更有效的是工具闭环。推荐流程：

```text
LLM generate
  -> postprocess 清洗 markdown/json 包裹
  -> signature checker 检查 module name/port/parameter
  -> iverilog/yosys compile
  -> 如果 compile fail，把 sim.log 反馈给模型 retry
  -> compile pass 后运行完整 harness
```

这类闭环对 syntax/compile 类失败最有效，因为错误信息非常明确。比如：

```text
'out' is not a valid l-value for a procedural assignment
```

模型看到这类错误后，通常能把 `output [2:0] out` 改成 `output reg [2:0] out`，或改为连续赋值。

再比如：

```text
Unable to find the root module "axis_border_gen_with_resize"
```

这可以通过静态 checker 直接发现，不需要等完整仿真。

预期收益：

| 失败类别 | 是否容易通过 wrapper 回收 |
|---|---|
| markdown fence | 很容易 |
| module/port mismatch | 很容易 |
| wire/reg procedural assignment | 很容易 |
| syntax error | 中高 |
| chained part-select | 中高 |
| unknown submodule | 中等，取决于是否需要补模块 |
| functional protocol bug | 低，通常需要更深能力 |

### 6.4 中期：加入任务类型模板

中期目标不是泛化地告诉模型“写正确 RTL”，而是对每类硬件任务给 checklist。

APB/AHB/AXI-lite register block 模板应强制模型覆盖：

```text
address decode
write enable condition
read mux
reset value
byte strobe if any
side-effect registers
interrupt status/set/clear/mask
ready/valid or psel/penable/pwrite timing
```

Ready/valid streaming 模板应覆盖：

```text
s_axis_ready behavior
m_axis_valid hold rule
data stability while valid && !ready
tlast/tuser alignment
backpressure
internal skid/pipeline state
```

参数位宽模板应要求模型先列：

```text
max input value
max intermediate value
required output range
exact bit width
whether over-provisioning is allowed
```

Pipeline/debug 模板应要求模型列 cycle table：

```text
cycle 0: input accepted
cycle 1: stage 1 output
cycle 2: stage 2 output
cycle N: valid/done/result observable
```

CDC/glitch-free clock mux 模板应覆盖：

```text
break-before-make
per-clock-domain enable synchronization
safe disable before enable
no combinational clock mux without gating discipline
reset behavior of clock enables
```

### 6.5 如何判断是否真的需要 Finetune

Finetune 应该用于真正硬件能力问题，而不是先拿来修 markdown fence、module name mismatch 或 wire/reg 这类工具可诊断错误。

严格来说，判断是否需要 finetune 应该做 ablation，而不是凭直觉。

推荐 ablation 阶梯：

| 阶段 | 加入能力 | 如果 case 通过，说明什么 |
|---|---|---|
| A0 | 当前单轮 prompt | baseline |
| A1 | output cleaner + raw RTL 约束 | 原问题主要是格式污染 |
| A2 | module/port/parameter signature checker | 原问题主要是接口契约不稳 |
| A3 | `iverilog` compile retry 1-3 次 | 原问题主要是语法/类型/工具兼容 |
| A4 | harness failure feedback retry | 模型能根据 expected/actual 修复，不一定需要训练 |
| A5 | Reflector + Coordinator + history | 需要 agentic context evolution，但不一定需要训练 |
| A6 | restart + parallel trajectories | 需要搜索和重启机制，仍不一定需要训练 |
| A7 | A1-A6 后仍稳定失败 | 才是需要 finetune/专项训练的强证据 |

因此，`pass5 都失败` 的正确解读是：

```text
当前 non-agentic 单轮流程无法解决。
下一步应该先试约束、checker、compile retry 和 agentic feedback。
只有这些仍失败，才把它归为训练需求。
```

最值得 finetune 的方向：

| 能力 | 为什么 prompt 不够 |
|---|---|
| 协议实现 | 如果 feedback loop 后仍无法实现 APB/AXI/register side effect，说明缺少模式内化 |
| 时序和 pipeline | 如果 cycle trace 反馈后仍反复错，说明 cycle-level reasoning 不稳 |
| CDC/glitch-free | 如果 restart 和 guidance 后仍 glitch，说明缺少硬件设计经验和反例训练 |
| Debug 最小修复 | 如果模型持续整文件重写或引入回归，说明需要 patch-style 数据训练 |
| Lint/QoR cleanup | 如果 lint feedback 后仍无法在不破坏功能的情况下 cleanup，说明需要 lint/QoR 数据 |

推荐 finetune 数据格式不要只做：

```text
prompt -> final RTL
```

更应该做：

```text
problem prompt + original RTL + failing log -> root cause + minimal patch
```

或者：

```text
generated RTL + compile error -> corrected RTL
```

再或者：

```text
generated RTL + cocotb failure trace -> corrected RTL
```

这样训练出来的模型才会更像硬件工程师，而不是只会一次性写代码。

### 6.6 推荐落地路线

按投入产出比，推荐分三阶段。

阶段 1：工程约束，不训练。

```text
postprocess 清洗
module/port checker
iverilog compile checker
compile fail retry
conservative RTL prompt
```

目标：显著降低 syntax/compile 类失败。

阶段 2：任务模板和 feedback retry。

```text
APB/AXI checklist
ready/valid checklist
parameter width derivation
pipeline cycle table
lint feedback retry
```

目标：提升协议、参数化、lint/QoR 类 case。

阶段 3：finetune 或 tool-use/RL 训练。

```text
compile-error repair data
harness-failure repair data
minimal patch debug data
protocol implementation data
CDC/pipeline waveform reasoning data
```

目标：提升 cid003/cid004/cid016 这类深层硬件能力。

### 6.7 总结判断

一句话：

```text
低级格式/编译问题靠 prompt + 约束 + checker；
工具可诊断问题靠 compile/harness feedback retry；
协议、CDC、pipeline、debug、QoR 这类硬件能力问题至少需要 agentic feedback loop；
若 feedback loop 后仍稳定失败，才需要专项训练或 finetune。
```

如果目标是快速提高 benchmark 分数，先做 wrapper 和 retry。如果目标是提升模型本身的硬件工程能力，再做 finetune。

## 7. 对照 Agentrys Blog 和 ACE-RTL 论文的高成功率方法

本节基于两类公开资料：

- Agentrys blog: `Self-improving Agent Solving CVDP RTL Coding Tasks`, `https://agentrys.ai/blog-cvdp.html`。
- ACE-RTL paper: `ACE-RTL: When Agentic Context Evolution Meets RTL-Specialized LLMs`, arXiv `2602.10218`。

需要先区分两者的信息粒度：Agentrys blog 给出了较高层的系统演进和结果，但没有公开完整 prompt、代码和实现细节；ACE-RTL 论文公开了更具体的方法，包括 RTL-specialized Generator、Reflector、Coordinator、restart、parallel scaling 和训练数据构造。因此，本节把 blog 当作高层结果参考，把 ACE-RTL 论文作为主要技术机制参考。

### 7.1 Agentrys Blog 的结果与方法摘要

Agentrys blog 报告 Gen 6 agent 在 CVDP RTL coding tasks 上达到：

| Task | Agentrys Gen 6 | ACE-RTL SOTA | Claude Opus 4.5 baseline |
|---|---:|---:|---:|
| Overall | `95.8%` | `88.9%` | `50.1%` |
| Code Completion | `96.8%` | `80.8%` | `42.4%` |
| Spec-to-RTL | `96.2%` | `96.2%` | `54.3%` |
| Code Modification | `90.9%` | `90.9%` | `52.1%` |
| Code Debug | `100.0%` | `91.4%` | `57.3%` |

blog 强调性能提升来自 agent architecture evolution：

| Generation | 结构 | 关键机制 |
|---|---|---|
| Gen 0 | Single-Agent | 一个 agent 完成读 spec、写 RTL、仿真、debug loop |
| Gen 1 | Multi-Agent System | orchestrator 协调 3 个 RTL designers 和 1 个 reviewer |
| Gen 2 | Hierarchical Agent Network | 3 个 solver team 并行竞争和 debate，aggregator 汇总，adversarial verifier 压测，simulation specialist 验证 |

blog 给出的核心结论是：高成功率来自 self-improving agent system，而不是单次模型调用。尤其是 Code Debug 达到 `100.0%`，说明多轮 simulation feedback 和 agentic iteration 对 debug 类任务有显著价值。

但 blog 没有公开以下细节：

- 每个 agent 的具体 prompt。
- 每轮仿真反馈如何结构化。
- aggregator 的打分或选择规则。
- adversarial verifier 的具体检查策略。
- 是否 finetune 了底层模型，或使用何种训练数据。

因此，不能仅凭 blog 复现它的 `95.8%`，但可以确认方向：多 agent、多 trajectory、仿真反馈、review/verification、self-improvement 是高成功率的关键。

### 7.2 ACE-RTL 的关键机制

ACE-RTL 论文给出了更具体的实现框架。它不是简单 prompt engineering，而是把 RTL-specialized model 和 frontier reasoning LLM 组合进 iterative agentic loop。

核心结构：

```text
Generator -> compile/simulate -> Reflector -> Coordinator -> updated context -> Generator
```

主要组件如下。

| 组件 | 作用 | 对应我们失败分析中的问题 |
|---|---|---|
| Generator | RTL-specialized LLM，生成或修复 RTL | 弥补通用模型硬件知识不足 |
| Reflector | frontier reasoning LLM，分析 simulation feedback 和 failure log | 把 raw log 转成 root cause 和 high-level fix guidance |
| Coordinator | 维护 evolving context，记录历史尝试、修复建议和结果 | 避免模型反复修同一个错误，保留有用进展 |
| Restart | 发现 trajectory 停滞后，带着历史经验重新生成 | 避免局部 patch 越修越坏 |
| Parallel Scaling | 并行跑多个 ACE-RTL process，任一通过即停止 | 提高 time-to-first-success 和覆盖率 |

ACE-RTL paper 中的重要细节：

- Generator 是 RTL-specialized model。
- 训练数据规模约 `1.7M` RTL samples。
- 训练样本覆盖 spec-to-RTL、editing、debugging，不只是从规格生成代码。
- Generator finetuned from `Qwen2.5-Coder-32B-Instruct`。
- 训练 context window 为 `32768` tokens。
- Reflector 使用 frontier reasoning LLM 分析 failure。
- 每轮用 `iverilog` 编译/运行 candidate RTL against benchmark harness。
- failure log 被解析成 structured report，包括 error message 和 expected-vs-actual signal behavior。
- Coordinator 保存 debugging history，并在停滞时触发 restart。
- inference 使用 5 个 parallel processes，每个最多 30 iterations，temperature `1.2`。

这些细节说明，高成功率来自系统级闭环：

```text
RTL finetune + simulator feedback + structured reflection + evolving context + restart + parallel search
```

不是来自：

```text
更长 prompt 或更详细 instruction
```

### 7.3 ACE-RTL 结果如何解释

ACE-RTL paper 在 CVDP v1.0.2 的四类 coding tasks 上报告 Pass@1 和 Agentic Pass Rate APR。

| CID | Task | ACE-RTL APR | 解释 |
|---|---|---:|---|
| cid002 | Code Completion | `80.85%` | 低于 Agentrys Gen 6 的 `96.8%`，但远高于 standalone baselines |
| cid003 | Spec-to-RTL | `96.15%` | 接近 Agentrys Gen 6 的 `96.2%` |
| cid004 | Code Modification | `90.91%` | 和 Agentrys Gen 6 / blog 中 SOTA 持平 |
| cid016 | Code Debugging | `91.43%` | 高于多数 baseline，但低于 Agentrys Gen 6 的 `100.0%` |

ACE-RTL 还报告 standalone Generator 已明显强于普通模型，尤其 code modification：

```text
Generator standalone cid004 Pass@1 = 65.09%
GPT-5 cid004 Pass@1 = 43.64%
```

这说明 finetune 的作用很大，尤其对 editing/modification 任务。agentic loop 则进一步把 standalone generator 的能力推到更高 APR。

### 7.4 ACE-RTL 的 Ablation 对我们的启示

论文 ablation 的核心结论是：

1. 只用 standalone Generator 不够。
2. 加 simulation-guided iterative refinement 会提升。
3. Coordinator 带来的 evolving context 是最大增益来源之一。
4. Restart 能进一步帮助系统跳出停滞 trajectory。
5. Parallel scaling 能降低达到正确解的 wall-clock iterations。

这直接修正了我们原始方案中“compile feedback retry”的表述。

我们原方案说：

```text
generate -> compile -> if fail, feed sim.log back -> regenerate
```

这只是 ACE-RTL 的弱化版本。论文里的完整机制应是：

```text
generate candidate RTL
  -> compile/simulate with harness
  -> parse failure into structured report
  -> Reflector diagnoses root cause and fix direction
  -> Coordinator updates evolving context with history and outcome
  -> Generator patches or regenerates under updated context
  -> Coordinator detects stagnation
  -> restart if needed
  -> run multiple trajectories in parallel
```

差别在于：

| 简单 retry | ACE-style context evolution |
|---|---|
| 只看当前错误 | 看全部历史尝试和进展 |
| 容易反复修同一个错误 | 记录已失败策略，避免重复 |
| 不知道何时放弃当前实现 | 有 stagnation detection 和 restart |
| 单 trajectory | 多 trajectory parallel scaling |
| raw log 直接喂模型 | Reflector 提炼 root cause 和 high-level guidance |

因此，我们当前报告中的工程化方案合理，但还不足以解释或达到 ACE/Agentrys 的高成功率。

### 7.5 对我们失败 Case 的重新映射

把前文失败 case 映射到 ACE/Agentrys 方法，可以看出哪些用 wrapper 就够，哪些至少需要 agentic feedback loop。注意：这里的“需要 agentic/finetune”不是说 pass5 失败就必须训练，而是说单轮 prompt 不足以可靠解决；是否需要训练还要看加入 feedback loop 后是否仍失败。

| 失败 case | 当前失败 | wrapper/prompt 是否足够 | ACE-style 需要什么 |
|---|---|---|---|
| `cvdp_copilot_axi_alu_0001` | markdown fence 进 RTL | 足够 | postprocess 即可，不需要深 agent |
| `cvdp_copilot_axis_border_gen_0014` | root module mismatch | 基本足够 | signature checker + regenerate |
| `cvdp_copilot_8x3_priority_encoder_0001` | `wire` procedural assignment | 基本足够 | compile log feedback |
| `cvdp_copilot_axi_stream_upscale_0001` | Icarus syntax/tool compatibility | 基本足够 | style constraint + compile retry |
| `cvdp_copilot_16qam_mapper_0001` | chained part-select | 基本足够 | compile log feedback |
| `cvdp_copilot_arithmetic_progression_generator_0003` | WIDTH_OUT_VAL off-by-one | prompt 不一定够 | Reflector 分析 expected-vs-actual，Generator 修 formula |
| `cvdp_copilot_apb_gpio_0001` | APB register/interrupt 行为缺失 | 不够 | 先用 directed simulation feedback；若仍不稳，再用协议数据训练 |
| `cvdp_copilot_GFCM_0001` | glitch-free mux CDC 语义错误 | 不够 | Reflector 识别 clock-switching root cause，可能需要 restart |
| `cvdp_copilot_gcd_0023` | modification 改坏 internal names | 不够 | 先用 patch-first workflow + Coordinator；若仍重写过度，再用 editing 数据训练 |
| `cvdp_copilot_Carry_Lookahead_Adder_0005` | pipeline latency/carry 对齐错误 | 不够 | cycle trace diagnosis + iterative patch |
| `cvdp_copilot_IIR_filter_0019` | sanity pass 但 lint fail | 部分够 | lint feedback loop + QoR/lint-specific repair data |

这个映射说明：我们原方案中 P0/P1 对 compile 类错误合理，但对功能性硬件能力错误，至少要引入 ACE-style loop。只有当 ACE-style loop 加入后仍稳定失败，才有充分理由把它归因到模型内化能力不足，并进一步考虑 finetuned Generator。

### 7.6 对我们方案合理性的最终评价

原方案合理的部分：

| 我们方案 | 为什么合理 | 论文/blog 支撑 |
|---|---|---|
| 输出清洗 | 低成本解决格式污染 | 属于 agent pipeline 的 hygiene 层 |
| module/port checker | 直接消灭 root module/接口错误 | 与 compile-before-sim 一致 |
| compile feedback retry | iverilog 反馈是 ACE-RTL 每轮基础 | ACE-RTL 每轮调用 iverilog |
| task-specific checklist | 对 APB/AXI/pipeline 有帮助 | 与 Reflector high-level guidance 类似 |
| finetune editing/debugging 数据 | 用于降低深层任务的迭代次数、提高少轮成功率 | ACE-RTL 1.7M 数据覆盖 editing/debugging |
| parallel attempts | 提升覆盖率和收敛速度 | ACE-RTL parallel scaling、Agentrys 多 solver team |

原方案不足的部分：

| 不足 | 为什么重要 | 应如何补强 |
|---|---|---|
| feedback retry 太简单 | raw log 直接给模型容易反复失败 | 加 Reflector，把 log 转成 root cause 和 fix guidance |
| 没有 evolving context | 模型不知道之前试过什么 | 加 Coordinator 保存 history、fixes、outcomes |
| 没有 stagnation detection | 会在坏 trajectory 上无限局部修补 | 连续 N 次同类失败触发 restart |
| 没有 parallel scaling | 单 trajectory 容易被初始生成质量限制 | 3 到 5 条 trajectory 并行，任一通过即停止 |
| 没有专门 RTL Generator | 通用模型在深层硬件任务上可能需要更多迭代 | 若 agentic loop 后仍不稳，再用 RTL spec/edit/debug 数据 finetune |
| 没有 adversarial verifier | 可能选择看似正确但脆弱的解 | 增加 reviewer/verifier 检查协议、reset、latency、corner case |

因此，最终判断是：

```text
我们的方案作为 baseline engineering improvement 是合理的；
但若目标是 ACE-RTL / Agentrys 级别高成功率，需要升级为 agentic context evolution system；
是否进一步 finetune，应由 feedback-loop ablation 后的残余失败决定。
```

### 7.7 修订后的推荐落地架构

结合 Agentrys blog 和 ACE-RTL paper，推荐目标架构如下。

```text
Input CVDP problem
  -> Prompt normalizer
  -> RTL Generator
  -> Output cleaner
  -> Signature checker
  -> Compile checker with iverilog/yosys
  -> Harness simulation
  -> Failure parser
  -> Reflector: diagnose root cause and fix direction
  -> Coordinator: update evolving context
  -> Stagnation detector
  -> Restart or patch/regenerate
  -> Parallel trajectory manager
  -> First passing solution wins
```

各模块职责：

| 模块 | 职责 |
|---|---|
| Prompt normalizer | 抽取 module name、port list、task type、hard constraints |
| RTL Generator | 生成初始 RTL 或根据 context 修复 RTL |
| Output cleaner | 删除 markdown fence、JSON wrapper、无关解释 |
| Signature checker | 检查 root module、端口、参数、文件路径 |
| Compile checker | 快速发现语法/类型/elaboration 错误 |
| Harness simulation | 运行完整 functional tests |
| Failure parser | 提取 error、expected/actual、first failing test、信号名 |
| Reflector | 解释失败根因，给出 high-level fix guidance |
| Coordinator | 保存每轮尝试、修复、结果、失败模式 |
| Stagnation detector | 判断是否连续多轮无改善 |
| Restart manager | 在停滞时丢弃当前实现并重新生成 |
| Parallel manager | 并行探索多个 stochastic trajectory |

### 7.8 实施优先级：从当前系统到 ACE-style

如果从当前 `run_samples.py` / `run_benchmark.py` 体系逐步改，建议分四步。

第一步：Hygiene + compile gate。

```text
postprocess raw RTL
module/port signature check
iverilog compile precheck
compile error retry 1-2 次
```

目标：先回收 syntax、module mismatch、wire/reg 等低级失败。

第二步：结构化 failure parser。

```text
extract first failing test
extract sim.log error
extract expected vs actual
classify failure type: syntax/compile/protocol/latency/reset/lint
```

目标：让后续 Reflector 不吃完整噪声 log，而是吃干净、可诊断的信息。

第三步：Reflector + Coordinator。

```text
Reflector: root cause + fix guidance
Coordinator: append history, remove redundant info, track progress
```

目标：从简单 retry 升级为 context evolution。

第四步：restart + parallel scaling。

```text
if same failure repeats N rounds -> restart
run K trajectories with different seeds/prompts/temperatures
stop when any trajectory passes
```

目标：提升 APR 和 time-to-first-success。

### 7.9 对 finetune 的准确定位

ACE-RTL 的 Generator finetune 对论文结果非常关键，但这不意味着当前所有 pass5 失败都必须先训练。训练不是第一步工程动作，应该在 feedback loop 和失败轨迹收集之后进行。

更合理的顺序是：

1. 先实现 compile/sim feedback loop。
2. 用这个 loop 产生大量失败轨迹。
3. 从失败轨迹构造训练数据。
4. 分析加入 feedback loop 后仍稳定失败的残余 case。
5. 再针对这些残余 case finetune Generator。

推荐训练样本格式：

```text
spec + current RTL + compile error -> corrected RTL
```

```text
spec + current RTL + failing test + expected/actual -> root cause + corrected RTL
```

```text
original RTL + requested modification + failed regression -> minimal patch
```

```text
buggy RTL + diagnostic failure -> minimal bug fix
```

这与 ACE-RTL 的 training data construction 一致：它不只训练 spec-to-RTL，还训练 editing 和 debugging。原因是 agentic loop 中后续迭代本质上不是“从零写代码”，而是“读失败上下文后修代码”。

### 7.10 最终结论

基于 Agentrys blog 和 ACE-RTL paper，对我们报告中的改进方案应做如下修正：

```text
Prompt/约束/后处理是必要的 hygiene layer，但不是高成功率核心。
Compile/sim feedback retry 是必要基础，但 raw retry 不够。
高成功率核心是 agentic context evolution：Reflector + Coordinator + restart + parallel scaling。
深层硬件能力若在完整 feedback loop 后仍不稳定，再需要 RTL-specialized Generator；训练数据应覆盖 spec、editing、debugging。
```

因此，如果目标只是提升当前 `vllm-glm` 在 `work_codegen_v110` 上的分数，先做 wrapper 和 compile retry 是最经济的。如果目标是达到 ACE-RTL/Agentrys 的 `90%+` 水平，需要构建完整 agentic refinement system；是否 finetune 以及训练哪些能力，应基于该系统运行后的残余失败分布来决定。

## 8. Two-Stage Thinking Codegen Research Plan

本研究项目的独立实验计划和产出目录位于：

```text
research_outputs/two_stage_thinking_codegen/
```

该目录将本报告中的策略进一步拆成可复现实验：

- 第一轮 codegen 默认使用 non-thinking，追求稳定、低 timeout、低格式污染。
- 第二轮只对失败或低置信 case 使用 thinking，测量 targeted rescue value。
- thinking 失败必须先诊断 timeout、`max_tokens`、empty final content、parser/sanitizer、harness failure，不能直接归因模型能力。
- 长 thinking sweep 成本高，放在短预算 failed-subset retry 之后，只对代表 case 运行。
- 是否 finetune 由 feedback-loop ablation 后的残余稳定失败决定，而不是由 pass5 失败直接决定。

核心文档：

| 文档 | 作用 |
|---|---|
| `README.md` | 研究目标和目录总览 |
| `experiment_plan.md` | 阶段化实验路线和 finetune 决策逻辑 |
| `two_stage_thinking_evaluation_plan.md` | non-thinking first pass + thinking retry 主策略 |
| `thinking_failure_diagnosis.md` | timeout/max_tokens/empty content/parser/harness failure 分类 |
| `ablation_matrix.md` | A/B/C/T 消融矩阵 |
| `metrics_and_reporting.md` | 指标定义和论文表格建议 |
| `dataset_subsets.md` | smoke/failed/rescued/residual/finetune candidate subset 定义 |
| `runbook.md` | 实验环境变量和执行命令 |
| `result_schema.md` | JSON/CSV 记录格式 |

两阶段策略的关键判断指标：

```text
thinking_rescue_rate = rescued_by_thinking / nonthinking_failed
final_two_stage_rate = (nonthinking_passed + rescued_by_thinking) / total
```

timeout 估算采用：

```text
timeout ~= max_tokens / 30 tokens_per_second_per_request * margin
margin = 1.3~1.5
```

示例：`max_tokens=12000` 时，理论生成时间约 `400s`，建议 timeout 约 `520s~600s`。`max_tokens=32384` 时，建议 timeout 约 `1403s~1619s`，因此长 thinking 不应作为第一批全量实验。
