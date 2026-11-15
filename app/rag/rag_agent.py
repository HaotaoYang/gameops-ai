import re

from dataclasses import dataclass
from typing import Literal

from openai import OpenAI

from app.llm import ask_model

from app.rag.rag_prompt import (
    INSUFFICIENT_ANSWER,
    RAG_INSTRUCTIONS,
    build_rag_prompt,
)

from app.rag.weighted_retriever import (
    WeightedRetriever,
    WeightedSearchHit,
)


RagStatus = Literal[
    "answered",
    "insufficient_evidence",
    "rejected",
    "failed",
]


@dataclass(frozen=True)
class RagSource:
    reference: str
    source: str
    heading: str
    chunk_id: str
    score: float


@dataclass(frozen=True)
class RagResult:
    status: RagStatus
    answer: str
    sources: tuple[RagSource, ...]
    retrieved_count: int
    model_called: bool
    issues: tuple[str, ...] = ()


CITATION_PATTERN = re.compile(
    r"\[资料(\d+)\]"
)


def extract_citations(answer: str) -> tuple[int, ...]:
    """Extract unique citation IDs in appearance order."""

    references = CITATION_PATTERN.findall(answer)

    return tuple(
        dict.fromkeys(
            int(reference)
            for reference in references
        )
    )


def validate_citations(
    answer: str,
    *,
    source_count: int,
) -> list[str]:
    """Check citation existence and numeric ranges."""

    citations = extract_citations(answer)

    if not citations:
        return ["回答缺少有效的资料引用"]

    issues = []

    for citation in citations:
        if not 1 <= citation <= source_count:
            issues.append(
                f"引用了不存在的资料编号：{citation}"
            )

    return issues


def build_source(
    index: int,
    hit: WeightedSearchHit,
) -> RagSource:
    """Create a source record from actual retrieval data."""

    return RagSource(
        reference=f"资料{index}",
        source=hit.chunk.source,
        heading=getattr(
            hit.chunk,
            "heading",
            "",
        ),
        chunk_id=hit.chunk.id,
        score=hit.score,
    )


def run_rag(
    question: str,
    retriever: WeightedRetriever,
    *,
    client: OpenAI | None = None,
    top_k: int = 3,
) -> RagResult:
    """Run retrieval, augmentation and generation."""

    if not question.strip():
        raise ValueError("问题不能为空")

    # Step 1: retrieve knowledge.
    hits = retriever.search(
        question,
        top_k=top_k,
    )

    # Step 2: do not call the model without evidence.
    if not hits:
        return RagResult(
            status="insufficient_evidence",
            answer=INSUFFICIENT_ANSWER,
            sources=(),
            retrieved_count=0,
            model_called=False,
        )

    # Step 3: build the augmented question.
    prompt = build_rag_prompt(
        question,
        hits,
    )

    # Step 4: call the existing LLM module.
    try:
        model_answer = ask_model(
            prompt,
            client=client,
            instructions=RAG_INSTRUCTIONS,
        ).strip()

    except Exception:
        return RagResult(
            status="failed",
            answer="知识库问答暂时不可用，请稍后重试。",
            sources=(),
            retrieved_count=len(hits),
            model_called=True,
            issues=("MODEL_REQUEST_FAILED",),
        )

    # Step 5: allow the model to abstain.
    if model_answer == INSUFFICIENT_ANSWER:
        return RagResult(
            status="insufficient_evidence",
            answer=INSUFFICIENT_ANSWER,
            sources=(),
            retrieved_count=len(hits),
            model_called=True,
        )

    # Step 6: validate citation IDs.
    issues = validate_citations(
        model_answer,
        source_count=len(hits),
    )

    if issues:
        return RagResult(
            status="rejected",
            answer="回答未通过资料引用检查，暂不展示。",
            sources=(),
            retrieved_count=len(hits),
            model_called=True,
            issues=tuple(issues),
        )

    # Step 7: build source metadata from real hits.
    citations = extract_citations(model_answer)

    sources = tuple(
        build_source(
            index,
            hits[index - 1],
        )
        for index in citations
    )

    return RagResult(
        status="answered",
        answer=model_answer,
        sources=sources,
        retrieved_count=len(hits),
        model_called=True,
    )