"""Manifest (`apm.yml` / `pack.yaml`) and `apm.lock.yaml` parser/verifier (`Story 31.1`)."""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import ValidationError

from orcia_core.packs._internal._apm_security_guards import (
    normalize_and_validate_archive_path,
    safe_load_yaml_strict,
)
from orcia_core.packs.errors import PackInvalidArchiveError
from orcia_core.packs.models import (
    PackBundleKind,
    PackBundleStatus,
    PackLockFileEntry,
    PackLockSpec,
    PackManifestV2,
    PackQuickActionSpec,
    PackScopeType,
    PackSlotSpec,
    PackSourceOrigin,
)


def compute_archive_sha256(data: bytes) -> str:
    """Return canonical lowercase hex SHA-256 of archive bytes."""
    return hashlib.sha256(data).hexdigest()


def build_lockfile_dict(files: dict[str, bytes]) -> dict[str, Any]:
    """Build deterministic `apm.lock.yaml` payload from normalized relative pack files."""
    entries: dict[str, dict[str, Any]] = {}
    digest_acc = hashlib.sha256()
    for rel_path in sorted(files.keys()):
        if rel_path == "apm.lock.yaml":
            continue
        blob = files[rel_path]
        file_sha = hashlib.sha256(blob).hexdigest()
        entries[rel_path] = {"sha256": file_sha, "byte_size": len(blob)}
        digest_acc.update(rel_path.encode("utf-8"))
        digest_acc.update(b":")
        digest_acc.update(file_sha.encode("ascii"))
        digest_acc.update(b"\n")
    return {
        "lockfile_version": "1",
        "bundle_sha256": digest_acc.hexdigest(),
        "files": entries,
    }


def strip_single_root_folder(files: dict[str, bytes]) -> dict[str, bytes]:
    """Strip single `<pack-slug>/` wrapper folder when `apm.yml` / `pack.yaml` is nested."""
    if not files or "apm.yml" in files or "pack.yaml" in files:
        return files
    first_segments = {path.split("/", 1)[0] for path in files if "/" in path}
    if len(first_segments) == 1 and all("/" in path for path in files):
        prefix = next(iter(first_segments)) + "/"
        stripped = {path[len(prefix) :]: blob for path, blob in files.items()}
        if "apm.yml" in stripped or "pack.yaml" in stripped:
            return stripped
    return files


