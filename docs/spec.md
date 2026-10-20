# Spec: DeFi analyst agent with deterministic verifiers (v1)

## Constitution
No fabricated data, no secrets in the repo, no wallets or money movement.
Grading is code, never model judgment. Every behavior change ships a failing-then-passing test.
Simplicity: one package, standard library plus the Claude Agent SDK.

## Outcome
Measure how reliably a Claude agent answers DeFi quantitative questions, and show that eval-driven
changes (a calculator tool, then an output-contract fix) move the pass rate.

## Scenarios
1. Run the suite against a model and condition; get a JSONL of raw runs.
2. Grade saved runs into a pass-rate table by condition and domain.
3. Answerable task: agent returns the exact or tolerance-matched number.
4. Missing-data task: agent returns `INSUFFICIENT_DATA` instead of guessing.

## Requirements -> tests
| Req | Requirement | Test |
|---|---|---|
| R1 | Ground truth matches published formulas (Uniswap v2 getAmountOut, IL, tick price, health factor, liquidation price) | tests/test_tasks.py |
| R2 | Suite is deterministic per seed; 40 answerable + 10 missing-data tasks with unique ids | test_suite_is_deterministic_and_complete |
| R3 | Grader verdicts: pass, wrong, format, false_refusal, missed_refusal; booleans, NaN, malformed output, lossy big floats are format failures | tests/test_verify.py |
| R4 | Calculator tool evaluates arithmetic only; rejects names, attributes, oversized powers | tests/test_calc.py |
| R5 | Report counts every run, including run errors | tests/test_report.py |
| R6 | Agent runs isolated from the operator's settings (`setting_sources=[]`, no built-in tools) | agent.py options; reviewed |

## Non-goals
Live chain reads, trading, any wallet or key handling, LLM-as-judge.

## Plan
Conditions: `bare` (no tools), `calc` (in-process MCP calculator), `calc_v2` (calculator plus integer amounts
as decimal strings, added after the calc run showed large integers losing precision as JSON floats).
SCORE: not applicable — a local CLI and library with no deployable workload.

## Kill condition
If verifiers cannot be made exact for a domain, drop the domain rather than grade it by judgment.
