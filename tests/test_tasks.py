import math

import pytest

from defi_agent_evals.tasks import (
    INSUFFICIENT,
    REQUIRED,
    amm_amount_out,
    build_suite,
    health_factor,
    impermanent_loss,
    liquidation_price,
    tick_to_price,
)


def test_amm_matches_uniswap_v2_reference():
    # Uniswap v2 getAmountOut: 1 ETH into a 100 ETH / 200,000 USDC pool at 30 bps.
    assert amm_amount_out(10**18, 100 * 10**18, 200_000 * 10**6, 30) == 1974316068


def test_amm_floors_and_rejects_bad_input():
    assert amm_amount_out(1, 10**6, 10**6, 30) == 0
    with pytest.raises(ValueError):
        amm_amount_out(0, 1, 1, 30)
    with pytest.raises(ValueError):
        amm_amount_out(1, 1, 1, 10_000)


def test_impermanent_loss_known_values():
    assert impermanent_loss(1.0) == 0.0
    assert math.isclose(impermanent_loss(4.0), -0.2)
    assert math.isclose(impermanent_loss(0.25), -0.2)  # symmetric in log-price
    with pytest.raises(ValueError):
        impermanent_loss(0)


def test_tick_price_and_decimals():
    assert tick_to_price(0, 18, 18) == 1.0
    assert math.isclose(tick_to_price(0, 18, 6), 1e12)
    assert math.isclose(tick_to_price(-1, 6, 6) * tick_to_price(1, 6, 6), 1.0)


def test_health_and_liquidation_are_consistent():
    hf = health_factor([{"amount": 10, "price": 2000, "liquidation_threshold": 0.8}], 8000, 1.0)
    assert math.isclose(hf, 2.0)
    p = liquidation_price(10, 0.8, 8000)
    assert math.isclose(health_factor([{"amount": 10, "price": p, "liquidation_threshold": 0.8}], 8000, 1.0), 1.0)


def test_suite_is_deterministic_and_complete():
    a, b = build_suite(seed=7), build_suite(seed=7)
    assert a == b
    assert build_suite(seed=8) != a
    assert len({t.id for t in a}) == len(a) == 50
    missing = [t for t in a if t.match == "refuse"]
    assert len(missing) == 10
    for t in missing:
        assert t.expected == INSUFFICIENT
        assert REQUIRED[t.domain] not in t.data
