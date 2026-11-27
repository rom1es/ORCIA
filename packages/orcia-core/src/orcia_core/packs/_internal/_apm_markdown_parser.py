"""Markdown frontmatter & APM asset parsers for `ApmPackCodec` (`Story 31.1`)."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from orcia_core.packs._internal._apm_security_guards import safe_load_yaml_strict
from orcia_core.packs.errors import PackInvalidArchiveError
from orcia_core.packs.models import (
    PackAgentSpec,
    PackDnaMechanismSpec,
    PackHelpArticleSpec,
    PackInstructionSpec,
    PackPolicySpec,
    PackReadinessStatus,
    PackSkillSpec,
)


def split_yaml_frontmatter(raw_text: str, *, source_path: str) -> tuple[dict[str, Any], str]:
    """Split optional YAML frontmatter (`--- ... ---`) from Markdown body safely."""
    lines = raw_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw_text
    end_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        raise PackInvalidArchiveError(
            detail_override=f"Unterminated YAML frontmatter block in {source_path!r}."
        )
    fm_yaml = "\n".join(lines[1:end_idx])
    parsed = safe_load_yaml_strict(fm_yaml, source_path=source_path) if fm_yaml.strip() else {}
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise PackInvalidArchiveError(
            detail_override=f"Frontmatter must be a YAML mapping in {source_path!r}."
        )
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    return parsed, body


def _classify_readiness(
    frontmatter: dict[str, Any],
    *,
    body_markdown: str,
    kind: Literal["agent", "skill"],
) -> tuple[PackReadinessStatus, bool]:
    x_orcia_raw = frontmatter.get("x-orcia")
    x_orcia: dict[str, Any] = dict(x_orcia_raw) if isinstance(x_orcia_raw, dict) else {}
    has_gov = len(x_orcia) > 0
    explicit_status = str(x_orcia.get("status") or frontmatter.get("status") or "").strip().lower()
    has_body = bool(body_markdown.strip())
    if kind == "agent":
        has_role_or_posture = any(
            bool(str(x_orcia.get(k) or "").strip())
            for k in ("posture", "role", "human_partner_role")
        )
    else:
        has_role_or_posture = bool(str(x_orcia.get("command_handle") or "").strip())
    if has_gov and has_body and has_role_or_posture and explicit_status != "draft":
        return PackReadinessStatus.ACTIVE, True
    return PackReadinessStatus.DRAFT, has_gov


def parse_agent_markdown(slug: str, raw_text: str, *, source_path: str) -> PackAgentSpec:
    """Parse `<slug>.agent.md` or legacy `agents/<slug>.md` into `PackAgentSpec`."""
    fm, body = split_yaml_frontmatter(raw_text, source_path=source_path)
    x_orcia_raw = fm.get("x-orcia")
    x_orcia: dict[str, Any] = dict(x_orcia_raw) if isinstance(x_orcia_raw, dict) else {}
    readiness, has_gov = _classify_readiness(fm, body_markdown=body, kind="agent")
    skill_refs = x_orcia.get("skill_refs") or fm.get("skills") or []
    connector_slots = x_orcia.get("connector_slots") or []
    return PackAgentSpec(
        slug=str(fm.get("slug") or slug),
        name=str(fm.get("name") or slug),
        description=str(fm.get("description") or ""),
        instructions_markdown=body,
        model_tier=str(x_orcia.get("llm_model_tier") or "medium"),
        skill_refs=[str(item) for item in skill_refs] if isinstance(skill_refs, list) else [],
        connector_slots=(
            [str(item) for item in connector_slots] if isinstance(connector_slots, list) else []
        ),
        lifecycle_status=readiness,
        has_orcia_governance=has_gov,
        frontmatter=fm,
    )


def parse_skill_markdown(slug: str, raw_text: str, *, source_path: str) -> PackSkillSpec:
    """Parse `skills/<slug>/SKILL.md` or legacy `skills/<slug>.md` into `PackSkillSpec`."""
    fm, body = split_yaml_frontmatter(raw_text, source_path=source_path)
    x_orcia_raw = fm.get("x-orcia")
    x_orcia: dict[str, Any] = dict(x_orcia_raw) if isinstance(x_orcia_raw, dict) else {}
    readiness, has_gov = _classify_readiness(fm, body_markdown=body, kind="skill")
    raw_params = x_orcia.get("input_parameters") or []
    params = (
        [dict(p) for p in raw_params if isinstance(p, dict)] if isinstance(raw_params, list) else []
    )
    return PackSkillSpec(
        slug=str(fm.get("slug") or slug),
        name=str(fm.get("name") or slug),
        description=str(fm.get("description") or ""),
        instructions_markdown=body,
        command_handle=str(x_orcia.get("command_handle") or slug),
        input_parameters=params,
        is_si_write=bool(x_orcia.get("is_si_write", False)),
        human_authored_required=bool(x_orcia.get("human_authored_required", False)),
        lifecycle_status=readiness,
        has_orcia_governance=has_gov,
        frontmatter=fm,
    )


def parse_instruction_markdown(
    slug: str, raw_text: str, *, source_path: str
) -> PackInstructionSpec:
    """Parse `instructions/<slug>.instructions.md` into `PackInstructionSpec`."""
    fm, body = split_yaml_frontmatter(raw_text, source_path=source_path)
    return PackInstructionSpec(
        slug=slug,
        apply_to=str(fm.get("applyTo") or fm.get("apply_to") or "**/*"),
        description=str(fm.get("description") or ""),
        body_markdown=body,
        frontmatter=fm,
    )


def parse_policy_markdown(slug: str, raw_text: str, *, source_path: str) -> PackPolicySpec:
    """Parse `policies/<slug>.policy.md` into `PackPolicySpec`."""
    fm, body = split_yaml_frontmatter(raw_text, source_path=source_path)
    uri_pattern = str(fm.get("uri_pattern") or "").strip()
    connector_scheme = str(fm.get("connector_scheme") or "").strip()
    required_role = str(fm.get("required_role") or "").strip()
    if not uri_pattern or not connector_scheme or not required_role:
        raise PackInvalidArchiveError(
            detail_override=(
                f"Policy file {source_path!r} must define uri_pattern, connector_scheme, "
                "and required_role in YAML frontmatter."
            )
        )
    sla_raw = fm.get("sla_hours", 24)
    try:
        sla_hours = int(sla_raw)
    except (TypeError, ValueError) as exc:
        raise PackInvalidArchiveError(
            detail_override=f"Invalid sla_hours in policy {source_path!r}."
        ) from exc
    return PackPolicySpec(
        policy_key=str(fm.get("policy_key") or slug),
        uri_pattern=uri_pattern,
        connector_scheme=connector_scheme,
        required_role=required_role,
        approver_team=str(fm.get("approver_team") or ""),
        sla_hours=max(1, sla_hours),
        procedure_markdown=body,
        frontmatter=fm,
    )


def parse_help_markdown(
    slug: str, lang: Literal["fr", "en"], raw_text: str, *, source_path: str
) -> PackHelpArticleSpec:
    """Parse `help/{fr,en}/<slug>.md` into `PackHelpArticleSpec`."""
    fm, body = split_yaml_frontmatter(raw_text, source_path=source_path)
    raw_routes = fm.get("bound_routes") or []
    routes = [str(r) for r in raw_routes] if isinstance(raw_routes, list) else []
    return PackHelpArticleSpec(
        slug=str(fm.get("resource_id") or slug),
        lang=lang,
        title=str(fm.get("title") or slug),
        bound_routes=routes,
        body_markdown=body,
        frontmatter=fm,
    )


def parse_starlark_mechanism(
    slug: str,
    star_source: str,
    sidecar_meta: dict[str, Any] | None = None,
) -> PackDnaMechanismSpec:
    """Build `PackDnaMechanismSpec` from `.star` source and optional sidecar metadata."""
    meta = sidecar_meta or {}
    source_sha = hashlib.sha256(star_source.encode("utf-8")).hexdigest()
    return PackDnaMechanismSpec(
        mechanism_slug=str(meta.get("mechanism_slug") or slug),
        name=str(meta.get("name") or slug),
        starlark_source=star_source,
        source_sha256=source_sha,
        input_schema=dict(meta.get("input_schema") or {}),
        output_schema=dict(meta.get("output_schema") or {}),
        passing_test_payload=(
            dict(meta["passing_test_payload"])
            if isinstance(meta.get("passing_test_payload"), dict)
            else None
        ),
        failing_test_payload=(
            dict(meta["failing_test_payload"])
            if isinstance(meta.get("failing_test_payload"), dict)
            else None
        ),
    )


__all__ = [
    "parse_agent_markdown",
    "parse_help_markdown",
    "parse_instruction_markdown",
    "parse_policy_markdown",
    "parse_skill_markdown",
    "parse_starlark_mechanism",
    "split_yaml_frontmatter",
]
