import React, { useEffect, useRef, useState } from "react";
import type { UiAssistantAttachedFileItem, UiAssistantAutocompleteOption } from "./AssistantPromptPlusAndAutocomplete";
import type { UiAssistantRagCitationItem } from "./AssistantResponseFooterActionsAndCitations";
import type {
  AssistantSpeedSelectorAndStreamViewLabels,
  UiAssistantModelOption,
  UiAssistantSpeedMode,
} from "./AssistantSpeedSelectorTypes";
import type { UiInferenceEffort, UiInferenceTier } from "./InferenceTierAndEffortSelector";

export function useAssistantSpeedViewState({
  initialSpeed,
  initialDeepAudit,
  supportsTools,
  initialTier,
  initialEffort,
  prefillPrompt,
  onPrefillConsumed,
  inputRef,
}: {
  readonly initialSpeed: UiAssistantSpeedMode;
  readonly initialDeepAudit: boolean;
  readonly supportsTools: boolean;
  readonly initialTier: UiInferenceTier;
  readonly initialEffort?: UiInferenceEffort;
  readonly prefillPrompt: string | null;
  readonly onPrefillConsumed?: () => void;
  readonly inputRef: React.RefObject<HTMLInputElement | null>;
}) {
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

  useEffect(() => {
    if (!prefillPrompt) return;
    setPromptText(prefillPrompt);
    setSpeed(supportsTools ? "SPEED_2_AGENT_TOOLS" : "SPEED_1_FAST");
    setEffort(supportsTools ? "balanced" : "fast");
    onPrefillConsumed?.();
    inputRef.current?.focus();
  }, [prefillPrompt, onPrefillConsumed, supportsTools, inputRef]);

  const handleSelectEffort = (nextEffort: UiInferenceEffort) => {
    if (!supportsTools && nextEffort !== "fast") {
      setEffort("fast");
      setDeepAuditActive(false);
      setSpeed("SPEED_1_FAST");
      return;
    }
    setUserEditedTierOrEffort(true);
    setEffort(nextEffort);
    setDeepAuditActive(nextEffort === "deep");
    setSpeed(nextEffort === "deep" ? "SPEED_3_DEEP_AUDIT" : nextEffort === "balanced" ? "SPEED_2_AGENT_TOOLS" : "SPEED_1_FAST");
  };

  const handlePromptChange = (val: string) => {
    setPromptText(val);
    setForcedAutocompleteKind(null);
    if (!supportsTools) {
      setSpeed("SPEED_1_FAST");
      setDeepAuditActive(false);
      setEffort("fast");
      return;
    }
    if (!deepAuditActive && !userEditedTierOrEffort) {
      setSpeed(/(?:^|\s)(@[a-zA-Z0-9_-]+|\/[a-zA-Z0-9_-]+)/.test(val) ? "SPEED_2_AGENT_TOOLS" : "SPEED_1_FAST");
      setEffort("balanced");
    }
  };

  return {
    speed, setSpeed, deepAuditActive, setDeepAuditActive, tier, setTier, effort, setEffort,
    pickerOpen, setPickerOpen, thinkingSubmenuOpen, setThinkingSubmenuOpen, plusMenuOpen, setPlusMenuOpen,
    promptText, setPromptText, lastSubmittedPrompt, setLastSubmittedPrompt, lastSubmittedFiles, setLastSubmittedFiles,
    userEditedTierOrEffort, setUserEditedTierOrEffort, localStoppedFlag, setLocalStoppedFlag,
    attachedFiles, setAttachedFiles, forcedAutocompleteKind, setForcedAutocompleteKind,
    handleSelectEffort, handlePromptChange,
  };
}

export function resolveDisplayModelBadge(activeModelOption: UiAssistantModelOption): string {
  if (activeModelOption.configuredModelName && activeModelOption.title !== activeModelOption.configuredModelName) {
    return `${activeModelOption.title} (${activeModelOption.configuredModelName})`;
  }
  return activeModelOption.configuredModelName || activeModelOption.title;
}

