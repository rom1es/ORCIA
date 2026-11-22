"""SQL statement constants for `assistant_folders`, `assistant_threads` & shares (`<= 300 L`)."""

from __future__ import annotations

import sqlalchemy as sa

SQL_UPSERT_FOLDER = sa.text(
    """
    INSERT INTO assistant_folders (
        folder_id, workspace_id, owner_user_id, title,
        pinned_notes_markdown, visibility_mode,
        consolidated_summary, has_restricted_sources,
        working_attachments_uris, evidence_tags
    ) VALUES (
        CAST(:folder_id AS uuid), CAST(:workspace_id AS uuid),
        CAST(:owner_user_id AS uuid), :title,
        :pinned_notes_markdown, :visibility_mode,
        :consolidated_summary, :has_restricted_sources,
        CAST(:working_attachments_uris AS jsonb), CAST(:evidence_tags AS text[])
    )
    ON CONFLICT (folder_id) DO UPDATE SET
        title = EXCLUDED.title,
        pinned_notes_markdown = EXCLUDED.pinned_notes_markdown,
        consolidated_summary = EXCLUDED.consolidated_summary,
        has_restricted_sources = EXCLUDED.has_restricted_sources,
        working_attachments_uris = EXCLUDED.working_attachments_uris,
        evidence_tags = EXCLUDED.evidence_tags,
        updated_at = NOW()
    RETURNING folder_id, workspace_id, owner_user_id, title,
              pinned_notes_markdown, visibility_mode,
              consolidated_summary, has_restricted_sources,
              working_attachments_uris, evidence_tags
    """
)

SQL_UPSERT_THREAD = sa.text(
    """
    INSERT INTO assistant_threads (
        thread_id, workspace_id, folder_id, creator_user_id,
        title, thread_summary, turn_count,
        last_author_user_id, last_author_passthrough_identity
    ) VALUES (
        CAST(:thread_id AS uuid), CAST(:workspace_id AS uuid),
        CAST(:folder_id AS uuid), CAST(:creator_user_id AS uuid),
        :title, :thread_summary, :turn_count,
        CAST(:last_author_user_id AS uuid), :last_author_passthrough_identity
    )
    ON CONFLICT (thread_id) DO UPDATE SET
        title = EXCLUDED.title,
        thread_summary = EXCLUDED.thread_summary,
        turn_count = EXCLUDED.turn_count,
        last_author_user_id = EXCLUDED.last_author_user_id,
        last_author_passthrough_identity = EXCLUDED.last_author_passthrough_identity,
        updated_at = NOW()
    RETURNING thread_id, workspace_id, folder_id, creator_user_id,
              title, thread_summary, turn_count,
              last_author_user_id, last_author_passthrough_identity
    """
)

SQL_UPDATE_THREAD_TURN = sa.text(
    """
    UPDATE assistant_threads
       SET thread_summary = :thread_summary,
           turn_count = :turn_count,
           last_author_user_id = CAST(:author_id AS uuid),
           last_author_passthrough_identity = :passthrough_id,
           updated_at = NOW()
     WHERE thread_id = CAST(:thread_id AS uuid)
       AND workspace_id = CAST(:workspace_id AS uuid)
    RETURNING thread_id, workspace_id, folder_id, creator_user_id,
              title, thread_summary, turn_count,
              last_author_user_id, last_author_passthrough_identity
    """
)

SQL_UPSERT_SHARE = sa.text(
    """
    INSERT INTO assistant_folder_shares (
        share_id, folder_id, workspace_id, grantee_user_id, access_role
    ) VALUES (
        CAST(:share_id AS uuid), CAST(:folder_id AS uuid),
        CAST(:workspace_id AS uuid), CAST(:grantee_user_id AS uuid), :access_role
    )
    ON CONFLICT (folder_id, grantee_user_id) DO UPDATE SET
        access_role = EXCLUDED.access_role
    """
)
