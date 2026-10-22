# defi-agent-evals

A small DeFi analyst agent built on the Claude Agent SDK, graded by deterministic verifiers.
Every task is generated from a seed and carries its own ground truth, so a pass is a fact, not an opinion.

Domains: constant-product swap output (Uniswap v2 integer math), impermanent loss, concentrated-liquidity
tick price, lending health factor, liquidation price, and missing-data tasks where the right answer is
to refuse (`INSUFFICIENT_DATA`).

## Run
```bash
uv sync
uv run pytest
uv run dae run --model claude-haiku-5-5 --condition bare --out results/haiku-bare.jsonl
uv run dae run --model claude-haiku-5-5 --condition calc --out results/haiku-calc.jsonl
uv run dae report results/*.jsonl
```
The agent runs through the Claude Code CLI (`CLAUDE_CLI` overrides its path) with user settings disabled.

## Results
On 50 seeded tasks, Claude Haiku 5.5 went from 56% to 100% pass. None of the gain came from a bigger model;
each fix came from reading failures. Full write-up: [docs/memo.md](docs/memo.md).

| Step | Change | Pass rate |
|---|---|---|
| v0 | Bare model, task spec silent on precision | 28/50 (56%) |
| v1 | Spec asks for full precision | 42/50 (84%) |
| v2 | + calculator tool (in-process MCP) | 45/50 (90%) |
| v3 | + output contract: numbers travel as strings | 50/50 (100%) |

For scale, `claude-sonnet-5-5` bare with the v1 spec scored 44/50 and failed the same large-integer swaps.

Design and requirement-to-test map: [docs/spec.md](docs/spec.md).
