import React from "react";
import { OrciaIcon } from "../components/icons";
import type { UiAssistantAutocompleteSuggestion } from "./AssistantAutocompleteDropdown";
import type { UiAssistantAutocompleteOption } from "./AssistantPromptPlusAndAutocomplete";
import type {
  AssistantSpeedSelectorAndStreamViewLabels,
  UiAssistantSpeedMode,
} from "./AssistantSpeedSelectorTypes";
import type { UiInferenceEffort } from "./InferenceTierAndEffortSelector";

export function AssistantActiveFolderPromptBadge({
  activeFolderTitle,
  activeFolderNotes,
  onClearActiveFolder,
}: {
  readonly activeFolderTitle: string | null;
  readonly activeFolderNotes: string | null;
  readonly onClearActiveFolder?: (() => void) | undefined;
}): React.JSX.Element | null {
  if (!activeFolderTitle) return null;
  return (
    <div
      data-testid="assistant-prompt-active-folder-badge"
      className="mb-1.5 inline-flex flex-wrap items-center gap-1.5 rounded-full border border-action-primary/30 bg-action-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-action-primary"
    >
      <span>
        <OrciaIcon name="folder" /> Dossier actif : <strong>{activeFolderTitle}</strong>
      </span>
      {activeFolderNotes && activeFolderNotes.trim() ? (
        <span
          data-testid="assistant-prompt-active-folder-note-indicator"
          className="text-text-secondary"
        >
          · <OrciaIcon name="pin" /> Note active prise en compte par l&apos;Assistant
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
  );
}

export function AssistantToolsUnsupportedNotice({
  supportsTools,
  toolsUnsupportedNotice,
}: {
  readonly supportsTools: boolean;
  readonly toolsUnsupportedNotice?: string | undefined;
}): React.JSX.Element | null {
  if (supportsTools || !toolsUnsupportedNotice) return null;
  return (
    <div
      role="status"
      data-testid="assistant-tools-unsupported-notice"
      style={{
        backgroundColor: "var(--color-arbitration-bg)",
        borderColor: "var(--color-arbitration-amber)",
        color: "var(--color-text-primary)",
      }}
      className="mb-1.5 rounded border px-2.5 py-1.5 text-[11px] font-medium"
    >
      {toolsUnsupportedNotice}
    </div>
  );
}

export function AssistantLegacySpeedPillsRow({
  labels,
  hideLegacySpeedPills,
  supportsTools,
  speed,
  deepAuditActive,
  onSelectSpeed,
  onToggleDeepAudit,
}: {
  readonly labels: AssistantSpeedSelectorAndStreamViewLabels;
  readonly hideLegacySpeedPills: boolean;
  readonly supportsTools: boolean;
  readonly speed: UiAssistantSpeedMode;
  readonly deepAuditActive: boolean;
  readonly onSelectSpeed: (mode: UiAssistantSpeedMode, effort: UiInferenceEffort) => void;
  readonly onToggleDeepAudit: () => void;
}): React.JSX.Element | null {
  if (hideLegacySpeedPills) return null;
  return (
    <div
      role="group"
      aria-label={labels.headerTitle}
      data-testid="assistant-legacy-speed-pills-row"
      className="flex flex-wrap items-center justify-center gap-2 pt-1"
    >
      {(
        [
          ["SPEED_1_FAST", "balanced", labels.speed1PillLabel],
          ["SPEED_2_AGENT_TOOLS", "balanced", labels.speed2PillLabel],
        ] as const
      ).map(([mode, eff, pillLabel]) => {
        const pillDisabled = !supportsTools && mode !== "SPEED_1_FAST";
        return (
          <button
            key={mode}
            type="button"
            disabled={pillDisabled}
            data-testid={`assistant-speed-pill-${mode}`}
            aria-pressed={speed === mode}
            onClick={() => {
              if (!pillDisabled) onSelectSpeed(mode, eff);
            }}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              pillDisabled
                ? "opacity-50 cursor-not-allowed bg-surface-secondary text-text-secondary"
                : speed === mode
                  ? "bg-action-primary text-white"
                  : "bg-surface-secondary text-text-secondary"
            }`}
          >
            {pillLabel}
          </button>
        );
      })}
      <button
        type="button"
        disabled={!supportsTools}
        data-testid="assistant-deep-audit-pill-toggle"
        aria-pressed={deepAuditActive}
        onClick={() => {
          if (supportsTools) onToggleDeepAudit();
        }}
        className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
          !supportsTools
            ? "opacity-50 cursor-not-allowed border border-border-subtle bg-surface-secondary text-text-secondary"
            : deepAuditActive
              ? "bg-action-primary text-white"
              : "border border-border-subtle bg-surface-secondary text-text-secondary"
        }`}
      >
        {labels.speed3DeepAuditPillLabel}
      </button>
    </div>
  );
}

export function mergeAssistantAutocompleteOptions(
  autocompleteSuggestions: readonly UiAssistantAutocompleteSuggestion[],
  agentOptions: readonly UiAssistantAutocompleteOption[],
  skillOptions: readonly UiAssistantAutocompleteOption[],
): {
  readonly mergedAgentOptions: readonly UiAssistantAutocompleteOption[];
  readonly mergedSkillOptions: readonly UiAssistantAutocompleteOption[];
} {
  const extraAgents = autocompleteSuggestions
    .filter((s) => s.kind === "agent")
    .map((s) => ({
      slug: s.token.replace(/^@/, ""),
      label: s.name,
      description: s.description,
      kind: "agent" as const,
    }));
  const extraSkills = autocompleteSuggestions
    .filter((s) => s.kind === "skill")
    .map((s) => ({
      slug: s.token.replace(/^\//, ""),
      label: s.name,
      description: s.description,
      kind: "skill" as const,
    }));
  return {
    mergedAgentOptions: [
      ...extraAgents,
      ...agentOptions.filter((a) => !extraAgents.some((e) => e.slug === a.slug)),
    ],
    mergedSkillOptions: [
      ...extraSkills,
      ...skillOptions.filter((s) => !extraSkills.some((e) => e.slug === s.slug)),
    ],
  };
}
