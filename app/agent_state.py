from dataclasses import dataclass, field
from typing import Literal


AgentStatus = Literal[
    "running",
    "completed",
    "failed",
]


@dataclass(frozen=True)
class AgentEvent:
    """One safe, structured execution event."""

    step: int
    kind: str
    status: str
    tool_name: str | None = None
    error_code: str | None = None


@dataclass
class AgentState:
    """Internal, mutable state for one agent run."""

    status: AgentStatus = "running"

    messages: list[dict] = field(
        default_factory=list
    )

    events: list[AgentEvent] = field(
        default_factory=list
    )

    seen_calls: set[tuple[str, str]] = field(
        default_factory=set
    )

    tool_calls: int = 0
    answer: str | None = None
    error_code: str | None = None

    def add_event(
        self,
        kind: str,
        status: str,
        *,
        tool_name: str | None = None,
        error_code: str | None = None,
    ) -> None:
        self.events.append(
            AgentEvent(
                step=len(self.events) + 1,
                kind=kind,
                status=status,
                tool_name=tool_name,
                error_code=error_code,
            )
        )


@dataclass(frozen=True)
class AgentRunResult:
    """Public result of an agent run."""

    status: AgentStatus
    answer: str | None
    error_code: str | None
    tool_calls: int
    events: tuple[AgentEvent, ...]

    @property
    def succeeded(self) -> bool:
        return self.status == "completed"