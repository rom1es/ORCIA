import React, { useEffect, useRef, useState } from "react";
import { AssistantActiveStreamContent } from "./AssistantActiveStreamContent";
import {
  ASSISTANT_EFFORT_OPTIONS,
  DEFAULT_ASSISTANT_MODEL_OPTIONS,
} from "./AssistantModelAndEffortPopover";
import {
  applyAutocompleteSelectionToPrompt,
  DEFAULT_ASSISTANT_AGENT_OPTIONS,
  DEFAULT_ASSISTANT_SKILL_OPTIONS,
  DEFAULT_ORCIA_DOCUMENT_OPTIONS,
  detectActiveAutocompleteTrigger,
  type UiAssistantAttachedFileItem,
  type UiAssistantAutocompleteOption,
} from "./AssistantPromptPlusAndAutocomplete";
import {
  sanitizeAssistantDisplayReply,
  type UiAssistantRagCitationItem,
} from "./AssistantResponseFooterActionsAndCitations";
import type {
  AssistantSpeedSelectorAndStreamViewProps,
  UiAssistantSpeedMode,
} from "./AssistantSpeedSelectorTypes";
import { AssistantStickyPromptFooter } from "./AssistantStickyPromptFooter";
import type {
  UiInferenceEffort,
  UiInferenceTier,
} from "./InferenceTierAndEffortSelector";

export type {
  AssistantSpeedSelectorAndStreamViewLabels,
  AssistantSpeedSelectorAndStreamViewProps,
  UiAssistantAutocompleteSuggestion,
  UiAssistantModelOption,
  UiAssistantSpeedMode,
  UiThreeSpeedStepProgress,
} from "./AssistantSpeedSelectorTypes";

