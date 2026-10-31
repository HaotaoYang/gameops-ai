import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.agent import run_agent
from app.tools import TOOLS, execute_tool


def fake_tool_call(
    arguments='{"server_id":3,"min_level":50}',
    name="get_high_level_players",
):
    return SimpleNamespace(
        type="function_call",
        name=name,
        arguments=arguments,
        call_id="call_test_001",
        model_dump=lambda exclude_none=True: {
            "type": "function_call",
            "name": name,
            "arguments": arguments,
            "call_id": "call_test_001",
        },
    )


def make_fake_client(
    tool_call=None,
    final_answer="符合条件的玩家有2人。",
):
    client = Mock()

    call = (
        fake_tool_call()
        if tool_call is None
        else tool_call
    )

    client.responses.create.side_effect = [
        SimpleNamespace(
            output=[call],
        ),
        SimpleNamespace(
            output_text=final_answer,
        ),
    ]

    return client


def test_tool_schema_is_strict():
    tool = TOOLS[0]

    assert tool["name"] == "get_high_level_players"
    assert tool["strict"] is True

    parameters = tool["parameters"]

    assert parameters["additionalProperties"] is False
    assert set(parameters["required"]) == {
        "server_id",
        "min_level",
    }


def test_execute_tool_returns_real_players():
    result = json.loads(
        execute_tool(
            "get_high_level_players",
            '{"server_id":3,"min_level":50}',
        )
    )

    assert result["server_id"] == 3
    assert result["min_level"] == 50
    assert result["high_level_count"] == 2

    names = {
        player["name"]
        for player in result["players"]
    }

    assert names == {"Alice", "David"}


def test_reject_unknown_tool():
    with pytest.raises(
        ValueError,
        match="不允许调用的工具",
    ):
        execute_tool(
            "delete_all_players",
            '{"server_id":3,"min_level":50}',
        )


def test_reject_invalid_arguments():
    with pytest.raises(ValidationError):
        execute_tool(
            "get_high_level_players",
            '{"server_id":-1,"min_level":50}',
        )


def test_reject_extra_arguments():
    with pytest.raises(ValidationError):
        execute_tool(
            "get_high_level_players",
            '{"server_id":3,"min_level":50,"admin":true}',
        )


def test_agent_returns_final_answer():
    client = make_fake_client(
        final_answer="Alice和David，共2人。"
    )

    answer = run_agent(
        "查询3服等级不低于50的玩家",
        client=client,
    )

    assert answer == "Alice和David，共2人。"
    assert client.responses.create.call_count == 2


def test_agent_returns_tool_result_to_model():
    client = make_fake_client()

    run_agent(
        "查询3服等级不低于50的玩家",
        client=client,
    )

    calls = client.responses.create.call_args_list

    first_kwargs = calls[0].kwargs
    second_kwargs = calls[1].kwargs

    assert first_kwargs["tool_choice"] == "required"
    assert first_kwargs["parallel_tool_calls"] is False

    assert second_kwargs["tool_choice"] == "none"

    tool_outputs = [
        item
        for item in second_kwargs["input"]
        if item.get("type") == "function_call_output"
    ]

    assert len(tool_outputs) == 1

    output = tool_outputs[0]

    assert output["call_id"] == "call_test_001"

    tool_result = json.loads(output["output"])

    assert tool_result["high_level_count"] == 2
    assert len(tool_result["players"]) == 2


def test_agent_does_not_execute_unknown_tool():
    client = make_fake_client(
        tool_call=fake_tool_call(
            name="delete_all_players"
        )
    )

    with pytest.raises(
        ValueError,
        match="不允许调用的工具",
    ):
        run_agent("删除所有玩家", client=client)

    assert client.responses.create.call_count == 1