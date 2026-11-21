"""Prompt Cache Serialization Helpers for `AssistantThreeSpeedRouterService` (`Story 10.2`)."""

from __future__ import annotations

import hashlib
import json

from orcia_core.orchestration.assistant_governance import AssembledLayerPreviewItem
from orcia_core.orchestration.assistant_three_speed_models import (
    PROMPT_CACHE_TTL_SECONDS,
    CachedAssembledPromptResult,
)


def decode_cached_prompt(
    *, cache_key: str, cached_raw: str, elapsed_ms: float
) -> CachedAssembledPromptResult:
    """Decode serialized JSON prompt layers into a `CachedAssembledPromptResult` hit."""
    data = json.loads(cached_raw)
    layers = tuple(
        AssembledLayerPreviewItem(
            layer_number=int(item["layer_number"]),
            layer_code=item["layer_code"],
            label=str(item["label"]),
            immutable=bool(item["immutable"]),
            origin_badge=item["origin_badge"],
            content=str(item["content"]),
            sha256=str(item["sha256"]),
        )
        for item in data["layers"]
    )
    return CachedAssembledPromptResult(
        cache_key=cache_key,
        cache_hit=True,
        ttl_seconds=PROMPT_CACHE_TTL_SECONDS,
        lookup_latency_ms=elapsed_ms,
        assembled_prompt_text=str(data["assembled_prompt_text"]),
        layers_sha256=str(data["layers_sha256"]),
        layers=layers,
    )


def encode_assembled_prompt(
    layers: tuple[AssembledLayerPreviewItem, ...],
) -> tuple[str, str, str]:
    """Serialize assembled 5-layer preview to JSON alongside assembled text and SHA-256."""
    assembled_text = "\n\n".join(f"### {layer.label}\n{layer.content}" for layer in layers)
    digest = hashlib.sha256(assembled_text.encode("utf-8")).hexdigest()
    payload = json.dumps(
        {
            "assembled_prompt_text": assembled_text,
            "layers_sha256": digest,
            "layers": [
                {
                    "layer_number": lyr.layer_number,
                    "layer_code": lyr.layer_code,
                    "label": lyr.label,
                    "immutable": lyr.immutable,
                    "origin_badge": lyr.origin_badge,
                    "content": lyr.content,
                    "sha256": lyr.sha256,
                }
                for lyr in layers
            ],
        },
        ensure_ascii=False,
    )
    return assembled_text, digest, payload
