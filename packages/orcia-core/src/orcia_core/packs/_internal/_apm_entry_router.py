"""Entry routing helper dispatching normalized pack files into typed specs (`Story 31.1`)."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field
from typing import Any

from orcia_core.packs._internal._apm_manifest_parser import load_yaml_safe
from orcia_core.packs._internal._apm_markdown_parser import (
    parse_agent_markdown,
    parse_help_markdown,
    parse_instruction_markdown,
    parse_policy_markdown,
    parse_skill_markdown,
)
from orcia_core.packs._internal._apm_security_guards import validate_starlark_mechanism_ast
from orcia_core.packs.models import (
    PackAgentSpec,
    PackHelpArticleSpec,
    PackInstructionSpec,
    PackPolicySpec,
    PackSkillSpec,
)
from orcia_core.workflows.schemas_v2 import ValueStreamMapSpec, WorkflowDefinitionV2


@dataclass(slots=True)
class ParsedPackEntries:
    """Mutable accumulator for parsed pack entries before bundle assembly."""

    agents: list[PackAgentSpec] = field(default_factory=list)
    skills: list[PackSkillSpec] = field(default_factory=list)
    instructions: list[PackInstructionSpec] = field(default_factory=list)
    vsm_specs: list[ValueStreamMapSpec] = field(default_factory=list)
    workflows: list[WorkflowDefinitionV2] = field(default_factory=list)
    glossary: dict[str, Any] = field(default_factory=dict)
    gates_specs: dict[str, Any] = field(default_factory=dict)
    policies: list[PackPolicySpec] = field(default_factory=list)
    help_articles: list[PackHelpArticleSpec] = field(default_factory=list)
    star_sources: dict[str, str] = field(default_factory=dict)
    star_meta: dict[str, dict[str, Any]] = field(default_factory=dict)


def ingest_pack_entry(acc: ParsedPackEntries, *, rel_path: str, blob: bytes) -> None:
    """Parse one normalized pack entry into `acc`."""
    norm = rel_path.removeprefix(".apm/")
    if norm.startswith("agents/") and norm.endswith(".md"):
        stem = posixpath.basename(norm).removesuffix(".agent.md").removesuffix(".md")
        acc.agents.append(parse_agent_markdown(stem, blob.decode("utf-8"), source_path=rel_path))
    elif norm.startswith("skills/") and norm.endswith(".md"):
        parts = norm.split("/")
        slug = (
            parts[1]
            if len(parts) >= 3 and parts[-1] == "SKILL.md"
            else posixpath.basename(norm).removesuffix(".md")
        )
        acc.skills.append(parse_skill_markdown(slug, blob.decode("utf-8"), source_path=rel_path))
    elif norm.startswith("instructions/") and norm.endswith(".instructions.md"):
        stem = posixpath.basename(norm).removesuffix(".instructions.md")
        acc.instructions.append(
            parse_instruction_markdown(stem, blob.decode("utf-8"), source_path=rel_path)
        )
    elif norm.startswith("workflows/") and norm.endswith((".yaml", ".yml")):
        wf_data = load_yaml_safe(blob, source_path=rel_path)
        is_vsm = isinstance(wf_data, dict) and (
            "nodes" in wf_data
            or (posixpath.basename(norm).startswith("vsm-") and "sub_steps" not in wf_data)
        )
        if is_vsm:
            acc.vsm_specs.append(ValueStreamMapSpec.model_validate(wf_data))
        else:
            acc.workflows.append(WorkflowDefinitionV2.model_validate(wf_data))
    elif norm in ("ontology/glossary.yaml", "glossary.yaml"):
        loaded_glossary = load_yaml_safe(blob, source_path=rel_path) or {}
        if isinstance(loaded_glossary, dict):
            acc.glossary = loaded_glossary
    elif norm.startswith("ontology/mechanisms/") and norm.endswith(".star"):
        stem = posixpath.basename(norm).removesuffix(".star")
        src = blob.decode("utf-8")
        validate_starlark_mechanism_ast(src, mechanism_path=rel_path)
        acc.star_sources[stem] = src
    elif norm.startswith("ontology/mechanisms/") and norm.endswith((".yaml", ".yml")):
        stem = posixpath.basename(norm).rsplit(".", 1)[0]
        loaded_meta = load_yaml_safe(blob, source_path=rel_path) or {}
        if isinstance(loaded_meta, dict):
            acc.star_meta[stem] = loaded_meta
    elif norm.startswith("gates/"):
        stem = posixpath.basename(norm).rsplit(".", 1)[0]
        acc.gates_specs[stem] = (
            load_yaml_safe(blob, source_path=rel_path)
            if norm.endswith((".yaml", ".yml"))
            else blob.decode("utf-8")
        )
    elif norm.startswith("policies/") and norm.endswith(".policy.md"):
        stem = posixpath.basename(norm).removesuffix(".policy.md")
        acc.policies.append(parse_policy_markdown(stem, blob.decode("utf-8"), source_path=rel_path))
    elif norm.startswith("help/fr/") and norm.endswith(".md"):
        stem = posixpath.basename(norm).removesuffix(".md")
        acc.help_articles.append(
            parse_help_markdown(stem, "fr", blob.decode("utf-8"), source_path=rel_path)
        )
    elif norm.startswith("help/en/") and norm.endswith(".md"):
        stem = posixpath.basename(norm).removesuffix(".md")
        acc.help_articles.append(
            parse_help_markdown(stem, "en", blob.decode("utf-8"), source_path=rel_path)
        )


__all__ = ["ParsedPackEntries", "ingest_pack_entry"]
