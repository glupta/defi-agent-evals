"""Deterministic grader. No model judgment: every verdict is a pure function of task and output."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from defi_agent_evals.tasks import INSUFFICIENT, Task

_INT_STRING = re.compile(r"-?[0-9]+")
_NUM_STRING = re.compile(r"-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?")
VERDICTS = ("pass", "wrong", "format", "false_refusal", "missed_refusal")


@dataclass(frozen=True)
class Verdict:
    verdict: str
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == "pass"


def grade(task: Task, output: Any) -> Verdict:
    if not isinstance(output, dict) or "answer" not in output:
        return Verdict("format", "output is not an object with an 'answer' field")
    answer = output["answer"]
    # Numbers may arrive as strings (the v2 output contract) so large amounts keep full precision.
    if isinstance(answer, str) and answer != INSUFFICIENT:
        if _INT_STRING.fullmatch(answer):
            answer = int(answer)
        elif _NUM_STRING.fullmatch(answer):
            if task.match == "exact":
                return Verdict("format", "integer amount sent as a non-integer string")
            answer = float(answer)
    if answer == INSUFFICIENT:
        return Verdict("pass") if task.match == "refuse" else Verdict("false_refusal")
    # bool is an int subclass; a True/False answer is a format failure, not 1/0.
    if isinstance(answer, bool) or not isinstance(answer, int | float):
        return Verdict("format", f"answer must be a number or {INSUFFICIENT!r}, got {type(answer).__name__}")
    if isinstance(answer, float) and not math.isfinite(answer):
        return Verdict("format", "answer is not finite")
    if task.match == "refuse":
        return Verdict("missed_refusal", f"answered {answer} without required data")
    if task.match == "exact":
        if isinstance(answer, float) and not answer.is_integer():
            return Verdict("wrong", f"expected integer {task.expected}, got {answer}")
        # A float beyond 2**53 cannot represent every integer, so exactness demands an int literal.
        if isinstance(answer, float) and abs(answer) > 2**53:
            return Verdict("format", "large integer sent as float loses precision")
        ok = int(answer) == task.expected
        return Verdict("pass") if ok else Verdict("wrong", f"expected {task.expected}, got {int(answer)}")
    ok = math.isclose(float(answer), float(task.expected), rel_tol=task.rel_tol, abs_tol=0.0)
    return Verdict("pass") if ok else Verdict("wrong", f"expected {task.expected:.10g}, got {answer:.10g}")
