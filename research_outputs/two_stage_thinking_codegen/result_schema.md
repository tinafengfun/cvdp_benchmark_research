# Result Schema

Experiments should save machine-readable results for reproducibility and later paper analysis.

## Per-Generation Record

Recommended JSONL record per model call:

```json
{
  "experiment_id": "A4_B2_T1",
  "sample_index": 1,
  "problem_id": "cvdp_copilot_axi_stream_upscale_0001",
  "category": 3,
  "difficulty": "easy",
  "stage": "thinking_retry",
  "thinking_enabled": true,
  "prompt_profile": "strict_codegen_thinking",
  "max_tokens": 12000,
  "timeout_s": 600,
  "duration_s": 412.5,
  "finish_reason": "stop",
  "content_len": 8123,
  "reasoning_len": 22014,
  "raw_output_path": "...",
  "parsed_output_path": "...",
  "error_type": null,
  "retry_mode": "none"
}
```

## Per-Harness Record

Recommended JSONL record per evaluated problem:

```json
{
  "experiment_id": "A4_B2_T1",
  "problem_id": "cvdp_copilot_axi_stream_upscale_0001",
  "category": 3,
  "stage": "thinking_retry",
  "harness_result": "fail",
  "failure_class": "syntax",
  "first_error": "/code/rtl/axis_upscale.sv:40: syntax error",
  "report_path": ".../reports/1.txt",
  "sim_log_path": ".../rundir/sim.log",
  "passed_tests": 0,
  "failed_tests": 1
}
```

## Per-Merged Two-Stage Record

Recommended JSONL record per problem after merging:

```json
{
  "problem_id": "cvdp_copilot_axi_stream_upscale_0001",
  "category": 3,
  "first_pass_status": "fail",
  "first_pass_failure_class": "syntax",
  "thinking_retry_status": "pass",
  "thinking_retry_failure_class": null,
  "final_status": "pass_thinking_rescue",
  "rescued_by_thinking": true,
  "residual_candidate": false,
  "finetune_candidate": false
}
```

## Experiment Summary Record

Recommended JSON:

```json
{
  "experiment_id": "A4_B2_T1",
  "dataset": "cvdp_v1.1.0_nonagentic_code_generation_no_commercial",
  "total_problems": 302,
  "first_pass_passed": 0,
  "first_pass_failed": 0,
  "thinking_retry_attempted": 0,
  "thinking_retry_passed": 0,
  "rescued_by_thinking": 0,
  "final_passed": 0,
  "final_pass_rate": 0.0,
  "timeout_count": 0,
  "empty_final_content_count": 0,
  "parse_failure_count": 0,
  "syntax_failure_count": 0,
  "compile_failure_count": 0,
  "harness_failure_count": 0,
  "notes": ""
}
```

## Naming Convention

Use stable experiment IDs:

```text
A{factory_ablation}_B{thinking_strategy}_T{token_sweep}_C{agentic_level}
```

Examples:

```text
A0_B0
A4_B0
A4_B2_T1
A6_B3_T1_C2
```
