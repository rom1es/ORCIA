#!/usr/bin/env python3
"""Stage 1 hygiene gate for always-on rule budgets, `@[...]` includes, and Rule ID uniqueness."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

MAX_RULE_FILE_BYTES = 20_480  # 20 KiB safety margin strictly below 24,000 B Antigravity cap
HARD_TRUNCATION_BYTES = 24_000
MAX_AGENTS_CORE_BYTES = 12_288  # 12 KiB canonical AGENTS.md target

INCLUDE_RE = re.compile(r"@\[[^\]]*\]\(([^)]+)\)")
RULE_ID_RE = re.compile(r"\[R-[A-Z0-9]+-\d{2,3}\]")
TRUNCATED_MARKER_RE = re.compile(r"<truncated\b", re.IGNORECASE)


class RuleLintError(ValueError):
    """Raised when an `@[label](path)` rule include is invalid or cyclic."""


def _resolve_include_target(raw_target: str, current_file: Path, repo_root: Path) -> Path:
    cleaned = raw_target.strip()
    if cleaned.startswith("file://"):
        cleaned = cleaned[7:]
    candidate = Path(cleaned)
    if candidate.is_absolute():
        return candidate.resolve()
    rel_to_file = (current_file.parent / candidate).resolve()
    if rel_to_file.is_file():
        return rel_to_file
    return (repo_root / candidate).resolve()


def expand_rule_includes(file_path: Path, repo_root: Path, *, seen: set[Path] | None = None) -> str:
    """Recursively expand `@[label](path)` directives with cycle detection."""
    resolved = file_path.resolve()
    active = set() if seen is None else set(seen)
    if resolved in active:
        raise RuleLintError(f"Circular rule include detected at {resolved}")
    active.add(resolved)

    text = resolved.read_text(encoding="utf-8")

    def _replace(match: re.Match[str]) -> str:
        target = _resolve_include_target(match.group(1), resolved, repo_root)
        if not target.is_file():
            raise RuleLintError(
                f"Missing rule include target '{match.group(1)}' referenced by {resolved}"
            )
        return expand_rule_includes(target, repo_root, seen=active)

    return INCLUDE_RE.sub(_replace, text)


def discover_always_on_rule_files(repo_root: Path) -> list[Path]:
    """Return all always-on rule files (`AGENTS.md`, optional `GEMINI.md`, `.agents/rules/*.md`)."""
    files: list[Path] = []
    agents_md = repo_root / "AGENTS.md"
    if agents_md.is_file():
        files.append(agents_md)
    gemini_md = repo_root / "GEMINI.md"
    if gemini_md.is_file() or gemini_md.is_symlink():
        files.append(gemini_md)
    rules_dir = repo_root / ".agents" / "rules"
    if rules_dir.is_dir():
        files.extend(sorted(p for p in rules_dir.glob("*.md") if p.is_file()))
    return files


def discover_playbook_files(repo_root: Path) -> list[Path]:
    """Return all on-demand role playbooks under `docs/agent-playbooks/*.md`."""
    playbooks_dir = repo_root / "docs" / "agent-playbooks"
    if not playbooks_dir.is_dir():
        return []
    return sorted(p for p in playbooks_dir.glob("*.md") if p.is_file())


def extract_rule_ids(text: str) -> list[str]:
    """Extract all `[R-<GROUP>-<NN>]` rule identifiers from Markdown text."""
    return RULE_ID_RE.findall(text)


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def lint_agent_rules(repo_root: Path) -> list[str]:
    """Validate rule file byte caps, zero truncation markers, and global Rule ID uniqueness."""
    errors: list[str] = []
    agents_md = repo_root / "AGENTS.md"
    if not agents_md.is_file():
        return ["Missing canonical AGENTS.md at repository root."]

    always_on = discover_always_on_rule_files(repo_root)
    for rule_file in always_on:
        rel_name = _rel(rule_file, repo_root)
        try:
            expanded = expand_rule_includes(rule_file, repo_root)
        except RuleLintError as exc:
            errors.append(f"[{rel_name}] {exc}")
            continue

        expanded_bytes = len(expanded.encode("utf-8"))
        if expanded_bytes >= HARD_TRUNCATION_BYTES or expanded_bytes > MAX_RULE_FILE_BYTES:
            errors.append(
                f"[{rel_name}] expanded size {expanded_bytes} B exceeds "
                f"{MAX_RULE_FILE_BYTES:,} B margin (< {HARD_TRUNCATION_BYTES:,} B cap)"
            )
        if rule_file == agents_md and expanded_bytes > MAX_AGENTS_CORE_BYTES:
            errors.append(
                f"[AGENTS.md] expanded size {expanded_bytes} B exceeds "
                f"{MAX_AGENTS_CORE_BYTES:,} B (12 KB) canonical core budget"
            )
        if TRUNCATED_MARKER_RE.search(expanded):
            errors.append(f"[{rel_name}] contains '<truncated' marker (truncation risk)")

    # Global Rule ID uniqueness across always-on files (deduped by resolved path) + role playbooks
    seen_ids: dict[str, str] = {}
    scanned_paths: set[Path] = set()
    for path in [*always_on, *discover_playbook_files(repo_root)]:
        resolved = path.resolve()
        if resolved in scanned_paths:
            continue
        scanned_paths.add(resolved)
        rel_name = _rel(path, repo_root)
        text = path.read_text(encoding="utf-8")
        for rid in extract_rule_ids(text):
            if rid in seen_ids:
                errors.append(
                    f"Duplicate Rule ID {rid}: defined in both '{seen_ids[rid]}' and '{rel_name}'"
                )
            else:
                seen_ids[rid] = rel_name

    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint returning 0 on clean rules and 1 on any budget/ID violation."""
    parser = argparse.ArgumentParser(description="Validate ORCIA always-on rules and playbooks.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root directory.",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors = lint_agent_rules(root)
    if errors:
        for err in errors:
            print(f"FAIL [rules-lint]: {err}")
        return 1
    agents_bytes = len((root / "AGENTS.md").read_bytes())
    print(f"PASS [rules-lint]: AGENTS.md={agents_bytes} B (<= {MAX_AGENTS_CORE_BYTES} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
