import { OrciaIcon, OrciaPageHeader, OrciaTabStrip, type OrciaTabStripItem } from "@orcia/ui";
import React from "react";
import { formatI18nTemplate, useI18n } from "../../i18n";

export type AssistantHeaderTabKey = "active" | "saved" | "folders";

export interface AssistantTopToolbarProps {
  readonly isFr: boolean;
  readonly savedCount: number;
  readonly foldersCount: number;
  readonly savedConversationsOpen: boolean;
  readonly foldersPanelOpen: boolean;
  readonly governanceModalTitle: string;
  readonly alertSlot?: React.ReactNode;
  readonly onSelectActiveDiscussion?: () => void;
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
  alertSlot,
  onSelectActiveDiscussion,
  onNewConversation,
  onToggleSavedConversations,
  onToggleFoldersPanel,
  onToggleGovernanceModal,
}: AssistantTopToolbarProps): React.JSX.Element {
  const { dictionary } = useI18n();
  const tbCopy = dictionary.featureInboxAssistant.toolbar;
  const pageCopy = dictionary.modulePages.inbox;

  const activeTabId: AssistantHeaderTabKey = foldersPanelOpen
    ? "folders"
    : savedConversationsOpen
      ? "saved"
      : "active";

  const tabs: readonly OrciaTabStripItem<AssistantHeaderTabKey>[] = [
    {
      key: "active",
      label: tbCopy.activeDiscussionTab,
      icon: "assistant",
      testId: "assistant-active-discussion-tab",
    },
    {
      key: "saved",
      label:
        savedCount > 0
          ? formatI18nTemplate(tbCopy.savedConversationsCountTemplate, { count: savedCount })
          : tbCopy.savedConversationsLabel,
      icon: "clock",
      testId: "assistant-saved-conversations-toggle-btn",
    },
    {
      key: "folders",
      label:
        foldersCount > 0
          ? formatI18nTemplate(tbCopy.foldersCountTemplate, { count: foldersCount })
          : tbCopy.foldersLabel,
      icon: "folder",
      testId: "assistant-folders-toggle-btn",
    },
  ];

  const handleSelectTab = (nextTab: AssistantHeaderTabKey) => {
    if (nextTab === "active") {
      if (onSelectActiveDiscussion) {
        onSelectActiveDiscussion();
        return;
      }
      if (savedConversationsOpen) onToggleSavedConversations();
      if (foldersPanelOpen) onToggleFoldersPanel();
      return;
    }
    if (nextTab === "saved") {
      if (!savedConversationsOpen) onToggleSavedConversations();
      if (foldersPanelOpen) onToggleFoldersPanel();
      return;
    }
    if (!foldersPanelOpen) onToggleFoldersPanel();
    if (savedConversationsOpen) onToggleSavedConversations();
  };

  return (
    <OrciaPageHeader
      testId="assistant-page-header"
      icon="assistant"
      title={pageCopy.uriBadgeExample}
      subtitle={pageCopy.subtitle}
      secondaryActions={
        <button
          type="button"
          data-testid="assistant-open-governance-btn"
          onClick={onToggleGovernanceModal}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm orcia-ds-nowrap"
        >
          <OrciaIcon name="configuration" size={14} />
          <span>{governanceModalTitle}</span>
        </button>
      }
      primaryAction={
        <button
          type="button"
          data-testid="assistant-new-conversation-btn"
          onClick={onNewConversation}
          className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
        >
          {tbCopy.newConversationBtn}
        </button>
      }
      tabs={
        <OrciaTabStrip<AssistantHeaderTabKey>
          testId="assistant-header-tabs"
          ariaLabel={tbCopy.tabsAriaLabel}
          variant="underline"
          tabs={tabs}
          activeTabId={activeTabId}
          onSelectTab={handleSelectTab}
        />
      }
      alertSlot={alertSlot}
    />
  );
}
