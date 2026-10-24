import os
from typing import Literal, TypedDict

from openai import OpenAI

from app.llm import DEFAULT_MODEL
from app.prompts import GAMEOPS_ANALYSIS_INSTRUCTIONS


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class ChatSession:
    """Manage a conversation's message history in memory."""

    def __init__(
        self,
        client: OpenAI | None = None,
        *,
        instructions: str = GAMEOPS_ANALYSIS_INSTRUCTIONS,
    ) -> None:
        if not instructions.strip():
            raise ValueError("instructions不能为空")

        self.client = client
        self.instructions = instructions
        self.history: list[ChatMessage] = []

    def ask(self, question: str) -> str:
        """Send a question with previous conversation messages."""

        if not question.strip():
            raise ValueError("问题不能为空")

        # Construct a new request without mutating history.
        messages: list[ChatMessage] = [
            message.copy()
            for message in self.history
        ]

        messages.append({
            "role": "user",
            "content": question,
        })

        client = self.client

        if client is None:
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError(
                    "缺少 OPENAI_API_KEY 环境变量"
                )

            client = OpenAI()
            self.client = client

        model = os.getenv(
            "OPENAI_MODEL",
            DEFAULT_MODEL,
        )

        response = client.responses.create(
            model=model,
            instructions=self.instructions,
            input=messages,
            max_output_tokens=400,
            store=False,
        )

        answer = response.output_text

        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("模型未返回有效文本")

        # Commit history only after a valid response.
        self.history.append({
            "role": "user",
            "content": question,
        })

        self.history.append({
            "role": "assistant",
            "content": answer,
        })

        return answer

    def get_history(self) -> list[ChatMessage]:
        """Return a copy of the conversation history."""
        return [
            message.copy()
            for message in self.history
        ]

    def clear(self) -> None:
        """Clear the current conversation history."""
        self.history.clear()