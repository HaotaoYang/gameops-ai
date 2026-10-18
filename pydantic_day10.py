
from datetime import date

from pydantic import ValidationError

from app.schemas import PlayerResponse


def main() -> None:
    player = PlayerResponse(
        player_id=1001,
        name="Alice",
        server_id=3,
        level=50,
        last_login=date(2026, 10, 13),
    )

    print("玩家姓名:", player.name)
    print("玩家等级:", player.level)

    print("转为Dict:", player.model_dump())
    print("转为JSON:", player.model_dump_json())

    try:
        PlayerResponse(
            player_id="1001",
            name="Alice",
            server_id=3,
            level=50,
            last_login=date(2026, 10, 13),
        )
    except ValidationError as exc:
        print("错误字段:", exc.errors()[0]["loc"])
        print("错误类型:", exc.errors()[0]["type"])


if __name__ == "__main__":
    main()
