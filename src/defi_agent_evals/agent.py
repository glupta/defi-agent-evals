"""Run one task through Claude via the Claude Agent SDK, with or without a calculator tool."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

from defi_agent_evals.calc import CalcError, evaluate
from defi_agent_evals.tasks import INSUFFICIENT, Task

SYSTEM = f"""You are a DeFi analyst agent. Answer the question using only the JSON data given.
Return a single value in the 'answer' field: a JSON number (an integer literal when the question asks
for an integer amount), or the exact string "{INSUFFICIENT}" if any input the calculation needs is
missing from the data. Never guess a missing input. Report real-valued answers at full precision
(at least 10 significant digits); never round. Keep 'reasoning' to one or two sentences."""

TOOL_HINT = "\nUse the calc tool for every arithmetic step; do not compute in your head."

STRING_HINT = (
    "\nReturn 'answer' as a string: integer amounts as exact decimal digits (e.g. \"140289045591767637466929\"), "
    'real numbers in decimal or scientific notation (e.g. "-0.2862508900", "2.425294740e24").'
)

OUTPUT_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "answer": {"anyOf": [{"type": "number"}, {"type": "string", "enum": [INSUFFICIENT]}]},
            "reasoning": {"type": "string"},
        },
        "required": ["answer", "reasoning"],
        "additionalProperties": False,
    },
}


@tool(
    "calc",
    "Evaluate an arithmetic expression exactly (Python ints are arbitrary precision). "
    "Supports + - * / // % ** and sqrt, log, exp, abs, int, float.",
    {"expression": str},
)
async def calc_tool(args: dict[str, Any]) -> dict[str, Any]:
    try:
        value = evaluate(args["expression"])
    except CalcError as e:
        return {"content": [{"type": "text", "text": f"error: {e}"}], "is_error": True}
    return {"content": [{"type": "text", "text": repr(value)}]}


# v2 output contract: every number travels as a string, so uint256-scale amounts keep full precision.
OUTPUT_SCHEMA_V2 = {
    "type": "json_schema",
    "schema": {
        **OUTPUT_SCHEMA["schema"],
        "properties": {
            "answer": {
                "anyOf": [
                    {"type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?([eE][-+]?[0-9]+)?$"},
                    {"type": "string", "enum": [INSUFFICIENT]},
                ]
            },
            "reasoning": {"type": "string"},
        },
    },
}


def cli_path() -> str:
    return os.environ.get("CLAUDE_CLI", str(Path.home() / ".local/node/bin/claude"))


def options(model: str, condition: str) -> ClaudeAgentOptions:
    common = {
        "model": model,
        "cli_path": cli_path(),
        "output_format": OUTPUT_SCHEMA_V2 if condition == "calc_v2" else OUTPUT_SCHEMA,
        "setting_sources": [],  # isolate from the operator's own settings, hooks, and memory
        "permission_mode": "dontAsk",
        "max_turns": 12,
    }
    if condition == "bare":
        return ClaudeAgentOptions(system_prompt=SYSTEM, tools=[], **common)
    if condition in ("calc", "calc_v2"):
        server = create_sdk_mcp_server("defi", tools=[calc_tool])
        hint = TOOL_HINT + (STRING_HINT if condition == "calc_v2" else "")
        return ClaudeAgentOptions(
            system_prompt=SYSTEM + hint,
            tools=[],
            mcp_servers={"defi": server},
            allowed_tools=["mcp__defi__calc"],
            **common,
        )
    raise ValueError(f"unknown condition {condition!r}")


def prompt_for(task: Task) -> str:
    return f"Question: {task.question}\n\nData:\n{json.dumps(task.data, indent=2)}"


async def run_task(task: Task, model: str, condition: str) -> dict[str, Any]:
    result: ResultMessage | None = None
    tool_calls = 0
    async for msg in query(prompt=prompt_for(task), options=options(model, condition)):
        if isinstance(msg, ResultMessage):
            result = msg
        elif type(msg).__name__ == "AssistantMessage":
            tool_calls += sum(
                1
                for b in msg.content
                if type(b).__name__ == "ToolUseBlock" and b.name != "StructuredOutput"  # output channel, not a tool
            )
    if result is None:
        raise RuntimeError(f"{task.id}: no result message")
    return {
        "task": asdict(task),
        "model": model,
        "condition": condition,
        "output": result.structured_output,
        "raw_result": result.result,
        "is_error": result.is_error,
        "num_turns": result.num_turns,
        "tool_calls": tool_calls,
        "duration_ms": result.duration_ms,
    }
