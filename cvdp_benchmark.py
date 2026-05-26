#!/usr/bin/env python3
"""
CVDP Model Benchmark Script — runs a curated subset for quick model scoring.

Usage:
    # Score all 302 cases (full benchmark)
    python cvdp_benchmark.py --model copilot --cases all

    # Score only easy/medium/hard cases
    python cvdp_benchmark.py --model copilot --difficulty easy,medium

    # Score only specific categories
    python cvdp_benchmark.py --model copilot --categories cid002,cid003

    # Compare with saved baseline
    python cvdp_benchmark.py --model copilot --compare baseline.json

Environment:
    CUSTOM_MODEL_FACTORY=/path/to/copilot_direct_factory.py
    COPILOT_MODEL=gpt-5-mini
    https_proxy=http://child-prc.intel.com:912   # if behind proxy
"""

import os
import sys
import json
import csv
import time
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

DATASET = "full_dataset/cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl"
BASELINE_PASS = 188  # CVDP paper baseline (non-thinking codegen)

# Scoring categories used in CVDP paper model comparisons
SCORING_CATEGORIES = {
    "all": "All 302 cases",
    "cid002": "Arithmetic/Logic (easy-medium)",
    "cid003": "Control Logic/FSM (medium)",
    "cid004": "Data Path/Arithmetic (medium)",
    "cid005": "Memory/Storage (medium-hard)",
    "cid007": "Signal Processing (medium-hard)",
    "cid016": "Optimization/Synthesis (hard)",
}

# Difficulty levels
DIFFICULTIES = {
    "easy": "Basic single-module designs",
    "medium": "Multi-module with FSM/timing",
    "hard": "Complex protocols + optimizations",
}


def parse_args():
    p = argparse.ArgumentParser(description="CVDP Model Benchmark")
    p.add_argument("--model", default="copilot",
                   help="Model key for CustomModelFactory (default: copilot)")
    p.add_argument("--cases", choices=["all", "by_category", "by_difficulty", "smoke"],
                   default="smoke",
                   help="Case selection strategy (default: smoke)")
    p.add_argument("--categories", default="cid002,cid003,cid004",
                   help="Comma-separated categories to test")
    p.add_argument("--difficulty", default="easy,medium",
                   help="Comma-separated difficulty levels")
    p.add_argument("--sample", type=int, default=3,
                   help="Number of cases to sample per group (smoke mode)")
    p.add_argument("--compare", help="JSON file with baseline results for comparison")
    p.add_argument("--output", default=None,
                   help="Output file for results (default: auto-name)")
    p.add_argument("--threads", type=int, default=1,
                   help="Parallel threads (default: 1)")
    return p.parse_args()


def load_dataset(select_ids=None):
    """Load cases from dataset, optionally filtering by ID list."""
    cases = []
    with open(DATASET) as f:
        for line in f:
            d = json.loads(line)
            if select_ids is None or d["id"] in select_ids:
                cases.append(d)
    return cases


def filter_by_category(cases, categories):
    """Filter cases matching any of the given category prefixes."""
    cats = set(c.strip() for c in categories.split(","))
    result = []
    for c in cases:
        for cat in c.get("categories", []):
            if cat in cats:
                result.append(c)
                break
    return result


