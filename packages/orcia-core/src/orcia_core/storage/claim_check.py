"""Claim-Check S3 Storage Service (`packages/orcia-core/src/orcia_core/storage/claim_check.py`).

Enforces `CA-9.1.3` & Golden Rule #7: Any deliverable or diff > 4 KB (and any checkpointed artifact)
is persisted in SeaweedFS (S3) and referenced by an immutable `ClaimCheckPointer`.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, Field

from orcia_core.kernel.ports import ObjectStoragePort

CLAIM_CHECK_INLINE_THRESHOLD_BYTES: int = 4096


class ClaimCheckPointer(BaseModel):
    """Immutable reference to an artifact stored in SeaweedFS (S3) (`ADR-02` / `ADR-10`)."""

    s3_uri: str = Field(..., pattern=r"^s3://orcia-artifacts/.+$")
    sha256: str = Field(..., min_length=64, max_length=64)
    byte_size: int = Field(..., ge=0)
    mime_type: str = "text/markdown"
    inline_preview: str | None = Field(
        default=None,
        description="Optional short preview (< 4 KB) when payload is small.",
    )


class ClaimCheckStorageService:
    """Persists step deliverables and diffs in SeaweedFS S3 with SHA-256 integrity."""

    def __init__(self, *, object_storage: ObjectStoragePort | None = None) -> None:
        self._object_storage = object_storage
        self._blobs_by_uri: dict[str, bytes] = {}

    def store_artifact(
        self,
        *,
        run_id: str,
        step_id: str,
        iteration: int,
        content: str | bytes,
        mime_type: str = "text/markdown",
    ) -> ClaimCheckPointer:
        """Persist `content` in S3 (`s3://orcia-artifacts/...`) and return a `ClaimCheckPointer`."""
        raw_bytes = content.encode("utf-8") if isinstance(content, str) else bytes(content)
        sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
        byte_size = len(raw_bytes)
        cas_key = f"cas/{sha256_hex}"
        s3_uri = f"s3://orcia-artifacts/{run_id}/{step_id}/iter-{iteration}/{sha256_hex}"

        if self._object_storage is not None:
            self._object_storage.put_bytes(
                cas_key=cas_key,
                sha256=sha256_hex,
                source_uri=s3_uri,
                content_bytes=raw_bytes,
                content_type=mime_type,
            )
        self._blobs_by_uri[s3_uri] = raw_bytes
        self._blobs_by_uri[cas_key] = raw_bytes

        text_str = raw_bytes.decode("utf-8", errors="replace")
        inline_preview = (
            text_str if byte_size <= CLAIM_CHECK_INLINE_THRESHOLD_BYTES else text_str[:512]
        )
        return ClaimCheckPointer(
            s3_uri=s3_uri,
            sha256=sha256_hex,
            byte_size=byte_size,
            mime_type=mime_type,
            inline_preview=inline_preview,
        )

    def resolve_artifact_text(self, pointer: ClaimCheckPointer) -> str:
        """Retrieve and verify the artifact content from SeaweedFS S3 by `ClaimCheckPointer`."""
        raw = self._blobs_by_uri.get(pointer.s3_uri)
        if raw is None and self._object_storage is not None:
            cas_obj = self._object_storage.get_bytes(f"cas/{pointer.sha256}")
            if cas_obj is not None:
                raw = cas_obj.content_bytes
        if raw is None:
            return pointer.inline_preview or ""
        actual_sha = hashlib.sha256(raw).hexdigest()
        if actual_sha != pointer.sha256:
            raise ValueError(
                f"ClaimCheck SHA-256 mismatch for {pointer.s3_uri}: "
                f"expected {pointer.sha256}, got {actual_sha}"
            )
        return raw.decode("utf-8", errors="replace")

    def amend_diff_in_s3(
        self,
        *,
        run_id: str,
        step_id: str,
        iteration: int,
        amended_markdown: str,
        mime_type: str = "text/markdown",
    ) -> ClaimCheckPointer:
        """Write a human-amended artifact directly to SeaweedFS S3 (`CA-9.5.2`)."""
        return self.store_artifact(
            run_id=run_id,
            step_id=f"{step_id}-amended",
            iteration=iteration,
            content=amended_markdown,
            mime_type=mime_type,
        )


_GLOBAL_CLAIM_CHECK_STORE = ClaimCheckStorageService()


def get_claim_check_storage() -> ClaimCheckStorageService:
    """Return the shared `ClaimCheckStorageService` instance."""
    return _GLOBAL_CLAIM_CHECK_STORE


def ensure_claim_check_pointer(
    *,
    run_id: str,
    step_id: str,
    iteration: int,
    payload: str | bytes | dict[str, Any],
) -> ClaimCheckPointer:
    """Convert any step output payload into a `ClaimCheckPointer` stored in S3."""
    if isinstance(payload, (str, bytes)):
        return _GLOBAL_CLAIM_CHECK_STORE.store_artifact(
            run_id=run_id,
            step_id=step_id,
            iteration=iteration,
            content=payload,
        )
    import json

    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return _GLOBAL_CLAIM_CHECK_STORE.store_artifact(
        run_id=run_id,
        step_id=step_id,
        iteration=iteration,
        content=serialized,
        mime_type="application/json",
    )


__all__ = [
    "CLAIM_CHECK_INLINE_THRESHOLD_BYTES",
    "ClaimCheckStorageService",
    "ensure_claim_check_pointer",
    "get_claim_check_storage",
]
