from pathlib import Path

import pytest

from app.rag.documents import (
    Document,
    build_chunks,
    load_documents,
    split_document,
)
from app.rag.retriever import (
    format_context,
    search_chunks,
    tokenize,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

KNOWLEDGE_DIR = (
    PROJECT_ROOT / "data" / "knowledge"
)


def sample_chunks():
    documents = load_documents(KNOWLEDGE_DIR)

    return build_chunks(
        documents,
        chunk_size=180,
        overlap=40,
    )


# 1. Load the three sample Markdown documents.
def test_load_three_knowledge_documents():
    documents = load_documents(KNOWLEDGE_DIR)

    assert len(documents) == 3

    sources = {
        doc.source
        for doc in documents
    }

    assert sources == {
        "活动规则.md",
        "账号安全.md",
        "客服指南.md",
    }

    assert all(doc.content for doc in documents)


# 2. Reject a nonexistent knowledge directory.
def test_missing_directory_is_rejected(tmp_path):
    missing = tmp_path / "not-exists"

    with pytest.raises(
        ValueError,
        match="知识库目录不存在",
    ):
        load_documents(missing)


# 3. Empty Markdown files are ignored.
def test_empty_documents_are_skipped(tmp_path):
    (tmp_path / "empty.md").write_text(
        " \n ",
        encoding="utf-8",
    )

    (tmp_path / "valid.md").write_text(
        "有效文档内容",
        encoding="utf-8",
    )

    documents = load_documents(tmp_path)

    assert len(documents) == 1
    assert documents[0].source == "valid.md"


# 4. Chunk boundaries and overlaps are correct.
def test_chunk_overlap_and_positions():
    document = Document(
        id="test",
        source="test.md",
        content="ABCDEFGHIJKL",
    )

    chunks = split_document(
        document,
        chunk_size=5,
        overlap=2,
    )

    assert [chunk.content for chunk in chunks] == [
        "ABCDE",
        "DEFGH",
        "GHIJK",
        "JKL",
    ]

    assert [
        (chunk.start, chunk.end)
        for chunk in chunks
    ] == [
        (0, 5),
        (3, 8),
        (6, 11),
        (9, 12),
    ]


# 5. Invalid chunk settings are rejected.
def test_invalid_chunk_settings():
    document = Document(
        id="test",
        source="test.md",
        content="Hello world",
    )

    with pytest.raises(ValueError):
        split_document(
            document,
            chunk_size=0,
        )

    with pytest.raises(ValueError):
        split_document(
            document,
            chunk_size=5,
            overlap=5,
        )

    with pytest.raises(ValueError):
        split_document(
            document,
            chunk_size=5,
            overlap=-1,
        )


# 6. Tokenization supports Chinese and numbers.
def test_chinese_and_number_tokenization():
    tokens = tokenize("50级玩家参加活动")

    assert "50" in tokens
    assert "玩家" in tokens
    assert "参加" in tokens
    assert "活动" in tokens


# 7. Activity questions retrieve activity rules.
def test_activity_question_retrieval():
    chunks = sample_chunks()

    hits = search_chunks(
        "50级玩家可以参加什么活动？",
        chunks,
        top_k=3,
    )

    assert hits
    assert hits[0].chunk.source == "活动规则.md"
    assert hits[0].score > 0

    assert "周末挑战活动" in hits[0].chunk.content


# 8. Account recovery questions retrieve help content.
def test_account_recovery_retrieval():
    chunks = sample_chunks()

    hits = search_chunks(
        "玩家忘记账号后应该怎么办？",
        chunks,
        top_k=3,
    )

    assert hits
    assert hits[0].chunk.source == "客服指南.md"
    assert "账号找回" in hits[0].chunk.content


# 9. Unrelated questions should have no lexical hits.
def test_unrelated_question_returns_no_hits():
    chunks = sample_chunks()

    hits = search_chunks(
        "火星基地的具体坐标是多少？",
        chunks,
    )

    assert hits == []
    assert format_context(hits) == (
        "没有检索到相关知识库内容。"
    )


# 10. Top-k and source formatting work together.
def test_top_k_and_source_context():
    chunks = sample_chunks()

    hits = search_chunks(
        "50级玩家可以参加什么活动？",
        chunks,
        top_k=1,
    )

    assert len(hits) == 1

    context = format_context(hits)

    assert "来源：活动规则.md" in context
    assert "片段ID：" in context
    assert "周末挑战活动" in context

    with pytest.raises(
        ValueError,
        match="top_k必须大于等于1",
    ):
        search_chunks(
            "活动",
            chunks,
            top_k=0,
        )