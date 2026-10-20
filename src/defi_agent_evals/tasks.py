"""Deterministic DeFi task generators. Each task carries its own ground truth."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

INSUFFICIENT = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class Task:
    id: str
    domain: str
    question: str
    data: dict[str, Any]
    expected: int | float | str
    # "exact" for integer token amounts, "rel" for real-valued answers, "refuse" for missing data.
    match: str
    rel_tol: float = 1e-6
    meta: dict[str, Any] = field(default_factory=dict)


def amm_amount_out(amount_in: int, reserve_in: int, reserve_out: int, fee_bps: int) -> int:
    """Constant-product swap output with integer floor, as in Uniswap v2 getAmountOut."""
    if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
        raise ValueError("amounts and reserves must be positive")
    if not 0 <= fee_bps < 10_000:
        raise ValueError("fee_bps must be in [0, 10000)")
    with_fee = amount_in * (10_000 - fee_bps)
    return (with_fee * reserve_out) // (reserve_in * 10_000 + with_fee)


def impermanent_loss(price_ratio: float) -> float:
    """Value change of a 50/50 constant-product LP vs holding, for price ratio r = p1/p0."""
    if price_ratio <= 0:
        raise ValueError("price_ratio must be positive")
    return 2 * math.sqrt(price_ratio) / (1 + price_ratio) - 1


def tick_to_price(tick: int, decimals0: int, decimals1: int) -> float:
    """Human price of token0 quoted in token1 for a concentrated-liquidity tick."""
    return 1.0001**tick * 10 ** (decimals0 - decimals1)


def health_factor(collaterals: list[dict[str, float]], debt_amount: float, debt_price: float) -> float:
    debt_value = debt_amount * debt_price
    if debt_value <= 0:
        raise ValueError("debt must be positive")
    return sum(c["amount"] * c["price"] * c["liquidation_threshold"] for c in collaterals) / debt_value


def liquidation_price(collateral_amount: float, liquidation_threshold: float, debt_value: float) -> float:
    """Collateral price at which a single-collateral position reaches health factor 1."""
    return debt_value / (collateral_amount * liquidation_threshold)


def _amm(rng: random.Random, i: int) -> Task:
    dec = rng.choice([6, 9, 18])
    reserve_in = rng.randint(10_000, 5_000_000) * 10**dec
    reserve_out = rng.randint(10_000, 5_000_000) * 10**dec
    amount_in = rng.randint(1, 50_000) * 10**dec + rng.randint(0, 10**dec - 1)
    fee_bps = rng.choice([1, 5, 30, 100])
    data = {"reserve_in": reserve_in, "reserve_out": reserve_out, "amount_in": amount_in, "fee_bps": fee_bps}
    q = (
        "A constant-product pool (x*y=k) charges fee_bps basis points on the input amount. "
        "All amounts are raw integer base units. Compute the output amount the trader receives, "
        "rounded down to an integer, exactly as Uniswap v2 getAmountOut does."
    )
    return Task(
        f"amm-{i:02d}", "amm_swap", q, data, amm_amount_out(amount_in, reserve_in, reserve_out, fee_bps), "exact"
    )


def _il(rng: random.Random, i: int) -> Task:
    r = round(rng.choice([rng.uniform(0.05, 0.95), rng.uniform(1.05, 20.0)]), 4)
    q = (
        "A liquidity provider deposits into a 50/50 constant-product pool. Afterward the price of the "
        "volatile asset changes by price_ratio (new price / old price), with no fees earned. Give the "
        "impermanent loss versus simply holding, as a signed decimal fraction (e.g. -0.05 for a 5% loss)."
    )
    return Task(f"il-{i:02d}", "impermanent_loss", q, {"price_ratio": r}, impermanent_loss(r), "rel", 1e-4)


def _tick(rng: random.Random, i: int) -> Task:
    d0, d1 = rng.choice([(18, 6), (6, 18), (9, 6), (8, 18), (18, 18)])
    tick = rng.randint(-300_000, 300_000)
    data = {"tick": tick, "token0_decimals": d0, "token1_decimals": d1}
    q = (
        "In a concentrated-liquidity pool, the raw price of token0 in token1 is 1.0001**tick. "
        "Convert it to a human-readable price of one whole token0 quoted in whole token1, "
        "adjusting for both tokens' decimals."
    )
    return Task(f"tick-{i:02d}", "tick_price", q, data, tick_to_price(tick, d0, d1), "rel", 1e-6)


def _hf(rng: random.Random, i: int) -> Task:
    cols = [
        {
            "asset": a,
            "amount": round(rng.uniform(0.5, 500.0), 4),
            "price": round(rng.uniform(0.5, 4000.0), 2),
            "liquidation_threshold": rng.choice([0.7, 0.75, 0.8, 0.825, 0.85]),
        }
        for a in rng.sample(["ETH", "WBTC", "SUI", "SOL", "stETH"], k=rng.randint(1, 3))
    ]
    debt_amount = round(rng.uniform(100, 200_000), 2)
    data = {"collaterals": cols, "debt_amount": debt_amount, "debt_price": 1.0, "debt_asset": "USDC"}
    q = (
        "Compute the lending position's health factor: the sum over collaterals of "
        "amount * price * liquidation_threshold, divided by the debt value (debt_amount * debt_price)."
    )
    return Task(f"hf-{i:02d}", "health_factor", q, data, health_factor(cols, debt_amount, 1.0), "rel")


def _liq(rng: random.Random, i: int) -> Task:
    amount = round(rng.uniform(1, 300), 3)
    lt = rng.choice([0.7, 0.75, 0.8, 0.825, 0.86])
    debt = round(rng.uniform(1_000, 400_000), 2)
    data = {"collateral_asset": "ETH", "collateral_amount": amount, "liquidation_threshold": lt, "debt_value_usd": debt}
    q = (
        "A position has a single collateral asset and stablecoin debt. At what collateral price (USD) "
        "does its health factor fall to exactly 1.0?"
    )
    return Task(f"liq-{i:02d}", "liquidation_price", q, data, liquidation_price(amount, lt, debt), "rel")


GENERATORS = [_amm, _il, _tick, _hf, _liq]
# Field whose removal makes each domain's question unanswerable.
REQUIRED = {
    "amm_swap": "reserve_out",
    "impermanent_loss": "price_ratio",
    "tick_price": "token1_decimals",
    "health_factor": "debt_amount",
    "liquidation_price": "liquidation_threshold",
}


def build_suite(seed: int = 7, per_domain: int = 8, unanswerable: int = 10) -> list[Task]:
    rng = random.Random(seed)
    tasks = [gen(rng, i) for gen in GENERATORS for i in range(per_domain)]
    for i in range(unanswerable):
        base = GENERATORS[i % len(GENERATORS)](rng, 90 + i)
        data = {k: v for k, v in base.data.items() if k != REQUIRED[base.domain]}
        tasks.append(
            Task(
                f"missing-{i:02d}",
                base.domain,
                base.question,
                data,
                INSUFFICIENT,
                "refuse",
                meta={"removed": REQUIRED[base.domain]},
            )
        )
    return tasks
