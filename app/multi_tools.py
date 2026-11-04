import json
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.tools import TOOLS, execute_tool
from services import count_players, get_active_players


class CountPlayersArgs(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    server_id: int = Field(ge=1)


class ActivePlayersArgs(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    server_id: int = Field(ge=1)
    login_date: str = Field(
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )


MULTI_TOOLS = [
    *TOOLS,
    {
        "type": "function",
        "name": "count_players",
        "description": (
            "查询指定服务器的模拟玩家总人数。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "integer",
                    "description": "服务器ID",
                },
            },
            "required": ["server_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_active_players",
        "description": (
            "查询最后登录日期等于指定日期的模拟玩家。"
            "该工具不提供历史DAU或留存率。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "integer",
                    "description": "服务器ID",
                },
                "login_date": {
                    "type": "string",
                    "description": (
                        "最后登录日期，格式YYYY-MM-DD"
                    ),
                },
            },
            "required": [
                "server_id",
                "login_date",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def execute_routed_tool(
    name: str,
    arguments_json: str,
) -> str:
    """Execute one explicitly permitted read-only tool."""

    # Reuse the Day 22 tool instead of duplicating it.
    if name == "get_high_level_players":
        return execute_tool(
            name,
            arguments_json,
        )

    if name not in {
        "count_players",
        "get_active_players",
    }:
        raise ValueError(
            f"不允许调用的工具：{name}"
        )

    raw = json.loads(arguments_json)

    if name == "count_players":
        args = CountPlayersArgs.model_validate(raw)

        result = {
            "server_id": args.server_id,
            "total_players": count_players(args.server_id),
        }

    else:
        args = ActivePlayersArgs.model_validate(raw)

        # Check calendar validity, not just string format.
        date.fromisoformat(args.login_date)

        players = get_active_players(
            args.server_id,
            args.login_date,
        )

        result = {
            "server_id": args.server_id,
            "login_date": args.login_date,
            "matched_last_login_count": len(players),
            "players": players,
            "note": (
                "仅匹配最后登录日期，"
                "不能据此计算历史DAU或留存率"
            ),
        }

    return json.dumps(
        result,
        ensure_ascii=False,
    )