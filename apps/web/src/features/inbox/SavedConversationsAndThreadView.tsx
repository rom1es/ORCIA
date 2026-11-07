import {
  AssistantResponseFooterActionsAndCitations,
  AssistantUserQuestionBubble,
  ContextualInfoTriggerButton,
  FormattedMarkdownContent,
  type UiAssistantRagCitationItem,
} from "@orcia/ui";
import React from "react";
import type { SavedAssistantConversation } from "./savedConversationsStore";

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
  isFr,
  savedCount,
  foldersCount,
  savedConversationsOpen,
  foldersPanelOpen,
  governanceModalTitle,
  onNewConversation,
  onToggleSavedConversations,
  onToggleFoldersPanel,
  onToggleGovernanceModal,
  onOpenHelpSection,
}: AssistantTopToolbarProps): React.JSX.Element {
  return (
    <div className="orcia-bento-card flex flex-wrap items-center justify-between gap-2 py-2.5 px-3.5">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          data-testid="assistant-new-conversation-btn"
          onClick={onNewConversation}
          className="rounded-full bg-action-primary px-3 py-1 text-xs font-semibold text-white"
        >
          {isFr ? "+ Nouvelle conversation" : "+ New conversation"}
        </button>

        <button
          type="button"
          data-testid="assistant-saved-conversations-toggle-btn"
          aria-expanded={savedConversationsOpen}
          onClick={onToggleSavedConversations}
          className="rounded-full border border-border-subtle bg-surface-secondary px-3 py-1 text-xs font-medium text-text-primary"
        >
          {isFr
            ? `🕒 Conversations sauvegardées (${savedCount})`
            : `🕒 Saved conversations (${savedCount})`}
        </button>

        <button
          type="button"
          data-testid="assistant-folders-toggle-btn"
          aria-expanded={foldersPanelOpen}
          onClick={onToggleFoldersPanel}
          className="rounded-full border border-border-subtle bg-surface-secondary px-3 py-1 text-xs font-medium text-text-primary"
        >
          {isFr
            ? `📁 Dossiers (${foldersCount})`
            : `📁 Folders (${foldersCount})`}
        </button>
      </div>

      <div className="flex items-center gap-2">
        <ContextualInfoTriggerButton
          sectionId="assistant-modes"
          label={
            isFr
              ? "Comprendre les modes de réponse et niveaux de réflexion de Mon Assistant"
              : "Understand My Assistant's response modes and thinking levels"
          }
          onOpenHelpSection={onOpenHelpSection}
        />
        <button
          type="button"
          data-testid="assistant-open-governance-btn"
          onClick={onToggleGovernanceModal}
          className="rounded-full border border-border-subtle bg-surface-elevated px-3 py-1 text-xs font-semibold text-text-primary"
        >
          {governanceModalTitle}
        </button>
      </div>
    </div>
  );
}

export interface SavedConversationsPanelProps {
  readonly conversations: readonly SavedAssistantConversation[];
  readonly activeConversationId: string | null;
  readonly isFr: boolean;
  readonly onResumeConversation: (conversationId: string) => void;
  readonly onDeleteConversation: (conversationId: string) => void;
}

