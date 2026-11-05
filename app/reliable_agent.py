import json
import os

from collections.abc import Callable

from openai import OpenAI

from app.llm import DEFAULT_MODEL
from app.multi_tools import MULTI_TOOLS
from app.tool_results import (
    ALLOWED_TOOLS,
    execute_safely,
)


RELIABLE_AGENT_INSTRUCTIONS = """
你是一名游戏运营数据查询助手。

规则：
1. 查询玩家事实时，必须使用提供的业务工具。
2. 根据用户问题选择合适的工具。
3. 工具成功时，只能依据工具实际结果回答。
4. 工具返回ok=false时，不得将失败当成成功。
5. 如果是INVALID_ARGUMENTS，可以修正参数后重新调用。
6. 如果工具执行失败，应说明当前数据无法获取。
7. 不要反复执行完全相同的工具请求。
8. min_level是高等级筛选阈值，不是玩家最低等级。
9. 最后登录日期匹配人数不等于历史DAU。
10. 缺少证据时明确说明数据不足。
""".strip()


def normalize_arguments(arguments_json: str) -> str:
    """Build a stable signature for duplicate-call detection."""

    try:
        arguments = json.loads(arguments_json)

        return json.dumps(
            arguments,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    except (ValueError, TypeError):
        return arguments_json.strip()


def run_reliable_agent(
    question: str,
    client: OpenAI | None = None,
    *,
    max_tool_calls: int = 3,
    on_tool_event: Callable[[str, str], None] | None = None,
    tool_executor: Callable[[str, str], str] | None = None,
) -> str:
    """Run a bounded agent with safe tool error handling."""

    if not question.strip():
        raise ValueError("问题不能为空")

    if not 1 <= max_tool_calls <= 5:
        raise ValueError(
            "max_tool_calls必须在1到5之间"
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

    seen_calls: set[tuple[str, str]] = set()

    if tool_executor is None:
        # Use the existing Day 23 business tool executor.
        from app.multi_tools import execute_routed_tool

        tool_executor = execute_routed_tool

    # One initial model response plus a bounded number of follow-ups.
    for round_index in range(max_tool_calls + 1):

        if round_index == 0:
            tool_choice = "required"
        elif round_index == max_tool_calls:
            tool_choice = "none"
        else:
            tool_choice = "auto"

        response = client.responses.create(
            model=model,
            instructions=RELIABLE_AGENT_INSTRUCTIONS,
            input=messages,
            tools=MULTI_TOOLS,
            tool_choice=tool_choice,
            parallel_tool_calls=False,
            store=False,
        )

        calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not calls:
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

        if round_index >= max_tool_calls:
            raise RuntimeError(
                "达到工具调用次数上限，"
                "不再执行新的工具"
            )

        if len(calls) != 1:
            raise RuntimeError(
                "本教学版本每轮只支持一个工具调用"
            )

        call = calls[0]

        # Authorization must happen before execution.
        if call.name not in ALLOWED_TOOLS:
            raise ValueError(
                f"不允许调用的工具：{call.name}"
            )

        # Recognize identical calls even if JSON key order changes.
        signature = (
            call.name,
            normalize_arguments(call.arguments),
        )

        if signature in seen_calls:
            raise RuntimeError(
                "检测到重复工具调用，Agent已停止"
            )

        seen_calls.add(signature)

        # Keep the model's original function call item.
        messages.extend(
            item.model_dump(exclude_none=True)
            for item in response.output
        )

        result_json, status = execute_safely(
            call.name,
            call.arguments,
            executor=tool_executor,
        )

        # The model receives the result, including safe errors.
        messages.append({
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": result_json,
        })

        if on_tool_event is not None:
            on_tool_event(call.name, status)

    raise RuntimeError(
        "Agent未能在规定轮数内完成任务"
    )