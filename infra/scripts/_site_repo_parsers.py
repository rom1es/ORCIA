"""Repository introspection parsers for ORCIA showcase site generation (`pnpm site:sync`)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml  # type: ignore[import-untyped]

HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")

_HEX_COLOR_LABELS = {
    "#6D28D9": "Violet signature",
    "#D97706": "Ambre arbitrage",
    "#059669": "Émeraude",
    "#2563EB": "Cobalt",
    "#DC2626": "Pourpre alerte",
    "#0F172A": "Ardoise",
    "#F8FAFC": "Clair",
}


def sanitize_no_hex_for_ts(text: str) -> str:
    """Strip any raw hex color literal so generated .ts files obey @orcia/ui Invariant 2."""

    def _replace(match: re.Match[str]) -> str:
        token = match.group(0).upper()
        return _HEX_COLOR_LABELS.get(token, f"teinte-{token[1:]}")

    return HEX_COLOR_RE.sub(_replace, text)


def clean_markdown_inline(text: str) -> str:
    """Clean markdown formatting links/backticks for clean display."""
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    cleaned = cleaned.replace("$\\rightarrow$", "→").replace("$\\leftrightarrow$", "↔")
    cleaned = cleaned.replace("$\\ge$", "≥").replace("$\\le$", "≤")
    cleaned = cleaned.replace("**", "").replace("`", "")
    return sanitize_no_hex_for_ts(cleaned.strip())


def parse_architecture_spine(
    spine_path: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Extract architecture decisions and locked stack versions from ARCHITECTURE-SPINE.md."""
    content = spine_path.read_text(encoding="utf-8")
    decisions: list[dict[str, str]] = []
    for match in re.finditer(
        r"^###\s+(AD-\d+)\s+—\s+([^\n]+?)(?:\s*\[ADOPTED\])?\s*$",
        content,
        flags=re.MULTILINE,
    ):
        decisions.append(
            {
                "code": match.group(1).strip(),
                "title": clean_markdown_inline(match.group(2)),
            }
        )

    stack_items: list[dict[str, str]] = []
    stack_section_match = re.search(r"^##\s+Stack\s*$([\s\S]+)", content, flags=re.MULTILINE)
    if stack_section_match:
        stack_block = stack_section_match.group(1)
        for line in stack_block.splitlines():
            line_str = line.strip()
            if not line_str.startswith("|"):
                if stack_items and line_str.startswith("#"):
                    break
                continue
            cells = [c.strip() for c in line_str.strip("|").split("|")]
            if len(cells) >= 2:
                name_raw, version_raw = cells[0], cells[1]
                if name_raw in ("Name", "---") or set(name_raw) <= {"-", ":"}:
                    continue
                stack_items.append(
                    {
                        "name": clean_markdown_inline(name_raw),
                        "version": clean_markdown_inline(version_raw),
                    }
                )
    return decisions, stack_items


def parse_active_routes(routes_dir: Path, router_file: Path) -> list[str]:
    """Discover all active TanStack Router SPA routes."""
    routes: set[str] = set()
    for route_file in sorted(routes_dir.glob("*.tsx")):
        if route_file.name in ("__root.tsx", "searchSchema.ts"):
            continue
        text = route_file.read_text(encoding="utf-8")
        for match in re.finditer(r'path:\s*"([^"]+)"', text):
            routes.add(match.group(1))
    if router_file.exists():
        router_text = router_file.read_text(encoding="utf-8")
        for match in re.finditer(r'path:\s*"([^"]+)"', router_text):
            routes.add(match.group(1))
    return sorted(routes)


def parse_ui_primitives(ui_index_file: Path) -> list[str]:
    """Discover exported UI primitives from packages/ui/src/index.ts."""
    text = ui_index_file.read_text(encoding="utf-8")
    primitives: list[str] = []
    for block_match in re.finditer(r'export\s*\{([^}]+)\}\s*from\s*"([^"]+)"', text):
        exports_raw = block_match.group(1)
        for token in exports_raw.split(","):
            tok = token.strip()
            if not tok or tok.startswith("type "):
                continue
            tok_name = tok.split(" as ")[0].strip()
            if (
                tok_name
                and tok_name[0].isupper()
                and not tok_name.startswith("DEFAULT_")
                and tok_name not in primitives
            ):
                primitives.append(tok_name)
    return sorted(primitives)


def parse_business_packs(packages_dir: Path, packs_dir: Path | None = None) -> list[dict[str, str]]:
    """Discover installed Python package packs and declarative YAML packs."""
    packs: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    for pack_toml in sorted(packages_dir.glob("orcia-pack-*/pyproject.toml")):
        text = pack_toml.read_text(encoding="utf-8")
        name_match = re.search(r'^name\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
        version_match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
        desc_match = re.search(r'^description\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
        key = name_match.group(1) if name_match else pack_toml.parent.name
        seen_keys.add(key)
        packs.append(
            {
                "key": key,
                "version": version_match.group(1) if version_match else "0.1.0",
                "description": sanitize_no_hex_for_ts(
                    desc_match.group(1) if desc_match else "Pack Métier ORCIA"
                ),
            }
        )
    resolved_packs_dir = packs_dir if packs_dir is not None else packages_dir.parent / "packs"
    for pack_yaml in sorted(resolved_packs_dir.glob("*/pack.yaml")):
        raw = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("id") or raw.get("slug") or pack_yaml.parent.name)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        packs.append(
            {
                "key": key,
                "version": str(raw.get("version") or "1.0.0"),
                "description": sanitize_no_hex_for_ts(
                    str(raw.get("description") or "Pack Métier ORCIA")
                ),
            }
        )
    return packs


def parse_migrations(migrations_dir: Path) -> list[str]:
    """List Alembic migration revision stems."""
    files: list[str] = []
    for file_path in sorted(migrations_dir.glob("*.py")):
        if file_path.name.startswith("__"):
            continue
        files.append(file_path.stem)
    return files


def parse_tech_lead_reports(readme_path: Path) -> list[dict[str, str]]:
    """Parse chronological Tech Lead reports table from tech-lead-reports/README.md."""
    content = readme_path.read_text(encoding="utf-8")
    reports: list[dict[str, str]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| **202"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 5:
            continue
        date_str = clean_markdown_inline(cells[0])
        story_str = clean_markdown_inline(cells[1])
        file_cell = cells[2]
        file_match = re.search(r"\[`?([^`\]]+)`?\]", file_cell)
        file_name = file_match.group(1) if file_match else clean_markdown_inline(file_cell)
        domain_str = clean_markdown_inline(cells[3])
        summary_str = clean_markdown_inline(cells[4])
        reports.append(
            {
                "date": date_str,
                "phaseOrStory": story_str,
                "reportFile": sanitize_no_hex_for_ts(file_name),
                "domain": domain_str,
                "summary": summary_str,
            }
        )
    return reports