export function AssistantSpeedSelectorAndStreamView(props: AssistantSpeedSelectorAndStreamViewProps): React.JSX.Element {
  const {
    workspaceId, userId, hat, activeSpeed: initialSpeed = "SPEED_1_FAST", deepAuditPillActive: initialDeepAudit = false,
    selectedTier: initialTier = "medium", selectedEffort: initialEffort, modelOptions = DEFAULT_ASSISTANT_MODEL_OPTIONS,
    agentOptions = DEFAULT_ASSISTANT_AGENT_OPTIONS, skillOptions = DEFAULT_ASSISTANT_SKILL_OPTIONS,
    orciaDocuments = DEFAULT_ORCIA_DOCUMENT_OPTIONS, ragCitations = [], autocompleteSuggestions = [], prefillPrompt = null,
    onPrefillConsumed, activeFolderTitle = null, activeFolderNotes = null, onClearActiveFolder, previousTurnsSlot = null,
    reflexiveTraceSlot = null, welcomeTitle = "Par quoi voulez-vous commencer ?", showWelcomeHero = true,
    hideTechnicalCacheHeader = false, hideLegacySpeedPills = false, hideDuplicateCompletedStream = false, cacheHit = true,
    cacheLookupMs = 1.4, nodes1To4DeterministicMs = 18.2, ttftMs = 398.2, stepProgress, streamedText = "", activeUserPrompt,
    isGenerating = false, initialElapsedSeconds = 0, generationStopped = false, errorMessage = null, labels,
    onOpenFoldersFromPlus, onStopGeneration, onRegenerateLastTurn, onSaveDraftFromResponse, onContinueInProcessFromResponse,
    onInspectCitation, currentTurnFeedback = null, onFeedbackLastTurn, onSendTurn,
  } = props;
  const inputRef = useRef<HTMLInputElement | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const isUserPinnedToBottomRef = useRef<boolean>(true);
  const [isPinnedToBottom, setIsPinnedToBottom] = useState<boolean>(true);
  const [speed, setSpeed] = useState<UiAssistantSpeedMode>(initialDeepAudit ? "SPEED_3_DEEP_AUDIT" : initialSpeed);
  const [deepAuditActive, setDeepAuditActive] = useState<boolean>(initialDeepAudit);
  const [tier, setTier] = useState<UiInferenceTier>(initialTier);
  const [effort, setEffort] = useState<UiInferenceEffort>(initialEffort ?? (initialDeepAudit ? "deep" : "balanced"));
  const [pickerOpen, setPickerOpen] = useState<boolean>(false);
  const [thinkingSubmenuOpen, setThinkingSubmenuOpen] = useState<boolean>(true);
  const [plusMenuOpen, setPlusMenuOpen] = useState<boolean>(false);
  const [promptText, setPromptText] = useState<string>(() => prefillPrompt ?? "");
  const [lastSubmittedPrompt, setLastSubmittedPrompt] = useState<string>("");
  const [lastSubmittedFiles, setLastSubmittedFiles] = useState<readonly UiAssistantAttachedFileItem[]>([]);
  const [userEditedTierOrEffort, setUserEditedTierOrEffort] = useState<boolean>(false);
  const [localStoppedFlag, setLocalStoppedFlag] = useState<boolean>(false);
  const [attachedFiles, setAttachedFiles] = useState<readonly UiAssistantAttachedFileItem[]>([]);
  const [forcedAutocompleteKind, setForcedAutocompleteKind] = useState<"agent" | "skill" | null>(null);

  const cacheKey = `assistant:prompt:${workspaceId}:${userId}:${hat}`;
  const visibleModelCount = modelOptions.filter((m) => !m.hiddenDuplicate).length;
  const activeModelOption =
    modelOptions.find((m) => m.tier === tier) ??
    modelOptions[1] ??
    DEFAULT_ASSISTANT_MODEL_OPTIONS[1]!;
  const normalizedEffort: UiInferenceEffort =
    effort === "deep" ? "deep" : "balanced";
  const activeEffortOption =
    ASSISTANT_EFFORT_OPTIONS.find((e) => e.effort === normalizedEffort) ??
    ASSISTANT_EFFORT_OPTIONS[1]!;

  const handleStreamScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distanceFromBottom > 48 && isUserPinnedToBottomRef.current) {
      isUserPinnedToBottomRef.current = false;
      setIsPinnedToBottom(false);
    } else if (distanceFromBottom <= 24 && !isUserPinnedToBottomRef.current) {
      isUserPinnedToBottomRef.current = true;
      setIsPinnedToBottom(true);
    }
  };

  const scrollToStreamBottom = () => {
    const el = scrollContainerRef.current;
    isUserPinnedToBottomRef.current = true;
    setIsPinnedToBottom(true);
    if (el) el.scrollTop = el.scrollHeight;
  };

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (
      isUserPinnedToBottomRef.current &&
      (streamedText || stepProgress.length > 0 || isGenerating) &&
      el
    ) {
      el.scrollTop = el.scrollHeight;
    }
  }, [streamedText, stepProgress, isGenerating]);

  useEffect(() => {
    if (!prefillPrompt) return;
    setPromptText(prefillPrompt);
    setSpeed("SPEED_2_AGENT_TOOLS");
    setEffort("balanced");
    onPrefillConsumed?.();
    inputRef.current?.focus();
  }, [prefillPrompt, onPrefillConsumed]);

  const extraAgents = autocompleteSuggestions
    .filter((s) => s.kind === "agent")
    .map((s) => ({ slug: s.token.replace(/^@/, ""), label: s.name, description: s.description, kind: "agent" as const }));
  const extraSkills = autocompleteSuggestions
    .filter((s) => s.kind === "skill")
    .map((s) => ({ slug: s.token.replace(/^\//, ""), label: s.name, description: s.description, kind: "skill" as const }));
  const mergedAgentOptions = [...extraAgents, ...agentOptions.filter((a) => !extraAgents.some((e) => e.slug === a.slug))];
  const mergedSkillOptions = [...extraSkills, ...skillOptions.filter((s) => !extraSkills.some((e) => e.slug === s.slug))];
  const effectiveAutocompleteTrigger =
    detectActiveAutocompleteTrigger(promptText) ??
    (forcedAutocompleteKind !== null ? { kind: forcedAutocompleteKind, query: "" } : null);

  const handleSelectEffort = (nextEffort: UiInferenceEffort) => {
    setUserEditedTierOrEffort(true);
    setEffort(nextEffort);
    setDeepAuditActive(nextEffort === "deep");
    setSpeed(nextEffort === "deep" ? "SPEED_3_DEEP_AUDIT" : nextEffort === "balanced" ? "SPEED_2_AGENT_TOOLS" : "SPEED_1_FAST");
  };

  const handlePromptChange = (val: string) => {
    setPromptText(val);
    setForcedAutocompleteKind(null);
    if (!deepAuditActive && !userEditedTierOrEffort) {
      setSpeed(/(?:^|\s)(@[a-zA-Z0-9_-]+|\/[a-zA-Z0-9_-]+)/.test(val) ? "SPEED_2_AGENT_TOOLS" : "SPEED_1_FAST");
      setEffort("balanced");
    }
  };

  const handleSelectAutocompleteOption = (option: UiAssistantAutocompleteOption) => {
    handlePromptChange(applyAutocompleteSelectionToPrompt(promptText, option));
    setForcedAutocompleteKind(null);
    setPlusMenuOpen(false);
    inputRef.current?.focus();
  };

  const triggerSendTurn = (overridePrompt?: string) => {
    const trimmed = (overridePrompt ?? promptText).trim();
    const fallbackPrompt = labels.sendPromptCta.toLowerCase().includes("envoyer")
      ? "Bonjour, peux-tu te présenter brièvement et confirmer que tu es opérationnel ?"
      : "Hello, can you briefly introduce yourself and confirm you are operational?";
    const effectivePrompt = trimmed || lastSubmittedPrompt || fallbackPrompt;
    const submittedFiles = attachedFiles;
    isUserPinnedToBottomRef.current = true;
    setIsPinnedToBottom(true);
    setLastSubmittedPrompt(effectivePrompt);
    setLastSubmittedFiles(submittedFiles);
    setAttachedFiles([]);
    setPromptText("");
    setForcedAutocompleteKind(null);
    setLocalStoppedFlag(false);
    setPickerOpen(false);
    setPlusMenuOpen(false);
    onSendTurn?.({
      userPrompt: effectivePrompt,
      requestedSpeed: speed,
      deepAuditPillActive: deepAuditActive,
      ...(userEditedTierOrEffort ? { requestedTier: tier, thinkingEffort: effort } : {}),
      ...(submittedFiles.length > 0 ? { attachedFiles: submittedFiles } : {}),
    });
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      if (effectiveAutocompleteTrigger !== null) {
        const list = effectiveAutocompleteTrigger.kind === "agent" ? mergedAgentOptions : mergedSkillOptions;
        const q = effectiveAutocompleteTrigger.query.toLowerCase();
        const matches = list.filter((opt) => !q || opt.slug.toLowerCase().includes(q) || opt.label.toLowerCase().includes(q));
        if (matches.length > 0 && (q.length === 0 || !promptText.includes(" "))) {
          e.preventDefault();
          handleSelectAutocompleteOption(matches[0]!);
          return;
        }
      }
      if (!isGenerating) {
        e.preventDefault();
        triggerSendTurn();
      }
    } else if (e.key === "Escape") {
      setForcedAutocompleteKind(null);
      setPlusMenuOpen(false);
    }
  };

  const displayModelBadge =
    activeModelOption.configuredModelName && activeModelOption.title !== activeModelOption.configuredModelName
      ? `${activeModelOption.title} (${activeModelOption.configuredModelName})`
      : activeModelOption.configuredModelName || activeModelOption.title;
  const isStoppedVisible = Boolean(generationStopped || localStoppedFlag) && !isGenerating;
  const actionAriaLabel = isGenerating ? "Arrêter la réflexion de Mon Assistant" : labels.sendPromptCta;
  const shownUserQuestion = activeUserPrompt || lastSubmittedPrompt;
  const cleanStreamedText = sanitizeAssistantDisplayReply(streamedText);
  const mergedRagCitations: readonly UiAssistantRagCitationItem[] = [
    ...ragCitations,
    ...lastSubmittedFiles
      .map((f) => ({ title: f.name, uri: f.uri ?? `#local-file-${encodeURIComponent(f.name)}` }))
      .filter((item) => !ragCitations.some((r) => r.uri === item.uri || r.title === item.title)),
  ];

  return (
    <section
      data-testid="assistant-speed-selector-and-stream"
      style={{ display: "flex", flexDirection: "column", maxHeight: "calc(100vh - 155px)", minHeight: "340px" }}
      className={hideTechnicalCacheHeader ? "pt-1 text-text-primary gap-2.5" : "rounded-xl border border-border-subtle bg-surface-elevated p-5 text-text-primary gap-3"}
    >
      {!hideTechnicalCacheHeader && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2">
          <h3 className="text-sm font-semibold">{labels.headerTitle}</h3>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span data-testid="assistant-prompt-cache-badge" className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 font-mono text-[11px]">{cacheHit ? labels.cacheHitBadge : labels.cacheMissBadge} · {cacheLookupMs} ms · {cacheKey}</span>
            <span data-testid="assistant-nodes-deterministic-badge" className="rounded bg-surface-secondary px-2 py-0.5 font-mono text-[11px] text-text-secondary">{labels.nodesDeterministicLabel}: {nodes1To4DeterministicMs} ms</span>
            <span data-testid="assistant-ttft-badge" className="rounded bg-action-primary/15 px-2 py-0.5 font-mono text-[11px] font-semibold text-action-primary">{labels.ttftBadgePrefix}: {ttftMs} ms</span>
          </div>
        </header>
      )}
      {showWelcomeHero && !cleanStreamedText && !isGenerating && !reflexiveTraceSlot && (
        <div className="py-6 text-center"><h2 data-testid="assistant-welcome-hero-title" className="text-xl font-semibold tracking-tight text-text-primary">{welcomeTitle}</h2></div>
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
          lastSubmittedFiles={lastSubmittedFiles}
          cleanStreamedText={cleanStreamedText}
          stepProgress={stepProgress}
          initialElapsedSeconds={initialElapsedSeconds}
          errorMessage={errorMessage}
          isStoppedVisible={isStoppedVisible}
          mergedRagCitations={mergedRagCitations}
          currentTurnFeedback={currentTurnFeedback}
          onFeedbackLastTurn={onFeedbackLastTurn}
          onRegenerate={() => (onRegenerateLastTurn ? onRegenerateLastTurn() : triggerSendTurn(lastSubmittedPrompt))}
          onSaveDraftFromResponse={onSaveDraftFromResponse}
          onContinueInProcessFromResponse={onContinueInProcessFromResponse}
          onInspectCitation={onInspectCitation}
        />
      </div>

      <AssistantStickyPromptFooter
        inputRef={inputRef}
        isPinnedToBottom={isPinnedToBottom}
        isGenerating={isGenerating}
        plusMenuOpen={plusMenuOpen}
        pickerOpen={pickerOpen}
        thinkingSubmenuOpen={thinkingSubmenuOpen}
        promptText={promptText}
        inputPlaceholder={labels.inputPlaceholder}
        actionAriaLabel={actionAriaLabel}
        visibleModelCount={visibleModelCount}
        displayModelBadge={displayModelBadge}
        activeEffortTitle={activeEffortOption.title}
        tier={tier}
        effort={effort}
        modelOptions={modelOptions}
        effectiveAutocompleteTrigger={effectiveAutocompleteTrigger}
        mergedAgentOptions={mergedAgentOptions}
        mergedSkillOptions={mergedSkillOptions}
        orciaDocuments={orciaDocuments}
        attachedFiles={attachedFiles}
        activeFolderTitle={activeFolderTitle}
        activeFolderNotes={activeFolderNotes}
        onScrollToStreamBottom={scrollToStreamBottom}
        onSelectAutocompleteOption={handleSelectAutocompleteOption}
        onTriggerAgentFromPlus={() => { setPromptText(promptText ? `${promptText} @` : "@"); setForcedAutocompleteKind("agent"); setPlusMenuOpen(false); inputRef.current?.focus(); }}
        onTriggerSkillFromPlus={() => { setPromptText(promptText ? `${promptText} /` : "/"); setForcedAutocompleteKind("skill"); setPlusMenuOpen(false); inputRef.current?.focus(); }}
        onAttachFile={(file) => { setAttachedFiles((prev) => [...prev, file]); setPlusMenuOpen(false); inputRef.current?.focus(); }}
        onRemoveAttachedFile={(fileId) => setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId))}
        onOpenFoldersAndCloseMenus={onOpenFoldersFromPlus ? () => { setPlusMenuOpen(false); setForcedAutocompleteKind(null); setPromptText((prev) => prev.replace(/(?:^|\s)[@/][a-zA-Z0-9_-]*$/, "")); onOpenFoldersFromPlus(); } : undefined}
        onClearActiveFolder={onClearActiveFolder}
        onTogglePlusMenu={() => { setPlusMenuOpen((prev) => !prev); setPickerOpen(false); }}
        onPromptChange={handlePromptChange}
        onInputKeyDown={handleInputKeyDown}
        onTogglePicker={() => { setPickerOpen((prev) => !prev); setPlusMenuOpen(false); }}
        onSendOrStopClick={() => { if (isGenerating) { setLocalStoppedFlag(true); onStopGeneration?.(); inputRef.current?.focus(); return; } triggerSendTurn(); }}
        onSelectTier={(nextTier) => { setUserEditedTierOrEffort(true); setTier(nextTier); }}
        onToggleThinkingSubmenu={() => setThinkingSubmenuOpen((prev) => !prev)}
        onSelectEffort={handleSelectEffort}
      />

      <div role="group" aria-label={labels.headerTitle} data-testid="assistant-legacy-speed-pills-row" style={hideLegacySpeedPills ? { display: "none" } : undefined} className={hideLegacySpeedPills ? "sr-only" : "flex flex-wrap items-center justify-center gap-2 pt-1"}>
        {([["SPEED_1_FAST", "balanced", labels.speed1PillLabel], ["SPEED_2_AGENT_TOOLS", "balanced", labels.speed2PillLabel]] as const).map(([mode, eff, pillLabel]) => (
          <button key={mode} type="button" data-testid={`assistant-speed-pill-${mode}`} aria-pressed={speed === mode} onClick={() => { setDeepAuditActive(false); setSpeed(mode); setEffort(eff); }} className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${speed === mode ? "bg-action-primary text-white" : "bg-surface-secondary text-text-secondary"}`}>{pillLabel}</button>
        ))}
        <button type="button" data-testid="assistant-deep-audit-pill-toggle" aria-pressed={deepAuditActive} onClick={() => { const next = !deepAuditActive; setDeepAuditActive(next); setSpeed(next ? "SPEED_3_DEEP_AUDIT" : "SPEED_1_FAST"); setEffort(next ? "deep" : "balanced"); }} className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${deepAuditActive ? "bg-action-primary text-white" : "border border-border-subtle bg-surface-secondary text-text-secondary"}`}>{labels.speed3DeepAuditPillLabel}</button>
      </div>
    </section>
  );
}
