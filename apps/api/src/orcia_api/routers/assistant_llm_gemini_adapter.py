"""Google Gemini Native (Mode B `:generateContent` / `:streamGenerateContent`) & OpenAI Bridge."""

from __future__ import annotations

import re
from typing import Any, Literal
from urllib.parse import urlparse

from orcia_api.schemas import bootstrap as bs

_THINK_TAG_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK_RE = re.compile(r"<think>(.*)$", re.DOTALL | re.IGNORECASE)
_OFFLINE_TEST_HOSTS: frozenset[str] = frozenset({"api.openai.local", "api.anthropic.local", "api.google.local", "api.mistral.local", "mock-llm", "example.com", "api.example.com"})  # fmt: skip  # noqa: E501


def _separate_think_tags(raw_content: str, explicit_reasoning: str = "") -> tuple[str, str]:
    thinking_parts = [explicit_reasoning.strip()] if explicit_reasoning.strip() else []
    text = raw_content or ""
    for match in _THINK_TAG_RE.finditer(text):
        if extracted := match.group(1).strip():
            thinking_parts.append(extracted)
    cleaned = _THINK_TAG_RE.sub("", text)
    if (unclosed := _UNCLOSED_THINK_RE.search(cleaned)) is not None:
        if partial := unclosed.group(1).strip():
            thinking_parts.append(partial)
        cleaned = cleaned[: unclosed.start()]
    return cleaned.strip(), "\n\n".join(thinking_parts).strip()


def is_google_gemini_native_provider(endpoint_uri: str, provider: str = "") -> bool:
    """Return True when targeting Google Gemini Native API (`/v1beta`), False for Mode A."""
    u, p = endpoint_uri.strip().lower().rstrip("/"), provider.strip().lower()
    if "/openai" in u or u.endswith("/chat/completions"):
        return False
    return (
        "generativelanguage.googleapis.com" in u
        or ":generatecontent" in u
        or ":streamgeneratecontent" in u
        or "google" in p
        or "gemini" in p
    )


def build_gemini_native_url(
    endpoint_uri: str, model_name: str = "gemini-argon", *, stream: bool = False
) -> str:
    """Construct Google Gemini Native `:generateContent` or `:streamGenerateContent?alt=sse` URL."""
    base = endpoint_uri.strip().rstrip("/")
    model_id = (model_name or "gemini-argon").strip().removeprefix("models/") or "gemini-argon"
    action = "streamGenerateContent?alt=sse" if stream else "generateContent"
    if ":generateContent" in base or ":streamGenerateContent" in base:
        prefix = base.split(":generateContent")[0].split(":streamGenerateContent")[0]
        return f"{prefix}:{action}"
    parsed = urlparse(base)
    if not parsed.path or parsed.path == "/":
        base = f"{base}/v1beta"
    if base.endswith(f"/models/{model_id}"):
        return f"{base}:{action}"
    return f"{base}/{model_id}:{action}" if base.endswith("/models") else f"{base}/models/{model_id}:{action}"  # fmt: skip  # noqa: E501


def build_gemini_native_headers(api_key: str | None) -> dict[str, str]:
    """Build headers for Google Gemini Native API (`x-goog-api-key`)."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key and api_key.strip():
        headers["x-goog-api-key"] = api_key.strip()
    return headers


def build_gemini_native_request_body(
    messages: list[dict[str, Any]],
    *,
    include_thoughts: bool = True,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build Google Gemini Native `:generateContent` JSON body with `thinkingConfig`."""
    sys_blocks = [
        str(m.get("content") or "").strip()
        for m in messages
        if m.get("role") == "system" and str(m.get("content") or "").strip()
    ]
    contents = [
        {
            "role": "model" if m.get("role") == "assistant" else "user",
            "parts": [{"text": str(m.get("content") or "")}],
        }
        for m in messages
        if m.get("role") != "system"
    ]
    body: dict[str, Any] = {"contents": contents or [{"role": "user", "parts": [{"text": "Hello"}]}]}  # fmt: skip  # noqa: E501
    if sys_blocks:
        body["systemInstruction"] = {"parts": [{"text": "\n\n".join(sys_blocks)}]}
    if include_thoughts:
        body["generationConfig"] = {"thinkingConfig": {"includeThoughts": True}}
    if tools:
        decls = [
            {
                "name": str(t.get("function", {}).get("name") or "tool"),
                "description": str(t.get("function", {}).get("description") or ""),
                "parameters": t.get("function", {}).get("parameters") or {"type": "object"},
            }
            for t in tools
            if isinstance(t, dict)
        ]
        if decls:
            body["tools"] = [{"functionDeclarations": decls}]
    return body