export function SavedConversationsPanel({
  conversations,
  activeConversationId,
  isFr,
  onResumeConversation,
  onDeleteConversation,
}: SavedConversationsPanelProps): React.JSX.Element {
  return (
    <section
      data-testid="assistant-saved-conversations-panel"
      className="orcia-bento-card space-y-2.5"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold text-text-primary">
          {isFr
            ? `🕒 Conversations sauvegardées (${conversations.length})`
            : `🕒 Saved conversations (${conversations.length})`}
        </h3>
      </div>

      {conversations.length === 0 ? (
        <p
          data-testid="assistant-saved-conversations-empty"
          className="text-xs text-text-secondary"
        >
          {isFr
            ? "Aucune conversation sauvegardée pour le moment. Posez une question ci-dessous pour démarrer et enregistrer automatiquement votre premier échange."
            : "No saved conversation yet. Ask a question below to start and automatically save your first thread."}
        </p>
      ) : (
        <ul className="space-y-1.5" data-testid="assistant-saved-conversations-list">
          {conversations.map((conv) => {
            const isCurrent = conv.id === activeConversationId;
            return (
              <li
                key={conv.id}
                data-testid={`assistant-saved-conversation-item-${conv.id}`}
                className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-xs ${
                  isCurrent
                    ? "border-action-primary bg-action-primary/10"
                    : "border-border-subtle bg-surface-primary"
                }`}
              >
                <button
                  type="button"
                  data-testid={`assistant-resume-conversation-${conv.id}`}
                  onClick={() => onResumeConversation(conv.id)}
                  className="flex-1 text-left"
                >
                  <div className="font-semibold text-text-primary">{conv.title}</div>
                  <div className="text-[11px] text-text-secondary">
                    {conv.turns.length}{" "}
                    {isFr
                      ? conv.turns.length > 1
                        ? "échanges"
                        : "échange"
                      : conv.turns.length > 1
                        ? "turns"
                        : "turn"}{" "}
                    · {conv.modelLabel}
                  </div>
                </button>
                <button
                  type="button"
                  data-testid={`assistant-delete-conversation-${conv.id}`}
                  onClick={() => onDeleteConversation(conv.id)}
                  className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 text-[11px] text-text-secondary hover:text-text-primary"
                >
                  {isFr ? "Supprimer" : "Delete"}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export interface ActiveConversationMessagesViewProps {
  readonly conversation: SavedAssistantConversation;
  readonly isFr: boolean;
  readonly ragCitations?: readonly UiAssistantRagCitationItem[];
  readonly onRegenerateTurn?: (userPrompt: string) => void;
  readonly onSaveDraft?: (content: string) => void;
  readonly onContinueInProcess?: (content: string) => void;
}

export function ActiveConversationMessagesView({
  conversation,
  isFr,
  ragCitations = [],
  onRegenerateTurn,
  onSaveDraft,
  onContinueInProcess,
}: ActiveConversationMessagesViewProps): React.JSX.Element | null {
  if (conversation.turns.length === 0) {
    return null;
  }

  return (
    <section
      data-testid="assistant-conversation-messages-list"
      className="orcia-bento-card space-y-3"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2">
        <div className="text-xs font-semibold text-text-primary">
          💬 {conversation.title}
        </div>
        <span className="rounded-full bg-surface-secondary px-2.5 py-0.5 text-[11px] text-text-secondary">
          {conversation.turns.length}{" "}
          {isFr
            ? conversation.turns.length > 1
              ? "échanges enregistrés"
              : "échange enregistré"
            : conversation.turns.length > 1
              ? "saved turns"
              : "saved turn"}
        </span>
      </header>

      <div className="space-y-3">
        {conversation.turns.map((turn, idx) => (
          <div
            key={turn.turnId}
            data-testid={`assistant-conversation-turn-${idx + 1}`}
            className="space-y-2.5 rounded-lg border border-border-subtle bg-surface-primary p-3.5 text-xs"
          >
            <AssistantUserQuestionBubble
              userPrompt={turn.userPrompt}
              isFr={isFr}
              modelLabel={turn.modelLabel}
              effortLabel={turn.effortLabel}
              testId={
                idx === conversation.turns.length - 1
                  ? "assistant-user-question-bubble"
                  : `assistant-user-question-bubble-${idx + 1}`
              }
            />

            <div className="border-t border-border-subtle pt-2.5 mt-2 space-y-2">
              <div className="font-semibold text-action-primary mb-1">
                🤖 {isFr ? "Mon Assistant" : "My Assistant"}
              </div>
              <FormattedMarkdownContent
                content={turn.assistantReply}
                testId={`assistant-turn-markdown-${idx + 1}`}
              />
              {idx === conversation.turns.length - 1 && (
                <AssistantResponseFooterActionsAndCitations
                  responseText={turn.assistantReply}
                  isFr={isFr}
                  ragCitations={ragCitations}
                  onRegenerate={() => onRegenerateTurn?.(turn.userPrompt)}
                  onSaveDraft={onSaveDraft}
                  onContinueInProcess={onContinueInProcess}
                />
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
