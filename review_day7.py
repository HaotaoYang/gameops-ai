from services import (
    count_players,
    get_active_players,
    get_high_level_players,
)

def main() -> None:
    print(f"3服的总玩家数量: {count_players(server_id=3)}")
    print(f"5服的总玩家数量: {count_players(server_id=5)}")

    high_level_players = get_high_level_players(3, 50)

    high_level_names = [
        player["name"]
        for player in high_level_players
    ]

    print("3服高等级玩家:", high_level_names)

    active_players = get_active_players(
        3, "2026-10-13"
    )

    active_names = [
        player["name"]
        for player in active_players
    ]

    print("3服指定日期最后登录玩家:", active_names)

if __name__ == "__main__":
    main()