import asyncio

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock

from defi_agent_evals import agent
from defi_agent_evals.tasks import build_suite


def test_options_per_condition():
    assert agent.options("m", "bare").mcp_servers == {}
    calc = agent.options("m", "calc")
    assert calc.allowed_tools == ["mcp__defi__calc"]
    assert calc.setting_sources == []
    assert agent.options("m", "calc_v2").output_format is agent.OUTPUT_SCHEMA_V2
    with pytest.raises(ValueError):
        agent.options("m", "nope")


def test_run_task_counts_real_tool_calls_only(monkeypatch):
    task = build_suite()[0]

    async def fake_query(prompt, options):
        assert task.question in prompt
        yield AssistantMessage(
            content=[ToolUseBlock("1", "mcp__defi__calc", {}), ToolUseBlock("2", "StructuredOutput", {})],
            model="m",
        )
        yield ResultMessage("success", 5, 5, False, 2, "s", structured_output={"answer": "1", "reasoning": ""})

    monkeypatch.setattr(agent, "query", fake_query)
    row = asyncio.run(agent.run_task(task, "m", "calc_v2"))
    assert row["tool_calls"] == 1
    assert row["output"] == {"answer": "1", "reasoning": ""}


def test_run_task_without_result_raises(monkeypatch):
    async def empty(prompt, options):
        return
        yield

    monkeypatch.setattr(agent, "query", empty)
    with pytest.raises(RuntimeError):
        asyncio.run(agent.run_task(build_suite()[0], "m", "bare"))


def test_calc_tool_reports_errors():
    ok = asyncio.run(agent.calc_tool.handler({"expression": "2**10"}))
    bad = asyncio.run(agent.calc_tool.handler({"expression": "open('x')"}))
    assert ok["content"][0]["text"] == "1024"
    assert bad["is_error"] is True
