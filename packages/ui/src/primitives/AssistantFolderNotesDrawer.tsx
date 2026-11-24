import React from "react";
import { OrciaIcon } from "../components/icons";
import type {
  AssistantFoldersAndCollaborativeThreadViewLabels,
  UiAssistantFolderItem,
} from "./AssistantFoldersAndCollaborativeThreadView";

export function AssistantFolderNotesDrawer({
  activeFolder,
  draftNotes,
  notesSavedBadge,
  labels,
  onChangeDraftNotes,
  onSavePinnedNotes,
}: {
  readonly activeFolder: UiAssistantFolderItem;
  readonly draftNotes: string;
  readonly notesSavedBadge: boolean;
  readonly labels: AssistantFoldersAndCollaborativeThreadViewLabels;
  readonly onChangeDraftNotes: (val: string) => void;
  readonly onSavePinnedNotes: () => void;
}): React.JSX.Element {
  return (
    <div
      data-testid="assistant-folder-pinned-notes-drawer"
      className="rounded-lg border border-border-subtle bg-surface-primary p-3 space-y-2"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-text-primary">
          <OrciaIcon name="pin" />{" "}
          {labels.permanentNotesTitleTemplate.replace("{title}", activeFolder.title)}
        </span>
        {notesSavedBadge && (
          <span
            data-testid="assistant-folder-notes-saved-badge"
            className="text-[11px] font-semibold text-status-success"
          >
            <OrciaIcon name="check" /> {labels.notesSavedBadgeLabel}
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
        placeholder={labels.notesTextareaPlaceholder}
        value={draftNotes}
        onChange={(e) => onChangeDraftNotes(e.target.value)}
        className="w-full rounded border border-border-subtle bg-surface-secondary px-2.5 py-1.5 text-xs"
      />
      <div className="flex items-center justify-between gap-2">
        {activeFolder.assembledLayer5PromptBlock.trim() ? (
          <span
            data-testid="assistant-layer5-injected-preview"
            className="font-mono text-[11px] text-text-secondary truncate"
          >
            {activeFolder.assembledLayer5PromptBlock}
          </span>
        ) : (
          <span className="text-[11px] text-text-secondary">{labels.notesEnrichHint}</span>
        )}
        <button
          type="button"
          data-testid="assistant-save-pinned-notes-btn"
          onClick={onSavePinnedNotes}
          className="rounded bg-action-primary px-3 py-1 text-xs font-semibold text-white shrink-0"
        >
          {labels.saveNotesCta}
        </button>
      </div>
    </div>
  );
}
