import React, { useState } from "react";

export type AssistantMainTabCode =
  | "ACTIVE_DISCUSSION"
  | "FOLDERS"
  | "HISTORY_SEARCH";

export type AssistantFolderVisibilityMode =
  | "PRIVATE"
  | "SHARED_SELECTED"
  | "WORKSPACE_OPEN";

export interface UiAssistantFolderItem {
  readonly folderId: string;
  readonly title: string;
  readonly pinnedNotesMarkdown: string;
  readonly consolidatedSummary: string;
  readonly visibilityMode: AssistantFolderVisibilityMode;
  readonly hasRestrictedSources: boolean;
  readonly assembledLayer5PromptBlock: string;
}

export interface UiAssistantHistoryHitItem {
  readonly itemId: string;
  readonly itemKind: "THREAD" | "FOLDER" | "ARTIFACT_CARD";
  readonly title: string;
  readonly snippet: string;
}

export interface AssistantFoldersAndCollaborativeThreadViewLabels {
  readonly tab1ActiveDiscussionTitle: string;
  readonly tab2FoldersTitlePrefix: string;
  readonly tab3HistorySearchTitle: string;
  readonly activeFolderPillPrefix: string;
  readonly pinnedNotesButtonLabel: string;
  readonly launchProcessFromFolderCta: string;
  readonly shareButtonLabel: string;
  readonly visibilityPrivateLabel: string;
  readonly visibilitySharedSelectedLabel: string;
  readonly visibilityWorkspaceOpenLabel: string;
  readonly restrictedSourcesWarningText: string;
  readonly searchPlaceholder: string;
}

export interface AssistantFoldersAndCollaborativeThreadViewProps {
  readonly workspaceId: string;
  readonly activeFolderId: string;
  readonly folders: readonly UiAssistantFolderItem[];
  readonly historyHits: readonly UiAssistantHistoryHitItem[];
  readonly activeTurnLockBanner?: string | null;
  readonly currentAuthorPassthroughIdentity: string;
  readonly labels: AssistantFoldersAndCollaborativeThreadViewLabels;
  readonly onSelectFolder?: (folderId: string) => void;
  readonly onUpdatePinnedNotes?: (folderId: string, notes: string) => void;
  readonly onLaunchProcessFromFolder?: (
    folderId: string,
    workflowUri: string,
  ) => void;
  readonly onChangeVisibility?: (
    folderId: string,
    mode: AssistantFolderVisibilityMode,
  ) => void;
  readonly onSendCollaborativeMessage?: (message: string) => void;
}

/**
 * Story 10.4 — Thematic `📁 Dossiers`, 3-Tab `Mon Assistant` Header (`💬 Discussion active`,
 * `📁 Dossiers (N)`, `🕘 Historique & Recherche`), Layer 5 Continuity (`📌 Notes du dossier`),
 * 1-Click Process Bridge (`☍ Lancer un Processus à partir de ce dossier →`), Collaborative
 * Sharing (`🔒 Privé | 👥 Partagé | 📦 Espace`) & Redis Turn Lock Banner (`✍️ {Prénom} interroge l'assistant...`).
 */
