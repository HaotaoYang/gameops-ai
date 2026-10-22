import os

from openai import OpenAI


DEFAULT_MODEL = "gpt-5.4-mini"

DEFAULT_INSTRUCTIONS = (
    "你是一名游戏运营分析助手。"
    "请使用简洁、准确的中文回答问题。"
    "如果缺少实际业务数据，不要编造数字。"
)


def ask_model(
    question: str,
    client: OpenAI | None = None,
    *,
    instructions: str | None = None,
) -> str:
    """Ask an LLM and return its text response."""

    if not question.strip():
        raise ValueError("问题不能为空")

    if instructions is not None and not instructions.strip():
        raise ValueError("instructions不能为空")

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

    effective_instructions = (
        DEFAULT_INSTRUCTIONS
        if instructions is None
        else instructions
    )

    response = client.responses.create(
        model=model,
        instructions=effective_instructions,
        input=question,
        max_output_tokens=300,
        store=False,
    )

    return response.output_text