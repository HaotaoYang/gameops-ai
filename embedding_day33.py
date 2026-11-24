import argparse

from pathlib import Path

from dotenv import load_dotenv

from app.rag.documents import load_documents
from app.rag.section_chunker import build_section_chunks
from app.rag.weighted_retriever import WeightedRetriever

from app.rag.embeddings import embed_texts

from app.rag.vector_retriever import (
    VectorRetriever,
    cosine_similarity,
)

from app.rag.evaluation import (
    evaluate_retrieval,
    load_eval_cases,
    summarize_retrieval,
)


def format_rate(value):
    if value is None:
        return "N/A"

    return f"{value:.1%}"


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--live",
        action="store_true",
        help="Use the real Embedding API",
    )

    args = parser.parse_args()

    print("=== Day33 Embedding与向量检索 ===")

    print("\n=== 余弦相似度数学练习 ===")

    examples = [
        ([1, 0], [1, 0]),
        ([1, 0], [0.8, 0.6]),
        ([1, 0], [0, 1]),
        ([1, 0], [-1, 0]),
    ]

    for a, b in examples:
        score = cosine_similarity(a, b)

        print(
            f"{a} 与 {b}："
            f"{score:.3f}"
        )

    if not args.live:
        print(
            "\n未启用--live，"
            "本次只运行离线数学演示。"
        )
        return

    load_dotenv()

    root = Path(__file__).resolve().parent

    documents = load_documents(
        root / "data" / "knowledge"
    )

    chunks = build_section_chunks(documents)

    cases = load_eval_cases(
        root / "data" / "evaluation" / "rag_cases.json"
    )

    print("\n=== 知识库 ===")

    print("文档数量：", len(documents))
    print("Chunk数量：", len(chunks))
    print("评测问题数量：", len(cases))

    # The heading is included in each existing Chunk,
    # so the original content can be embedded directly.
    chunk_texts = [
        chunk.content
        for chunk in chunks
    ]

    question_texts = [
        case.question
        for case in cases
    ]

    # Batch request: embed the six knowledge chunks.
    chunk_vectors = embed_texts(chunk_texts)

    # Batch request: embed the six evaluation questions.
    question_vectors = embed_texts(question_texts)

    index = VectorRetriever(
        chunks,
        chunk_vectors,
    )

    keyword_retriever = WeightedRetriever(chunks)

    print("\n=== Embedding索引 ===")
    print("向量数量：", len(chunk_vectors))
    print("向量维度：", index.dimensions)

    keyword_results = []
    vector_results = []

    for case, question_vector in zip(
        cases,
        question_vectors,
    ):
        keyword_hits = keyword_retriever.search(
            case.question,
            top_k=3,
        )

        vector_hits = index.search(
            question_vector,
            top_k=3,
        )

        keyword_sources = [
            hit.chunk.source
            for hit in keyword_hits
        ]

        vector_sources = [
            hit.chunk.source
            for hit in vector_hits
        ]

        keyword_eval = evaluate_retrieval(
            keyword_sources,
            case.expected_sources,
        )

        vector_eval = evaluate_retrieval(
            vector_sources,
            case.expected_sources,
        )

        keyword_results.append(keyword_eval)
        vector_results.append(vector_eval)

        print("\n" + "=" * 50)

        print(case.id, case.question)
        print("预期文档：", case.expected_sources)

        print(
            "\n关键词检索来源：",
            keyword_sources,
        )

        print(
            "关键词Precision：",
            format_rate(keyword_eval.precision),
        )

        print("\n向量检索Top-3：")

        for hit in vector_hits:
            print(
                f"- {hit.chunk.source} / "
                f"{hit.chunk.heading} / "
                f"cosine={hit.score:.4f}"
            )

        print(
            "向量Precision：",
            format_rate(vector_eval.precision),
        )

        print(
            "向量Recall：",
            format_rate(vector_eval.recall),
        )

    print("\n=== Day32评测集汇总对比 ===")

    for name, results in [
        ("Day30关键词检索", keyword_results),
        ("Day33向量检索Top-3", vector_results),
    ]:
        metrics = summarize_retrieval(results)

        print(f"\n{name}")
        print(
            "Hit Rate：",
            format_rate(metrics["hit_rate"]),
        )
        print(
            "Macro Precision：",
            format_rate(metrics["macro_precision"]),
        )
        print(
            "Macro Recall：",
            format_rate(metrics["macro_recall"]),
        )
        print(
            "无资料过滤准确率：",
            format_rate(metrics["empty_accuracy"]),
        )

    print(
        "\n注意：向量检索当前没有设置"
        "无关问题过滤阈值。"
    )

    print(
        "因此即使是无关问题，"
        "Top-3也可能返回候选文档。"
    )


if __name__ == "__main__":
    main()