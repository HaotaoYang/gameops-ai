from pydantic import BaseModel, ConfigDict


class GameOpsReport(BaseModel):
    """Structured game operations analysis."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    observations: list[str]
    limitations: list[str]
    needs_more_data: bool