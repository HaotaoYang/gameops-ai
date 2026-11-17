import argparse

from pathlib import Path

from dotenv import load_dotenv

from app.rag.documents import (
    load_documents,
    build_chunks,
)

from app.rag.retriever import search_chunks

from app.rag.section_chunker import (
    build_section_chunks,
)

from app.rag.weighted_retriever import (
    WeightedRetriever,
)

from app.rag.rag_agent import run_rag

from app.rag.rag_prompt import (
    INSUFFICIENT_ANSWER,
)

from app.rag.evaluation import (
    load_eval_cases,
    evaluate_retrieval,
    summarize_retrieval,
    evaluate_answer,
)


def format_rate(value):
    if value is None:
        return "N/A"

    return f"{value:.1%}"


def print_metrics(title, results):
    summary = summarize_retrieval(results)

    print(f"\n=== {title} ===")

    print("评测问题数：", summary["case_count"])

    print(
        "有相关资料的问题数：",
        summary["positive_count"],
    )

    print(
        "无相关资料的问题数：",
        summary["negative_count"],
    )

    print(
        "命中率：",
        format_rate(summary["hit_rate"]),
    )

    print(
        "宏平均Precision：",
        format_rate(summary["macro_precision"]),
    )

    print(
        "宏平均Recall：",
        format_rate(summary["macro_recall"]),
    )

    print(
        "无资料过滤准确率：",
        format_rate(summary["empty_accuracy"]),
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the real LLM for answer evaluation",
    )

    args = parser.parse_args()

    if args.live:
        load_dotenv()

    root = Path(__file__).resolve().parent

    documents = load_documents(
        root / "data" / "knowledge"
    )

    cases = load_eval_cases(
        root / "data" / "evaluation"
        / "rag_cases.json"
    )

    old_chunks = build_chunks(documents)

    new_chunks = build_section_chunks(
        documents
    )

    retriever = WeightedRetriever(new_chunks)

    old_results = []
    new_results = []
    section_results = []

    answer_results = []

    print("=== Day32 RAG质量评测 ===")

    print(
        "评测模式：",
        "真实模型" if args.live else "离线样例",
    )

    print("评测案例数量：", len(cases))

    for case in cases:
        print("\n" + "=" * 50)

        print(case.id, case.question)

        old_hits = search_chunks(
            case.question,
            old_chunks,
            top_k=3,
        )

        new_hits = retriever.search(
            case.question,
            top_k=3,
        )

        old_sources = [
            hit.chunk.source
            for hit in old_hits
        ]

        new_sources = [
            hit.chunk.source
            for hit in new_hits
        ]

        new_headings = [
            hit.chunk.heading
            for hit in new_hits
        ]

        old_eval = evaluate_retrieval(
            old_sources,
            case.expected_sources,
        )

        new_eval = evaluate_retrieval(
            new_sources,
            case.expected_sources,
        )

        section_eval = evaluate_retrieval(
            new_headings,
            case.expected_headings,
        )

        old_results.append(old_eval)
        new_results.append(new_eval)

        section_results.append(section_eval)

        print("预期文档：", case.expected_sources)
        print("Day29检索：", old_sources)
        print("Day30检索：", new_sources)
        print("Day30章节：", new_headings)

        print(
            "Day29 Precision：",
            format_rate(old_eval.precision),
        )

        print(
            "Day30 Precision：",
            format_rate(new_eval.precision),
        )

        # Evaluate a live answer or an offline fixture.
        if args.live:
            result = run_rag(
                case.question,
                retriever,
                top_k=3,
            )

            answer = result.answer
            status = result.status
            origin = "live"

            print(
                "是否调用模型：",
                result.model_called,
            )

        else:
            answer = case.sample_answer

            status = (
                "insufficient_evidence"
                if answer == INSUFFICIENT_ANSWER
                else "answered"
            )

            origin = case.sample_origin

        answer_eval = evaluate_answer(
            case,
            answer=answer,
            status=status,
            hits=new_hits,
        )

        answer_results.append(
            (case, origin, answer_eval)
        )

        print("\n回答来源：", origin)
        print("回答：", answer)

        print(
            "回答规则评测：",
            "PASS" if answer_eval.passed else "FAIL",
        )

        for issue in answer_eval.issues:
            print("-", issue)

    print_metrics(
        "Day29 文档级检索汇总",
        old_results,
    )

    print_metrics(
        "Day30 文档级检索汇总",
        new_results,
    )

    print_metrics(
        "Day30 章节级检索汇总",
        section_results,
    )

    print("\n=== 回答规则评测汇总 ===")

    groups = sorted({
        origin
        for _, origin, _ in answer_results
    })

    for group in groups:
        group_results = [
            result
            for _, origin, result in answer_results
            if origin == group
        ]

        passed = sum(
            result.passed
            for result in group_results
        )

        print(
            f"{group}："
            f"{passed}/{len(group_results)}"
        )

    refusal_results = [
        (case, result)
        for case, _, result in answer_results
        if case.expected_status
        == "insufficient_evidence"
    ]

    refusal_passed = sum(
        result.passed
        for _, result in refusal_results
    )

    print(
        "应拒答案例规则通过率：",
        format_rate(
            refusal_passed / len(refusal_results)
            if refusal_results
            else None
        ),
    )

    # Use a deliberately incorrect numeric claim.
    print("\n=== 已知错误回答检测 ===")

    activity_case = next(
        case
        for case in cases
        if case.id == "Q01"
    )

    activity_hits = retriever.search(
        activity_case.question
    )

    bad_answer = (
        "50级玩家可以参加周末挑战活动，"
        "并获得10000金币奖励。[资料1]"
    )

    bad_result = evaluate_answer(
        activity_case,
        answer=bad_answer,
        status="answered",
        hits=activity_hits,
    )

    print("错误样例：", bad_answer)

    print(
        "评测结果：",
        "PASS" if bad_result.passed else "FAIL",
    )

    for issue in bad_result.issues:
        print("-", issue)

    if bad_result.passed:
        raise RuntimeError(
            "评测器未识别已知错误样例"
        )


if __name__ == "__main__":
    main()