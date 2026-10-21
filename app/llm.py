import os

from openai import OpenAI


DEFAULT_MODEL = "gpt-5.4-mini"


def ask_model(
    question: str,
    client: OpenAI | None = None,
) -> str:
    """Ask an LLM a question and return its text response."""

    if not question.strip():
        raise ValueError("问题不能为空")

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

    response = client.responses.create(
        model=model,
        instructions=(
            "你是一名游戏运营分析助手。"
            "请使用简洁、准确的中文回答问题。"
            "如果缺少实际业务数据，不要编造数字。"
        ),
        input=question,
        max_output_tokens=300,
        store=False,
    )

    if response.usage is not None:
        print("输入Token：", response.usage.input_tokens)
        print("输出Token：", response.usage.output_tokens)
        print("总Token：", response.usage.total_tokens)

    return response.output_text