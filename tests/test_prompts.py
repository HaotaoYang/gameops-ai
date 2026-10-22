from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.llm import (
    DEFAULT_INSTRUCTIONS,
    ask_model,
)
from app.prompts import (
    GAMEOPS_ANALYSIS_INSTRUCTIONS,
    build_player_analysis_prompt,
)
from services import count_players, get_high_level_players


def make_fake_client(answer: str) -> Mock:
    client = Mock()

    client.responses.create.return_value = SimpleNamespace(
        output_text=answer
    )

    return client


def test_default_instructions_still_work():
    """Day 15's behavior remains compatible."""
    client = make_fake_client("正常回答")

    answer = ask_model(
        "解释次日留存率",
        client=client,
    )

    assert answer == "正常回答"

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["instructions"] == DEFAULT_INSTRUCTIONS
    assert kwargs["input"] == "解释次日留存率"


def test_custom_instructions_are_passed():
    """Custom instructions must reach the Responses API."""
    client = make_fake_client("分析完成")

    answer = ask_model(
        "分析服务器3",
        client=client,
        instructions=GAMEOPS_ANALYSIS_INSTRUCTIONS,
    )

    assert answer == "分析完成"

    kwargs = client.responses.create.call_args.kwargs

    assert kwargs["instructions"] == GAMEOPS_ANALYSIS_INSTRUCTIONS
    assert kwargs["input"] == "分析服务器3"


def test_reject_blank_custom_instructions():
    """Blank explicit instructions should be rejected."""
    client = make_fake_client("不应调用")

    with pytest.raises(
        ValueError,
        match="instructions不能为空",
    ):
        ask_model(
            "分析玩家",
            client=client,
            instructions="   ",
        )

    client.responses.create.assert_not_called()


def test_prompt_uses_existing_game_data():
    """Statistics must come from existing service functions."""
    total = count_players(3)
    high_level = len(get_high_level_players(3, 50))

    prompt = build_player_analysis_prompt(
        server_id=3,
        total_players=total,
        high_level_players=high_level,
        min_level=50,
    )

    assert total == 3
    assert high_level == 2

    assert "server_id: 3" in prompt
    assert "total_players: 3" in prompt
    assert "min_level: 50" in prompt
    assert "high_level_players: 2" in prompt


def test_prompt_rejects_inconsistent_stats():
    """High-level count cannot exceed total count."""
    with pytest.raises(
        ValueError,
        match="高等级玩家数不能超过总玩家数",
    ):
        build_player_analysis_prompt(
            server_id=3,
            total_players=3,
            high_level_players=5,
            min_level=50,
        )


def test_prompt_documents_missing_data_boundary():
    """Instructions must address unsupported claims."""
    instructions = GAMEOPS_ANALYSIS_INSTRUCTIONS

    assert "数据不足" in instructions
    assert "不编造" in instructions
    assert "历史DAU" in instructions
    assert "已知事实" in instructions