"""Pure dependency extraction dispatch for closure analysis (`Story 31.5`, `<= 220 L`)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from orcia_core.packs._internal._pack_closure_lint import (
    aliases_for_member,
    fk_uuid_for_member,
    lint_prose_bare_handles,
    normalized_lookup_candidates,
)
from orcia_core.packs.models import PackDraftEntityType

_AGENT_URI_RE = re.compile(
    r"(?:orcia|pack)://(?:(?:packs|workspaces|system)/)?[^/]+/agents/([^/@\s]+)"
)
_SKILL_URI_RE = re.compile(
    r"(?:orcia|pack)://(?:(?:packs|workspaces|system)/)?[^/]+/skills/([^/@\s]+)"
)
_WF_URI_RE = re.compile(
    r"(?:orcia|pack)://(?:(?:packs|workspaces|system)/)?[^/]+/workflows/([^/@\s]+)"
)
_INSTR_URI_RE = re.compile(
    r"(?:orcia|pack)://(?:(?:packs|workspaces|system)/)?[^/]+/instructions/([^/@\s]+)"
)


@dataclass(frozen=True, slots=True)
class ExtractedRef:
    """One extracted dependency reference from an entity's structured fields."""

    entity_type: PackDraftEntityType
    lookup_key: str
    referenced_by: str


def _extract_controls_refs(controls: Any, src_label: str, refs: list[ExtractedRef]) -> None:
    if not isinstance(controls, dict):
        return
    for item in controls.get("non_deterministic") or []:
        if isinstance(item, dict):
            ag = item.get("agent_ref")
            if isinstance(ag, str) and ag.strip():
                refs.append(ExtractedRef(PackDraftEntityType.AGENT, ag.strip(), src_label))
    for item in controls.get("deterministic") or []:
        if not isinstance(item, dict):
            continue
        cfg = item.get("config")
        if isinstance(cfg, dict):
            for key in ("dna_mechanism_slug", "starlark_mechanism_slug", "mechanism_slug"):
                val = cfg.get(key)
                if isinstance(val, str) and val.strip():
                    refs.append(
                        ExtractedRef(PackDraftEntityType.DNA_MECHANISM, val.strip(), src_label)
                    )
            ax_keys = cfg.get("ontology_axiom_keys") or []
            if isinstance(ax_keys, list):
                for ax in ax_keys:
                    if isinstance(ax, str) and ax.strip():
                        refs.append(
                            ExtractedRef(PackDraftEntityType.ONTOLOGY_AXIOM, ax.strip(), src_label)
                        )


def extract_agent_refs(agent_slug: str, meta: dict[str, Any]) -> list[ExtractedRef]:
    """Extract skill, ontology, instruction & policy deps from catalog `USER_AGENT` metadata."""
    refs: list[ExtractedRef] = []
    src_label = f"AGENT:{agent_slug}"
    for key in ("skill_ids", "skill_refs"):
        vals = meta.get(key) or []
        if isinstance(vals, list):
            for item in vals:
                if isinstance(item, str) and item.strip():
                    refs.append(ExtractedRef(PackDraftEntityType.SKILL, item.strip(), src_label))
    ont_views = meta.get("ontology_views") or meta.get("ontology_concept_keys") or []
    if isinstance(ont_views, list):
        for item in ont_views:
            if isinstance(item, str) and item.strip():
                refs.append(
                    ExtractedRef(PackDraftEntityType.ONTOLOGY_CONCEPT, item.strip(), src_label)
                )
    for key, etype in (
        ("instruction_refs", PackDraftEntityType.INSTRUCTION),
        ("policy_keys", PackDraftEntityType.POLICY),
    ):
        vals = meta.get(key) or []
        if isinstance(vals, list):
            for item in vals:
                if isinstance(item, str) and item.strip():
                    refs.append(ExtractedRef(etype, item.strip(), src_label))
    return refs


def _extract_step_refs(step: dict[str, Any], src_label: str, refs: list[ExtractedRef]) -> None:
    for key in ("agent_ref", "agent_id", "owner_agent_ref"):
        val = step.get(key)
        if isinstance(val, str) and val.strip():
            refs.append(ExtractedRef(PackDraftEntityType.AGENT, val.strip(), src_label))
    prompt_ref = str(step.get("instruction_prompt_or_ref") or "").strip()
    if m := _AGENT_URI_RE.search(prompt_ref):
        refs.append(ExtractedRef(PackDraftEntityType.AGENT, m.group(1), src_label))
    elif m := _SKILL_URI_RE.search(prompt_ref):
        refs.append(ExtractedRef(PackDraftEntityType.SKILL, m.group(1), src_label))
    elif m := _INSTR_URI_RE.search(prompt_ref):
        refs.append(ExtractedRef(PackDraftEntityType.INSTRUCTION, m.group(1), src_label))
    elif prompt_ref.startswith("@"):
        refs.append(ExtractedRef(PackDraftEntityType.AGENT, prompt_ref, src_label))
    for key in ("skill_refs", "skill_ids"):
        vals = step.get(key) or []
        if isinstance(vals, list):
            for item in vals:
                if isinstance(item, str) and item.strip():
                    refs.append(ExtractedRef(PackDraftEntityType.SKILL, item.strip(), src_label))
    for key in ("sub_workflow_id", "linked_workflow_id", "target_workflow_slug"):
        val = step.get(key)
        if isinstance(val, str) and val.strip():
            m_wf = _WF_URI_RE.search(val)
            refs.append(
                ExtractedRef(
                    PackDraftEntityType.WORKFLOW_V2,
                    m_wf.group(1) if m_wf else val.strip(),
                    src_label,
                )
            )
    for key in ("dna_mechanism_slug", "starlark_mechanism_slug", "mechanism_slug"):
        val = step.get(key)
        if isinstance(val, str) and val.strip():
            refs.append(ExtractedRef(PackDraftEntityType.DNA_MECHANISM, val.strip(), src_label))
    ax_keys = step.get("ontology_axiom_keys") or []
    if isinstance(ax_keys, list):
        for ax in ax_keys:
            if isinstance(ax, str) and ax.strip():
                refs.append(ExtractedRef(PackDraftEntityType.ONTOLOGY_AXIOM, ax.strip(), src_label))
    _extract_controls_refs(step.get("controls"), src_label, refs)


