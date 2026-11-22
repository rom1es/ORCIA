"""Domain errors for AI Models Hub and LLM endpoint governance (`Story 17.5`)."""

from __future__ import annotations

from orcia_core.permissions.ssrf_policy import (
    UnsafeLlmEndpointUrlError as UnsafeLlmEndpointUrlError,
)
from orcia_kernel.enums import SupportedLocale
from orcia_kernel.errors import LocalizedErrorCopy, OrciaDomainError, register_domain_error_catalog

AI_MODELS_ERROR_CATALOG: dict[str, dict[SupportedLocale, LocalizedErrorCopy]] = {
    "ERR_UNSAFE_LLM_ENDPOINT_URL": {
        "fr": LocalizedErrorCopy(
            "URL de fournisseur LLM non sécurisée (protection anti-SSRF)",
            "L'URL de l'endpoint LLM doit utiliser HTTP/HTTPS et ne peut pas cibler une adresse "
            "de métadonnées Cloud ou link-local (169.254.0.0/16, fe80::/10, "
            "metadata.google.internal, 100.100.100.200).",
        ),
        "en": LocalizedErrorCopy(
            "Unsafe LLM endpoint URL (SSRF protection)",
            "The LLM endpoint URL must use HTTP/HTTPS and must not target cloud metadata or "
            "link-local addresses (169.254.0.0/16, fe80::/10, metadata.google.internal, "
            "100.100.100.200).",
        ),
    },
    "ERR_AI_MODEL_REQUIRED_BY_WORKFLOWS": {
        "fr": LocalizedErrorCopy(
            "Modèle IA requis par des workflows actifs",
            "Impossible de supprimer ce modèle car il s'agit de l'unique fournisseur actif pour "
            "ce tier cognitif et des workflows publiés en dépendent. Configurez d'abord un modèle "
            "de substitution ou forcez la suppression.",
        ),
        "en": LocalizedErrorCopy(
            "AI model required by active workflows",
            "Cannot delete this model because it is the sole active provider for this "
            "cognitive tier and published workflows depend on it. Configure a fallback "
            "model first or force deletion.",
        ),
    },
    "ERR_MODEL_DISCOVERY_AUTH_FAILED": {
        "fr": LocalizedErrorCopy(
            "Authentification échouée auprès du fournisseur IA",
            "La clé d'API fournie est invalide, expirée ou ne dispose pas des privilèges "
            "nécessaires pour lister les modèles disponibles.",
        ),
        "en": LocalizedErrorCopy(
            "AI model provider authentication failed",
            "The provided API key is invalid, expired, or lacks permissions to list "
            "available models.",
        ),
    },
    "ERR_MODEL_DISCOVERY_NOT_SUPPORTED": {
        "fr": LocalizedErrorCopy(
            "Point de terminaison de découverte introuvable",
            "Le point de terminaison ne supporte pas l'API standard de découverte des modèles "
            "ou a renvoyé une erreur 404.",
        ),
        "en": LocalizedErrorCopy(
            "Model discovery endpoint not found",
            "The endpoint does not support standard model discovery API or returned 404.",
        ),
    },
    "ERR_MODEL_DISCOVERY_NETWORK_ERROR": {
        "fr": LocalizedErrorCopy(
            "Erreur réseau lors de la découverte des modèles",
            "Impossible de contacter le fournisseur LLM : délai d'attente dépassé ou erreur "
            "de connexion réseau.",
        ),
        "en": LocalizedErrorCopy(
            "Network error during model discovery",
            "Failed to reach the LLM provider endpoint: connection timed out or network error.",
        ),
    },
    "ERR_MODEL_CONNECTION_AUTH_FAILED": {
        "fr": LocalizedErrorCopy(
            "Authentification échouée auprès du fournisseur IA",
            "La clé d'API ou les identifiants fournis ont été refusés "
            "par le fournisseur (HTTP 401/403).",
        ),
        "en": LocalizedErrorCopy(
            "AI model provider authentication failed",
            "The provided API key or credentials were rejected by the provider (HTTP 401/403).",
        ),
    },
    "ERR_MODEL_CONNECTION_NOT_FOUND": {
        "fr": LocalizedErrorCopy(
            "Modèle ou point de terminaison introuvable",
            "Le modèle spécifié n'existe pas chez le fournisseur "
            "ou l'URL d'API est incorrecte (HTTP 404).",
        ),
        "en": LocalizedErrorCopy(
            "Model or endpoint not found",
            "The specified model does not exist on the provider "
            "or the API URL is incorrect (HTTP 404).",
        ),
    },
    "ERR_MODEL_CONNECTION_RATE_LIMITED": {
        "fr": LocalizedErrorCopy(
            "Limite de requêtes atteinte auprès du fournisseur IA",
            "Le quota ou la limite de requêtes (rate limit) "
            "du fournisseur a été dépassé (HTTP 429).",
        ),
        "en": LocalizedErrorCopy(
            "AI provider rate limit exceeded",
            "The provider quota or rate limit has been exceeded (HTTP 429).",
        ),
    },
    "ERR_MODEL_CONNECTION_TIMEOUT": {
        "fr": LocalizedErrorCopy(
            "Délai d'attente dépassé lors du test de connexion",
            "Le fournisseur IA n'a pas répondu dans le délai imparti (timeout).",
        ),
        "en": LocalizedErrorCopy(
            "Connection test timed out",
            "The AI provider did not respond within the allocated timeout.",
        ),
    },
    "ERR_MODEL_CONNECTION_NETWORK_ERROR": {
        "fr": LocalizedErrorCopy(
            "Erreur réseau lors du test de connexion",
            "Impossible de joindre l'adresse du fournisseur IA "
            "(hôte injoignable ou connexion refusée).",
        ),
        "en": LocalizedErrorCopy(
            "Network error during connection test",
            "Failed to reach the AI provider endpoint (unreachable host or connection refused).",
        ),
    },
    "ERR_MODEL_CONNECTION_UPSTREAM_ERROR": {
        "fr": LocalizedErrorCopy(
            "Erreur renvoyée par le fournisseur IA",
            "Le fournisseur IA a retourné une erreur interne ou une réponse invalide (HTTP 5xx).",
        ),
        "en": LocalizedErrorCopy(
            "Upstream error from AI provider",
            "The AI provider returned an internal error or invalid response (HTTP 5xx).",
        ),
    },
    "ERR_MODEL_TOOLS_UNSUPPORTED": {
        "fr": LocalizedErrorCopy(
            "Appels d'outils natifs non pris en charge par ce modèle IA",
            "Le modèle configuré pour ce palier ne supporte pas les appels d'outils natifs "
            "(supports_tools=false). Utilisez le mode rapide (Vitesse 1) ou activez un modèle "
            "compatible OpenAI/Anthropic.",
        ),
        "en": LocalizedErrorCopy(
            "Native tool calling is not supported by this AI model",
            "The configured AI model for this tier does not support native tool calling "
            "(supports_tools=false). Use fast mode (Speed 1) or select an OpenAI/Anthropic "
            "tool-capable model.",
        ),
    },
}

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
