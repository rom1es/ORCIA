"""Story 10.4 — Thematic Folders (`📁 Dossiers`), Layer 5 Memory Continuity (`AD-15`),
Collaborative Sharing (`🔒 | 👥 | 📦`, `AD-21`) & Redis Turn Lock (`AD-4`, `AD-6`).

Implements:
- 3-tab `Mon Assistant` workspace overview (`💬 Discussion active`, `📁 Dossiers (N)`,
  `🕘 Historique & Recherche`).
- Automatic Layer 5 (`5_UTILISATEUR`) memory continuity injecting `📌 Notes du dossier`,
  working attachments (`@draft`), and consolidated summaries of previous threads in the folder.
- 1-click Process Bridge (`☍ Lancer un Processus à partir de ce dossier →`) pre-filling workflow
  contract inputs (defaulting to pilot workflow `orcia://pack-sdlc/workflows/ticket-to-tech-spec`).
- 3 visibility modes strictly confined to current Workspace members (`PRIVATE`, `SHARED_SELECTED`
  with `READ_ONLY` or `CO_CONTRIBUTOR`, `WORKSPACE_OPEN`) + preventive warning when restricted
  sources are cited in the folder.
- Lightweight Redis turn lock (`SET lock:thread:<thread_id> <user_id> NX EX 60`,
  `HTTP 409 ERR_THREAD_TURN_LOCK_HELD`) + real-time SSE indicator
  `✍️ {Prénom} interroge l'assistant...` + strict per-author `Passthrough` identity (`AD-6`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ThreadTurnLockHeldError,
    ValidationDomainError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

FolderVisibilityMode = Literal["PRIVATE", "SHARED_SELECTED", "WORKSPACE_OPEN"]
FolderAccessRole = Literal["READ_ONLY", "CO_CONTRIBUTOR"]
AssistantMainTab = Literal["ACTIVE_DISCUSSION", "FOLDERS", "HISTORY_SEARCH"]

PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI = "orcia://pack-sdlc/workflows/ticket-to-tech-spec"
THREAD_TURN_LOCK_TTL_SECONDS = 60


@dataclass(frozen=True)
class FolderShareGrant:
    """Per-colleague share grant inside the same Workspace (`READ_ONLY` or `CO_CONTRIBUTOR`)."""

    grantee_user_id: str
    access_role: FolderAccessRole


@dataclass(frozen=True)
class AssistantThreadSummary:
    """Discussion thread belonging to a thematic `📁 Dossier` (or standalone)."""

    thread_id: str
    workspace_id: str
    folder_id: str | None
    creator_user_id: str
    title: str
    thread_summary: str
    turn_count: int
    last_author_user_id: str | None
    last_author_passthrough_identity: str | None


@dataclass(frozen=True)
class AssistantFolderRecord:
    """Thematic `📁 Dossier` in `Mon Assistant` with Layer 5 continuity & sharing."""

    folder_id: str
    workspace_id: str
    owner_user_id: str
    title: str
    pinned_notes_markdown: str
    working_attachments_uris: tuple[str, ...]
    consolidated_summary: str
    evidence_tags: tuple[str, ...]
    has_restricted_sources: bool
    visibility_mode: FolderVisibilityMode
    shares: tuple[FolderShareGrant, ...] = ()


@dataclass(frozen=True)
class Layer5FolderMemoryInjection:
    """Layer 5 (`5_UTILISATEUR`) memory continuity payload injected by `AssistantHarness`."""

    folder_id: str
    folder_title: str
    layer_number: int
    layer_code: str
    pinned_notes_markdown: str
    working_attachments_uris: tuple[str, ...]
    previous_threads_summaries: tuple[str, ...]
    assembled_layer5_prompt_block: str


@dataclass(frozen=True)
class FolderWorkflowLaunchPreparation:
    """1-click `☍ Lancer un Processus à partir de ce dossier →` pre-filled contract."""

    folder_id: str
    workspace_id: str
    workflow_uri: str
    initiated_by_user_id: str
    passthrough_identity: str
    prefilled_contract_inputs: dict[str, object]


@dataclass(frozen=True)
class FolderSharingUpdateResult:
    """Outcome of updating a folder's visibility and colleague grants (`🔒 | 👥 | 📦`)."""

    folder_id: str
    workspace_id: str
    visibility_mode: FolderVisibilityMode
    shares: tuple[FolderShareGrant, ...]
    has_restricted_sources: bool
    restricted_sources_warning: str | None


