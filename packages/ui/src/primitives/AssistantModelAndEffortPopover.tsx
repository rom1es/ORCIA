import React from "react";
import { OrciaIcon } from "../components/icons";
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
  readonly hiddenDuplicate?: boolean;
}

export interface UiAssistantEffortOption {
  readonly effort: UiInferenceEffort;
  readonly speed: UiAssistantSpeedMode;
  readonly title: string;
  readonly subtitle: string;
  readonly hiddenLegacyFast?: boolean;
}

export interface AssistantModelAndEffortPopoverLabels {
  readonly aiModelHeading: string;
  readonly selectedAriaLabel: string;
  readonly thinkingLevelTriggerLabel: string;
  readonly thinkingModeHeading: string;
  readonly effortOptions: readonly UiAssistantEffortOption[];
}

export interface AssistantModelAndEffortPopoverProps {
  readonly modelOptions: readonly UiAssistantModelOption[];
  readonly selectedTier: UiInferenceTier;
  readonly selectedEffort: UiInferenceEffort;
  readonly thinkingSubmenuOpen: boolean;
  readonly supportsTools?: boolean;
  readonly toolsUnsupportedBadge?: string;
  readonly labels: AssistantModelAndEffortPopoverLabels;
  readonly onSelectTier: (tier: UiInferenceTier) => void;
  readonly onToggleThinkingSubmenu: () => void;
  readonly onSelectEffort: (effort: UiInferenceEffort) => void;
}

export function AssistantModelAndEffortPopover({
  modelOptions,
  selectedTier,
  selectedEffort,
  thinkingSubmenuOpen,
  supportsTools = true,
  toolsUnsupportedBadge,
  labels,
  onSelectTier,
  onToggleThinkingSubmenu,
  onSelectEffort,
}: AssistantModelAndEffortPopoverProps): React.JSX.Element {
  const normalizedSelectedEffort: UiInferenceEffort = !supportsTools
    ? "fast"
    : selectedEffort === "deep"
      ? "deep"
      : "balanced";
  const activeEffortOption =
    labels.effortOptions.find((e) => e.effort === normalizedSelectedEffort) ??
    labels.effortOptions[1] ??
    labels.effortOptions[0];
  const visibleModelCount = modelOptions.filter((m) => !m.hiddenDuplicate).length;
  const isSingleModelOnly = visibleModelCount === 1;

  return (
    <div
      data-testid="assistant-model-picker-popover"
      className={
        isSingleModelOnly
          ? "mt-2 rounded-xl border border-border-subtle bg-surface-primary p-2.5 text-xs shadow-lg max-w-xs ml-auto"
          : "mt-2 grid grid-cols-1 gap-2 rounded-xl border border-border-subtle bg-surface-primary p-3 text-xs shadow-lg md:grid-cols-2"
      }
    >
      {/* Column 1: AI Model Tiers (hidden visually when only 1 distinct model is configured) */}
      <div
        style={isSingleModelOnly ? { display: "none" } : undefined}
        className={
          isSingleModelOnly
            ? "sr-only"
            : "space-y-1 border-b border-border-subtle pb-2 md:border-b-0 md:border-r md:pr-3"
        }
      >
        <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-text-secondary">
          {labels.aiModelHeading}
        </div>
        {modelOptions.map((opt) => {
          const isSelected = opt.tier === selectedTier || visibleModelCount === 1;
          const displaySingleModelTitle =
            visibleModelCount === 1 && opt.configuredModelName
              ? opt.configuredModelName
              : opt.title;
          return (
            <button
              key={opt.tier}
              type="button"
              data-testid={`assistant-model-option-${opt.tier}`}
              style={opt.hiddenDuplicate ? { display: "none" } : undefined}
              onClick={() => onSelectTier(opt.tier)}
              className={
                opt.hiddenDuplicate
                  ? "sr-only"
                  : `flex w-full items-start justify-between gap-2 rounded-lg px-2.5 py-1.5 text-left transition-colors ${
                      isSelected
                        ? "bg-action-primary/10 font-semibold text-text-primary"
                        : "hover:bg-surface-secondary text-text-primary"
                    }`
              }
            >
              <div>
                <div className="text-xs font-semibold">
                  {displaySingleModelTitle}
                  {visibleModelCount > 1 && opt.configuredModelName ? (
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
                <OrciaIcon
                  name="check"
                  ariaLabel={labels.selectedAriaLabel}
                  className="text-xs font-bold"
                />
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
            <span>
              <OrciaIcon name="brain" /> {labels.thinkingLevelTriggerLabel}
            </span>
            <span className="text-text-secondary">
              {activeEffortOption?.title ?? ""} <OrciaIcon name="caretRight" />
            </span>
          </button>
        </div>
      </div>

      {/* Column 2 (or sole vertical list when 1 model): Thinking Effort Submenu */}
      {(thinkingSubmenuOpen || isSingleModelOnly) && (
        <div
          data-testid="assistant-thinking-level-submenu"
          className={isSingleModelOnly ? "space-y-1" : "space-y-1 md:pl-1"}
        >
          <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-text-secondary">
            {labels.thinkingModeHeading}
          </div>
          {labels.effortOptions.map((eff) => {
            const isHidden = supportsTools ? Boolean(eff.hiddenLegacyFast) : false;
            const isDisabledByTools = !supportsTools && eff.effort !== "fast";
            const isSelected = !isHidden && eff.effort === normalizedSelectedEffort;
            return (
              <button
                key={eff.effort}
                type="button"
                disabled={isDisabledByTools}
                data-testid={`assistant-effort-option-${eff.effort}`}
                style={isHidden ? { display: "none" } : undefined}
                onClick={() => {
                  if (!isDisabledByTools) onSelectEffort(eff.effort);
                }}
                className={
                  isHidden
                    ? "sr-only"
                    : `flex w-full items-start justify-between gap-2 rounded-lg px-2.5 py-1.5 text-left transition-colors ${
                        isDisabledByTools
                          ? "opacity-50 cursor-not-allowed text-text-secondary"
                          : isSelected
                            ? "bg-action-primary/10 font-semibold text-text-primary"
                            : "hover:bg-surface-secondary text-text-primary"
                      }`
                }
              >
                <div>
                  <div className="text-xs font-semibold">
                    {eff.title}
                    {isDisabledByTools && toolsUnsupportedBadge ? (
                      <span className="ml-1.5 text-[10px] font-normal text-text-secondary">
                        ({toolsUnsupportedBadge})
                      </span>
                    ) : null}
                  </div>
                  <div className="text-[11px] text-text-secondary">
                    {eff.subtitle}
                  </div>
                </div>
                {isSelected && (
                  <OrciaIcon
                    name="check"
                    ariaLabel={labels.selectedAriaLabel}
                    className="text-xs font-bold"
                  />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export {
  applyAutocompleteSuggestionToPrompt,
  AssistantAutocompleteDropdown,
  extractAutocompleteTrigger,
  type UiAssistantAutocompleteSuggestion,
} from "./AssistantAutocompleteDropdown";
