import React from "react";
import { OrciaIcon } from "../components/icons";
import {
  AssistantModelAndEffortPopover,
  type UiAssistantModelOption,
} from "./AssistantModelAndEffortPopover";
import {
  AssistantAttachedFilesInlineBar,
  AssistantPromptPlusAndAutocomplete,
  type UiAssistantAttachedFileItem,
  type UiAssistantAutocompleteOption,
  type UiAssistantOrciaDocumentOption,
} from "./AssistantPromptPlusAndAutocomplete";
import type {
  UiInferenceEffort,
  UiInferenceTier,
} from "./InferenceTierAndEffortSelector";

export interface AssistantStickyPromptFooterProps {
  readonly inputRef: React.RefObject<HTMLInputElement | null>;
  readonly isPinnedToBottom: boolean;
  readonly isGenerating: boolean;
  readonly plusMenuOpen: boolean;
  readonly pickerOpen: boolean;
  readonly thinkingSubmenuOpen: boolean;
  readonly promptText: string;
  readonly inputPlaceholder: string;
  readonly actionAriaLabel: string;
  readonly visibleModelCount: number;
  readonly displayModelBadge: string;
  readonly activeEffortTitle: string;
  readonly tier: UiInferenceTier;
  readonly effort: UiInferenceEffort;
  readonly modelOptions: readonly UiAssistantModelOption[];
  readonly effectiveAutocompleteTrigger: {
    readonly kind: "agent" | "skill";
    readonly query: string;
  } | null;
  readonly mergedAgentOptions: readonly UiAssistantAutocompleteOption[];
  readonly mergedSkillOptions: readonly UiAssistantAutocompleteOption[];
  readonly orciaDocuments: readonly UiAssistantOrciaDocumentOption[];
  readonly attachedFiles: readonly UiAssistantAttachedFileItem[];
  readonly activeFolderTitle: string | null;
  readonly activeFolderNotes: string | null;
  readonly onScrollToStreamBottom: () => void;
  readonly onSelectAutocompleteOption: (
    option: UiAssistantAutocompleteOption,
  ) => void;
  readonly onTriggerAgentFromPlus: () => void;
  readonly onTriggerSkillFromPlus: () => void;
  readonly onAttachFile: (file: UiAssistantAttachedFileItem) => void;
  readonly onRemoveAttachedFile: (fileId: string) => void;
  readonly onOpenFoldersAndCloseMenus?: () => void;
  readonly onClearActiveFolder?: () => void;
  readonly onTogglePlusMenu: () => void;
  readonly onPromptChange: (val: string) => void;
  readonly onInputKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  readonly onTogglePicker: () => void;
  readonly onSendOrStopClick: () => void;
  readonly onSelectTier: (tier: UiInferenceTier) => void;
  readonly onToggleThinkingSubmenu: () => void;
  readonly onSelectEffort: (effort: UiInferenceEffort) => void;
}

