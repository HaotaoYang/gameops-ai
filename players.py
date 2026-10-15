import json
from datetime import date
from pathlib import Path

Player = dict[str, int | str]

DATA_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "players.json"
)


def read_players(
    file_path: Path = DATA_FILE
) -> list[Player]:
    """Read player records from a JSON file."""
    try:
        with file_path.open(
            "r",
            encoding="utf-8"
        ) as file:
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
        raise ValueError(
            "玩家数据必须是 JSON 数组"
        )

    for index, player in enumerate(data):
        if not isinstance(player, dict):
            raise ValueError(
                f"第 {index + 1} 条玩家数据不是对象"
            )

        required_fields = {
            "player_id": int,
            "name": str,
            "server_id": int,
            "level": int,
            "last_login": str,
        }

        for field, expected_type in required_fields.items():
            if field not in player:
                raise ValueError(
                    f"第 {index + 1} 条玩家缺少字段: {field}"
                )

            if type(player[field]) is not expected_type:
                raise ValueError(
                    f"第 {index + 1} 条玩家字段类型错误: {field}"
                )

        try:
            date.fromisoformat(player["last_login"])
        except ValueError as exc:
            raise ValueError(
                f"第 {index + 1} 条玩家登录日期无效"
            ) from exc

    return data


def get_players(server_id: int) -> list[Player]:
    """Return players belonging to a server."""
    result: list[Player] = []

    for player in read_players():
        if player["server_id"] == server_id:
            result.append(player.copy())

    return result


def count_players(server_id: int) -> int:
    """Count players belonging to the specified server."""
    return len(get_players(server_id))


def get_high_level_players(
    server_id: int,
    min_level: int
) -> list[Player]:
    """Return players from the specified server with level >= min_level."""
    result: list[Player] = []
    for player in get_players(server_id):
        if player["level"] >= min_level:
            result.append(player.copy())
    return result

def get_active_players(
    server_id: int,
    target_date: str
) -> list[Player]:
    """Return players whose last login equals target_date."""

    try:
        query_date = date.fromisoformat(target_date)
    except ValueError as exc:
        raise ValueError(
            f"查询日期格式无效: {target_date}"
        ) from exc

    result: list[Player] = []

    for player in get_players(server_id):
        login_date = date.fromisoformat(
            player["last_login"]
        )

        if login_date == query_date:
            result.append(player.copy())

    return result

def count_active_players(
    server_id: int,
    target_date: str
) -> int:
    return len(get_active_players(server_id, target_date))

def main() -> None:
    server_id = 3
    target_date = "2026-10-14"

    print(f"服务器ID: {server_id}")
    print(f"服务器玩家总数: {count_players(server_id)}")

    active_players = get_active_players(
        server_id,
        target_date
    )

    print(f"查询日期: {target_date}")
    print(f"最后登录日期为当天的玩家数: {len(active_players)}")

    print("\n玩家列表:")

    for player in active_players:
        print(
            f"ID={player['player_id']}, "
            f"名字={player['name']}, "
            f"等级={player['level']}"
        )

    print(count_active_players(3, "2026-10-14"))
    print(count_active_players(5, "2026-10-14"))
    print(count_active_players(3, "2026-10-13"))

if __name__ == "__main__":
    main()
