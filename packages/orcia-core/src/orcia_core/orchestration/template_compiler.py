"""Multi-Audience Artifact Template Compiler (Story 3.1, FR-12, FR-6, AD-7).

Simultaneously compiles a declarative template into:
1. A structured Human Markdown view (variable interpolation, mandatory sections,
   `human_authored_required` markers, and cognitive chunking <= 800 words).
2. A formal JSON Schema (Draft 2020-12) typed by the 4-level Ontology for downstream agents.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import json
import re
from typing import Any

from orcia_core.catalog.cas_resolver import compute_bytes_sha256
from orcia_core.ontology.models import OntologyConceptEntity, ResolvedOntologySnapshot
from orcia_core.orchestration.errors import ValidationDomainError
from orcia_core.orchestration.models import (
    ArtifactTemplateDefinition,
    ArtifactTemplateSectionSpec,
    CompiledArtifactTemplate,
    CompiledMarkdownChunk,
)

_MUSTACHE_VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
MAX_COGNITIVE_CHUNK_WORDS = 800


def _map_ontology_field_type(raw_type: str) -> dict[str, Any]:
    if raw_type == "int":
        return {"type": "integer"}
    if raw_type in ("float", "number", "decimal"):
        return {"type": "number"}
    if raw_type == "bool":
        return {"type": "boolean"}
    if raw_type == "non_empty_list":
        return {"type": "array", "items": {"type": "string"}, "minItems": 1}
    return {"type": "string"}


class MultiAudienceTemplateCompiler:
    """Compiles an `ArtifactTemplateDefinition` into Human Markdown + Ontology JSON Schema."""

    @staticmethod
    def _interpolate_variables(
        template_text: str,
        variables: dict[str, str],
        required_variables: tuple[str, ...],
        *,
        instance: str | None = None,
    ) -> str:
        missing = [var for var in required_variables if var not in variables]
        if missing:
            raise ValidationDomainError(
                detail_override=f"Variables obligatoires manquantes dans le gabarit: {missing}",
                instance=instance,
            )

        def _replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return str(variables.get(var_name, f"{{{{ {var_name} }}}}"))

        return _MUSTACHE_VAR_PATTERN.sub(_replace, template_text)

    @staticmethod
    def _split_into_cognitive_chunks(
        section: ArtifactTemplateSectionSpec,
        rendered_body: str,
        start_chunk_index: int,
    ) -> list[CompiledMarkdownChunk]:
        max_words = min(max(section.max_words_chunk, 50), MAX_COGNITIVE_CHUNK_WORDS)
        words = rendered_body.split()
        if not words:
            return [
                CompiledMarkdownChunk(
                    chunk_index=start_chunk_index,
                    section_key=section.section_key,
                    section_title=section.title,
                    markdown_content=f"## {section.title}\n",
                    word_count=0,
                    human_authored_required=section.human_authored_required,
                )
            ]

        chunks: list[CompiledMarkdownChunk] = []
        for offset in range(0, len(words), max_words):
            slice_words = words[offset : offset + max_words]
            part_suffix = f" (Partie {len(chunks) + 1})" if len(words) > max_words else ""
            header_badge = (
                " [✍️ ANCRE HUMAINE OBLIGATOIRE]" if section.human_authored_required else ""
            )
            chunk_md = f"## {section.title}{part_suffix}{header_badge}\n\n{' '.join(slice_words)}"
            chunks.append(
                CompiledMarkdownChunk(
                    chunk_index=start_chunk_index + len(chunks),
                    section_key=section.section_key,
                    section_title=f"{section.title}{part_suffix}",
                    markdown_content=chunk_md,
                    word_count=len(slice_words),
                    human_authored_required=section.human_authored_required,
                )
            )
        return chunks

    @staticmethod
    def _build_section_schema(
        section: ArtifactTemplateSectionSpec,
        concept: OntologyConceptEntity | None,
    ) -> dict[str, Any]:
        if concept is not None:
            properties: dict[str, Any] = {
                "markdown_summary": {
                    "type": "string",
                    "description": f"Synthèse rédigée de la section '{section.title}'.",
                },
                "human_authored_required": {
                    "type": "boolean",
                    "const": section.human_authored_required,
                },
            }
            required_fields = ["markdown_summary"]
            for field_name, field_type in sorted(concept.expected_schema.items()):
                properties[field_name] = _map_ontology_field_type(field_type)
                required_fields.append(field_name)
            return {
                "type": "object",
                "title": section.title,
                "description": (
                    f"{concept.canonical_term} ({concept.level}): {concept.definition_text}"
                ),
                "x-ontology-concept-key": concept.concept_key,
                "x-ontology-canonical-term": concept.canonical_term,
                "x-ontology-synonyms": list(concept.synonyms),
                "x-ontology-banned-terms": list(concept.banned_terms),
                "x-human-authored-required": section.human_authored_required,
                "properties": properties,
                "required": required_fields,
                "additionalProperties": False,
            }

        return {
            "type": "object",
            "title": section.title,
            "x-human-authored-required": section.human_authored_required,
            "properties": {
                "markdown_summary": {"type": "string", "minLength": 1},
                "human_authored_required": {
                    "type": "boolean",
                    "const": section.human_authored_required,
                },
            },
            "required": ["markdown_summary"],
            "additionalProperties": False,
        }

    @classmethod
    def compile_template(
        cls,
        template: ArtifactTemplateDefinition,
        *,
        variables: dict[str, str] | None = None,
        ontology_snapshot: ResolvedOntologySnapshot | None = None,
        instance: str | None = None,
    ) -> CompiledArtifactTemplate:
        """Compile `template` into its dual Human Markdown & Ontology-typed JSON Schema views."""
        if not template.sections:
            raise ValidationDomainError(
                detail_override="Le gabarit d'artefact doit comporter au moins une section.",
                instance=instance,
            )

        vars_map = variables or {}
        markdown_blocks: list[str] = [f"# {template.title} (`{template.version}`)"]
        all_chunks: list[CompiledMarkdownChunk] = []
        schema_properties: dict[str, Any] = {}
        required_sections: list[str] = []
        bound_terms: list[str] = []

        for section in template.sections:
            rendered_body = cls._interpolate_variables(
                section.markdown_body_template,
                vars_map,
                template.required_variables,
                instance=instance,
            )
            concept: OntologyConceptEntity | None = None
            if section.ontology_concept_term:
                if ontology_snapshot is None or (
                    section.ontology_concept_term not in ontology_snapshot.concepts_by_term
                ):
                    raise ValidationDomainError(
                        detail_override=(
                            f"Concept ontologique '{section.ontology_concept_term}' introuvable "
                            f"pour la section '{section.section_key}'."
                        ),
                        instance=instance,
                    )
                concept = ontology_snapshot.concepts_by_term[section.ontology_concept_term]
                if concept.canonical_term not in bound_terms:
                    bound_terms.append(concept.canonical_term)

            section_chunks = cls._split_into_cognitive_chunks(
                section, rendered_body, start_chunk_index=len(all_chunks)
            )
            all_chunks.extend(section_chunks)
            for chunk in section_chunks:
                markdown_blocks.append(chunk.markdown_content)

            schema_properties[section.section_key] = cls._build_section_schema(section, concept)
            if section.mandatory:
                required_sections.append(section.section_key)

        human_markdown = "\n\n---\n\n".join(markdown_blocks)
        agent_schema: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": template.uri,
            "title": template.title,
            "description": template.description,
            "type": "object",
            "x-template-key": template.template_key,
            "x-template-version": template.version,
            "x-bound-ontology-terms": bound_terms,
            "properties": schema_properties,
            "required": required_sections,
            "additionalProperties": False,
        }
        canonical = json.dumps(
            {
                "template_key": template.template_key,
                "uri": template.uri,
                "version": template.version,
                "human_markdown_view": human_markdown,
                "agent_json_schema": agent_schema,
            },
            sort_keys=True,
        )
        return CompiledArtifactTemplate(
            template_key=template.template_key,
            uri=template.uri,
            version=template.version,
            human_markdown_view=human_markdown,
            cognitive_chunks=tuple(all_chunks),
            agent_json_schema=agent_schema,
            bound_ontology_terms=tuple(bound_terms),
            sha256=compute_bytes_sha256(canonical.encode("utf-8")),
        )
