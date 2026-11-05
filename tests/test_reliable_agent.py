import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.reliable_agent import run_reliable_agent
from app.tool_results import execute_safely


def fake_call(name, arguments, call_id):
    """Create a fake Responses API function_call item."""

    if isinstance(arguments, dict):
        arguments = json.dumps(arguments)

    data = {
        "type": "function_call",
        "name": name,
        "arguments": arguments,
        "call_id": call_id,
    }

    item = SimpleNamespace(
        **data,
    )

    item.model_dump = lambda exclude_none=True: data.copy()

    return item


def tool_response(name, arguments, call_id):
    return SimpleNamespace(
        output=[
            fake_call(
                name,
                arguments,
                call_id,
            )
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


# 1. Safe execution returns a successful result.
def test_safe_tool_success():
    result_json, status = execute_safely(
        "count_players",
        '{"server_id":3}',
    )

    result = json.loads(result_json)

    assert status == "success"
    assert result["ok"] is True
    assert result["data"]["total_players"] == 3


# 2. Invalid arguments are converted into a safe error.
def test_invalid_arguments_return_safe_error():
    result_json, status = execute_safely(
        "count_players",
        '{"server_id":-3}',
    )

    result = json.loads(result_json)

    assert status == "invalid_arguments"
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ARGUMENTS"


# 3. Malformed JSON is handled safely.
def test_malformed_json_returns_error():
    result_json, status = execute_safely(
        "count_players",
        '{"server_id":',
    )

    result = json.loads(result_json)

    assert status == "invalid_arguments"
    assert result["error"]["code"] == "INVALID_ARGUMENTS"


# 4. Unexpected tool failure must not leak exception details.
def test_tool_execution_failure_is_sanitized():
    def broken_executor(name, arguments):
        raise RuntimeError("internal-secret-db-host")

    result_json, status = execute_safely(
        "count_players",
        '{"server_id":3}',
        executor=broken_executor,
    )

    result = json.loads(result_json)

    assert status == "execution_failed"
    assert result["error"]["code"] == "TOOL_EXECUTION_FAILED"
    assert "internal-secret-db-host" not in result_json


# 5. An unknown tool is never executed.
def test_unknown_tool_is_rejected():
    executor = Mock()

    with pytest.raises(
        ValueError,
        match="不允许调用的工具",
    ):
        execute_safely(
            "delete_all_players",
            "{}",
            executor=executor,
        )

    executor.assert_not_called()


# 6. Model can correct invalid arguments on a later turn.
def test_agent_recovers_after_invalid_arguments():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": -3},
            "call_bad",
        ),
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_good",
        ),
        final_response("服务器3共有3名玩家。"),
    )

    events = []

    answer = run_reliable_agent(
        "请查询3服玩家总数",
        client=client,
        on_tool_event=lambda name, status: events.append(
            (name, status)
        ),
    )

    assert answer == "服务器3共有3名玩家。"

    assert events == [
        ("count_players", "invalid_arguments"),
        ("count_players", "success"),
    ]

    calls = client.responses.create.call_args_list

    assert len(calls) == 3

    # The first error is returned to the model.
    second_input = calls[1].kwargs["input"]

    outputs = [
        item
        for item in second_input
        if item.get("type") == "function_call_output"
    ]

    first_result = json.loads(outputs[0]["output"])

    assert outputs[0]["call_id"] == "call_bad"
    assert first_result["ok"] is False
    assert (
        first_result["error"]["code"]
        == "INVALID_ARGUMENTS"
    )


# 7. Duplicate calls with reordered JSON keys are rejected.
def test_duplicate_tool_call_is_stopped():
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

    events = []

    with pytest.raises(
        RuntimeError,
        match="重复工具调用",
    ):
        run_reliable_agent(
            "查询3服高等级玩家",
            client=client,
            on_tool_event=lambda name, status: events.append(
                (name, status)
            ),
        )

    assert events == [
        ("get_high_level_players", "success"),
    ]


# 8. Tool calls beyond the limit are not executed.
def test_tool_call_limit_is_enforced():
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

    events = []

    with pytest.raises(
        RuntimeError,
        match="达到工具调用次数上限",
    ):
        run_reliable_agent(
            "查询玩家数据",
            client=client,
            max_tool_calls=1,
            on_tool_event=lambda name, status: events.append(
                (name, status)
            ),
        )

    assert events == [("count_players", "success")]

    calls = client.responses.create.call_args_list

    assert len(calls) == 2
    assert calls[1].kwargs["tool_choice"] == "none"


# 9. The first model response must contain a tool call.
def test_first_turn_requires_tool():
    client = make_client(
        final_response("我猜服务器有3个人。"),
    )

    with pytest.raises(
        RuntimeError,
        match="首轮没有产生必须的工具调用",
    ):
        run_reliable_agent(
            "查询服务器人数",
            client=client,
        )


# 10. Two different tools can still be used sequentially.
def test_two_tool_calls_still_work():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_count",
        ),
        tool_response(
            "get_high_level_players",
            {"server_id": 3, "min_level": 50},
            "call_high",
        ),
        final_response(
            "3服共有3人，其中等级不低于50的有2人。"
        ),
    )

    events = []

    answer = run_reliable_agent(
        "3服有多少人？高等级有多少人？",
        client=client,
        on_tool_event=lambda name, status: events.append(
            (name, status)
        ),
    )

    assert "等级不低于50的有2人" in answer

    assert events == [
        ("count_players", "success"),
        ("get_high_level_players", "success"),
    ]

    calls = client.responses.create.call_args_list

    assert len(calls) == 3

    final_input = calls[2].kwargs["input"]

    outputs = [
        item
        for item in final_input
        if item.get("type") == "function_call_output"
    ]

    assert len(outputs) == 2

    assert [item["call_id"] for item in outputs] == [
        "call_count",
        "call_high",
    ]

    first_result = json.loads(outputs[0]["output"])
    second_result = json.loads(outputs[1]["output"])

    assert first_result["data"]["total_players"] == 3
    assert second_result["data"]["high_level_count"] == 2