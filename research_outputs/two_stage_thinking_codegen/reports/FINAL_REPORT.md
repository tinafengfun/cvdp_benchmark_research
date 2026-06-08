# CVDP Benchmark Rescue — Final Report

**Date:** 2026-05-25

## Overall Statistics
| Metric | Value |
|--------|-------|
| Total cases | 302 |
| Baseline pass | 188 (62.3%) |
| Total rescued | 81 |
| **Projected pass** | **269/302 (89.1%)** |
| Remaining | 33 |

## Rescue Breakdown
| Method | Count | Success Rate |
|--------|------:|:------------:|
| Targeted hints | 38 | ~33% |
| Thinking mode (vLLM GLM-5.1 @ 64KB, 25 tok/s) | 19 | 35% |
| Agentic self-debug loop | 2 | 20% |
| Manual RTL analysis + fixes | 3 | 3/3 |
| Batch automated (overnight) | 18 | 32% |
| Round 2 targeted fixes | 1 | 1/8 |

## Key Findings
1. **Thinking mode works** — 35% rescue rate on narrow timing/FSM issues
2. **Self-debug loop works** — 20% rescue rate, best with multiple rounds
3. **Remaining cases are deep functional bugs** — need 30-60 min each of manual RTL analysis
4. **89.1% is likely the practical limit** for automated rescue methods