def pick_smoke_cases(cases, n=3):
    """Pick a diverse smoke test subset: 1 easy, 1 medium, 1+ residual."""
    import random
    random.seed(42)

    # Read funnel failures for difficulty info
    failures = {}
    try:
        with open("research_outputs/two_stage_thinking_codegen/reports/"
                   "full_funnel_failure_cases_2026-05-15.csv") as f:
            for row in csv.DictReader(f):
                failures[row["case_id"]] = row
    except FileNotFoundError:
        pass

    # Tag each case with difficulty from funnel data
    tagged = []
    for c in cases:
        cid = c["id"]
        diff = failures.get(cid, {}).get("difficulty", "medium") if failures else "medium"
        tagged.append((c, diff))

    # Pick by difficulty distribution
    picks = []
    random.shuffle(tagged)
    for diff in ["easy", "medium", "hard"]:
        pool = [c for c, d in tagged if d == diff and c not in picks]
        picks.extend(pool[:max(1, n // 3)])
    # Fill remaining
    if len(picks) < n:
        for c, d in tagged:
            if c not in picks:
                picks.append(c)
                if len(picks) >= n:
                    break
    return picks[:n]


def make_subset_jsonl(cases, output_path):
    """Write filtered cases to a temp JSONL file."""
    with open(output_path, "w") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
    return output_path


def run_benchmark(subset_file, model, threads, prefix):
    """Run run_benchmark.py on the subset file."""
    env = os.environ.copy()
    env["BENCHMARK_THREADS"] = str(threads)

    cmd = [
        sys.executable, "run_benchmark.py",
        "-f", subset_file,
        "-l",
        "-m", model,
        "-p", prefix,
    ]
    print(f"  Running: {' '.join(cmd)}")
    start = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200, env=env)
    elapsed = time.time() - start

    output = r.stdout + r.stderr
    # Parse result
    result = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "elapsed_s": round(elapsed, 1),
        "raw": output,
        "returncode": r.returncode,
    }
    import re
    tests = re.findall(r"Passed Problems[^0-9]*([0-9]+)", output)
    if tests:
        result["passed"] = int(tests[0])
    fails = re.findall(r"Failed Problems[^0-9]*([0-9]+)", output)
    if fails:
        result["failed"] = int(fails[0])
    result["total"] = result["passed"] + result["failed"]
    result["rate"] = round(result["passed"] / max(result["total"], 1) * 100, 1)
    return result


def main():
    args = parse_args()

    # Load all cases
    print(f"Loading dataset...")
    all_cases = load_dataset()
    print(f"  Total cases: {len(all_cases)}")

    # Select subset
    if args.cases == "smoke":
        subset = pick_smoke_cases(all_cases, args.sample)
        label = f"smoke{len(subset)}"
    elif args.cases == "all":
        subset = all_cases
        label = "all302"
    else:
        subset = filter_by_category(all_cases, args.categories)
        label = args.categories.replace(",", "_")

    print(f"  Selected {len(subset)} cases ({label})")

    # Write subset
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"work_bench_{args.model}_{label}_{ts}"
    subset_file = f"/tmp/bench_subset_{ts}.jsonl"
    make_subset_jsonl(subset, subset_file)

    # Run benchmark
    print(f"\n{'='*60}")
    print(f"  Model:      {args.model}")
    print(f"  Cases:      {len(subset)} ({label})")
    print(f"  Threads:    {args.threads}")
    print(f"  Prefix:     {prefix}")
    print(f"{'='*60}\n")

    result = run_benchmark(subset_file, args.model, args.threads, prefix)

    # Report
    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Passed:  {result['passed']}/{result['total']} ({result['rate']}%)")
    print(f"  Elapsed: {result['elapsed_s']:.0f}s")
    print(f"  Return:  {result['returncode']}")

    # Compare with baseline
    if result["total"] > 0:
        impl = (result["passed"] / result["total"]) * 100

    # Save results
    if args.output:
        out_path = args.output
    else:
        out_path = f"bench_result_{args.model}_{label}_{ts}.json"
    with open(out_path, "w") as f:
        json.dump({
            "model": args.model,
            "label": label,
            "timestamp": ts,
            "cases": len(subset),
            "passed": result["passed"],
            "failed": result["failed"],
            "total": result["total"],
            "rate": result["rate"],
            "elapsed_s": result["elapsed_s"],
        }, f, indent=2)
    print(f"\n  Results saved: {out_path}")

    # Cleanup
    os.remove(subset_file)

    print(f"\nDone.")


if __name__ == "__main__":
    main()
