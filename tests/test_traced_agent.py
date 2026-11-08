import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.agent_state import AgentState
from app.traced_agent import run_traced_agent


def fake_call(name, arguments, call_id):
    if isinstance(arguments, dict):
        arguments = json.dumps(arguments)

    data = {
        "type": "function_call",
        "name": name,
        "arguments": arguments,
        "call_id": call_id,
    }

    item = SimpleNamespace(**data)

    item.model_dump = (
        lambda exclude_none=True: data.copy()
    )

    return item


def tool_response(name, arguments, call_id):
    return SimpleNamespace(
        output=[
            fake_call(name, arguments, call_id)
        ],
        output_text="",
    )


def final_response(answer):
    return SimpleNamespace(
        output=[],
        output_text=answer,
    )


def make_client(*responses):
    client = Mock()
    client.responses.create.side_effect = list(responses)
    return client


# 1. State instances must not share lists or sets.
def test_agent_states_are_isolated():
    a = AgentState()
    b = AgentState()

    a.add_event(
        kind="tool",
        status="success",
        tool_name="count_players",
    )

    a.seen_calls.add(
        ("count_players", '{"server_id":3}')
    )

    assert len(a.events) == 1
    assert b.events == []
    assert b.seen_calls == set()
    assert a.status == "running"
    assert b.status == "running"


# 2. A successful two-tool run has a complete trace.
def test_successful_two_tool_run():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_1",
        ),
        tool_response(
            "get_high_level_players",
            {"server_id": 3, "min_level": 50},
            "call_2",
        ),
        final_response(
            "3服有3人，其中高等级玩家2人。"
        ),
    )

    result = run_traced_agent(
        "查询3服总人数和高等级人数",
        client=client,
    )

    assert result.succeeded is True
    assert result.status == "completed"
    assert result.tool_calls == 2
    assert result.error_code is None

    assert [e.step for e in result.events] == [
        1, 2, 3,
    ]

    assert [e.status for e in result.events] == [
        "success",
        "success",
        "completed",
    ]

    assert result.events[0].tool_name == "count_players"
    assert (
        result.events[1].tool_name
        == "get_high_level_players"
    )


# 3. Invalid arguments are recorded and may be corrected.
def test_invalid_arguments_then_recovery():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": -3},
            "bad_call",
        ),
        tool_response(
            "count_players",
            {"server_id": 3},
            "good_call",
        ),
        final_response("3服共有3名玩家。"),
    )

    result = run_traced_agent(
        "查询3服人数",
        client=client,
    )

    assert result.status == "completed"
    assert result.tool_calls == 2

    assert result.events[0].status == "invalid_arguments"
    assert (
        result.events[0].error_code
        == "INVALID_ARGUMENTS"
    )

    assert result.events[1].status == "success"
    assert result.events[2].status == "completed"

    second_input = (
        client.responses.create.call_args_list[1]
        .kwargs["input"]
    )

    outputs = [
        item
        for item in second_input
        if item.get("type") == "function_call_output"
    ]

    assert outputs[0]["call_id"] == "bad_call"

    error = json.loads(outputs[0]["output"])

    assert error["ok"] is False


# 4. Tool failures are recorded without leaking secrets.
def test_execution_failure_is_sanitized():
    def broken_executor(name, arguments):
        raise RuntimeError(
            "internal-secret-database-host"
        )

    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_1",
        ),
        final_response("当前无法获取数据。"),
    )

    result = run_traced_agent(
        "查询人数",
        client=client,
        tool_executor=broken_executor,
    )

    assert result.status == "completed"
    assert result.tool_calls == 1

    assert result.events[0].status == "execution_failed"
    assert (
        result.events[0].error_code
        == "TOOL_EXECUTION_FAILED"
    )

    trace_text = str(result.events)

    assert "internal-secret-database-host" not in trace_text

    second_input = (
        client.responses.create.call_args_list[1]
        .kwargs["input"]
    )

    output = [
        item
        for item in second_input
        if item.get("type") == "function_call_output"
    ][0]

    assert (
        "internal-secret-database-host"
        not in output["output"]
    )


# 5. Unknown tools must not execute.
def test_unknown_tool_fails_safely():
    client = make_client(
        tool_response(
            "delete_all_players",
            {},
            "call_bad",
        ),
    )

    executor = Mock()

    result = run_traced_agent(
        "删除玩家",
        client=client,
        tool_executor=executor,
    )

    assert result.status == "failed"
    assert result.error_code == "UNAUTHORIZED_TOOL"
    assert result.tool_calls == 0

    executor.assert_not_called()


# 6. Duplicate calls are blocked even if JSON order changes.
def test_duplicate_call_is_blocked():
    client = make_client(
        tool_response(
            "get_high_level_players",
            {"server_id": 3, "min_level": 50},
            "call_1",
        ),
        tool_response(
            "get_high_level_players",
            {"min_level": 50, "server_id": 3},
            "call_2",
        ),
    )

    result = run_traced_agent(
        "查询高等级玩家",
        client=client,
    )

    assert result.status == "failed"
    assert result.error_code == "DUPLICATE_TOOL_CALL"
    assert result.tool_calls == 1

    assert result.events[-1].status == "failed"


# 7. Tool call limit must be enforced.
def test_tool_limit_is_recorded():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_1",
        ),
        tool_response(
            "get_high_level_players",
            {"server_id": 3, "min_level": 50},
            "call_2",
        ),
    )

    result = run_traced_agent(
        "查询服务器玩家情况",
        client=client,
        max_tool_calls=1,
    )

    assert result.status == "failed"
    assert result.error_code == "TOOL_LIMIT_REACHED"
    assert result.tool_calls == 1

    calls = client.responses.create.call_args_list

    assert len(calls) == 2
    assert calls[1].kwargs["tool_choice"] == "none"


# 8. The first turn must contain a tool call.
def test_first_turn_without_tool_is_failed():
    client = make_client(
        final_response("我猜服务器有3个人。"),
    )

    result = run_traced_agent(
        "查询3服人数",
        client=client,
    )

    assert result.status == "failed"
    assert result.error_code == "FIRST_TOOL_REQUIRED"
    assert result.tool_calls == 0
    assert result.answer is None


# 9. Model request errors become terminal safe failures.
def test_model_request_failure_is_recorded():
    client = Mock()

    client.responses.create.side_effect = RuntimeError(
        "private-api-error-detail"
    )

    result = run_traced_agent(
        "查询人数",
        client=client,
    )

    assert result.status == "failed"
    assert result.error_code == "MODEL_REQUEST_FAILED"
    assert result.tool_calls == 0

    assert "private-api-error-detail" not in str(
        result.events
    )


# 10. Reject invalid entry parameters before model calls.
def test_invalid_entry_parameters():
    client = Mock()

    with pytest.raises(
        ValueError,
        match="问题不能为空",
    ):
        run_traced_agent(
            "   ",
            client=client,
        )

    with pytest.raises(
        ValueError,
        match="max_tool_calls必须在1到5之间",
    ):
        run_traced_agent(
            "查询人数",
            client=client,
            max_tool_calls=0,
        )

    client.responses.create.assert_not_called()