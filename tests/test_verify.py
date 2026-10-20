import pytest

from defi_agent_evals.tasks import INSUFFICIENT, Task
from defi_agent_evals.verify import grade

EXACT = Task("e", "amm_swap", "q", {}, 1974316068, "exact")
REL = Task("r", "impermanent_loss", "q", {}, -0.2, "rel", 1e-4)
BIG = Task("b", "amm_swap", "q", {}, 2**60 + 1, "exact")
REFUSE = Task("m", "amm_swap", "q", {}, INSUFFICIENT, "refuse")


@pytest.mark.parametrize(
    ("task", "output", "verdict"),
    [
        (EXACT, {"answer": 1974316068}, "pass"),
        (EXACT, {"answer": 1974316068.0}, "pass"),
        (EXACT, {"answer": 1974316069}, "wrong"),
        (EXACT, {"answer": 1974316068.5}, "wrong"),
        (BIG, {"answer": float(2**60 + 1)}, "format"),
        (BIG, {"answer": 2**60 + 1}, "pass"),
        (REL, {"answer": -0.20001}, "pass"),
        (REL, {"answer": -0.2001}, "wrong"),
        (REL, {"answer": "-0.2"}, "pass"),
        (REL, {"answer": "-2.0000e-1"}, "pass"),
        (REL, {"answer": "-0.2%"}, "format"),
        (REL, {"answer": "about -0.2"}, "format"),
        (REL, {"answer": float("nan")}, "format"),
        (REL, {"answer": True}, "format"),
        (REL, {"value": -0.2}, "format"),
        (REL, "-0.2", "format"),
        (REL, {"answer": INSUFFICIENT}, "false_refusal"),
        (REFUSE, {"answer": INSUFFICIENT}, "pass"),
        (REFUSE, {"answer": 5}, "missed_refusal"),
        (REFUSE, {"answer": "insufficient_data"}, "format"),
        (BIG, {"answer": str(2**60 + 1)}, "pass"),
        (BIG, {"answer": str(2**60)}, "wrong"),
        (EXACT, {"answer": "1,974,316,068"}, "format"),
        (EXACT, {"answer": "1974316068.0"}, "format"),
        (REL, {"answer": "1"}, "wrong"),
        (REFUSE, {"answer": "5"}, "missed_refusal"),
    ],
)
def test_grade(task, output, verdict):
    assert grade(task, output).verdict == verdict
