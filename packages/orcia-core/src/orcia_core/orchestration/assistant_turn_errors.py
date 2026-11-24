"""Assistant Turn Reliability, Liveness & Rate-Limit Domain Errors (`AD-19`, `AD-25`)."""

from __future__ import annotations

from orcia_core.kernel.errors import OrciaDomainError, register_domain_error_catalog
from orcia_core.orchestration._assistant_turn_error_catalog import ASSISTANT_TURN_ERROR_CATALOG

register_domain_error_catalog(ASSISTANT_TURN_ERROR_CATALOG)


class AssistantTurnInterruptedError(OrciaDomainError):
    """Raised/emitted when an active turn's worker liveness expires mid-stream (`R1`)."""

    error_code = "ERR_ASSISTANT_TURN_INTERRUPTED"
    http_status = 503
    type_slug = "assistant-turn-interrupted"


class AssistantRateLimitExceededError(OrciaDomainError):
    """Raised when sliding-window rate limit for assistant turns is exceeded (`HTTP 429`)."""

    error_code = "ERR_ASSISTANT_RATE_LIMITED"
    http_status = 429
    type_slug = "assistant-rate-limited"

    def __init__(
        self,
        *,
        retry_after_s: int = 1,
        detail_override: str | None = None,
        instance: str | None = None,
    ) -> None:
        self.retry_after_s = max(1, retry_after_s)
        super().__init__(detail_override=detail_override, instance=instance)


class AssistantConcurrencyLimitError(OrciaDomainError):
    """Raised when per-user concurrent active assistant turn semaphore is exhausted (`429`)."""

    error_code = "ERR_ASSISTANT_CONCURRENCY_LIMIT"
    http_status = 429
    type_slug = "assistant-concurrency-limit"


class TurnBudgetExceededError(OrciaDomainError):
    """Raised when assistant multi-step tool loop exceeds iteration, token, or wall-clock limit."""

    error_code = "ERR_ASSISTANT_TURN_BUDGET_EXCEEDED"
    http_status = 422
    type_slug = "assistant-turn-budget-exceeded"

    def __init__(
        self,
        *,
        limit_kind: str = "iterations",
        detail_override: str | None = None,
        instance: str | None = None,
    ) -> None:
        self.limit_kind = limit_kind
        super().__init__(detail_override=detail_override, instance=instance)


__all__ = [
    "ASSISTANT_TURN_ERROR_CATALOG",
    "AssistantConcurrencyLimitError",
    "AssistantRateLimitExceededError",
    "AssistantTurnInterruptedError",
    "TurnBudgetExceededError",
]
