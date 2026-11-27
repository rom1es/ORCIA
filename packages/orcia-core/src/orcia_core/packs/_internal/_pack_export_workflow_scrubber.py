"""Workflow v2 & VSM v2 scrubbing helpers for pack export (`Story 31.5`, `<= 195 L`)."""

from __future__ import annotations

from typing import Any

from orcia_core.packs._internal._pack_export_scrubber import TenantInfraIdentifiers
from orcia_core.packs._internal._pack_export_scrubber_mappers import (
    debind_ref_value,
    normalize_model_tier,
)
from orcia_core.packs.models import PackSlotSpec
from orcia_core.workflows.schemas_v2 import (
    ValueStreamMapSpec,
    WorkflowDefinitionV2,
    WorkflowLifecycleStatus,
)


def _scrub_value_recursive(
    val: Any,
    *,
    pack_slug: str,
    infra: TenantInfraIdentifiers,
    slots_by_key: dict[str, PackSlotSpec],
) -> Any:
    if isinstance(val, str):
        if val.strip().lower() in infra.tenant_emails or val.strip().lower() in infra.tenant_uuids:
            deb = debind_ref_value(val, pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key)
            return "" if deb == val else deb
        return debind_ref_value(val, pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key)
    if isinstance(val, list):
        return [
            _scrub_value_recursive(x, pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key)
            for x in val
        ]
    if isinstance(val, dict):
        return {
            str(k): _scrub_value_recursive(
                v, pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
            )
            for k, v in val.items()
        }
    return val


def _scrub_controls_pipeline(
    raw_controls: Any,
    *,
    pack_slug: str,
    infra: TenantInfraIdentifiers,
    slots_by_key: dict[str, PackSlotSpec],
) -> Any:
    if not isinstance(raw_controls, dict):
        return raw_controls
    controls = dict(raw_controls)
    if isinstance(controls.get("deterministic"), list):
        controls["deterministic"] = [
            {
                **c,
                "config": _scrub_value_recursive(
                    c.get("config") or {},
                    pack_slug=pack_slug,
                    infra=infra,
                    slots_by_key=slots_by_key,
                ),
            }
            if isinstance(c, dict)
            else c
            for c in controls["deterministic"]
        ]
    if isinstance(controls.get("non_deterministic"), list):
        new_nd: list[Any] = []
        for c in controls["non_deterministic"]:
            if not isinstance(c, dict):
                new_nd.append(c)
                continue
            item = dict(c)
            if isinstance(item.get("agent_ref"), str) and item["agent_ref"]:
                item["agent_ref"] = debind_ref_value(
                    item["agent_ref"], pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
                )
            if isinstance(item.get("model_override"), str) and item["model_override"]:
                mo = item["model_override"].strip().lower()
                if mo not in ("team_default", "auto", "simple", "medium", "complex"):
                    item["model_override"] = normalize_model_tier(mo)
            new_nd.append(item)
        controls["non_deterministic"] = new_nd
    return controls


