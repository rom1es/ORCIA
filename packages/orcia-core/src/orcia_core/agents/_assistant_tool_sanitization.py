"""Anti-Injection Delimiters & Secret Scrubbing for Untrusted Tool Outputs (`Story 26.6b`)."""

from __future__ import annotations

import json
import re
from typing import Any

from orcia_core.observability.logging import scrub_sensitive_text
from orcia_core.permissions.connector_invoker import scrub_connector_secrets

_MARKER_TAG_RE = re.compile(
    r"\[((?:"
    r"LAYER|CONSTITUTIONAL|ONTOLOGY|HUMAN_PROFILE|ADAPTATION|"
    r"FEDERATED_CONTEXT_FANOUT|CONVERSATIONAL_INTENT|"
    r"SERVER_EVIDENCE_TABLE|TABLE_PREUVES_SERVEUR|"
    r"NO_HUMAN_ANCHOR_WRITE|NO_GATE_SELF_APPROVAL|"
    r"EXPLICIT_PROVENANCE_URI|STALE_WARNING"
    r")(?:[_\s:=-]+[^\]]*)?)\]",
    re.IGNORECASE,
)
_TOOL_TAG_OPEN_RE = re.compile(r"<\s*untrusted_tool_output\b", re.IGNORECASE)
_TOOL_TAG_CLOSE_RE = re.compile(r"<\s*/\s*untrusted_tool_output\b", re.IGNORECASE)


def neutralize_untrusted_text(raw_text: str) -> str:
    """Scrub secrets and escape `[LAYER_*]` / `<untrusted_tool_output>` prompt-injection tags."""
    scrubbed = scrub_sensitive_text(raw_text)
    neutralized = _MARKER_TAG_RE.sub(r"(escaped:\1)", scrubbed)
    neutralized = _TOOL_TAG_CLOSE_RE.sub("&lt;/untrusted_tool_output", neutralized)
    neutralized = _TOOL_TAG_OPEN_RE.sub("&lt;untrusted_tool_output", neutralized)
    return neutralized


def wrap_untrusted_tool_output(
    *,
    tool_call_id: str,
    tool_name: str,
    payload: str | dict[str, Any],
) -> tuple[str, str]:
    """Scrub secrets, neutralize injection markers, and wrap in delimited untrusted tags."""
    if isinstance(payload, dict):
        scrubbed_dict = scrub_connector_secrets(payload)
        raw_str = json.dumps(scrubbed_dict, ensure_ascii=False, sort_keys=True)
    else:
        raw_str = str(payload)
    clean_body = neutralize_untrusted_text(raw_str)
    clean_call_id = re.sub(r"[^a-zA-Z0-9_.:-]", "_", tool_call_id or "call_1")
    clean_tool = re.sub(r"[^a-zA-Z0-9_.:-]", "_", tool_name or "tool")
    delimited = (
        f'<untrusted_tool_output tool_call_id="{clean_call_id}" '
        f'tool_name="{clean_tool}" untrusted="true">\n'
        f"{clean_body}\n"
        "</untrusted_tool_output>"
    )
    return delimited, clean_body[:512]


__all__ = ["neutralize_untrusted_text", "wrap_untrusted_tool_output"]
