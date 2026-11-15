"""Pure agnostic URL normalization & protocol detection helpers for AI Models (`AD-24`, `AD-19`).

Free of web frameworks or third-party SDKs; shared between `orcia_core` and `apps/api`.
"""

from __future__ import annotations

from urllib.parse import urlparse


def is_anthropic_provider(
    endpoint_uri: str, provider: str | None = "", provider_slug: str | None = ""
) -> bool:
    """Return True if the endpoint targets Anthropic Messages API (`/v1/messages`)."""
    u = (endpoint_uri or "").strip().lower().rstrip("/")
    p = ((provider_slug or provider) or "").strip().lower()
    return (
        u.endswith("/messages")
        or "anthropic.com" in u
        or ("anthropic" in p and not u.endswith("/chat/completions"))
    )


def is_gemini_native_provider(
    endpoint_uri: str, provider: str | None = "", provider_slug: str | None = ""
) -> bool:
    """Return True when targeting Google Gemini Native API (`/v1beta`), False for OpenAI Mode A."""
    u = (endpoint_uri or "").strip().lower().rstrip("/")
    p = ((provider_slug or provider) or "").strip().lower()
    if "/openai" in u or u.endswith("/chat/completions"):
        return False
    if "googleapis.com" in u:
        return "/v1beta/openai" not in u
    return (
        "generativelanguage.googleapis.com" in u
        or ":generatecontent" in u
        or ":streamgeneratecontent" in u
        or ("gemini" in p and "native" in p)
        or ("google" in p and "gemini" in p)
    )


def build_gemini_native_chat_url(
    endpoint_uri: str,
    model_name: str,
    *,
    stream: bool = False,
) -> str:
    """Construct Google Gemini Native `:generateContent` or `:streamGenerateContent?alt=sse` URL."""
    base = endpoint_uri.strip().rstrip("/")
    cleaned_name = (model_name or "").strip()
    if not cleaned_name:
        raise ValueError("model_name is mandatory and cannot be empty")
    model_id = cleaned_name.removeprefix("models/").strip()
    if not model_id:
        raise ValueError("model_name is mandatory and cannot be empty")
    action = "streamGenerateContent?alt=sse" if stream else "generateContent"
    if ":generateContent" in base or ":streamGenerateContent" in base:
        prefix = base.split(":generateContent")[0].split(":streamGenerateContent")[0]
        return f"{prefix}:{action}"
    parsed = urlparse(base)
    if not parsed.path or parsed.path == "/":
        base = f"{base}/v1beta"
    if base.endswith(f"/models/{model_id}"):
        return f"{base}:{action}"
    return (
        f"{base}/{model_id}:{action}"
        if base.endswith("/models")
        else f"{base}/models/{model_id}:{action}"
    )


def normalize_chat_completions_url(
    endpoint_uri: str,
    provider: str = "",
    *,
    provider_slug: str = "",
    protocol_mode: str = "",
    model_name: str = "",
    stream: bool = False,
) -> str:
    """Normalize provider base URL to its canonical chat/messages/generateContent endpoint."""
    base = endpoint_uri.strip().rstrip("/")
    effective_prov = provider_slug or provider
    if protocol_mode == "anthropic_messages" or is_anthropic_provider(
        base, provider=effective_prov
    ):
        if base.endswith("/messages"):
            return base
        return f"{base}/messages" if base.endswith("/v1") else f"{base}/v1/messages"

    if (
        protocol_mode == "gemini_native" or is_gemini_native_provider(base, provider=effective_prov)
    ) and model_name:
        return build_gemini_native_chat_url(base, model_name, stream=stream)

    if base.endswith(("/chat/completions", "/api/chat", "/messages")):
        return base
    if base.endswith(("/v1beta/openai", "/openai", "/v1")):
        return f"{base}/chat/completions"
    if base.endswith("/api"):
        return f"{base[:-4].rstrip('/')}/v1/chat/completions"
    return f"{base}/v1/chat/completions"


def build_legacy_local_chat_url(endpoint_uri: str) -> str:
    """Build fallback `/api/chat` URL for legacy local servers returning 404 on `/v1/chat`."""
    clean = endpoint_uri.strip().rstrip("/")
    for suffix in ("/v1/chat/completions", "/chat/completions", "/v1", "/api/chat", "/api"):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)].rstrip("/")
            break
    return f"{clean}/api/chat"
