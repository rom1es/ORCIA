"""Domain errors for AI Models Hub and LLM endpoint governance (`Story 17.5`)."""

from __future__ import annotations

from orcia_core.orchestration._ai_models_error_catalog import AI_MODELS_ERROR_CATALOG
from orcia_core.permissions.ssrf_policy import (
    UnsafeLlmEndpointUrlError as UnsafeLlmEndpointUrlError,
)
from orcia_kernel.errors import OrciaDomainError, register_domain_error_catalog

register_domain_error_catalog(AI_MODELS_ERROR_CATALOG)


class LastTierModelInUseError(OrciaDomainError):
    error_code = "ERR_AI_MODEL_REQUIRED_BY_WORKFLOWS"
    http_status, type_slug = 409, "ai-model-required-by-workflows"


class ModelDiscoveryAuthFailedError(OrciaDomainError):
    error_code = "ERR_MODEL_DISCOVERY_AUTH_FAILED"
    http_status, type_slug = 401, "model-discovery-auth-failed"


class ModelDiscoveryEndpointNotFoundError(OrciaDomainError):
    error_code = "ERR_MODEL_DISCOVERY_NOT_SUPPORTED"
    http_status, type_slug = 404, "model-discovery-not-supported"


class ModelDiscoveryNetworkError(OrciaDomainError):
    error_code = "ERR_MODEL_DISCOVERY_NETWORK_ERROR"
    http_status, type_slug = 502, "model-discovery-network-error"


class ModelConnectionAuthFailedError(OrciaDomainError):
    error_code = "ERR_MODEL_CONNECTION_AUTH_FAILED"
    http_status, type_slug = 401, "model-connection-auth-failed"

    def __init__(
        self,
        detail_override: str | None = None,
        *,
        instance: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        super().__init__(detail_override=detail_override, instance=instance)
        self.latency_ms = latency_ms


class ModelConnectionNotFoundError(OrciaDomainError):
    error_code = "ERR_MODEL_CONNECTION_NOT_FOUND"
    http_status, type_slug = 404, "model-connection-not-found"

    def __init__(
        self,
        detail_override: str | None = None,
        *,
        instance: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        super().__init__(detail_override=detail_override, instance=instance)
        self.latency_ms = latency_ms


class ModelConnectionRateLimitedError(OrciaDomainError):
    error_code = "ERR_MODEL_CONNECTION_RATE_LIMITED"
    http_status, type_slug = 429, "model-connection-rate-limited"

    def __init__(
        self,
        detail_override: str | None = None,
        *,
        instance: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        super().__init__(detail_override=detail_override, instance=instance)
        self.latency_ms = latency_ms


class ModelConnectionTimeoutError(OrciaDomainError):
    error_code = "ERR_MODEL_CONNECTION_TIMEOUT"
    http_status, type_slug = 504, "model-connection-timeout"

    def __init__(
        self,
        detail_override: str | None = None,
        *,
        instance: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        super().__init__(detail_override=detail_override, instance=instance)
        self.latency_ms = latency_ms


class ModelConnectionNetworkError(OrciaDomainError):
    error_code = "ERR_MODEL_CONNECTION_NETWORK_ERROR"
    http_status, type_slug = 502, "model-connection-network-error"

    def __init__(
        self,
        detail_override: str | None = None,
        *,
        instance: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        super().__init__(detail_override=detail_override, instance=instance)
        self.latency_ms = latency_ms


class ModelConnectionUpstreamError(OrciaDomainError):
    error_code = "ERR_MODEL_CONNECTION_UPSTREAM_ERROR"
    http_status, type_slug = 502, "model-connection-upstream-error"

    def __init__(
        self,
        detail_override: str | None = None,
        *,
        instance: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        super().__init__(detail_override=detail_override, instance=instance)
        self.latency_ms = latency_ms


class ModelToolsUnsupportedError(OrciaDomainError):
    """Raised pre-stream (`HTTP 422`) when Speed 2/3 is requested on `supports_tools=false`."""

    error_code = "ERR_MODEL_TOOLS_UNSUPPORTED"
    http_status, type_slug = 422, "model-tools-unsupported"

    def __init__(
        self,
        model_name: str = "",
        *,
        detail_override: str | None = None,
        instance: str | None = None,
    ) -> None:
        self.model_name = model_name
        super().__init__(detail_override=detail_override, instance=instance)


__all__ = [
    "AI_MODELS_ERROR_CATALOG",
    "LastTierModelInUseError",
    "ModelConnectionAuthFailedError",
    "ModelConnectionNetworkError",
    "ModelConnectionNotFoundError",
    "ModelConnectionRateLimitedError",
    "ModelConnectionTimeoutError",
    "ModelConnectionUpstreamError",
    "ModelDiscoveryAuthFailedError",
    "ModelDiscoveryEndpointNotFoundError",
    "ModelDiscoveryNetworkError",
    "ModelToolsUnsupportedError",
    "UnsafeLlmEndpointUrlError",
]
