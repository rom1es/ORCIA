"""JSONL transcript discovery and parsing for dev-only `scripts/agent_token_report.py` (`T-D9`)."""

from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TEST_CMD_RE = re.compile(
    r"\b(agent_check\.py|pytest|vitest|ruff|mypy|lint-imports|playwright|turbo|site:check|coverage|lint_spine\.py)\b"
)
GEN_PATH_RE = re.compile(r"(?:^|/)(?:generated/|openapi\.json$|pnpm-lock\.yaml$|uv\.lock$)")
WRITE_TOOLS = frozenset(
    (
        "write_file",
        "edit_file",
        "replace_file_content",
        "multi_replace_file_content",
        "write_to_file",
    )
)
READ_TOOLS = frozenset({"read_file", "view_file"})
ACT_ORDER = (
    "run_test_or_check",
    "poll_task",
    "write_test",
    "read_test",
    "write_src",
    "read_src",
    "write_docs",
    "read_docs",
    "shell_explore",
    "code_intel",
    "manage_task",
    "other_tool",
)


@dataclass(slots=True)
class ConversationStats:
    """Aggregated token and activity metrics for one conversation transcript."""

    conv_id: str
    turns: int = 0
    fresh_input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    total_read_file_calls: int = 0
    duplicate_read_file_calls: int = 0
    generated_full_read_count: int = 0
    activity_turns: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    activity_input_tokens: dict[str, int] = field(default_factory=lambda: defaultdict(int))


def _first_val(mapping: dict[str, Any], *keys: str) -> Any:
    return next((mapping[k] for k in keys if mapping.get(k) is not None), None)


def _is_test_path(path_str: str) -> bool:
    norm = path_str.replace("\\", "/")
    return any(x in f"/{norm}" for x in ("/tests/", "/__tests__/", ".test.", ".spec.")) or (
        Path(norm).name.startswith("test_")
    )


def extract_tokens(record: dict[str, Any]) -> tuple[int, int, int]:
    """Return `(fresh_input, cached_input, output)` aligned with the Epic 30-31 baseline formula."""
    u = _first_val(record, "usage", "token_usage", "usageMetadata") or record
    if not isinstance(u, dict):
        return 0, 0, 0
    out = int(_first_val(u, "output_tokens", "completion_tokens", "candidatesTokenCount") or 0)
    if "cache_read_tokens" in u:
        return int(u.get("input_tokens") or 0), int(u.get("cache_read_tokens") or 0), out
    if "cache_read_input_tokens" in u:
        return int(u.get("input_tokens") or 0), int(u.get("cache_read_input_tokens") or 0), out
    if "fresh_input_tokens" in u:
        return int(u.get("fresh_input_tokens") or 0), int(u.get("cached_input_tokens") or 0), out
    total_in = int(_first_val(u, "prompt_tokens", "input_tokens", "promptTokenCount") or 0)
    details = _first_val(u, "prompt_tokens_details", "input_tokens_details")
    cached_sub = details.get("cached_tokens") if isinstance(details, dict) else 0
    cached = int(cached_sub or _first_val(u, "cached_input_tokens", "cachedContentTokenCount") or 0)
    return max(0, total_in - cached), cached, out


def _parse_calls_field(raw_calls: Any) -> list[Any]:
    if isinstance(raw_calls, list):
        return raw_calls
    if isinstance(raw_calls, str) and raw_calls.strip():
        try:
            parsed = json.loads(raw_calls)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(raw_calls)
                return parsed if isinstance(parsed, list) else []
            except (ValueError, SyntaxError):
                return []
    return []


