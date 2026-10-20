# Memo: what moved a DeFi agent from 56% to 100% (2026-10-20)

**Result.** On 50 seeded DeFi tasks graded by code, Claude Haiku 5.5 went from 56% to 100% pass.
None of the gain came from a better model. It came from three fixes, each found by reading failures:

| Step | Change | Pass rate |
|---|---|---|
| v0 | Bare model, task spec silent on precision | 28/50 (56%) |
| v1 | Spec asks for full precision (no rounding) | 42/50 (84%) |
| v2 | + calculator tool (in-process MCP) | 45/50 (90%) |
| v3 | + output contract: numbers travel as strings | 50/50 (100%) |

Model: `claude-haiku-5-5` through the Claude Agent SDK, one run per task, seed 7. Missing-data refusals
were 10/10 in every condition. For scale: the larger `claude-sonnet-5-5`, bare with the v1 spec,
scored 44/50 (88%) and failed the same five large-integer swaps, so that failure is a contract
problem, not a model-size problem. The small model with the fixes beat the large model without them.

## What the failures said

1. **The first bug was mine, not the model's.** 15 of 22 v0 failures were answers rounded to
   4 or 5 significant digits, graded against a 1e-6 tolerance the task never stated (two were real
   arithmetic errors; five were the integer problem in point 3). A verifier that is stricter
   than the spec measures the spec, so I fixed the spec and kept the tolerance.
2. **Mental arithmetic fails quietly.** The bare model's remaining misses were plausible numbers off in
   the fourth or fifth significant digit (health factor 9.67409 vs 9.67377; 37.1883 vs 37.1933). A calculator tool
   removed every arithmetic miss.
3. **The model computed the right integer and then lost it.** Five swap outputs exceed 2^53. The model
   got the exact value from the calculator, then emitted it as a JSON number, which a float cannot
   hold. Telling it to send strings did not work in a two-task smoke test: the schema still allowed numbers, and it used them.
   Changing the schema so every number is a string fixed all five. This is why payment and onchain APIs
   carry amounts as strings or integer base units.

## How the grading works
Every task is generated from a seed with its own ground truth: Uniswap v2 `getAmountOut` integer math,
impermanent loss, concentrated-liquidity tick price with decimals, health factor, and liquidation
price. Ten tasks drop a required field; the only correct answer is `INSUFFICIENT_DATA`. The grader
returns pass, wrong, format, false refusal, or missed refusal, and never asks a model for an opinion.
I rechecked the v3 swap and tick answers with 50-digit `Decimal` arithmetic; all matched.

## Limits
- Each question states its formula, so this measures arithmetic and output contracts, not DeFi judgment.
- 50 tasks and one run per condition: a 100% here is not a reliability claim, and run-to-run variance
  is unmeasured.
- The v0 calculator run (37/50) was graded but its raw file was overwritten; only the v0 baseline raw
  file is kept (`results/v0-ambiguous-precision/`).
- Not tested: the string contract without the calculator.

## Next
Harder tasks where the agent must choose the formula: swaps that cross ticks, multi-asset liquidation
ordering, and fee-tier routing. Repeat runs per task to measure variance, and a cost-per-pass column.
