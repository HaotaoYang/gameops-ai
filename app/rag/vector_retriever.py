import math

from dataclasses import dataclass
from collections.abc import Sequence

from app.rag.documents import Chunk


def cosine_similarity(
    a: Sequence[float],
    b: Sequence[float],
) -> float:
    """Calculate cosine similarity between two vectors."""

    if not a or not b:
        raise ValueError("向量不能为空")

    if len(a) != len(b):
        raise ValueError("向量维度不一致")

    if any(
        not math.isfinite(value)
        for value in (*a, *b)
    ):
        raise ValueError("向量包含非有限数字")

    dot_product = sum(
        x * y for x, y in zip(a, b)
    )

    norm_a = math.sqrt(
        sum(x * x for x in a)
    )

    norm_b = math.sqrt(
        sum(y * y for y in b)
    )

    if norm_a == 0 or norm_b == 0:
        raise ValueError("不能使用零向量")

    return dot_product / (norm_a * norm_b)


@dataclass(frozen=True)
class VectorSearchHit:
    chunk: Chunk
    score: float


class VectorRetriever:
    """Small in-memory vector search index."""

    def __init__(
        self,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(
                "Chunk数量与向量数量不一致"
            )

        if not chunks:
            self.chunks = ()
            self.vectors = ()
            self.dimensions = 0
            return

        dimensions = len(vectors[0])

        if dimensions < 1:
            raise ValueError("向量不能为空")

        if any(
            len(vector) != dimensions
            for vector in vectors
        ):
            raise ValueError("向量维度不一致")

        # Copy values to prevent the original list from
        # being modified after the index is built.
        self.chunks = tuple(chunks)
        self.vectors = tuple(
            tuple(float(value) for value in vector)
            for vector in vectors
        )

        self.dimensions = dimensions

        # Validate vector contents and zero norms.
        for vector in self.vectors:
            cosine_similarity(vector, vector)

    def search(
        self,
        query_vector: Sequence[float],
        *,
        top_k: int = 3,
        min_score: float | None = None,
    ) -> list[VectorSearchHit]:
        """Return chunks ranked by cosine similarity."""

        if top_k < 1:
            raise ValueError("top_k必须大于等于1")

        if min_score is not None and (
            not math.isfinite(min_score)
            or not -1 <= min_score <= 1
        ):
            raise ValueError(
                "min_score必须在-1到1之间"
            )

        if not self.chunks:
            return []

        if len(query_vector) != self.dimensions:
            raise ValueError(
                "查询向量维度与索引不一致"
            )

        hits = []

        for chunk, vector in zip(
            self.chunks,
            self.vectors,
        ):
            score = cosine_similarity(
                query_vector,
                vector,
            )

            if (
                min_score is not None
                and score < min_score
            ):
                continue

            hits.append(
                VectorSearchHit(
                    chunk=chunk,
                    score=score,
                )
            )

        hits.sort(
            key=lambda hit: (
                -hit.score,
                hit.chunk.source,
                hit.chunk.id,
            )
        )

        return hits[:top_k]