"""List non-passing runs with grader detail: uv run python scripts/failures.py results/x.jsonl"""

import json
import sys
from pathlib import Path

from defi_agent_evals.tasks import build_suite
from defi_agent_evals.verify import grade

suite = {t.id: t for t in build_suite(seed=7)}
for line in Path(sys.argv[1]).read_text().splitlines():
    r = json.loads(line)
    if "error" in r:
        print(r["task"]["id"], "run_error", r["error"][:100])
        continue
    v = grade(suite[r["task"]["id"]], r.get("output"))
    if not v.passed:
        print(r["task"]["id"], v.verdict, v.detail[:110], "| tools:", r.get("tool_calls"))
