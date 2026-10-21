from dotenv import load_dotenv

from app.my_llm import get_answer


def main() -> None:
    load_dotenv()

    while True:
        try:
            question = input("请输入问题（输入 stop 退出）：")
        except (EOFError, KeyboardInterrupt):
            print("\n程序已退出。")
            break

        if question == "stop":
            print("程序已退出。")
            break

        if not question.strip():
            print("问题不能为空，请重新输入。")
            continue

        try:
            answer = get_answer(question)
        except Exception as exc:
            print(f"请求失败：{exc}")
            continue

        print("回答：", answer)


if __name__ == "__main__":
    main()
