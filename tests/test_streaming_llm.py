from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.llm import DEFAULT_INSTRUCTIONS
from app.streaming_llm import stream_model


def event(event_type: str, delta: str = ""):
    return SimpleNamespace(
        type=event_type,
        delta=delta,
    )


class FakeStream:
    """A minimal fake of the SDK's response stream."""

    def __init__(self, events):
        self.events = events
        self.closed = False

    def __iter__(self):
        return iter(self.events)

    def close(self):
        self.closed = True


def make_fake_client(*events):
    client = Mock()
    stream = FakeStream(events)

    client.responses.create.return_value = stream

    return client, stream


def test_stream_yields_text_deltas():
    client, stream = make_fake_client(
        event("response.created"),
        event("response.output_text.delta", "你好"),
        event("response.output_text.delta", "，世界"),
        event("response.completed"),
    )

    chunks = list(
        stream_model("打个招呼", client=client)
    )

    assert chunks == ["你好", "，世界"]
    assert "".join(chunks) == "你好，世界"
    assert stream.closed is True


def test_stream_passes_correct_api_parameters():
    client, _ = make_fake_client(
        event("response.output_text.delta", "正常"),
        event("response.completed"),
    )

    list(stream_model("测试问题", client=client))

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["input"] == "测试问题"
    assert kwargs["stream"] is True
    assert kwargs["store"] is False
    assert kwargs["instructions"] == DEFAULT_INSTRUCTIONS


def test_stream_supports_custom_instructions():
    client, _ = make_fake_client(
        event("response.output_text.delta", "回答"),
        event("response.completed"),
    )

    list(
        stream_model(
            "分析玩家",
            client=client,
            instructions="只根据给出的数据回答",
        )
    )

    kwargs = client.responses.create.call_args.kwargs

    assert (
        kwargs["instructions"]
        == "只根据给出的数据回答"
    )


def test_stream_ignores_non_text_events():
    client, _ = make_fake_client(
        event("response.created"),
        event("response.output_text.delta", "结果"),
        event("response.output_text.done"),
        event("response.completed"),
    )

    chunks = list(
        stream_model("测试", client=client)
    )

    assert chunks == ["结果"]


def test_failed_stream_raises_and_closes():
    client, stream = make_fake_client(
        event("response.output_text.delta", "部分回答"),
        event("response.failed"),
    )

    with pytest.raises(
        RuntimeError,
        match="模型流式响应失败",
    ):
        list(stream_model("测试", client=client))

    assert stream.closed is True


def test_incomplete_stream_raises():
    client, stream = make_fake_client(
        event("response.output_text.delta", "未完成"),
        event("response.incomplete"),
    )

    with pytest.raises(
        RuntimeError,
        match="未完整完成",
    ):
        list(stream_model("测试", client=client))

    assert stream.closed is True


def test_missing_completion_event_raises():
    client, stream = make_fake_client(
        event("response.output_text.delta", "只有部分内容"),
    )

    with pytest.raises(
        RuntimeError,
        match="未收到完成事件",
    ):
        list(stream_model("测试", client=client))

    assert stream.closed is True


def test_empty_question_does_not_call_api():
    client, _ = make_fake_client()

    with pytest.raises(
        ValueError,
        match="问题不能为空",
    ):
        list(stream_model("   ", client=client))

    client.responses.create.assert_not_called()