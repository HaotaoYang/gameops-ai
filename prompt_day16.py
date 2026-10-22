from dotenv import load_dotenv

from app.llm import ask_model
from app.prompts import (
    GAMEOPS_ANALYSIS_INSTRUCTIONS,
    build_player_analysis_prompt,
)
from services import (
    count_players,
    get_high_level_players,
)


def main() -> None:
    load_dotenv()

    server_id = 3
    min_level = 50

    total = count_players(server_id)

    high_level = len(
        get_high_level_players(
            server_id,
            min_level,
        )
    )

    question = build_player_analysis_prompt(
        server_id=server_id,
        total_players=total,
        high_level_players=high_level,
        min_level=min_level,
    )

    print("发送给模型的业务问题：")
    print(question)

    print("\n正在调用大模型...")

    answer = ask_model(
        question,
        instructions=GAMEOPS_ANALYSIS_INSTRUCTIONS,
    )

    print("\n模型回答：")
    print(answer)


if __name__ == "__main__":
    main()