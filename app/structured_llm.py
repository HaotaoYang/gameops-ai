import os

from openai import OpenAI

from app.llm import DEFAULT_MODEL
from app.prompts import GAMEOPS_ANALYSIS_INSTRUCTIONS
from app.report_schemas import GameOpsReport


STRUCTURED_REPORT_INSTRUCTIONS = (
    GAMEOPS_ANALYSIS_INSTRUCTIONS
    + "\n请将分析结果填入指定的结构化报告字段。"
    + "\nsummary：简短概括。"
    + "\nobservations：仅列出有数据支持的观察。"
    + "\nlimitations：列出缺少的数据及分析限制。"
    + "\nneeds_more_data：若需要更多数据才能完成分析，设为true。"
)


def generate_structured_report(
    question: str,
    client: OpenAI | None = None,
) -> GameOpsReport:
    """Generate and parse a structured game operations report."""

    if not question.strip():
        raise ValueError("问题不能为空")

    if client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "缺少 OPENAI_API_KEY 环境变量"
            )

        client = OpenAI()

    model = os.getenv(
        "OPENAI_MODEL",
        DEFAULT_MODEL,
    )

    response = client.responses.parse(
        model=model,
        instructions=STRUCTURED_REPORT_INSTRUCTIONS,
        input=question,
        text_format=GameOpsReport,
        max_output_tokens=600,
        store=False,
    )

    report = response.output_parsed

    if report is None:
        raise ValueError(
            "模型没有返回可用的结构化报告"
        )

    if not isinstance(report, GameOpsReport):
        raise TypeError(
            "模型返回的对象不是GameOpsReport"
        )

    return report