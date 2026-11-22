"""PG18 Thread Messages Route & Persistence Helpers (`D4`, `H-18`, `Story 26.5`)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import (
    get_assistant_folders_and_sharing_service,
    get_assistant_thread_messages_repository,
)
from orcia_api.dependencies._assistant_guards import enforce_assistant_workspace_guard
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant import (
    AssistantThreadMessageSchemaItem,
    AssistantThreadMessagesListResponse,
)
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._assistant_folders_helpers import enforce_folder_turn_access
from orcia_core.orchestration.assistant_folders_and_sharing import AssistantFoldersAndSharingService
from orcia_core.orchestration.assistant_thread_messages import SqlAssistantThreadMessagesRepository
from orcia_core.orchestration.errors import ResourceNotFoundError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity

logger = get_logger("orcia.assistant.thread_messages")

thread_messages_router = APIRouter()
CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
FoldersSharingDep = Annotated[
    AssistantFoldersAndSharingService, Depends(get_assistant_folders_and_sharing_service)
]
ThreadMessagesRepoDep = Annotated[
    SqlAssistantThreadMessagesRepository, Depends(get_assistant_thread_messages_repository)
]


async def enforce_thread_read_acl(
    folders_svc: AssistantFoldersAndSharingService,
    *,
    workspace_id: str,
    thread_id: str,
    user: UserIdentity,
    instance: str,
) -> None:
    """Verify thread exists in `workspace_id` and `user` can read its folder if attached."""
    overview = await folders_svc.get_workspace_overview_async(workspace_id=workspace_id)
    folders_by_id = {f.folder_id: f for f in overview.folders}
    threads_by_id = {t.thread_id: t for t in overview.threads}
    target_thread = threads_by_id.get(thread_id)
    if target_thread is None:
        target_thread = getattr(folders_svc, "_threads", {}).get(thread_id)
    if target_thread is None:
        raise ResourceNotFoundError(
            detail_override=f"Thread '{thread_id}' not found in workspace '{workspace_id}'.",
            instance=instance,
        )
    if target_thread.folder_id:
        folder = folders_by_id.get(target_thread.folder_id) or getattr(
            folders_svc, "_folders", {}
        ).get(target_thread.folder_id)
        if folder is not None:
            if folder.owner_user_id == user.id:
                return
            if folder.visibility_mode == "PRIVATE":
                raise ScopeAccessDeniedError(instance=instance)
            if folder.visibility_mode == "SHARED_SELECTED" and not any(
                s.grantee_user_id == user.id for s in folder.shares
            ):
                raise ScopeAccessDeniedError(instance=instance)
            enforce_folder_turn_access(folder, user)


async def persist_thread_turn_messages(
    repo: SqlAssistantThreadMessagesRepository | None,
    *,
    thread_id: str | None,
    workspace_id: str,
    turn_id: str,
    parent_turn_id: str | None,
    user_prompt: str,
    assistant_reply: str,
    citation_map: dict[str, Any] | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """Persist `(user, assistant)` messages for a turn in `assistant_thread_messages`."""
    if repo is None or not thread_id or not thread_id.strip():
        return
    if not await repo.pg_tables_ready():
        return
    try:
        if user_prompt.strip():
            await repo.append_message(
                thread_id=thread_id,
                workspace_id=workspace_id,
                turn_id=turn_id,
                parent_turn_id=parent_turn_id,
                role="user",
                content=user_prompt,
                citation_map={},
                token_count=input_tokens if input_tokens > 0 else None,
            )
        if assistant_reply.strip():
            await repo.append_message(
                thread_id=thread_id,
                workspace_id=workspace_id,
                turn_id=turn_id,
                parent_turn_id=parent_turn_id,
                role="assistant",
                content=assistant_reply,
                citation_map=citation_map or {},
                token_count=output_tokens if output_tokens > 0 else None,
            )
    except Exception as exc:
        logger.warning(
            "assistant_thread_messages_persist_failed",
            thread_id=thread_id,
            turn_id=turn_id,
            error_type=type(exc).__name__,
        )


@thread_messages_router.get(
    "/threads/{thread_id}/messages",
    response_model=AssistantThreadMessagesListResponse,
)
async def list_assistant_thread_messages_endpoint(
    thread_id: str,
    request: Request,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
    messages_repo: ThreadMessagesRepoDep,
    workspace_id: str = Query(..., min_length=1),
    limit: int = Query(default=200, ge=1, le=500),
) -> AssistantThreadMessagesListResponse:
    """List persisted `user` and `assistant` messages for `thread_id` (`D4`, `H-18`)."""
    instance = str(request.url.path)
    await enforce_assistant_workspace_guard(request, user, workspace_id, require_write=False)
    await enforce_thread_read_acl(
        folders_svc,
        workspace_id=workspace_id,
        thread_id=thread_id,
        user=user,
        instance=instance,
    )
    records = await messages_repo.list_messages_for_thread(
        workspace_id=workspace_id,
        thread_id=thread_id,
        limit=limit,
    )
    return AssistantThreadMessagesListResponse(
        workspace_id=workspace_id,
        thread_id=thread_id,
        messages=[
            AssistantThreadMessageSchemaItem(
                message_id=m.message_id,
                thread_id=m.thread_id,
                workspace_id=m.workspace_id,
                turn_id=m.turn_id,
                parent_turn_id=m.parent_turn_id,
                role=m.role,
                content=m.content,
                citation_map=dict(m.citation_map),
                token_count=m.token_count,
                created_at=m.created_at,
            )
            for m in records
        ],
    )
