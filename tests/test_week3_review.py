from types import SimpleNamespace
from unittest.mock import Mock

from app.conversation import ChatSession
from app.evaluator import evaluate_player_analysis
from app.llm import ask_model
from app.prompts import (
    GAMEOPS_ANALYSIS_INSTRUCTIONS,
    build_player_analysis_prompt,
)
from app.report_schemas import GameOpsReport
from app.streaming_llm import stream_model
from app.structured_llm import generate_structured_report

from services import (
    count_players,
    get_high_level_players,
)


SERVER_ID = 3
MIN_LEVEL = 50


def get_stats():
    """Get verified statistics from the existing business layer."""
    total = count_players(SERVER_ID)

    high_level = len(
        get_high_level_players(
            SERVER_ID,
            MIN_LEVEL,
        )
    )

    return total, high_level


def get_prompt():
    """Build a real game operations analysis prompt."""
    total, high_level = get_stats()

    return build_player_analysis_prompt(
        server_id=SERVER_ID,
        total_players=total,
        high_level_players=high_level,
        min_level=MIN_LEVEL,
    )


def make_text_client(answer):
    client = Mock()

    client.responses.create.return_value = SimpleNamespace(
        output_text=answer,
    )

    return client


# 1. Business data is correct.
def test_week3_business_statistics():
    total, high_level = get_stats()

    assert total == 3
    assert high_level == 2

    percentage = high_level / total * 100

    assert round(percentage, 1) == 66.7


# 2. Prompt preserves business meaning.
def test_week3_prompt_contract():
    prompt = get_prompt()

    assert "server_id: 3" in prompt
    assert "total_players: 3" in prompt
    assert "min_level: 50" in prompt
    assert "high_level_players: 2" in prompt

    assert "高等级筛选阈值" in prompt
    assert "min_level" in GAMEOPS_ANALYSIS_INSTRUCTIONS


# 3. Normal LLM call receives real business input.
def test_week3_llm_request_contract():
    client = make_text_client("服务器3共有3名玩家。")

    prompt = get_prompt()

    answer = ask_model(
        prompt,
        client=client,
        instructions=GAMEOPS_ANALYSIS_INSTRUCTIONS,
    )

    assert answer == "服务器3共有3名玩家。"

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["input"] == prompt
    assert kwargs["instructions"] == GAMEOPS_ANALYSIS_INSTRUCTIONS
    assert kwargs["store"] is False


# 4. Multi-turn conversation carries earlier messages.
def test_week3_conversation_context():
    client = Mock()

    client.responses.create.side_effect = [
        SimpleNamespace(
            output_text="高等级玩家有2人。"
        ),
        SimpleNamespace(
            output_text="占比约66.7%。"
        ),
    ]

    session = ChatSession(client=client)

    session.ask("服务器3有3人，其中2人等级不低于50。")
    second_answer = session.ask("他们的占比是多少？")

    assert second_answer == "占比约66.7%。"

    calls = client.responses.create.call_args_list

    second_input = calls[1].kwargs["input"]

    assert len(second_input) == 3

    assert second_input[0]["role"] == "user"
    assert second_input[1]["role"] == "assistant"
    assert second_input[2]["role"] == "user"

    assert "等级不低于50" in second_input[0]["content"]
    assert "占比是多少" in second_input[2]["content"]

    assert len(session.get_history()) == 4


# 5. Structured output is a real Pydantic object.
def test_week3_structured_report_contract():
    expected = GameOpsReport(
        summary="服务器3共有3名玩家",
        observations=[
            "等级不低于50的玩家有2人，占比66.7%",
        ],
        limitations=[
            "没有历史活跃记录，无法计算留存率",
        ],
        needs_more_data=True,
    )

    client = Mock()

    client.responses.parse.return_value = SimpleNamespace(
        output_parsed=expected,
    )

    prompt = get_prompt()

    report = generate_structured_report(
        prompt,
        client=client,
    )

    assert isinstance(report, GameOpsReport)
    assert report.needs_more_data is True
    assert "3名玩家" in report.summary

    kwargs = client.responses.parse.call_args.kwargs

    assert kwargs["input"] == prompt
    assert kwargs["text_format"] is GameOpsReport


# 6. Streaming chunks form the expected complete text.
def test_week3_streaming_contract():
    class FakeStream:
        def __init__(self):
            self.closed = False

        def __iter__(self):
            return iter([
                SimpleNamespace(
                    type="response.output_text.delta",
                    delta="高等级玩家",
                ),
                SimpleNamespace(
                    type="response.output_text.delta",
                    delta="占比66.7%",
                ),
                SimpleNamespace(
                    type="response.completed",
                ),
            ])

        def close(self):
            self.closed = True

    client = Mock()
    fake_stream = FakeStream()

    client.responses.create.return_value = fake_stream

    chunks = list(
        stream_model(
            "分析玩家等级",
            client=client,
        )
    )

    assert chunks == [
        "高等级玩家",
        "占比66.7%",
    ]

    assert "".join(chunks) == "高等级玩家占比66.7%"
    assert fake_stream.closed is True

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["stream"] is True


# 7. Evaluation detects a historical semantic error.
def test_week3_evaluator_rejects_known_error():
    total, high_level = get_stats()

    wrong_answer = (
        "服务器最低等级为50级。"
        "所有玩家等级均不低于50级。"
        "具体等级门槛未提供。"
    )

    result = evaluate_player_analysis(
        wrong_answer,
        total_players=total,
        high_level_players=high_level,
        min_level=MIN_LEVEL,
    )

    assert result.passed is False
    assert result.score == 0.0
    assert len(result.issues) == 3


# 8. Integrated workflow:
# business data -> prompt -> mocked model -> evaluation.
def test_week3_end_to_end_offline():
    total, high_level = get_stats()
    prompt = get_prompt()

    correct_answer = (
        "服务器3共有3名模拟玩家。"
        "等级不低于50的玩家有2人，"
        "高等级玩家占比约66.7%。"
        "min_level=50表示筛选阈值，"
        "不能据此推断全体玩家的最低等级。"
        "缺少新增玩家和后续活跃事件，"
        "无法计算次日留存率。"
    )

    client = make_text_client(correct_answer)

    answer = ask_model(
        prompt,
        client=client,
        instructions=GAMEOPS_ANALYSIS_INSTRUCTIONS,
    )

    result = evaluate_player_analysis(
        answer,
        total_players=total,
        high_level_players=high_level,
        min_level=MIN_LEVEL,
    )

    assert result.passed is True
    assert result.score == 1.0
    assert result.issues == []

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["input"] == prompt