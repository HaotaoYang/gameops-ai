import os
from typing import Literal, TypedDict

from contextlib import closing
from collections.abc import Iterator

from openai import OpenAI

DEFAULT_MODEL = "gpt-6.1-sol"

class MyChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str

class MyChatSession:
    """Manage a conversation's message history in memory."""
    
    def __init__(
        self,
        *,
        instructions: str = "你是一个私人助手",
    ) -> None:
        client = OpenAI()
        self.client = client
        self.instructions = instructions
        self.history: list[MyChatMessage] = []

    def ask(self, question: str) -> Iterator[str]:
        """Send a question with previous conversation messages."""
        
        if not question.strip():
            raise ValueError("问题不能为空")

        messages: list[MyChatMessage] = [
            message.copy() for message in self.history
        ]

        messages.append({
            "role": "user",
            "content": question,
        })

        if self.client is None:
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError(
                    "缺少 OPENAI_API_KEY 环境变量"
                )

            self.client = OpenAI()

        model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

        response = self.client.responses.create(
            model=model,
            instructions=self.instructions,
            input=messages,
            max_output_tokens=500,
            stream=True,
            store=False,
        )

        completed = False

        reply_text = ""

        with closing(response):
            for event in response:
                event_type = event.type

                if event_type == "response.output_text.delta":
                    delta = event.delta

                    if delta:
                        reply_text += delta
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

        if not reply_text.strip():
            raise ValueError("模型未返回任何有效文本")

        self.history.append({
            "role": "user",
            "content": question,
        })

        self.history.append({
            "role": "assistant",
            "content": reply_text,
        })

    def get_history(self) -> list[MyChatMessage]:
        """Return a copy of the conversation history."""
        return [message.copy() for message in self.history]

    def clear(self) -> None:
        """Clear the conversation history."""
        self.history.clear()