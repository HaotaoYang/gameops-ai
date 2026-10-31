import os

from openai import OpenAI

from app.llm import DEFAULT_MODEL
from app.tools import TOOLS, execute_tool


AGENT_INSTRUCTIONS = (
    "你是一名游戏运营助手。"
    "对于玩家查询，必须使用提供的工具获取数据。"
    "只能根据真实工具结果回答。"
    "min_level是等级筛选阈值，"
    "不是全体玩家的最低等级。"
    "不得编造玩家数量、等级或留存率。"
)


def run_agent(
    question: str,
    client: OpenAI | None = None,
) -> str:
    """Run one read-only tool call and return the model answer."""

    if not question.strip():
        raise ValueError("问题不能为空")

    if client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("缺少 OPENAI_API_KEY 环境变量")

        client = OpenAI()

    model = os.getenv(
        "OPENAI_MODEL",
        DEFAULT_MODEL,
    )

    # First model call: request tool selection.
    first = client.responses.create(
        model=model,
        instructions=AGENT_INSTRUCTIONS,
        input=question,
        tools=TOOLS,
        tool_choice="required",
        parallel_tool_calls=False,
        store=False,
    )

    tool_calls = [
        item
        for item in first.output
        if item.type == "function_call"
    ]

    if len(tool_calls) != 1:
        raise RuntimeError(
            "本教学版本要求模型恰好调用一个工具"
        )

    call = tool_calls[0]

    print("要调用的函数信息：", call)

    # Execute the tool in Python, not inside the model.
    result_json = execute_tool(
        call.name,
        call.arguments,
    )

    # Preserve the original model output and attach tool result.
    next_input = [
        {"role": "user", "content": question},
        *[
            item.model_dump(exclude_none=True)
            for item in first.output
        ],
        {
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": result_json,
        },
    ]

    # Second model call: generate a natural-language answer.
    second = client.responses.create(
        model=model,
        instructions=AGENT_INSTRUCTIONS,
        input=next_input,
        tools=TOOLS,
        tool_choice="none",
        store=False,
    )

    answer = second.output_text

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("模型没有返回有效回答")

    return answer