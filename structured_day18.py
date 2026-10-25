from dotenv import load_dotenv

from app.prompts import build_player_analysis_prompt
from app.structured_llm import generate_structured_report
from services import count_players, get_high_level_players


def main() -> None:
    load_dotenv()

    server_id = 3
    min_level = 50

    total_players = count_players(server_id)

    high_level_players = len(
        get_high_level_players(
            server_id,
            min_level,
        )
    )

    question = build_player_analysis_prompt(
        server_id=server_id,
        total_players=total_players,
        high_level_players=high_level_players,
        min_level=min_level,
    )

    print("正在生成结构化运营报告...")

    report = generate_structured_report(question)

    print("\n=== 报告概述 ===")
    print(report.summary)

    print("\n=== 观察结果 ===")

    for observation in report.observations:
        print("-", observation)

    print("\n=== 数据限制 ===")

    for limitation in report.limitations:
        print("-", limitation)

    print("\n是否需要更多数据：")
    print(report.needs_more_data)

    print("\n=== 完整JSON ===")
    print(
        report.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    main()