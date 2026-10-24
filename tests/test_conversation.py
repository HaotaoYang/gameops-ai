from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.conversation import ChatSession
from app.prompts import GAMEOPS_ANALYSIS_INSTRUCTIONS


def make_fake_client(*answers: str) -> Mock:
    client = Mock()

    client.responses.create.side_effect = [
        SimpleNamespace(output_text=answer)
        for answer in answers
    ]

    return client


def test_first_turn_sends_one_user_message():
    client = make_fake_client("第一轮回答")
    session = ChatSession(client=client)

    answer = session.ask("请分析服务器3")

    assert answer == "第一轮回答"

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["input"] == [
        {
            "role": "user",
            "content": "请分析服务器3",
        }
    ]

    assert (
        kwargs["instructions"]
        == GAMEOPS_ANALYSIS_INSTRUCTIONS
    )

    assert kwargs["store"] is False


def test_second_turn_contains_history():
    client = make_fake_client(
        "高等级玩家有2人。",
        "占比约66.7%。",
    )

    session = ChatSession(client=client)

    session.ask("高等级玩家有几人？")
    session.ask("他们的占比是多少？")

    calls = client.responses.create.call_args_list

    assert len(calls) == 2

    second_input = calls[1].kwargs["input"]

    assert second_input == [
        {
            "role": "user",
            "content": "高等级玩家有几人？",
        },
        {
            "role": "assistant",
            "content": "高等级玩家有2人。",
        },
        {
            "role": "user",
            "content": "他们的占比是多少？",
        },
    ]

    assert len(session.get_history()) == 4


def test_sessions_are_isolated():
    client_a = make_fake_client("A的回答")
    client_b = make_fake_client("B的回答")

    session_a = ChatSession(client=client_a)
    session_b = ChatSession(client=client_b)

    session_a.ask("问题A")
    session_b.ask("问题B")

    assert session_a.get_history() == [
        {"role": "user", "content": "问题A"},
        {"role": "assistant", "content": "A的回答"},
    ]

    assert session_b.get_history() == [
        {"role": "user", "content": "问题B"},
        {"role": "assistant", "content": "B的回答"},
    ]


def test_failed_request_does_not_change_history():
    client = Mock()

    client.responses.create.side_effect = RuntimeError(
        "模拟API故障"
    )

    session = ChatSession(client=client)

    with pytest.raises(
        RuntimeError,
        match="模拟API故障",
    ):
        session.ask("分析玩家数据")

    assert session.get_history() == []


def test_blank_question_is_rejected():
    client = Mock()
    session = ChatSession(client=client)

    with pytest.raises(
        ValueError,
        match="问题不能为空",
    ):
        session.ask("   ")

    client.responses.create.assert_not_called()
    assert session.get_history() == []


def test_history_copy_and_clear():
    client = make_fake_client("模型回答")
    session = ChatSession(client=client)

    session.ask("你好")

    history = session.get_history()
    history[0]["content"] = "外部修改"

    assert session.get_history()[0]["content"] == "你好"

    session.clear()

    assert session.get_history() == []