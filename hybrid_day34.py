from pathlib import Path

from app.rag.documents import load_documents
from app.rag.section_chunker import build_section_chunks

from app.rag.weighted_retriever import (
    WeightedRetriever,
)

from app.rag.vector_retriever import (
    VectorRetriever,
)

from app.rag.hybrid_retriever import (
    HybridRetriever,
)


# Teaching vectors, not real model embeddings.
MOCK_VECTORS = {
    "账号找回": [1.0, 0.0, 0.0],
    "联系客服": [0.85, 0.15, 0.0],
    "密码保护": [0.70, 0.30, 0.0],
    "异常登录": [0.75, 0.25, 0.0],
    "周末挑战活动": [0.0, 1.0, 0.0],
    "新手成长活动": [0.0, 0.8, 0.2],
}


QUESTIONS = [
    (
        "50级玩家可以参加什么活动？",
        [0.0, 1.0, 0.0],
    ),
    (
        "玩家忘记账号后应该怎么办？",
        [1.0, 0.0, 0.0],
    ),
    (
        "游戏登录凭证丢了，如何恢复？",
        [0.98, 0.02, 0.0],
    ),
    (
        "火星基地的具体坐标是多少？",
        [0.0, 0.0, 1.0],
    ),
]


def main():
    root = Path(__file__).resolve().parent

    documents = load_documents(
        root / "data" / "knowledge"
    )

    chunks = build_section_chunks(documents)

    vectors = [
        MOCK_VECTORS[chunk.heading]
        for chunk in chunks
    ]

    keyword_retriever = WeightedRetriever(chunks)

    vector_retriever = VectorRetriever(
        chunks,
        vectors,
    )

    hybrid_retriever = HybridRetriever(
        keyword_retriever,
        vector_retriever,
    )

    print("=== Day34 RRF混合检索 ===")
    print("文档数量：", len(documents))
    print("Chunk数量：", len(chunks))
    print("向量来源：人工模拟")
    print("Embedding API调用：无")

    for question, query_vector in QUESTIONS:
        print("\n" + "=" * 50)
        print("问题：", question)

        keyword_hits = keyword_retriever.search(
            question,
            top_k=6,
        )

        vector_hits = vector_retriever.search(
            query_vector,
            top_k=6,
        )

        hybrid_hits = hybrid_retriever.search(
            question,
            query_vector,
            candidate_k=6,
            top_k=3,
        )

        print("\n--- 关键词检索 ---")

        for index, hit in enumerate(
            keyword_hits,
            start=1,
        ):
            print(
                f"{index}. {hit.chunk.heading} "
                f"score={hit.score:.3f}"
            )

        if not keyword_hits:
            print("无结果")

        print("\n--- 模拟向量检索 ---")

        for index, hit in enumerate(
            vector_hits,
            start=1,
        ):
            print(
                f"{index}. {hit.chunk.heading} "
                f"cosine={hit.score:.3f}"
            )

        print("\n--- RRF混合排名 ---")

        for index, hit in enumerate(
            hybrid_hits,
            start=1,
        ):
            print(
                f"{index}. {hit.chunk.heading}"
                f" | RRF={hit.score:.6f}"
                f" | keyword_rank={hit.keyword_rank}"
                f" | vector_rank={hit.vector_rank}"
            )

        if not hybrid_hits:
            print("无结果")

    print("\n=== 注意 ===")

    print(
        "向量是人工设计的，只验证融合逻辑，"
        "不能用来证明真实语义检索效果。"
    )

    print(
        "RRF没有内置拒答机制，"
        "无关问题也可能返回候选资料。"
    )


if __name__ == "__main__":
    main()