import math

import pytest

from defi_agent_evals.calc import CalcError, evaluate


def test_arithmetic_and_functions():
    assert evaluate("(10**18*9970*200000*10**6)//(100*10**18*10000+10**18*9970)") == 1974316068
    assert math.isclose(evaluate("2*sqrt(4)/(1+4)-1"), -0.2)
    assert math.isclose(evaluate("1.0001**-1 * 1.0001**1"), 1.0)


@pytest.mark.parametrize(
    "expr",
    ["__import__('os')", "open('x')", "(1).__class__", "x + 1", "1/0", "9**9**9", "a" * 3000, "sqrt(-1)", "exp(1e6)"],
)
def test_rejects_unsafe_or_failing(expr):
    with pytest.raises(CalcError):
        evaluate(expr)
