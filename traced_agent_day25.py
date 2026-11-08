from dotenv import load_dotenv

from app.traced_agent import run_traced_agent


def main() -> None:
    load_dotenv()

    question = (
        "查询3服有多少玩家，"
        "其中等级不低于50的有多少人？"
        "请列出符合条件的玩家名字和等级。"
    )

    print("=== Day 25 Agent 状态与执行轨迹 ===")
    print("用户问题：", question)

    result = run_traced_agent(
        question,
        max_tool_calls=3,
    )

    print("\n=== 执行轨迹 ===")

    for event in result.events:
        print(
            f"第{event.step}步："
            f"{event.tool_name or event.kind}"
        )

        print("状态：", event.status)

        if event.error_code:
            print("错误码：", event.error_code)

        print()

    print("=== 最终状态 ===")
    print("状态：", result.status)
    print("工具调用次数：", result.tool_calls)

    if result.succeeded:
        print("\nAgent回答：")
        print(result.answer)
    else:
        print("任务失败，错误码：", result.error_code)


if __name__ == "__main__":
    main()