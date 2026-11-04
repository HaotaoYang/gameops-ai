import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.multi_agent import run_multi_agent
from app.multi_tools import MULTI_TOOLS, execute_routed_tool


def fake_call(
    name: str,
    args: dict,
    call_id: str,
):
    arguments = json.dumps(args)

    return SimpleNamespace(
        type="function_call",
        name=name,
        arguments=arguments,
        call_id=call_id,
        model_dump=lambda exclude_none=True: {
            "type": "function_call",
            "name": name,
            "arguments": arguments,
            "call_id": call_id,
        },
    )


def tool_response(call):
    return SimpleNamespace(
        output=[call],
        output_text="",
    )


def final_response(answer: str):
    return SimpleNamespace(
        output=[],
        output_text=answer,
    )


def fake_client(*responses):
    client = Mock()
    client.responses.create.side_effect = list(responses)
    return client


# 1. All tools have strict schemas.
def test_multi_tool_schema():
    names = {
        tool["name"]
        for tool in MULTI_TOOLS
    }

    assert names == {
        "count_players",
        "get_high_level_players",
        "get_active_players",
    }

    for tool in MULTI_TOOLS:
        assert tool["strict"] is True

        params = tool["parameters"]
        assert params["additionalProperties"] is False
        assert set(params["properties"]) == set(
            params["required"]
        )


# 2. Count players using the existing service.
def test_count_players_tool():
    result = json.loads(
        execute_routed_tool(
            "count_players",
            '{"server_id":3}',
        )
    )

    assert result["server_id"] == 3
    assert result["total_players"] == 3


# 3. Reuse the previous high-level player tool.
def test_high_level_tool_reused():
    result = json.loads(
        execute_routed_tool(
            "get_high_level_players",
            '{"server_id":3,"min_level":50}',
        )
    )

    assert result["high_level_count"] == 2

    names = {
        player["name"]
        for player in result["players"]
    }

    assert names == {"Alice", "David"}


# 4. Last-login-date matching returns Bob and David.
def test_last_login_tool():
    result = json.loads(
        execute_routed_tool(
            "get_active_players",
            '{"server_id":3,"login_date":"2026-10-14"}',
        )
    )

    assert result["matched_last_login_count"] == 2

    names = {
        player["name"]
        for player in result["players"]
    }

    assert names == {"Bob", "David"}
    assert "历史DAU" in result["note"]


# 5. Reject unknown tools.
def test_unknown_tool_rejected():
    with pytest.raises(
        ValueError,
        match="不允许调用的工具",
    ):
        execute_routed_tool(
            "delete_all_players",
            "{}",
        )


# 6. Reject invalid arguments and calendar dates.
def test_invalid_tool_arguments():
    with pytest.raises(ValidationError):
        execute_routed_tool(
            "count_players",
            '{"server_id":-1}',
        )

    with pytest.raises(ValidationError):
        execute_routed_tool(
            "count_players",
            '{"server_id":"3"}',
        )

    with pytest.raises(ValueError):
        execute_routed_tool(
            "get_active_players",
            '{"server_id":3,"login_date":"2026-02-30"}',
        )


# 7. Agent routes to the count tool.
def test_agent_routes_to_count_tool():
    client = fake_client(
        tool_response(
            fake_call(
                "count_players",
                {"server_id": 3},
                "call_count",
            )
        ),
        final_response("3服共有3名玩家。"),
    )

    executed = []

    answer = run_multi_agent(
        "3服有多少玩家？",
        client=client,
        on_tool_call=executed.append,
    )

    assert answer == "3服共有3名玩家。"
    assert executed == ["count_players"]

    calls = client.responses.create.call_args_list

    assert calls[0].kwargs["tool_choice"] == "required"

    outputs = [
        item
        for item in calls[1].kwargs["input"]
        if item.get("type") == "function_call_output"
    ]

    assert len(outputs) == 1
    assert outputs[0]["call_id"] == "call_count"

    result = json.loads(outputs[0]["output"])

    assert result["total_players"] == 3


# 8. Agent handles two sequential tool calls.
def test_agent_calls_two_tools_in_sequence():
    client = fake_client(
        tool_response(
            fake_call(
                "count_players",
                {"server_id": 3},
                "call_1",
            )
        ),
        tool_response(
            fake_call(
                "get_high_level_players",
                {
                    "server_id": 3,
                    "min_level": 50,
                },
                "call_2",
            )
        ),
        final_response(
            "3服共有3人，其中2人等级不低于50。"
        ),
    )

    executed = []

    answer = run_multi_agent(
        "3服有多少人，等级不低于50的有多少？",
        client=client,
        on_tool_call=executed.append,
    )

    assert "3服共有3人" in answer

    assert executed == [
        "count_players",
        "get_high_level_players",
    ]

    calls = client.responses.create.call_args_list

    assert len(calls) == 3

    assert calls[0].kwargs["tool_choice"] == "required"
    assert calls[1].kwargs["tool_choice"] == "auto"

    final_input = calls[2].kwargs["input"]

    outputs = [
        item
        for item in final_input
        if item.get("type") == "function_call_output"
    ]

    assert len(outputs) == 2
    assert [item["call_id"] for item in outputs] == [
        "call_1",
        "call_2",
    ]

    second_result = json.loads(outputs[1]["output"])

    assert second_result["high_level_count"] == 2


# 9. Reject a missing required first tool call.
def test_first_turn_must_call_tool():
    client = fake_client(
        final_response("我猜服务器有3个人。"),
    )

    with pytest.raises(
        RuntimeError,
        match="首轮没有产生必须的工具调用",
    ):
        run_multi_agent(
            "查询服务器人数",
            client=client,
        )

    assert client.responses.create.call_count == 1


# 10. Enforce the tool-round limit.
def test_max_tool_rounds():
    client = fake_client(
        tool_response(
            fake_call(
                "count_players",
                {"server_id": 3},
                "call_1",
            )
        ),
        tool_response(
            fake_call(
                "count_players",
                {"server_id": 3},
                "call_2",
            )
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="达到工具调用轮数上限",
    ):
        run_multi_agent(
            "查询服务器人数",
            client=client,
            max_tool_rounds=1,
        )

    calls = client.responses.create.call_args_list

    assert len(calls) == 2
    assert calls[1].kwargs["tool_choice"] == "none"