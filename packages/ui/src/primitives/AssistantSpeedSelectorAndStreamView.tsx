import React, { useEffect, useRef, useState } from "react";
import { FormattedMarkdownContent } from "../components/FormattedMarkdownContent";
import {
  ASSISTANT_EFFORT_OPTIONS,
  AssistantModelAndEffortPopover,
  DEFAULT_ASSISTANT_MODEL_OPTIONS,
  type UiAssistantAutocompleteSuggestion,
  type UiAssistantModelOption,
} from "./AssistantModelAndEffortPopover";
import {
  applyAutocompleteSelectionToPrompt,
  AssistantAttachedFilesInlineBar,
  AssistantPromptPlusAndAutocomplete,
  DEFAULT_ASSISTANT_AGENT_OPTIONS,
  DEFAULT_ASSISTANT_SKILL_OPTIONS,
  DEFAULT_ORCIA_DOCUMENT_OPTIONS,
  detectActiveAutocompleteTrigger,
  type UiAssistantAttachedFileItem,
  type UiAssistantAutocompleteOption,
  type UiAssistantOrciaDocumentOption,
} from "./AssistantPromptPlusAndAutocomplete";
import {
  AssistantResponseFooterActionsAndCitations,
  AssistantThinkingSliderIndicator,
  AssistantUserQuestionBubble,
  sanitizeAssistantDisplayReply,
  type UiAssistantRagCitationItem,
} from "./AssistantResponseFooterActionsAndCitations";
import { AssistantThinkingSubWindow } from "./AssistantThinkingSubWindow";
import type { UiInferenceEffort, UiInferenceTier } from "./InferenceTierAndEffortSelector";

export type { UiAssistantAutocompleteSuggestion, UiAssistantModelOption };
export type UiAssistantSpeedMode = "SPEED_1_FAST" | "SPEED_2_AGENT_TOOLS" | "SPEED_3_DEEP_AUDIT";

export interface UiThreeSpeedStepProgress {
  readonly stepCode: string;
  readonly label: string;
  readonly durationMs: number;
  readonly status: "COMPLETED" | "RUNNING";
  readonly connectorOrLens?: string | null;
  readonly intermediateOutput?: string | null;
}

export interface AssistantSpeedSelectorAndStreamViewLabels {
  readonly headerTitle: string;
  readonly speed1PillLabel: string;
  readonly speed2PillLabel: string;
  readonly speed3DeepAuditPillLabel: string;
  readonly cacheHitBadge: string;
  readonly cacheMissBadge: string;
  readonly nodesDeterministicLabel: string;
  readonly ttftBadgePrefix: string;
  readonly inputPlaceholder: string;
  readonly sendPromptCta: string;
}

export interface AssistantSpeedSelectorAndStreamViewProps {
  readonly workspaceId: string;
  readonly userId: string;
  readonly hat: string;
  readonly activeSpeed?: UiAssistantSpeedMode;
  readonly deepAuditPillActive?: boolean;
  readonly selectedTier?: UiInferenceTier;
  readonly selectedEffort?: UiInferenceEffort;
  readonly modelOptions?: readonly UiAssistantModelOption[];
  readonly agentOptions?: readonly UiAssistantAutocompleteOption[];
  readonly skillOptions?: readonly UiAssistantAutocompleteOption[];
  readonly orciaDocuments?: readonly UiAssistantOrciaDocumentOption[];
  readonly ragCitations?: readonly UiAssistantRagCitationItem[];
  readonly autocompleteSuggestions?: readonly UiAssistantAutocompleteSuggestion[];
  readonly prefillPrompt?: string | null;
  readonly onPrefillConsumed?: () => void;
  readonly activeFolderTitle?: string | null;
  readonly activeFolderNotes?: string | null;
  readonly onClearActiveFolder?: () => void;
  readonly previousTurnsSlot?: React.ReactNode;
  readonly welcomeTitle?: string;
  readonly showWelcomeHero?: boolean;
  readonly hideTechnicalCacheHeader?: boolean;
  readonly hideLegacySpeedPills?: boolean;
  readonly hideDuplicateCompletedStream?: boolean;
  readonly cacheHit?: boolean;
  readonly cacheLookupMs?: number;
  readonly nodes1To4DeterministicMs?: number;
  readonly ttftMs?: number;
  readonly stepProgress: readonly UiThreeSpeedStepProgress[];
  readonly streamedText?: string;
  readonly activeUserPrompt?: string;
  readonly isGenerating?: boolean;
  readonly initialElapsedSeconds?: number;
  readonly generationStopped?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: AssistantSpeedSelectorAndStreamViewLabels;
  readonly onOpenFoldersFromPlus?: () => void;
  readonly onStopGeneration?: () => void;
  readonly onRegenerateLastTurn?: () => void;
  readonly onSaveDraftFromResponse?: (content: string) => void;
  readonly onContinueInProcessFromResponse?: (content: string) => void;
  readonly currentTurnFeedback?: "LIKE" | "DISLIKE" | null;
  readonly onFeedbackLastTurn?: (feedback: "LIKE" | "DISLIKE" | null) => void;
  readonly onSendTurn?: (payload: {
    userPrompt: string;
    requestedSpeed: UiAssistantSpeedMode;
    deepAuditPillActive: boolean;
    requestedTier?: UiInferenceTier;
    thinkingEffort?: UiInferenceEffort;
    attachedFiles?: readonly UiAssistantAttachedFileItem[];
  }) => void;
}

