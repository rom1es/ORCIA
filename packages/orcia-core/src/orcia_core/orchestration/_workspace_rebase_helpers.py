"""External Edit Rebaser (`Verrou V2`) & Pilot Workflow (`Verrou V3`) helpers (`Story 11.1`)."""

from __future__ import annotations

import hashlib
import os
import re
from typing import Literal
from uuid import UUID

from orcia_core.orchestration._workspace_governance_models import (
    SOVEREIGNTY_RANK,
    ExternalRebaseResult,
    PilotWorkflowRunResult,
    RebasedSectionChunk,
    ResolvedArtifactDestination,
    SovereigntyTier,
)
from orcia_core.orchestration.errors import (
    OrthogonalJudgeSovereigntyViolationError,
    PathTraversalDeniedError,
)


def enforce_local_realpath_confinement(*, local_uri: str, allowed_root: str) -> str:
    """Ensure `local://` destination stays within `allowed_root`."""
    rel_part = local_uri.removeprefix("local://").lstrip("/")
    root_real = os.path.realpath(allowed_root)
    candidate_real = os.path.realpath(os.path.join(root_real, rel_part))
    if candidate_real != root_real and not candidate_real.startswith(root_real + os.sep):
        raise PathTraversalDeniedError(
            detail_override=f"Destination '{local_uri}' escapes workspace root '{root_real}'."
        )
    return candidate_real


def resolve_artifact_destination_cascade(
    *,
    workspace_slug: str,
    artifact_type: str,
    artifact_slug: str,
    version: int,
    content_bytes: bytes,
    default_entry: tuple[str, str, str | None] | None,
    run_override_uri: str | None = None,
    workflow_step_target_uri: str | None = None,
    workspace_default_uri: str | None = None,
    local_root_realpath: str | None = None,
) -> ResolvedArtifactDestination:
    """Resolve the 4-level artifact destination cascade with `local://` confinement."""
    sha256_hex = hashlib.sha256(content_bytes).hexdigest()
    cas_storage_path = f"cas/{sha256_hex}"
    canonical_alias = (
        f"orcia://workspaces/{workspace_slug}/artifacts/{artifact_type}/{artifact_slug}@v{version}"
    )

    if run_override_uri:
        selected_level: Literal[
            "1_RUN_OVERRIDE",
            "2_WORKFLOW_STEP_TARGET",
            "3_WORKSPACE_DEFAULT",
            "4_ORCIA_VAULT_FALLBACK",
        ] = "1_RUN_OVERRIDE"
        raw_uri = run_override_uri
    elif workflow_step_target_uri:
        selected_level = "2_WORKFLOW_STEP_TARGET"
        raw_uri = workflow_step_target_uri
    elif workspace_default_uri or default_entry is not None:
        selected_level = "3_WORKSPACE_DEFAULT"
        raw_uri = workspace_default_uri or (default_entry[1] if default_entry else canonical_alias)
    else:
        selected_level = "4_ORCIA_VAULT_FALLBACK"
        raw_uri = canonical_alias

    if raw_uri.startswith("local://"):
        effective_root = local_root_realpath or (default_entry[2] if default_entry else None)
        enforce_local_realpath_confinement(
            local_uri=raw_uri,
            allowed_root=effective_root or "/tmp/orcia-workspaces",
        )

    staged = "://" in raw_uri and not raw_uri.startswith("orcia://")
    return ResolvedArtifactDestination(
        selected_level=selected_level,
        resolved_uri=raw_uri,
        cas_storage_path=cas_storage_path,
        canonical_alias_uri=canonical_alias,
        staged_for_gate_publication=staged,
    )


def split_markdown_sections(markdown_text: str) -> dict[str, tuple[str, str]]:
    """Split markdown document into slugged sections."""
    sections: dict[str, tuple[str, str]] = {}
    current_title = "Introduction"
    current_lines: list[str] = []
    for line in markdown_text.splitlines():
        if line.startswith("## ") or line.startswith("# "):
            if current_lines:
                slug = re.sub(r"[^a-z0-9]+", "-", current_title.lower()).strip("-") or "sec"
                sections[slug] = (current_title, "\n".join(current_lines).strip())
            current_title = line.lstrip("#").strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        slug = re.sub(r"[^a-z0-9]+", "-", current_title.lower()).strip("-") or "sec"
        sections[slug] = (current_title, "\n".join(current_lines).strip())
    return sections


