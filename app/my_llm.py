import os
from typing import Literal, TypedDict

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

    def ask(self, question: str) -> str:
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
            store=False,
        )

        answer = response.output_text

        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("模型未返回有效文本")

        self.history.append({
            "role": "user",
            "content": question,
        })

        self.history.append({
            "role": "assistant",
            "content": answer,
        })

        return answer

    def get_history(self) -> list[MyChatMessage]:
        """Return a copy of the conversation history."""
        return [message.copy() for message in self.history]

    def clear(self) -> None:
        """Clear the conversation history."""
        self.history.clear()