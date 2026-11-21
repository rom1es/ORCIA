"""Thin API facade re-exporting Gemini & Anthropic dialect helpers from `orcia_core`."""

from __future__ import annotations

from orcia_core.orchestration.llm_gemini_dialect import (
    build_anthropic_native_request_body as build_anthropic_native_request_body,
)
from orcia_core.orchestration.llm_gemini_dialect import (
    build_gemini_native_headers as build_gemini_native_headers,
)
from orcia_core.orchestration.llm_gemini_dialect import (
    build_gemini_native_request_body as build_gemini_native_request_body,
)
from orcia_core.orchestration.llm_gemini_dialect import (
    build_gemini_native_url as build_gemini_native_url,
)
from orcia_core.orchestration.llm_gemini_dialect import (
    extract_gemini_stream_chunk_deltas as extract_gemini_stream_chunk_deltas,
)
from orcia_core.orchestration.llm_gemini_dialect import (
    is_google_gemini_native_provider as is_google_gemini_native_provider,
)
from orcia_core.orchestration.llm_gemini_dialect import (
    parse_gemini_native_response as parse_gemini_native_response,
)
from orcia_core.orchestration.llm_gemini_dialect import (
    separate_think_tags as _separate_think_tags,
)

__all__ = [
    "_separate_think_tags",
    "build_anthropic_native_request_body",
    "build_gemini_native_headers",
    "build_gemini_native_request_body",
    "build_gemini_native_url",
    "extract_gemini_stream_chunk_deltas",
    "is_google_gemini_native_provider",
    "parse_gemini_native_response",
]
