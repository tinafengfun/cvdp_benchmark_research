# Runbook

This runbook describes the intended experiment order. Do not run live vLLM experiments until the service is explicitly started and confirmed.

## Environment Defaults

First-pass codegen defaults:

```bash
export CUSTOM_MODEL_FACTORY=/mnt/disk9/tianfeng/cvdp/cvdp_benchmark/kimi_vllm_factory.py
export VLLM_BASE_URL=http://127.0.0.1:30009/v1
export VLLM_THINKING_POLICY=auto
export VLLM_CODEGEN_ENABLE_THINKING=false
export VLLM_COMPREHENSION_ENABLE_THINKING=true
export VLLM_PROMPT_PROFILE=strict_codegen
export VLLM_SANITIZE_OUTPUT=true
export VLLM_CHECK_MODULE_NAME=true
export VLLM_AUTO_TIMEOUT=true
export VLLM_THROUGHPUT_TOKENS_PER_SEC=30
export VLLM_TIMEOUT_MARGIN=1.5
export VLLM_MAX_TOKENS_CODEGEN_NONTHINKING=8192
export VLLM_MAX_TOKENS_CODEGEN_THINKING=12000
```

## Offline Validation

Run before any live vLLM call:

```bash
python -m py_compile kimi_vllm_factory.py
```

Optional offline smoke should test:

- sanitizer removes markdown fences.
- thinking policy maps codegen to non-thinking and comprehension to thinking.
- timeout estimator returns expected values.

## Step 1: Non-Thinking First Pass

Full n=1 first pass:

```bash
VLLM_ENABLE_THINKING=false \
python run_samples.py \
  -f full_dataset/cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl \
  -l -m vllm-glm -n 1 -k 1 \
  -p research_outputs/two_stage_thinking_codegen/runs/A4_B0_nonthinking_first
```

For initial low-cost validation, use a smoke subset instead of the full dataset.

## Step 2: Extract Failed IDs

After first pass, extract failed IDs from `report.json` or `raw_result.json` and create:

```text
research_outputs/two_stage_thinking_codegen/subsets/failed_subset.jsonl
```

This extraction script should be written as a separate utility in the next implementation phase.

## Step 3: Thinking Retry on Failed Subset

Short/medium thinking retry:

```bash
VLLM_ENABLE_THINKING=true \
VLLM_PROMPT_PROFILE=strict_codegen_thinking \
VLLM_MAX_TOKENS_CODEGEN_THINKING=12000 \
python run_samples.py \
  -f research_outputs/two_stage_thinking_codegen/subsets/failed_subset.jsonl \
  -l -m vllm-glm -n 1 -k 1 \
  -p research_outputs/two_stage_thinking_codegen/runs/A4_B2_thinking_retry
```

## Step 4: Merge Results

Merge first pass and retry results:

```text
if first_pass[id] == pass:
    final[id] = pass_nonthinking
elif thinking_retry[id] == pass:
    final[id] = pass_thinking_rescue
else:
    final[id] = fail_residual
```

Output should include:

```text
first_pass_rate
thinking_rescue_rate
final_two_stage_rate
empty_final_content_count
extra_cost_per_rescue
```

## Step 5: Long Thinking Sweep

Only run on selected representative cases after short thinking shows a rescue signal.

Do not run full-dataset T3/T4 sweeps without prior evidence.

## Step 6: Failure-Log Repair

Later runner-level phase:

```text
first-pass fail -> parse compile/harness log -> thinking repair -> rerun harness
```

This requires changes outside `kimi_vllm_factory.py`.