@dataclass(frozen=True)
class CollaborativeThreadTurnResult:
    """Outcome of sending a message in a shared thread under Redis turn lock & `Passthrough`."""

    thread_id: str
    folder_id: str | None
    workspace_id: str
    redis_lock_key: str
    lock_holder_user_id: str
    lock_ttl_seconds: int
    sse_presence_banner: str
    author_user_id: str
    author_passthrough_identity: str
    folder_creator_user_id: str
    layer5_memory_injected: bool
    assembled_layer5_preview: str
    assistant_reply_markdown: str


@dataclass(frozen=True)
class AssistantHistorySearchHit:
    """Search hit in the 3rd tab `🕘 Historique & Recherche`."""

    item_id: str
    item_kind: Literal["THREAD", "FOLDER", "ARTIFACT_CARD"]
    title: str
    snippet: str
    folder_id: str | None


@dataclass(frozen=True)
class AssistantWorkspaceOverview:
    """3-tab overview for `Mon Assistant` (`💬`, `📁 Dossiers (N)`, `🕘 Historique`)."""

    workspace_id: str
    tabs: tuple[AssistantMainTab, AssistantMainTab, AssistantMainTab]
    active_folder_pill_label: str | None
    folders_count: int
    folders: tuple[AssistantFolderRecord, ...]
    threads: tuple[AssistantThreadSummary, ...]
    history_hits: tuple[AssistantHistorySearchHit, ...]


@dataclass
class _ActiveTurnLockEntry:
    holder_user_id: str
    expires_at_monotonic: float


