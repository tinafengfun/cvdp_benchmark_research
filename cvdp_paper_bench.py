#!/usr/bin/env python3
"""
CVDP Paper-Style Benchmark — runs per-category scoring matching paper methodology.

Usage:
    # Full 302-case benchmark (matches paper Table 2)
    python cvdp_paper_bench.py --model copilot --samples 5

    # Quick per-category smoke test (1 sample each, 5 categories)
    python cvdp_paper_bench.py --model copilot --samples 1 --smoke

    # Run specific categories only
    python cvdp_paper_bench.py --model copilot --categories cid003,cid004 --samples 3

Environment:
    CUSTOM_MODEL_FACTORY=/path/to/copilot_direct_factory.py
    COPILOT_MODEL=gpt-5-mini
    https_proxy=http://child-prc.intel.com:912
"""

import os, sys, json, csv, time, argparse, subprocess, re, random, tempfile
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

DATASET = "full_dataset/cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl"

# Paper's model results (pass@1 rates from Table 2)
PAPER_RESULTS = {
    "Claude 3.7 Sonnet": {"cid02": 34.0, "cid03": 48.0, "cid04": 45.0, "cid07": 44.0, "cid16": 53.0, "overall": 33.56},
    "GPT 4.1":          {"cid02": 37.0, "cid03": 44.0, "cid04": 37.0, "cid07": 32.0, "cid16": 45.0, "overall": 28.91},
    "Llama 3.1 405B":   {"cid02": 24.0, "cid03": 31.0, "cid04": 36.0, "cid07": 20.0, "cid16": 32.0, "overall": 22.79},
    "GPT o4-mini":      {"cid02": 35.0, "cid03": 47.0, "cid04": 44.0, "cid07": 27.0, "cid16": 43.0, "overall": 28.74},
}

ALL_CATEGORIES = ["cid002", "cid003", "cid004", "cid007", "cid016"]  # skip cid012-014 (need commercial EDA)


def parse_args():
    p = argparse.ArgumentParser(description="CVDP Paper-Style Benchmark")
    p.add_argument("--model", default="copilot", help="Model key")
    p.add_argument("--samples", type=int, default=1, help="Number of samples (paper uses 5)")
    p.add_argument("--smoke", action="store_true", help="Quick smoke test: 3 cases/category")
    p.add_argument("--categories", default=None, help="Comma-separated categories to run")
    p.add_argument("--output", default=None, help="Output JSON path")
    p.add_argument("--threads", type=int, default=2, help="Parallel threads")
    return p.parse_args()


def load_cases():
    cases_by_cat = OrderedDict()
    with open(DATASET) as f:
        for line in f:
            d = json.loads(line)
            cats = d.get("categories", [])
            for c in cats:
                cid = c.split("-")[0] if "-" in c else c
                if cid in ALL_CATEGORIES or cid in (args.categories or ""):
                    cases_by_cat.setdefault(cid, []).append(d)
                    break
    return cases_by_cat


def pick_smoke_subset(cases_by_cat, n=3):
    random.seed(42)
    subset = []
    for cid in ALL_CATEGORIES:
        pool = cases_by_cat.get(cid, [])
        random.shuffle(pool)
        subset.extend(pool[:n])
    return subset


def make_jsonl(cases, path):
    with open(path, "w") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")


def run_sample(subset_file, model, threads, sample_num, prefix):
    env = os.environ.copy()
    env["BENCHMARK_THREADS"] = str(threads)
    cmd = [sys.executable, "run_benchmark.py", "-f", subset_file, "-l", "-m", model, "-p", prefix]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200, env=env)
    output = r.stdout + r.stderr

    # Parse per-category results
    cat_results = {}
    for cid in ALL_CATEGORIES:
        m = re.findall(rf"\| {cid}[^|]*\|[^|]*\|[^|]*\|[^|]*\|", output)
        if m:
            parts = m[0].split("|")
            if len(parts) >= 5:
                try:
                    p = int(parts[3].strip().split("/")[0]) if "/" in parts[3] else int(parts[3].strip())
                    cat_results[cid] = p
                except ValueError:
                    pass

    # Overall total
    total_pass = sum(cat_results.get(c, 0) for c in ALL_CATEGORIES)
    total_tests = re.search(r"Total Tests\D+(\d+)", output)
    total = int(total_tests.group(1)) if total_tests else 0

    return {"pass": cat_results, "total": total, "raw": output}


