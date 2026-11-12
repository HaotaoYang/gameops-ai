from pathlib import Path

from app.rag.documents import (
    build_chunks,
    load_documents,
)
from app.rag.retriever import (
    format_context,
    search_chunks,
)


def main() -> None:
    # Resolve relative to this script, not shell's
    # current working directory.
    project_root = Path(__file__).resolve().parent

    knowledge_dir = (
        project_root / "data" / "knowledge"
    )

    print("=== Day29 本地知识库检索 ===")

    documents = load_documents(knowledge_dir)

    chunks = build_chunks(
        documents,
        chunk_size=180,
        overlap=40,
    )

    print(f"加载文档数量：{len(documents)}")
    print(f"生成Chunk数量：{len(chunks)}")

    questions = [
        "50级玩家可以参加什么活动？",
        "玩家忘记账号后应该怎么办？",
        "火星基地的具体坐标是多少？",
    ]

    for question in questions:
        print("\n" + "=" * 40)
        print("用户问题：", question)

        hits = search_chunks(
            question,
            chunks,
            top_k=2,
        )

        print("\n检索结果数量：", len(hits))

        for index, hit in enumerate(hits, start=1):
            print(f"\n结果{index}：")
            print("来源：", hit.chunk.source)
            print("匹配分数：", hit.score)
            print("匹配词：", hit.matched_terms)

        print("\n=== 可供后续模型使用的资料 ===")
        print(format_context(hits))


if __name__ == "__main__":
    main()