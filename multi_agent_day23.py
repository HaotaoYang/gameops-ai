from dotenv import load_dotenv

from app.multi_agent import run_multi_agent


def log_tool(name: str) -> None:
    print(f"[工具执行成功] {name}", flush=True)


def main() -> None:
    load_dotenv()

    questions = [
        (
            "查询3服总共有多少玩家，"
            "其中等级不低于50的有多少人？"
            "请列出符合条件的玩家名字及等级。"
        ),
        (
            "查询3服最后登录日期为2026-10-14的玩家，"
            "列出名字，并说明能否根据这些数据"
            "计算历史DAU和次日留存率。"
        ),
    ]

    for index, question in enumerate(questions, start=1):
        print(f"\n=== 第{index}个问题 ===")
        print("用户：", question)
        print("\n正在执行 Agent...")

        answer = run_multi_agent(
            question,
            on_tool_call=log_tool,
        )

        print("\nAgent最终回答：")
        print(answer)


if __name__ == "__main__":
    main()