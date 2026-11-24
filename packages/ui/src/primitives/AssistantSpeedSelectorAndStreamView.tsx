import React, { useRef } from "react";
import { useResponsiveBreakpoint } from "../hooks/useResponsiveBreakpoint";
import { AssistantActiveStreamContent } from "./AssistantActiveStreamContent";
import {
  applyAutocompleteSelectionToPrompt,
  detectActiveAutocompleteTrigger,
  type UiAssistantAutocompleteOption,
} from "./AssistantPromptPlusAndAutocomplete";
import { sanitizeAssistantDisplayReply } from "./AssistantResponseFooterActionsAndCitations";
import {
  AssistantTechnicalCacheHeader,
  findTopAutocompleteMatch,
  mergeRagCitationsWithFiles,
  resolveDisplayModelBadge,
  resolveEffectiveTurnPrompt,
  useAssistantPinnedScroll,
  useAssistantSpeedViewState,
} from "./AssistantSpeedSelectorHelpers";
import type { AssistantSpeedSelectorAndStreamViewProps } from "./AssistantSpeedSelectorTypes";
import {
  AssistantLegacySpeedPillsRow,
  mergeAssistantAutocompleteOptions,
} from "./AssistantStickyFooterBadges";
import { AssistantStickyPromptFooter } from "./AssistantStickyPromptFooter";
import type { UiInferenceEffort } from "./InferenceTierAndEffortSelector";

export type {
  AssistantActiveStreamLabels,
  AssistantModelAndEffortPopoverLabels,
  AssistantPromptPlusLabels,
  AssistantResponseFooterLabels,
  AssistantSpeedSelectorAndStreamViewLabels,
  AssistantSpeedSelectorAndStreamViewProps,
  UiAssistantAutocompleteSuggestion,
  UiAssistantEffortOption,
  UiAssistantErrorKind,
  UiAssistantModelOption,
  UiAssistantSpeedMode,
  UiThreeSpeedStepProgress,
} from "./AssistantSpeedSelectorTypes";

