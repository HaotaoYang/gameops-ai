import re

from dataclasses import dataclass

from app.rag.documents import Chunk


@dataclass(frozen=True)
class SearchHit:
    """One ranked search result."""

    chunk: Chunk
    score: int
    matched_terms: tuple[str, ...]


def tokenize(text: str) -> set[str]:
    """
    Extract English/number tokens and Chinese bigrams.

    This is a simple lexical tokenizer, not an
    embedding model or full Chinese word segmenter.
    """

    tokens = set()

    parts = re.findall(
        r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+",
        text.lower(),
    )

    for part in parts:
        # Chinese continuous text.
        if re.fullmatch(
            r"[\u4e00-\u9fff]+",
            part,
        ):
            if len(part) == 1:
                tokens.add(part)
            else:
                for i in range(len(part) - 1):
                    tokens.add(part[i:i + 2])

        # English words and numbers.
        else:
            tokens.add(part)

    return tokens


def search_chunks(
    query: str,
    chunks: list[Chunk],
    *,
    top_k: int = 3,
) -> list[SearchHit]:
    """Return chunks ranked by lexical term overlap."""

    if top_k < 1:
        raise ValueError("top_k必须大于等于1")

    query_terms = tokenize(query)

    if not query_terms:
        return []

    hits = []

    for chunk in chunks:
        chunk_terms = tokenize(chunk.content)

        matched = query_terms & chunk_terms

        score = len(matched)

        # Never return an unrelated zero-score chunk.
        if score == 0:
            continue

        hits.append(
            SearchHit(
                chunk=chunk,
                score=score,
                matched_terms=tuple(sorted(matched)),
            )
        )

    # Highest score first, deterministic tie-breaking.
    hits.sort(
        key=lambda hit: (
            -hit.score,
            hit.chunk.source,
            hit.chunk.id,
        )
    )

    return hits[:top_k]


def format_context(
    hits: list[SearchHit],
) -> str:
    """Format retrieved evidence with source metadata."""

    if not hits:
        return "没有检索到相关知识库内容。"

    sections = []

    for index, hit in enumerate(hits, start=1):
        sections.append(
            f"[资料{index}]\n"
            f"来源：{hit.chunk.source}\n"
            f"片段ID：{hit.chunk.id}\n"
            f"内容：\n{hit.chunk.content}"
        )

    return "\n\n---\n\n".join(sections)