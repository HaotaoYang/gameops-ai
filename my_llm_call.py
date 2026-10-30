from dotenv import load_dotenv

from app.my_llm import MyChatSession


def main() -> None:
    load_dotenv()

    session = MyChatSession()

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

        chunks: list[str] = []

        try:
            for chunk in session.ask(question):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            print()
        except Exception as exc:
            print("\n\n模型输出失败，以上内容可能不完整。")
            print("错误类型：", type(exc).__name__)
            print("错误信息：", str(exc))
            continue

if __name__ == "__main__":
    main()
