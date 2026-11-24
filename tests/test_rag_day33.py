import math

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.rag.documents import Chunk

from app.rag.embeddings import embed_texts

from app.rag.vector_retriever import (
    VectorRetriever,
    cosine_similarity,
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


def make_embedding_item(index, vector):
    return SimpleNamespace(
        index=index,
        embedding=vector,
    )


def make_embedding_client(items):
    client = Mock()

    client.embeddings.create.return_value = (
        SimpleNamespace(data=items)
    )

    return client


def sample_index():
    chunks = [
        make_chunk("账号找回"),
        make_chunk("周末挑战"),
        make_chunk("密码安全"),
    ]

    vectors = [
        [1.0, 0.0],
        [0.0, 1.0],
        [0.8, 0.6],
    ]

    return VectorRetriever(
        chunks,
        vectors,
    )


# 1. Identical vectors have similarity 1.
def test_identical_vectors():
    assert cosine_similarity(
        [1, 2, 3],
        [1, 2, 3],
    ) == pytest.approx(1.0)


# 2. Orthogonal and opposite vectors.
def test_vector_angles():
    assert cosine_similarity(
        [1, 0],
        [0, 1],
    ) == pytest.approx(0.0)

    assert cosine_similarity(
        [1, 0],
        [-1, 0],
    ) == pytest.approx(-1.0)


# 3. Different lengths do not change direction.
def test_cosine_scale_invariance():
    assert cosine_similarity(
        [1, 0],
        [10, 0],
    ) == pytest.approx(1.0)

    assert cosine_similarity(
        [1, 0],
        [0.8, 0.6],
    ) == pytest.approx(0.8)


# 4. Invalid input vectors are rejected.
def test_invalid_cosine_vectors():
    with pytest.raises(ValueError):
        cosine_similarity([], [])

    with pytest.raises(
        ValueError,
        match="向量维度不一致",
    ):
        cosine_similarity(
            [1, 2],
            [1],
        )

    with pytest.raises(
        ValueError,
        match="零向量",
    ):
        cosine_similarity(
            [0, 0],
            [1, 0],
        )

    with pytest.raises(ValueError):
        cosine_similarity(
            [float("nan"), 0],
            [1, 0],
        )


# 5. Vector retrieval sorts by similarity.
def test_vector_search_ranking():
    index = sample_index()

    hits = index.search(
        [1, 0],
        top_k=3,
    )

    assert [
        hit.chunk.source
        for hit in hits
    ] == [
        "账号找回.md",
        "密码安全.md",
        "周末挑战.md",
    ]

    assert [
        hit.score
        for hit in hits
    ] == pytest.approx([
        1.0,
        0.8,
        0.0,
    ])


# 6. Top-k and minimum score filter results.
def test_vector_search_filters():
    index = sample_index()

    hits = index.search(
        [1, 0],
        top_k=2,
        min_score=0.9,
    )

    assert len(hits) == 1

    assert hits[0].chunk.source == (
        "账号找回.md"
    )

    with pytest.raises(ValueError):
        index.search(
            [1, 0],
            top_k=0,
        )

    with pytest.raises(ValueError):
        index.search(
            [1, 0],
            min_score=1.5,
        )

    with pytest.raises(ValueError):
        index.search([1, 0, 0])


# 7. Index validation and empty index behavior.
def test_vector_index_validation():
    with pytest.raises(ValueError):
        VectorRetriever(
            [make_chunk("a")],
            [],
        )

    with pytest.raises(ValueError):
        VectorRetriever(
            [
                make_chunk("a"),
                make_chunk("b"),
            ],
            [
                [1.0, 0.0],
                [1.0],
            ],
        )

    with pytest.raises(ValueError):
        VectorRetriever(
            [make_chunk("a")],
            [[0.0, 0.0]],
        )

    empty = VectorRetriever([], [])

    assert empty.search([1, 0]) == []


# 8. Embedding API batch results preserve input order.
def test_embedding_batch_and_index_order():
    client = make_embedding_client([
        make_embedding_item(
            1,
            [0.0, 1.0],
        ),
        make_embedding_item(
            0,
            [1.0, 0.0],
        ),
    ])

    vectors = embed_texts(
        ["账号找回", "周末挑战"],
        client=client,
        model="test-embedding-model",
    )

    assert vectors == [
        [1.0, 0.0],
        [0.0, 1.0],
    ]

    client.embeddings.create.assert_called_once_with(
        model="test-embedding-model",
        input=["账号找回", "周末挑战"],
        encoding_format="float",
    )


# 9. Empty and invalid API inputs are handled safely.
def test_embedding_input_validation():
    client = Mock()

    assert embed_texts(
        [],
        client=client,
    ) == []

    client.embeddings.create.assert_not_called()

    with pytest.raises(ValueError):
        embed_texts(
            ["账号找回", "   "],
            client=client,
        )

    client.embeddings.create.assert_not_called()


# 10. Malformed embedding API results are rejected.
def test_invalid_embedding_response():
    duplicate_index = make_embedding_client([
        make_embedding_item(
            0,
            [1.0, 0.0],
        ),
        make_embedding_item(
            0,
            [0.0, 1.0],
        ),
    ])

    with pytest.raises(RuntimeError):
        embed_texts(
            ["A", "B"],
            client=duplicate_index,
        )

    wrong_dimensions = make_embedding_client([
        make_embedding_item(
            0,
            [1.0, 0.0],
        ),
        make_embedding_item(
            1,
            [1.0],
        ),
    ])

    with pytest.raises(
        RuntimeError,
        match="维度不一致",
    ):
        embed_texts(
            ["A", "B"],
            client=wrong_dimensions,
        )

    invalid_values = make_embedding_client([
        make_embedding_item(
            0,
            [math.inf, 0.0],
        ),
    ])

    with pytest.raises(RuntimeError):
        embed_texts(
            ["A"],
            client=invalid_values,
        )