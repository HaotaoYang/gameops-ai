
from services import (
    count_players,
    get_active_players,
)


def main() -> None:
    server_id = 3
    target_date = "2026-10-14"

    total = count_players(server_id)
    active_players = get_active_players(
        server_id,
        target_date
    )

    print(f"服务器ID: {server_id}")
    print(f"服务器玩家总数: {total}")
    print(f"查询日期: {target_date}")
    print(
        f"最后登录日期为当天的玩家数: "
        f"{len(active_players)}"
    )

    print("\n玩家列表:")

    for player in active_players:
        print(
            f"ID={player['player_id']}, "
            f"名字={player['name']}, "
            f"等级={player['level']}"
        )


if __name__ == "__main__":
    main()
