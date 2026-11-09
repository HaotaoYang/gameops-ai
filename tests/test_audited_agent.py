import json
from types import SimpleNamespace
from unittest.mock import Mock

from app.audited_agent import run_audited_agent
from app.multi_tools import execute_routed_tool


GOOD_ANSWER = (
    "3服共有3名玩家，"
    "等级不低于50的有2名。"
)


def fake_call(name, arguments, call_id):
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


def make_good_client(answer=GOOD_ANSWER):
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


def run_test_agent(client, **kwargs):
    return run_audited_agent(
        "查询3服总人数和等级不低于50的玩家",
        server_id=3,
        min_level=50,
        client=client,
        **kwargs,
    )


# 1. All required facts are checked and published.
def test_successful_audited_report():
    client = make_good_client()

    result = run_test_agent(client)

    assert result.status == "approved"
    assert result.approved is True

    assert result.trusted_facts == {
        "total_players": 3,
        "high_level_count": 2,
        "min_level": 50,
    }

    assert result.agent_result.status == "completed"
    assert result.agent_result.tool_calls == 2

    assert "3服共有3名玩家" in result.answer
    assert "| Alice | 50 |" in result.answer
    assert "| David | 60 |" in result.answer

    assert client.responses.create.call_count == 3


# 2. Wrong model-reported total must be rejected.
def test_wrong_total_is_rejected():
    client = make_good_client(
        "3服共有5名玩家，"
        "等级不低于50的有2名。"
    )

    result = run_test_agent(client)

    assert result.status == "rejected"
    assert result.answer is None
    assert (
        "玩家总人数与工具结果不一致"
        in result.issues
    )


# 3. Wrong model-reported high-level count is rejected.
def test_wrong_high_count_is_rejected():
    client = make_good_client(
        "3服共有3名玩家，"
        "等级不低于50的有4名。"
    )

    result = run_test_agent(client)

    assert result.status == "rejected"
    assert result.answer is None
    assert (
        "高等级玩家人数与工具结果不一致"
        in result.issues
    )


# 4. The total-count tool is mandatory.
def test_missing_total_tool_is_rejected():
    client = make_client(
        tool_response(
            "get_high_level_players",
            {
                "server_id": 3,
                "min_level": 50,
            },
            "call_high",
        ),
        final_response(GOOD_ANSWER),
    )

    result = run_test_agent(client)

    assert result.status == "rejected"
    assert result.answer is None

    assert any(
        "count_players" in issue
        for issue in result.issues
    )


# 5. The high-level player tool is mandatory.
def test_missing_high_level_tool_is_rejected():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_count",
        ),
        final_response(GOOD_ANSWER),
    )

    result = run_test_agent(client)

    assert result.status == "rejected"

    assert any(
        "get_high_level_players" in issue
        for issue in result.issues
    )


# 6. A request for the wrong server is not executed.
def test_wrong_server_is_blocked_before_execution():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 5},
            "call_wrong",
        ),
        final_response(GOOD_ANSWER),
    )

    executor = Mock(wraps=execute_routed_tool)

    result = run_test_agent(
        client,
        business_executor=executor,
    )

    assert result.status == "rejected"
    assert result.answer is None

    executor.assert_not_called()

    assert result.agent_result.events[0].status == (
        "invalid_arguments"
    )


# 7. A request for the wrong threshold is not executed.
def test_wrong_threshold_is_blocked():
    client = make_client(
        tool_response(
            "get_high_level_players",
            {
                "server_id": 3,
                "min_level": 60,
            },
            "call_wrong",
        ),
        final_response(GOOD_ANSWER),
    )

    executor = Mock(wraps=execute_routed_tool)

    result = run_test_agent(
        client,
        business_executor=executor,
    )

    assert result.status == "rejected"

    executor.assert_not_called()


# 8. An inconsistent tool result must be rejected.
def test_inconsistent_player_count_is_rejected():
    def inconsistent_executor(name, arguments_json):
        raw = execute_routed_tool(
            name,
            arguments_json,
        )

        data = json.loads(raw)

        if name == "get_high_level_players":
            # Lie about count without adding another player.
            data["high_level_count"] = 3

        return json.dumps(
            data,
            ensure_ascii=False,
        )

    client = make_good_client()

    result = run_test_agent(
        client,
        business_executor=inconsistent_executor,
    )

    assert result.status == "rejected"
    assert result.answer is None

    assert "工具统计结果存在不一致" in result.issues


# 9. Failed business tools cannot produce approved reports.
def test_execution_failure_is_not_approved():
    def broken_executor(name, arguments_json):
        raise RuntimeError("internal-secret-host")

    client = make_client(
        tool_response(
            "count_players",
            {"server_id": 3},
            "call_count",
        ),
        final_response(GOOD_ANSWER),
    )

    result = run_test_agent(
        client,
        business_executor=broken_executor,
    )

    assert result.status == "rejected"
    assert result.answer is None

    assert any(
        "工具执行过程中出现失败" in issue
        for issue in result.issues
    )

    assert "internal-secret-host" not in str(
        result.issues
    )


# 10. Model request failure cannot be approved.
def test_model_failure_is_not_approved():
    client = Mock()

    client.responses.create.side_effect = RuntimeError(
        "private-model-error"
    )

    result = run_test_agent(client)

    assert result.status == "failed"
    assert result.answer is None
    assert result.approved is False

    assert result.agent_result.error_code == (
        "MODEL_REQUEST_FAILED"
    )

    assert "private-model-error" not in str(
        result.issues
    )