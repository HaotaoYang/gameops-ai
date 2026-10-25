from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.prompts import build_player_analysis_prompt
from app.report_schemas import GameOpsReport
from app.structured_llm import (
    STRUCTURED_REPORT_INSTRUCTIONS,
    generate_structured_report,
)
from services import count_players, get_high_level_players


def sample_report() -> GameOpsReport:
    return GameOpsReport(
        summary="服务器3共有3名玩家",
        observations=[
            "等级不低于50的玩家有2人",
        ],
        limitations=[
            "无法根据当前数据计算留存率",
        ],
        needs_more_data=True,
    )


def make_fake_client(report: GameOpsReport | None) -> Mock:
    client = Mock()

    client.responses.parse.return_value = SimpleNamespace(
        output_parsed=report
    )

    return client


def test_report_schema_accepts_valid_data():
    report = sample_report()

    assert report.summary == "服务器3共有3名玩家"
    assert len(report.observations) == 1
    assert report.needs_more_data is True


def test_report_schema_rejects_extra_fields():
    with pytest.raises(ValidationError):
        GameOpsReport.model_validate({
            "summary": "正常",
            "observations": [],
            "limitations": [],
            "needs_more_data": True,
            "unknown_field": 123,
        })


def test_structured_api_receives_schema_and_prompt():
    client = make_fake_client(sample_report())

    report = generate_structured_report(
        "请分析服务器3",
        client=client,
    )

    assert isinstance(report, GameOpsReport)

    kwargs = client.responses.parse.call_args.kwargs

    assert kwargs["input"] == "请分析服务器3"
    assert kwargs["text_format"] is GameOpsReport
    assert (
        kwargs["instructions"]
        == STRUCTURED_REPORT_INSTRUCTIONS
    )
    assert kwargs["store"] is False


def test_structured_report_uses_real_service_statistics():
    total = count_players(3)
    high_level = len(get_high_level_players(3, 50))

    question = build_player_analysis_prompt(
        server_id=3,
        total_players=total,
        high_level_players=high_level,
        min_level=50,
    )

    client = make_fake_client(sample_report())

    generate_structured_report(
        question,
        client=client,
    )

    kwargs = client.responses.parse.call_args.kwargs

    assert total == 3
    assert high_level == 2
    assert "total_players: 3" in kwargs["input"]
    assert "high_level_players: 2" in kwargs["input"]


def test_none_parsed_response_raises_error():
    client = make_fake_client(None)

    with pytest.raises(
        ValueError,
        match="没有返回可用的结构化报告",
    ):
        generate_structured_report(
            "请分析玩家",
            client=client,
        )


def test_empty_question_does_not_call_api():
    client = make_fake_client(sample_report())

    with pytest.raises(
        ValueError,
        match="问题不能为空",
    ):
        generate_structured_report(
            "   ",
            client=client,
        )

    client.responses.parse.assert_not_called()