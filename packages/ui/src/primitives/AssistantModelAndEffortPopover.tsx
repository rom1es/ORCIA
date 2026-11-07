import React from "react";
import type { UiAssistantSpeedMode } from "./AssistantSpeedSelectorAndStreamView";
import type {
  UiInferenceEffort,
  UiInferenceTier,
} from "./InferenceTierAndEffortSelector";

export interface UiAssistantModelOption {
  readonly tier: UiInferenceTier;
  readonly title: string;
  readonly subtitle: string;
  readonly configuredModelName?: string;
}

export const DEFAULT_ASSISTANT_MODEL_OPTIONS: readonly UiAssistantModelOption[] = [
  {
    tier: "simple",
    title: "Rapide",
    subtitle: "Réponses les plus rapides",
  },
  {
    tier: "medium",
    title: "Polyvalent",
    subtitle: "Aide polyvalente au quotidien",
  },
  {
    tier: "complex",
    title: "Raisonnement avancé",
    subtitle: "Tâches complexes & analyse critique",
  },
];

export const ASSISTANT_EFFORT_OPTIONS: ReadonlyArray<{
  readonly effort: UiInferenceEffort;
  readonly speed: UiAssistantSpeedMode;
  readonly title: string;
  readonly subtitle: string;
}> = [
  {
    effort: "fast",
    speed: "SPEED_1_FAST",
    title: "Bas",
    subtitle: "Rapide et efficace",
  },
  {
    effort: "balanced",
    speed: "SPEED_2_AGENT_TOOLS",
    title: "Moyen",
    subtitle: "Équilibré (Sources & Compétences)",
  },
  {
    effort: "deep",
    speed: "SPEED_3_DEEP_AUDIT",
    title: "Élevé",
    subtitle: "Très poussé (Plusieurs points de vue)",
  },
];

export interface AssistantModelAndEffortPopoverProps {
  readonly modelOptions: readonly UiAssistantModelOption[];
  readonly selectedTier: UiInferenceTier;
  readonly selectedEffort: UiInferenceEffort;
  readonly thinkingSubmenuOpen: boolean;
  readonly onSelectTier: (tier: UiInferenceTier) => void;
  readonly onToggleThinkingSubmenu: () => void;
  readonly onSelectEffort: (effort: UiInferenceEffort) => void;
}

