"""Unit tests for dev-only `scripts/agent_token_report.py` (`T-D9`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.agent_token_report import main as report_main


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n",
        encoding="utf-8",
    )


def test_token_report_graceful_skip_when_env_unset_or_missing_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ORCIA_TRANSCRIPTS_DIR", raising=False)
    assert report_main([]) == 0
    assert "SKIP: ORCIA_TRANSCRIPTS_DIR not set" in capsys.readouterr().out

    missing = tmp_path / "no_such_dir"
    assert report_main(["--transcripts-dir", str(missing)]) == 0
    assert "SKIP: transcripts directory not found" in capsys.readouterr().out


def test_token_report_handles_edge_records_and_secondary_activities(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tdir = tmp_path / "transcripts"
    conv_file = tdir / "story_edge.jsonl"
    conv_file.parent.mkdir(parents=True)
    conv_file.write_text(
        "\n".join(
            [
                "{not-json",
                '"scalar-line"',
                json.dumps(
                    {
                        "story": "32-2-edge",
                        "tool_name": "read_file",
                        "arguments": json.dumps({"Path": "docs/guide.md"}),
                    }
                ),
                json.dumps(
                    {
                        "usage": {"input_tokens": 100, "output_tokens": 20},
                        "tool_calls": [
                            {"name": "write_file", "arguments": {"Path": "docs/guide.md"}},
                            {"name": "run_command", "arguments": {"CommandLine": "ls -la"}},
                            {"name": "call_mcp_tool", "arguments": {}},
                            {"name": "manage_task", "arguments": {"Action": "kill"}},
                            {"name": "custom_tool", "arguments": {}},
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert report_main(["--transcripts-dir", str(tdir), "--story", "32-2", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["conversations_matched"] == 1
    assert data["turns"] == 2
    assert "read_docs" in data["activity_breakdown"]
    assert "write_docs" in data["activity_breakdown"]


def test_token_report_parses_epic31_schema_activities_dupes_and_generated_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tdir = tmp_path / "transcripts"
    conv_dir = tdir / "32-1-coder-conv"
    _write_jsonl(
        conv_dir / "transcript_full.jsonl",
        [
            {
                "turn": 1,
                "story": "32-1-token-first",
                "usage": {
                    "prompt_tokens": 250000,
                    "prompt_tokens_details": {"cached_tokens": 235000},
                    "completion_tokens": 1200,
                },
                "tool_calls": [
                    {"name": "read_file", "arguments": {"Path": "apps/api/src/main.py"}},
                ],
            },
            {
                "turn": 2,
                "usage": {
                    "input_tokens": 10000,
                    "cache_read_input_tokens": 240000,
                    "output_tokens": 800,
                },
                "tool_calls": [
                    {"name": "read_file", "arguments": {"Path": "apps/api/src/main.py"}},
                    {
                        "name": "read_file",
                        "arguments": {"Path": "packages/api-client/src/generated/index.ts"},
                    },
                ],
            },
            {
                "turn": 3,
                "usage": {
                    "fresh_input_tokens": 5000,
                    "cached_input_tokens": 245000,
                    "output_tokens": 600,
                },
                "tool_calls": [
                    {
                        "name": "read_file",
                        "arguments": {
                            "Path": "apps/api/src/router.py",
                            "StartLine": 1,
                            "EndLine": 40,
                        },
                    },
                    {
                        "name": "read_file",
                        "arguments": {
                            "Path": "apps/api/src/router.py",
                            "StartLine": 41,
                            "EndLine": 80,
                        },
                    },
                    {
                        "name": "edit_file",
                        "arguments": {"Path": "apps/api/src/main.py"},
                    },
                ],
            },
            {
                "turn": 4,
                "usage": {
                    "fresh_input_tokens": 4000,
                    "cached_input_tokens": 246000,
                    "output_tokens": 500,
                },
                "tool_calls": [
                    {
                        "name": "write_file",
                        "arguments": {"Path": "tests/unit/tooling/test_agent_check.py"},
                    },
                    {
                        "name": "read_file",
                        "arguments": {"Path": "tests/unit/tooling/test_agent_check.py"},
                    },
                ],
            },
            {
                "turn": 5,
                "usage": {
                    "fresh_input_tokens": 3000,
                    "cached_input_tokens": 247000,
                    "output_tokens": 400,
                },
                "tool_calls": [
                    {
                        "name": "run_command",
                        "arguments": {
                            "CommandLine": ".venv/bin/python scripts/agent_check.py full"
                        },
                    },
                ],
            },
            {
                "turn": 6,
                "usage": {
                    "fresh_input_tokens": 2000,
                    "cached_input_tokens": 248000,
                    "output_tokens": 300,
                },
                "tool_calls": [
                    {"name": "manage_task", "arguments": {"Action": "status", "TaskId": "t1"}},
                ],
            },
            {
                "turn": 7,
                "usage": {
                    "fresh_input_tokens": 1000,
                    "cached_input_tokens": 249000,
                    "output_tokens": 200,
                },
                "tool_calls": [],
            },
        ],
    )
    # Unrelated conversation should be filtered out by --story 32-1
    _write_jsonl(
        tdir / "31-5-other" / "transcript.jsonl",
        [
            {
                "turn": 1,
                "usage": {"fresh_input_tokens": 100, "cached_input_tokens": 0, "output_tokens": 10},
                "tool_calls": [],
            }
        ],
    )

    monkeypatch.setenv("ORCIA_TRANSCRIPTS_DIR", str(tdir))
    rc_json = report_main(["--story", "32-1", "--format", "json"])
    assert rc_json == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["conversations_matched"] == 1
    assert payload["turns"] == 7
    assert payload["fresh_input_tokens"] == 15000 + 10000 + 5000 + 4000 + 3000 + 2000 + 1000
    assert (
        payload["cached_input_tokens"]
        == 235000 + 240000 + 245000 + 246000 + 247000 + 248000 + 249000
    )
    assert payload["output_tokens"] == 4000
    assert payload["total_read_file_calls"] == 6
    # Only the 2nd full read of main.py is a duplicate (disjoint ranges on router.py are not)
    assert payload["duplicate_read_file_calls"] == 1
    assert payload["duplicate_read_rate"] == pytest.approx(1 / 6, abs=1e-4)
    assert payload["generated_full_read_count"] == 1

    acts = payload["activity_breakdown"]
    assert acts["read_src"]["turns"] == 2
    assert acts["write_src"]["turns"] == 1
    assert acts["write_test"]["turns"] == 1
    assert acts["run_test_or_check"]["turns"] == 1
    assert acts["poll_task"]["turns"] == 1
    assert acts["no_tool_turn"]["turns"] == 1

    # Markdown output + --conv filter
    rc_md = report_main(["--conv", "32-1-coder-conv", "--format", "markdown"])
    assert rc_md == 0
    md_out = capsys.readouterr().out
    assert "Token Telemetry Report" in md_out
    assert "duplicate_read_rate" in md_out or "Duplicate" in md_out
    assert "run_test_or_check" in md_out


def test_token_report_antigravity_planner_response_cache_read_and_multi_conv(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tdir = tmp_path / "brain"
    _write_jsonl(
        tdir / "aaaa1111-conv" / ".system_generated" / "logs" / "transcript_full.jsonl",
        [
            {"type": "SYSTEM_MESSAGE", "content": "brief"},
            {
                "type": "PLANNER_RESPONSE",
                "input_tokens": 20000,
                "cache_read_tokens": 230000,
                "output_tokens": 900,
                "tool_calls": "[{'name': 'run_command', 'args': {'CommandLine': 'pytest -q'}}]",
            },
            {"type": "GENERIC", "content": "tool result"},
        ],
    )
    # Chunk shard inside chunks/ must be ignored
    _write_jsonl(
        tdir / "aaaa1111-conv" / ".system_generated" / "logs" / "chunks" / "001.jsonl",
        [{"type": "PLANNER_RESPONSE", "input_tokens": 999999, "cache_read_tokens": 0}],
    )
    _write_jsonl(
        tdir / "bbbb2222-conv" / ".system_generated" / "logs" / "transcript.jsonl",
        [
            {
                "type": "PLANNER_RESPONSE",
                "input_tokens": 5000,
                "cache_read_tokens": 95000,
                "output_tokens": 300,
                "tool_calls": [{"name": "read_file", "args": {"Path": "apps/api/src/a.py"}}],
            }
        ],
    )
    rc = report_main(
        [
            "--transcripts-dir",
            str(tdir),
            "--conv",
            "aaaa1111",
            "--conv",
            "bbbb2222",
            "--format",
            "json",
        ]
    )
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["conversations_matched"] == 2
    assert data["turns"] == 2
    assert data["fresh_input_tokens"] == 25000
    assert data["cached_input_tokens"] == 325000
    assert data["total_input_tokens"] == 350000
    assert data["avg_context_per_turn"] == 175000
    assert data["output_tokens"] == 1200
    assert data["activity_breakdown"]["run_test_or_check"]["turns"] == 1
    assert data["activity_breakdown"]["read_src"]["turns"] == 1
