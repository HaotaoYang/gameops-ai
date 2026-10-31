import json

from pydantic import BaseModel, ConfigDict, Field

from services import get_high_level_players


class HighLevelPlayersArgs(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    server_id: int = Field(ge=1)
    min_level: int = Field(ge=0)


TOOLS = [
    {
        "type": "function",
        "name": "get_high_level_players",
        "description": (
            "查询指定游戏服务器中，等级大于等于"
            "min_level 的玩家。"
            "min_level 是筛选阈值，"
            "不是全部玩家的最低等级。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "integer",
                    "description": "游戏服务器ID",
                },
                "min_level": {
                    "type": "integer",
                    "description": "高等级筛选阈值",
                },
            },
            "required": [
                "server_id",
                "min_level",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


def execute_tool(
    name: str,
    arguments_json: str,
) -> str:
    """Validate and execute a permitted read-only tool."""

    if name != "get_high_level_players":
        raise ValueError(f"不允许调用的工具：{name}")

    raw_arguments = json.loads(arguments_json)

    args = HighLevelPlayersArgs.model_validate(
        raw_arguments
    )

    players = get_high_level_players(
        args.server_id,
        args.min_level,
    )

    result = {
        "server_id": args.server_id,
        "min_level": args.min_level,
        "high_level_count": len(players),
        "players": players,
    }

    return json.dumps(
        result,
        ensure_ascii=False,
    )