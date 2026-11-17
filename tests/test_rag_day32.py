from pathlib import Path

import pytest

from app.rag.documents import load_documents

from app.rag.section_chunker import (
    build_section_chunks,
)

from app.rag.weighted_retriever import (
    WeightedRetriever,
)

from app.rag.rag_prompt import (
    INSUFFICIENT_ANSWER,
)

from app.rag.evaluation import (
    load_eval_cases,
    evaluate_retrieval,
    summarize_retrieval,
    extract_numbers,
    find_unsupported_numbers,
    evaluate_answer,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]


CASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "rag_cases.json"
)


KNOWLEDGE_DIR = (
    PROJECT_ROOT
    / "data"
    / "knowledge"
)


def get_case(case_id):
    cases = load_eval_cases(CASE_PATH)

    return next(
        case
        for case in cases
        if case.id == case_id
    )


def make_retriever():
    documents = load_documents(
        KNOWLEDGE_DIR
    )

    chunks = build_section_chunks(
        documents
    )

    return WeightedRetriever(chunks)


# 1. The golden dataset has six unique cases.
def test_load_golden_dataset():
    cases = load_eval_cases(CASE_PATH)

    assert len(cases) == 6

    assert len({
        case.id for case in cases
    }) == 6

    assert sum(
        case.expected_status == "answered"
        for case in cases
    ) == 4

    assert sum(
        case.expected_status
        == "insufficient_evidence"
        for case in cases
    ) == 2

    assert sum(
        case.sample_origin == "day31_real"
        for case in cases
    ) == 4


# 2. Retrieval metrics are mathematically correct.
def test_retrieval_metrics():
    result = evaluate_retrieval(
        ["a.md", "b.md", "c.md"],
        ["a.md", "d.md"],
    )

    assert result.hit is True
    assert result.matched_count == 1

    assert result.precision == (
        pytest.approx(1 / 3)
    )

    assert result.recall == (
        pytest.approx(1 / 2)
    )


# 3. Duplicate document IDs do not inflate scores.
def test_duplicate_sources_are_deduplicated():
    result = evaluate_retrieval(
        ["a.md", "a.md", "b.md"],
        ["a.md"],
    )

    assert result.returned_count == 2
    assert result.matched_count == 1

    assert result.precision == 0.5
    assert result.recall == 1.0


# 4. Empty results and missed evidence differ.
def test_empty_retrieval_cases():
    correct_empty = evaluate_retrieval(
        [],
        [],
    )

    assert correct_empty.correct_empty is True
    assert correct_empty.precision is None
    assert correct_empty.recall is None

    missed = evaluate_retrieval(
        [],
        ["a.md"],
    )

    assert missed.hit is False
    assert missed.correct_empty is False
    assert missed.precision is None
    assert missed.recall == 0.0

    false_positive = evaluate_retrieval(
        ["a.md"],
        [],
    )

    assert false_positive.correct_empty is False
    assert false_positive.precision == 0.0


# 5. Aggregate metrics use explicit conventions.
def test_retrieval_summary():
    results = [
        evaluate_retrieval(
            ["a.md"],
            ["a.md"],
        ),
        evaluate_retrieval(
            [],
            ["b.md"],
        ),
        evaluate_retrieval(
            [],
            [],
        ),
        evaluate_retrieval(
            ["c.md"],
            [],
        ),
    ]

    summary = summarize_retrieval(
        results
    )

    assert summary["case_count"] == 4

    assert summary["positive_count"] == 2
    assert summary["negative_count"] == 2

    assert summary["hit_rate"] == 0.5

    assert summary["macro_precision"] == 0.5
    assert summary["macro_recall"] == 0.5

    assert summary["empty_accuracy"] == 0.5


# 6. Citation numbers are not business numbers.
def test_numeric_extraction_ignores_citations():
    numbers = extract_numbers(
        "50级可以参加活动。"
        "报名时间18:00。[资料1]"
    )

    assert numbers == {
        "50",
        "18",
        "00",
    }


# 7. Unsupported numeric claims are detected.
def test_unsupported_numeric_claims():
    unsupported = (
        find_unsupported_numbers(
            "50级参加活动，奖励10000金币。[资料1]",
            [
                "玩家达到50级后可以参加活动。",
                "完成挑战后可获得金币奖励。",
            ],
        )
    )

    assert unsupported == {
        "10000",
    }


# 8. A correct grounded answer passes current checks.
def test_correct_rag_answer_passes():
    case = get_case("Q01")

    retriever = make_retriever()

    hits = retriever.search(
        case.question
    )

    result = evaluate_answer(
        case,
        answer=(
            "50级玩家可以参加"
            "周末挑战活动。[资料1]"
        ),
        status="answered",
        hits=hits,
    )

    assert result.passed is True
    assert result.status_correct is True

    assert result.required_terms_present is True
    assert result.citations_valid is True
    assert result.sources_correct is True
    assert result.numbers_supported is True

    assert result.issues == ()


# 9. Wrong facts and citations are detected.
def test_invalid_answer_is_detected():
    case = get_case("Q01")

    retriever = make_retriever()

    hits = retriever.search(
        case.question
    )

    bad_number = evaluate_answer(
        case,
        answer=(
            "50级玩家可以参加周末挑战活动，"
            "并获得10000金币。[资料1]"
        ),
        status="answered",
        hits=hits,
    )

    assert bad_number.passed is False
    assert bad_number.numbers_supported is False

    assert (
        "引用资料不包含数字：10000"
        in bad_number.issues
    )

    bad_citation = evaluate_answer(
        case,
        answer=(
            "50级玩家可以参加"
            "周末挑战活动。[资料9]"
        ),
        status="answered",
        hits=hits,
    )

    assert bad_citation.passed is False
    assert bad_citation.citations_valid is False

    missing_content = evaluate_answer(
        case,
        answer="可以参加活动。[资料1]",
        status="answered",
        hits=hits,
    )

    assert missing_content.passed is False

    assert (
        missing_content.required_terms_present
        is False
    )

    negative_claim = evaluate_answer(
        case,
        answer=(
            "50级玩家不能参加"
            "周末挑战活动。[资料1]"
        ),
        status="answered",
        hits=hits,
    )

    assert negative_claim.passed is False

    assert any(
        "出现已知错误表述" in issue
        for issue in negative_claim.issues
    )


# 10. Both abstention paths are evaluated.
def test_abstention_evaluation():
    retriever = make_retriever()

    for case_id in ("Q05", "Q06"):
        case = get_case(case_id)

        hits = retriever.search(
            case.question
        )

        result = evaluate_answer(
            case,
            answer=INSUFFICIENT_ANSWER,
            status="insufficient_evidence",
            hits=hits,
        )

        assert result.passed is True

        fabricated = evaluate_answer(
            case,
            answer="答案是2020年。[资料1]",
            status="answered",
            hits=hits,
        )

        assert fabricated.passed is False

        assert (
            fabricated.status_correct
            is False
        )