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
  readonly generationStopped?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: AssistantSpeedSelectorAndStreamViewLabels;
  readonly onOpenFoldersFromPlus?: () => void;
  readonly onStopGeneration?: () => void;
  readonly onRegenerateLastTurn?: () => void;
  readonly onSaveDraftFromResponse?: (content: string) => void;
  readonly onContinueInProcessFromResponse?: (content: string) => void;
  readonly onSendTurn?: (payload: {
    userPrompt: string;
    requestedSpeed: UiAssistantSpeedMode;
    deepAuditPillActive: boolean;
    requestedTier?: UiInferenceTier;
    thinkingEffort?: UiInferenceEffort;
    attachedFiles?: readonly UiAssistantAttachedFileItem[];
  }) => void;
}

export function AssistantSpeedSelectorAndStreamView({
  workspaceId,
  userId,
  hat,
  activeSpeed: initialSpeed = "SPEED_1_FAST",
  deepAuditPillActive: initialDeepAudit = false,
  selectedTier: initialTier = "medium",
  selectedEffort: initialEffort,
  modelOptions = DEFAULT_ASSISTANT_MODEL_OPTIONS,
  agentOptions = DEFAULT_ASSISTANT_AGENT_OPTIONS,
  skillOptions = DEFAULT_ASSISTANT_SKILL_OPTIONS,
  orciaDocuments = DEFAULT_ORCIA_DOCUMENT_OPTIONS,
  ragCitations = [],
  autocompleteSuggestions = [],
  prefillPrompt = null,
  onPrefillConsumed,
  welcomeTitle = "Par quoi voulez-vous commencer ?",
  showWelcomeHero = true,
  hideTechnicalCacheHeader = false,
  hideLegacySpeedPills = false,
  hideDuplicateCompletedStream = false,
  cacheHit = true,
  cacheLookupMs = 1.4,
  nodes1To4DeterministicMs = 18.2,
  ttftMs = 398.2,
  stepProgress,
  streamedText = "",
  activeUserPrompt,
  isGenerating = false,
  generationStopped = false,
  errorMessage = null,
  labels,
  onOpenFoldersFromPlus,
  onStopGeneration,
  onRegenerateLastTurn,
  onSaveDraftFromResponse,
  onContinueInProcessFromResponse,
  onSendTurn,
}: AssistantSpeedSelectorAndStreamViewProps): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const streamEndRef = useRef<HTMLDivElement | null>(null);
  const [speed, setSpeed] = useState<UiAssistantSpeedMode>(
    initialDeepAudit ? "SPEED_3_DEEP_AUDIT" : initialSpeed,
  );
  const [deepAuditActive, setDeepAuditActive] = useState<boolean>(initialDeepAudit);
  const [tier, setTier] = useState<UiInferenceTier>(initialTier);
  const [effort, setEffort] = useState<UiInferenceEffort>(
    initialEffort ?? (initialDeepAudit ? "deep" : initialSpeed === "SPEED_2_AGENT_TOOLS" ? "balanced" : "fast"),
  );
  const [pickerOpen, setPickerOpen] = useState<boolean>(false);
  const [thinkingSubmenuOpen, setThinkingSubmenuOpen] = useState<boolean>(true);
  const [plusMenuOpen, setPlusMenuOpen] = useState<boolean>(false);
  const [promptText, setPromptText] = useState<string>(() => prefillPrompt ?? "");
  const [lastSubmittedPrompt, setLastSubmittedPrompt] = useState<string>("");
  const [userEditedTierOrEffort, setUserEditedTierOrEffort] = useState<boolean>(false);
  const [localStoppedFlag, setLocalStoppedFlag] = useState<boolean>(false);
  const [attachedFiles, setAttachedFiles] = useState<readonly UiAssistantAttachedFileItem[]>([]);
  const [forcedAutocompleteKind, setForcedAutocompleteKind] = useState<"agent" | "skill" | null>(null);

  const cacheKey = `assistant:prompt:${workspaceId}:${userId}:${hat}`;
  const activeModelOption =
    modelOptions.find((m) => m.tier === tier) ?? modelOptions[1] ?? DEFAULT_ASSISTANT_MODEL_OPTIONS[1]!;
  const activeEffortOption =
    ASSISTANT_EFFORT_OPTIONS.find((e) => e.effort === effort) ?? ASSISTANT_EFFORT_OPTIONS[0]!;

  useEffect(() => {
    const el = streamEndRef.current;
    if (streamedText && el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [streamedText]);

  useEffect(() => {
    if (prefillPrompt) {
      setPromptText(prefillPrompt);
      setSpeed("SPEED_2_AGENT_TOOLS");
      setEffort("balanced");
      onPrefillConsumed?.();
      inputRef.current?.focus();
    }
  }, [prefillPrompt, onPrefillConsumed]);

  const extraAgentOptions: readonly UiAssistantAutocompleteOption[] = autocompleteSuggestions
    .filter((s) => s.kind === "agent")
    .map((s) => ({
      slug: s.token.replace(/^@/, ""),
      label: s.name,
      description: s.description,
      kind: "agent" as const,
    }));
  const extraSkillOptions: readonly UiAssistantAutocompleteOption[] = autocompleteSuggestions
    .filter((s) => s.kind === "skill")
    .map((s) => ({
      slug: s.token.replace(/^\//, ""),
      label: s.name,
      description: s.description,
      kind: "skill" as const,
    }));
  const mergedAgentOptions: readonly UiAssistantAutocompleteOption[] = [
    ...extraAgentOptions,
    ...agentOptions.filter((a) => !extraAgentOptions.some((e) => e.slug === a.slug)),
  ];
  const mergedSkillOptions: readonly UiAssistantAutocompleteOption[] = [
    ...extraSkillOptions,
    ...skillOptions.filter((s) => !extraSkillOptions.some((e) => e.slug === s.slug)),
  ];

  const detectedTrigger = detectActiveAutocompleteTrigger(promptText);
  const effectiveAutocompleteTrigger =
    detectedTrigger ?? (forcedAutocompleteKind !== null ? { kind: forcedAutocompleteKind, query: "" } : null);

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
      const hasAgentOrSkill = /(?:^|\s)(@[a-zA-Z0-9_-]+|\/[a-zA-Z0-9_-]+)/.test(val);
      setSpeed(hasAgentOrSkill ? "SPEED_2_AGENT_TOOLS" : "SPEED_1_FAST");
      setEffort(hasAgentOrSkill ? "balanced" : "fast");
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
    const effectivePrompt =
      trimmed ||
      lastSubmittedPrompt ||
      (labels.sendPromptCta.toLowerCase().includes("envoyer")
        ? "Bonjour, peux-tu te présenter brièvement et confirmer que tu es opérationnel ?"
        : "Hello, can you briefly introduce yourself and confirm you are operational?");
    setLastSubmittedPrompt(effectivePrompt);
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
      ...(attachedFiles.length > 0 ? { attachedFiles } : {}),
    });
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      if (effectiveAutocompleteTrigger !== null) {
        const list = effectiveAutocompleteTrigger.kind === "agent" ? mergedAgentOptions : mergedSkillOptions;
        const q = effectiveAutocompleteTrigger.query.toLowerCase();
        const matches = list.filter(
          (opt) => !q || opt.slug.toLowerCase().includes(q) || opt.label.toLowerCase().includes(q),
        );
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

  const displayModelBadge = activeModelOption.configuredModelName
    ? `${activeModelOption.title} (${activeModelOption.configuredModelName})`
    : activeModelOption.title;
  const isStoppedVisible = Boolean(generationStopped || localStoppedFlag) && !isGenerating;
  const actionAriaLabel = isGenerating ? "Arrêter la réflexion de Mon Assistant" : labels.sendPromptCta;
  const shownUserQuestion = activeUserPrompt || (isGenerating ? lastSubmittedPrompt : "");
  const mergedRagCitations: readonly UiAssistantRagCitationItem[] = [
    ...ragCitations,
    ...attachedFiles
      .filter((f): f is UiAssistantAttachedFileItem & { readonly uri: string } => Boolean(f.uri))
      .map((f) => ({ title: f.name, uri: f.uri })),
  ];

  return (
    <section data-testid="assistant-speed-selector-and-stream" className="rounded-xl border border-border-subtle bg-surface-elevated p-5 text-text-primary space-y-4">
      {!hideTechnicalCacheHeader && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2">
          <h3 className="text-sm font-semibold">{labels.headerTitle}</h3>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span data-testid="assistant-prompt-cache-badge" className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 font-mono text-[11px]">
              {cacheHit ? labels.cacheHitBadge : labels.cacheMissBadge} · {cacheLookupMs} ms · {cacheKey}
            </span>
            <span data-testid="assistant-nodes-deterministic-badge" className="rounded bg-surface-secondary px-2 py-0.5 font-mono text-[11px] text-text-secondary">
              {labels.nodesDeterministicLabel}: {nodes1To4DeterministicMs} ms
            </span>
            <span data-testid="assistant-ttft-badge" className="rounded bg-action-primary/15 px-2 py-0.5 font-mono text-[11px] font-semibold text-action-primary">
              {labels.ttftBadgePrefix}: {ttftMs} ms
            </span>
          </div>
        </header>
      )}

      {showWelcomeHero && !streamedText && !isGenerating && (
        <div className="py-6 text-center space-y-1.5">
          <h2 data-testid="assistant-welcome-hero-title" className="text-xl font-semibold tracking-tight text-text-primary">{welcomeTitle}</h2>
        </div>
      )}

      {shownUserQuestion ? <AssistantUserQuestionBubble userPrompt={shownUserQuestion} modelLabel={displayModelBadge} effortLabel={activeEffortOption.title} /> : null}
      {isGenerating && !streamedText && <AssistantThinkingSliderIndicator />}
      <AssistantThinkingSubWindow stepProgress={stepProgress} isGenerating={isGenerating} hasStreamedResponse={Boolean(streamedText && !streamedText.startsWith("⏳"))} />

      {errorMessage && (
        <div role="alert" data-testid="assistant-error-banner" className="rounded border border-status-warning/40 bg-status-warning/10 p-2.5 text-xs font-medium text-status-warning">
          {errorMessage}
        </div>
      )}

      {(streamedText || isStoppedVisible) && (
        <div
          data-testid="assistant-streamed-response-box"
          aria-live="polite"
          style={hideDuplicateCompletedStream && !isStoppedVisible ? { display: "none" } : undefined}
          className={hideDuplicateCompletedStream && !isStoppedVisible ? "sr-only" : "rounded-lg border border-border-subtle bg-surface-primary p-4 text-xs leading-relaxed space-y-2"}
        >
          {streamedText ? <FormattedMarkdownContent content={streamedText} /> : null}
          {isStoppedVisible ? (
            <div data-testid="assistant-generation-stopped-badge" className="inline-flex items-center gap-1.5 rounded border border-border-subtle bg-surface-secondary px-2.5 py-1 text-[11px] font-medium text-text-secondary">
              ⏹ Génération interrompue par l&apos;utilisateur
            </div>
          ) : null}
          {!isGenerating && streamedText && !hideDuplicateCompletedStream ? (
            <AssistantResponseFooterActionsAndCitations
              responseText={streamedText}
              ragCitations={mergedRagCitations}
              onRegenerate={() => (onRegenerateLastTurn ? onRegenerateLastTurn() : triggerSendTurn(lastSubmittedPrompt))}
              onSaveDraft={onSaveDraftFromResponse}
              onContinueInProcess={onContinueInProcessFromResponse}
            />
          ) : null}
          <div ref={streamEndRef} />
        </div>
      )}

      <div className="relative">
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
          onAttachFile={(file) => { setAttachedFiles((prev) => [...prev, file]); setPlusMenuOpen(false); }}
          onRemoveAttachedFile={(fileId) => setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId))}
          onOpenFoldersAndCloseMenus={
            onOpenFoldersFromPlus
              ? () => { setPlusMenuOpen(false); setForcedAutocompleteKind(null); setPromptText((prev) => prev.replace(/(?:^|\s)[@/][a-zA-Z0-9_-]*$/, "")); onOpenFoldersFromPlus(); }
              : undefined
          }
        />

        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border-subtle bg-surface-primary px-3 py-2 shadow-sm">
          <button type="button" data-testid="assistant-prompt-plus-btn" aria-label="Actions rapides et dossiers" onClick={() => { setPlusMenuOpen((prev) => !prev); setPickerOpen(false); }} className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-border-subtle bg-surface-secondary text-sm font-semibold text-text-primary hover:bg-surface-elevated">+</button>
          <input ref={inputRef} type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="assistant-three-speed-input" value={promptText} placeholder={labels.inputPlaceholder} onChange={(e) => handlePromptChange(e.target.value)} onKeyDown={handleInputKeyDown} className="flex-1 min-w-[200px] border-0 bg-transparent px-2 py-1 text-xs text-text-primary focus:outline-none" />
          <button type="button" data-testid="assistant-model-and-effort-picker-trigger" aria-expanded={pickerOpen} onClick={() => { setPickerOpen((prev) => !prev); setPlusMenuOpen(false); }} className="inline-flex items-center gap-1.5 rounded-full border border-border-subtle bg-surface-secondary px-3 py-1 text-xs font-medium text-text-primary hover:bg-surface-elevated">
            <span>{displayModelBadge}</span>
            <span className="text-text-secondary">· {activeEffortOption.title}</span>
            <span aria-hidden="true">▾</span>
          </button>
          <button type="button" data-testid="assistant-three-speed-send-btn" aria-label={actionAriaLabel} title={actionAriaLabel} onClick={() => { if (isGenerating) { setLocalStoppedFlag(true); onStopGeneration?.(); inputRef.current?.focus(); return; } triggerSendTurn(); }} className="inline-flex items-center gap-1.5 rounded-full bg-action-primary px-3.5 py-1.5 text-xs font-semibold text-white hover:opacity-95">
            {isGenerating ? (<><span data-testid="assistant-stop-square-icon" aria-hidden="true">■</span><span>Arrêter</span></>) : (<><span data-testid="assistant-send-play-icon" aria-hidden="true">▶</span><span>{labels.sendPromptCta}</span></>)}
          </button>
        </div>

        {pickerOpen && (
          <AssistantModelAndEffortPopover
            modelOptions={modelOptions}
            selectedTier={tier}
            selectedEffort={effort}
            thinkingSubmenuOpen={thinkingSubmenuOpen}
            onSelectTier={(nextTier) => { setUserEditedTierOrEffort(true); setTier(nextTier); }}
            onToggleThinkingSubmenu={() => setThinkingSubmenuOpen((prev) => !prev)}
            onSelectEffort={handleSelectEffort}
          />
        )}
      </div>

      <div role="group" aria-label={labels.headerTitle} data-testid="assistant-legacy-speed-pills-row" style={hideLegacySpeedPills ? { display: "none" } : undefined} className={hideLegacySpeedPills ? "sr-only" : "flex flex-wrap items-center justify-center gap-2 pt-1"}>
        {(
          [
            ["SPEED_1_FAST", "fast", labels.speed1PillLabel],
            ["SPEED_2_AGENT_TOOLS", "balanced", labels.speed2PillLabel],
          ] as const
        ).map(([mode, eff, pillLabel]) => (
          <button key={mode} type="button" data-testid={`assistant-speed-pill-${mode}`} aria-pressed={speed === mode} onClick={() => { setDeepAuditActive(false); setSpeed(mode); setEffort(eff); }} className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${speed === mode ? "bg-action-primary text-white" : "bg-surface-secondary text-text-secondary"}`}>{pillLabel}</button>
        ))}
        <button type="button" data-testid="assistant-deep-audit-pill-toggle" aria-pressed={deepAuditActive} onClick={() => { const next = !deepAuditActive; setDeepAuditActive(next); setSpeed(next ? "SPEED_3_DEEP_AUDIT" : "SPEED_1_FAST"); setEffort(next ? "deep" : "fast"); }} className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${deepAuditActive ? "bg-action-primary text-white" : "border border-border-subtle bg-surface-secondary text-text-secondary"}`}>{labels.speed3DeepAuditPillLabel}</button>
      </div>
    </section>
  );
}