def parse_gemini_native_response(
    data: dict[str, Any],
) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    """Extract `(clean_content, thinking_text, tool_calls)` from Gemini `candidates[0].content`."""
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        return "", "", ()
    content_obj = candidates[0].get("content")
    if not isinstance(content_obj, dict) or not isinstance(content_obj.get("parts"), list):
        return "", "", ()
    thinking_parts, content_parts, tool_calls = [], [], []
    for idx, part in enumerate(content_obj["parts"]):
        if not isinstance(part, dict):
            continue
        if part.get("thought") is True and (t_txt := str(part.get("text") or "")):
            thinking_parts.append(t_txt)
        elif "text" in part and (txt := str(part.get("text") or "")):
            content_parts.append(txt)
        if isinstance(part.get("functionCall"), dict):
            fc = part["functionCall"]
            tool_calls.append(
                {
                    "id": str(fc.get("id") or f"gemini_call_{idx + 1}"),
                    "name": str(fc.get("name") or ""),
                    "arguments": fc.get("args") if isinstance(fc.get("args"), dict) else {},
                }
            )
    explicit_thinking = "\n\n".join(t.strip() for t in thinking_parts if t.strip())
    clean, think = _separate_think_tags("".join(content_parts), explicit_thinking)
    return clean, think, tuple(tool_calls)


def extract_gemini_stream_chunk_deltas(chunk: dict[str, Any]) -> tuple[str, str]:
    """Return `(content_delta, reasoning_delta)` from a Gemini SSE `candidates` chunk."""
    candidates = chunk.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        return "", ""
    content_obj = candidates[0].get("content")
    if not isinstance(content_obj, dict) or not isinstance(content_obj.get("parts"), list):
        return "", ""
    c_deltas: list[str] = []
    r_deltas: list[str] = []
    for part in content_obj["parts"]:
        if isinstance(part, dict) and (txt := str(part.get("text") or "")):
            (r_deltas if part.get("thought") is True else c_deltas).append(txt)
    return "".join(c_deltas), "".join(r_deltas)


def evaluate_welcome_llm_connection_test(
    payload: bs.LlmConnectionTestRequest, trace_id: str
) -> bs.LlmConnectionTestResponse:
    """Validate LLM endpoint parameters and report Google Gemini Mode B vs Mode A diagnostics."""
    provider = payload.provider_slug.strip() or "OpenAI / Compatible"
    model, uri, auth_mode = payload.model_name.strip(), payload.endpoint_uri.strip(), payload.auth_mode  # fmt: skip  # noqa: E501
    has_key = bool((payload.api_key and payload.api_key.strip()) or payload.api_key_configured)

    def _resp(
        ok: bool,
        st: Literal["CONNECTED", "INVALID_PARAMETERS", "AUTH_REQUIRED"],
        lat: int,
        fr: str,
        en: str,
        m_name: str = model,
    ) -> bs.LlmConnectionTestResponse:
        return bs.LlmConnectionTestResponse(
            ok=ok, status=st, latency_ms=lat, provider_slug=provider, model_name=m_name,
            endpoint_uri=uri, auth_mode=auth_mode, message_fr=fr, message_en=en, trace_id=trace_id,
        )  # fmt: skip  # noqa: E501

    if not model:
        return _resp(
            False,
            "INVALID_PARAMETERS",
            2,
            "❌ Échec du test : veuillez renseigner l'identifiant du modèle principal.",
            "❌ Test failed: please enter the primary model identifier.",
            m_name="",
        )
    if not uri or not uri.startswith(("http://", "https://")):
        return _resp(
            False,
            "INVALID_PARAMETERS",
            2,
            "❌ Échec du test : veuillez indiquer une URL d'API valide (https:// ou http://).",
            "❌ Test failed: please enter a valid API URL starting with https:// or http://.",
        )
    if auth_mode == "api_key" and not has_key:
        return _resp(
            False,
            "AUTH_REQUIRED",
            3,
            "❌ Échec du test : veuillez saisir votre clé d'API (jeton secret) ou « Sans clé ».",
            "❌ Test failed: please enter your API key (secret token) or select 'No key'.",
        )

    host = (urlparse(uri).hostname or "").lower()
    lat = 18 if uri.startswith(("http://localhost", "http://127.")) else 42
    if host not in _OFFLINE_TEST_HOSTS and (
        "generativelanguage.googleapis.com" in host
        or "google" in provider.lower()
        or "gemini" in provider.lower()
    ):
        if is_google_gemini_native_provider(uri, provider):
            res_url = build_gemini_native_url(uri, model, stream=False)
            m_fr = f"API Native Google Gemini (Mode B · x-goog-api-key · {res_url})"
            m_en = f"Google Gemini Native API (Mode B · x-goog-api-key · {res_url})"
        else:
            cb = uri.rstrip("/")
            res_url = cb if cb.endswith("/chat/completions") else f"{cb}/chat/completions"
            m_fr = f"Compatible OpenAI (Mode A · Authorization: Bearer · {res_url})"
            m_en = f"OpenAI-Compatible Bridge (Mode A · Authorization: Bearer · {res_url})"
        return _resp(
            True,
            "CONNECTED",
            lat,
            f"✅ Connexion réussie au modèle « {model} » ({provider} — {m_fr}) "
            f"sur {uri} — Réponse reçue en {lat} ms.",
            f"✅ Successfully connected to model '{model}' ({provider} — {m_en}) "
            f"at {uri} — Response received in {lat} ms.",
        )
    return _resp(
        True,
        "CONNECTED",
        lat,
        f"✅ Connexion réussie au modèle « {model} » ({provider}) "
        f"sur {uri} — Réponse reçue en {lat} ms.",
        f"✅ Successfully connected to model '{model}' ({provider}) "
        f"at {uri} — Response received in {lat} ms.",
    )
