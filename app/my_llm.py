import os
from openai import OpenAI

DEFAULT_MODEL = "gpt-6.1-sol"

def get_answer(question: str) -> str:

    if not question.strip():
        raise ValueError("问题不能为空")

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError(
            "缺少 OPENAI_API_KEY 环境变量"
        )

    client = OpenAI()

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    response = client.responses.create(
        model=model,
        instructions=(
            "你是一个私人助手。"
        ),
        input=question,
        max_output_tokens=500,
        store=False,
    )

    return response.output_text