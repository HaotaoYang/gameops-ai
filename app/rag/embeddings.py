import math
import os

from openai import OpenAI


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def embed_texts(
    texts: list[str],
    *,
    client: OpenAI | None = None,
    model: str | None = None,
) -> list[list[float]]:
    """
    Convert a batch of texts to embedding vectors.

    Preserves original input order and supports
    injecting a Mock client for offline testing.
    """

    if not texts:
        return []

    if any(
        not isinstance(text, str) or not text.strip()
        for text in texts
    ):
        raise ValueError("Embedding输入不能是空文本")

    model_name = (
        model
        or os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            DEFAULT_EMBEDDING_MODEL,
        )
    )

    if not model_name.strip():
        raise ValueError("Embedding模型名称不能为空")

    if client is None:
        client = OpenAI()

    response = client.embeddings.create(
        model=model_name,
        input=texts,
        encoding_format="float",
    )

    # Validate the returned indices before rebuilding
    # the original input order.
    items = list(response.data)

    if len(items) != len(texts):
        raise RuntimeError("Embedding返回数量不一致")

    vectors: list[list[float] | None] = [
        None for _ in texts
    ]

    for item in items:
        index = item.index

        if (
            type(index) is not int
            or index < 0
            or index >= len(texts)
            or vectors[index] is not None
        ):
            raise RuntimeError(
                "Embedding返回的索引不合法"
            )

        vector = list(item.embedding)

        if not vector or any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            for value in vector
        ):
            raise RuntimeError(
                "Embedding向量包含非法数值"
            )

        vectors[index] = [
            float(value) for value in vector
        ]

    if any(vector is None for vector in vectors):
        raise RuntimeError("Embedding返回结果不完整")

    result = [
        vector
        for vector in vectors
        if vector is not None
    ]

    dimensions = {len(vector) for vector in result}

    if len(dimensions) != 1:
        raise RuntimeError(
            "Embedding向量维度不一致"
        )

    return result