import json
from collections.abc import Callable

from pydantic import ValidationError

from app.multi_tools import execute_routed_tool


ALLOWED_TOOLS = frozenset({
    "count_players",
    "get_high_level_players",
    "get_active_players",
})


def make_success(data: dict) -> str:
    """Encode a successful tool result."""

    return json.dumps(
        {
            "ok": True,
            "data": data,
        },
        ensure_ascii=False,
    )


def make_error(code: str, message: str) -> str:
    """Encode a safe tool error."""

    return json.dumps(
        {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
        ensure_ascii=False,
    )


def execute_safely(
    name: str,
    arguments_json: str,
    *,
    executor: Callable[[str, str], str] = execute_routed_tool,
) -> tuple[str, str]:
    """
    Execute one allowed tool and return:
    (JSON result, execution status).
    """

    # Never execute an unknown tool.
    if name not in ALLOWED_TOOLS:
        raise ValueError(
            f"不允许调用的工具：{name}"
        )

    try:
        raw_result = executor(
            name,
            arguments_json,
        )

        data = json.loads(raw_result)

        if not isinstance(data, dict):
            raise RuntimeError(
                "工具返回结果不是JSON对象"
            )

        return make_success(data), "success"

    except (ValueError, ValidationError):
        # Includes malformed JSON and invalid business arguments.
        return (
            make_error(
                "INVALID_ARGUMENTS",
                "工具参数不合法，请检查字段类型和取值",
            ),
            "invalid_arguments",
        )

    except Exception:
        # Do not expose internal exception details to the model.
        return (
            make_error(
                "TOOL_EXECUTION_FAILED",
                "工具执行失败，当前无法获取该项数据",
            ),
            "execution_failed",
        )