def extract_workflow_refs(wf_slug: str, spec: dict[str, Any]) -> list[ExtractedRef]:
    """Extract agent, skill, sub-workflow, VSM, DNA, contract & axiom deps from workflow spec."""
    refs: list[ExtractedRef] = []
    src_label = f"WORKFLOW_V2:{wf_slug}"
    for key in ("vsm_id", "linked_vsm_id"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip():
            refs.append(ExtractedRef(PackDraftEntityType.VSM_V2, val.strip(), src_label))
    delegates = spec.get("allowed_delegate_agents") or []
    if isinstance(delegates, list):
        for ag in delegates:
            if isinstance(ag, str) and ag.strip():
                refs.append(ExtractedRef(PackDraftEntityType.AGENT, ag.strip(), src_label))
    fb_ag = spec.get("knowledge_feedback_target_agent")
    if isinstance(fb_ag, str) and fb_ag.strip():
        refs.append(ExtractedRef(PackDraftEntityType.AGENT, fb_ag.strip(), src_label))
    contract = spec.get("contract")
    if isinstance(contract, dict):
        out_uri = str(contract.get("output_schema_uri") or "").strip()
        if m_in := _INSTR_URI_RE.search(out_uri):
            refs.append(ExtractedRef(PackDraftEntityType.INSTRUCTION, m_in.group(1), src_label))
    _extract_controls_refs(spec.get("controls"), src_label, refs)
    sub_steps = spec.get("sub_steps") or spec.get("steps") or []
    if isinstance(sub_steps, list):
        for step in sub_steps:
            if isinstance(step, dict):
                _extract_step_refs(step, src_label, refs)
    return refs


def extract_vsm_refs(vsm_slug: str, spec: dict[str, Any]) -> list[ExtractedRef]:
    """Extract linked workflow, agent & control dependencies from a VSM specification."""
    refs: list[ExtractedRef] = []
    src_label = f"VSM_V2:{vsm_slug}"
    for list_key in ("nodes", "stages", "steps"):
        nodes = spec.get(list_key) or []
        if not isinstance(nodes, list):
            continue
        for node in nodes:
            if not isinstance(node, dict):
                continue
            for wf_key in ("linked_workflow_id", "workflow_id", "target_workflow_slug"):
                val = node.get(wf_key)
                if isinstance(val, str) and val.strip():
                    refs.append(
                        ExtractedRef(PackDraftEntityType.WORKFLOW_V2, val.strip(), src_label)
                    )
            for ag_key in ("owner_agent_ref", "agent_ref", "agent_id"):
                val = node.get(ag_key)
                if isinstance(val, str) and val.strip():
                    refs.append(ExtractedRef(PackDraftEntityType.AGENT, val.strip(), src_label))
            _extract_controls_refs(node.get("controls"), src_label, refs)
    return refs


def extract_refs_from_payload(
    etype: PackDraftEntityType, slug: str, payload: dict[str, Any]
) -> list[ExtractedRef]:
    """Dispatch dependency extraction according to member entity type."""
    if etype == PackDraftEntityType.AGENT:
        return extract_agent_refs(slug, payload.get("meta") or {})
    if etype == PackDraftEntityType.WORKFLOW_V2:
        return extract_workflow_refs(slug, payload.get("spec") or {})
    if etype == PackDraftEntityType.VSM_V2:
        return extract_vsm_refs(slug, payload.get("spec") or {})
    if etype == PackDraftEntityType.ONTOLOGY_RELATION:
        return [
            ExtractedRef(
                PackDraftEntityType.ONTOLOGY_CONCEPT, str(payload[c]), f"ONTOLOGY_RELATION:{slug}"
            )
            for c in ("source_concept_id", "target_concept_id")
            if payload.get(c)
        ]
    if etype == PackDraftEntityType.ONTOLOGY_AXIOM and payload.get("concept_id"):
        return [
            ExtractedRef(
                PackDraftEntityType.ONTOLOGY_CONCEPT,
                str(payload["concept_id"]),
                f"ONTOLOGY_AXIOM:{slug}",
            )
        ]
    return []


__all__ = [
    "ExtractedRef",
    "aliases_for_member",
    "extract_agent_refs",
    "extract_refs_from_payload",
    "extract_vsm_refs",
    "extract_workflow_refs",
    "fk_uuid_for_member",
    "lint_prose_bare_handles",
    "normalized_lookup_candidates",
]