class AssistantFoldersAndSharingService:
    """Domain service for Story 10.4 (`📁 Dossiers`, Layer 5 Memory, Sharing & Redis Turn Lock)."""

    def __init__(self) -> None:
        self._folders: dict[str, AssistantFolderRecord] = {}
        self._threads: dict[str, AssistantThreadSummary] = {}
        self._workspace_members: dict[str, set[str]] = {}
        self._turn_locks: dict[str, _ActiveTurnLockEntry] = {}

    @staticmethod
    def build_thread_lock_key(thread_id: str) -> str:
        """Return canonical Redis turn lock key `lock:thread:<thread_id>` (`AD-4`)."""
        return f"lock:thread:{thread_id}"

    @staticmethod
    def _ensure_not_observer(user: UserIdentity) -> None:
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(
                detail_override=(
                    "Les observateurs en lecture seule ne peuvent pas modifier un dossier ou "
                    "envoyer de message dans une discussion."
                )
            )

    def register_workspace_members(self, workspace_id: str, member_user_ids: list[str]) -> None:
        """Register explicit member user IDs for `workspace_id` confinement checks (`AD-21`)."""
        bucket = self._workspace_members.setdefault(workspace_id, set())
        bucket.update(member_user_ids)

    def create_or_update_folder(
        self,
        *,
        workspace_id: str,
        user: UserIdentity,
        title: str,
        pinned_notes_markdown: str = "",
        working_attachments_uris: list[str] | None = None,
        consolidated_summary: str = "",
        evidence_tags: list[str] | None = None,
        has_restricted_sources: bool = False,
        folder_id: str | None = None,
    ) -> AssistantFolderRecord:
        """Create or update a thematic `📁 Dossier` and its `📌 Notes du dossier`."""
        self._ensure_not_observer(user)
        clean_title = title.strip()
        if not clean_title:
            raise ValidationDomainError(
                detail_override="Le titre du dossier thématique ne peut pas être vide."
            )

        self.register_workspace_members(workspace_id, [user.id])
        resolved_folder_id = folder_id or new_uuid7_str()
        existing = self._folders.get(resolved_folder_id)

        record = AssistantFolderRecord(
            folder_id=resolved_folder_id,
            workspace_id=workspace_id,
            owner_user_id=existing.owner_user_id if existing is not None else user.id,
            title=clean_title,
            pinned_notes_markdown=pinned_notes_markdown.strip(),
            working_attachments_uris=tuple(working_attachments_uris or ()),
            consolidated_summary=consolidated_summary.strip(),
            evidence_tags=tuple(evidence_tags or ("S1",)),
            has_restricted_sources=has_restricted_sources,
            visibility_mode=existing.visibility_mode if existing is not None else "PRIVATE",
            shares=existing.shares if existing is not None else (),
        )
        self._folders[resolved_folder_id] = record
        return record

    def create_thread_in_folder(
        self,
        *,
        workspace_id: str,
        user: UserIdentity,
        title: str,
        folder_id: str | None = None,
        initial_summary: str = "",
        thread_id: str | None = None,
    ) -> AssistantThreadSummary:
        """Create a discussion thread inside a `📁 Dossier` (or standalone)."""
        self._ensure_not_observer(user)
        if folder_id is not None and folder_id not in self._folders:
            raise ResourceNotFoundError(detail_override=f"Dossier introuvable : {folder_id}")

        self.register_workspace_members(workspace_id, [user.id])
        resolved_thread_id = thread_id or new_uuid7_str()
        passthrough_id = f"passthrough:oidc:{user.id}:{user.email}"
        thread = AssistantThreadSummary(
            thread_id=resolved_thread_id,
            workspace_id=workspace_id,
            folder_id=folder_id,
            creator_user_id=user.id,
            title=title.strip() or "Nouvelle discussion",
            thread_summary=initial_summary.strip(),
            turn_count=1 if initial_summary.strip() else 0,
            last_author_user_id=user.id,
            last_author_passthrough_identity=passthrough_id,
        )
        self._threads[resolved_thread_id] = thread
        return thread

    def build_layer5_folder_memory_injection(
        self,
        *,
        workspace_id: str,
        folder_id: str,
    ) -> Layer5FolderMemoryInjection:
        """Assemble Layer 5 (`AD-15`) memory block from folder notes, attachments & past threads."""
        folder = self._folders.get(folder_id)
        if folder is None or folder.workspace_id != workspace_id:
            raise ResourceNotFoundError(
                detail_override=f"Dossier introuvable dans l'Espace {workspace_id} : {folder_id}"
            )

        folder_threads = [
            t.thread_summary
            for t in self._threads.values()
            if t.workspace_id == workspace_id and t.folder_id == folder_id and t.thread_summary
        ]
        if folder.consolidated_summary and folder.consolidated_summary not in folder_threads:
            folder_threads.insert(0, folder.consolidated_summary)

        attachments_str = (
            ", ".join(folder.working_attachments_uris)
            if folder.working_attachments_uris
            else "Aucune pièce jointe"
        )
        summaries_str = " | ".join(folder_threads) if folder_threads else "Aucun résumé précédent"
        block = (
            f"[LAYER_5_FOLDER_CONTINUITY folder={folder.title}]\n"
            f"📌 Notes du dossier : {folder.pinned_notes_markdown or 'Aucune note épinglée'}\n"
            f"📎 Livrables & pièces de travail : {attachments_str}\n"
            f"🧵 Résumés consolidés des discussions précédentes : {summaries_str}"
        )
        return Layer5FolderMemoryInjection(
            folder_id=folder.folder_id,
            folder_title=folder.title,
            layer_number=5,
            layer_code="5_UTILISATEUR",
            pinned_notes_markdown=folder.pinned_notes_markdown,
            working_attachments_uris=folder.working_attachments_uris,
            previous_threads_summaries=tuple(folder_threads),
            assembled_layer5_prompt_block=block,
        )

    def prepare_workflow_launch_from_folder(
        self,
        *,
        workspace_id: str,
        folder_id: str,
        user: UserIdentity,
        target_workflow_uri: str = PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI,
    ) -> FolderWorkflowLaunchPreparation:
        """Pre-fill a Process contract in 1 click from a thematic folder."""
        self._ensure_not_observer(user)
        memory = self.build_layer5_folder_memory_injection(
            workspace_id=workspace_id,
            folder_id=folder_id,
        )
        folder = self._folders[folder_id]
        passthrough_identity = f"passthrough:oidc:{user.id}:{user.email}"
        return FolderWorkflowLaunchPreparation(
            folder_id=folder.folder_id,
            workspace_id=workspace_id,
            workflow_uri=target_workflow_uri,
            initiated_by_user_id=user.id,
            passthrough_identity=passthrough_identity,
            prefilled_contract_inputs={
                "source_folder_id": folder.folder_id,
                "source_folder_title": folder.title,
                "pinned_decisions_markdown": folder.pinned_notes_markdown,
                "consolidated_threads_summary": " | ".join(memory.previous_threads_summaries),
                "working_attachments_uris": list(folder.working_attachments_uris),
                "cited_evidence_tags": list(folder.evidence_tags),
                "layer5_context_block": memory.assembled_layer5_prompt_block,
            },
        )

    def configure_folder_sharing(
        self,
        *,
        workspace_id: str,
        folder_id: str,
        owner_user: UserIdentity,
        visibility_mode: FolderVisibilityMode,
        shares: list[FolderShareGrant] | None = None,
        outside_workspace_user_ids: list[str] | None = None,
    ) -> FolderSharingUpdateResult:
        """Configure folder visibility (`🔒 | 👥 | 📦`) confined to Workspace."""
        self._ensure_not_observer(owner_user)
        folder = self._folders.get(folder_id)
        if folder is None or folder.workspace_id != workspace_id:
            raise ResourceNotFoundError(detail_override=f"Dossier introuvable : {folder_id}")

        if folder.owner_user_id != owner_user.id and owner_user.platform_role not in (
            "TEAM_LEAD",
            "BU_DIRECTOR",
            "PLATFORM_ADMIN",
        ):
            raise ScopeAccessDeniedError(
                detail_override=(
                    "Seul le propriétaire du dossier ou un responsable d'équipe peut "
                    "modifier son partage."
                )
            )

        outside_ids = set(outside_workspace_user_ids or ())
        resolved_shares = tuple(shares or ())
        known_members = self._workspace_members.get(workspace_id, set())

        for grant in resolved_shares:
            if grant.grantee_user_id in outside_ids or (
                known_members and grant.grantee_user_id not in known_members
            ):
                raise ScopeAccessDeniedError(
                    detail_override=(
                        f"Confinement à l'Espace ({workspace_id}) : impossible de partager un "
                        f"dossier avec l'utilisateur externe '{grant.grantee_user_id}' (AD-21)."
                    )
                )

        updated = AssistantFolderRecord(
            folder_id=folder.folder_id,
            workspace_id=folder.workspace_id,
            owner_user_id=folder.owner_user_id,
            title=folder.title,
            pinned_notes_markdown=folder.pinned_notes_markdown,
            working_attachments_uris=folder.working_attachments_uris,
            consolidated_summary=folder.consolidated_summary,
            evidence_tags=folder.evidence_tags,
            has_restricted_sources=folder.has_restricted_sources,
            visibility_mode=visibility_mode,
            shares=resolved_shares if visibility_mode == "SHARED_SELECTED" else (),
        )
        self._folders[folder_id] = updated

        warning: str | None = None
        if visibility_mode != "PRIVATE" and updated.has_restricted_sources:
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

    def acquire_thread_turn_lock(
        self,
        *,
        thread_id: str,
        user_id: str,
        ttl_seconds: int = THREAD_TURN_LOCK_TTL_SECONDS,
    ) -> str:
        """Acquire atomic turn lock `SET lock:thread:<thread_id> <user_id> NX EX 60` (`AD-4`)."""
        now = time.monotonic()
        existing = self._turn_locks.get(thread_id)
        if (
            existing is not None
            and existing.expires_at_monotonic > now
            and existing.holder_user_id != user_id
        ):
            raise ThreadTurnLockHeldError(
                detail_override=(
                    f"Verrou de tour Redis actif sur {self.build_thread_lock_key(thread_id)} "
                    f"(détenu par '{existing.holder_user_id}')."
                )
            )
        self._turn_locks[thread_id] = _ActiveTurnLockEntry(
            holder_user_id=user_id,
            expires_at_monotonic=now + ttl_seconds,
        )
        return self.build_thread_lock_key(thread_id)

    def release_thread_turn_lock(self, *, thread_id: str, user_id: str) -> None:
        """Release the turn lock if held by `user_id`."""
        existing = self._turn_locks.get(thread_id)
        if existing is not None and existing.holder_user_id == user_id:
            del self._turn_locks[thread_id]

    def send_collaborative_thread_turn(
        self,
        *,
        workspace_id: str,
        thread_id: str,
        sender_user: UserIdentity,
        message_text: str,
        release_lock_after_turn: bool = False,
    ) -> CollaborativeThreadTurnResult:
        """Execute a turn in a shared thread with Redis turn lock (`NX EX 60`)."""
        self._ensure_not_observer(sender_user)
        thread = self._threads.get(thread_id)
        if thread is None or thread.workspace_id != workspace_id:
            raise ResourceNotFoundError(detail_override=f"Discussion introuvable : {thread_id}")

        folder: AssistantFolderRecord | None = None
        if thread.folder_id is not None:
            folder = self._folders.get(thread.folder_id)
            if folder is not None and folder.owner_user_id != sender_user.id:
                if folder.visibility_mode == "PRIVATE":
                    raise ScopeAccessDeniedError(detail_override="Ce dossier est privé (🔒 Privé).")
                if folder.visibility_mode == "SHARED_SELECTED":
                    matching = next(
                        (s for s in folder.shares if s.grantee_user_id == sender_user.id),
                        None,
                    )
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

        lock_key = self.acquire_thread_turn_lock(
            thread_id=thread_id,
            user_id=sender_user.id,
            ttl_seconds=THREAD_TURN_LOCK_TTL_SECONDS,
        )

        first_name = (
            sender_user.display_name.split()[0] if sender_user.display_name else sender_user.id
        )
        sse_banner = f"✍️ {first_name} interroge l'assistant..."
        personal_passthrough = f"passthrough:oidc:{sender_user.id}:{sender_user.email}"

        layer5_preview = ""
        if folder is not None:
            layer5_injection = self.build_layer5_folder_memory_injection(
                workspace_id=workspace_id,
                folder_id=folder.folder_id,
            )
            layer5_preview = layer5_injection.assembled_layer5_prompt_block

        updated_thread = AssistantThreadSummary(
            thread_id=thread.thread_id,
            workspace_id=thread.workspace_id,
            folder_id=thread.folder_id,
            creator_user_id=thread.creator_user_id,
            title=thread.title,
            thread_summary=f"{thread.thread_summary} | {message_text.strip()}".strip(" |"),
            turn_count=thread.turn_count + 1,
            last_author_user_id=sender_user.id,
            last_author_passthrough_identity=personal_passthrough,
        )
        self._threads[thread_id] = updated_thread

        if release_lock_after_turn:
            self.release_thread_turn_lock(thread_id=thread_id, user_id=sender_user.id)

        folder_creator_id = folder.owner_user_id if folder is not None else thread.creator_user_id
        return CollaborativeThreadTurnResult(
            thread_id=thread_id,
            folder_id=thread.folder_id,
            workspace_id=workspace_id,
            redis_lock_key=lock_key,
            lock_holder_user_id=sender_user.id,
            lock_ttl_seconds=THREAD_TURN_LOCK_TTL_SECONDS,
            sse_presence_banner=sse_banner,
            author_user_id=sender_user.id,
            author_passthrough_identity=personal_passthrough,
            folder_creator_user_id=folder_creator_id,
            layer5_memory_injected=folder is not None,
            assembled_layer5_preview=layer5_preview,
            assistant_reply_markdown=(
                f"Réponse générée sous identité `{personal_passthrough}` avec continuité "
                f"Couche 5 (`{folder.title if folder else 'Sans dossier'}`) [S1]."
            ),
        )

    def get_workspace_overview(
        self,
        *,
        workspace_id: str,
        active_folder_id: str | None = None,
        search_query: str = "",
    ) -> AssistantWorkspaceOverview:
        """Return the 3-tab structure (`💬`, `📁 Dossiers (N)`, `🕘 Historique`)."""
        ws_folders = tuple(f for f in self._folders.values() if f.workspace_id == workspace_id)
        ws_threads = tuple(t for t in self._threads.values() if t.workspace_id == workspace_id)
        active_folder = (
            self._folders.get(active_folder_id)
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


__all__ = [
    "AssistantFolderRecord",
    "AssistantFoldersAndSharingService",
    "AssistantHistorySearchHit",
    "AssistantMainTab",
    "AssistantThreadSummary",
    "AssistantWorkspaceOverview",
    "CollaborativeThreadTurnResult",
    "FolderAccessRole",
    "FolderShareGrant",
    "FolderSharingUpdateResult",
    "FolderVisibilityMode",
    "FolderWorkflowLaunchPreparation",
    "Layer5FolderMemoryInjection",
    "PILOT_WORKFLOW_TICKET_TO_TECH_SPEC_URI",
    "THREAD_TURN_LOCK_TTL_SECONDS",
]
