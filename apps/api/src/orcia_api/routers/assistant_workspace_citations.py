"""Epic 10 Sub-Router — Deterministic Citations & Verrou V5 Guard (`Story 10.3`, `Story 26.1`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from orcia_api.dependencies import get_assistant_citation_and_v5_guard_service
from orcia_api.dependencies._assistant_guards import (
    enforce_assistant_workspace_guard,
    resolve_server_allowed_source_uris,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant_citations_and_folders import (
    ArtifactCardActionRequest,
    ArtifactCardActionResponse,
    EvidenceGlossaryCitationSchemaItem,
    EvidenceSourceCitationSchemaItem,
    EvidenceToolCitationSchemaItem,
    VerifyAndFilterCitationsRequest,
    VerifyAndFilterCitationsResponse,
)
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
    RawGlossaryCandidate,
    RawSourceCandidate,
    RawToolOutputCandidate,
)
from orcia_core.permissions.models import UserIdentity

router = APIRouter()

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
CitationGuardDep = Annotated[
    AssistantCitationAndV5GuardService, Depends(get_assistant_citation_and_v5_guard_service)
]


@router.post("/citations/verify-turn", response_model=VerifyAndFilterCitationsResponse)
async def verify_and_filter_citations_endpoint(
    payload: VerifyAndFilterCitationsRequest,
    request: Request,
    user: CurrentUserDep,
    citation_svc: CitationGuardDep,
) -> VerifyAndFilterCitationsResponse:
    """Build Evidence Table (`REFERENCE > ACTIVE`), enforce `READ_SOURCE` & strip phantom tags."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    table = citation_svc.build_evidence_table(
        sources=tuple(
            RawSourceCandidate(
                uri=s.uri,
                title=s.title,
                authority_tier=s.authority_tier,
                freshness=s.freshness,
                snippet=s.snippet,
                line_start=s.line_start,
                line_end=s.line_end,
                relevance_score=s.relevance_score,
            )
            for s in payload.sources
        ),
        glossary_items=tuple(
            RawGlossaryCandidate(
                term_or_axiom_id=g.term_or_axiom_id,
                label=g.label,
                ontology_level=g.ontology_level,
                definition=g.definition,
            )
            for g in payload.glossary_items
        ),
        tool_outputs=tuple(
            RawToolOutputCandidate(
                tool_name=t.tool_name,
                connector_uri=t.connector_uri,
                summary=t.summary,
            )
            for t in payload.tool_outputs
        ),
    )
    allowed_uris = await resolve_server_allowed_source_uris(
        request,
        user,
        workspace_id=payload.workspace_id,
        candidate_uris=tuple(s.uri for s in table.sources),
    )
    table = citation_svc.filter_citation_map_for_reader(
        user,
        evidence_table=table,
        reader_allowed_source_uris=allowed_uris,
    )
    verified = await citation_svc.verify_and_sanitize_citations_async(
        response_text=payload.response_text,
        evidence_table=table,
        workspace_id=payload.workspace_id,
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        trace_id=str(getattr(getattr(request, "state", None), "trace_id", "") or "") or None,
    )
    return VerifyAndFilterCitationsResponse(
        sanitized_text=verified.sanitized_text,
        valid_tags=list(verified.valid_tags),
        stripped_phantom_tags=list(verified.stripped_phantom_tags),
        verification_duration_ms=verified.verification_duration_ms,
        audit_id=verified.audit_entry.audit_id if verified.audit_entry is not None else None,
        sources=[
            EvidenceSourceCitationSchemaItem(
                tag=s.tag,
                index=s.index,
                uri=s.uri,
                title=s.title,
                authority_tier=s.authority_tier,
                freshness=s.freshness,
                snippet=s.snippet,
                line_start=s.line_start,
                line_end=s.line_end,
                restricted_access=s.restricted_access,
                display_pill=s.display_pill,
                request_access_uri=s.request_access_uri,
            )
            for s in table.sources
        ],
        glossary_items=[
            EvidenceGlossaryCitationSchemaItem(
                tag=g.tag,
                index=g.index,
                term_or_axiom_id=g.term_or_axiom_id,
                label=g.label,
                ontology_level=g.ontology_level,
                definition=g.definition,
            )
            for g in table.glossary_items
        ],
        tool_outputs=[
            EvidenceToolCitationSchemaItem(
                tag=t.tag,
                index=t.index,
                tool_name=t.tool_name,
                connector_uri=t.connector_uri,
                summary=t.summary,
            )
            for t in table.tool_outputs
        ],
        footer_summary_line=table.footer_summary_line,
        citation_map_emitted_at_ms=table.citation_map_emitted_at_ms,
    )


@router.post("/artifacts/action", response_model=ArtifactCardActionResponse)
async def execute_artifact_card_action_endpoint(
    payload: ArtifactCardActionRequest,
    request: Request,
    user: CurrentUserDep,
    citation_svc: CitationGuardDep,
) -> ArtifactCardActionResponse:
    """Execute a Structured Artifact Card action, enforcing scope & Verrou V5 (`AD-15`)."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    outcome = citation_svc.execute_artifact_card_action(
        user,
        workspace_id=payload.workspace_id,
        action_type=payload.action_type,
        artifact_title=payload.artifact_title,
        artifact_content=payload.artifact_content,
        cited_tags=tuple(payload.cited_tags),
        target_uri=payload.target_uri,
    )
    return ArtifactCardActionResponse(
        action_id=outcome.action_id,
        workspace_id=outcome.workspace_id,
        action_type=outcome.action_type,
        artifact_title=outcome.artifact_title,
        artifact_version_tag=outcome.artifact_version_tag,
        draft_uri=outcome.draft_uri,
        process_launch_prefill=outcome.process_launch_prefill,
    )
