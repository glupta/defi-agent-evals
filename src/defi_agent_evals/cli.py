"""CLI: `dae run` executes the suite against Claude; `dae report` grades saved runs into a table."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from defi_agent_evals.tasks import Task, build_suite
from defi_agent_evals.verify import VERDICTS, grade


def _write_atomic(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    os.replace(tmp, path)


async def _run(args: argparse.Namespace) -> tuple[list[dict], int]:
    from defi_agent_evals.agent import (
        run_task,  # SDK import only when a model run is requested
    )

    tasks = build_suite(seed=args.seed)
    if args.limit:
        tasks = tasks[: args.limit]
    sem = asyncio.Semaphore(args.concurrency)
    failures = 0

    async def one(t: Task) -> dict:
        nonlocal failures
        async with sem:
            try:
                return await run_task(t, args.model, args.condition)
            except Exception as e:  # noqa: BLE001 record the failed run and keep the suite going
                failures += 1
                print(f"{t.id}: run failed: {e}", file=sys.stderr)
                return {"task": {"id": t.id}, "model": args.model, "condition": args.condition, "error": str(e)}

    rows = await asyncio.gather(*(one(t) for t in tasks))
    return list(rows), failures


def report(paths: list[Path], seed: int) -> str:
    suite = {t.id: t for t in build_suite(seed=seed)}
    table: dict[tuple[str, str], Counter] = defaultdict(Counter)
    by_domain: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
    for p in paths:
        for line in p.read_text().splitlines():
            r = json.loads(line)
            key = (r["model"], r["condition"])
            task = suite[r["task"]["id"]]
            v = "run_error" if "error" in r else grade(task, r.get("output")).verdict
            table[key][v] += 1
            dom = "missing_data" if task.match == "refuse" else task.domain
            by_domain[(*key, dom)][v] += 1
    cols = [*VERDICTS, "run_error"]
    lines = ["| model | condition | pass rate | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 3)]
    for (model, cond), c in sorted(table.items()):
        n = sum(c.values())
        lines.append(
            f"| {model} | {cond} | {c['pass']}/{n} ({c['pass'] / n:.0%}) | "
            + " | ".join(str(c[v]) for v in cols)
            + " |"
        )
    lines += ["", "| model | condition | domain | pass |", "|---|---|---|---|"]
    for (model, cond, dom), c in sorted(by_domain.items()):
        lines.append(f"| {model} | {cond} | {dom} | {c['pass']}/{sum(c.values())} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(prog="dae")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--model", required=True)
    r.add_argument("--condition", choices=["bare", "calc", "calc_v2"], required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--seed", type=int, default=7)
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--concurrency", type=int, default=4)
    rep = sub.add_parser("report")
    rep.add_argument("paths", nargs="+", type=Path)
    rep.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    if args.cmd == "run":
        rows, failures = asyncio.run(_run(args))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(out, rows)
        print(f"wrote {len(rows)} runs to {out} ({failures} run failures)")
        sys.exit(1 if failures else 0)
    print(report(args.paths, args.seed))