def extract_tool_calls(record: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Extract `(tool_name, args_dict)` pairs from list or serialized `tool_calls` fields."""
    calls: list[tuple[str, dict[str, Any]]] = []
    items = _parse_calls_field(_first_val(record, "tool_calls", "calls", "tool_uses"))
    if not items and record.get("tool_name"):
        items = [
            {"name": record["tool_name"], "arguments": _first_val(record, "arguments", "args")}
        ]
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(_first_val(item, "name", "tool_name") or "").strip()
        raw_args = _first_val(item, "arguments", "args", "input")
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args)
            except json.JSONDecodeError:
                raw_args = {}
        if name:
            calls.append((name, raw_args if isinstance(raw_args, dict) else {}))
    return calls


def _read_path_and_range(args: dict[str, Any]) -> tuple[str, int | None, int | None]:
    path_val = str(_first_val(args, "Path", "path", "file_path", "TargetFile") or "").strip()
    start = _first_val(args, "StartLine", "start_line")
    end = _first_val(args, "EndLine", "end_line")
    return (
        path_val,
        int(start) if isinstance(start, int) else None,
        int(end) if isinstance(end, int) else None,
    )


def _is_dup_read(
    seen: dict[str, list[tuple[int | None, int | None]]],
    path_val: str,
    start: int | None,
    end: int | None,
) -> bool:
    prev = seen.get(path_val, [])
    if not prev:
        return False
    if start is None and end is None:
        return True
    s1, e1 = start or 1, end or 10**9
    return any(
        (ps is None and pe is None) or (s1 <= (pe or 10**9) and (ps or 1) <= e1) for ps, pe in prev
    )


def _classify_call(name: str, args: dict[str, Any]) -> str:
    low = name.lower()
    if low in READ_TOOLS or low in WRITE_TOOLS:
        path_val, _, _ = _read_path_and_range(args)
        prefix = "read" if low in READ_TOOLS else "write"
        if _is_test_path(path_val):
            return f"{prefix}_test"
        return f"{prefix}_docs" if path_val.startswith("docs/") else f"{prefix}_src"
    if low in {"run_command", "bash", "shell"}:
        cmd = str(_first_val(args, "CommandLine", "command") or "")
        return "run_test_or_check" if TEST_CMD_RE.search(cmd) else "shell_explore"
    if low == "manage_task":
        act = str(_first_val(args, "Action", "action") or "").lower()
        return "poll_task" if act in {"status", "list", ""} else "manage_task"
    return "code_intel" if ("gitnexus" in low or low == "call_mcp_tool") else "other_tool"


def _is_llm_turn_record(rec: dict[str, Any]) -> bool:
    """In Antigravity transcripts only `PLANNER_RESPONSE` rows represent billed LLM turns."""
    rec_type = rec.get("type")
    if isinstance(rec_type, str):
        return rec_type == "PLANNER_RESPONSE"
    return True


def analyze_transcript(jsonl_path: Path) -> ConversationStats:
    """Parse one JSONL transcript into token, activity, and read-discipline counters."""
    cid = jsonl_path.parent.name if jsonl_path.stem.startswith("transcript") else jsonl_path.stem
    stats = ConversationStats(conv_id=cid)
    seen: dict[str, list[tuple[int | None, int | None]]] = defaultdict(list)

    for raw in jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or not _is_llm_turn_record(rec):
            continue
        stats.turns += 1
        fresh, cached, output = extract_tokens(rec)
        stats.fresh_input_tokens += fresh
        stats.cached_input_tokens += cached
        stats.output_tokens += output
        turn_acts: set[str] = set()
        for name, args in extract_tool_calls(rec):
            turn_acts.add(_classify_call(name, args))
            if name.lower() in READ_TOOLS:
                p, s, e = _read_path_and_range(args)
                if p:
                    stats.total_read_file_calls += 1
                    stats.duplicate_read_file_calls += int(_is_dup_read(seen, p, s, e))
                    seen[p].append((s, e))
                    stats.generated_full_read_count += int(
                        bool(GEN_PATH_RE.search(p)) and s is None and e is None
                    )
        primary = next((a for a in ACT_ORDER if a in turn_acts), "no_tool_turn")
        stats.activity_turns[primary] += 1
        stats.activity_input_tokens[primary] += fresh + cached
    return stats


def _matches(path: Path, *, story: str | None, convs: list[str]) -> bool:
    posix = path.as_posix()
    if convs and not any(c in posix for c in convs):
        return False
    if not story:
        return True
    low = story.lower()
    if low in posix.lower():
        return True
    head = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:5])
    return low in head.lower()


def discover_transcript_files(
    tdir: Path, *, story: str | None = None, convs: list[str] | None = None
) -> list[Path]:
    """Locate one canonical transcript JSONL per conversation (skipping `chunks/` shards)."""
    if not tdir.is_dir():
        return []
    conv_filters = [c for c in (convs or []) if c]
    by_parent: dict[Path, dict[str, Path]] = defaultdict(dict)
    for cand in sorted(tdir.rglob("*.jsonl")):
        if "chunks" in cand.parts:
            continue
        if _matches(cand, story=story, convs=conv_filters):
            by_parent[cand.parent][cand.name] = cand
    selected: list[Path] = []
    for parent in sorted(by_parent):
        names = by_parent[parent]
        pick = names.get("transcript_full.jsonl") or names.get("transcript.jsonl")
        selected.extend([pick] if pick else names.values())
    return selected
