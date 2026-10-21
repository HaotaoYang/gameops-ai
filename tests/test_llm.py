from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.llm import DEFAULT_MODEL, ask_model


def make_fake_client(answer: str):
    """Create a fake client that never makes network calls."""
    client = Mock()

    client.responses.create.return_value = SimpleNamespace(
        output_text=answer,
        usage=None,
    )

    return client


def test_ask_model_returns_text():
    client = make_fake_client("次日留存率是重要指标。")

    answer = ask_model(
        "什么是次日留存率？",
        client=client,
    )

    assert answer == "次日留存率是重要指标。"


def test_ask_model_passes_question():
    client = make_fake_client("回答内容")

    ask_model(
        "请分析玩家留存",
        client=client,
    )

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["input"] == "请分析玩家留存"
    assert "游戏运营分析助手" in kwargs["instructions"]


def test_ask_model_uses_default_model(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    client = make_fake_client("回答内容")

    ask_model("你好", client=client)

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["model"] == DEFAULT_MODEL


def test_ask_model_supports_model_override(monkeypatch):
    monkeypatch.setenv(
        "OPENAI_MODEL",
        "example-test-model",
    )

    client = make_fake_client("回答内容")

    ask_model("你好", client=client)

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["model"] == "example-test-model"


def test_ask_model_rejects_empty_question():
    client = make_fake_client("不应该返回")

    with pytest.raises(
        ValueError,
        match="问题不能为空",
    ):
        ask_model("   ", client=client)

    client.responses.create.assert_not_called()
