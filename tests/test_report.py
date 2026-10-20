import json

from defi_agent_evals.cli import report
from defi_agent_evals.tasks import build_suite


def test_report_counts_verdicts_and_run_errors(tmp_path):
    suite = build_suite(seed=7)
    exact = next(t for t in suite if t.match == "exact")
    refuse = next(t for t in suite if t.match == "refuse")
    rows = [
        {"task": {"id": exact.id}, "model": "m", "condition": "calc", "output": {"answer": exact.expected}},
        {"task": {"id": refuse.id}, "model": "m", "condition": "calc", "output": {"answer": 3}},
        {"task": {"id": exact.id}, "model": "m", "condition": "calc", "error": "boom"},
    ]
    p = tmp_path / "r.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    out = report([p], seed=7)
    assert "| m | calc | 1/3 (33%) | 1 | 0 | 0 | 0 | 1 | 1 |" in out
    assert "| m | calc | missing_data | 0/1 |" in out