export function AssistantSpeedSelectorAndStreamView(props: AssistantSpeedSelectorAndStreamViewProps): React.JSX.Element {
  const {
    workspaceId, userId, hat, activeSpeed: initialSpeed = "SPEED_1_FAST", deepAuditPillActive: initialDeepAudit = false,
    supportsTools = true, lowEvidence = false,
    selectedTier: initialTier = "medium", selectedEffort: initialEffort, modelOptions: providedModelOptions,
    agentOptions = [], skillOptions = [],
    orciaDocuments = [], ragCitations = [], autocompleteSuggestions = [], prefillPrompt = null,
    onPrefillConsumed, activeFolderTitle = null, activeFolderNotes = null, onClearActiveFolder, previousTurnsSlot = null,
    reflexiveTraceSlot = null, welcomeTitle, showWelcomeHero = true,
    hideTechnicalCacheHeader = false, hideLegacySpeedPills = false, hideDuplicateCompletedStream = false, cacheHit = true,
    cacheLookupMs = 1.4, nodes1To4DeterministicMs = 18.2, ttftMs = 398.2, stepProgress, streamedText = "", activeUserPrompt,
    isGenerating = false, initialElapsedSeconds = 0, generationStopped = false, errorMessage = null,
    errorKind = null, reconnectCtaLabel, onReconnect,
    disabled = false, disabledReasonBanner = null, labels,
    onOpenFoldersFromPlus, onStopGeneration, onRegenerateLastTurn, onSaveDraftFromResponse, onContinueInProcessFromResponse,
    onInspectCitation, currentTurnFeedback = null, onFeedbackLastTurn, onDeepenLastTurn, onSendTurn,
  } = props;
  const modelOptions = providedModelOptions ?? labels.defaultModelOptions;
  const resolvedWelcomeTitle = welcomeTitle ?? labels.defaultWelcomeTitle;
  const inputRef = useRef<HTMLInputElement | null>(null);
  const { isMobile } = useResponsiveBreakpoint();
  const st = useAssistantSpeedViewState({
    initialSpeed, initialDeepAudit, supportsTools, initialTier, initialEffort, prefillPrompt, onPrefillConsumed, inputRef,
  });

  const {
    scrollContainerRef,
    isPinnedToBottom,
    handleStreamScroll,
    scrollToStreamBottom,
    pinToBottomRef,
  } = useAssistantPinnedScroll([
    streamedText,
    stepProgress.length > 0,
    isGenerating,
    activeUserPrompt,
    previousTurnsSlot,
  ]);

  const cacheKey = `assistant:prompt:${workspaceId}:${userId}:${hat}`;
  const visibleModelCount = modelOptions.filter((m) => !m.hiddenDuplicate).length;
  const activeModelOption = modelOptions.find((m) => m.tier === st.tier) ?? modelOptions[1] ?? modelOptions[0] ?? labels.defaultModelOptions[0]!;
  const normalizedEffort: UiInferenceEffort = !supportsTools ? "fast" : st.effort === "deep" ? "deep" : "balanced";
  const activeEffortOption =
    labels.modelPopover.effortOptions.find((e) => e.effort === normalizedEffort) ??
    labels.modelPopover.effortOptions[1] ??
    labels.modelPopover.effortOptions[0]!;

  const { mergedAgentOptions, mergedSkillOptions } = mergeAssistantAutocompleteOptions(
    autocompleteSuggestions,
    agentOptions,
    skillOptions,
  );
  const effectiveAutocompleteTrigger =
    detectActiveAutocompleteTrigger(st.promptText) ??
    (st.forcedAutocompleteKind !== null ? { kind: st.forcedAutocompleteKind, query: "" } : null);

  const handleSelectAutocompleteOption = (option: UiAssistantAutocompleteOption) => {
    st.handlePromptChange(applyAutocompleteSelectionToPrompt(st.promptText, option));
    st.setForcedAutocompleteKind(null);
    st.setPlusMenuOpen(false);
    inputRef.current?.focus();
  };

  const triggerSendTurn = (overridePrompt?: string) => {
    if (disabled) return;
    const effectivePrompt = resolveEffectiveTurnPrompt(overridePrompt, st.promptText, st.lastSubmittedPrompt, labels.defaultGreetingPrompt);
    const submittedFiles = st.attachedFiles;
    pinToBottomRef();
    st.setLastSubmittedPrompt(effectivePrompt);
    st.setLastSubmittedFiles(submittedFiles);
    st.setAttachedFiles([]);
    st.setPromptText("");
    st.setForcedAutocompleteKind(null);
    st.setLocalStoppedFlag(false);
    st.setPickerOpen(false);
    st.setPlusMenuOpen(false);
    onSendTurn?.({
      userPrompt: effectivePrompt,
      requestedSpeed: supportsTools ? st.speed : "SPEED_1_FAST",
      deepAuditPillActive: supportsTools ? st.deepAuditActive : false,
      ...(st.userEditedTierOrEffort ? { requestedTier: st.tier, thinkingEffort: supportsTools ? st.effort : "fast" } : {}),
      ...(submittedFiles.length > 0 ? { attachedFiles: submittedFiles } : {}),
    });
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (disabled) {
      e.preventDefault();
      return;
    }
    if (e.key === "Enter") {
      if (effectiveAutocompleteTrigger !== null) {
        const topMatch = findTopAutocompleteMatch(
          effectiveAutocompleteTrigger.kind,
          effectiveAutocompleteTrigger.query,
          st.promptText,
          mergedAgentOptions,
          mergedSkillOptions,
        );
        if (topMatch) {
          e.preventDefault();
          handleSelectAutocompleteOption(topMatch);
          return;
        }
      }
      if (!isGenerating) {
        e.preventDefault();
        triggerSendTurn();
      }
    } else if (e.key === "Escape") {
      st.setForcedAutocompleteKind(null);
      st.setPlusMenuOpen(false);
    }
  };

  const displayModelBadge = resolveDisplayModelBadge(activeModelOption);
  const isStoppedVisible = Boolean(generationStopped || st.localStoppedFlag) && !isGenerating;
  const actionAriaLabel = isGenerating ? labels.stopGenerationAriaLabel : labels.sendPromptCta;
  const shownUserQuestion = activeUserPrompt || st.lastSubmittedPrompt;
  const cleanStreamedText = sanitizeAssistantDisplayReply(streamedText);
  const mergedRagCitations = mergeRagCitationsWithFiles(ragCitations, st.lastSubmittedFiles);

  return (
    <section
      data-testid="assistant-speed-selector-and-stream"
      style={{
        display: "flex",
        flexDirection: "column",
        maxHeight: isMobile ? "calc(100dvh - 190px)" : "calc(100vh - 155px)",
        minHeight: isMobile ? "260px" : "340px",
        minWidth: 0,
      }}
      className={hideTechnicalCacheHeader ? "pt-1 text-text-primary gap-2.5 min-w-0" : "rounded-xl border border-border-subtle bg-surface-elevated p-5 text-text-primary gap-3 min-w-0"}
    >
      {!hideTechnicalCacheHeader && (
        <AssistantTechnicalCacheHeader
          labels={labels}
          cacheHit={cacheHit}
          cacheLookupMs={cacheLookupMs}
          cacheKey={cacheKey}
          nodes1To4DeterministicMs={nodes1To4DeterministicMs}
          ttftMs={ttftMs}
        />
      )}
      {showWelcomeHero && !cleanStreamedText && !isGenerating && !reflexiveTraceSlot && (
        <div className="py-6 text-center"><h2 data-testid="assistant-welcome-hero-title" className="text-xl font-semibold tracking-tight text-text-primary">{resolvedWelcomeTitle}</h2></div>
      )}
      <div ref={scrollContainerRef} onScroll={handleStreamScroll} data-testid="assistant-central-scrollable-stream" data-pinned-to-bottom={isPinnedToBottom ? "true" : "false"} style={{ flex: "1 1 auto", minHeight: 0, overflowY: "auto" }} className="space-y-3 pr-1">
        <AssistantActiveStreamContent
          previousTurnsSlot={previousTurnsSlot}
          reflexiveTraceSlot={reflexiveTraceSlot}
          shownUserQuestion={shownUserQuestion}
          hideDuplicateCompletedStream={hideDuplicateCompletedStream}
          isGenerating={isGenerating}
          displayModelBadge={displayModelBadge}
          effortTitle={activeEffortOption.title}
          lastSubmittedFiles={st.lastSubmittedFiles}
          cleanStreamedText={cleanStreamedText}
          stepProgress={stepProgress}
          initialElapsedSeconds={initialElapsedSeconds}
          errorMessage={errorMessage}
          errorKind={errorKind}
          reconnectCtaLabel={reconnectCtaLabel}
          onReconnect={onReconnect}
          isStoppedVisible={isStoppedVisible}
          mergedRagCitations={mergedRagCitations}
          currentTurnFeedback={currentTurnFeedback}
          onFeedbackLastTurn={onFeedbackLastTurn}
          canDeepen={Boolean(supportsTools && st.speed === "SPEED_1_FAST" && onDeepenLastTurn)}
          lowEvidence={lowEvidence}
          deepenLabel={labels.deepenCta}
          deepenLowEvidenceLabel={labels.deepenLowEvidenceCta}
          labels={{ ...labels.stream, responseFooter: labels.responseFooter }}
          onDeepen={onDeepenLastTurn}
          onRegenerate={() => (onRegenerateLastTurn ? onRegenerateLastTurn() : triggerSendTurn(st.lastSubmittedPrompt))}
          onSaveDraftFromResponse={onSaveDraftFromResponse}
          onContinueInProcessFromResponse={onContinueInProcessFromResponse}
          onInspectCitation={onInspectCitation}
        />
      </div>

      <AssistantStickyPromptFooter
        inputRef={inputRef}
        isPinnedToBottom={isPinnedToBottom}
        isGenerating={isGenerating}
        plusMenuOpen={st.plusMenuOpen}
        pickerOpen={st.pickerOpen}
        thinkingSubmenuOpen={st.thinkingSubmenuOpen}
        promptText={st.promptText}
        inputPlaceholder={labels.inputPlaceholder}
        actionAriaLabel={actionAriaLabel}
        visibleModelCount={visibleModelCount}
        displayModelBadge={displayModelBadge}
        activeEffortTitle={activeEffortOption.title}
        tier={st.tier}
        effort={st.effort}
        modelOptions={modelOptions}
        effectiveAutocompleteTrigger={effectiveAutocompleteTrigger}
        mergedAgentOptions={mergedAgentOptions}
        mergedSkillOptions={mergedSkillOptions}
        orciaDocuments={orciaDocuments}
        attachedFiles={st.attachedFiles}
        activeFolderTitle={activeFolderTitle}
        activeFolderNotes={activeFolderNotes}
        disabled={disabled}
        supportsTools={supportsTools}
        {...(labels.toolsUnsupportedNotice ? { toolsUnsupportedNotice: labels.toolsUnsupportedNotice } : {})}
        {...(labels.toolsUnsupportedBadge ? { toolsUnsupportedBadge: labels.toolsUnsupportedBadge } : {})}
        disabledReasonBanner={disabledReasonBanner}
        plusMenuAriaLabel={labels.plusMenuAriaLabel}
        sendTitle={labels.sendTitle}
        stopTitle={labels.stopTitle}
        followLiveResponseCta={labels.followLiveResponseCta}
        activeFolderPrefix={labels.activeFolderPrefix}
        activeNoteAppliedText={labels.activeNoteAppliedText}
        detachActiveFolderAriaLabel={labels.detachActiveFolderAriaLabel}
        plusLabels={labels.plusMenu}
        popoverLabels={labels.modelPopover}
        onScrollToStreamBottom={scrollToStreamBottom}
        onSelectAutocompleteOption={handleSelectAutocompleteOption}
        onTriggerAgentFromPlus={() => { st.setPromptText(st.promptText ? `${st.promptText} @` : "@"); st.setForcedAutocompleteKind("agent"); st.setPlusMenuOpen(false); inputRef.current?.focus(); }}
        onTriggerSkillFromPlus={() => { st.setPromptText(st.promptText ? `${st.promptText} /` : "/"); st.setForcedAutocompleteKind("skill"); st.setPlusMenuOpen(false); inputRef.current?.focus(); }}
        onAttachFile={(file) => { st.setAttachedFiles((prev) => [...prev, file]); st.setPlusMenuOpen(false); inputRef.current?.focus(); }}
        onRemoveAttachedFile={(fileId) => st.setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId))}
        onOpenFoldersAndCloseMenus={onOpenFoldersFromPlus ? () => { st.setPlusMenuOpen(false); st.setForcedAutocompleteKind(null); st.setPromptText((prev) => prev.replace(/(?:^|\s)[@/][a-zA-Z0-9_-]*$/, "")); onOpenFoldersFromPlus(); } : undefined}
        onClearActiveFolder={onClearActiveFolder}
        onTogglePlusMenu={() => { st.setPlusMenuOpen((prev) => !prev); st.setPickerOpen(false); }}
        onPromptChange={st.handlePromptChange}
        onInputKeyDown={handleInputKeyDown}
        onTogglePicker={() => { st.setPickerOpen((prev) => !prev); st.setPlusMenuOpen(false); }}
        onSendOrStopClick={() => { if (disabled && !isGenerating) return; if (isGenerating) { st.setLocalStoppedFlag(true); onStopGeneration?.(); inputRef.current?.focus(); return; } triggerSendTurn(); }}
        onSelectTier={(nextTier) => { st.setUserEditedTierOrEffort(true); st.setTier(nextTier); }}
        onToggleThinkingSubmenu={() => st.setThinkingSubmenuOpen((prev) => !prev)}
        onSelectEffort={st.handleSelectEffort}
      />

      <AssistantLegacySpeedPillsRow
        labels={labels}
        hideLegacySpeedPills={hideLegacySpeedPills}
        supportsTools={supportsTools}
        speed={st.speed}
        deepAuditActive={st.deepAuditActive}
        onSelectSpeed={(mode, eff) => {
          st.setDeepAuditActive(false);
          st.setSpeed(mode);
          st.setEffort(eff);
        }}
        onToggleDeepAudit={() => {
          const next = !st.deepAuditActive;
          st.setDeepAuditActive(next);
          st.setSpeed(next ? "SPEED_3_DEEP_AUDIT" : "SPEED_1_FAST");
          st.setEffort(next ? "deep" : "balanced");
        }}
      />
    </section>
  );
}
