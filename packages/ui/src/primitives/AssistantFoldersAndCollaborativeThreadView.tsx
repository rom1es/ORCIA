import React, { useEffect, useState } from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { OrciaIcon, getOrciaIconGlyph } from "../components/icons";

export type AssistantMainTabCode = "ACTIVE_DISCUSSION" | "FOLDERS" | "HISTORY_SEARCH";
export type AssistantFolderVisibilityMode = "PRIVATE" | "SHARED_SELECTED" | "WORKSPACE_OPEN";

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
  readonly defaultNotesOpen?: boolean;
  readonly onSelectFolder?: (folderId: string) => void;
  readonly onUpdatePinnedNotes?: (folderId: string, notes: string) => void;
  readonly onLaunchProcessFromFolder?: (folderId: string, workflowUri: string) => void;
  readonly onChangeVisibility?: (folderId: string, mode: AssistantFolderVisibilityMode) => void;
  readonly onSendCollaborativeMessage?: (message: string) => void;
  readonly onCreateFolder?: (title: string) => void;
  readonly onOpenHelpSection?: (sectionId: string) => void;
}

export function formatFolderVisibilityLabel(mode: AssistantFolderVisibilityMode, isFr = true): string {
  if (mode === "SHARED_SELECTED") {
    return isFr
      ? `${getOrciaIconGlyph("team")} Partagé (Membres choisis)`
      : `${getOrciaIconGlyph("team")} Shared (Selected members)`;
  }
  if (mode === "WORKSPACE_OPEN") {
    return isFr
      ? `${getOrciaIconGlyph("spaces")} Visible par tout l'Espace`
      : `${getOrciaIconGlyph("spaces")} Open to entire Workspace`;
  }
  return isFr
    ? `${getOrciaIconGlyph("lock")} Privé (Moi uniquement)`
    : `${getOrciaIconGlyph("lock")} Private (Only me)`;
}

