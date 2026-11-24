import pytest

from app.rag.documents import Chunk

from app.rag.weighted_retriever import (
    WeightedRetriever,
    WeightedSearchHit,
)

from app.rag.vector_retriever import (
    VectorRetriever,
    VectorSearchHit,
)

from app.rag.hybrid_retriever import (
    fuse_rrf,
    HybridRetriever,
)


def make_chunk(name):
    return Chunk(
        id=f"{name}#chunk-0",
        document_id=name,
        source=f"{name}.md",
        content=name,
        start=0,
        end=len(name),
    )


A = make_chunk("账号找回")
B = make_chunk("密码保护")
C = make_chunk("联系客服")
D = make_chunk("异常登录")


def keyword_hits(*chunks):
    return [
        WeightedSearchHit(
            chunk=chunk,
            score=float(len(chunks) - index),
            matched_terms=("测试",),
        )
        for index, chunk in enumerate(chunks)
    ]


def vector_hits(*chunks):
    return [
        VectorSearchHit(
            chunk=chunk,
            score=1.0 - index * 0.1,
        )
        for index, chunk in enumerate(chunks)
    ]


# 1. RRF combines both ranking contributions.
def test_rrf_both_sources():
    hits = fuse_rrf(
        keyword_hits(A, B, C),
        vector_hits(D, A, B),
        top_k=4,
    )

    assert hits[0].chunk == A

    assert hits[0].keyword_rank == 1
    assert hits[0].vector_rank == 2

    assert hits[0].score == pytest.approx(
        1 / 61 + 1 / 62
    )


# 2. An item in both lists can outrank a single-list item.
def test_rrf_shared_candidate_advantage():
    hits = fuse_rrf(
        keyword_hits(A, B),
        vector_hits(C, B),
        top_k=3,
    )

    assert hits[0].chunk == B

    assert hits[0].score == pytest.approx(
        2 / 62
    )


# 3. Results are deduplicated by Chunk ID.
def test_rrf_deduplicates_results():
    results = fuse_rrf(
        keyword_hits(A, A, B),
        vector_hits(A, C),
        top_k=10,
    )

    assert len(results) == 3

    ids = [
        result.chunk.id
        for result in results
    ]

    assert len(ids) == len(set(ids))

    first = next(
        hit for hit in results
        if hit.chunk.id == A.id
    )

    assert first.score == pytest.approx(
        1 / 61 + 1 / 61
    )


# 4. One retrieval source can be empty.
def test_rrf_single_source():
    results = fuse_rrf(
        [],
        vector_hits(A, B),
        top_k=3,
    )

    assert [
        result.chunk
        for result in results
    ] == [A, B]

    assert all(
        result.keyword_rank is None
        for result in results
    )


# 5. No candidates means no results.
def test_rrf_empty_lists():
    assert fuse_rrf([], []) == []


# 6. Top-K limits the final results.
def test_rrf_top_k():
    results = fuse_rrf(
        keyword_hits(A, B, C),
        vector_hits(C, B, D),
        top_k=2,
    )

    assert len(results) == 2

    assert results[0].score >= (
        results[1].score
    )


# 7. Weighting changes the final ranking.
def test_rrf_weights():
    results = fuse_rrf(
        keyword_hits(A, B),
        vector_hits(B, A),
        keyword_weight=3.0,
        vector_weight=1.0,
    )

    assert results[0].chunk == A

    assert results[0].score == pytest.approx(
        3 / 61 + 1 / 62
    )


# 8. Invalid parameters are rejected.
def test_rrf_invalid_parameters():
    with pytest.raises(ValueError):
        fuse_rrf(
            keyword_hits(A),
            vector_hits(B),
            top_k=0,
        )

    with pytest.raises(ValueError):
        fuse_rrf(
            keyword_hits(A),
            vector_hits(B),
            rrf_k=0,
        )

    with pytest.raises(ValueError):
        fuse_rrf(
            keyword_hits(A),
            vector_hits(B),
            keyword_weight=-1,
        )

    with pytest.raises(ValueError):
        fuse_rrf(
            keyword_hits(A),
            vector_hits(B),
            keyword_weight=0,
            vector_weight=0,
        )

    with pytest.raises(ValueError):
        fuse_rrf(
            keyword_hits(A),
            vector_hits(B),
            vector_weight=float("nan"),
        )


# 9. HybridRetriever integrates the existing modules.
def test_hybrid_retriever_integration():
    chunks = [A, B, C]

    vectors = [
        [1.0, 0.0],
        [0.0, 1.0],
        [0.8, 0.6],
    ]

    keyword = WeightedRetriever(chunks)

    vector = VectorRetriever(
        chunks,
        vectors,
    )

    hybrid = HybridRetriever(
        keyword,
        vector,
    )

    result = hybrid.search(
        "账号找回",
        [1.0, 0.0],
        candidate_k=3,
        top_k=2,
    )

    assert len(result) == 2

    assert result[0].chunk.id == A.id

    assert result[0].vector_rank == 1


# 10. RRF alone does not guarantee rejection
# of an irrelevant question.
def test_hybrid_requires_separate_relevance_guard():
    chunks = [A, B]

    keyword = WeightedRetriever(chunks)

    vector = VectorRetriever(
        chunks,
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ],
    )

    hybrid = HybridRetriever(
        keyword,
        vector,
    )

    result = hybrid.search(
        "火星基地的具体坐标是多少？",
        [0.0, 1.0],
        candidate_k=2,
        top_k=2,
    )

    # Keyword search has no relevant hits.
    assert keyword.search(
        "火星基地的具体坐标是多少？"
    ) == []

    # Yet vector ranking still returns candidates.
    assert len(result) == 2

    assert result[0].vector_rank == 1