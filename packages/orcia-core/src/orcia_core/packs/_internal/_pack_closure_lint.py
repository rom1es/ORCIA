"""Prose linter, ref normalization & member alias helpers (`Story 31.5`, `<= 115 L`)."""

from __future__ import annotations

import re

from orcia_core.domain.namespacing import parse_qualified_entity_ref
from orcia_core.packs.composer_models import PackDraftMemberView, ProseLintWarning
from orcia_core.packs.models import PackDraftEntityType
from orcia_kernel.errors import ValidationDomainError

_BARE_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_/@.-])@([a-z][a-z0-9_-]{1,63})(?![/a-z0-9_-])")
_BARE_SLASH_RE = re.compile(r"(?<![A-Za-z0-9_/:.-])/([a-z][a-z0-9_-]{1,63})(?![/a-z0-9_-])")


def norm_ref(raw: str) -> str:
    """Normalize a ref string to its bare entity slug/key."""
    clean = raw.strip()
    if not clean:
        return ""
    try:
        return parse_qualified_entity_ref(clean).entity_slug
    except ValidationDomainError:
        pass
    if clean.startswith(("@", "/")):
        clean = clean[1:]
    if "/" in clean and "://" not in clean:
        clean = clean.rsplit("/", 1)[-1]
    if ":" in clean and "://" not in clean:
        clean = clean.rsplit(":", 1)[-1]
    return clean.split("@", 1)[0].strip()


def lint_prose_bare_handles(
    entity_type: str,
    entity_slug: str,
    markdown_text: str,
    *,
    known_agent_slugs: frozenset[str],
    known_skill_slugs: frozenset[str],
) -> list[ProseLintWarning]:
    """Flag bare `@slug` / `/slug` references in markdown without mutating prose (`R1`)."""
    warnings: list[ProseLintWarning] = []
    seen: set[str] = set()
    for match in _BARE_MENTION_RE.finditer(markdown_text):
        slug = match.group(1)
        tok = f"@{slug}"
        if slug in known_agent_slugs and tok not in seen:
            seen.add(tok)
            warnings.append(
                ProseLintWarning(
                    entity_type=entity_type,
                    entity_slug=entity_slug,
                    token=tok,
                    message=f"Bare agent handle '{tok}' should be qualified in pack prose.",
                )
            )
    for match in _BARE_SLASH_RE.finditer(markdown_text):
        slug = match.group(1)
        tok = f"/{slug}"
        if slug in known_skill_slugs and tok not in seen:
            seen.add(tok)
            warnings.append(
                ProseLintWarning(
                    entity_type=entity_type,
                    entity_slug=entity_slug,
                    token=tok,
                    message=f"Bare skill handle '{tok}' should be qualified in pack prose.",
                )
            )
    return warnings


def normalized_lookup_candidates(raw_ref: str) -> list[str]:
    """Generate ordered candidate keys for resolving a dependency reference."""
    clean = raw_ref.strip()
    norm = norm_ref(clean)
    out = [clean]
    if ":" in clean and "://" not in clean:
        tail = clean.split(":")[-1].strip()
        if tail and tail not in out:
            out.append(tail)
    if norm and norm not in out:
        out.append(norm)
    return out


def aliases_for_member(etype: PackDraftEntityType, eid: str, slug: str) -> set[str]:
    """Build normalized lowercase lookup aliases for an entity."""
    _ = etype
    clean_eid = eid.strip().lower()
    clean_slug = slug.strip().lower()
    aliases = {clean_eid, clean_slug}
    if ":" in clean_eid:
        aliases.add(clean_eid.rsplit(":", 1)[-1].strip())
        aliases.add(clean_eid.split(":", 1)[1].strip())
    return {a for a in aliases if a}


def fk_uuid_for_member(m: PackDraftMemberView) -> str:
    """Return the active surrogate UUID FK populated on a hydrated draft member."""
    return (
        m.catalog_item_id
        or m.workflow_v2_id
        or m.vsm_v2_id
        or m.ontology_concept_id
        or m.ontology_relation_id
        or m.ontology_axiom_id
        or m.dna_mechanism_id
        or m.policy_id
        or ""
    )


__all__ = [
    "aliases_for_member",
    "fk_uuid_for_member",
    "lint_prose_bare_handles",
    "norm_ref",
    "normalized_lookup_candidates",
]
