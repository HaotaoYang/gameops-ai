import json
import os

from collections.abc import Callable

from openai import OpenAI

from app.agent_state import (
    AgentRunResult,
    AgentState,
)
from app.llm import DEFAULT_MODEL
from app.multi_tools import (
    MULTI_TOOLS,
    execute_routed_tool,
)
from app.reliable_agent import (
    RELIABLE_AGENT_INSTRUCTIONS,
    normalize_arguments,
)
from app.tool_results import (
    ALLOWED_TOOLS,
    execute_safely,
)


def build_result(state: AgentState) -> AgentRunResult:
    """Return an immutable public snapshot."""

    return AgentRunResult(
        status=state.status,
        answer=state.answer,
        error_code=state.error_code,
        tool_calls=state.tool_calls,
        events=tuple(state.events),
    )


def fail(
    state: AgentState,
    error_code: str,
) -> AgentRunResult:
    """Transition the run into a terminal failure."""

    state.status = "failed"
    state.error_code = error_code
    state.answer = None

    state.add_event(
        kind="run",
        status="failed",
        error_code=error_code,
    )

    return build_result(state)


def run_traced_agent(
    question: str,
    client: OpenAI | None = None,
    *,
    max_tool_calls: int = 3,
    tool_executor: Callable[[str, str], str] = (
        execute_routed_tool
    ),
) -> AgentRunResult:
    """Run a read-only agent and return its execution trace."""

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

    # State belongs exclusively to this invocation.
    state = AgentState()

    state.messages.append({
        "role": "user",
        "content": question,
    })

    for round_index in range(max_tool_calls + 1):

        if round_index == 0:
            tool_choice = "required"
        elif round_index == max_tool_calls:
            tool_choice = "none"
        else:
            tool_choice = "auto"

        # Model request failures are terminal in Day 25.
        try:
            response = client.responses.create(
                model=model,
                instructions=RELIABLE_AGENT_INSTRUCTIONS,
                input=state.messages,
                tools=MULTI_TOOLS,
                tool_choice=tool_choice,
                parallel_tool_calls=False,
                store=False,
            )
        except Exception:
            return fail(
                state,
                "MODEL_REQUEST_FAILED",
            )

        calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        # No tool call: candidate final response.
        if not calls:
            if round_index == 0:
                return fail(
                    state,
                    "FIRST_TOOL_REQUIRED",
                )

            answer = response.output_text

            if not isinstance(answer, str) or not answer.strip():
                return fail(
                    state,
                    "EMPTY_ANSWER",
                )

            state.answer = answer
            state.status = "completed"

            state.add_event(
                kind="run",
                status="completed",
            )

            return build_result(state)

        # Do not execute tools after reaching the limit.
        if round_index >= max_tool_calls:
            return fail(
                state,
                "TOOL_LIMIT_REACHED",
            )

        if len(calls) != 1:
            return fail(
                state,
                "MULTIPLE_TOOL_CALLS",
            )

        call = calls[0]

        if call.name not in ALLOWED_TOOLS:
            return fail(
                state,
                "UNAUTHORIZED_TOOL",
            )

        signature = (
            call.name,
            normalize_arguments(call.arguments),
        )

        if signature in state.seen_calls:
            return fail(
                state,
                "DUPLICATE_TOOL_CALL",
            )

        state.seen_calls.add(signature)

        # Preserve the real model's output items.
        try:
            output_items = [
                item.model_dump(exclude_none=True)
                for item in response.output
            ]
        except Exception:
            return fail(
                state,
                "INVALID_MODEL_OUTPUT",
            )

        state.messages.extend(output_items)

        # Execute the authorized tool safely.
        result_json, tool_status = execute_safely(
            call.name,
            call.arguments,
            executor=tool_executor,
        )

        state.tool_calls += 1

        # Only store the safe error code in the trace.
        error_code = None

        if tool_status != "success":
            result_data = json.loads(result_json)
            error_code = result_data["error"]["code"]

        state.add_event(
            kind="tool",
            status=tool_status,
            tool_name=call.name,
            error_code=error_code,
        )

        # The model still receives the tool result,
        # including recoverable errors.
        state.messages.append({
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": result_json,
        })

    return fail(
        state,
        "AGENT_NOT_COMPLETED",
    )