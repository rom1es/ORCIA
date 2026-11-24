import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import { handleRgaaSubmitKeyDown, type RgaaModalDialogLabels } from "../components/RgaaModalDialog.js";
import type {
  DeepLinkResolutionPayload,
  TopHeaderSearchCommandLabels,
  TopSearchHitItem,
  TopSearchScopeMode,
} from "./TopHeaderSearchCommandTypes";

export function TopHeaderSearchFooterBanner({
  labels,
  resolvedRgaaLabels,
  query,
  scope,
  activeHit,
  lastDeepLink,
  onAskAssistant,
  onExecuteHit,
}: {
  readonly labels: TopHeaderSearchCommandLabels;
  readonly resolvedRgaaLabels: RgaaModalDialogLabels;
  readonly query: string;
  readonly scope: TopSearchScopeMode;
  readonly activeHit: TopSearchHitItem | null;
  readonly lastDeepLink: DeepLinkResolutionPayload | null;
  readonly onAskAssistant?: (query: string, scope: TopSearchScopeMode) => void;
  readonly onExecuteHit: (hit: TopSearchHitItem) => void;
}): React.JSX.Element {
  return (
    <>
      {lastDeepLink !== null && (
        <div
          data-testid="cmdk-deeplink-highlight-banner"
          className="px-3 py-1.5 bg-surface-secondary border-t border-surface-border text-xs font-mono text-text-primary"
        >
          {lastDeepLink.opensContextualHelpColumn ? (
            <>
              <OrciaIcon name="help" />{" "}
              {`${labels.helpColumnDeepLinkPrefix ?? ""} -> ${lastDeepLink.deepLinkUri}`}
            </>
          ) : (
            <>
              <OrciaIcon name="target" />{" "}
              {`${labels.autoFocusDeepLinkPrefix ?? ""} (${lastDeepLink.highlightDurationMs} ${labels.durationMsUnit ?? "ms"}) -> ${lastDeepLink.deepLinkUri}`}
            </>
          )}
        </div>
      )}

      <div className="p-2.5 border-t border-surface-border bg-surface-secondary flex items-center justify-between gap-2">
        <button
          type="button"
          data-testid="cmdk-ask-assistant-cta"
          onClick={() => onAskAssistant?.(query, scope)}
          className="text-xs font-medium text-brand-primary hover:underline"
        >
          {labels.askAssistantFooterPrefix} « {query || "..."} »{" "}
          {labels.askAssistantFooterSuffix}
        </button>
        <div className="flex items-center gap-2">
          {labels.keyboardShortcutsHint ? (
            <span className="text-[11px] font-mono text-text-secondary">
              {labels.keyboardShortcutsHint}
            </span>
          ) : null}
          <button
            type="button"
            data-testid="cmdk-submit-btn"
            disabled={!activeHit}
            onClick={() => {
              if (activeHit) onExecuteHit(activeHit);
            }}
            onKeyDown={(e) =>
              handleRgaaSubmitKeyDown(
                e,
                () => {
                  if (activeHit) onExecuteHit(activeHit);
                },
                !activeHit,
              )
            }
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-brand-primary text-[var(--color-primary-foreground)] font-medium disabled:opacity-50"
          >
            <span>{resolvedRgaaLabels.submitCta}</span>
            <DisabledButtonAlertIndicator
              disabled={!activeHit}
              reason={labels.disabledOpenHint ?? ""}
              testIdSuffix="cmdk-submit-btn"
            />
          </button>
        </div>
      </div>
    </>
  );
}