export function AssistantModelAndEffortPopover({
  modelOptions,
  selectedTier,
  selectedEffort,
  thinkingSubmenuOpen,
  onSelectTier,
  onToggleThinkingSubmenu,
  onSelectEffort,
}: AssistantModelAndEffortPopoverProps): React.JSX.Element {
  const activeEffortOption =
    ASSISTANT_EFFORT_OPTIONS.find((e) => e.effort === selectedEffort) ??
    ASSISTANT_EFFORT_OPTIONS[0]!;

  return (
    <div
      data-testid="assistant-model-picker-popover"
      className="mt-2 grid grid-cols-1 gap-2 rounded-xl border border-border-subtle bg-surface-primary p-3 text-xs shadow-lg md:grid-cols-2"
    >
      {/* Column 1: AI Model Tiers */}
      <div className="space-y-1 border-b border-border-subtle pb-2 md:border-b-0 md:border-r md:pr-3">
        <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-text-secondary">
          Modèle IA
        </div>
        {modelOptions.map((opt) => {
          const isSelected = opt.tier === selectedTier;
          return (
            <button
              key={opt.tier}
              type="button"
              data-testid={`assistant-model-option-${opt.tier}`}
              onClick={() => onSelectTier(opt.tier)}
              className={`flex w-full items-start justify-between gap-2 rounded-lg px-2.5 py-1.5 text-left transition-colors ${
                isSelected
                  ? "bg-action-primary/10 font-semibold text-text-primary"
                  : "hover:bg-surface-secondary text-text-primary"
              }`}
            >
              <div>
                <div className="text-xs font-semibold">
                  {opt.title}
                  {opt.configuredModelName ? (
                    <span className="ml-1.5 font-mono text-[11px] text-text-secondary">
                      ({opt.configuredModelName})
                    </span>
                  ) : null}
                </div>
                <div className="text-[11px] text-text-secondary">
                  {opt.subtitle}
                </div>
              </div>
              {isSelected && (
                <span aria-label="Sélectionné" className="text-xs font-bold">
                  ✓
                </span>
              )}
            </button>
          );
        })}

        <div className="border-t border-border-subtle pt-1.5 mt-1.5">
          <button
            type="button"
            data-testid="assistant-thinking-level-trigger"
            onClick={onToggleThinkingSubmenu}
            className="flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left font-medium hover:bg-surface-secondary"
          >
            <span>🧠 Niveau de réflexion</span>
            <span className="text-text-secondary">
              {activeEffortOption.title} ▸
            </span>
          </button>
        </div>
      </div>

      {/* Column 2: Thinking Effort Submenu */}
      {thinkingSubmenuOpen && (
        <div
          data-testid="assistant-thinking-level-submenu"
          className="space-y-1 md:pl-1"
        >
          <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-text-secondary">
            Niveau de réflexion
          </div>
          {ASSISTANT_EFFORT_OPTIONS.map((eff) => {
            const isSelected = eff.effort === selectedEffort;
            return (
              <button
                key={eff.effort}
                type="button"
                data-testid={`assistant-effort-option-${eff.effort}`}
                onClick={() => onSelectEffort(eff.effort)}
                className={`flex w-full items-start justify-between gap-2 rounded-lg px-2.5 py-1.5 text-left transition-colors ${
                  isSelected
                    ? "bg-action-primary/10 font-semibold text-text-primary"
                    : "hover:bg-surface-secondary text-text-primary"
                }`}
              >
                <div>
                  <div className="text-xs font-semibold">{eff.title}</div>
                  <div className="text-[11px] text-text-secondary">
                    {eff.subtitle}
                  </div>
                </div>
                {isSelected && (
                  <span aria-label="Sélectionné" className="text-xs font-bold">
                    ✓
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export interface UiAssistantAutocompleteSuggestion {
  readonly id: string;
  readonly kind: "agent" | "skill";
  readonly token: string;
  readonly name: string;
  readonly description: string;
  readonly badge?: string;
}

export function extractAutocompleteTrigger(promptText: string): {
  readonly kind: "agent" | "skill";
  readonly query: string;
} | null {
  const match = /(?:^|\s)(@|\/)([a-zA-Z0-9_-]*)$/.exec(promptText);
  if (!match) return null;
  const prefix = match[1];
  const query = (match[2] ?? "").toLowerCase();
  return {
    kind: prefix === "@" ? "agent" : "skill",
    query,
  };
}

export function applyAutocompleteSuggestionToPrompt(
  promptText: string,
  token: string,
): string {
  return promptText.replace(/(?:^|\s)(?:@|\/)[a-zA-Z0-9_-]*$/, (m) => {
    const leadingSpace = m.startsWith(" ") ? " " : "";
    return `${leadingSpace}${token} `;
  });
}

export function AssistantAutocompleteDropdown({
  suggestions,
  onSelectSuggestion,
}: {
  readonly suggestions: readonly UiAssistantAutocompleteSuggestion[];
  readonly onSelectSuggestion: (item: UiAssistantAutocompleteSuggestion) => void;
}): React.JSX.Element | null {
  if (suggestions.length === 0) return null;
  return (
    <div
      data-testid="assistant-autocomplete-dropdown"
      role="listbox"
      aria-label="Suggestions d'agents et compétences"
      className="mt-2 max-h-52 overflow-y-auto rounded-lg border border-border-subtle bg-surface-primary p-1.5 text-xs shadow-md space-y-1"
    >
      {suggestions.map((item) => (
        <button
          key={item.id}
          type="button"
          role="option"
          aria-selected={false}
          data-testid={`assistant-autocomplete-option-${item.token.slice(1)}`}
          onClick={() => onSelectSuggestion(item)}
          className="flex w-full items-center justify-between gap-2 rounded px-2.5 py-1.5 text-left hover:bg-surface-secondary"
        >
          <div className="flex flex-wrap items-center gap-2">
            <code className="rounded border border-border-subtle bg-surface-secondary px-1.5 py-0.5 font-mono text-[11px] font-semibold">
              {item.token}
            </code>
            <span className="font-semibold text-text-primary">{item.name}</span>
            <span className="text-[11px] text-text-secondary">{item.description}</span>
          </div>
          {item.badge && (
            <span className="rounded-full border border-border-subtle bg-surface-secondary px-2 py-0.5 text-[10px]">
              {item.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
