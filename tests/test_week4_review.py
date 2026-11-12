import json
from types import SimpleNamespace
from unittest.mock import Mock

from app.audited_agent import run_audited_agent
from app.multi_tools import MULTI_TOOLS, execute_routed_tool
from app.tool_results import execute_safely


GOOD_ANSWER = (
    "3服共有3名玩家，"
    "等级不低于50的有2名。"
)


def fake_call(name, arguments, call_id):
    """Simulate a model-generated function call."""

    arguments_json = json.dumps(arguments)

    data = {
        "type": "function_call",
        "name": name,
        "arguments": arguments_json,
        "call_id": call_id,
    }

    item = SimpleNamespace(**data)

    item.model_dump = (
        lambda exclude_none=True: data.copy()
    )

    return item


def tool_response(name, arguments, call_id):
    """Simulate a Responses API tool-call response."""

    return SimpleNamespace(
        output=[
            fake_call(name, arguments, call_id)
        ],
        output_text="",
    )


def final_response(answer):
    """Simulate the model's final text response."""

    return SimpleNamespace(
        output=[],
        output_text=answer,
    )


def make_client(*responses):
    client = Mock()
    client.responses.create.side_effect = list(responses)
    return client


def make_success_client(answer=GOOD_ANSWER):
    """Simulate the full two-tool workflow."""

    return make_client(
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_count",
        ),
        tool_response(
            "get_high_level_players",
            {
                "server_id": 3,
                "min_level": 50,
            },
            "call_high",
        ),
        final_response(answer),
    )


def run_review(client, **kwargs):
    return run_audited_agent(
        "查询3服总人数和等级不低于50的玩家",
        server_id=3,
        min_level=50,
        client=client,
        **kwargs,
    )


# 1. Day 22-23: all expected tools are registered.
def test_week4_tool_registration():
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
        assert (
            tool["parameters"]["additionalProperties"]
            is False
        )


# 2. Tools return the correct source-of-truth data.
def test_week4_business_facts():
    count_result = json.loads(
        execute_routed_tool(
            "count_players",
            '{"server_id":3}',
        )
    )

    high_result = json.loads(
        execute_routed_tool(
            "get_high_level_players",
            '{"server_id":3,"min_level":50}',
        )
    )

    assert count_result["total_players"] == 3
    assert high_result["high_level_count"] == 2

    players = high_result["players"]

    assert {
        player["name"]: player["level"]
        for player in players
    } == {
        "Alice": 50,
        "David": 60,
    }


# 3. Day 24: invalid arguments are safely classified.
def test_week4_safe_error_protocol():
    result_json, status = execute_safely(
        "count_players",
        '{"server_id":-3}',
    )

    data = json.loads(result_json)

    assert status == "invalid_arguments"
    assert data["ok"] is False
    assert (
        data["error"]["code"]
        == "INVALID_ARGUMENTS"
    )


# 4. Day 25-27: successful end-to-end mock workflow.
def test_week4_complete_agent_workflow():
    client = make_success_client()

    result = run_review(client)

    assert result.agent_result.status == "completed"
    assert result.agent_result.tool_calls == 2

    assert result.status == "approved"
    assert result.approved is True

    assert result.trusted_facts == {
        "total_players": 3,
        "high_level_count": 2,
        "min_level": 50,
    }

    assert result.answer is not None
    assert "3服共有3名玩家" in result.answer
    assert "| Alice | 50 |" in result.answer
    assert "| David | 60 |" in result.answer


# 5. Tool call IDs, state and trace remain consistent.
def test_week4_trace_and_call_ids():
    client = make_success_client()

    result = run_review(client)

    events = result.agent_result.events

    assert [e.step for e in events] == [1, 2, 3]

    assert [e.status for e in events] == [
        "success",
        "success",
        "completed",
    ]

    assert events[0].tool_name == "count_players"
    assert (
        events[1].tool_name
        == "get_high_level_players"
    )

    calls = client.responses.create.call_args_list

    assert len(calls) == 3

    final_input = calls[2].kwargs["input"]

    tool_outputs = [
        item
        for item in final_input
        if item.get("type") == "function_call_output"
    ]

    assert [
        item["call_id"]
        for item in tool_outputs
    ] == [
        "call_count",
        "call_high",
    ]

    assert calls[0].kwargs["tool_choice"] == "required"
    assert calls[1].kwargs["tool_choice"] == "auto"


# 6. Missing business evidence cannot be approved.
def test_week4_missing_required_tool():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_count",
        ),
        final_response(GOOD_ANSWER),
    )

    result = run_review(client)

    assert result.agent_result.status == "completed"
    assert result.status == "rejected"
    assert result.answer is None

    assert any(
        "get_high_level_players" in issue
        for issue in result.issues
    )


# 7. Wrong business scope must be blocked before execution.
def test_week4_wrong_server_blocked():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 5},
            "call_wrong",
        ),
        final_response(GOOD_ANSWER),
    )

    executor = Mock(wraps=execute_routed_tool)

    result = run_review(
        client,
        business_executor=executor,
    )

    assert result.status == "rejected"
    assert result.answer is None

    executor.assert_not_called()

    assert (
        result.agent_result.events[0].status
        == "invalid_arguments"
    )


# 8. Corrupted player levels must not be published.
def test_week4_invalid_player_record_blocked():
    def corrupted_executor(name, arguments_json):
        raw = execute_routed_tool(
            name,
            arguments_json,
        )

        data = json.loads(raw)

        if name == "get_high_level_players":
            data["players"][0]["level"] = 20

        return json.dumps(
            data,
            ensure_ascii=False,
        )

    client = make_success_client()

    result = run_review(
        client,
        business_executor=corrupted_executor,
    )

    assert result.status == "rejected"
    assert result.answer is None

    assert (
        "玩家姓名或等级数据不合法"
        in result.issues
    )


# 9. Day 24-25: duplicate calls stop the agent.
def test_week4_duplicate_call_protection():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_1",
        ),
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_2",
        ),
    )

    result = run_review(client)

    assert result.status == "failed"
    assert result.approved is False
    assert result.answer is None

    assert (
        result.agent_result.error_code
        == "DUPLICATE_TOOL_CALL"
    )

    assert result.agent_result.tool_calls == 1


# 10. Model failures are sanitized and never approved.
def test_week4_model_failure_blocked():
    client = Mock()

    client.responses.create.side_effect = RuntimeError(
        "internal-secret-model-error"
    )

    result = run_review(client)

    assert result.status == "failed"
    assert result.approved is False
    assert result.answer is None

    assert (
        result.agent_result.error_code
        == "MODEL_REQUEST_FAILED"
    )

    assert (
        "internal-secret-model-error"
        not in str(result.issues)
    )

    assert (
        "internal-secret-model-error"
        not in str(result.agent_result.events)
    )