def load_yaml_safe(raw_bytes: bytes, *, source_path: str) -> Any:
    """Decode UTF-8 YAML strictly, rejecting duplicate keys, alias bombs, and hook keys."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PackInvalidArchiveError(
            detail_override=f"Invalid UTF-8 in {source_path!r}: {exc}"
        ) from exc
    return safe_load_yaml_strict(text, source_path=source_path)


def _parse_apm_manifest(
    raw_bytes: bytes, *, source_origin: PackSourceOrigin
) -> tuple[PackManifestV2, str]:
    raw_text = raw_bytes.decode("utf-8", errors="strict")
    raw = load_yaml_safe(raw_bytes, source_path="apm.yml")
    if not isinstance(raw, dict):
        raise PackInvalidArchiveError(detail_override="apm.yml must be a YAML mapping.")
    x_orcia_raw = raw.get("x-orcia")
    x_orcia: dict[str, Any] = dict(x_orcia_raw) if isinstance(x_orcia_raw, dict) else {}
    slug = str(x_orcia.get("slug") or raw.get("slug") or raw.get("name") or "").strip()
    name = str(x_orcia.get("title_en") or x_orcia.get("title_fr") or raw.get("name") or slug)
    version = str(raw.get("version") or "").strip()
    if not slug or not version:
        raise PackInvalidArchiveError(detail_override="apm.yml requires name/slug and version.")
    default_scope = "GLOBAL" if source_origin == PackSourceOrigin.LOCAL_SYSTEM else "WORKSPACE"
    slots_raw = x_orcia.get("connector_slots") or []
    qa_raw = x_orcia.get("quick_actions") or []
    maintainers_raw = raw.get("maintainers") or []
    mcp_raw = raw.get("mcp")
    if not isinstance(slots_raw, list) or not isinstance(qa_raw, list):
        raise PackInvalidArchiveError(
            detail_override="connector_slots and quick_actions in x-orcia must be lists."
        )
    try:
        manifest = PackManifestV2(
            id=str(x_orcia.get("id") or f"orcia-pack-{slug}"),
            slug=slug,
            name=name,
            version=version,
            description=str(raw.get("description") or ""),
            author=str(raw.get("author") or ""),
            maintainers=(
                [str(m) for m in maintainers_raw] if isinstance(maintainers_raw, list) else []
            ),
            license=str(raw.get("license") or ""),
            rbac_namespace=str(x_orcia.get("rbac_namespace") or slug),
            bundle_kind=PackBundleKind(str(x_orcia.get("bundle_kind") or "IMPORTED")),
            scope_type=PackScopeType(str(x_orcia.get("scope_type") or default_scope)),
            scope_id=str(x_orcia.get("scope_id") or "global"),
            status=PackBundleStatus(str(x_orcia.get("status") or "PUBLISHED")),
            source_origin=source_origin,
            declared_slots=[PackSlotSpec.model_validate(s) for s in slots_raw],
            mcp_declarations=dict(mcp_raw) if isinstance(mcp_raw, dict) else {},
            quick_actions=[PackQuickActionSpec.model_validate(q) for q in qa_raw],
            x_orcia=x_orcia,
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise PackInvalidArchiveError(
            detail_override=f"Invalid apm.yml manifest fields: {exc}"
        ) from exc
    return manifest, raw_text


def _parse_legacy_pack_manifest(
    raw_bytes: bytes, *, source_origin: PackSourceOrigin
) -> tuple[PackManifestV2, str]:
    raw_text = raw_bytes.decode("utf-8", errors="strict")
    raw = load_yaml_safe(raw_bytes, source_path="pack.yaml")
    if not isinstance(raw, dict):
        raise PackInvalidArchiveError(detail_override="pack.yaml must be a YAML mapping.")
    slug = str(raw.get("slug") or "").strip()
    name = str(raw.get("name") or "").strip()
    version = str(raw.get("version") or "").strip()
    if not slug or not name or not version:
        raise PackInvalidArchiveError(
            detail_override="pack.yaml requires non-empty slug, name, and version."
        )
    slots: list[PackSlotSpec] = []
    for idx, conn in enumerate(raw.get("required_connectors") or []):
        if isinstance(conn, dict):
            ctype = str(conn.get("connector_type") or "mcp")
            scheme = ctype.split(":", 1)[0] if ":" in ctype else ctype
            slots.append(
                PackSlotSpec(
                    slot_key=f"legacy_{scheme}_{idx}",
                    scheme=scheme[:32] or "mcp",
                    connector_kind=ctype,
                    required_access=[str(s) for s in (conn.get("required_scopes") or ["read"])],
                    required=True,
                    description_fr=str(conn.get("used_for") or ""),
                )
            )
    qa_raw = raw.get("quick_actions") or []
    try:
        manifest = PackManifestV2(
            id=str(raw.get("id") or f"orcia-pack-{slug}"),
            slug=slug,
            name=name,
            version=version,
            description=str(raw.get("description") or ""),
            rbac_namespace=str(raw.get("rbac_namespace") or slug),
            bundle_kind=PackBundleKind.SYSTEM,
            scope_type=PackScopeType.GLOBAL,
            scope_id="global",
            status=PackBundleStatus.PUBLISHED,
            source_origin=source_origin,
            declared_slots=slots,
            quick_actions=[PackQuickActionSpec.model_validate(q) for q in qa_raw],
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise PackInvalidArchiveError(
            detail_override=f"Invalid pack.yaml manifest fields: {exc}"
        ) from exc
    return manifest, raw_text


def parse_manifest(
    files: dict[str, bytes], *, source_origin: PackSourceOrigin
) -> tuple[PackManifestV2, str]:
    """Parse `apm.yml` (preferred) or legacy `pack.yaml` into `PackManifestV2`."""
    if "apm.yml" in files:
        return _parse_apm_manifest(files["apm.yml"], source_origin=source_origin)
    if "pack.yaml" in files:
        return _parse_legacy_pack_manifest(files["pack.yaml"], source_origin=source_origin)
    raise PackInvalidArchiveError(
        detail_override="Pack archive must contain apm.yml or legacy pack.yaml at root."
    )


def verify_lockfile(files: dict[str, bytes]) -> PackLockSpec | None:
    """Verify `apm.lock.yaml` checksums, byte sizes, bundle digest, and reject unlisted files."""
    if "apm.lock.yaml" not in files:
        return None
    raw = load_yaml_safe(files["apm.lock.yaml"], source_path="apm.lock.yaml")
    if not isinstance(raw, dict):
        raise PackInvalidArchiveError(detail_override="apm.lock.yaml must be a YAML mapping.")
    raw_files = raw.get("files", {})
    if raw_files is None:
        raw_files = {}
    if not isinstance(raw_files, dict):
        raise PackInvalidArchiveError(detail_override="apm.lock.yaml 'files' must be a mapping.")
    try:
        lock_spec = PackLockSpec.model_validate(
            {
                "lockfile_version": str(raw.get("lockfile_version") or "1"),
                "bundle_sha256": str(raw.get("bundle_sha256") or ""),
                "files": {
                    str(path): PackLockFileEntry(
                        path=str(path),
                        sha256=str(meta.get("sha256") if isinstance(meta, dict) else meta),
                        byte_size=(
                            int(meta.get("byte_size", -1)) if isinstance(meta, dict) else -1
                        ),
                    )
                    for path, meta in raw_files.items()
                },
            }
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise PackInvalidArchiveError(
            detail_override=f"Malformed apm.lock.yaml schema: {exc}"
        ) from exc

    locked_paths: set[str] = set()
    for rel_path, entry in lock_spec.files.items():
        norm_path = normalize_and_validate_archive_path(rel_path)
        locked_paths.add(norm_path)
        blob = files.get(norm_path)
        if blob is None:
            raise PackInvalidArchiveError(
                detail_override=f"apm.lock.yaml references missing file: {norm_path!r}"
            )
        if entry.byte_size != len(blob):
            raise PackInvalidArchiveError(
                detail_override=f"Byte size mismatch in apm.lock.yaml for {norm_path!r}."
            )
        actual = hashlib.sha256(blob).hexdigest()
        if actual != entry.sha256.lower():
            raise PackInvalidArchiveError(
                detail_override=f"SHA-256 mismatch in apm.lock.yaml for {norm_path!r}."
            )

    extra_files = sorted(set(files.keys()) - {"apm.lock.yaml"} - locked_paths)
    if extra_files:
        raise PackInvalidArchiveError(
            detail_override=(
                f"Archive contains unlisted file(s) absent from apm.lock.yaml: {extra_files}"
            )
        )
    expected_bundle_sha = str(build_lockfile_dict(files)["bundle_sha256"])
    if not lock_spec.bundle_sha256 or lock_spec.bundle_sha256.lower() != expected_bundle_sha:
        raise PackInvalidArchiveError(
            detail_override="apm.lock.yaml bundle_sha256 mismatch against archive contents."
        )
    return lock_spec


__all__ = [
    "build_lockfile_dict",
    "compute_archive_sha256",
    "load_yaml_safe",
    "parse_manifest",
    "strip_single_root_folder",
    "verify_lockfile",
]
