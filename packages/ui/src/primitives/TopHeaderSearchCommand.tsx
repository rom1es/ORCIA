import * as DialogPrimitive from "@radix-ui/react-dialog";
import React, { useState } from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import {
  DEFAULT_RGAA_MODAL_LABELS_FR,
  RgaaUnsavedChangesAlert,
  handleRgaaSubmitKeyDown,
  useUnsavedChangesDialogGuard,
  type RgaaModalDialogLabels,
} from "../components/RgaaModalDialog.js";
import type {
  DeepLinkResolutionPayload,
  TopHeaderSearchCommandLabels,
  TopHeaderSearchCommandProps,
  TopSearchFamilyKey,
  TopSearchHitItem,
  TopSearchScopeMode,
} from "./TopHeaderSearchCommandTypes";
import { TopHeaderSearchResultsPane } from "./TopHeaderSearchResultsPane";

export type {
  DeepLinkResolutionPayload,
  TopHeaderSearchCommandLabels,
  TopHeaderSearchCommandProps,
  TopSearchFamilyKey,
  TopSearchHitItem,
  TopSearchScopeMode,
};

const SCOPE_ORDER: readonly TopSearchScopeMode[] = [
  "SCREEN",
  "WORKSPACE",
  "ALL_WORKSPACES",
];

/**
 * Story 9.3 — Two-Speed Federated & Contextual Search Command Palette (`⌘K`, `680px × max 480px`).
 * Guarantees Zero Layout Shift: Speed 1 lexical hits remain locked at the top while Speed 2
 * semantic hits (`✨ Passage proche`) are appended at the bottom without moving `selectedIndex`.
 */
