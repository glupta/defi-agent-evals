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
See [docs/memo.md](docs/memo.md).

Design and requirement-to-test map: [docs/spec.md](docs/spec.md).
