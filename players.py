
# Day 3: Python functions and type hints

Player = dict[str, int | str]

PLAYERS: list[Player] = [
    {
        "player_id": 1001,
        "name": "Alice",
        "server_id": 3,
        "level": 50,
        "last_login": "2026-10-13"
    },
    {
        "player_id": 1002,
        "name": "Bob",
        "server_id": 3,
        "level": 42,
        "last_login": "2026-10-14"
    },
    {
        "player_id": 1003,
        "name": "Charlie",
        "server_id": 5,
        "level": 36,
        "last_login": "2026-10-12"
    },
    {
        "player_id": 1004,
        "name": "David",
        "server_id": 3,
        "level": 60,
        "last_login": "2026-10-14"
    },
    {
        "player_id": 1005,
        "name": "Eva",
        "server_id": 5,
        "level": 28,
        "last_login": "2026-10-11"
    }
]


def get_players(server_id: int) -> list[Player]:
    """Return players belonging to the specified server."""
    result: list[Player] = []

    for player in PLAYERS:
        if player["server_id"] == server_id:
            result.append(player.copy())

    return result


def count_players(server_id: int) -> int:
    """Count players belonging to the specified server."""
    return len(get_players(server_id))


def main() -> None:
    server_id = 3

    server_players = get_players(server_id)
    player_count = count_players(server_id)

    print(f"服务器ID: {server_id}")
    print(f"玩家数量: {player_count}")

    print("\n玩家列表:")

    for player in server_players:
        print(
            f"ID={player['player_id']}, "
            f"名字={player['name']}, "
            f"等级={player['level']}"
        )

def get_high_level_players(
    server_id: int,
    min_level: int
) -> list[Player]:
    """Return players from the specified server with level >= min_level."""
    result: list[Player] = []
    for player in PLAYERS:
        if player["server_id"] == server_id and player["level"] >= min_level:
            result.append(player.copy())
    return result

if __name__ == "__main__":
    main()
