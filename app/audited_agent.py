import json

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from openai import OpenAI

from app.agent_state import AgentRunResult
from app.answer_guard import validate_answer
from app.multi_tools import execute_routed_tool
from app.traced_agent import run_traced_agent


AuditStatus = Literal[
    "approved",
    "rejected",
    "failed",
]


@dataclass(frozen=True)
class AuditedAgentResult:
    status: AuditStatus
    answer: str | None
    issues: tuple[str, ...]
    trusted_facts: dict
    agent_result: AgentRunResult

    @property
    def approved(self) -> bool:
        return self.status == "approved"


def render_report(
    server_id: int,
    min_level: int,
    total: int,
    players: list[dict],
) -> str:
    """Generate an authoritative report using Python."""

    lines = [
        (
            f"{server_id}服共有{total}名玩家，"
            f"等级不低于{min_level}的有{len(players)}名。"
        ),
        "",
        "| 玩家名字 | 等级 |",
        "|---|---:|",
    ]

    for player in players:
        # Escape basic Markdown characters in player names.
        name = (
            player["name"]
            .replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("\n", " ")
            .replace("\r", " ")
        )

        lines.append(
            f"| {name} | {player['level']} |"
        )

    return "\n".join(lines)


def run_audited_agent(
    question: str,
    *,
    server_id: int,
    min_level: int,
    client: OpenAI | None = None,
    max_tool_calls: int = 3,
    business_executor: Callable[[str, str], str] = (
        execute_routed_tool
    ),
) -> AuditedAgentResult:
    """
    Require the correct tools and facts before publishing
    a deterministic player report.
    """

    if not question.strip():
        raise ValueError("问题不能为空")

    if type(server_id) is not int or server_id < 1:
        raise ValueError("server_id必须是正整数")

    if type(min_level) is not int or min_level < 0:
        raise ValueError("min_level必须是非负整数")

    # Only successful executions are recorded here.
    records: dict[str, dict] = {}

    required_tools = {
        "count_players",
        "get_high_level_players",
    }

    def checked_executor(
        name: str,
        arguments_json: str,
    ) -> str:
        """Enforce the requested scope before execution."""

        if name not in required_tools:
            raise RuntimeError(
                "当前任务不允许调用此工具"
            )

        arguments = json.loads(arguments_json)

        if not isinstance(arguments, dict):
            raise ValueError("工具参数必须是JSON对象")

        if (
            type(arguments.get("server_id")) is not int
            or arguments["server_id"] != server_id
        ):
            raise ValueError("工具服务器与任务不一致")

        if name == "get_high_level_players":
            if (
                type(arguments.get("min_level")) is not int
                or arguments["min_level"] != min_level
            ):
                raise ValueError("等级门槛与任务不一致")

        # Execute only after checking the task's scope.
        raw_result = business_executor(
            name,
            arguments_json,
        )

        data = json.loads(raw_result)

        if not isinstance(data, dict):
            raise RuntimeError("业务工具结果格式错误")

        records[name] = data

        return raw_result

    # Reuse Day 25's state tracking and Day 24's safety.
    run = run_traced_agent(
        question,
        client=client,
        max_tool_calls=max_tool_calls,
        tool_executor=checked_executor,
    )

    def finish(
        status: AuditStatus,
        issues: list[str],
        *,
        answer: str | None = None,
        facts: dict | None = None,
    ) -> AuditedAgentResult:
        return AuditedAgentResult(
            status=status,
            answer=answer,
            issues=tuple(issues),
            trusted_facts=(
                {} if facts is None else facts.copy()
            ),
            agent_result=run,
        )

    # First, verify the agent execution itself.
    if run.status != "completed" or run.answer is None:
        return finish(
            "failed",
            [f"Agent执行失败：{run.error_code}"],
        )

    # A completed model response does not erase tool failures.
    if any(
        event.kind == "tool"
        and event.status != "success"
        for event in run.events
    ):
        return finish(
            "rejected",
            ["工具执行过程中出现失败"],
        )

    # Both business tools are required.
    missing = required_tools - set(records)

    if missing:
        return finish(
            "rejected",
            [
                f"缺少必需工具结果：{name}"
                for name in sorted(missing)
            ],
        )

    count_data = records["count_players"]
    high_data = records["get_high_level_players"]

    # Validate the actual results, not just the call arguments.
    if (
        count_data.get("server_id") != server_id
        or high_data.get("server_id") != server_id
        or high_data.get("min_level") != min_level
    ):
        return finish(
            "rejected",
            ["工具返回的数据范围不符合任务要求"],
        )

    total = count_data.get("total_players")
    high = high_data.get("high_level_count")
    players = high_data.get("players")

    if (
        type(total) is not int
        or type(high) is not int
        or total < 0
        or high < 0
        or high > total
        or not isinstance(players, list)
        or len(players) != high
    ):
        return finish(
            "rejected",
            ["工具统计结果存在不一致"],
        )

    # Verify every player record returned by the tool.
    seen_ids = set()

    for player in players:
        if not isinstance(player, dict):
            return finish(
                "rejected",
                ["玩家记录格式不正确"],
            )

        name = player.get("name")
        level = player.get("level")
        player_id = player.get("player_id")

        if (
            not isinstance(name, str)
            or not name.strip()
            or type(level) is not int
            or level < min_level
        ):
            return finish(
                "rejected",
                ["玩家姓名或等级数据不合法"],
            )

        if (
            "server_id" in player
            and player["server_id"] != server_id
        ):
            return finish(
                "rejected",
                ["玩家所在服务器与任务不一致"],
            )

        if player_id is not None:
            if player_id in seen_ids:
                return finish(
                    "rejected",
                    ["玩家列表存在重复ID"],
                )

            seen_ids.add(player_id)

    facts = {
        "total_players": total,
        "high_level_count": high,
        "min_level": min_level,
    }

    # Continue using Day 26's known-fact checks.
    issues = validate_answer(
        run.answer,
        facts,
    )

    if issues:
        return finish(
            "rejected",
            issues,
            facts=facts,
        )

    # Important: the public answer is generated by Python.
    # It does not copy unverified player claims from the LLM.
    report = render_report(
        server_id,
        min_level,
        total,
        players,
    )

    return finish(
        "approved",
        [],
        answer=report,
        facts=facts,
    )