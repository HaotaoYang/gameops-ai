import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationResult:
    passed: bool
    score: float
    issues: list[str]


def evaluate_player_analysis(
    text: str,
    *,
    total_players: int,
    high_level_players: int,
    min_level: int,
) -> EvaluationResult:
    """Detect known semantic mistakes in player analysis."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("待评测文本不能为空")

    if total_players < 0:
        raise ValueError("总玩家数不能为负数")

    if not 0 <= high_level_players <= total_players:
        raise ValueError("高等级人数必须在0到总人数之间")

    if min_level < 0:
        raise ValueError("高等级筛选阈值不能为负数")

    issues: list[str] = []

    # Normalize whitespace for simpler matching.
    normalized = re.sub(r"\s+", "", text)
    threshold = re.escape(str(min_level))

    # Rule 1: Treating the threshold as everybody's minimum level.
    wrong_minimum = (
        rf"最低等级(?:为|是|[:：])?{threshold}(?:级)?"
    )

    if re.search(wrong_minimum, normalized):
        issues.append(
            "将min_level误认为全体玩家的最低等级"
        )

    # Rule 2: Claiming all players meet the threshold.
    # This is false whenever some players are below the threshold.
    if high_level_players < total_players:
        wrong_all_players = (
            rf"所有玩家(?:的)?等级(?:均|都)?"
            rf"(?:不低于|大于等于|>=|≥){threshold}"
        )

        if re.search(wrong_all_players, normalized):
            issues.append(
                "错误声称所有玩家都达到高等级门槛"
            )

    # Rule 3: Claiming the supplied threshold was missing.
    missing_threshold_patterns = [
        r"(?:未提供|没有提供|缺少).{0,32}"
        r"(?:判定标准|等级门槛)",
        r"(?:等级门槛|判定标准).{0,8}"
        r"(?:未提供|不明确)",
    ]

    for pattern in missing_threshold_patterns:
        if re.search(pattern, normalized):
            issues.append(
                "错误声称未提供高等级判定标准"
            )
            break

    passed = len(issues) == 0

    return EvaluationResult(
        passed=passed,
        score=1.0 if passed else 0.0,
        issues=issues,
    )