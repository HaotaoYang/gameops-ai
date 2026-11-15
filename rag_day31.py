from pathlib import Path

from dotenv import load_dotenv

from app.rag.documents import load_documents

from app.rag.section_chunker import (
    build_section_chunks,
)

from app.rag.weighted_retriever import (
    WeightedRetriever,
)

from app.rag.rag_agent import run_rag


def main() -> None:
    load_dotenv()

    project_root = Path(__file__).resolve().parent

    knowledge_dir = (
        project_root / "data" / "knowledge"
    )

    documents = load_documents(knowledge_dir)

    chunks = build_section_chunks(documents)

    retriever = WeightedRetriever(chunks)

    print("=== Day31 完整RAG问答 ===")

    print("文档数量：", len(documents))
    print("Chunk数量：", len(chunks))

    questions = [
        "50级玩家可以参加什么活动？",
        "玩家忘记账号后应该怎么办？",
        "火星基地的具体坐标是多少？",
        "周末挑战活动是哪一年首次上线的？",
    ]

    for question in questions:
        print("\n" + "=" * 50)

        print("用户问题：", question)

        result = run_rag(
            question,
            retriever,
        )

        print("\n=== 执行状态 ===")

        print("状态：", result.status)

        print(
            "检索片段数：",
            result.retrieved_count,
        )

        print(
            "是否调用模型：",
            result.model_called,
        )

        print("\n=== 最终回答 ===")
        print(result.answer)

        if result.sources:
            print("\n=== 真实知识来源 ===")

            for source in result.sources:
                print(
                    f"[{source.reference}] "
                    f"{source.source}"
                )

                print("章节：", source.heading)
                print("片段ID：", source.chunk_id)

                print(
                    "检索分数：",
                    f"{source.score:.3f}",
                )

        if result.issues:
            print("\n=== 问题记录 ===")

            for issue in result.issues:
                print("-", issue)


if __name__ == "__main__":
    main()