import json
import re

from dataclasses import dataclass
from typing import Literal

from openai import OpenAI

from app.agent_state import AgentRunResult
from app.evaluator import evaluate_player_analysis
from app.multi_tools import execute_routed_tool
from app.traced_agent import run_traced_agent


GuardStatus = Literal[
    "approved",
    "rejected",
    "failed",
]


@dataclass(frozen=True)
class GuardedAgentResult:
    status: GuardStatus
    answer: str | None
    issues: tuple[str, ...]
    trusted_facts: dict
    agent_result: AgentRunResult

    @property
    def approved(self) -> bool:
        return self.status == "approved"


def normalize_answer(text: str) -> str:
    """Remove simple formatting used in model responses."""

    return re.sub(r"[\s*_`]", "", text)


def validate_answer(
    answer: str,
    facts: dict,
) -> list[str]:
    """Check supported numerical claims and known semantic errors."""

    issues: list[str] = []

    if not answer.strip():
        return ["模型回答为空"]

    normalized = normalize_answer(answer)

    total = facts.get("total_players")
    high = facts.get("high_level_count")
    threshold = facts.get("min_level")

    # Validate the total-player statement when known.
    if total is not None:
        total_matches = re.findall(
            r"(?:\d+服|服务器\d+)"
            r".{0,12}?"
            r"(?:共有|总共|玩家总数(?:为|是|[:：])?"
            r"|总人数(?:为|是|[:：])?)"
            r".{0,8}?(\d+)(?:名|人)",
            normalized,
        )

        if not total_matches:
            issues.append("回答缺少可识别的玩家总人数")
        elif any(int(n) != total for n in total_matches):
            issues.append("玩家总人数与工具结果不一致")

    # Validate high-level player counts when known.
    if high is not None and threshold is not None:
        pattern = (
            rf"(?:等级(?:不低于|大于等于|>=|≥)"
            rf"{threshold}(?:级)?(?:的)?(?:玩家)?"
            rf"|高等级玩家)"
            rf".{{0,12}}?"
            rf"(?:有|共|为|[:：])?"
            rf"(\d+)(?:名|人)"
        )

        high_matches = re.findall(pattern, normalized)

        if not high_matches:
            issues.append("回答缺少可识别的高等级玩家人数")
        elif any(int(n) != high for n in high_matches):
            issues.append("高等级玩家人数与工具结果不一致")

    # Reuse the known-error evaluator from Day 20.
    if (
        total is not None
        and high is not None
        and threshold is not None
    ):
        evaluation = evaluate_player_analysis(
            answer,
            total_players=total,
            high_level_players=high,
            min_level=threshold,
        )

        issues.extend(evaluation.issues)

    return issues


def run_guarded_agent(
    question: str,
    client: OpenAI | None = None,
    *,
    max_tool_calls: int = 3,
) -> GuardedAgentResult:
    """Run the traced agent and validate its final business answer."""

    tool_records: list[tuple[str, dict]] = []

    def recording_executor(
        name: str,
        arguments_json: str,
    ) -> str:
        # Execute the actual authorized business tool.
        result_json = execute_routed_tool(
            name,
            arguments_json,
        )

        data = json.loads(result_json)

        if not isinstance(data, dict):
            raise RuntimeError(
                "工具没有返回JSON对象"
            )

        # Store only successful tool results.
        tool_records.append((name, data))

        return result_json

    run = run_traced_agent(
        question,
        client=client,
        max_tool_calls=max_tool_calls,
        tool_executor=recording_executor,
    )

    facts: dict = {}

    for name, data in tool_records:
        if name == "count_players":
            facts["total_players"] = data["total_players"]

        elif name == "get_high_level_players":
            facts["high_level_count"] = data[
                "high_level_count"
            ]
            facts["min_level"] = data["min_level"]

    # The agent itself failed.
    if run.status != "completed" or run.answer is None:
        return GuardedAgentResult(
            status="failed",
            answer=None,
            issues=(
                f"Agent执行失败：{run.error_code}",
            ),
            trusted_facts=facts.copy(),
            agent_result=run,
        )

    # A tool may have failed even if the model produced text.
    if any(
        event.kind == "tool"
        and event.status != "success"
        for event in run.events
    ):
        return GuardedAgentResult(
            status="rejected",
            answer=None,
            issues=("工具执行过程中出现失败，结果未获完整验证",),
            trusted_facts=facts.copy(),
            agent_result=run,
        )

    # No verified facts means no approved business report.
    if not facts:
        return GuardedAgentResult(
            status="rejected",
            answer=None,
            issues=("没有取得可用于验证的业务事实",),
            trusted_facts={},
            agent_result=run,
        )

    issues = validate_answer(
        run.answer,
        facts,
    )

    if issues:
        return GuardedAgentResult(
            status="rejected",
            answer=None,
            issues=tuple(issues),
            trusted_facts=facts.copy(),
            agent_result=run,
        )

    return GuardedAgentResult(
        status="approved",
        answer=run.answer,
        issues=(),
        trusted_facts=facts.copy(),
        agent_result=run,
    )