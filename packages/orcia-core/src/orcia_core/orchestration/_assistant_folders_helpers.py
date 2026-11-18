"""Pure helpers for Story 10.4 Assistant Folders, Layer 5 memory & sharing."""

from __future__ import annotations

import re

from orcia_core.orchestration._assistant_folders_models import (
    THREAD_TURN_LOCK_TTL_SECONDS,
    AssistantFolderRecord,
    AssistantHistorySearchHit,
    AssistantThreadSummary,
    AssistantWorkspaceOverview,
    CollaborativeThreadTurnResult,
    FolderShareGrant,
    FolderSharingUpdateResult,
    FolderWorkflowLaunchPreparation,
    Layer5FolderMemoryInjection,
)
from orcia_core.orchestration.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity

_LAYER5_MARKER_RE = re.compile(r"\[LAYER_5_[^\]]*\]\s*")


def sanitize_user_pinned_notes(raw_notes: str) -> str:
    """Ensure user-facing `pinned_notes_markdown` never leaks `[LAYER_5_*]` prompt tags."""
    return _LAYER5_MARKER_RE.sub("", raw_notes).strip()


def ensure_not_observer(user: UserIdentity) -> None:
    """Reject `OBSERVER` role mutations with `ObserverModeReadOnlyError`."""
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(
            detail_override=(
                "Les observateurs en lecture seule ne peuvent pas modifier un dossier ou "
                "envoyer de message dans une discussion."
            )
        )


def assemble_layer5_injection(
    folder: AssistantFolderRecord, folder_threads: list[str]
) -> Layer5FolderMemoryInjection:
    """Build internal `[LAYER_5_FOLDER_CONTINUITY ...]` prompt block for `AssistantHarness`."""
    if folder.consolidated_summary and folder.consolidated_summary not in folder_threads:
        folder_threads.insert(0, folder.consolidated_summary)
    attachments_str = (
        ", ".join(folder.working_attachments_uris)
        if folder.working_attachments_uris
        else "Aucune pièce jointe"
    )
    summaries_str = " | ".join(folder_threads) if folder_threads else "Aucun résumé précédent"
    clean_notes = sanitize_user_pinned_notes(folder.pinned_notes_markdown)
    block = (
        f"[LAYER_5_FOLDER_CONTINUITY folder={folder.title}]\n"
        f"📌 Notes du dossier : {clean_notes or 'Aucune note épinglée'}\n"
        f"📎 Livrables & pièces de travail : {attachments_str}\n"
        f"🧵 Résumés consolidés des discussions précédentes : {summaries_str}"
    )
    return Layer5FolderMemoryInjection(
        folder_id=folder.folder_id,
        folder_title=folder.title,
        layer_number=5,
        layer_code="5_UTILISATEUR",
        pinned_notes_markdown=clean_notes,
        working_attachments_uris=folder.working_attachments_uris,
        previous_threads_summaries=tuple(folder_threads),
        assembled_layer5_prompt_block=block,
    )


def make_launch_prep(
    folder: AssistantFolderRecord,
    memory: Layer5FolderMemoryInjection,
    user: UserIdentity,
    target_workflow_uri: str,
) -> FolderWorkflowLaunchPreparation:
    """Assemble pre-filled workflow contract launch preparation from a folder."""
    passthrough_identity = f"passthrough:oidc:{user.id}:{user.email}"
    return FolderWorkflowLaunchPreparation(
        folder_id=folder.folder_id,
        workspace_id=folder.workspace_id,
        workflow_uri=target_workflow_uri,
        initiated_by_user_id=user.id,
        passthrough_identity=passthrough_identity,
        prefilled_contract_inputs={
            "source_folder_id": folder.folder_id,
            "source_folder_title": folder.title,
            "pinned_decisions_markdown": memory.pinned_notes_markdown,
            "consolidated_threads_summary": " | ".join(memory.previous_threads_summaries),
            "working_attachments_uris": list(memory.working_attachments_uris),
            "cited_evidence_tags": list(folder.evidence_tags),
        },
    )


def validate_sharing_request(
    *,
    workspace_id: str,
    folder: AssistantFolderRecord,
    owner_user: UserIdentity,
    shares: tuple[FolderShareGrant, ...],
    outside_workspace_user_ids: list[str] | None,
    known_members: set[str],
) -> None:
    """Validate ownership/role and workspace confinement (`AD-21`) for folder sharing."""
    if folder.owner_user_id != owner_user.id and owner_user.platform_role not in (
        "TEAM_LEAD",
        "BU_DIRECTOR",
        "BU_LEAD",
        "PLATFORM_ADMIN",
    ):
        raise ScopeAccessDeniedError(
            detail_override=(
                "Seul le propriétaire du dossier ou un responsable d'équipe peut "
                "modifier son partage."
            )
        )
    outside_ids = set(outside_workspace_user_ids or ())
    for grant in shares:
        if grant.grantee_user_id in outside_ids or (
            known_members and grant.grantee_user_id not in known_members
        ):
            raise ScopeAccessDeniedError(
                detail_override=(
                    f"Confinement à l'Espace ({workspace_id}) : impossible de partager un "
                    f"dossier avec l'utilisateur externe '{grant.grantee_user_id}' (AD-21)."
                )
            )


