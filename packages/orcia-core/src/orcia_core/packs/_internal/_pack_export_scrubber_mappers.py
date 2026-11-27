"""Entity scrubbing & de-binding mappers for pack export (`Story 31.5`, `<= 225 L`)."""

from __future__ import annotations

import re
from typing import Any

from orcia_core.domain.namespacing import parse_qualified_entity_ref
from orcia_core.packs._internal._pack_export_loaders import RawExportEntities
from orcia_core.packs._internal._pack_export_scrubber import TenantInfraIdentifiers
from orcia_core.packs._internal._sql_pack_composer_hydration import decode_json_dict
from orcia_core.packs.models import (
    PackAgentSpec,
    PackHelpArticleSpec,
    PackInstructionSpec,
    PackReadinessStatus,
    PackSkillSpec,
    PackSlotSpec,
)
from orcia_kernel.errors import ValidationDomainError

_SLOT_REF_RE = re.compile(r"^slot://([a-zA-Z0-9_.-]+)$")
_WS_URI_RE = re.compile(r"orcia://workspaces/[^/]+/(agents|skills|workflows|gates)/([^/@\s]+)")
_PACK_URI_RE = re.compile(
    r"(?:orcia|pack)://(?:packs/)?[^/]+/(agents|skills|workflows|gates)/([^/@\s]+)"
)


def normalize_model_tier(raw: object) -> str:
    """Normalize concrete model IDs or effort labels to `simple | medium | complex`."""
    val = str(raw or "medium").strip().lower()
    if val in ("simple", "fast"):
        return "simple"
    if val in ("complex", "deep", "reasoning"):
        return "complex"
    return "medium"


def normalize_skill_ref(raw: str) -> str:
    """Extract clean skill slug from any qualified/URI/colon reference."""
    clean = raw.strip()
    if not clean:
        return ""
    try:
        return parse_qualified_entity_ref(clean, default_kind="skills").entity_slug
    except ValidationDomainError:
        tail = clean.rsplit("/", 1)[-1]
        return tail.rsplit(":", 1)[-1].lstrip("/@").strip()


def _parse_readiness_status(raw: object) -> PackReadinessStatus:
    val = str(raw or "ACTIVE").strip().upper()
    for member in PackReadinessStatus:
        if member.value == val:
            return member
    return PackReadinessStatus.ACTIVE


def debind_ref_value(
    raw: str,
    *,
    pack_slug: str,
    infra: TenantInfraIdentifiers,
    slots_by_key: dict[str, PackSlotSpec],
) -> str:
    """Rewrite concrete datasource/connector UUID/URL or workspace URI to `slot://` or pack URI."""
    clean = raw.strip()
    slot_meta = infra.datasource_slots_by_ref.get(
        clean.lower()
    ) or infra.datasource_slots_by_ref.get(clean)
    if slot_meta is not None:
        skey = slot_meta["slot_key"]
        if skey not in slots_by_key:
            slots_by_key[skey] = PackSlotSpec(
                slot_key=skey,
                scheme=slot_meta.get("scheme") or "git",
                connector_kind=slot_meta.get("connector_kind") or "",
                source_nature=slot_meta.get("source_nature") or "",
                required=True,
            )
        return f"slot://{skey}"
    if m_slot := _SLOT_REF_RE.match(clean):
        skey = m_slot.group(1)
        if skey not in slots_by_key:
            slots_by_key[skey] = PackSlotSpec(slot_key=skey, scheme="git", required=True)
        return clean
    if m_ws := _WS_URI_RE.search(clean):
        return f"orcia://packs/{pack_slug}/{m_ws.group(1)}/{m_ws.group(2)}"
    if clean.startswith("pack://") and (m_pk := _PACK_URI_RE.search(clean)):
        return f"orcia://packs/{pack_slug}/{m_pk.group(1)}/{m_pk.group(2)}"
    return raw


