from dotenv import load_dotenv

from app.conversation import ChatSession
from app.prompts import build_player_analysis_prompt
from services import count_players, get_high_level_players


def main() -> None:
    load_dotenv()

    server_id = 3
    min_level = 50

    total = count_players(server_id)
    high_level = len(
        get_high_level_players(server_id, min_level)
    )

    first_question = build_player_analysis_prompt(
        server_id=server_id,
        total_players=total,
        high_level_players=high_level,
        min_level=min_level,
    )

    session = ChatSession()

    print("=== 第一轮 ===")
    print("用户：", first_question)

    first_answer = session.ask(first_question)

    print("模型：", first_answer)

    print("\n=== 第二轮 ===")

    second_question = (
        "刚才提到的高等级玩家占总玩家的比例是多少？"
        "请展示计算公式，并说明能否据此判断留存率。"
    )

    print("用户：", second_question)

    second_answer = session.ask(second_question)

    print("模型：", second_answer)

    print("\n=== 对话历史 ===")

    history = session.get_history()

    for index, message in enumerate(history, start=1):
        print(
            f"{index}. {message['role']}: "
            f"{message['content'][:80]}"
        )

    print("\n消息数量：", len(history))


if __name__ == "__main__":
    main()