#!/usr/bin/env python3
"""Dev-only agent transcript token and read-discipline telemetry (`T-D9`, never in CI)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.agent_check_lib.token_parser import (  # noqa: E402
    ConversationStats,
    analyze_transcript,
    discover_transcript_files,
)


def aggregate_reports(stats_list: list[ConversationStats]) -> dict[str, Any]:
    """Combine per-conversation stats into a single JSON-serializable report."""
    fresh = sum(s.fresh_input_tokens for s in stats_list)
    cached = sum(s.cached_input_tokens for s in stats_list)
    total_in = fresh + cached
    turns = sum(s.turns for s in stats_list)
    reads = sum(s.total_read_file_calls for s in stats_list)
    dupes = sum(s.duplicate_read_file_calls for s in stats_list)
    all_acts = sorted({act for s in stats_list for act in s.activity_turns})
    return {
        "conversations_matched": len(stats_list),
        "turns": turns,
        "fresh_input_tokens": fresh,
        "cached_input_tokens": cached,
        "total_input_tokens": total_in,
        "avg_context_per_turn": round(total_in / turns) if turns else 0,
        "output_tokens": sum(s.output_tokens for s in stats_list),
        "total_read_file_calls": reads,
        "duplicate_read_file_calls": dupes,
        "duplicate_read_rate": round(dupes / reads, 4) if reads else 0.0,
        "generated_full_read_count": sum(s.generated_full_read_count for s in stats_list),
        "activity_breakdown": {
            act: {
                "turns": sum(s.activity_turns.get(act, 0) for s in stats_list),
                "input_tokens": sum(s.activity_input_tokens.get(act, 0) for s in stats_list),
            }
            for act in all_acts
        },
    }


def format_markdown(r: dict[str, Any]) -> str:
    """Render report dictionary as compact Markdown for Tech Lead Report §3."""
    rate = f"{r['duplicate_read_rate'] * 100:.1f}%"
    dupes = f"{r['duplicate_read_file_calls']}/{r['total_read_file_calls']}"
    lines = [
        "### Token Telemetry Report",
        f"- Conversations: `{r['conversations_matched']}`, Turns: `{r['turns']}`",
        f"- Billed Input: `{r['total_input_tokens']:,}` "
        f"(fresh `{r['fresh_input_tokens']:,}`, cached `{r['cached_input_tokens']:,}`, "
        f"avg/turn `{r['avg_context_per_turn']:,}`)",
        f"- Output: `{r['output_tokens']:,}`",
        f"- Duplicate `read_file`: `{rate}` (`{dupes}`), "
        f"`generated/`: `{r['generated_full_read_count']}`",
        "",
        "| Activity | Turns | Input Tokens |",
        "| :--- | ---: | ---: |",
    ]
    for a, v in r["activity_breakdown"].items():
        lines.append(f"| `{a}` | {v['turns']} | {v['input_tokens']:,} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint; exits 0 gracefully with SKIP if `ORCIA_TRANSCRIPTS_DIR` is unset."""
    p = argparse.ArgumentParser(description="Dev-only ORCIA agent token telemetry report.")
    p.add_argument("--transcripts-dir", default=None)
    p.add_argument("--story", default=None)
    p.add_argument("--conv", action="append", default=[])
    p.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = p.parse_args(argv)
    raw = (args.transcripts_dir or os.environ.get("ORCIA_TRANSCRIPTS_DIR", "")).strip()
    if not raw:
        print("SKIP: ORCIA_TRANSCRIPTS_DIR not set")
        return 0
    tdir = Path(raw).expanduser()
    if not tdir.is_dir():
        print(f"SKIP: transcripts directory not found: {tdir}")
        return 0
    files = discover_transcript_files(tdir, story=args.story, convs=args.conv)
    report = aggregate_reports([analyze_transcript(f) for f in files])
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