def build_sharing_result(updated: AssistantFolderRecord) -> FolderSharingUpdateResult:
    """Build sharing update response with restricted-source masking notice when applicable."""
    warning: str | None = None
    if updated.visibility_mode != "PRIVATE" and updated.has_restricted_sources:
        warning = (
            "⚠️ Ce dossier cite des sources restreintes : leurs extraits seront "
            "automatiquement masqués ([🔒 Source restreinte — Demander l'accès]) "
            "pour les collègues non habilités."
        )
    return FolderSharingUpdateResult(
        folder_id=updated.folder_id,
        workspace_id=updated.workspace_id,
        visibility_mode=updated.visibility_mode,
        shares=updated.shares,
        has_restricted_sources=updated.has_restricted_sources,
        restricted_sources_warning=warning,
    )


def enforce_folder_turn_access(
    folder: AssistantFolderRecord | None, sender_user: UserIdentity
) -> None:
    """Enforce folder visibility & collaborator role before executing a thread turn."""
    if folder is None or folder.owner_user_id == sender_user.id:
        return
    if folder.visibility_mode == "PRIVATE":
        raise ScopeAccessDeniedError(detail_override="Ce dossier est privé (🔒 Privé).")
    if folder.visibility_mode == "SHARED_SELECTED":
        matching = next((s for s in folder.shares if s.grantee_user_id == sender_user.id), None)
        if matching is None:
            raise ScopeAccessDeniedError(
                detail_override="Vous n'avez pas accès à ce dossier partagé."
            )
        if matching.access_role == "READ_ONLY":
            raise ObserverModeReadOnlyError(
                detail_override=(
                    "Accès en 👁️ Lecture seule sur ce dossier partagé : "
                    "seul un ✍️ Co-contributeur peut interroger l'assistant."
                )
            )


def build_turn_result(
    *,
    thread: AssistantThreadSummary,
    folder: AssistantFolderRecord | None,
    workspace_id: str,
    sender_user: UserIdentity,
    lock_key: str,
    personal_passthrough: str,
) -> CollaborativeThreadTurnResult:
    """Build `CollaborativeThreadTurnResult` without leaking `[LAYER_5_*]` tags."""
    first_name = sender_user.display_name.split()[0] if sender_user.display_name else sender_user.id
    folder_creator_id = folder.owner_user_id if folder is not None else thread.creator_user_id
    return CollaborativeThreadTurnResult(
        thread_id=thread.thread_id,
        folder_id=thread.folder_id,
        workspace_id=workspace_id,
        redis_lock_key=lock_key,
        lock_holder_user_id=sender_user.id,
        lock_ttl_seconds=THREAD_TURN_LOCK_TTL_SECONDS,
        sse_presence_banner=f"✍️ {first_name} interroge l'assistant...",
        author_user_id=sender_user.id,
        author_passthrough_identity=personal_passthrough,
        folder_creator_user_id=folder_creator_id,
        layer5_memory_injected=folder is not None,
        assembled_layer5_preview="",
        assistant_reply_markdown=(
            f"Réponse générée sous identité `{personal_passthrough}` avec continuité "
            f"Couche 5 (`{folder.title if folder else 'Sans dossier'}`) [S1]."
        ),
    )


def assemble_overview(
    *,
    workspace_id: str,
    ws_folders: tuple[AssistantFolderRecord, ...],
    ws_threads: tuple[AssistantThreadSummary, ...],
    active_folder_id: str | None,
    search_query: str,
) -> AssistantWorkspaceOverview:
    """Assemble the 3-tab Assistant overview and filtered history hits."""
    active_folder = (
        next((f for f in ws_folders if f.folder_id == active_folder_id), None)
        if active_folder_id is not None
        else (ws_folders[0] if ws_folders else None)
    )
    pill_label = f"📁 Dossier : {active_folder.title} ⌄" if active_folder is not None else None
    q = search_query.strip().lower()
    hits: list[AssistantHistorySearchHit] = []
    for f in ws_folders:
        if not q or q in f.title.lower() or q in f.pinned_notes_markdown.lower():
            hits.append(
                AssistantHistorySearchHit(
                    item_id=f.folder_id,
                    item_kind="FOLDER",
                    title=f.title,
                    snippet=f.pinned_notes_markdown or f.consolidated_summary,
                    folder_id=f.folder_id,
                )
            )
    for t in ws_threads:
        if not q or q in t.title.lower() or q in t.thread_summary.lower():
            hits.append(
                AssistantHistorySearchHit(
                    item_id=t.thread_id,
                    item_kind="THREAD",
                    title=t.title,
                    snippet=t.thread_summary,
                    folder_id=t.folder_id,
                )
            )
    return AssistantWorkspaceOverview(
        workspace_id=workspace_id,
        tabs=("ACTIVE_DISCUSSION", "FOLDERS", "HISTORY_SEARCH"),
        active_folder_pill_label=pill_label,
        folders_count=len(ws_folders),
        folders=ws_folders,
        threads=ws_threads,
        history_hits=tuple(hits),
    )
