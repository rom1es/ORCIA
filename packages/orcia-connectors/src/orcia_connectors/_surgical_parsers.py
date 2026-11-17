"""Security validators, badge resolvers & structural outline parsers for `surgical.py`."""

from __future__ import annotations

import ast
import ipaddress
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from orcia_core.kernel.errors import PolicyDeniedError, ValidationDomainError
from orcia_core.ports.surgical_explorer_port import (
    SurgicalFileBadgeCode,
    SurgicalOutlineNode,
)

_SSRF_BLOCKED_HOSTS: frozenset[str] = frozenset(
    {
        "169.254.169.254",
        "100.100.100.200",
        "metadata.google.internal",
        "metadata.goog",
        "metadata.azure.com",
        "instance-data",
        "localhost",
    }
)
_NETWORK_SCHEMES: frozenset[str] = frozenset(
    {"http", "https", "ftp", "ftps", "gopher", "dict", "ws", "wss", "ldap", "ssh"}
)
_ALLOWED_VIRTUAL_SCHEMES: frozenset[str] = frozenset(
    {"pack", "catalog", "orcia", "git", "confluence", "jira"}
)

_MD_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
_YAML_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*:")
_JSON_KEY_RE = re.compile(r'^"([^"\\]{1,128})"\s*:')
_TS_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?"
    r"(class|interface|type|function|const)\s+([A-Za-z_$][A-Za-z0-9_$]*)"
)
_PY_FALLBACK_RE = re.compile(r"^(\s*)(?:async\s+)?(class|def)\s+([A-Za-z_][A-Za-z0-9_]*)")


def strip_uri_fragment_and_query(uri: str) -> str:
    """Strip `#Lstart-end` fragment and `?query` from a resource URI."""
    base = uri.split("#", 1)[0].split("?", 1)[0].strip()
    return base


def extract_display_filename(uri: str) -> str:
    """Extract clean human-readable filename from a relative path or virtual URI."""
    cleaned = strip_uri_fragment_and_query(uri)
    if "@" in cleaned and "://" in cleaned:
        cleaned = cleaned.split("@", 1)[0]
    if "://" in cleaned:
        tail = cleaned.split("://", 1)[1].strip("/")
        name = Path(tail).name if tail else cleaned
        return name or cleaned
    name = Path(cleaned).name
    return name or cleaned or "resource"


def resolve_file_badge_code(filename_or_uri: str) -> SurgicalFileBadgeCode:
    """Map resource extension to normalized badge (`M↓`, `Y`, `TS`, `PY`, `JSON`, `SQL`, `DOC`)."""
    name = extract_display_filename(filename_or_uri).lower()
    suffix = Path(name).suffix
    if suffix in (".md", ".mdx", ".markdown"):
        return "M↓"
    if suffix in (".yaml", ".yml"):
        return "Y"
    if suffix in (".ts", ".tsx"):
        return "TS"
    if suffix in (".py", ".pyi"):
        return "PY"
    if suffix in (".json", ".jsonl"):
        return "JSON"
    if suffix == ".sql":
        return "SQL"
    return "DOC"


def _is_ssrf_host(host: str) -> bool:
    norm = host.strip().lower().rstrip(".").strip("[]")
    if not norm or norm in _SSRF_BLOCKED_HOSTS or norm.endswith(".google.internal"):
        return True
    try:
        ip = ipaddress.ip_address(norm)
        return (
            ip.is_link_local
            or ip.is_loopback
            or ip.is_unspecified
            or ip.is_multicast
            or norm.startswith("100.100.100.")
        )
    except ValueError:
        return False