export function mergeRagCitationsWithFiles(
  ragCitations: readonly UiAssistantRagCitationItem[],
  lastSubmittedFiles: readonly UiAssistantAttachedFileItem[],
): readonly UiAssistantRagCitationItem[] {
  return [
    ...ragCitations,
    ...lastSubmittedFiles
      .map((f) => ({ title: f.name, uri: f.uri ?? `#local-file-${encodeURIComponent(f.name)}` }))
      .filter((item) => !ragCitations.some((r) => r.uri === item.uri || r.title === item.title)),
  ];
}

export function resolveEffectiveTurnPrompt(overridePrompt: string | undefined, promptText: string, lastSubmittedPrompt: string, sendPromptCta: string): string {
  const trimmed = (overridePrompt ?? promptText).trim();
  const fallbackPrompt = sendPromptCta.toLowerCase().includes("envoyer")
    ? "Bonjour, peux-tu te présenter brièvement et confirmer que tu es opérationnel ?"
    : "Hello, can you briefly introduce yourself and confirm you are operational?";
  return trimmed || lastSubmittedPrompt || fallbackPrompt;
}

export function findTopAutocompleteMatch(
  kind: "agent" | "skill",
  query: string,
  promptText: string,
  mergedAgentOptions: readonly UiAssistantAutocompleteOption[],
  mergedSkillOptions: readonly UiAssistantAutocompleteOption[],
): UiAssistantAutocompleteOption | null {
  const list = kind === "agent" ? mergedAgentOptions : mergedSkillOptions;
  const q = query.toLowerCase();
  const matches = list.filter((opt) => !q || opt.slug.toLowerCase().includes(q) || opt.label.toLowerCase().includes(q));
  if (matches.length > 0 && (q.length === 0 || !promptText.includes(" "))) {
    return matches[0] ?? null;
  }
  return null;
}

export function useAssistantPinnedScroll(deps: readonly unknown[]) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const isUserPinnedToBottomRef = useRef<boolean>(true);
  const [isPinnedToBottom, setIsPinnedToBottom] = useState<boolean>(true);

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

  const pinToBottomRef = () => {
    isUserPinnedToBottomRef.current = true;
    setIsPinnedToBottom(true);
  };

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (isUserPinnedToBottomRef.current && deps.some(Boolean) && el) {
      el.scrollTop = el.scrollHeight;
      if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
        window.requestAnimationFrame(() => {
          el.scrollTop = el.scrollHeight;
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return {
    scrollContainerRef,
    isPinnedToBottom,
    handleStreamScroll,
    scrollToStreamBottom,
    pinToBottomRef,
  };
}

export function AssistantTechnicalCacheHeader({
  labels,
  cacheHit,
  cacheLookupMs,
  cacheKey,
  nodes1To4DeterministicMs,
  ttftMs,
}: {
  readonly labels: AssistantSpeedSelectorAndStreamViewLabels;
  readonly cacheHit: boolean;
  readonly cacheLookupMs: number;
  readonly cacheKey: string;
  readonly nodes1To4DeterministicMs: number;
  readonly ttftMs: number;
}): React.JSX.Element {
  return (
    <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2">
      <h3 className="text-sm font-semibold">{labels.headerTitle}</h3>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span
          data-testid="assistant-prompt-cache-badge"
          className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 font-mono text-[11px]"
        >
          {cacheHit ? labels.cacheHitBadge : labels.cacheMissBadge} · {cacheLookupMs} ms · {cacheKey}
        </span>
        <span
          data-testid="assistant-nodes-deterministic-badge"
          className="rounded bg-surface-secondary px-2 py-0.5 font-mono text-[11px] text-text-secondary"
        >
          {labels.nodesDeterministicLabel}: {nodes1To4DeterministicMs} ms
        </span>
        <span
          data-testid="assistant-ttft-badge"
          className="rounded bg-action-primary/15 px-2 py-0.5 font-mono text-[11px] font-semibold text-action-primary"
        >
          {labels.ttftBadgePrefix}: {ttftMs} ms
        </span>
      </div>
    </header>
  );
}
