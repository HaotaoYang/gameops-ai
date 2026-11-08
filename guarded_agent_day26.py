from dotenv import load_dotenv

from app.answer_guard import run_guarded_agent


def main() -> None:
    load_dotenv()

    question = (
        "查询3服共有多少玩家，"
        "其中等级不低于50的玩家有多少名？"
        "请使用“3服共有X名玩家，"
        "等级不低于50的有Y名”的格式，"
        "再列出符合条件的玩家名字与等级。"
    )

    print("=== Day26 Agent 事实校验 ===")
    print("用户：", question)

    result = run_guarded_agent(question)

    print("\n=== Agent执行状态 ===")
    print(result.agent_result.status)

    print("\n=== 可信工具事实 ===")
    print(result.trusted_facts)

    print("\n=== 事实校验 ===")
    print("状态：", result.status)

    for issue in result.issues:
        print("问题：", issue)

    if result.approved:
        print("\n=== 已通过当前规则校验的回答 ===")
        print(result.answer)

    else:
        print("\n回答未通过校验，不作为正式运营结果展示。")


if __name__ == "__main__":
    main()