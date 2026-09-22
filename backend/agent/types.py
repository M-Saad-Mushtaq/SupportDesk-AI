from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    id: str
    name: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ModelResult:
    text: str = ""
    calls: tuple[ToolCall, ...] = ()
    finish_reason: str = "stop"
    usage: dict[str, int | None] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelRequest:
    system: str
    history: list[dict[str, str]]
    tools: list[dict]
    max_output_tokens: int


class ProviderError(Exception):
    """Only application-owned safe messages cross the adapter boundary."""
    def __init__(self, code: str, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class ModelSession(Protocol):
    async def complete(self, results: list[ToolResult], timeout: float) -> ModelResult: ...
    async def close(self) -> None: ...


class Provider(Protocol):
    supports_tools: bool
    def start(self, request: ModelRequest) -> ModelSession: ...
