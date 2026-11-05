from dotenv import load_dotenv

from app.reliable_agent import run_reliable_agent


def log_tool(name: str, status: str) -> None:
    print(
        f"[工具事件] {name} -> {status}",
        flush=True,
    )


def main() -> None:
    load_dotenv()

    question = (
        "查询3服有多少玩家，"
        "其中等级不低于50的有多少人？"
        "请列出符合条件的玩家名字和等级。"
    )

    print("=== Day24 可靠性增强 Agent ===")
    print("用户：", question)
    print("\n开始执行...\n")

    answer = run_reliable_agent(
        question,
        max_tool_calls=3,
        on_tool_event=log_tool,
    )

    print("\nAgent最终回答：")
    print(answer)


if __name__ == "__main__":
    main()