export function AssistantStickyPromptFooter({
  inputRef,
  isPinnedToBottom,
  isGenerating,
  plusMenuOpen,
  pickerOpen,
  thinkingSubmenuOpen,
  promptText,
  inputPlaceholder,
  actionAriaLabel,
  visibleModelCount,
  displayModelBadge,
  activeEffortTitle,
  tier,
  effort,
  modelOptions,
  effectiveAutocompleteTrigger,
  mergedAgentOptions,
  mergedSkillOptions,
  orciaDocuments,
  attachedFiles,
  activeFolderTitle,
  activeFolderNotes,
  onScrollToStreamBottom,
  onSelectAutocompleteOption,
  onTriggerAgentFromPlus,
  onTriggerSkillFromPlus,
  onAttachFile,
  onRemoveAttachedFile,
  onOpenFoldersAndCloseMenus,
  onClearActiveFolder,
  onTogglePlusMenu,
  onPromptChange,
  onInputKeyDown,
  onTogglePicker,
  onSendOrStopClick,
  onSelectTier,
  onToggleThinkingSubmenu,
  onSelectEffort,
}: AssistantStickyPromptFooterProps): React.JSX.Element {
  return (
    <div
      data-testid="assistant-sticky-prompt-footer"
      style={{
        flexShrink: 0,
        position: "sticky",
        bottom: 0,
        zIndex: 20,
        backgroundColor: "var(--color-bg-surface)",
        paddingTop: "6px",
      }}
      className="relative"
    >
      {!isPinnedToBottom && isGenerating ? (
        <div className="mb-1.5 flex justify-center">
          <button
            type="button"
            data-testid="assistant-resume-autoscroll-btn"
            onClick={onScrollToStreamBottom}
            className="inline-flex items-center gap-1 rounded-full border border-border-subtle bg-surface-elevated px-3 py-0.5 text-[11px] font-medium text-action-primary shadow-sm hover:bg-surface-secondary"
          >
            <OrciaIcon name="arrowDown" /> Suivre la réponse en direct
          </button>
        </div>
      ) : null}
      <AssistantPromptPlusAndAutocomplete
        plusMenuOpen={plusMenuOpen}
        autocompleteTrigger={effectiveAutocompleteTrigger}
        agentOptions={mergedAgentOptions}
        skillOptions={mergedSkillOptions}
        orciaDocuments={orciaDocuments}
        attachedFiles={attachedFiles}
        onSelectAutocompleteOption={onSelectAutocompleteOption}
        onTriggerAgentAutocompleteFromPlus={onTriggerAgentFromPlus}
        onTriggerSkillAutocompleteFromPlus={onTriggerSkillFromPlus}
        onAttachFile={onAttachFile}
        onRemoveAttachedFile={onRemoveAttachedFile}
        onOpenFoldersAndCloseMenus={onOpenFoldersAndCloseMenus}
      />
      {activeFolderTitle ? (
        <div
          data-testid="assistant-prompt-active-folder-badge"
          className="mb-1.5 inline-flex flex-wrap items-center gap-1.5 rounded-full border border-action-primary/30 bg-action-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-action-primary"
        >
          <span>
            <OrciaIcon name="folder" /> Dossier actif :{" "}
            <strong>{activeFolderTitle}</strong>
          </span>
          {activeFolderNotes && activeFolderNotes.trim() ? (
            <span
              data-testid="assistant-prompt-active-folder-note-indicator"
              className="text-text-secondary"
            >
              · <OrciaIcon name="pin" /> Note active prise en compte par
              l&apos;Assistant
            </span>
          ) : null}
          {onClearActiveFolder ? (
            <button
              type="button"
              data-testid="assistant-prompt-clear-active-folder-btn"
              onClick={onClearActiveFolder}
              aria-label="Détacher le dossier actif"
              className="ml-1 font-bold hover:opacity-80"
            >
              <OrciaIcon name="times" />
            </button>
          ) : null}
        </div>
      ) : null}
      <div className="rounded-2xl border border-border-subtle bg-surface-primary px-3 py-2 shadow-sm space-y-1.5">
        <AssistantAttachedFilesInlineBar
          attachedFiles={attachedFiles}
          onRemoveAttachedFile={onRemoveAttachedFile}
        />
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            data-testid="assistant-prompt-plus-btn"
            aria-label="Actions rapides et dossiers"
            onClick={onTogglePlusMenu}
            className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-border-subtle bg-surface-secondary text-sm font-semibold text-text-primary hover:bg-surface-elevated"
          >
            <OrciaIcon name="plus" />
          </button>
          <input
            ref={inputRef}
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="assistant-three-speed-input"
            value={promptText}
            placeholder={inputPlaceholder}
            onChange={(e) => onPromptChange(e.target.value)}
            onKeyDown={onInputKeyDown}
            className="flex-1 min-w-[200px] border-0 bg-transparent px-2 py-1 text-xs text-text-primary focus:outline-none"
          />
          <button
            type="button"
            data-testid="assistant-model-and-effort-picker-trigger"
            aria-expanded={pickerOpen}
            onClick={onTogglePicker}
            className="inline-flex items-center gap-1.5 rounded-full border border-border-subtle bg-surface-secondary px-3 py-1 text-xs font-medium text-text-primary hover:bg-surface-elevated"
          >
            {visibleModelCount === 1 ? (
              <span>{activeEffortTitle}</span>
            ) : (
              <>
                <span>{displayModelBadge}</span>
                <span className="text-text-secondary">
                  · {activeEffortTitle}
                </span>
              </>
            )}
            <OrciaIcon name="caretDown" />
          </button>
          <button
            type="button"
            data-testid="assistant-three-speed-send-btn"
            aria-label={actionAriaLabel}
            title={isGenerating ? "Arrêter" : "Envoyer"}
            onClick={onSendOrStopClick}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-action-primary text-xs font-semibold text-white hover:opacity-95"
          >
            {isGenerating ? (
              <OrciaIcon name="stopSquare" testId="assistant-stop-square-icon" />
            ) : (
              <OrciaIcon name="play" testId="assistant-send-play-icon" />
            )}
          </button>
        </div>
      </div>
      {pickerOpen && (
        <AssistantModelAndEffortPopover
          modelOptions={modelOptions}
          selectedTier={tier}
          selectedEffort={effort}
          thinkingSubmenuOpen={thinkingSubmenuOpen}
          onSelectTier={onSelectTier}
          onToggleThinkingSubmenu={onToggleThinkingSubmenu}
          onSelectEffort={onSelectEffort}
        />
      )}
    </div>
  );
}
