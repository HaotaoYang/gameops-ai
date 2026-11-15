from pathlib import Path

import pytest

from app.rag.documents import (
    Document,
    load_documents,
)
from app.rag.section_chunker import (
    build_section_chunks,
    split_by_heading,
)
from app.rag.weighted_retriever import (
    WeightedRetriever,
    meaningful_terms,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

KNOWLEDGE_DIR = (
    PROJECT_ROOT / "data" / "knowledge"
)


def sample_documents():
    return load_documents(KNOWLEDGE_DIR)


def sample_chunks():
    return build_section_chunks(
        sample_documents()
    )


# 1. The sample knowledge base contains six sections.
def test_six_section_chunks():
    chunks = sample_chunks()

    assert len(chunks) == 6

    assert {
        chunk.heading
        for chunk in chunks
    } == {
        "周末挑战活动",
        "新手成长活动",
        "密码保护",
        "异常登录",
        "联系客服",
        "账号找回",
    }


# 2. Every Chunk maps back to the original document.
def test_original_document_positions():
    documents = sample_documents()

    for document in documents:
        chunks = split_by_heading(document)

        for chunk in chunks:
            assert chunk.document_id == document.id
            assert chunk.source == document.source

            assert chunk.content == (
                document.content[
                    chunk.start:chunk.end
                ]
            )


# 3. Long sections fall back to overlapping windows.
def test_long_section_window_fallback():
    document = Document(
        id="long",
        source="long.md",
        content=(
            "# 测试文档\n\n"
            "## 长章节\n\n"
            + "这是需要切分的游戏规则。" * 50
        ),
    )

    chunks = split_by_heading(
        document,
        chunk_size=60,
        overlap=10,
    )

    assert len(chunks) > 1

    assert all(
        len(chunk.content) <= 60
        for chunk in chunks
    )

    assert all(
        chunk.heading == "长章节"
        for chunk in chunks
    )

    for previous, current in zip(
        chunks,
        chunks[1:],
    ):
        assert previous.end - current.start == 10

        assert (
            previous.content[-10:]
            == current.content[:10]
        )


# 4. Documents without headings are still searchable.
def test_document_without_headings():
    document = Document(
        id="plain",
        source="plain.md",
        content="玩家可以通过客服申请账号找回。",
    )

    chunks = split_by_heading(document)

    assert len(chunks) == 1
    assert chunks[0].content == document.content
    assert chunks[0].heading == "plain"


# 5. Stop terms are removed, meaningful terms retained.
def test_stop_terms_are_removed():
    terms = meaningful_terms(
        "50级玩家可以参加什么活动？"
    )

    assert "玩家" not in terms
    assert "可以" not in terms
    assert "什么" not in terms

    assert "50" in terms
    assert "参加" in terms
    assert "活动" in terms


# 6. Rare terms receive larger IDF weights.
def test_rare_term_has_higher_idf():
    documents = [
        Document(
            id="a",
            source="a.md",
            content="活动 金币",
        ),
        Document(
            id="b",
            source="b.md",
            content="活动 装备",
        ),
        Document(
            id="c",
            source="c.md",
            content="活动 经验",
        ),
    ]

    retriever = WeightedRetriever(
        build_section_chunks(documents)
    )

    assert retriever.idf("金币") > (
        retriever.idf("活动")
    )

    assert retriever.idf("活动") == (
        pytest.approx(1.0)
    )


# 7. Numeric weighting and filtering improve activity search.
def test_activity_search_is_more_precise():
    retriever = WeightedRetriever(sample_chunks())

    hits = retriever.search(
        "50级玩家可以参加什么活动？"
    )

    assert len(hits) == 1

    assert hits[0].chunk.source == "活动规则.md"
    assert hits[0].chunk.heading == "周末挑战活动"

    assert "50" in hits[0].matched_terms

    assert retriever.term_weight("50") == (
        pytest.approx(
            retriever.idf("50") * 3
        )
    )


# 8. Account recovery retrieves the correct section.
def test_account_recovery_is_more_precise():
    retriever = WeightedRetriever(sample_chunks())

    hits = retriever.search(
        "玩家忘记账号后应该怎么办？"
    )

    assert len(hits) == 1

    assert hits[0].chunk.source == "客服指南.md"
    assert hits[0].chunk.heading == "账号找回"

    assert "身份验证" in hits[0].chunk.content


# 9. Unrelated and empty questions return no hits.
def test_unrelated_and_empty_questions():
    retriever = WeightedRetriever(sample_chunks())

    assert retriever.search(
        "火星基地的具体坐标是多少？"
    ) == []

    assert retriever.search("") == []
    assert retriever.search("玩家 可以") == []

    empty_retriever = WeightedRetriever([])

    assert empty_retriever.search(
        "账号找回"
    ) == []


# 10. Both relative filtering and top-k work correctly.
def test_relative_threshold_and_top_k():
    retriever = WeightedRetriever(sample_chunks())

    loose_hits = retriever.search(
        "50级玩家可以参加什么活动？",
        relative_threshold=0,
        top_k=10,
    )

    strict_hits = retriever.search(
        "50级玩家可以参加什么活动？",
        relative_threshold=0.6,
        top_k=10,
    )

    assert len(loose_hits) >= 2
    assert len(strict_hits) == 1

    top_one = retriever.search(
        "50级玩家可以参加什么活动？",
        relative_threshold=0,
        top_k=1,
    )

    assert len(top_one) == 1
    assert top_one[0] == loose_hits[0]

    with pytest.raises(ValueError):
        retriever.search("活动", top_k=0)

    with pytest.raises(ValueError):
        retriever.search(
            "活动",
            relative_threshold=1.5,
        )

    with pytest.raises(ValueError):
        retriever.search(
            "活动",
            min_matches=0,
        )