def validate_surgical_uri_security(raw_uri: str, *, allow_empty: bool = False) -> str:
    """Enforce zero null-byte, zero `..` traversal, zero `file://`, and zero SSRF targets."""
    trimmed = raw_uri.strip()
    if not trimmed:
        if allow_empty:
            return ""
        raise ValidationDomainError(detail_override="Le paramètre `uri` ne peut pas être vide.")

    decoded = unquote(trimmed)
    if "\x00" in trimmed or "\x00" in decoded:
        raise ValidationDomainError(detail_override="Octet nul interdit dans l'URI.")

    if "://" in trimmed:
        parsed = urlparse(trimmed)
        scheme = (parsed.scheme or "").lower()
        if scheme == "file":
            raise ValidationDomainError(detail_override="Le schéma `file://` est interdit.")
        if scheme in _NETWORK_SCHEMES:
            host = parsed.hostname or ""
            if _is_ssrf_host(host):
                raise PolicyDeniedError(
                    detail_override=f"Cible SSRF bloquée par la gouvernance : `{host}`."
                )
            raise PolicyDeniedError(
                detail_override="Les URL réseau directes ne sont pas autorisées en exploration."
            )
        if scheme not in _ALLOWED_VIRTUAL_SCHEMES:
            raise ValidationDomainError(
                detail_override=f"Schéma d'URI non supporté : `{scheme}://`."
            )
        path_part = unquote(f"{parsed.netloc}/{parsed.path}")
    else:
        path_part = decoded

    normalized_segments = path_part.replace("\\", "/").split("/")
    if any(seg == ".." for seg in normalized_segments):
        raise ValidationDomainError(
            detail_override="Traversée de chemin `..` strictement interdite."
        )

    return strip_uri_fragment_and_query(trimmed)


def extract_outline_nodes(
    text: str, filename_or_uri: str, *, max_nodes: int = 200
) -> list[SurgicalOutlineNode]:
    """Extract structural headings, top/second-level keys, or code symbols with line numbers."""
    badge = resolve_file_badge_code(filename_or_uri)
    lines = text.splitlines()
    nodes: list[SurgicalOutlineNode] = []

    if badge == "M↓":
        in_fence = False
        for idx, raw_line in enumerate(lines, start=1):
            stripped = raw_line.lstrip()
            if stripped.startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = _MD_HEADING_RE.match(raw_line)
            if m:
                nodes.append(
                    SurgicalOutlineNode(
                        kind="heading",
                        title=m.group(2).strip(),
                        line_number=idx,
                        level=len(m.group(1)),
                    )
                )
    elif badge == "Y":
        for idx, raw_line in enumerate(lines, start=1):
            stripped = raw_line.lstrip(" ")
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue
            indent = len(raw_line) - len(stripped)
            if indent > 4:
                continue
            m = _YAML_KEY_RE.match(stripped)
            if m:
                nodes.append(
                    SurgicalOutlineNode(
                        kind="yaml_key",
                        title=m.group(1),
                        line_number=idx,
                        level=1 if indent == 0 else 2,
                    )
                )
    elif badge == "JSON":
        for idx, raw_line in enumerate(lines, start=1):
            stripped = raw_line.lstrip(" ")
            indent = len(raw_line) - len(stripped)
            if indent > 6:
                continue
            m = _JSON_KEY_RE.match(stripped)
            if m:
                nodes.append(
                    SurgicalOutlineNode(
                        kind="json_key",
                        title=m.group(1),
                        line_number=idx,
                        level=1 if indent <= 2 else 2,
                    )
                )
    elif badge == "PY":
        nodes.extend(_extract_python_outline(text, lines))
    elif badge == "TS":
        for idx, raw_line in enumerate(lines, start=1):
            m = _TS_SYMBOL_RE.match(raw_line)
            if m:
                nodes.append(
                    SurgicalOutlineNode(
                        kind=m.group(1),
                        title=m.group(2),
                        line_number=idx,
                        level=1,
                    )
                )

    return nodes[:max_nodes]


def _extract_python_outline(text: str, lines: list[str]) -> list[SurgicalOutlineNode]:
    nodes: list[SurgicalOutlineNode] = []
    try:
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                nodes.append(
                    SurgicalOutlineNode(
                        kind="class", title=node.name, line_number=node.lineno, level=1
                    )
                )
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nodes.append(
                            SurgicalOutlineNode(
                                kind="function",
                                title=child.name,
                                line_number=child.lineno,
                                level=2,
                            )
                        )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nodes.append(
                    SurgicalOutlineNode(
                        kind="function", title=node.name, line_number=node.lineno, level=1
                    )
                )
        return nodes
    except SyntaxError:
        for idx, raw_line in enumerate(lines, start=1):
            m = _PY_FALLBACK_RE.match(raw_line)
            if m:
                indent = len(m.group(1))
                kind = "class" if m.group(2) == "class" else "function"
                nodes.append(
                    SurgicalOutlineNode(
                        kind=kind,
                        title=m.group(3),
                        line_number=idx,
                        level=1 if indent == 0 else 2,
                    )
                )
        return nodes
