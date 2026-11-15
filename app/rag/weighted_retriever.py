import math

from collections import Counter
from dataclasses import dataclass

from app.rag.documents import Chunk
from app.rag.retriever import tokenize


STOP_TERMS = frozenset({
    "玩家",
    "可以",
    "具体",
    "什么",
    "应该",
    "怎么",
    "多少",
    "家可",
    "以参",
    "么活",
    "该怎",
    "么办",
})


@dataclass(frozen=True)
class WeightedSearchHit:
    chunk: Chunk
    score: float
    matched_terms: tuple[str, ...]


def meaningful_terms(text: str) -> set[str]:
    """Remove common or weak lexical tokens."""

    return tokenize(text) - STOP_TERMS


class WeightedRetriever:
    """A simple in-memory IDF-weighted retriever."""

    def __init__(
        self,
        chunks: list[Chunk],
        *,
        numeric_boost: float = 3.0,
    ):
        if (
            not math.isfinite(numeric_boost)
            or numeric_boost < 1
        ):
            raise ValueError(
                "numeric_boost必须是大于等于1的有限数字"
            )

        self.numeric_boost = numeric_boost

        # Build an in-memory index once.
        self._indexed_chunks = [
            (chunk, meaningful_terms(chunk.content))
            for chunk in chunks
        ]

        self._document_frequency = Counter()

        for _, terms in self._indexed_chunks:
            self._document_frequency.update(terms)

    def idf(self, term: str) -> float:
        """Calculate smoothed inverse document frequency."""

        n = len(self._indexed_chunks)

        df = self._document_frequency.get(
            term,
            0,
        )

        return math.log(
            (n + 1) / (df + 1)
        ) + 1

    def term_weight(self, term: str) -> float:
        """Calculate the weight of one matched term."""

        weight = self.idf(term)

        if term.isascii() and term.isdigit():
            weight *= self.numeric_boost

        return weight

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        min_matches: int = 2,
        relative_threshold: float = 0.6,
    ) -> list[WeightedSearchHit]:
        """Search chunks with weighted lexical scoring."""

        if top_k < 1:
            raise ValueError("top_k必须大于等于1")

        if min_matches < 1:
            raise ValueError("min_matches必须大于等于1")

        if not 0 <= relative_threshold <= 1:
            raise ValueError(
                "relative_threshold必须在0到1之间"
            )

        query_terms = meaningful_terms(query)

        if not query_terms:
            return []

        hits = []

        for chunk, chunk_terms in self._indexed_chunks:
            matched = query_terms & chunk_terms

            if len(matched) < min_matches:
                continue

            score = sum(
                self.term_weight(term)
                for term in sorted(matched)
            )

            hits.append(
                WeightedSearchHit(
                    chunk=chunk,
                    score=score,
                    matched_terms=tuple(
                        sorted(matched)
                    ),
                )
            )

        if not hits:
            return []

        hits.sort(
            key=lambda hit: (
                -hit.score,
                hit.chunk.source,
                hit.chunk.id,
            )
        )

        best_score = hits[0].score

        # Remove candidates much weaker than the top hit.
        filtered = [
            hit
            for hit in hits
            if hit.score
            >= best_score * relative_threshold
        ]

        return filtered[:top_k]