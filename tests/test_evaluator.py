import pytest

from app.evaluator import evaluate_player_analysis
from app.prompts import (
    GAMEOPS_ANALYSIS_INSTRUCTIONS,
    build_player_analysis_prompt,
)
from services import count_players, get_high_level_players


STATS = {
    "total_players": 3,
    "high_level_players": 2,
    "min_level": 50,
}


def check(text: str):
    return evaluate_player_analysis(text, **STATS)


def test_correct_analysis_passes():
    result = check(
        "服务器共有3人，等级不低于50的有2人，"
        "占比约66.7%。无法根据这些数据计算留存率。"
    )

    assert result.passed is True
    assert result.score == 1.0
    assert result.issues == []


def test_wrong_minimum_level_is_detected():
    result = check(
        "服务器最低等级：50级。"
    )

    assert result.passed is False
    assert (
        "将min_level误认为全体玩家的最低等级"
        in result.issues
    )


def test_wrong_all_players_claim_is_detected():
    result = check(
        "所有玩家等级均不低于50级。"
    )

    assert result.passed is False
    assert (
        "错误声称所有玩家都达到高等级门槛"
        in result.issues
    )


def test_missing_threshold_claim_is_detected():
    result = check(
        "未提供高等级玩家的等级判定标准。"
    )

    assert result.passed is False
    assert (
        "错误声称未提供高等级判定标准"
        in result.issues
    )


def test_day19_multiple_errors_are_detected():
    result = check(
        "最低等级：50级。"
        "所有玩家等级均不低于50级。"
        "具体等级门槛未提供。"
    )

    assert result.passed is False
    assert len(result.issues) == 3


def test_all_players_claim_can_be_true():
    result = evaluate_player_analysis(
        "所有玩家等级均不低于50级。",
        total_players=3,
        high_level_players=3,
        min_level=50,
    )

    assert result.passed is True


def test_invalid_statistics_are_rejected():
    with pytest.raises(
        ValueError,
        match="高等级人数必须在0到总人数之间",
    ):
        evaluate_player_analysis(
            "正常回答",
            total_players=3,
            high_level_players=5,
            min_level=50,
        )


def test_prompt_contains_explicit_field_semantics():
    total = count_players(3)
    high_level = len(
        get_high_level_players(3, 50)
    )

    prompt = build_player_analysis_prompt(
        server_id=3,
        total_players=total,
        high_level_players=high_level,
        min_level=50,
    )

    assert total == 3
    assert high_level == 2

    assert "min_level: 50" in prompt
    assert "high_level_players: 2" in prompt
    assert "高等级筛选阈值" in prompt

    assert (
        "min_level是高等级筛选阈值"
        in GAMEOPS_ANALYSIS_INSTRUCTIONS
    )