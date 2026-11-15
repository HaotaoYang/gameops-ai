from pathlib import Path

from app.rag.documents import (
    build_chunks,
    load_documents,
)
from app.rag.retriever import search_chunks
from app.rag.section_chunker import (
    build_section_chunks,
)
from app.rag.weighted_retriever import (
    WeightedRetriever,
)


def main() -> None:
    project_root = Path(__file__).resolve().parent

    knowledge_dir = (
        project_root / "data" / "knowledge"
    )

    documents = load_documents(knowledge_dir)

    old_chunks = build_chunks(documents)

    new_chunks = build_section_chunks(documents)

    retriever = WeightedRetriever(new_chunks)

    print("=== Day30 RAG检索优化 ===")

    print(f"文档数量：{len(documents)}")
    print(f"Day29 Chunk数量：{len(old_chunks)}")
    print(f"Day30 Chunk数量：{len(new_chunks)}")

    print("\n=== Day30章节索引 ===")

    for chunk in new_chunks:
        print(
            f"{chunk.source} | "
            f"{chunk.heading} | "
            f"{len(chunk.content)}字符"
        )

    questions = [
        "50级玩家可以参加什么活动？",
        "玩家忘记账号后应该怎么办？",
        "火星基地的具体坐标是多少？",
    ]

    for question in questions:
        print("\n" + "=" * 50)
        print("用户问题：", question)

        old_hits = search_chunks(
            question,
            old_chunks,
            top_k=3,
        )

        section_hits = search_chunks(
            question,
            new_chunks,
            top_k=3,
        )

        new_hits = retriever.search(
            question,
            top_k=3,
        )

        print("\n--- Day29原始检索 ---")

        print("结果数量：", len(old_hits))

        for hit in old_hits:
            print(
                f"{hit.chunk.source} | "
                f"score={hit.score} | "
                f"匹配词={hit.matched_terms}"
            )

        print("\n--- 仅优化文本切分 ---")

        print("结果数量：", len(section_hits))

        for hit in section_hits:
            print(
                f"{hit.chunk.source} | "
                f"{hit.chunk.heading} | "
                f"score={hit.score}"
            )

        print("\n--- Day30切分+加权检索 ---")

        print("结果数量：", len(new_hits))

        for hit in new_hits:
            print(
                f"{hit.chunk.source} | "
                f"{hit.chunk.heading} | "
                f"score={hit.score:.3f}"
            )

            print(
                "匹配词：",
                hit.matched_terms,
            )

            print("片段ID：", hit.chunk.id)
            print("内容：", hit.chunk.content)

        if not new_hits:
            print("没有检索到相关知识库内容")


if __name__ == "__main__":
    main()