export function AssistantFoldersAndCollaborativeThreadView({
  workspaceId,
  activeFolderId,
  folders,
  historyHits,
  activeTurnLockBanner = null,
  currentAuthorPassthroughIdentity,
  labels,
  onSelectFolder,
  onUpdatePinnedNotes,
  onLaunchProcessFromFolder,
  onChangeVisibility,
  onSendCollaborativeMessage,
}: AssistantFoldersAndCollaborativeThreadViewProps): React.JSX.Element {
  const [activeTab, setActiveTab] =
    useState<AssistantMainTabCode>("ACTIVE_DISCUSSION");
  const [notesOpen, setNotesOpen] = useState<boolean>(false);
  const [shareModalOpen, setShareModalOpen] = useState<boolean>(false);
  const [draftNotes, setDraftNotes] = useState<string>(
    folders.find((f) => f.folderId === activeFolderId)?.pinnedNotesMarkdown ??
      "",
  );
  const [draftMessage, setDraftMessage] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const activeFolder =
    folders.find((f) => f.folderId === activeFolderId) ?? folders[0];

  const filteredHits = historyHits.filter(
    (h) =>
      !searchQuery.trim() ||
      h.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      h.snippet.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <section
      data-testid="assistant-folders-and-collaborative-thread-view"
      data-workspace-id={workspaceId}
      className="rounded-lg border border-border-subtle bg-surface-elevated p-4 text-text-primary space-y-3"
    >
      {/* 3-Tab Header: 💬 Discussion active | 📁 Dossiers (N) | 🕘 Historique & Recherche */}
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2.5">
        <div role="tablist" className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            role="tab"
            data-testid="assistant-main-tab-ACTIVE_DISCUSSION"
            aria-selected={activeTab === "ACTIVE_DISCUSSION"}
            onClick={() => setActiveTab("ACTIVE_DISCUSSION")}
            className={`rounded px-2.5 py-1 text-xs font-medium ${
              activeTab === "ACTIVE_DISCUSSION"
                ? "bg-action-primary text-white"
                : "bg-surface-secondary text-text-secondary"
            }`}
          >
            {labels.tab1ActiveDiscussionTitle}
          </button>
          <button
            type="button"
            role="tab"
            data-testid="assistant-main-tab-FOLDERS"
            aria-selected={activeTab === "FOLDERS"}
            onClick={() => setActiveTab("FOLDERS")}
            className={`rounded px-2.5 py-1 text-xs font-medium ${
              activeTab === "FOLDERS"
                ? "bg-action-primary text-white"
                : "bg-surface-secondary text-text-secondary"
            }`}
          >
            {labels.tab2FoldersTitlePrefix} ({folders.length})
          </button>
          <button
            type="button"
            role="tab"
            data-testid="assistant-main-tab-HISTORY_SEARCH"
            aria-selected={activeTab === "HISTORY_SEARCH"}
            onClick={() => setActiveTab("HISTORY_SEARCH")}
            className={`rounded px-2.5 py-1 text-xs font-medium ${
              activeTab === "HISTORY_SEARCH"
                ? "bg-action-primary text-white"
                : "bg-surface-secondary text-text-secondary"
            }`}
          >
            {labels.tab3HistorySearchTitle}
          </button>
        </div>

        {/* Active Folder Pill + 📌 Notes du dossier + 👥 Partager */}
        {activeFolder && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span
              data-testid="assistant-active-folder-pill"
              className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 text-xs font-medium"
            >
              {labels.activeFolderPillPrefix} : {activeFolder.title} ⌄
            </span>
            <button
              type="button"
              data-testid="assistant-folder-notes-toggle-btn"
              onClick={() => setNotesOpen((prev) => !prev)}
              className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 text-xs font-medium"
            >
              {labels.pinnedNotesButtonLabel}
            </button>
            <button
              type="button"
              data-testid="assistant-folder-share-modal-btn"
              onClick={() => setShareModalOpen((prev) => !prev)}
              className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 text-xs font-medium"
            >
              {labels.shareButtonLabel}
            </button>
          </div>
        )}
      </header>

      {/* Real-time Redis Turn Lock SSE indicator (`✍️ {Prénom} interroge l'assistant...`) */}
      {activeTurnLockBanner && (
        <div
          data-testid="assistant-redis-turn-lock-banner"
          role="status"
          aria-live="polite"
          className="rounded border border-status-warning/40 bg-status-warning/10 px-3 py-1.5 text-xs font-semibold text-status-warning"
        >
          {activeTurnLockBanner}
        </div>
      )}

      {/* Pinned Folder Notes Drawer (Couche 5 Memory Continuity) */}
      {notesOpen && activeFolder && (
        <div
          data-testid="assistant-folder-pinned-notes-drawer"
          className="rounded border border-border-subtle bg-surface-primary p-3 space-y-2"
        >
          <textarea
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="assistant-folder-pinned-notes-textarea"
            rows={2}
            value={draftNotes}
            onChange={(e) => setDraftNotes(e.target.value)}
            className="w-full rounded border border-border-subtle bg-surface-secondary px-2.5 py-1.5 text-xs"
          />
          <div className="flex items-center justify-between gap-2">
            <span
              data-testid="assistant-layer5-injected-preview"
              className="font-mono text-[11px] text-text-secondary"
            >
              {activeFolder.assembledLayer5PromptBlock}
            </span>
            <button
              type="button"
              data-testid="assistant-save-pinned-notes-btn"
              onClick={() =>
                onUpdatePinnedNotes?.(activeFolder.folderId, draftNotes)
              }
              className="rounded bg-action-primary px-2.5 py-1 text-xs font-semibold text-white"
            >
              Enregistrer les notes
            </button>
          </div>
        </div>
      )}

      {/* Collaborative Sharing Modal (`🔒 Privé | 👥 Partagé | 📦 Espace`) */}
      {shareModalOpen && activeFolder && (
        <div
          data-testid="assistant-folder-share-modal"
          className="rounded border border-border-subtle bg-surface-primary p-3 space-y-2"
        >
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="folder-visibility-btn-PRIVATE"
              onClick={() =>
                onChangeVisibility?.(activeFolder.folderId, "PRIVATE")
              }
              className="rounded border border-border-subtle bg-surface-secondary px-2.5 py-1 text-xs"
            >
              {labels.visibilityPrivateLabel}
            </button>
            <button
              type="button"
              data-testid="folder-visibility-btn-SHARED_SELECTED"
              onClick={() =>
                onChangeVisibility?.(activeFolder.folderId, "SHARED_SELECTED")
              }
              className="rounded border border-border-subtle bg-surface-secondary px-2.5 py-1 text-xs"
            >
              {labels.visibilitySharedSelectedLabel}
            </button>
            <button
              type="button"
              data-testid="folder-visibility-btn-WORKSPACE_OPEN"
              onClick={() =>
                onChangeVisibility?.(activeFolder.folderId, "WORKSPACE_OPEN")
              }
              className="rounded border border-border-subtle bg-surface-secondary px-2.5 py-1 text-xs"
            >
              {labels.visibilityWorkspaceOpenLabel}
            </button>
          </div>

          {activeFolder.hasRestrictedSources && (
            <p
              data-testid="assistant-share-restricted-sources-warning"
              className="rounded border border-status-warning/40 bg-status-warning/10 px-2.5 py-1 text-[11px] text-status-warning"
            >
              {labels.restrictedSourcesWarningText}
            </p>
          )}
        </div>
      )}

      {/* Tab 1: Active Discussion + 1-click Process Bridge */}
      {activeTab === "ACTIVE_DISCUSSION" && activeFolder && (
        <div
          data-testid="assistant-tab-panel-active-discussion"
          className="space-y-2.5"
        >
          <div className="flex items-center justify-between gap-2 text-[11px] text-text-secondary">
            <span data-testid="assistant-author-passthrough-badge">
              Identité Passthrough auteur :{" "}
              <code className="font-mono">{currentAuthorPassthroughIdentity}</code>
            </span>
            <button
              type="button"
              data-testid="assistant-launch-process-from-folder-btn"
              onClick={() =>
                onLaunchProcessFromFolder?.(
                  activeFolder.folderId,
                  "orcia://pack-sdlc/workflows/ticket-to-tech-spec",
                )
              }
              className="rounded bg-action-primary px-3 py-1 text-xs font-semibold text-white"
            >
              {labels.launchProcessFromFolderCta}
            </button>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="assistant-collaborative-message-input"
              value={draftMessage}
              onChange={(e) => setDraftMessage(e.target.value)}
              className="flex-1 rounded border border-border-subtle bg-surface-primary px-3 py-1.5 text-xs"
            />
            <button
              type="button"
              data-testid="assistant-collaborative-send-btn"
              onClick={() => {
                if (draftMessage.trim()) {
                  onSendCollaborativeMessage?.(draftMessage.trim());
                }
              }}
              className="rounded bg-action-primary px-3 py-1.5 text-xs font-semibold text-white"
            >
              Envoyer
            </button>
          </div>
        </div>
      )}

      {/* Tab 2: 📁 Dossiers (N) Grid */}
      {activeTab === "FOLDERS" && (
        <div
          data-testid="assistant-tab-panel-folders"
          className="grid grid-cols-1 gap-2 md:grid-cols-2"
        >
          {folders.map((folder) => (
            <div
              key={folder.folderId}
              data-testid={`assistant-folder-card-${folder.folderId}`}
              className="rounded border border-border-subtle bg-surface-primary p-3 space-y-1.5"
            >
              <div className="flex items-center justify-between gap-2">
                <button
                  type="button"
                  data-testid={`assistant-select-folder-btn-${folder.folderId}`}
                  onClick={() => onSelectFolder?.(folder.folderId)}
                  className="text-xs font-semibold hover:underline"
                >
                  📁 {folder.title}
                </button>
                <span className="rounded bg-surface-secondary px-1.5 py-0.5 font-mono text-[10px]">
                  {folder.visibilityMode}
                </span>
              </div>
              <p className="text-[11px] text-text-secondary">
                {folder.consolidatedSummary}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: 🕘 Historique & Recherche */}
      {activeTab === "HISTORY_SEARCH" && (
        <div
          data-testid="assistant-tab-panel-history-search"
          className="space-y-2"
        >
          <input
            type="search"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="assistant-history-search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={labels.searchPlaceholder}
            className="w-full rounded border border-border-subtle bg-surface-primary px-3 py-1.5 text-xs"
          />
          <ul
            data-testid="assistant-history-search-results"
            className="space-y-1"
          >
            {filteredHits.map((hit) => (
              <li
                key={hit.itemId}
                data-testid={`assistant-history-hit-${hit.itemId}`}
                className="rounded border border-border-subtle bg-surface-primary px-2.5 py-1.5 text-xs"
              >
                <span className="font-mono text-[10px] text-text-secondary mr-1.5">
                  [{hit.itemKind}]
                </span>
                <span className="font-semibold">{hit.title}</span> —{" "}
                <span className="text-text-secondary">{hit.snippet}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