def main():
    global args
    args = parse_args()

    print(f"{'='*70}")
    print(f"  CVDP Paper-Style Benchmark")
    print(f"  Model:   {args.model}")
    print(f"  Samples: {args.samples}")
    print(f"  Smoke:   {args.smoke}")
    print(f"{'='*70}\n")

    # Load cases
    cases_by_cat = load_cases()
    if args.smoke:
        cases = pick_smoke_subset(cases_by_cat, 3)
        print(f"Smoke mode: {len(cases)} cases ({sum(1 for c in cases for cat in c['categories'] if cat.split('-')[0] in ALL_CATEGORIES)} unique)")
    else:
        cases = [c for cid in ALL_CATEGORIES for c in cases_by_cat.get(cid, [])]
        print(f"Full mode: {len(cases)} cases")

    # Count per category
    for cid in ALL_CATEGORIES:
        n = len(cases_by_cat.get(cid, []))
        paper = ", ".join(f"{k}: {v[cid[:5]]}%" for k, v in PAPER_RESULTS.items() if cid[:5] in v)
        print(f"  {cid}: {n} cases (paper: {paper})")

    if len(cases) == 0:
        print("No cases found!")
        return

    # Run samples
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_passes = {cid: [] for cid in ALL_CATEGORIES}
    totals = []

    for s in range(args.samples):
        print(f"\n--- Sample {s+1}/{args.samples} ---")
        sf = f"/tmp/bench_paper_{ts}_s{s}.jsonl"
        make_jsonl(cases, sf)

        prefix = f"work_paper_{args.model}_{ts}_s{s}"
        result = run_sample(sf, args.model, args.threads, s, prefix)

        tot = result["total"]
        totals.append(tot)
        for cid in ALL_CATEGORIES:
            p = result["pass"].get(cid, 0)
            all_passes[cid].append(p)
            print(f"  {cid}: {p}/{len(cases_by_cat.get(cid, []))} passed")

        os.remove(sf)

    # Compute pass@1 with n=samples
    results = {}
    overall_pass = 0
    overall_total = 0
    print(f"\n{'='*70}")
    print(f"  RESULTS (pass@1, n={args.samples})")
    print(f"{'='*70}")
    print(f"  {'Category':<10} {'Cases':<7} {'Pass@1':<10} {'Rate':<8} {'Paper (best)':<20}")
    print(f"  {'-'*55}")

    for cid in ALL_CATEGORIES:
        n_cases = len(cases_by_cat.get(cid, []))
        if n_cases == 0:
            continue
        passes = all_passes[cid]
        # pass@1 with n=samples: count cases that passed at least once
        from collections import Counter
        case_passes = Counter()
        for s_idx in range(len(passes)):
            # We don't have per-case pass/fail from aggregate data
            # Use aggregate as approximation
            pass
        # Simplified: use average pass count
        avg = sum(passes) / max(len(passes), 1)
        rate = avg / n_cases * 100

        paper_best = max((v.get(cid[:5], 0) for v in PAPER_RESULTS.values() if cid[:5] in v), default=0)
        paper_str = f"{paper_best}%" if paper_best else "-"

        print(f"  {cid:<10} {n_cases:<7} {avg:<10.0f} {rate:<8.1f} {paper_str:<20}")
        results[cid] = {"cases": n_cases, "pass": avg, "rate": rate, "paper_best": paper_best}

    # Overall
    total_cases = sum(len(cases_by_cat.get(c, [])) for c in ALL_CATEGORIES)
    total_avg = sum(sum(all_passes[c]) / max(len(all_passes[c]), 1) for c in ALL_CATEGORIES)
    total_rate = total_avg / max(total_cases, 1) * 100
    paper_overall = max(v["overall"] for v in PAPER_RESULTS.values())
    print(f"  {'-'*55}")
    print(f"  {'OVERALL':<10} {total_cases:<7} {total_avg:<10.0f} {total_rate:<8.1f} {paper_overall:<20}")

    results["overall"] = {"cases": total_cases, "pass": total_avg, "rate": total_rate, "paper_best": paper_overall}

    # Save
    out_path = args.output or f"bench_paper_{args.model}_{ts}.json"
    with open(out_path, "w") as f:
        json.dump({
            "model": args.model,
            "model_name": os.environ.get("COPILOT_MODEL", "?"),
            "samples": args.samples,
            "smoke": args.smoke,
            "timestamp": ts,
            "results": results,
        }, f, indent=2)
    print(f"\n  Results saved: {out_path}")
    print(f"\n  Done.")


if __name__ == "__main__":
    main()