def scrub_workflow_v2_spec(
    raw_spec: dict[str, Any],
    *,
    pack_slug: str,
    infra: TenantInfraIdentifiers,
    slots_by_key: dict[str, PackSlotSpec],
) -> WorkflowDefinitionV2:
    """Rewrite workflow URI/datasource/model/control references to portable pack slots."""
    spec = dict(raw_spec)
    spec["pack_id"] = f"orcia-pack-{pack_slug}"
    spec["status"] = WorkflowLifecycleStatus.PUBLISHED.value
    if isinstance(spec.get("model_override"), str) and spec["model_override"]:
        mo = spec["model_override"].strip().lower()
        if mo not in ("team_default", "auto", "simple", "medium", "complex"):
            spec["model_override"] = normalize_model_tier(mo)
    for fk in ("global_system_prompt_or_ref", "knowledge_feedback_target_agent"):
        if isinstance(spec.get(fk), str) and spec[fk]:
            spec[fk] = debind_ref_value(
                spec[fk], pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
            )
    if isinstance(spec.get("contract"), dict):
        cdict = dict(spec["contract"])
        if isinstance(cdict.get("output_schema_uri"), str) and cdict["output_schema_uri"]:
            cdict["output_schema_uri"] = debind_ref_value(
                cdict["output_schema_uri"],
                pack_slug=pack_slug,
                infra=infra,
                slots_by_key=slots_by_key,
            )
        if isinstance(cdict.get("parameters"), list):
            cdict["parameters"] = [
                {
                    **p,
                    "catalog_entity_uri_pattern": debind_ref_value(
                        p["catalog_entity_uri_pattern"],
                        pack_slug=pack_slug,
                        infra=infra,
                        slots_by_key=slots_by_key,
                    ),
                }
                if isinstance(p, dict) and isinstance(p.get("catalog_entity_uri_pattern"), str)
                else p
                for p in cdict["parameters"]
            ]
        spec["contract"] = cdict
    if isinstance(spec.get("allowed_delegate_agents"), list):
        spec["allowed_delegate_agents"] = [
            debind_ref_value(str(x), pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key)
            for x in spec["allowed_delegate_agents"]
        ]
    if "controls" in spec:
        spec["controls"] = _scrub_controls_pipeline(
            spec["controls"], pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
        )
    if isinstance(spec.get("sub_steps"), list):
        new_steps = []
        for st in spec["sub_steps"]:
            if not isinstance(st, dict):
                continue
            step = dict(st)
            for rk in ("instruction_prompt_or_ref", "agent_ref", "datasource_id"):
                if isinstance(step.get(rk), str) and step[rk]:
                    step[rk] = debind_ref_value(
                        step[rk], pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
                    )
            for lk in ("allowed_rag_sources", "skill_refs"):
                if isinstance(step.get(lk), list):
                    step[lk] = [
                        debind_ref_value(
                            str(x), pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
                        )
                        for x in step[lk]
                    ]
            if isinstance(step.get("toolbox_mcp_permissions"), list):
                step["toolbox_mcp_permissions"] = [
                    {
                        str(k): debind_ref_value(
                            str(v), pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
                        )
                        for k, v in item.items()
                    }
                    for item in step["toolbox_mcp_permissions"]
                    if isinstance(item, dict)
                ]
            new_steps.append(step)
        spec["sub_steps"] = new_steps
    return WorkflowDefinitionV2.model_validate(spec)


def scrub_vsm_v2_spec(
    raw_spec: dict[str, Any],
    *,
    pack_slug: str,
    infra: TenantInfraIdentifiers,
    slots_by_key: dict[str, PackSlotSpec],
) -> ValueStreamMapSpec:
    """Scrub VSM v2 agent refs, linked workflows, controls & tenant fields."""
    vspec = dict(raw_spec)
    vspec["pack_id"] = f"orcia-pack-{pack_slug}"
    if isinstance(vspec.get("knowledge_foundation"), dict):
        vspec["knowledge_foundation"] = _scrub_value_recursive(
            vspec["knowledge_foundation"],
            pack_slug=pack_slug,
            infra=infra,
            slots_by_key=slots_by_key,
        )
    if isinstance(vspec.get("agents_catalog"), dict):
        vspec["agents_catalog"] = _scrub_value_recursive(
            vspec["agents_catalog"], pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
        )
    if isinstance(vspec.get("nodes"), list):
        new_nodes: list[Any] = []
        for raw_node in vspec["nodes"]:
            if not isinstance(raw_node, dict):
                new_nodes.append(raw_node)
                continue
            node = dict(raw_node)
            for rk in ("agent_ref", "linked_workflow_id", "human_co_author"):
                if isinstance(node.get(rk), str) and node[rk]:
                    node[rk] = _scrub_value_recursive(
                        node[rk], pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
                    )
            for lk in (
                "tools_actuel",
                "tools_ia",
                "humans_actuel",
                "humans_ia",
                "interactions_actuel",
                "interactions_ia",
            ):
                if lk in node:
                    node[lk] = _scrub_value_recursive(
                        node[lk], pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
                    )
            if "controls" in node:
                node["controls"] = _scrub_controls_pipeline(
                    node["controls"], pack_slug=pack_slug, infra=infra, slots_by_key=slots_by_key
                )
            new_nodes.append(node)
        vspec["nodes"] = new_nodes
    return ValueStreamMapSpec.model_validate(vspec)


__all__ = ["scrub_vsm_v2_spec", "scrub_workflow_v2_spec"]
