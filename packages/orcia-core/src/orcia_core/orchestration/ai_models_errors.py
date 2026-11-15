"""Domain errors for AI Models Hub and LLM endpoint governance (`Story 17.5`)."""

from __future__ import annotations

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
}

register_domain_error_catalog(AI_MODELS_ERROR_CATALOG)


class UnsafeLlmEndpointUrlError(OrciaDomainError):
    error_code = "ERR_UNSAFE_LLM_ENDPOINT_URL"
    http_status, type_slug = 422, "unsafe-llm-endpoint-url"


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


__all__ = [
    "AI_MODELS_ERROR_CATALOG",
    "LastTierModelInUseError",
    "ModelDiscoveryAuthFailedError",
    "ModelDiscoveryEndpointNotFoundError",
    "ModelDiscoveryNetworkError",
    "UnsafeLlmEndpointUrlError",
]
