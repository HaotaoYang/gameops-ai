import json
import re

from dataclasses import dataclass
from pathlib import Path

from app.rag.rag_agent import (
    extract_citations,
    validate_citations,
)

from app.rag.rag_prompt import (
    INSUFFICIENT_ANSWER,
)


@dataclass(frozen=True)
class EvalCase:
    """One manually labelled evaluation case."""

    id: str
    question: str
    expected_sources: tuple[str, ...]
    expected_headings: tuple[str, ...]
    expected_status: str
    required_terms: tuple[str, ...]
    forbidden_terms: tuple[str, ...]
    sample_answer: str
    sample_origin: str


@dataclass(frozen=True)
class RetrievalEvaluation:
    hit: bool
    precision: float | None
    recall: float | None
    returned_count: int
    relevant_count: int
    matched_count: int
    correct_empty: bool


@dataclass(frozen=True)
class AnswerEvaluation:
    passed: bool
    status_correct: bool
    required_terms_present: bool
    citations_valid: bool
    sources_correct: bool
    numbers_supported: bool
    issues: tuple[str, ...]


def load_eval_cases(path: Path) -> list[EvalCase]:
    """Load the golden evaluation dataset."""

    raw_cases = json.loads(
        path.read_text(encoding="utf-8")
    )

    cases = []

    for raw in raw_cases:
        cases.append(
            EvalCase(
                id=raw["id"],
                question=raw["question"],
                expected_sources=tuple(
                    raw["expected_sources"]
                ),
                expected_headings=tuple(
                    raw["expected_headings"]
                ),
                expected_status=raw[
                    "expected_status"
                ],
                required_terms=tuple(
                    raw["required_terms"]
                ),
                forbidden_terms=tuple(
                    raw["forbidden_terms"]
                ),
                sample_answer=raw[
                    "sample_answer"
                ],
                sample_origin=raw[
                    "sample_origin"
                ],
            )
        )

    ids = [case.id for case in cases]

    if len(ids) != len(set(ids)):
        raise ValueError("评测数据存在重复ID")

    return cases


def evaluate_retrieval(
    retrieved_ids: list[str],
    expected_ids: list[str] | tuple[str, ...],
) -> RetrievalEvaluation:
    """Evaluate retrieval with unique evidence IDs."""

    retrieved = set(retrieved_ids)
    expected = set(expected_ids)

    matched = retrieved & expected

    precision = (
        len(matched) / len(retrieved)
        if retrieved
        else None
    )

    recall = (
        len(matched) / len(expected)
        if expected
        else None
    )

    return RetrievalEvaluation(
        hit=bool(matched),
        precision=precision,
        recall=recall,
        returned_count=len(retrieved),
        relevant_count=len(expected),
        matched_count=len(matched),
        correct_empty=(
            not retrieved and not expected
        ),
    )


def summarize_retrieval(
    results: list[RetrievalEvaluation],
) -> dict:
    """Summarize answerable retrieval targets separately
    from cases with no relevant documents.
    """

    positive = [
        result
        for result in results
        if result.relevant_count > 0
    ]

    negative = [
        result
        for result in results
        if result.relevant_count == 0
    ]

    def average(values):
        return (
            sum(values) / len(values)
            if values
            else None
        )

    return {
        "case_count": len(results),

        "positive_count": len(positive),

        "negative_count": len(negative),

        "hit_rate": average([
            int(result.hit)
            for result in positive
        ]),

        # For macro precision, use zero for
        # positive cases with no retrieved results.
        "macro_precision": average([
            result.precision
            if result.precision is not None
            else 0.0
            for result in positive
        ]),

        "macro_recall": average([
            result.recall
            for result in positive
        ]),

        "empty_accuracy": average([
            int(result.correct_empty)
            for result in negative
        ]),
    }


NUMBER_PATTERN = re.compile(
    r"[0-9]+(?:\.[0-9]+)?"
)


def extract_numbers(text: str) -> set[str]:
    """Extract simple Arabic numeric tokens.

    Remove citation IDs before extracting numbers.
    """

    cleaned = re.sub(
        r"\[资料\d+\]",
        "",
        text,
    )

    return set(
        NUMBER_PATTERN.findall(cleaned)
    )


def find_unsupported_numbers(
    answer: str,
    evidence_texts: list[str],
) -> set[str]:
    """Detect numeric tokens absent from cited evidence."""

    supported = set()

    for text in evidence_texts:
        supported.update(
            extract_numbers(text)
        )

    return (
        extract_numbers(answer) - supported
    )


def evaluate_answer(
    case: EvalCase,
    *,
    answer: str,
    status: str,
    hits: list,
) -> AnswerEvaluation:
    """Evaluate known answer requirements and citations.

    This is a limited rule-based check, not a complete
    semantic correctness or faithfulness evaluator.
    """

    issues = []

    status_correct = (
        status == case.expected_status
    )

    if not status_correct:
        issues.append(
            f"状态错误：预期{case.expected_status}，"
            f"实际{status}"
        )

    # Non-answering cases must actually abstain.
    if case.expected_status == (
        "insufficient_evidence"
    ):
        if answer.strip() != INSUFFICIENT_ANSWER:
            issues.append("未返回标准资料不足提示")

        return AnswerEvaluation(
            passed=not issues,
            status_correct=status_correct,
            required_terms_present=True,
            citations_valid=True,
            sources_correct=True,
            numbers_supported=True,
            issues=tuple(issues),
        )

    # Check the known required answer content.
    missing_terms = [
        term
        for term in case.required_terms
        if term not in answer
    ]

    for term in missing_terms:
        issues.append(
            f"缺少必要内容：{term}"
        )

    for term in case.forbidden_terms:
        if term in answer:
            issues.append(
                f"出现已知错误表述：{term}"
            )

    # Validate citation IDs against actual hits.
    citation_issues = validate_citations(
        answer,
        source_count=len(hits),
    )

    issues.extend(citation_issues)

    citation_ids = extract_citations(answer)

    cited_chunks = [
        hits[index - 1].chunk
        for index in citation_ids
        if 1 <= index <= len(hits)
    ]

    cited_sources = {
        chunk.source
        for chunk in cited_chunks
    }

    cited_headings = {
        getattr(chunk, "heading", "")
        for chunk in cited_chunks
    }

    sources_correct = (
        not citation_issues
        and cited_sources
        == set(case.expected_sources)
        and cited_headings
        == set(case.expected_headings)
    )

    if not sources_correct:
        issues.append("引用来源或章节不符合预期")

    # Only cited evidence can support answer numbers.
    unsupported = find_unsupported_numbers(
        answer,
        [
            chunk.content
            for chunk in cited_chunks
        ],
    )

    for number in sorted(unsupported):
        issues.append(
            f"引用资料不包含数字：{number}"
        )

    return AnswerEvaluation(
        passed=not issues,
        status_correct=status_correct,
        required_terms_present=not missing_terms,
        citations_valid=not citation_issues,
        sources_correct=sources_correct,
        numbers_supported=not unsupported,
        issues=tuple(issues),
    )