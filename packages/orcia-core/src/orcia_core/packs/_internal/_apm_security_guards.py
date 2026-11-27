"""Fail-closed archive, YAML, magic-byte, and Starlark AST security guards (`Story 31.1`)."""

from __future__ import annotations

import posixpath
import re
import stat
import zipfile
from typing import Any

import yaml  # type: ignore[import-untyped]

from orcia_core.gates import StarlarkSandboxError, validate_starlark_ast
from orcia_core.packs.errors import PackExecutableHookForbiddenError, PackInvalidArchiveError

MAX_ARCHIVE_FILES = 500
MAX_ARCHIVE_COMPRESSED_BYTES = 10 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
MAX_SINGLE_FILE_BYTES = 2 * 1024 * 1024
MAX_COMPRESSION_RATIO = 50
MAX_YAML_ALIASES = 64

FORBIDDEN_HOOK_DIRS: frozenset[str] = frozenset({"scripts", "hooks"})
FORBIDDEN_HOOK_YAML_KEYS: frozenset[str] = frozenset(
    {"hooks", "lifecycle_hooks", "pre_install", "post_install", "scripts", "shell", "exec"}
)
FORBIDDEN_EXECUTABLE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".py",
        ".pyw",
        ".pyc",
        ".pyo",
        ".sh",
        ".bash",
        ".zsh",
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".mts",
        ".ps1",
        ".bat",
        ".cmd",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".wasm",
        ".rb",
        ".pl",
        ".php",
    }
)
_EXECUTABLE_MAGIC_PREFIXES: tuple[bytes, ...] = (b"#!", b"\x7fELF", b"MZ\x90\x00", b"\x00asm")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


class _StrictYamlLoader(yaml.SafeLoader):  # type: ignore[misc]
    """YAML SafeLoader enforcing unique mapping keys."""


def _construct_unique_mapping(
    loader: _StrictYamlLoader, node: Any, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, val_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key {key!r}",
                    key_node.start_mark,
                )
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"unhashable key: {exc}",
                key_node.start_mark,
            ) from exc
        mapping[key] = loader.construct_object(val_node, deep=deep)
    return mapping


_StrictYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def safe_load_yaml_strict(raw_text: str, *, source_path: str) -> Any:
    """Parse YAML rejecting duplicate keys, alias bombs, and forbidden hook keys."""
    try:
        alias_count = sum(
            1
            for tok in yaml.scan(raw_text, Loader=_StrictYamlLoader)
            if isinstance(tok, yaml.AliasToken)
        )
        if alias_count > MAX_YAML_ALIASES:
            raise PackInvalidArchiveError(
                detail_override=f"YAML alias count exceeds limit in {source_path!r}."
            )
        parsed = yaml.load(raw_text, Loader=_StrictYamlLoader)  # noqa: S506
    except (yaml.YAMLError, ValueError, RecursionError) as exc:
        raise PackInvalidArchiveError(
            detail_override=f"Malformed or unsafe YAML in {source_path!r}: {exc}"
        ) from exc
    assert_no_forbidden_hook_yaml_keys(parsed, source_path=source_path)
    return parsed


