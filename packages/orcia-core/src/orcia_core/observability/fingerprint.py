"""Deterministic pure-Python error fingerprinting for log-sink anomaly detection (`AD-23`)."""

from __future__ import annotations

import hashlib
import os
import re

_FRAME_RE = re.compile(r'File\s+"([^"]+)",\s+line\s+\d+,\s+in\s+([^\s\r\n]+)')
_HEX_ADDR_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_frame_path(raw_path: str) -> str:
    cleaned = raw_path.strip().replace("\\", "/")
    if not cleaned:
        return "unknown"
    return os.path.basename(cleaned) or cleaned


def extract_top_frame(traceback_text: str | None) -> str:
    """Extract normalized innermost `<filename>:<function>` from a Python traceback."""
    if not traceback_text or not traceback_text.strip():
        return "unknown"
    matches = _FRAME_RE.findall(traceback_text)
    if matches:
        file_path, func_name = matches[-1]
        norm_file = _normalize_frame_path(file_path)
        norm_func = func_name.strip() or "<module>"
        return f"{norm_file}:{norm_func}"

    first_line = traceback_text.strip().splitlines()[0].strip()
    normalized = _HEX_ADDR_RE.sub("0xADDR", first_line)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized[:160] if normalized else "unknown"


def compute_error_fingerprint_sha256(
    service: str,
    exception_type: str,
    top_frame: str,
) -> str:
    """Compute deterministic `sha256:<64-hex>` error fingerprint in pure Python (`AD-23` D5/D7)."""
    norm_service = (service or "unknown").strip().lower()
    norm_exc = (exception_type or "Exception").strip()
    norm_frame = _HEX_ADDR_RE.sub("0xADDR", (top_frame or "unknown").strip())
    norm_frame = _WHITESPACE_RE.sub(" ", norm_frame)
    canonical = f"{norm_service}|{norm_exc}|{norm_frame}"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


__all__ = [
    "compute_error_fingerprint_sha256",
    "extract_top_frame",
]
