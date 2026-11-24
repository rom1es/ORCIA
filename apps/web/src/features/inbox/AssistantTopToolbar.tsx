import { OrciaIcon } from "@orcia/ui";
import React from "react";
import { formatI18nTemplate, useI18n } from "../../i18n";

export interface AssistantTopToolbarProps {
  readonly isFr: boolean;
  readonly savedCount: number;
  readonly foldersCount: number;
  readonly savedConversationsOpen: boolean;
  readonly foldersPanelOpen: boolean;
  readonly governanceModalTitle: string;
  readonly onNewConversation: () => void;
  readonly onToggleSavedConversations: () => void;
  readonly onToggleFoldersPanel: () => void;
  readonly onToggleGovernanceModal: () => void;
  readonly onOpenHelpSection: (sectionId: string) => void;
}

export function AssistantTopToolbar({
  savedCount,
  foldersCount,
  savedConversationsOpen,
  foldersPanelOpen,
  governanceModalTitle,
  onNewConversation,
  onToggleSavedConversations,
  onToggleFoldersPanel,
  onToggleGovernanceModal,
}: AssistantTopToolbarProps): React.JSX.Element {
  const { dictionary } = useI18n();
  const tbCopy = dictionary.featureInboxAssistant.toolbar;

  return (
    <div className="orcia-bento-card flex flex-wrap items-center justify-between gap-2 py-2.5 px-3.5">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          data-testid="assistant-new-conversation-btn"
          onClick={onNewConversation}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm rounded-full"
        >
          {tbCopy.newConversationBtn}
        </button>

        <button
          type="button"
          data-testid="assistant-saved-conversations-toggle-btn"
          aria-expanded={savedConversationsOpen}
          onClick={onToggleSavedConversations}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm rounded-full"
        >
          <OrciaIcon name="clock" />{" "}
          {savedCount > 0
            ? formatI18nTemplate(tbCopy.savedConversationsCountTemplate, { count: savedCount })
            : tbCopy.savedConversationsLabel}
        </button>

        <button
          type="button"
          data-testid="assistant-folders-toggle-btn"
          aria-expanded={foldersPanelOpen}
          onClick={onToggleFoldersPanel}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm rounded-full"
        >
          <OrciaIcon name="folder" />{" "}
          {foldersCount > 0
            ? formatI18nTemplate(tbCopy.foldersCountTemplate, { count: foldersCount })
            : tbCopy.foldersLabel}
        </button>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          data-testid="assistant-open-governance-btn"
          onClick={onToggleGovernanceModal}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm rounded-full font-semibold"
        >
          {governanceModalTitle}
        </button>
      </div>
    </div>
  );
}
