import React from "react";
import { OrciaIcon } from "../components/icons";
import { useResponsiveBreakpoint } from "../hooks/useResponsiveBreakpoint";
import {
  AssistantModelAndEffortPopover,
  type AssistantModelAndEffortPopoverLabels,
  type UiAssistantModelOption,
} from "./AssistantModelAndEffortPopover";
import {
  AssistantAttachedFilesInlineBar,
  AssistantPromptPlusAndAutocomplete,
  type AssistantPromptPlusLabels,
  type UiAssistantAttachedFileItem,
  type UiAssistantAutocompleteOption,
  type UiAssistantOrciaDocumentOption,
} from "./AssistantPromptPlusAndAutocomplete";
import {
  AssistantActiveFolderPromptBadge,
  AssistantToolsUnsupportedNotice,
} from "./AssistantStickyFooterBadges";
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
  readonly disabled?: boolean;
  readonly supportsTools?: boolean;
  readonly toolsUnsupportedNotice?: string;
  readonly toolsUnsupportedBadge?: string;
  readonly disabledReasonBanner?: React.ReactNode;
  readonly plusMenuAriaLabel: string;
  readonly sendTitle: string;
  readonly stopTitle: string;
  readonly followLiveResponseCta: string;
  readonly activeFolderPrefix: string;
  readonly activeNoteAppliedText: string;
  readonly detachActiveFolderAriaLabel: string;
  readonly plusLabels: AssistantPromptPlusLabels;
  readonly popoverLabels: AssistantModelAndEffortPopoverLabels;
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

