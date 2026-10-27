import os
from contextlib import closing
from collections.abc import Iterator

from openai import OpenAI

from app.llm import DEFAULT_MODEL, DEFAULT_INSTRUCTIONS


def stream_model(
    question: str,
    client: OpenAI | None = None,
    *,
    instructions: str | None = None,
) -> Iterator[str]:
    """Yield model-generated text chunks as they arrive."""

    if not question.strip():
        raise ValueError("问题不能为空")

    if instructions is not None and not instructions.strip():
        raise ValueError("instructions不能为空")

    if client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("缺少 OPENAI_API_KEY 环境变量")

        client = OpenAI()

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    effective_instructions = (
        DEFAULT_INSTRUCTIONS
        if instructions is None
        else instructions
    )

    stream = client.responses.create(
        model=model,
        instructions=effective_instructions,
        input=question,
        max_output_tokens=500,
        stream=True,
        store=False,
    )

    completed = False
    received_text = False

    # Always close the stream after consumption or failure.
    with closing(stream):
        for event in stream:
            event_type = event.type

            if event_type == "response.output_text.delta":
                delta = event.delta

                if delta:
                    received_text = True
                    yield delta

            elif event_type == "response.completed":
                completed = True

            elif event_type == "response.failed":
                raise RuntimeError("模型流式响应失败")

            elif event_type == "response.incomplete":
                raise RuntimeError("模型流式响应未完整完成")

            elif event_type == "error":
                raise RuntimeError("模型流式传输出现错误")

    if not completed:
        raise RuntimeError("流已结束，但未收到完成事件")

    if not received_text:
        raise ValueError("模型没有返回有效文本")