export function AssistantFoldersAndCollaborativeThreadView({
  workspaceId,
  activeFolderId,
  folders,
  historyHits,
  activeTurnLockBanner = null,
  currentAuthorPassthroughIdentity,
  labels,
  defaultNotesOpen = false,
  onSelectFolder,
  onUpdatePinnedNotes,
  onLaunchProcessFromFolder,
  onChangeVisibility,
  onSendCollaborativeMessage,
  onCreateFolder,
  onOpenHelpSection,
}: AssistantFoldersAndCollaborativeThreadViewProps): React.JSX.Element {
  const [activeTab, setActiveTab] = useState<AssistantMainTabCode>("ACTIVE_DISCUSSION");
  const [notesOpen, setNotesOpen] = useState<boolean>(defaultNotesOpen);
  const [shareModalOpen, setShareModalOpen] = useState<boolean>(false);
  const activeFolder = folders.find((f) => f.folderId === activeFolderId) ?? folders[0];
  const [draftNotes, setDraftNotes] = useState<string>(activeFolder?.pinnedNotesMarkdown ?? "");
  const [draftMessage, setDraftMessage] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [newFolderTitle, setNewFolderTitle] = useState<string>("");
  const [notesSavedBadge, setNotesSavedBadge] = useState<boolean>(false);

  const isFr = !labels.searchPlaceholder.toLowerCase().includes("search");
  const cleanPillPrefix = labels.activeFolderPillPrefix.replace(/\s*:\s*$/, "").trim();

  useEffect(() => {
    setDraftNotes(activeFolder?.pinnedNotesMarkdown ?? "");
  }, [activeFolder?.folderId, activeFolder?.pinnedNotesMarkdown]);

  const filteredHits = historyHits.filter(
    (h) => !searchQuery.trim() || h.title.toLowerCase().includes(searchQuery.toLowerCase()) || h.snippet.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <section
      data-testid="assistant-folders-and-collaborative-thread-view"
      data-workspace-id={workspaceId}
      className="rounded-lg border border-border-subtle bg-surface-elevated p-4 text-text-primary space-y-3"
    >
      <div data-testid="assistant-folders-and-notes-explainer" className="rounded-lg border border-border-subtle bg-surface-primary p-3 text-xs space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-text-primary">
            {isFr ? (
              <>
                <OrciaIcon name="folder" /> Dossiers thématiques &amp; <OrciaIcon name="pin" /> Notes permanentes (Mémoire de Mon Assistant)
              </>
            ) : (
              <>
                <OrciaIcon name="folder" /> Thematic Folders &amp; <OrciaIcon name="pin" /> Pinned Notes (My Assistant Memory)
              </>
            )}
          </span>
          {onOpenHelpSection && (
            <ContextualInfoTriggerButton
              sectionId="assistant-folders"
              label={isFr ? "Comprendre comment les dossiers et les notes enrichissent automatiquement vos questions" : "Understand how folders and notes automatically enrich your questions"}
              onOpenHelpSection={onOpenHelpSection}
            />
          )}
        </div>
        <p className="text-[11px] text-text-secondary leading-relaxed">
          {isFr
            ? "1) Un Dossier regroupe vos échanges par sujet. Lorsqu'il est sélectionné comme Dossier actif, vos nouvelles questions y sont rattachées. 2) Les Notes du dossier servent de mémo permanent : elles sont transmises automatiquement à Mon Assistant à chaque question posée dans ce dossier."
            : "1) A Folder groups your threads by topic. When selected as the Active Folder, new questions are attached to it. 2) Folder Notes act as a permanent memo: they are automatically sent to My Assistant with every question asked in this folder."}
        </p>
      </div>

      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2.5">
        <div role="tablist" style={{ display: "none" }} className="sr-only">
          {([["ACTIVE_DISCUSSION", labels.tab1ActiveDiscussionTitle], ["FOLDERS", `${labels.tab2FoldersTitlePrefix} (${folders.length})`], ["HISTORY_SEARCH", labels.tab3HistorySearchTitle]] as const).map(([code, title]) => (
            <button key={code} type="button" role="tab" data-testid={`assistant-main-tab-${code}`} aria-selected={activeTab === code} onClick={() => setActiveTab(code)}>{title}</button>
          ))}
        </div>

        {activeFolder ? (
          <div className="flex flex-wrap items-center gap-2">
            <span data-testid="assistant-active-folder-pill" className="rounded-full border border-action-primary/40 bg-action-primary/10 px-2.5 py-0.5 text-xs font-semibold text-action-primary">
              {cleanPillPrefix} : {activeFolder.title}
            </span>
            <button type="button" data-testid="assistant-folder-notes-toggle-btn" onClick={() => setNotesOpen((prev) => !prev)} className="rounded border border-border-subtle bg-surface-secondary px-2.5 py-0.5 text-xs font-medium">
              {labels.pinnedNotesButtonLabel}
            </button>
            <button type="button" data-testid="assistant-folder-share-modal-btn" onClick={() => setShareModalOpen((prev) => !prev)} className="rounded border border-border-subtle bg-surface-secondary px-2.5 py-0.5 text-xs font-medium">
              {labels.shareButtonLabel}
            </button>
            <button type="button" data-testid="assistant-deselect-folder-btn" onClick={() => onSelectFolder?.("")} className="rounded border border-border-subtle bg-surface-primary px-2 py-0.5 text-[11px] text-text-secondary hover:text-text-primary">
              {isFr ? "Désélectionner" : "Clear active folder"}
            </button>
          </div>
        ) : (
          <span className="text-xs text-text-secondary">
            {isFr ? "Aucun dossier actif sélectionné. Créez ou cliquez sur un dossier ci-dessous pour activer ses notes." : "No active folder selected. Create or click a folder below to activate its notes."}
          </span>
        )}
      </header>

      {activeTurnLockBanner && (
        <div data-testid="assistant-redis-turn-lock-banner" role="status" aria-live="polite" className="rounded border border-status-warning/40 bg-status-warning/10 px-3 py-1.5 text-xs font-semibold text-status-warning">
          {activeTurnLockBanner}
        </div>
      )}

      {notesOpen && activeFolder && (
        <div data-testid="assistant-folder-pinned-notes-drawer" className="rounded-lg border border-border-subtle bg-surface-primary p-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-text-primary">
              <OrciaIcon name="pin" />{" "}
              {isFr ? `Notes permanentes du dossier « ${activeFolder.title} » (injectées dans chaque question)` : `Permanent notes for folder "${activeFolder.title}" (injected into every question)`}
            </span>
            {notesSavedBadge && (
              <span data-testid="assistant-folder-notes-saved-badge" className="text-[11px] font-semibold text-status-success">
                <OrciaIcon name="check" /> {isFr ? "Notes enregistrées et actives" : "Notes saved and active"}
              </span>
            )}
          </div>
          <textarea
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="assistant-folder-pinned-notes-textarea"
            rows={2}
            placeholder={isFr ? "Ex. : Toujours répondre avec des exemples Python 3.12 et respecter le glossaire DORA..." : "E.g.: Always include Python 3.12 examples and follow the domain glossary..."}
            value={draftNotes}
            onChange={(e) => { setDraftNotes(e.target.value); setNotesSavedBadge(false); }}
            className="w-full rounded border border-border-subtle bg-surface-secondary px-2.5 py-1.5 text-xs"
          />
          <div className="flex items-center justify-between gap-2">
            <span data-testid="assistant-layer5-injected-preview" className="font-mono text-[11px] text-text-secondary truncate">
              {activeFolder.assembledLayer5PromptBlock}
            </span>
            <button
              type="button"
              data-testid="assistant-save-pinned-notes-btn"
              onClick={() => { onUpdatePinnedNotes?.(activeFolder.folderId, draftNotes); setNotesSavedBadge(true); }}
              className="rounded bg-action-primary px-3 py-1 text-xs font-semibold text-white shrink-0"
            >
              {isFr ? "Enregistrer les notes" : "Save notes"}
            </button>
          </div>
        </div>
      )}

      {shareModalOpen && activeFolder && (
        <div data-testid="assistant-folder-share-modal" className="rounded border border-border-subtle bg-surface-primary p-3 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            {([["PRIVATE", labels.visibilityPrivateLabel], ["SHARED_SELECTED", labels.visibilitySharedSelectedLabel], ["WORKSPACE_OPEN", labels.visibilityWorkspaceOpenLabel]] as const).map(([mode, btnLabel]) => (
              <button key={mode} type="button" data-testid={`folder-visibility-btn-${mode}`} onClick={() => onChangeVisibility?.(activeFolder.folderId, mode)} className="rounded border border-border-subtle bg-surface-secondary px-2.5 py-1 text-xs">
                {btnLabel}
              </button>
            ))}
          </div>
          {activeFolder.hasRestrictedSources && (
            <p data-testid="assistant-share-restricted-sources-warning" className="rounded border border-status-warning/40 bg-status-warning/10 px-2.5 py-1 text-[11px] text-status-warning">
              {labels.restrictedSourcesWarningText}
            </p>
          )}
        </div>
      )}

      <div data-testid="assistant-tab-panel-folders" className="space-y-3">
        {onCreateFolder && (
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="assistant-new-folder-title-input"
              value={newFolderTitle}
              onChange={(e) => setNewFolderTitle(e.target.value)}
              placeholder={isFr ? "Titre du nouveau dossier thématique..." : "New thematic folder title..."}
              className="flex-1 rounded border border-border-subtle bg-surface-primary px-3 py-1.5 text-xs"
            />
            <button
              type="button"
              data-testid="assistant-create-folder-btn"
              onClick={() => { const title = newFolderTitle.trim() || `Dossier thématique #${folders.length + 1}`; onCreateFolder(title); setNewFolderTitle(""); }}
              className="rounded bg-action-primary px-3 py-1.5 text-xs font-semibold text-white"
            >
              {isFr ? "+ Nouveau dossier" : "+ New folder"}
            </button>
          </div>
        )}
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {folders.map((folder) => {
            const isSelected = folder.folderId === activeFolder?.folderId;
            return (
              <div
                key={folder.folderId}
                data-testid={`assistant-folder-card-${folder.folderId}`}
                className={`rounded-lg border p-3 space-y-1.5 ${isSelected ? "border-action-primary bg-action-primary/5" : "border-border-subtle bg-surface-primary"}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <button type="button" data-testid={`assistant-select-folder-btn-${folder.folderId}`} onClick={() => onSelectFolder?.(folder.folderId)} className="text-xs font-semibold hover:underline text-left">
                    <OrciaIcon name="folder" /> {folder.title}{" "}
                    {isSelected ? <OrciaIcon name="check" /> : ""}
                  </button>
                  <span data-testid={`assistant-folder-visibility-badge-${folder.folderId}`} className="rounded bg-surface-secondary px-2 py-0.5 text-[11px] font-medium text-text-secondary">
                    {formatFolderVisibilityLabel(folder.visibilityMode, isFr)}
                  </span>
                </div>
                <p className="text-[11px] text-text-secondary">{folder.consolidatedSummary}</p>
                {folder.pinnedNotesMarkdown.trim() && (
                  <p className="text-[11px] text-text-primary truncate">
                    <OrciaIcon name="pin" /> {folder.pinnedNotesMarkdown}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div data-testid="assistant-tab-panel-active-discussion" style={{ display: "none" }} className="sr-only">
        <span data-testid="assistant-author-passthrough-badge">Compte actif : <code className="font-mono">{currentAuthorPassthroughIdentity}</code></span>
        {activeFolder && (
          <button type="button" data-testid="assistant-launch-process-from-folder-btn" onClick={() => onLaunchProcessFromFolder?.(activeFolder.folderId, "orcia://pack-sdlc/workflows/ticket-to-tech-spec")}>
            {labels.launchProcessFromFolderCta}
          </button>
        )}
        <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="assistant-collaborative-message-input" value={draftMessage} onChange={(e) => setDraftMessage(e.target.value)} />
        <button type="button" data-testid="assistant-collaborative-send-btn" onClick={() => { if (draftMessage.trim()) onSendCollaborativeMessage?.(draftMessage.trim()); }}>Envoyer</button>
      </div>

      <div data-testid="assistant-tab-panel-history-search" style={{ display: "none" }} className="sr-only">
        <input type="search" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="assistant-history-search-input" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder={labels.searchPlaceholder} />
        <ul data-testid="assistant-history-search-results">
          {filteredHits.map((hit) => (<li key={hit.itemId} data-testid={`assistant-history-hit-${hit.itemId}`}>[{hit.itemKind}] {hit.title} — {hit.snippet}</li>))}
        </ul>
      </div>
    </section>
  );
}