export function AssistantStickyPromptFooter(props: AssistantStickyPromptFooterProps): React.JSX.Element {
  const {
    inputRef, isPinnedToBottom, isGenerating, plusMenuOpen, pickerOpen, thinkingSubmenuOpen, promptText,
    inputPlaceholder, actionAriaLabel, visibleModelCount, displayModelBadge, activeEffortTitle, tier, effort,
    modelOptions, effectiveAutocompleteTrigger, mergedAgentOptions, mergedSkillOptions, orciaDocuments,
    attachedFiles, activeFolderTitle, activeFolderNotes, disabled = false, supportsTools = true,
    toolsUnsupportedNotice, toolsUnsupportedBadge, disabledReasonBanner = null, plusMenuAriaLabel,
    sendTitle, stopTitle, followLiveResponseCta, activeFolderPrefix, activeNoteAppliedText,
    detachActiveFolderAriaLabel, plusLabels, popoverLabels, onScrollToStreamBottom,
    onSelectAutocompleteOption, onTriggerAgentFromPlus, onTriggerSkillFromPlus, onAttachFile,
    onRemoveAttachedFile, onOpenFoldersAndCloseMenus, onClearActiveFolder, onTogglePlusMenu,
    onPromptChange, onInputKeyDown, onTogglePicker, onSendOrStopClick, onSelectTier,
    onToggleThinkingSubmenu, onSelectEffort,
  } = props;
  const { isMobile } = useResponsiveBreakpoint();
  const plusBtnNode = (
    <button
      type="button"
      data-testid="assistant-prompt-plus-btn"
      aria-label={plusMenuAriaLabel}
      onClick={onTogglePlusMenu}
      className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border-subtle bg-surface-secondary text-sm font-semibold text-text-primary hover:bg-surface-elevated"
    >
      <OrciaIcon name="plus" />
    </button>
  );
  const inputNode = (
    <input
      ref={inputRef}
      type="text"
      disabled={disabled}
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
      className={`${
        isMobile ? "w-full min-w-0 px-1" : "flex-1 min-w-[200px] px-2"
      } border-0 bg-transparent py-1 text-xs text-text-primary focus:outline-none ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
    />
  );
  const pickerBtnNode = (
    <button
      type="button"
      data-testid="assistant-model-and-effort-picker-trigger"
      aria-expanded={pickerOpen}
      onClick={onTogglePicker}
      className="inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-full border border-border-subtle bg-surface-secondary px-2.5 py-1 text-xs font-medium text-text-primary hover:bg-surface-elevated"
    >
      {visibleModelCount === 1 ? (
        <span className="truncate">{activeEffortTitle}</span>
      ) : (
        <>
          <span className="truncate">{displayModelBadge}</span>
          <span className="shrink-0 text-text-secondary">· {activeEffortTitle}</span>
        </>
      )}
      <OrciaIcon name="caretDown" />
    </button>
  );
  const sendBtnNode = (
    <button
      type="button"
      data-testid="assistant-three-speed-send-btn"
      disabled={Boolean(disabled) && !isGenerating}
      aria-label={actionAriaLabel}
      title={isGenerating ? stopTitle : sendTitle}
      onClick={onSendOrStopClick}
      className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-action-primary text-xs font-semibold text-white hover:opacity-95 ${Boolean(disabled) && !isGenerating ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      {isGenerating ? (
        <OrciaIcon name="stopSquare" testId="assistant-stop-square-icon" />
      ) : (
        <OrciaIcon name="play" testId="assistant-send-play-icon" />
      )}
    </button>
  );

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
            <OrciaIcon name="arrowDown" /> {followLiveResponseCta}
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
        labels={plusLabels}
        onSelectAutocompleteOption={onSelectAutocompleteOption}
        onTriggerAgentAutocompleteFromPlus={onTriggerAgentFromPlus}
        onTriggerSkillAutocompleteFromPlus={onTriggerSkillFromPlus}
        onAttachFile={onAttachFile}
        onRemoveAttachedFile={onRemoveAttachedFile}
        onOpenFoldersAndCloseMenus={onOpenFoldersAndCloseMenus}
      />
      <AssistantActiveFolderPromptBadge
        activeFolderTitle={activeFolderTitle}
        activeFolderNotes={activeFolderNotes}
        activeFolderPrefix={activeFolderPrefix}
        activeNoteAppliedText={activeNoteAppliedText}
        detachActiveFolderAriaLabel={detachActiveFolderAriaLabel}
        onClearActiveFolder={onClearActiveFolder}
      />
      {disabledReasonBanner}
      <AssistantToolsUnsupportedNotice
        supportsTools={supportsTools}
        toolsUnsupportedNotice={toolsUnsupportedNotice}
      />
      <div className="rounded-2xl border border-border-subtle bg-surface-primary px-3 py-2 shadow-sm space-y-1.5">
        <AssistantAttachedFilesInlineBar
          attachedFiles={attachedFiles}
          removeFilePrefix={plusLabels.removeFilePrefix}
          onRemoveAttachedFile={onRemoveAttachedFile}
        />
        {isMobile ? (
          <div data-testid="assistant-mobile-two-row-composer" className="flex flex-col gap-1.5 min-w-0">
            {inputNode}
            <div className="flex w-full min-w-0 items-center justify-between gap-2">
              <div className="flex min-w-0 flex-1 items-center gap-1.5">
                {plusBtnNode}
                {pickerBtnNode}
              </div>
              {sendBtnNode}
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            {plusBtnNode}
            {inputNode}
            {pickerBtnNode}
            {sendBtnNode}
          </div>
        )}
      </div>
      {pickerOpen && (
        <AssistantModelAndEffortPopover
          modelOptions={modelOptions}
          selectedTier={tier}
          selectedEffort={effort}
          thinkingSubmenuOpen={thinkingSubmenuOpen}
          supportsTools={supportsTools}
          {...(toolsUnsupportedBadge ? { toolsUnsupportedBadge } : {})}
          labels={popoverLabels}
          onSelectTier={onSelectTier}
          onToggleThinkingSubmenu={onToggleThinkingSubmenu}
          onSelectEffort={onSelectEffort}
        />
      )}
    </div>
  );
}
