"""Reversible PII Pseudonymizer (`PiiReversibleScrubber`) & Executor CoT Purger (`Story 4.2`).

Implements `FR-18`, `AD-10`, and `NFR-SEC-2`:
- `PiiReversibleScrubber`: replaces personal data (emails, phone numbers, IBANs, SSN/NIR,
  tokens/secrets, and custom named entities) with deterministic tokens (`[PII_EMAIL_1]`,
  `[PII_IBAN_1]`, etc.) scoped to `run_id` (stored in Redis with TTL or in-memory per `run_id`),
  and re-hydrates them locally upon evaluator return.
- `purge_executor_chain_of_thought`: strips internal reasoning blocks (`<thinking>...</thinking>`,
  `[THOUGHT]...[/THOUGHT]`, `chain_of_thought`, `reasoning_content`, `internal_cot`) from the
  executor's candidate artifact before sending it to the 4 independent evaluator lenses.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b")
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.\-]?\(?\d{1,4}\)?|\b0[1-9])(?:[\s.\-]?\d{2}){4}\b")
_SSN_RE = re.compile(r"\b[12]\s?\d{2}\s?(?:0[1-9]|1[0-2])\s?\d{2}\s?\d{3}\s?\d{3}(?:\s?\d{2})?\b")
_SECRET_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_\-]{8,}|ghp_[A-Za-z0-9]{12,}|CANARY_SECRET_[A-Za-z0-9_\-]+)\b"
)

_COT_TAG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<cot>.*?</cot>", re.DOTALL | re.IGNORECASE),
    re.compile(r"\[THOUGHT\].*?\[/THOUGHT\]", re.DOTALL | re.IGNORECASE),
    re.compile(r"\[INTERNAL_REASONING\].*?\[/INTERNAL_REASONING\]", re.DOTALL | re.IGNORECASE),
)

_COT_FIELD_KEYS: frozenset[str] = frozenset(
    {
        "chain_of_thought",
        "reasoning_content",
        "internal_cot",
        "executor_thinking",
        "thinking_trace",
        "raw_cot",
    }
)


@runtime_checkable
class PiiTokenVaultBackendPort(Protocol):
    """Optional Redis-compatible key-value backend for `PiiReversibleScrubber` (`NFR-SEC-2`)."""

    def setex(self, name: str, time: int, value: str) -> Any:
        """Store JSON token map under `name` with TTL `time` seconds."""
        ...

    def get(self, name: str) -> str | bytes | None:
        """Retrieve JSON token map stored under `name`."""
        ...


@dataclass(frozen=True, slots=True)
class PiiScrubResult:
    """Result of reversible PII scrubbing on a text or structured payload (`NFR-SEC-2`)."""

    run_id: str
    scrubbed_text: str
    token_to_original: dict[str, str] = field(default_factory=dict)
    redacted_count: int = 0


class PiiReversibleScrubber:
    """Reversible PII pseudonymizer scoped per `run_id` (`anonymize_pii_reversible: true`)."""

    def __init__(
        self,
        *,
        vault_backend: PiiTokenVaultBackendPort | None = None,
        ttl_seconds: int = 3600,
    ) -> None:
        self._backend = vault_backend
        self.ttl_seconds = max(60, ttl_seconds)
        self._memory_vault: dict[str, dict[str, str]] = {}

    def _redis_key(self, run_id: str) -> str:
        return f"pii:vault:run:{run_id}"

    def get_token_map(self, run_id: str) -> dict[str, str]:
        """Return `{token: original_value}` map for `run_id` from Redis or memory."""
        if self._backend is not None:
            raw = self._backend.get(self._redis_key(run_id))
            if raw is not None:
                text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                loaded = json.loads(text)
                if isinstance(loaded, dict):
                    mapping = {str(k): str(v) for k, v in loaded.items()}
                    self._memory_vault[run_id] = dict(mapping)
                    return mapping
        return dict(self._memory_vault.get(run_id, {}))

    def _save_token_map(self, run_id: str, token_to_original: dict[str, str]) -> None:
        self._memory_vault[run_id] = dict(token_to_original)
        if self._backend is not None:
            self._backend.setex(
                self._redis_key(run_id),
                self.ttl_seconds,
                json.dumps(token_to_original, sort_keys=True),
            )

    def scrub_text(
        self,
        run_id: str,
        text: str,
        *,
        custom_entities: tuple[str, ...] = (),
    ) -> PiiScrubResult:
        """Replace PII and secrets in `text` with deterministic tokens scoped to `run_id`."""
        token_to_original = self.get_token_map(run_id)
        original_to_token: dict[str, str] = {v: k for k, v in token_to_original.items()}
        counters: dict[str, int] = {
            "EMAIL": 0,
            "IBAN": 0,
            "PHONE": 0,
            "SSN": 0,
            "SECRET": 0,
            "ENTITY": 0,
        }
        for tok in token_to_original:
            for category in counters:
                prefix = f"[PII_{category}_"
                if tok.startswith(prefix) and tok.endswith("]"):
                    try:
                        idx = int(tok[len(prefix) : -1])
                        counters[category] = max(counters[category], idx)
                    except ValueError:
                        pass

        redacted_count = 0

        def _assign_token(category: str, original_val: str) -> str:
            nonlocal redacted_count
            redacted_count += 1
            existing = original_to_token.get(original_val)
            if existing is not None:
                return existing
            counters[category] += 1
            token = f"[PII_{category}_{counters[category]}]"
            token_to_original[token] = original_val
            original_to_token[original_val] = token
            return token

        scrubbed = text
        for entity in custom_entities:
            cleaned_entity = entity.strip()
            if cleaned_entity and cleaned_entity in scrubbed:
                tok = _assign_token("ENTITY", cleaned_entity)
                scrubbed = scrubbed.replace(cleaned_entity, tok)

        for category, pattern in (
            ("SECRET", _SECRET_RE),
            ("IBAN", _IBAN_RE),
            ("EMAIL", _EMAIL_RE),
            ("SSN", _SSN_RE),
            ("PHONE", _PHONE_RE),
        ):

            def _replace_match(match: re.Match[str], cat: str = category) -> str:
                return _assign_token(cat, match.group(0))

            scrubbed = pattern.sub(_replace_match, scrubbed)

        self._save_token_map(run_id, token_to_original)
        return PiiScrubResult(
            run_id=run_id,
            scrubbed_text=scrubbed,
            token_to_original=dict(token_to_original),
            redacted_count=redacted_count,
        )

    def scrub_payload(
        self,
        run_id: str,
        payload: dict[str, Any],
        *,
        custom_entities: tuple[str, ...] = (),
    ) -> tuple[dict[str, Any], dict[str, str], int]:
        """Recursively scrub all string values in `payload` using deterministic tokens."""
        total_redacted = 0

        def _walk(node: Any) -> Any:
            nonlocal total_redacted
            if isinstance(node, str):
                res = self.scrub_text(run_id, node, custom_entities=custom_entities)
                total_redacted += res.redacted_count
                return res.scrubbed_text
            if isinstance(node, dict):
                return {str(k): _walk(v) for k, v in node.items()}
            if isinstance(node, (list, tuple)):
                return [_walk(item) for item in node]
            return node

        scrubbed_dict: dict[str, Any] = _walk(payload)
        return scrubbed_dict, self.get_token_map(run_id), total_redacted

    def rehydrate_text(self, run_id: str, scrubbed_text: str) -> str:
        """Restore original PII values in `scrubbed_text` from the `run_id` vault (`NFR-SEC-2`)."""
        mapping = self.get_token_map(run_id)
        restored = scrubbed_text
        for token, original in mapping.items():
            if token in restored:
                restored = restored.replace(token, original)
        return restored

    def rehydrate_payload(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively restore original PII values in `payload` from the `run_id` vault."""

        def _walk(node: Any) -> Any:
            if isinstance(node, str):
                return self.rehydrate_text(run_id, node)
            if isinstance(node, dict):
                return {str(k): _walk(v) for k, v in node.items()}
            if isinstance(node, (list, tuple)):
                return [_walk(item) for item in node]
            return node

        rehydrated: dict[str, Any] = _walk(payload)
        return rehydrated


def purge_executor_chain_of_thought(
    artifact_payload: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Strip executor Chain-of-Thought fields and inline tags before evaluator lenses (`FR-18`)."""

    purged_count = 0

    def _clean_str(value: str) -> str:
        nonlocal purged_count
        cleaned = value
        for pattern in _COT_TAG_PATTERNS:
            matches = pattern.findall(cleaned)
            if matches:
                purged_count += len(matches)
                cleaned = pattern.sub("", cleaned)
        return cleaned.strip()

    def _walk(node: Any) -> Any:
        nonlocal purged_count
        if isinstance(node, str):
            return _clean_str(node)
        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for k, v in node.items():
                if str(k).strip().lower() in _COT_FIELD_KEYS:
                    purged_count += 1
                    continue
                out[str(k)] = _walk(v)
            return out
        if isinstance(node, (list, tuple)):
            return [_walk(item) for item in node]
        return node

    purged: dict[str, Any] = _walk(artifact_payload)
    return purged, purged_count


__all__ = [
    "PiiReversibleScrubber",
    "PiiScrubResult",
    "PiiTokenVaultBackendPort",
    "purge_executor_chain_of_thought",
]
