import math

from dataclasses import dataclass
from collections.abc import Sequence

from app.rag.documents import Chunk

from app.rag.weighted_retriever import (
    WeightedRetriever,
    WeightedSearchHit,
)

from app.rag.vector_retriever import (
    VectorRetriever,
    VectorSearchHit,
)


@dataclass(frozen=True)
class HybridSearchHit:
    chunk: Chunk
    score: float
    keyword_rank: int | None
    vector_rank: int | None


def _validate_weight(
    name: str,
    value: float,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(
            f"{name}必须是非负有限数字"
        )


def fuse_rrf(
    keyword_hits: Sequence[WeightedSearchHit],
    vector_hits: Sequence[VectorSearchHit],
    *,
    top_k: int = 3,
    rrf_k: int = 60,
    keyword_weight: float = 1.0,
    vector_weight: float = 1.0,
) -> list[HybridSearchHit]:
    """Fuse independently ranked retrieval results."""

    if top_k < 1:
        raise ValueError("top_k必须大于等于1")

    if rrf_k < 1:
        raise ValueError("rrf_k必须大于等于1")

    _validate_weight(
        "keyword_weight",
        keyword_weight,
    )

    _validate_weight(
        "vector_weight",
        vector_weight,
    )

    if keyword_weight == 0 and vector_weight == 0:
        raise ValueError(
            "至少一个检索权重必须大于0"
        )

    # Chunk ID is the unique key for fusion.
    # Each retrieval list is already sorted by score.
    records: dict[str, dict] = {}

    def add_hits(hits, *, source, weight):
        seen = set()

        for rank, hit in enumerate(hits, start=1):
            chunk_id = hit.chunk.id

            # Avoid scoring the same chunk twice
            # within one retrieval source.
            if chunk_id in seen:
                continue

            seen.add(chunk_id)

            if chunk_id not in records:
                records[chunk_id] = {
                    "chunk": hit.chunk,
                    "score": 0.0,
                    "keyword_rank": None,
                    "vector_rank": None,
                }

            record = records[chunk_id]

            record["score"] += (
                weight / (rrf_k + rank)
            )

            record[f"{source}_rank"] = rank

    add_hits(
        keyword_hits,
        source="keyword",
        weight=keyword_weight,
    )

    add_hits(
        vector_hits,
        source="vector",
        weight=vector_weight,
    )

    results = [
        HybridSearchHit(
            chunk=record["chunk"],
            score=record["score"],
            keyword_rank=record["keyword_rank"],
            vector_rank=record["vector_rank"],
        )
        for record in records.values()
    ]

    results.sort(
        key=lambda hit: (
            -hit.score,
            hit.chunk.source,
            hit.chunk.id,
        )
    )

    return results[:top_k]


class HybridRetriever:
    """Combine keyword and vector search using RRF."""

    def __init__(
        self,
        keyword_retriever: WeightedRetriever,
        vector_retriever: VectorRetriever,
    ) -> None:
        self.keyword_retriever = keyword_retriever
        self.vector_retriever = vector_retriever

    def search(
        self,
        question: str,
        query_vector: Sequence[float],
        *,
        top_k: int = 3,
        candidate_k: int = 6,
        rrf_k: int = 60,
        keyword_weight: float = 1.0,
        vector_weight: float = 1.0,
    ) -> list[HybridSearchHit]:
        if not question.strip():
            raise ValueError("问题不能为空")

        if top_k < 1:
            raise ValueError("top_k必须大于等于1")

        if candidate_k < 1:
            raise ValueError(
                "candidate_k必须大于等于1"
            )

        # Retrieve candidates independently.
        keyword_hits = self.keyword_retriever.search(
            question,
            top_k=candidate_k,
        )

        vector_hits = self.vector_retriever.search(
            query_vector,
            top_k=candidate_k,
        )

        return fuse_rrf(
            keyword_hits,
            vector_hits,
            top_k=top_k,
            rrf_k=rrf_k,
            keyword_weight=keyword_weight,
            vector_weight=vector_weight,
        )