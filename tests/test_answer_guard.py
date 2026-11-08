import json
from types import SimpleNamespace
from unittest.mock import Mock

from app.answer_guard import (
    run_guarded_agent,
    validate_answer,
)


FACTS = {
    "total_players": 3,
    "high_level_count": 2,
    "min_level": 50,
}


def fake_call(name, arguments, call_id):
    """Simulate a Responses API function_call."""

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


def make_two_tool_client(answer):
    """Return a client with two tools followed by an answer."""

    return make_client(
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
        final_response(answer),
    )


# 1. Correct numerical facts are accepted.
def test_correct_answer_passes():
    answer = (
        "3服共有3名玩家，"
        "等级不低于50的有2名。"
    )

    issues = validate_answer(answer, FACTS)

    assert issues == []


# 2. Markdown formatting does not break count extraction.
def test_markdown_numbers_pass():
    answer = (
        "3服共有 **3名玩家**，"
        "等级不低于50级的有 **2名**。"
    )

    issues = validate_answer(answer, FACTS)

    assert issues == []


# 3. Wrong total-player count is rejected.
def test_wrong_total_is_detected():
    answer = (
        "3服共有5名玩家，"
        "等级不低于50的有2名。"
    )

    issues = validate_answer(answer, FACTS)

    assert "玩家总人数与工具结果不一致" in issues


# 4. Wrong high-level player count is rejected.
def test_wrong_high_level_count_is_detected():
    answer = (
        "3服共有3名玩家，"
        "等级不低于50的有4名。"
    )

    issues = validate_answer(answer, FACTS)

    assert "高等级玩家人数与工具结果不一致" in issues


# 5. Reuse Day 20's known semantic-error detection.
def test_min_level_semantic_error_is_detected():
    answer = (
        "3服共有3名玩家，"
        "等级不低于50的有2名。"
        "服务器最低等级为50级。"
    )

    issues = validate_answer(answer, FACTS)

    assert (
        "将min_level误认为全体玩家的最低等级"
        in issues
    )


# 6. Missing required numerical claims are not approved.
def test_missing_total_is_detected():
    answer = (
        "等级不低于50的有2名。"
    )

    issues = validate_answer(answer, FACTS)

    assert "回答缺少可识别的玩家总人数" in issues


# 7. Full guarded flow approves supported correct facts.
def test_guarded_agent_approves_correct_answer():
    client = make_two_tool_client(
        "3服共有3名玩家，"
        "等级不低于50的有2名。"
    )

    result = run_guarded_agent(
        "查询3服总人数和高等级人数",
        client=client,
    )

    assert result.status == "approved"
    assert result.approved is True
    assert result.answer is not None
    assert result.issues == ()

    assert result.trusted_facts == FACTS

    assert result.agent_result.status == "completed"
    assert result.agent_result.tool_calls == 2

    assert client.responses.create.call_count == 3


# 8. Agent completed, but wrong answer must be blocked.
def test_guarded_agent_rejects_wrong_answer():
    client = make_two_tool_client(
        "3服共有5名玩家，"
        "等级不低于50的有2名。"
    )

    result = run_guarded_agent(
        "查询3服总人数和高等级人数",
        client=client,
    )

    assert result.agent_result.status == "completed"

    assert result.status == "rejected"
    assert result.approved is False
    assert result.answer is None

    assert (
        "玩家总人数与工具结果不一致"
        in result.issues
    )


# 9. A failed tool cannot produce an approved report.
def test_failed_tool_blocks_approval():
    client = make_client(
        tool_response(
            "count_players",
            {"server_id": -3},
            "bad_call",
        ),
        final_response("3服共有3名玩家。"),
    )

    result = run_guarded_agent(
        "查询3服人数",
        client=client,
    )

    # The model may complete after a tool error,
    # but the business answer is not approved.
    assert result.agent_result.status == "completed"

    assert result.status == "rejected"
    assert result.approved is False
    assert result.answer is None

    assert any(
        "工具执行过程中出现失败" in issue
        for issue in result.issues
    )


# 10. Model-request failure is never approved.
def test_model_failure_is_not_approved():
    client = Mock()

    client.responses.create.side_effect = RuntimeError(
        "internal-model-error"
    )

    result = run_guarded_agent(
        "查询3服人数",
        client=client,
    )

    assert result.status == "failed"
    assert result.approved is False
    assert result.answer is None
    assert result.agent_result.status == "failed"

    assert (
        result.agent_result.error_code
        == "MODEL_REQUEST_FAILED"
    )

    assert "internal-model-error" not in str(
        result.issues
    )