def compute_external_rebase_result(
    *,
    artifact_uri: str,
    current_version: int,
    orcia_markdown: str,
    external_markdown: str,
    step_memlog_entries: list[str],
) -> ExternalRebaseResult:
    """Detect external `SHA-256` divergence and lock human-amended sections (`Verrou V2`)."""
    prev_sha = hashlib.sha256(orcia_markdown.encode("utf-8")).hexdigest()
    ext_sha = hashlib.sha256(external_markdown.encode("utf-8")).hexdigest()
    orcia_sections = split_markdown_sections(orcia_markdown)
    ext_sections = split_markdown_sections(external_markdown)

    if prev_sha == ext_sha:
        chunks = tuple(
            RebasedSectionChunk(
                chunk_key=key,
                section_title=title,
                content_markdown=body,
                status="APPROVED",
                locked_against_agent_overwrite=False,
            )
            for key, (title, body) in orcia_sections.items()
        )
        return ExternalRebaseResult(
            artifact_uri=artifact_uri,
            previous_version=current_version,
            imported_version=current_version,
            previous_sha256=prev_sha,
            external_sha256=ext_sha,
            divergence_detected=False,
            chunks=chunks,
            step_memlog_annotations=tuple(step_memlog_entries),
        )

    rebased_chunks: list[RebasedSectionChunk] = []
    amended_titles: list[str] = []
    for key, (ext_title, ext_body) in ext_sections.items():
        orig = orcia_sections.get(key)
        if orig is None or orig[1].strip() != ext_body.strip():
            rebased_chunks.append(
                RebasedSectionChunk(
                    chunk_key=key,
                    section_title=ext_title,
                    content_markdown=ext_body,
                    status="HUMAN_AMENDED_EXTERNAL",
                    locked_against_agent_overwrite=True,
                )
            )
            amended_titles.append(ext_title)
        else:
            rebased_chunks.append(
                RebasedSectionChunk(
                    chunk_key=key,
                    section_title=ext_title,
                    content_markdown=ext_body,
                    status="APPROVED",
                    locked_against_agent_overwrite=False,
                )
            )

    annotated_memlog = list(step_memlog_entries)
    for idx, entry in enumerate(annotated_memlog):
        if any(title.lower() in entry.lower() for title in amended_titles):
            annotated_memlog[idx] = f"[SUPERSEDED_BY_HUMAN_COMMIT] {entry}"
    if amended_titles and not any("[SUPERSEDED_BY_HUMAN_COMMIT]" in e for e in annotated_memlog):
        annotated_memlog.append(
            f"[SUPERSEDED_BY_HUMAN_COMMIT] External commit amended sections: "
            f"{', '.join(amended_titles)}"
        )

    return ExternalRebaseResult(
        artifact_uri=artifact_uri,
        previous_version=current_version,
        imported_version=current_version + 1,
        previous_sha256=prev_sha,
        external_sha256=ext_sha,
        divergence_detected=True,
        chunks=tuple(rebased_chunks),
        step_memlog_annotations=tuple(annotated_memlog),
    )


def build_pilot_ticket_to_tech_spec_result(
    *,
    workspace_id: UUID,
    workspace_slug: str,
    ticket_key: str,
    ticket_summary: str,
    workspace_sovereignty_tier: SovereigntyTier,
    generator_model_family: str,
    judge_model_family: str,
    judge_sovereignty_tier: SovereigntyTier,
    resolve_destination_fn: object,
    run_override_uri: str | None = None,
) -> PilotWorkflowRunResult:
    """Execute pilot workflow `ticket-to-tech-spec` (`Verrou V3`)."""
    del workspace_id, workspace_slug, run_override_uri
    judge_rank = SOVEREIGNTY_RANK[judge_sovereignty_tier]
    ws_rank = SOVEREIGNTY_RANK[workspace_sovereignty_tier]
    if judge_rank < ws_rank:
        raise OrthogonalJudgeSovereigntyViolationError(
            detail_override=(
                f"Judge tier '{judge_sovereignty_tier}' is less sovereign than workspace tier "
                f"'{workspace_sovereignty_tier}'."
            )
        )
    requires_human_anchor = (
        generator_model_family.strip().lower() == judge_model_family.strip().lower()
    )
    spec_markdown = (
        f"# Spécification Technique — {ticket_key}\n\n"
        f"## 1. Contexte & Périmètre\n{ticket_summary}\n\n"
        "## 2. Contrats d'Interface & Impacts\nValidation via Gate adaptative.\n"
    )
    destination: ResolvedArtifactDestination = resolve_destination_fn(spec_markdown.encode("utf-8"))  # type: ignore[operator]
    return PilotWorkflowRunResult(
        workflow_uri="orcia://pack-sdlc/workflows/ticket-to-tech-spec",
        ticket_key=ticket_key,
        executed_steps=(
            "1_extract_ticket_and_repo_context",
            "2_draft_tech_spec_and_impact_tree",
            "3_adaptive_human_gate_and_staged_publish",
        ),
        generator_model_family=generator_model_family,
        judge_model_family=judge_model_family,
        judge_sovereignty_tier=judge_sovereignty_tier,
        requires_human_anchor_card=requires_human_anchor,
        destination=destination,
        staged_transitions=(
            f"STAGE_PUBLISH:{destination.resolved_uri}",
            f"STAGE_TICKET_COMMENT:{ticket_key}",
        ),
    )