export function AssistantSpeedSelectorAndStreamView(props: AssistantSpeedSelectorAndStreamViewProps): React.JSX.Element {
  const {
    workspaceId, userId, hat, activeSpeed: initialSpeed = "SPEED_1_FAST", deepAuditPillActive: initialDeepAudit = false,
    selectedTier: initialTier = "medium", selectedEffort: initialEffort, modelOptions = DEFAULT_ASSISTANT_MODEL_OPTIONS,
    agentOptions = DEFAULT_ASSISTANT_AGENT_OPTIONS, skillOptions = DEFAULT_ASSISTANT_SKILL_OPTIONS,
    orciaDocuments = DEFAULT_ORCIA_DOCUMENT_OPTIONS, ragCitations = [], autocompleteSuggestions = [], prefillPrompt = null,
    onPrefillConsumed, activeFolderTitle = null, activeFolderNotes = null, onClearActiveFolder, previousTurnsSlot = null,
    welcomeTitle = "Par quoi voulez-vous commencer ?", showWelcomeHero = true, hideTechnicalCacheHeader = false,
    hideLegacySpeedPills = false, hideDuplicateCompletedStream = false, cacheHit = true, cacheLookupMs = 1.4,
    nodes1To4DeterministicMs = 18.2, ttftMs = 398.2, stepProgress, streamedText = "", activeUserPrompt,
    isGenerating = false, initialElapsedSeconds = 0, generationStopped = false, errorMessage = null, labels,
    onOpenFoldersFromPlus, onStopGeneration, onRegenerateLastTurn, onSaveDraftFromResponse, onContinueInProcessFromResponse,
    currentTurnFeedback = null, onFeedbackLastTurn, onSendTurn,
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
  const activeModelOption = modelOptions.find((m) => m.tier === tier) ?? modelOptions[1] ?? DEFAULT_ASSISTANT_MODEL_OPTIONS[1]!;
  const normalizedEffort: UiInferenceEffort = effort === "deep" ? "deep" : "balanced";
  const activeEffortOption = ASSISTANT_EFFORT_OPTIONS.find((e) => e.effort === normalizedEffort) ?? ASSISTANT_EFFORT_OPTIONS[1]!;

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
    if (isUserPinnedToBottomRef.current && (streamedText || stepProgress.length > 0 || isGenerating) && el) {
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

  const extraAgents = autocompleteSuggestions.filter((s) => s.kind === "agent").map((s) => ({ slug: s.token.replace(/^@/, ""), label: s.name, description: s.description, kind: "agent" as const }));
  const extraSkills = autocompleteSuggestions.filter((s) => s.kind === "skill").map((s) => ({ slug: s.token.replace(/^\//, ""), label: s.name, description: s.description, kind: "skill" as const }));
  const mergedAgentOptions = [...extraAgents, ...agentOptions.filter((a) => !extraAgents.some((e) => e.slug === a.slug))];
  const mergedSkillOptions = [...extraSkills, ...skillOptions.filter((s) => !extraSkills.some((e) => e.slug === s.slug))];
  const effectiveAutocompleteTrigger = detectActiveAutocompleteTrigger(promptText) ?? (forcedAutocompleteKind !== null ? { kind: forcedAutocompleteKind, query: "" } : null);

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
    ...lastSubmittedFiles.map((f) => ({ title: f.name, uri: f.uri ?? `#local-file-${encodeURIComponent(f.name)}` })).filter((item) => !ragCitations.some((r) => r.uri === item.uri || r.title === item.title)),
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
      {showWelcomeHero && !cleanStreamedText && !isGenerating && (
        <div className="py-6 text-center"><h2 data-testid="assistant-welcome-hero-title" className="text-xl font-semibold tracking-tight text-text-primary">{welcomeTitle}</h2></div>
      )}
      <div
        ref={scrollContainerRef}
        onScroll={handleStreamScroll}
        data-testid="assistant-central-scrollable-stream"
        data-pinned-to-bottom={isPinnedToBottom ? "true" : "false"}
        style={{ flex: "1 1 auto", minHeight: 0, overflowY: "auto" }}
        className="space-y-3 pr-1"
      >
        {previousTurnsSlot}
        {shownUserQuestion && (!hideDuplicateCompletedStream || isGenerating) ? (
          <AssistantUserQuestionBubble userPrompt={shownUserQuestion} modelLabel={displayModelBadge} effortLabel={activeEffortOption.title} attachedFiles={lastSubmittedFiles} />
        ) : null}
        {isGenerating && !cleanStreamedText ? <div className="py-2 my-1"><AssistantThinkingSliderIndicator /></div> : null}
        {!hideDuplicateCompletedStream ? (
          <div data-testid="assistant-active-research-zone" className="py-1 flex flex-col items-start justify-center gap-2">
            <AssistantThinkingSubWindow stepProgress={stepProgress} isGenerating={isGenerating} initialElapsedSeconds={initialElapsedSeconds} hasStreamedResponse={Boolean(cleanStreamedText && !cleanStreamedText.startsWith("⏳"))} />
          </div>
        ) : null}
        {errorMessage && (
          <div role="alert" data-testid="assistant-error-banner" className="rounded border border-status-warning/40 bg-status-warning/10 p-2.5 text-xs font-medium text-status-warning">{errorMessage}</div>
        )}
        {(cleanStreamedText || isStoppedVisible) && (
          <div data-testid="assistant-streamed-response-box" aria-live="polite" style={hideDuplicateCompletedStream && !isStoppedVisible ? { display: "none" } : undefined} className={hideDuplicateCompletedStream && !isStoppedVisible ? "sr-only" : "rounded-lg bg-surface-primary py-2 text-xs leading-relaxed space-y-2"}>
            {cleanStreamedText ? <FormattedMarkdownContent content={cleanStreamedText} /> : null}
            {isStoppedVisible ? (
              <div data-testid="assistant-generation-stopped-badge" className="inline-flex items-center gap-1.5 rounded border border-border-subtle bg-surface-secondary px-2.5 py-1 text-[11px] font-medium text-text-secondary">⏹ Génération interrompue par l&apos;utilisateur</div>
            ) : null}
            {!isGenerating && cleanStreamedText && !hideDuplicateCompletedStream ? (
              <AssistantResponseFooterActionsAndCitations responseText={cleanStreamedText} modelLabel={displayModelBadge} effortLabel={activeEffortOption.title} ragCitations={mergedRagCitations} initialFeedback={currentTurnFeedback} onFeedbackChange={onFeedbackLastTurn} onRegenerate={() => (onRegenerateLastTurn ? onRegenerateLastTurn() : triggerSendTurn(lastSubmittedPrompt))} onSaveDraft={onSaveDraftFromResponse} onContinueInProcess={onContinueInProcessFromResponse} />
            ) : null}
          </div>
        )}
      </div>

      <div data-testid="assistant-sticky-prompt-footer" style={{ flexShrink: 0, position: "sticky", bottom: 0, zIndex: 20, backgroundColor: "var(--color-bg-surface)", paddingTop: "6px" }} className="relative">
        {!isPinnedToBottom && isGenerating ? (
          <div className="mb-1.5 flex justify-center">
            <button type="button" data-testid="assistant-resume-autoscroll-btn" onClick={scrollToStreamBottom} className="inline-flex items-center gap-1 rounded-full border border-border-subtle bg-surface-elevated px-3 py-0.5 text-[11px] font-medium text-action-primary shadow-sm hover:bg-surface-secondary">
              ↓ Suivre la réponse en direct
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
          onSelectAutocompleteOption={handleSelectAutocompleteOption}
          onTriggerAgentAutocompleteFromPlus={() => { setPromptText(promptText ? `${promptText} @` : "@"); setForcedAutocompleteKind("agent"); setPlusMenuOpen(false); inputRef.current?.focus(); }}
          onTriggerSkillAutocompleteFromPlus={() => { setPromptText(promptText ? `${promptText} /` : "/"); setForcedAutocompleteKind("skill"); setPlusMenuOpen(false); inputRef.current?.focus(); }}
          onAttachFile={(file) => { setAttachedFiles((prev) => [...prev, file]); setPlusMenuOpen(false); inputRef.current?.focus(); }}
          onRemoveAttachedFile={(fileId) => setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId))}
          onOpenFoldersAndCloseMenus={onOpenFoldersFromPlus ? () => { setPlusMenuOpen(false); setForcedAutocompleteKind(null); setPromptText((prev) => prev.replace(/(?:^|\s)[@/][a-zA-Z0-9_-]*$/, "")); onOpenFoldersFromPlus(); } : undefined}
        />
        {activeFolderTitle ? (
          <div data-testid="assistant-prompt-active-folder-badge" className="mb-1.5 inline-flex flex-wrap items-center gap-1.5 rounded-full border border-action-primary/30 bg-action-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-action-primary">
            <span>📁 Dossier actif : <strong>{activeFolderTitle}</strong></span>
            {activeFolderNotes && activeFolderNotes.trim() ? <span data-testid="assistant-prompt-active-folder-note-indicator" className="text-text-secondary">· 📌 Note active prise en compte par l&apos;Assistant</span> : null}
            {onClearActiveFolder ? <button type="button" data-testid="assistant-prompt-clear-active-folder-btn" onClick={onClearActiveFolder} aria-label="Détacher le dossier actif" className="ml-1 font-bold hover:opacity-80">×</button> : null}
          </div>
        ) : null}
        <div className="rounded-2xl border border-border-subtle bg-surface-primary px-3 py-2 shadow-sm space-y-1.5">
          <AssistantAttachedFilesInlineBar attachedFiles={attachedFiles} onRemoveAttachedFile={(fileId) => setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId))} />
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" data-testid="assistant-prompt-plus-btn" aria-label="Actions rapides et dossiers" onClick={() => { setPlusMenuOpen((prev) => !prev); setPickerOpen(false); }} className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-border-subtle bg-surface-secondary text-sm font-semibold text-text-primary hover:bg-surface-elevated">+</button>
            <input ref={inputRef} type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="assistant-three-speed-input" value={promptText} placeholder={labels.inputPlaceholder} onChange={(e) => handlePromptChange(e.target.value)} onKeyDown={handleInputKeyDown} className="flex-1 min-w-[200px] border-0 bg-transparent px-2 py-1 text-xs text-text-primary focus:outline-none" />
            <button type="button" data-testid="assistant-model-and-effort-picker-trigger" aria-expanded={pickerOpen} onClick={() => { setPickerOpen((prev) => !prev); setPlusMenuOpen(false); }} className="inline-flex items-center gap-1.5 rounded-full border border-border-subtle bg-surface-secondary px-3 py-1 text-xs font-medium text-text-primary hover:bg-surface-elevated">
              {visibleModelCount === 1 ? <span>{activeEffortOption.title}</span> : (<><span>{displayModelBadge}</span><span className="text-text-secondary">· {activeEffortOption.title}</span></>)}
              <span aria-hidden="true">▾</span>
            </button>
            <button type="button" data-testid="assistant-three-speed-send-btn" aria-label={actionAriaLabel} title={isGenerating ? "Arrêter" : "Envoyer"} onClick={() => { if (isGenerating) { setLocalStoppedFlag(true); onStopGeneration?.(); inputRef.current?.focus(); return; } triggerSendTurn(); }} className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-action-primary text-xs font-semibold text-white hover:opacity-95">
              {isGenerating ? <span data-testid="assistant-stop-square-icon" aria-hidden="true">■</span> : <span data-testid="assistant-send-play-icon" aria-hidden="true">▶</span>}
            </button>
          </div>
        </div>
        {pickerOpen && (
          <AssistantModelAndEffortPopover modelOptions={modelOptions} selectedTier={tier} selectedEffort={effort} thinkingSubmenuOpen={thinkingSubmenuOpen} onSelectTier={(nextTier) => { setUserEditedTierOrEffort(true); setTier(nextTier); }} onToggleThinkingSubmenu={() => setThinkingSubmenuOpen((prev) => !prev)} onSelectEffort={handleSelectEffort} />
        )}
      </div>

      <div role="group" aria-label={labels.headerTitle} data-testid="assistant-legacy-speed-pills-row" style={hideLegacySpeedPills ? { display: "none" } : undefined} className={hideLegacySpeedPills ? "sr-only" : "flex flex-wrap items-center justify-center gap-2 pt-1"}>
        {([["SPEED_1_FAST", "balanced", labels.speed1PillLabel], ["SPEED_2_AGENT_TOOLS", "balanced", labels.speed2PillLabel]] as const).map(([mode, eff, pillLabel]) => (
          <button key={mode} type="button" data-testid={`assistant-speed-pill-${mode}`} aria-pressed={speed === mode} onClick={() => { setDeepAuditActive(false); setSpeed(mode); setEffort(eff); }} className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${speed === mode ? "bg-action-primary text-white" : "bg-surface-secondary text-text-secondary"}`}>{pillLabel}</button>
        ))}
        <button type="button" data-testid="assistant-deep-audit-pill-toggle" aria-pressed={deepAuditActive} onClick={() => { const next = !deepAuditActive; setDeepAuditActive(next); setSpeed(next ? "SPEED_3_DEEP_AUDIT" : "SPEED_1_FAST"); setEffort(next ? "deep" : "balanced"); }} className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${deepAuditActive ? "bg-action-primary text-white" : "border border-border-subtle bg-surface-secondary text-text-secondary"}`}>{labels.speed3DeepAuditPillLabel}</button>
      </div>
    </section>
  );
}
