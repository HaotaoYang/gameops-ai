from dotenv import load_dotenv

from app.audited_agent import run_audited_agent


def main() -> None:
    load_dotenv()

    server_id = 3
    min_level = 50

    question = (
        f"请分别调用业务工具查询{server_id}服的玩家总数，"
        f"以及等级不低于{min_level}的玩家列表。"
        f"最后请使用“{server_id}服共有X名玩家，"
        f"等级不低于{min_level}的有Y名”的格式，"
        "说明查询结果，并列出玩家名字和等级。"
    )

    print("=== Day27 可靠性综合实战 ===")
    print("用户问题：", question)

    result = run_audited_agent(
        question,
        server_id=server_id,
        min_level=min_level,
    )

    print("\n=== Agent执行轨迹 ===")

    for event in result.agent_result.events:
        print(
            f"第{event.step}步："
            f"{event.tool_name or event.kind}"
            f" -> {event.status}"
        )

        if event.error_code:
            print("  错误码：", event.error_code)

    print("\n=== Agent状态 ===")
    print(result.agent_result.status)

    print("\n=== 审计状态 ===")
    print(result.status)

    print("\n=== 可信业务事实 ===")
    print(result.trusted_facts)

    if result.approved:
        print("\n=== Python生成的最终报告 ===")
        print(result.answer)
    else:
        print("\n报告未通过检查。")

        for issue in result.issues:
            print("-", issue)


if __name__ == "__main__":
    main()