
import json
from datetime import date
from pathlib import Path

from models import Player


DATA_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "players.json"
)


def read_players(
    file_path: Path = DATA_FILE
) -> list[Player]:
    """Read and validate players from a JSON file."""

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except FileNotFoundError as exc:
        raise ValueError(
            f"玩家数据文件不存在: {file_path}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"玩家数据 JSON 格式错误: {file_path}"
        ) from exc

    if not isinstance(data, list):
        raise ValueError("玩家数据必须是 JSON 数组")

    players: list[Player] = []

    required_fields = {
        "player_id": int,
        "name": str,
        "server_id": int,
        "level": int,
        "last_login": str,
    }

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"第 {index + 1} 条玩家数据不是对象"
            )

        for field, expected_type in required_fields.items():
            if field not in item:
                raise ValueError(
                    f"第 {index + 1} 条玩家缺少字段: {field}"
                )

            if type(item[field]) is not expected_type:
                raise ValueError(
                    f"第 {index + 1} 条玩家字段类型错误: {field}"
                )

        try:
            date.fromisoformat(item["last_login"])
        except ValueError as exc:
            raise ValueError(
                f"第 {index + 1} 条玩家登录日期无效"
            ) from exc

        player = Player(
            player_id=item["player_id"],
            name=item["name"],
            server_id=item["server_id"],
            level=item["level"],
            last_login=item["last_login"],
        )

        players.append(player)

    return players
