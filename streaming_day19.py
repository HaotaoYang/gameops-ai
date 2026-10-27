from dotenv import load_dotenv

from app.streaming_llm import stream_model
from app.prompts import GAMEOPS_ANALYSIS_INSTRUCTIONS
from app.prompts import build_player_analysis_prompt

from services import count_players, get_high_level_players


def main() -> None:
    load_dotenv()

    server_id = 3
    min_level = 50

    total_players = count_players(server_id)

    high_level_players = len(
        get_high_level_players(server_id, min_level)
    )

    question = build_player_analysis_prompt(
        server_id=server_id,
        total_players=total_players,
        high_level_players=high_level_players,
        min_level=min_level,
    )

    print("=== GameOps AI 流式分析 ===")
    print("服务器：", server_id)
    print("总玩家：", total_players)
    print("等级>=50人数：", high_level_players)

    print("\n模型正在回答：\n")

    chunks: list[str] = []

    try:
        for chunk in stream_model(
            question,
            instructions=GAMEOPS_ANALYSIS_INSTRUCTIONS,
        ):
            print(chunk, end="", flush=True)
            chunks.append(chunk)

    except Exception as exc:
        print("\n\n模型输出失败，以上内容可能不完整。")
        print("错误类型：", type(exc).__name__)
        print("错误信息：", str(exc))
        raise

    print("\n\n=== 生成完成 ===")

    answer = "".join(chunks)

    print("最终文本字符数：", len(answer))


if __name__ == "__main__":
    main()