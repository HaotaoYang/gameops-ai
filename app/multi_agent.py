import os
from collections.abc import Callable

from openai import OpenAI

from app.llm import DEFAULT_MODEL
from app.multi_tools import MULTI_TOOLS, execute_routed_tool


MULTI_AGENT_INSTRUCTIONS = (
    "你是一名游戏运营数据查询助手。"
    "需要玩家统计时必须调用提供的业务工具。"
    "根据用户问题选择工具。"
    "如果一个工具的结果不足以回答，可以继续调用其他工具。"
    "只能依据工具实际返回的数据回答。"
    "min_level表示高等级筛选阈值，"
    "不是全部玩家的最低等级。"
    "最后登录日期匹配人数不等于历史DAU。"
    "不得编造玩家数量、等级或留存率。"
)


def run_multi_agent(
    question: str,
    client: OpenAI | None = None,
    *,
    max_tool_rounds: int = 3,
    on_tool_call: Callable[[str], None] | None = None,
) -> str:
    """Run a bounded, sequential, read-only agent loop."""

    if not question.strip():
        raise ValueError("问题不能为空")

    if not 1 <= max_tool_rounds <= 5:
        raise ValueError(
            "max_tool_rounds必须在1到5之间"
        )

    if client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "缺少 OPENAI_API_KEY 环境变量"
            )

        client = OpenAI()

    model = os.getenv(
        "OPENAI_MODEL",
        DEFAULT_MODEL,
    )

    messages: list[dict] = [
        {
            "role": "user",
            "content": question,
        }
    ]

    # Allow at most max_tool_rounds tool rounds,
    # followed by one final no-tool response.
    for round_index in range(max_tool_rounds + 1):

        if round_index == 0:
            tool_choice = "required"
        elif round_index == max_tool_rounds:
            tool_choice = "none"
        else:
            tool_choice = "auto"

        response = client.responses.create(
            model=model,
            instructions=MULTI_AGENT_INSTRUCTIONS,
            input=messages,
            tools=MULTI_TOOLS,
            tool_choice=tool_choice,
            parallel_tool_calls=False,
            store=False,
        )

        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            if round_index == 0:
                raise RuntimeError(
                    "首轮没有产生必须的工具调用"
                )

            answer = response.output_text

            if not isinstance(answer, str) or not answer.strip():
                raise ValueError(
                    "模型没有返回有效的最终回答"
                )

            return answer

        if round_index >= max_tool_rounds:
            raise RuntimeError(
                "达到工具调用轮数上限，"
                "模型仍要求执行工具"
            )

        if len(tool_calls) != 1:
            raise RuntimeError(
                "本教学版本每轮只支持一个工具调用"
            )

        call = tool_calls[0]

        # Preserve the model's actual output items.
        messages.extend(
            item.model_dump(exclude_none=True)
            for item in response.output
        )

        # Python validates and executes the named tool.
        result_json = execute_routed_tool(
            call.name,
            call.arguments,
        )

        if on_tool_call is not None:
            on_tool_call(call.name)

        # Return the result using the original call_id.
        messages.append({
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": result_json,
        })

    raise RuntimeError(
        "Agent未能在规定轮数内完成任务"
    )