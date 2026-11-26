"""Synthesize APM-Superset archive files from structured `LoadedPackBundleV2` (`Story 31.1`)."""

from __future__ import annotations

from typing import Any

import yaml  # type: ignore[import-untyped]

from orcia_core.packs.models import LoadedPackBundleV2


def _dump_frontmatter_md(frontmatter: dict[str, Any], body: str) -> bytes:
    if not frontmatter:
        return body.encode("utf-8")
    fm_text = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=True).strip()
    return f"---\n{fm_text}\n---\n{body}".encode()


def synthesize_files_from_bundle(bundle: LoadedPackBundleV2) -> dict[str, bytes]:
    """Build deterministic normalized archive entries from structured `LoadedPackBundleV2`."""
    files: dict[str, bytes] = {}
    m = bundle.manifest
    if bundle.manifest_yaml:
        files["apm.yml"] = bundle.manifest_yaml.encode("utf-8")
    else:
        apm_payload = {
            "name": m.name,
            "version": m.version,
            "description": m.description,
            "author": m.author,
            "maintainers": list(m.maintainers),
            "license": m.license,
            "mcp": m.mcp_declarations,
            "x-orcia": {
                "id": m.id or f"orcia-pack-{m.slug}",
                "slug": m.slug,
                "rbac_namespace": m.rbac_namespace,
                "bundle_kind": m.bundle_kind.value,
                "scope_type": m.scope_type.value,
                "scope_id": m.scope_id,
                "status": m.status.value,
                "connector_slots": [s.model_dump(mode="json") for s in m.declared_slots],
                "quick_actions": [q.model_dump(mode="json") for q in m.quick_actions],
            },
        }
        files["apm.yml"] = yaml.safe_dump(apm_payload, allow_unicode=True, sort_keys=True).encode(
            "utf-8"
        )

    for agent in bundle.agents:
        fm = dict(agent.frontmatter) or {"name": agent.name, "description": agent.description}
        files[f"agents/{agent.slug}.agent.md"] = _dump_frontmatter_md(
            fm, agent.instructions_markdown
        )
    for skill in bundle.skills:
        fm = dict(skill.frontmatter) or {"name": skill.name, "description": skill.description}
        files[f"skills/{skill.slug}/SKILL.md"] = _dump_frontmatter_md(
            fm, skill.instructions_markdown
        )
    for instr in bundle.instructions:
        fm = dict(instr.frontmatter) or {
            "applyTo": instr.apply_to,
            "description": instr.description,
        }
        files[f"instructions/{instr.slug}.instructions.md"] = _dump_frontmatter_md(
            fm, instr.body_markdown
        )
    for vsm in bundle.vsm_specs:
        files[f"workflows/vsm-{vsm.slug}.yaml"] = yaml.safe_dump(
            vsm.model_dump(mode="json"), allow_unicode=True, sort_keys=True
        ).encode("utf-8")
    for wf in bundle.workflows:
        files[f"workflows/{wf.slug}.yaml"] = yaml.safe_dump(
            wf.model_dump(mode="json"), allow_unicode=True, sort_keys=True
        ).encode("utf-8")
    if bundle.glossary:
        files["ontology/glossary.yaml"] = yaml.safe_dump(
            bundle.glossary, allow_unicode=True, sort_keys=True
        ).encode("utf-8")
    for mech in bundle.dna_mechanisms:
        files[f"ontology/mechanisms/{mech.mechanism_slug}.star"] = mech.starlark_source.encode(
            "utf-8"
        )
        mech_meta = {
            "name": mech.name,
            "input_schema": mech.input_schema,
            "output_schema": mech.output_schema,
            "passing_test_payload": mech.passing_test_payload,
            "failing_test_payload": mech.failing_test_payload,
        }
        files[f"ontology/mechanisms/{mech.mechanism_slug}.yaml"] = yaml.safe_dump(
            mech_meta, allow_unicode=True, sort_keys=True
        ).encode("utf-8")
    for gate_slug, spec in bundle.gates_specs.items():
        if isinstance(spec, str):
            files[f"gates/{gate_slug}.md"] = spec.encode("utf-8")
        else:
            files[f"gates/{gate_slug}.yaml"] = yaml.safe_dump(
                spec, allow_unicode=True, sort_keys=True
            ).encode("utf-8")
    for policy in bundle.policies:
        fm = dict(policy.frontmatter) or {
            "policy_key": policy.policy_key,
            "uri_pattern": policy.uri_pattern,
            "connector_scheme": policy.connector_scheme,
            "required_role": policy.required_role,
            "approver_team": policy.approver_team,
            "sla_hours": policy.sla_hours,
        }
        files[f"policies/{policy.policy_key}.policy.md"] = _dump_frontmatter_md(
            fm, policy.procedure_markdown
        )
    for art in bundle.help_articles:
        fm = dict(art.frontmatter) or {
            "resource_id": art.slug,
            "title": art.title,
            "bound_routes": art.bound_routes,
        }
        files[f"help/{art.lang}/{art.slug}.md"] = _dump_frontmatter_md(fm, art.body_markdown)
    return files


__all__ = ["synthesize_files_from_bundle"]
