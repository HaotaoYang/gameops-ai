import json

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

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
    RAG_INSTRUCTIONS,
    build_rag_prompt,
)

from app.rag.rag_agent import (
    extract_citations,
    validate_citations,
    run_rag,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

KNOWLEDGE_DIR = (
    PROJECT_ROOT / "data" / "knowledge"
)


ACTIVITY_QUESTION = (
    "50级玩家可以参加什么活动？"
)


ACCOUNT_QUESTION = (
    "玩家忘记账号后应该怎么办？"
)


def make_retriever():
    documents = load_documents(
        KNOWLEDGE_DIR
    )

    chunks = build_section_chunks(
        documents
    )

    return WeightedRetriever(chunks)


def make_client(answer):
    client = Mock()

    client.responses.create.return_value = (
        SimpleNamespace(
            output_text=answer,
        )
    )

    return client


# 1. The prompt contains real retrieved evidence.
def test_rag_prompt_contains_source_and_question():
    retriever = make_retriever()

    hits = retriever.search(
        ACTIVITY_QUESTION
    )

    prompt = build_rag_prompt(
        ACTIVITY_QUESTION,
        hits,
    )

    payload = json.loads(prompt)

    assert (
        payload["question"]
        == ACTIVITY_QUESTION
    )

    evidence = payload["knowledge_base"]

    assert len(evidence) == 1

    assert evidence[0]["reference"] == "资料1"

    assert (
        evidence[0]["source"]
        == "活动规则.md"
    )

    assert (
        evidence[0]["heading"]
        == "周末挑战活动"
    )

    assert (
        "50级" in evidence[0]["content"]
    )


# 2. Citation IDs are extracted and deduplicated.
def test_extract_unique_citations():
    answer = (
        "活动规则见[资料2]。"
        "奖励见[资料1]。"
        "时间见[资料2]。"
    )

    assert extract_citations(answer) == (2, 1)

    assert extract_citations(
        "没有引用的回答"
    ) == ()


# 3. Missing and invalid citations are detected.
def test_validate_citation_ranges():
    assert validate_citations(
        "回答内容。[资料1]",
        source_count=1,
    ) == []

    assert validate_citations(
        "没有引用的回答",
        source_count=1,
    ) == [
        "回答缺少有效的资料引用"
    ]

    assert validate_citations(
        "活动规则。[资料9]",
        source_count=1,
    ) == [
        "引用了不存在的资料编号：9"
    ]

    assert validate_citations(
        "活动规则。[资料0]",
        source_count=1,
    ) == [
        "引用了不存在的资料编号：0"
    ]


# 4. The complete activity RAG workflow succeeds.
def test_activity_rag_answer():
    retriever = make_retriever()

    client = make_client(
        "50级玩家可以参加周末挑战活动。[资料1]"
    )

    result = run_rag(
        ACTIVITY_QUESTION,
        retriever,
        client=client,
    )

    assert result.status == "answered"
    assert result.model_called is True
    assert result.retrieved_count == 1

    assert "周末挑战活动" in result.answer

    assert len(result.sources) == 1

    source = result.sources[0]

    assert source.reference == "资料1"
    assert source.source == "活动规则.md"
    assert source.heading == "周末挑战活动"

    assert (
        source.chunk_id
        == "活动规则#section-0#chunk-0"
    )

    client.responses.create.assert_called_once()

    kwargs = (
        client.responses.create.call_args.kwargs
    )

    assert (
        kwargs["instructions"]
        == RAG_INSTRUCTIONS
    )


# 5. Account recovery returns its real source.
def test_account_recovery_rag_answer():
    retriever = make_retriever()

    client = make_client(
        "通过客服申请账号找回，"
        "并完成身份验证。[资料1]"
    )

    result = run_rag(
        ACCOUNT_QUESTION,
        retriever,
        client=client,
    )

    assert result.status == "answered"

    assert "身份验证" in result.answer

    assert result.sources[0].source == (
        "客服指南.md"
    )

    assert result.sources[0].heading == (
        "账号找回"
    )


# 6. No evidence means no model API request.
def test_no_evidence_skips_model():
    retriever = make_retriever()

    client = Mock()

    result = run_rag(
        "火星基地的具体坐标是多少？",
        retriever,
        client=client,
    )

    assert result.status == (
        "insufficient_evidence"
    )

    assert result.model_called is False
    assert result.retrieved_count == 0
    assert result.sources == ()
    assert result.answer == INSUFFICIENT_ANSWER

    client.responses.create.assert_not_called()


# 7. The model can abstain after retrieval.
def test_model_abstains_when_evidence_insufficient():
    retriever = make_retriever()

    client = make_client(
        INSUFFICIENT_ANSWER
    )

    result = run_rag(
        "周末挑战活动是哪一年首次上线的？",
        retriever,
        client=client,
    )

    assert result.status == (
        "insufficient_evidence"
    )

    assert result.model_called is True
    assert result.retrieved_count > 0
    assert result.sources == ()

    client.responses.create.assert_called_once()


# 8. Invalid citations are rejected.
def test_invalid_model_citation_rejected():
    retriever = make_retriever()

    client = make_client(
        "50级可以参加周末挑战活动。[资料9]"
    )

    result = run_rag(
        ACTIVITY_QUESTION,
        retriever,
        client=client,
    )

    assert result.status == "rejected"
    assert result.sources == ()

    assert (
        "引用了不存在的资料编号：9"
        in result.issues
    )

    assert "资料9" not in result.answer


# 9. Uncited answers are not published.
def test_missing_citation_rejected():
    retriever = make_retriever()

    client = make_client(
        "50级玩家可以参加周末挑战活动。"
    )

    result = run_rag(
        ACTIVITY_QUESTION,
        retriever,
        client=client,
    )

    assert result.status == "rejected"

    assert (
        "回答缺少有效的资料引用"
        in result.issues
    )

    assert result.sources == ()


# 10. Model errors are sanitized.
def test_model_error_is_safely_handled():
    retriever = make_retriever()

    client = Mock()

    client.responses.create.side_effect = (
        RuntimeError("internal-private-api-error")
    )

    result = run_rag(
        ACTIVITY_QUESTION,
        retriever,
        client=client,
    )

    assert result.status == "failed"

    assert result.model_called is True

    assert result.issues == (
        "MODEL_REQUEST_FAILED",
    )

    assert "internal-private-api-error" not in (
        result.answer
    )

    assert "internal-private-api-error" not in (
        str(result.issues)
    )

    with pytest.raises(
        ValueError,
        match="问题不能为空",
    ):
        run_rag(
            "   ",
            retriever,
            client=client,
        )