def normalize_and_validate_archive_path(raw_path: str) -> str:
    """Validate an archive entry path against zip-slip traversal and normalize to POSIX."""
    if not raw_path or "\x00" in raw_path:
        raise PackInvalidArchiveError(detail_override="Empty or null-byte archive path rejected.")
    cleaned = raw_path.replace("\\", "/").strip()
    if cleaned.startswith("/") or _WINDOWS_DRIVE_RE.match(cleaned):
        raise PackInvalidArchiveError(
            detail_override=f"Absolute archive path is forbidden: {raw_path!r}"
        )
    parts = [part for part in cleaned.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise PackInvalidArchiveError(
            detail_override=f"Path traversal segment is forbidden: {raw_path!r}"
        )
    normalized = posixpath.normpath("/".join(parts))
    if normalized.startswith("../") or normalized in ("..", "."):
        raise PackInvalidArchiveError(
            detail_override=f"Normalized path traversal rejected: {raw_path!r}"
        )
    return normalized


def validate_zip_info_safe(info: zipfile.ZipInfo) -> str:
    """Validate a `ZipInfo` entry for symlinks, zip-slip, and size/ratio bomb limits."""
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise PackInvalidArchiveError(
            detail_override=f"Symbolic link entry is forbidden in archive: {info.filename!r}"
        )
    normalized = normalize_and_validate_archive_path(info.filename)
    if info.file_size > MAX_SINGLE_FILE_BYTES:
        raise PackInvalidArchiveError(
            detail_override=(
                f"Archive entry {normalized!r} exceeds {MAX_SINGLE_FILE_BYTES} bytes limit."
            )
        )
    if info.compress_size > 0 and (info.file_size / info.compress_size) > MAX_COMPRESSION_RATIO:
        raise PackInvalidArchiveError(
            detail_override=f"Archive entry {normalized!r} exceeds permitted compression ratio."
        )
    return normalized


def assert_no_executable_hooks_or_scripts(rel_path: str) -> None:
    """Fail-closed with `ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN` on hooks dirs or executable files."""
    parts = [p.lower() for p in rel_path.split("/") if p]
    if any(part in FORBIDDEN_HOOK_DIRS for part in parts[:-1]):
        raise PackExecutableHookForbiddenError(
            detail_override=f"Executable scripts/hooks directory is forbidden: {rel_path!r}"
        )
    filename = parts[-1] if parts else ""
    for suffix in FORBIDDEN_EXECUTABLE_SUFFIXES:
        if filename.endswith(suffix):
            raise PackExecutableHookForbiddenError(
                detail_override=(
                    f"Executable file extension {suffix!r} is forbidden in pack: {rel_path!r}"
                )
            )


def assert_no_executable_magic_bytes(blob: bytes, *, rel_path: str) -> None:
    """Reject shebang (`#!`) and binary executable headers (`ELF`, `PE`, `WASM`)."""
    head = blob[:16]
    stripped_head = blob[:64].lstrip()
    for prefix in _EXECUTABLE_MAGIC_PREFIXES:
        if head.startswith(prefix) or (prefix == b"#!" and stripped_head.startswith(b"#!")):
            raise PackExecutableHookForbiddenError(
                detail_override=(
                    f"Executable shebang or binary magic bytes forbidden in {rel_path!r}."
                )
            )


def assert_no_forbidden_hook_yaml_keys(data: Any, *, source_path: str) -> None:
    """Recursively reject YAML hook/script execution keys inside manifests or frontmatter."""
    if isinstance(data, dict):
        for key, value in data.items():
            key_norm = str(key).strip().lower()
            if key_norm in FORBIDDEN_HOOK_YAML_KEYS:
                raise PackExecutableHookForbiddenError(
                    detail_override=(
                        f"Forbidden executable hook key {key!r} found in {source_path!r}."
                    )
                )
            assert_no_forbidden_hook_yaml_keys(value, source_path=source_path)
    elif isinstance(data, list):
        for item in data:
            assert_no_forbidden_hook_yaml_keys(item, source_path=source_path)


def validate_starlark_mechanism_ast(source: str, *, mechanism_path: str) -> None:
    """Validate `.star` mechanism source using shared `orcia_core.gates` AST whitelist."""
    try:
        validate_starlark_ast(source, filename=mechanism_path)
    except StarlarkSandboxError as exc:
        raise PackInvalidArchiveError(
            detail_override=f"Unsafe Starlark mechanism {mechanism_path!r}: {exc}"
        ) from exc


__all__ = [
    "FORBIDDEN_EXECUTABLE_SUFFIXES",
    "FORBIDDEN_HOOK_DIRS",
    "FORBIDDEN_HOOK_YAML_KEYS",
    "MAX_ARCHIVE_COMPRESSED_BYTES",
    "MAX_ARCHIVE_FILES",
    "MAX_COMPRESSION_RATIO",
    "MAX_SINGLE_FILE_BYTES",
    "MAX_UNCOMPRESSED_BYTES",
    "assert_no_executable_hooks_or_scripts",
    "assert_no_executable_magic_bytes",
    "assert_no_forbidden_hook_yaml_keys",
    "normalize_and_validate_archive_path",
    "safe_load_yaml_strict",
    "validate_starlark_mechanism_ast",
    "validate_zip_info_safe",
]
