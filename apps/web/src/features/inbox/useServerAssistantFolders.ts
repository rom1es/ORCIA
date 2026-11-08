import { createOrciaApiClient } from "@orcia/api-client";
import type { AssistantFolderVisibilityMode, UiAssistantFolderItem } from "@orcia/ui";
import { useCallback, useEffect, useState } from "react";
import { readSavedAssistantFolders, writeSavedAssistantFolders } from "./assistantFoldersAndPrefsStore";

interface ServerFolderPayload {
  readonly folder_id: string;
  readonly title: string;
  readonly pinned_notes_markdown?: string;
  readonly consolidated_summary?: string;
  readonly visibility_mode?: string;
  readonly has_restricted_sources?: boolean;
  readonly assembled_layer5_prompt_block?: string;
}

const VISIBILITY_MODES: readonly AssistantFolderVisibilityMode[] = ["PRIVATE", "SHARED_SELECTED", "WORKSPACE_OPEN"];

export function mapServerFolder(payload: ServerFolderPayload): UiAssistantFolderItem {
  const visibility = VISIBILITY_MODES.find((m) => m === payload.visibility_mode) ?? "PRIVATE";
  return {
    folderId: payload.folder_id,
    title: payload.title,
    pinnedNotesMarkdown: payload.pinned_notes_markdown ?? "",
    consolidatedSummary: payload.consolidated_summary ?? "",
    visibilityMode: visibility,
    hasRestrictedSources: payload.has_restricted_sources ?? false,
    assembledLayer5PromptBlock: payload.assembled_layer5_prompt_block ?? "",
  };
}

function errorDetail(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export interface ServerAssistantFoldersMessages {
  readonly workspaceRequired: string;
  readonly loadFailed: (detail: string) => string;
  readonly saveFailed: (detail: string) => string;
}

/**
 * Dossiers de Mon Assistant : le serveur est la source de vérité (BUG-E2E-01).
 *
 * - réhydratation par `GET /api/v1/assistant/workspaces/{id}/overview` à chaque changement d'espace,
 *   y compris après un vrai F5 avec un localStorage vidé ;
 * - création / notes / visibilité envoyées à l'API, l'état local n'est mis à jour qu'avec la réponse
 *   (identifiant serveur, jamais d'identifiant fabriqué côté client) ;
 * - aucun espace de repli fictif : sans espace actif, la création est refusée explicitement ;
 * - toute erreur est remontée via `onFeedback` (zéro `.catch` silencieux, garde-fou n°5).
 */
export function useServerAssistantFolders(params: {
  readonly workspaceId: string;
  readonly messages: ServerAssistantFoldersMessages;
  readonly onFeedback: (message: string) => void;
}) {
  const { workspaceId, messages, onFeedback } = params;
  const [folders, setFolders] = useState<readonly UiAssistantFolderItem[]>(() => readSavedAssistantFolders());

  const applyFolders = useCallback((next: readonly UiAssistantFolderItem[]) => {
    setFolders(next);
    writeSavedAssistantFolders(next);
  }, []);

  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;
    createOrciaApiClient({ baseUrl: "" })
      .listAssistantFolders(workspaceId)
      .then((overview) => {
        if (!cancelled) applyFolders(overview.folders.map(mapServerFolder));
      })
      .catch((err: unknown) => {
        if (!cancelled) onFeedback(messages.loadFailed(errorDetail(err)));
      });
    return () => {
      cancelled = true;
    };
    // `messages` / `onFeedback` sont des libellés et callbacks d'affichage : seul l'espace déclenche le rechargement.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, applyFolders]);

  const upsertFromServer = useCallback(
    (saved: UiAssistantFolderItem) => {
      setFolders((prev) => {
        const exists = prev.some((f) => f.folderId === saved.folderId);
        const next = exists ? prev.map((f) => (f.folderId === saved.folderId ? saved : f)) : [...prev, saved];
        writeSavedAssistantFolders(next);
        return next;
      });
    },
    [],
  );

  const createFolder = useCallback(
    async (title: string): Promise<UiAssistantFolderItem | null> => {
      if (!workspaceId) {
        onFeedback(messages.workspaceRequired);
        return null;
      }
      try {
        const saved = mapServerFolder(
          await createOrciaApiClient({ baseUrl: "" }).createAssistantFolder({ workspace_id: workspaceId, title }),
        );
        upsertFromServer(saved);
        return saved;
      } catch (err: unknown) {
        onFeedback(messages.saveFailed(errorDetail(err)));
        return null;
      }
    },
    [workspaceId, messages, onFeedback, upsertFromServer],
  );

  const savePinnedNotes = useCallback(
    async (folder: UiAssistantFolderItem, notes: string): Promise<boolean> => {
      try {
        const saved = mapServerFolder(
          await createOrciaApiClient({ baseUrl: "" }).createAssistantFolder({
            workspace_id: workspaceId,
            folder_id: folder.folderId,
            title: folder.title,
            pinned_notes_markdown: notes,
            consolidated_summary: folder.consolidatedSummary,
            has_restricted_sources: folder.hasRestrictedSources,
          }),
        );
        upsertFromServer({ ...saved, visibilityMode: folder.visibilityMode });
        return true;
      } catch (err: unknown) {
        onFeedback(messages.saveFailed(errorDetail(err)));
        return false;
      }
    },
    [workspaceId, messages, onFeedback, upsertFromServer],
  );

  const changeVisibility = useCallback(
    async (folder: UiAssistantFolderItem, mode: AssistantFolderVisibilityMode): Promise<boolean> => {
      try {
        const outcome = await createOrciaApiClient({ baseUrl: "" }).configureAssistantFolderSharing(folder.folderId, {
          workspace_id: workspaceId,
          visibility_mode: mode,
        });
        upsertFromServer({ ...folder, visibilityMode: mapServerFolder({ ...outcome, title: folder.title }).visibilityMode });
        return true;
      } catch (err: unknown) {
        onFeedback(messages.saveFailed(errorDetail(err)));
        return false;
      }
    },
    [workspaceId, messages, onFeedback, upsertFromServer],
  );

  return { folders, createFolder, savePinnedNotes, changeVisibility };
}
