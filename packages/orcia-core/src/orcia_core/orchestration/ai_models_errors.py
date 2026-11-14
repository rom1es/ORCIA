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
}

register_domain_error_catalog(AI_MODELS_ERROR_CATALOG)


class UnsafeLlmEndpointUrlError(OrciaDomainError):
    error_code = "ERR_UNSAFE_LLM_ENDPOINT_URL"
    http_status, type_slug = 422, "unsafe-llm-endpoint-url"


class LastTierModelInUseError(OrciaDomainError):
    error_code = "ERR_AI_MODEL_REQUIRED_BY_WORKFLOWS"
    http_status, type_slug = 409, "ai-model-required-by-workflows"


__all__ = [
    "AI_MODELS_ERROR_CATALOG",
    "LastTierModelInUseError",
    "UnsafeLlmEndpointUrlError",
]
