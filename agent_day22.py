from dotenv import load_dotenv

from app.agent import run_agent


def main() -> None:
    load_dotenv()

    question = (
        "帮我查询3服等级不低于50的玩家，"
        "告诉我一共有多少人，并列出玩家名字。"
    )

    print("用户问题：")
    print(question)

    print("\n正在调用 AI Agent...")

    answer = run_agent(question)

    print("\nAgent 回答：")
    print(answer)


if __name__ == "__main__":
    main()