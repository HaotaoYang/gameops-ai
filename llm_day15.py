from dotenv import load_dotenv

from app.llm import ask_model


def main() -> None:
    load_dotenv()

    question = (
        "请用三句话解释游戏运营中的"
        "玩家次日留存率，并说明如何计算。"
    )

    print("问题：", question)
    print("正在调用大模型...")

    answer = ask_model(question)

    print("\n模型回答：")
    print(answer)


if __name__ == "__main__":
    main()