"""Payload parser for MCP `_meta.usage`, A2A `usage`, and `X-Orcia-Usage` headers (`Story 6.4`)."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

from orcia_core.ports.finops_telemetry import RemoteUsageRawPayload
from orcia_kernel.errors import ValidationDomainError


def _parse_header_usage(raw_header: str) -> dict[str, Any]:
    text = raw_header.strip()
    if not text:
        return {}
    if text.startswith(("{", "[")):
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise ValidationDomainError(
                    detail_override="X-Orcia-Usage JSON payload must be an object."
                )
            return parsed
        except json.JSONDecodeError as exc:
            raise ValidationDomainError(
                detail_override="Malformed JSON in X-Orcia-Usage header."
            ) from exc

    parsed_kv: dict[str, Any] = {}
    for chunk in text.replace(";", ",").split(","):
        part = chunk.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        key = k.strip()
        val_str = v.strip()
        if key in ("currency", "unit_name", "model_name"):
            parsed_kv[key] = val_str
        else:
            try:
                num = float(val_str)
            except ValueError as exc:
                raise ValidationDomainError(
                    detail_override=f"Invalid numeric X-Orcia-Usage value for '{key}': {val_str!r}"
                ) from exc
            if not math.isfinite(num) or num < 0.0:
                raise ValidationDomainError(
                    detail_override=f"Invalid X-Orcia-Usage value for '{key}': {val_str!r}"
                )
            parsed_kv[key] = int(num) if key.endswith("_tokens") and num.is_integer() else num
    return parsed_kv


def extract_remote_usage_payload(
    response_payload: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> RemoteUsageRawPayload:
    """Extract raw telemetry from `_meta.usage`, A2A `usage`, or `X-Orcia-Usage` header."""
    usage_dict: dict[str, Any] = {}
    if response_payload is not None:
        meta = response_payload.get("_meta")
        if isinstance(meta, Mapping) and isinstance(meta.get("usage"), Mapping):
            usage_dict = dict(meta["usage"])
        elif isinstance(response_payload.get("usage"), Mapping):
            usage_dict = dict(response_payload["usage"])

    if not usage_dict and headers is not None:
        for hdr_key, hdr_val in headers.items():
            if hdr_key.lower() == "x-orcia-usage":
                usage_dict = _parse_header_usage(hdr_val)
                break

    if not usage_dict:
        return RemoteUsageRawPayload()

    def _parse_int_field(keys: tuple[str, ...]) -> int | None:
        for k in keys:
            if k in usage_dict and usage_dict[k] is not None:
                raw_v = usage_dict[k]
                if isinstance(raw_v, bool):
                    raise ValidationDomainError(detail_override=f"Invalid boolean for '{k}'.")
                if isinstance(raw_v, float):
                    if not math.isfinite(raw_v) or raw_v < 0 or not raw_v.is_integer():
                        raise ValidationDomainError(
                            detail_override=f"Invalid token count for '{k}': {raw_v!r}."
                        )
                    return int(raw_v)
                if isinstance(raw_v, int):
                    return raw_v
                raise ValidationDomainError(
                    detail_override=f"Invalid integer for '{k}': {raw_v!r}."
                )
        return None

    def _parse_float_field(keys: tuple[str, ...]) -> float | None:
        for k in keys:
            if k in usage_dict and usage_dict[k] is not None:
                raw_v = usage_dict[k]
                if isinstance(raw_v, bool):
                    raise ValidationDomainError(detail_override=f"Invalid boolean for '{k}'.")
                try:
                    fval = float(raw_v)
                except (TypeError, ValueError) as exc:
                    raise ValidationDomainError(
                        detail_override=f"Invalid numeric value for '{k}': {raw_v!r}."
                    ) from exc
                if not math.isfinite(fval) or fval < 0.0:
                    raise ValidationDomainError(
                        detail_override=f"Telemetry '{k}' must be finite and >= 0: {raw_v!r}."
                    )
                return fval
        return None

    currency = usage_dict.get("currency")
    if currency is None and "cost_usd" in usage_dict and "cost_eur" not in usage_dict:
        currency = "USD"
    elif currency is None and "cost_eur" in usage_dict:
        currency = "EUR"

    return RemoteUsageRawPayload(
        input_tokens=_parse_int_field(("input_tokens", "prompt_tokens")),
        output_tokens=_parse_int_field(("output_tokens", "completion_tokens")),
        cost_amount=_parse_float_field(("cost_amount", "cost", "cost_eur", "cost_usd")),
        currency=str(currency) if currency is not None else None,
        unit_count=_parse_float_field(("unit_count", "units")),
        unit_name=str(usage_dict["unit_name"]) if usage_dict.get("unit_name") is not None else None,
        model_name=(
            str(usage_dict["model_name"]) if usage_dict.get("model_name") is not None else None
        ),
        raw_metadata=usage_dict,
    )


__all__ = ["extract_remote_usage_payload"]