export function TopHeaderSearchCommand({
  labels,
  initialQuery = "",
  initialScope = "WORKSPACE",
  speed1Hits,
  speed2Hits = [],
  speed2Loading = false,
  speed2Executed = false,
  speed2Error = null,
  isDirty = false,
  rgaaLabels,
  onQueryChange,
  onScopeChange,
  onTriggerSpeed2Now,
  onSelectDeepLink,
  onAskAssistant,
  onClose,
}: TopHeaderSearchCommandProps): React.ReactElement {
  const [query, setQuery] = useState<string>(initialQuery);
  const [scope, setScope] = useState<TopSearchScopeMode>(initialScope);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [previewItemId, setPreviewItemId] = useState<string | null>(null);
  const [lastDeepLink, setLastDeepLink] = useState<DeepLinkResolutionPayload | null>(null);

  const resolvedRgaaLabels: RgaaModalDialogLabels = {
    ...DEFAULT_RGAA_MODAL_LABELS_FR,
    submitCta: labels.deepLinkActionLabel || DEFAULT_RGAA_MODAL_LABELS_FR.submitCta,
    ...rgaaLabels,
  };

  const {
    showUnsavedConfirm,
    requestClose,
    confirmDiscardAndClose,
    cancelDiscardAndStay,
  } = useUnsavedChangesDialogGuard({
    isOpen: true,
    isDirty,
    onClose: () => onClose?.(),
    onDiscardUnsavedChanges: () => setQuery(initialQuery),
  });

  // Speed 1 hits are strictly locked at the top; Speed 2 hits are appended at the bottom
  const deduplicatedSpeed2 = speed2Hits.filter(
    (s2) => !speed1Hits.some((s1) => s1.itemId === s2.itemId),
  );
  const combinedHits: readonly TopSearchHitItem[] = [
    ...speed1Hits,
    ...deduplicatedSpeed2,
  ];

  const safeSelectedIndex =
    combinedHits.length === 0
      ? 0
      : Math.min(selectedIndex, combinedHits.length - 1);
  const activeHit = combinedHits[safeSelectedIndex] ?? null;
  const previewHit =
    combinedHits.find((h) => h.itemId === previewItemId) ?? null;

  const handleScopeSelect = (nextScope: TopSearchScopeMode): void => {
    setScope(nextScope);
    onScopeChange?.(nextScope);
    onQueryChange?.(query, nextScope);
  };

  const handleExecuteHit = (hit: TopSearchHitItem): void => {
    const payload: DeepLinkResolutionPayload = {
      itemId: hit.itemId,
      deepLinkUri: hit.deepLinkUri,
      highlightDurationMs: hit.highlightDurationMs,
      opensContextualHelpColumn: hit.opensContextualHelpColumn,
    };
    setLastDeepLink(payload);
    onSelectDeepLink?.(payload);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>): void => {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      requestClose();
      return;
    }
    if (e.key === "Tab") {
      e.preventDefault();
      const idx = SCOPE_ORDER.indexOf(scope);
      const nextScope = SCOPE_ORDER[(idx + 1) % SCOPE_ORDER.length] ?? "WORKSPACE";
      handleScopeSelect(nextScope);
      return;
    }
    if (e.key === "ArrowDown" && combinedHits.length > 0) {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % combinedHits.length);
      return;
    }
    if (e.key === "ArrowUp" && combinedHits.length > 0) {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + combinedHits.length) % combinedHits.length);
      return;
    }
    if (e.key === "Enter" && activeHit) {
      e.preventDefault();
      if (e.metaKey || e.ctrlKey) {
        setPreviewItemId(activeHit.itemId);
      } else {
        handleExecuteHit(activeHit);
      }
    }
  };

  return (
    <DialogPrimitive.Root
      open={true}
      modal={false}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) requestClose();
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Content
          asChild
          aria-describedby={undefined}
          onEscapeKeyDown={(e) => {
            e.preventDefault();
          }}
        >
          <div
            aria-label={labels.modalTitle}
            data-testid="top-header-search-command"
            onKeyDown={handleKeyDown}
            style={{ zIndex: "var(--z-dialog)" }}
            className="fixed left-1/2 top-[12vh] -translate-x-1/2 w-[680px] max-w-[95vw] max-h-[480px] flex flex-col rounded-xl border border-surface-border bg-surface-elevated text-text-primary shadow-xl overflow-hidden"
          >
            <DialogPrimitive.Title className="sr-only">{labels.modalTitle}</DialogPrimitive.Title>
      {/* Top Search Input + Scope Pills (SCREEN | WORKSPACE | ALL_WORKSPACES) */}
      <div className="p-3 border-b border-surface-border flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <OrciaIcon name="cmdkShortcut" className="text-sm font-mono text-text-secondary" />
          <input
            type="search"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            value={query}
            onChange={(e) => {
              const nextQ = e.target.value;
              setQuery(nextQ);
              onQueryChange?.(nextQ, scope);
            }}
            placeholder={labels.inputPlaceholder}
            data-testid="cmdk-search-input"
            className="flex-1 bg-surface-primary border border-surface-border rounded px-2.5 py-1.5 text-sm text-text-primary"
          />
          <button
            type="button"
            data-testid="cmdk-trigger-speed2-btn"
            onClick={() => onTriggerSpeed2Now?.(query, scope)}
            className="px-2 py-1 rounded text-xs border border-surface-border bg-surface-secondary text-text-secondary"
          >
            <OrciaIcon name="sparkles" /> Recherche approfondie
          </button>
          <button
            type="button"
            data-testid="cmdk-cancel-btn"
            onClick={requestClose}
            className="px-2 py-1 rounded text-xs border border-surface-border bg-surface-secondary text-text-secondary"
          >
            {resolvedRgaaLabels.cancelCta}
          </button>
        </div>

        {showUnsavedConfirm ? (
          <RgaaUnsavedChangesAlert
            testIdPrefix="cmdk"
            labels={resolvedRgaaLabels}
            onStay={cancelDiscardAndStay}
            onDiscard={confirmDiscardAndClose}
          />
        ) : null}

        {speed2Error ? (
          <div
            role="alert"
            data-testid="cmdk-speed2-error-banner"
            className="orcia-ds-alert orcia-ds-alert-error"
          >
            {speed2Error}
          </div>
        ) : null}

        <div
          role="tablist"
          aria-label="Portées de recherche"
          data-testid="cmdk-scope-pills"
          className="orcia-ds-tabs items-center text-xs"
        >
          <button
            type="button"
            role="tab"
            aria-selected={scope === "SCREEN"}
            data-testid="cmdk-scope-SCREEN"
            onClick={() => handleScopeSelect("SCREEN")}
            className="orcia-ds-tab"
          >
            {labels.scopeScreenLabel}
          </button>
          <button type="button" role="tab" aria-selected={scope === "WORKSPACE"} data-testid="cmdk-scope-WORKSPACE" onClick={() => handleScopeSelect("WORKSPACE")} className="orcia-ds-tab">
            {labels.scopeWorkspaceLabel}
          </button>
          <button type="button" role="tab" aria-selected={scope === "ALL_WORKSPACES"} data-testid="cmdk-scope-ALL_WORKSPACES" onClick={() => handleScopeSelect("ALL_WORKSPACES")} className="orcia-ds-tab">
            {labels.scopeAllWorkspacesLabel}
          </button>
        </div>
      </div>

      {/* Main Split Area: Results List (Left) + Optional ⌘+Enter Preview Pane (Right) */}
      <TopHeaderSearchResultsPane
        labels={labels}
        speed1Hits={speed1Hits}
        deduplicatedSpeed2={deduplicatedSpeed2}
        combinedHits={combinedHits}
        safeSelectedIndex={safeSelectedIndex}
        speed2Executed={speed2Executed}
        speed2Loading={speed2Loading}
        previewHit={previewHit}
        onSelectPreview={setPreviewItemId}
        onExecuteHit={handleExecuteHit}
      />

      {/* Auto-Focus Deep-Link Feedback Banner (2s Yellow Highlight Status) */}
      {lastDeepLink !== null && (
        <div
          data-testid="cmdk-deeplink-highlight-banner"
          className="px-3 py-1.5 bg-surface-secondary border-t border-surface-border text-xs font-mono text-text-primary"
        >
          {lastDeepLink.opensContextualHelpColumn ? (
            <>
              <OrciaIcon name="help" /> Help Column -&gt; {lastDeepLink.deepLinkUri}
            </>
          ) : (
            <>
              <OrciaIcon name="target" /> Deep-Link Auto-Focus ({lastDeepLink.highlightDurationMs} ms) -&gt; {lastDeepLink.deepLinkUri}
            </>
          )}
        </div>
      )}

      {/* Footer CTA: Ask Mon Assistant with pre-filled query & active scope */}
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
          <span className="text-[11px] font-mono text-text-secondary">
            Tab: Portée · ↵: Ouvrir · ⌘↵: Aperçu
          </span>
          <button
            type="button"
            data-testid="cmdk-submit-btn"
            disabled={!activeHit}
            onClick={() => {
              if (activeHit) handleExecuteHit(activeHit);
            }}
            onKeyDown={(e) =>
              handleRgaaSubmitKeyDown(
                e,
                () => {
                  if (activeHit) handleExecuteHit(activeHit);
                },
                !activeHit,
              )
            }
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-brand-primary text-surface-elevated font-medium disabled:opacity-50"
          >
            <span>{resolvedRgaaLabels.submitCta}</span>
            <DisabledButtonAlertIndicator
              disabled={!activeHit}
              reason="Sélectionnez un élément dans la recherche pour l'ouvrir."
              testIdSuffix="cmdk-submit-btn"
            />
          </button>
        </div>
      </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
