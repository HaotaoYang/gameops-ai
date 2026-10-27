from dotenv import load_dotenv

from app.evaluator import evaluate_player_analysis
from app.llm import ask_model
from app.prompts import (
    GAMEOPS_ANALYSIS_INSTRUCTIONS,
    build_player_analysis_prompt,
)
from services import count_players, get_high_level_players


def main() -> None:
    load_dotenv()

    server_id = 3
    min_level = 50

    total = count_players(server_id)
    high_level = len(
        get_high_level_players(server_id, min_level)
    )

    question = build_player_analysis_prompt(
        server_id=server_id,
        total_players=total,
        high_level_players=high_level,
        min_level=min_level,
    )

    answer = ask_model(
        question,
        instructions=GAMEOPS_ANALYSIS_INSTRUCTIONS,
    )

    print("=== 模型回答 ===")
    print(answer)

    result = evaluate_player_analysis(
        answer,
        total_players=total,
        high_level_players=high_level,
        min_level=min_level,
    )

    print("\n=== 自动评测 ===")
    print("通过：", result.passed)
    print("评分：", result.score)

    for issue in result.issues:
        print("发现问题：", issue)


if __name__ == "__main__":
    main()