def build_scrubbed_catalog_specs(
    entities: RawExportEntities,
    *,
    pack_slug: str,
    infra: TenantInfraIdentifiers,
    slots_by_key: dict[str, PackSlotSpec],
) -> tuple[
    list[PackAgentSpec], list[PackSkillSpec], list[PackInstructionSpec], list[PackHelpArticleSpec]
]:
    """Convert raw `catalog_items` rows into scrubbed portable APM specs."""
    agents: list[PackAgentSpec] = []
    skills: list[PackSkillSpec] = []
    instructions: list[PackInstructionSpec] = []
    help_articles: list[PackHelpArticleSpec] = []
    skill_id_to_slug: dict[str, str] = {}
    for row in entities.catalog_items:
        itype = str(row.get("item_type") or "").upper()
        rtype = str(row.get("resource_type") or "").lower()
        if itype == "USER_SKILL" or rtype == "skill":
            meta = decode_json_dict(row.get("metadata_jsonb"))
            res_id = str(row.get("resource_id") or "")
            default_slug = res_id.rsplit(":", 1)[-1] if ":" in res_id else res_id
            sk_slug = str(meta.get("slug") or default_slug)
            if res_id:
                skill_id_to_slug[res_id] = sk_slug
            if row.get("id"):
                skill_id_to_slug[str(row["id"])] = sk_slug

    for row in entities.catalog_items:
        meta = decode_json_dict(row.get("metadata_jsonb"))
        itype = str(row.get("item_type") or "").upper()
        rtype = str(row.get("resource_type") or "").lower()
        res_id = str(row.get("resource_id") or "")
        slug = str(meta.get("slug") or (res_id.rsplit(":", 1)[-1] if ":" in res_id else res_id))
        if itype == "USER_AGENT" or rtype == "agent":
            raw_skills = meta.get("skill_ids") or meta.get("skill_refs") or []
            skill_refs = [
                norm
                for s in raw_skills
                if isinstance(s, str)
                and (norm := skill_id_to_slug.get(s.strip()) or normalize_skill_ref(s))
            ]
            raw_slots = list(meta.get("connector_slots") or []) + list(
                meta.get("allowed_rag_sources") or []
            )
            slot_keys: list[str] = []
            for sref in raw_slots:
                if isinstance(sref, str) and sref.strip():
                    deb = debind_ref_value(
                        sref, pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
                    )
                    if deb.startswith("slot://"):
                        sk = deb.removeprefix("slot://")
                        if sk not in slot_keys:
                            slot_keys.append(sk)
            tier = normalize_model_tier(meta.get("llm_model_tier") or meta.get("thinking_level"))
            posture = str(meta.get("posture") or "PRODUCER").upper()
            partner = str(meta.get("human_partner_role") or "TECH_LEAD").upper()
            body = str(
                meta.get("instructions") or row.get("description") or row.get("title") or slug
            )
            readiness = _parse_readiness_status(meta.get("lifecycle_status"))
            x_orcia = {
                "posture": posture,
                "human_partner_role": partner,
                "llm_model_tier": tier,
                "skill_refs": skill_refs,
                "connector_slots": slot_keys,
                "status": "draft" if readiness == PackReadinessStatus.DRAFT else "active",
            }
            agents.append(
                PackAgentSpec(
                    slug=slug,
                    name=str(row.get("title") or slug),
                    description=str(row.get("description") or ""),
                    instructions_markdown=body,
                    model_tier=tier,
                    skill_refs=skill_refs,
                    connector_slots=slot_keys,
                    lifecycle_status=readiness,
                    has_orcia_governance=True,
                    frontmatter={
                        "name": str(row.get("title") or slug),
                        "description": str(row.get("description") or ""),
                        "x-orcia": x_orcia,
                    },
                )
            )
        elif itype == "USER_SKILL" or rtype == "skill":
            cmd = str(meta.get("command_handle") or f"/{slug}")
            raw_params = meta.get("input_parameters") or []
            params = [
                {"name": p} if isinstance(p, str) else dict(p)
                for p in raw_params
                if isinstance(p, (str, dict))
            ]
            body = str(
                meta.get("instructions") or row.get("description") or row.get("title") or slug
            )
            readiness = _parse_readiness_status(meta.get("lifecycle_status"))
            x_orcia_sk = {
                "command_handle": cmd,
                "input_parameters": params,
                "is_si_write": bool(meta.get("is_si_write", False)),
                "human_authored_required": bool(meta.get("human_authored_required", False)),
            }
            skills.append(
                PackSkillSpec(
                    slug=slug,
                    name=str(row.get("title") or slug),
                    description=str(row.get("description") or ""),
                    instructions_markdown=body,
                    command_handle=cmd,
                    input_parameters=params,
                    is_si_write=bool(x_orcia_sk["is_si_write"]),
                    human_authored_required=bool(x_orcia_sk["human_authored_required"]),
                    lifecycle_status=readiness,
                    has_orcia_governance=True,
                    frontmatter={
                        "name": str(row.get("title") or slug),
                        "description": str(row.get("description") or ""),
                        "x-orcia": x_orcia_sk,
                    },
                )
            )
        elif itype == "HELP_ARTICLE" or rtype == "help_article":
            lang_val = "en" if str(meta.get("lang") or "fr").lower() == "en" else "fr"
            body = str(
                meta.get("markdown_body")
                or meta.get("body_markdown")
                or row.get("description")
                or ""
            )
            fm: dict[str, Any] = {
                "resource_id": slug.removeprefix("help:").removeprefix("fr:").removeprefix("en:"),
                "title": str(row.get("title") or slug),
                "bound_routes": [str(r) for r in (meta.get("bound_routes") or [])],
            }
            if meta.get("summary_what_for"):
                fm["summary_what_for"] = str(meta["summary_what_for"])
            help_articles.append(
                PackHelpArticleSpec(
                    slug=fm["resource_id"],
                    lang=lang_val,  # type: ignore[arg-type]
                    title=str(row.get("title") or slug),
                    bound_routes=fm["bound_routes"],
                    body_markdown=body,
                    frontmatter=fm,
                )
            )
        else:
            instructions.append(
                PackInstructionSpec(
                    slug=slug.removeprefix("instr:"),
                    apply_to=str(meta.get("apply_to") or "**/*"),
                    description=str(row.get("description") or ""),
                    body_markdown=str(
                        meta.get("markdown_body")
                        or meta.get("body_markdown")
                        or row.get("description")
                        or ""
                    ),
                )
            )
    return agents, skills, instructions, help_articles


__all__ = [
    "build_scrubbed_catalog_specs",
    "debind_ref_value",
    "normalize_model_tier",
    "normalize_skill_ref",
]
