"""Parser & Formatters for Qualified Pack & Workspace Entity Refs (`Story 31.3`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dbos`, `redis`, `litellm`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from orcia_kernel.errors import ValidationDomainError

_SLUG_SEGMENT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True, slots=True)
class QualifiedEntityRef:
    """Normalized structural representation of a pack or workspace entity reference."""

    raw_ref: str
    entity_slug: str
    pack_slug: str | None = None
    kind: str | None = None
    version_ref: str | None = None
    is_qualified: bool = False
    is_workspace_scope: bool = False

    @property
    def canonical_id(self) -> str:
        """Return `{pack_slug}:{entity_slug}` when qualified, else `{entity_slug}`."""
        return f"{self.pack_slug}:{self.entity_slug}" if self.pack_slug else self.entity_slug

    @property
    def mention_handle(self) -> str:
        """Return canonical `@` mention handle (`@<pack>/<slug>` or `@<slug>`)."""
        return format_agent_mention(
            self.entity_slug, pack_slug=self.pack_slug, workspace_scoped=self.is_workspace_scope
        )

    @property
    def command_handle(self) -> str:
        """Return canonical `/` skill command (`/<pack>/<slug>` or `/<slug>`)."""
        return format_skill_command(
            self.entity_slug, pack_slug=self.pack_slug, workspace_scoped=self.is_workspace_scope
        )


def _normalize_segment(raw: str, *, field_name: str, raw_ref: str) -> str:
    cleaned = raw.strip().lower()
    if not cleaned or not _SLUG_SEGMENT_RE.match(cleaned):
        raise ValidationDomainError(
            detail_override=f"Invalid {field_name} in entity reference {raw_ref!r}."
        )
    return cleaned


def _split_version_suffix(segment: str) -> tuple[str, str | None]:
    if "@" in segment and not segment.startswith("@"):
        head, ver = segment.rsplit("@", 1)
        if head and ver:
            return head, ver.strip()
    if ":" in segment:
        head, ver = segment.rsplit(":", 1)
        if head and ver:
            return head, ver.strip()
    return segment, None


def _parse_uri_entity_ref(cleaned: str, *, default_kind: str | None) -> QualifiedEntityRef:
    normalized = (
        f"orcia://packs/{cleaned[7:].lstrip('/')}"
        if cleaned.lower().startswith("pack://")
        else cleaned
    )
    if "://" not in normalized:
        raise ValidationDomainError(detail_override=f"Invalid entity URI {cleaned!r}.")
    scheme, remainder = normalized.split("://", 1)
    if scheme.lower() != "orcia":
        raise ValidationDomainError(detail_override=f"Unsupported entity URI scheme {scheme!r}.")
    parts = [p for p in remainder.strip("/").split("/") if p]
    if len(parts) >= 4 and parts[0].lower() == "packs":
        pack_slug = _normalize_segment(parts[1], field_name="pack_slug", raw_ref=cleaned)
        kind = parts[2].strip().lower() or default_kind
        raw_slug, version_ref = _split_version_suffix(parts[3])
        entity_slug = _normalize_segment(raw_slug, field_name="entity_slug", raw_ref=cleaned)
        return QualifiedEntityRef(
            raw_ref=cleaned,
            entity_slug=entity_slug,
            pack_slug=pack_slug,
            kind=kind,
            version_ref=version_ref,
            is_qualified=True,
            is_workspace_scope=(pack_slug == "workspace"),
        )
    if len(parts) >= 4 and parts[0].lower() == "workspaces":
        kind = parts[2].strip().lower() or default_kind
        raw_slug, version_ref = _split_version_suffix(parts[3])
        entity_slug = _normalize_segment(raw_slug, field_name="entity_slug", raw_ref=cleaned)
        return QualifiedEntityRef(
            raw_ref=cleaned,
            entity_slug=entity_slug,
            pack_slug="workspace",
            kind=kind,
            version_ref=version_ref,
            is_qualified=True,
            is_workspace_scope=True,
        )
    raise ValidationDomainError(detail_override=f"Unsupported ORCIA entity URI path {cleaned!r}.")


def parse_qualified_entity_ref(
    raw_ref: str, *, default_kind: str | None = None
) -> QualifiedEntityRef:
    """Parse `@pack/slug`, `/pack/slug`, `pack:slug`, `@slug`, `/slug`, or `orcia://packs/...`."""
    cleaned = (raw_ref or "").strip()
    if not cleaned:
        raise ValidationDomainError(detail_override="Entity reference cannot be empty.")
    if cleaned.lower().startswith(("orcia://", "pack://")):
        return _parse_uri_entity_ref(cleaned, default_kind=default_kind)

    inferred_kind = default_kind
    work = cleaned
    if work.startswith("@"):
        inferred_kind, work = default_kind or "agents", work[1:]
    elif work.startswith("/"):
        inferred_kind, work = default_kind or "skills", work[1:]

    if "/" in work and (":" not in work or work.index("/") < work.index(":")):
        raw_pack, raw_rest = work.split("/", 1)
        pack_slug = _normalize_segment(raw_pack, field_name="pack_slug", raw_ref=cleaned)
        raw_slug, version_ref = _split_version_suffix(raw_rest.lstrip("@/"))
        entity_slug = _normalize_segment(raw_slug, field_name="entity_slug", raw_ref=cleaned)
        return QualifiedEntityRef(
            raw_ref=cleaned,
            entity_slug=entity_slug,
            pack_slug=pack_slug,
            kind=inferred_kind,
            version_ref=version_ref,
            is_qualified=True,
            is_workspace_scope=(pack_slug == "workspace"),
        )

    if ":" in work:
        raw_pack, raw_rest = work.split(":", 1)
        pack_slug = _normalize_segment(raw_pack, field_name="pack_slug", raw_ref=cleaned)
        raw_rest = raw_rest.strip()
        if raw_rest.startswith("@"):
            inferred_kind, raw_rest = default_kind or "agents", raw_rest[1:]
        elif raw_rest.startswith("/"):
            inferred_kind, raw_rest = default_kind or "skills", raw_rest[1:]
        raw_slug, version_ref = _split_version_suffix(raw_rest)
        entity_slug = _normalize_segment(raw_slug, field_name="entity_slug", raw_ref=cleaned)
        return QualifiedEntityRef(
            raw_ref=cleaned,
            entity_slug=entity_slug,
            pack_slug=pack_slug,
            kind=inferred_kind,
            version_ref=version_ref,
            is_qualified=True,
            is_workspace_scope=(pack_slug == "workspace"),
        )

    raw_slug, version_ref = _split_version_suffix(work)
    entity_slug = _normalize_segment(raw_slug, field_name="entity_slug", raw_ref=cleaned)
    return QualifiedEntityRef(
        raw_ref=cleaned,
        entity_slug=entity_slug,
        pack_slug=None,
        kind=inferred_kind,
        version_ref=version_ref,
        is_qualified=False,
        is_workspace_scope=False,
    )


def format_agent_mention(
    entity_slug: str, *, pack_slug: str | None = None, workspace_scoped: bool = False
) -> str:
    """Format canonical `D6.a` agent mention (`@<pack>/<slug>` or `@workspace/<slug>`)."""
    slug = entity_slug.strip().lstrip("@").lower()
    if workspace_scoped or (pack_slug and pack_slug.strip().lower() == "workspace"):
        return f"@workspace/{slug}"
    if pack_slug and pack_slug.strip():
        return f"@{pack_slug.strip().lower()}/{slug}"
    return f"@{slug}"


def format_skill_command(
    entity_slug: str, *, pack_slug: str | None = None, workspace_scoped: bool = False
) -> str:
    """Format canonical `D6.a` skill command (`/<pack>/<slug>` or `/workspace/<slug>`)."""
    slug = entity_slug.strip().lstrip("/").lower()
    if workspace_scoped or (pack_slug and pack_slug.strip().lower() == "workspace"):
        return f"/workspace/{slug}"
    if pack_slug and pack_slug.strip():
        return f"/{pack_slug.strip().lower()}/{slug}"
    return f"/{slug}"


def format_pack_resource_uri(
    pack_slug: str,
    kind: str,
    entity_slug: str,
    *,
    version: str | None = None,
    workspace_id: str | None = None,
) -> str:
    """Format canonical `orcia://packs/<pack>/<kind>/<slug>[@<semver>]` or workspace URI."""
    clean_pack, clean_kind, clean_slug = (
        pack_slug.strip().lower(),
        kind.strip().lower(),
        entity_slug.strip().lower(),
    )
    if clean_pack == "workspace" and workspace_id:
        base = f"orcia://workspaces/{workspace_id.strip()}/{clean_kind}/{clean_slug}"
    else:
        base = f"orcia://packs/{clean_pack}/{clean_kind}/{clean_slug}"
    return f"{base}@{version.strip()}" if version and version.strip() else base
