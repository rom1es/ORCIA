import React, { useState } from "react";
import {
  DEFAULT_RGAA_MODAL_LABELS_FR,
  RgaaUnsavedChangesAlert,
  handleRgaaSubmitKeyDown,
  useUnsavedChangesDialogGuard,
  type RgaaModalDialogLabels,
} from "../components/RgaaModalDialog.js";

export type TopSearchScopeMode = "SCREEN" | "WORKSPACE" | "ALL_WORKSPACES";

export type TopSearchFamilyKey =
  | "FOLDERS_DISCUSSIONS"
  | "PROCESSES_EXECUTIONS"
  | "AGENTS_TOOLS"
  | "DELIVERABLES_ARTIFACTS"
  | "SOURCES_SNIPPETS"
  | "ONTOLOGY_GLOSSARY"
  | "HELP_ACTIONS";

export interface TopSearchHitItem {
  readonly itemId: string;
  readonly family: TopSearchFamilyKey;
  readonly title: string;
  readonly snippet: string;
  readonly workspaceId: string;
  readonly screenRoute: string;
  readonly deepLinkUri: string;
  readonly speedTier: 1 | 2;
  readonly lockedTop: boolean;
  readonly score: number;
  readonly badge: string | null;
  readonly highlightDurationMs: number;
  readonly opensContextualHelpColumn: boolean;
}

export interface TopHeaderSearchCommandLabels {
  readonly modalTitle: string;
  readonly inputPlaceholder: string;
  readonly scopeScreenLabel: string;
  readonly scopeWorkspaceLabel: string;
  readonly scopeAllWorkspacesLabel: string;
  readonly speed1SectionTitle: string;
  readonly speed2SectionTitle: string;
  readonly semanticCloseMatchBadge: string;
  readonly emptyResultsLabel: string;
  readonly previewPaneTitle: string;
  readonly deepLinkActionLabel: string;
  readonly openHelpColumnActionLabel: string;
  readonly askAssistantFooterPrefix: string;
  readonly askAssistantFooterSuffix: string;
  readonly familyLabels: Readonly<Record<TopSearchFamilyKey, string>>;
}

export interface DeepLinkResolutionPayload {
  readonly itemId: string;
  readonly deepLinkUri: string;
  readonly highlightDurationMs: number;
  readonly opensContextualHelpColumn: boolean;
}

export interface TopHeaderSearchCommandProps {
  readonly labels: TopHeaderSearchCommandLabels;
  readonly initialQuery?: string;
  readonly initialScope?: TopSearchScopeMode;
  readonly speed1Hits: readonly TopSearchHitItem[];
  readonly speed2Hits?: readonly TopSearchHitItem[];
  readonly speed2Loading?: boolean;
  readonly isDirty?: boolean;
  readonly rgaaLabels?: Partial<RgaaModalDialogLabels>;
  readonly onQueryChange?: (query: string, scope: TopSearchScopeMode) => void;
  readonly onScopeChange?: (scope: TopSearchScopeMode) => void;
  readonly onTriggerSpeed2Now?: (query: string, scope: TopSearchScopeMode) => void;
  readonly onSelectDeepLink?: (payload: DeepLinkResolutionPayload) => void;
  readonly onAskAssistant?: (query: string, scope: TopSearchScopeMode) => void;
  readonly onClose?: () => void;
}

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
    <div
      role="dialog"
      aria-modal="true"
      aria-label={labels.modalTitle}
      data-testid="top-header-search-command"
      onKeyDown={handleKeyDown}
      className="w-[680px] max-h-[480px] flex flex-col rounded-xl border border-surface-border bg-surface-elevated text-text-primary shadow-xl overflow-hidden"
    >
      {/* Top Search Input + Scope Pills (SCREEN | WORKSPACE | ALL_WORKSPACES) */}
      <div className="p-3 border-b border-surface-border flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="text-sm font-mono text-text-secondary">
            ⌘K
          </span>
          <input
            type="search"
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
            ✨ Vitesse 2 (450 ms)
          </button>
          <button
            type="button"
            data-testid="cmdk-cancel-btn"
            onClick={requestClose}
            className="px-2 py-1 rounded text-xs border border-surface-border bg-surface-secondary text-text-secondary"
          >
            {resolvedRgaaLabels.cancelCta} (Esc)
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

        <div
          role="tablist"
          aria-label="Portées de recherche"
          data-testid="cmdk-scope-pills"
          className="flex items-center gap-1.5 text-xs"
        >
          <button
            type="button"
            role="tab"
            aria-selected={scope === "SCREEN"}
            data-testid="cmdk-scope-SCREEN"
            onClick={() => handleScopeSelect("SCREEN")}
            className={`px-2.5 py-1 rounded-full border ${
              scope === "SCREEN"
                ? "border-brand-primary bg-surface-secondary font-semibold text-text-primary"
                : "border-surface-border text-text-secondary"
            }`}
          >
            {labels.scopeScreenLabel}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={scope === "WORKSPACE"}
            data-testid="cmdk-scope-WORKSPACE"
            onClick={() => handleScopeSelect("WORKSPACE")}
            className={`px-2.5 py-1 rounded-full border ${
              scope === "WORKSPACE"
                ? "border-brand-primary bg-surface-secondary font-semibold text-text-primary"
                : "border-surface-border text-text-secondary"
            }`}
          >
            {labels.scopeWorkspaceLabel}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={scope === "ALL_WORKSPACES"}
            data-testid="cmdk-scope-ALL_WORKSPACES"
            onClick={() => handleScopeSelect("ALL_WORKSPACES")}
            className={`px-2.5 py-1 rounded-full border ${
              scope === "ALL_WORKSPACES"
                ? "border-brand-primary bg-surface-secondary font-semibold text-text-primary"
                : "border-surface-border text-text-secondary"
            }`}
          >
            {labels.scopeAllWorkspacesLabel}
          </button>
        </div>
      </div>

      {/* Main Split Area: Results List (Left) + Optional ⌘+Enter Preview Pane (Right) */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        <div
          data-testid="cmdk-results-list"
          data-selected-index={safeSelectedIndex}
          className="flex-1 overflow-y-auto p-2.5 space-y-2"
        >
          {combinedHits.length === 0 ? (
            <p
              data-testid="cmdk-empty-results"
              className="text-xs text-text-secondary py-4 text-center"
            >
              {labels.emptyResultsLabel}
            </p>
          ) : (
            <>
              {/* Speed 1 Locked Section */}
              <div data-testid="cmdk-speed1-locked-group" className="space-y-1">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-text-secondary px-1">
                  {labels.speed1SectionTitle}
                </div>
                {speed1Hits.map((hit, idx) => {
                  const isSelected = idx === safeSelectedIndex;
                  return (
                    <div
                      key={hit.itemId}
                      data-testid={`cmdk-hit-${hit.itemId}`}
                      data-speed-tier="1"
                      data-selected={isSelected ? "true" : "false"}
                      className={`p-2 rounded border flex items-start justify-between gap-2 ${
                        isSelected
                          ? "border-brand-primary bg-surface-secondary"
                          : "border-surface-border bg-surface-primary"
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-secondary text-text-secondary">
                            {labels.familyLabels[hit.family]}
                          </span>
                          <span className="text-xs font-semibold truncate">
                            {hit.title}
                          </span>
                        </div>
                        <p className="text-[11px] text-text-secondary truncate mt-0.5">
                          {hit.snippet}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          data-testid={`cmdk-preview-btn-${hit.itemId}`}
                          onClick={() => setPreviewItemId(hit.itemId)}
                          className="px-1.5 py-0.5 rounded text-[10px] border border-surface-border text-text-secondary"
                        >
                          ⌘↵
                        </button>
                        <button
                          type="button"
                          data-testid={`cmdk-open-btn-${hit.itemId}`}
                          onClick={() => handleExecuteHit(hit)}
                          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, () => handleExecuteHit(hit))}
                          className="px-2 py-0.5 rounded text-[11px] bg-brand-primary text-surface-elevated font-medium"
                        >
                          {hit.opensContextualHelpColumn
                            ? labels.openHelpColumnActionLabel
                            : labels.deepLinkActionLabel}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Speed 2 Appended Bottom Section (Zero Layout Shift on Top Hits) */}
              {(deduplicatedSpeed2.length > 0 || speed2Loading) && (
                <div
                  data-testid="cmdk-speed2-appended-group"
                  className="space-y-1 pt-2 border-t border-surface-border"
                >
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-text-secondary px-1">
                    {labels.speed2SectionTitle}
                  </div>
                  {deduplicatedSpeed2.map((hit, s2Idx) => {
                    const globalIdx = speed1Hits.length + s2Idx;
                    const isSelected = globalIdx === safeSelectedIndex;
                    return (
                      <div
                        key={hit.itemId}
                        data-testid={`cmdk-hit-${hit.itemId}`}
                        data-speed-tier="2"
                        data-selected={isSelected ? "true" : "false"}
                        className={`p-2 rounded border flex items-start justify-between gap-2 ${
                          isSelected
                            ? "border-brand-primary bg-surface-secondary"
                            : "border-surface-border bg-surface-primary"
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span
                              data-testid={`cmdk-semantic-badge-${hit.itemId}`}
                              className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-surface-secondary text-brand-primary border border-surface-border"
                            >
                              {hit.badge ?? labels.semanticCloseMatchBadge}
                            </span>
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-secondary text-text-secondary">
                              {labels.familyLabels[hit.family]}
                            </span>
                            <span className="text-xs font-semibold truncate">
                              {hit.title}
                            </span>
                          </div>
                          <p className="text-[11px] text-text-secondary truncate mt-0.5">
                            {hit.snippet}
                          </p>
                        </div>
                        <button
                          type="button"
                          data-testid={`cmdk-open-btn-${hit.itemId}`}
                          onClick={() => handleExecuteHit(hit)}
                          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, () => handleExecuteHit(hit))}
                          className="px-2 py-0.5 rounded text-[11px] bg-brand-primary text-surface-elevated font-medium shrink-0"
                        >
                          {hit.opensContextualHelpColumn
                            ? labels.openHelpColumnActionLabel
                            : labels.deepLinkActionLabel}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>

        {/* Right-Side Preview Drawer (`⌘+Entrée`) */}
        {previewHit !== null && (
          <aside
            data-testid="cmdk-preview-pane"
            className="w-60 border-l border-surface-border bg-surface-secondary p-3 flex flex-col justify-between"
          >
            <div>
              <div className="text-[11px] font-semibold uppercase text-text-secondary">
                {labels.previewPaneTitle}
              </div>
              <h4 className="text-xs font-semibold mt-1">{previewHit.title}</h4>
              <p className="text-xs text-text-secondary mt-1.5">
                {previewHit.snippet}
              </p>
              <div className="mt-2 text-[11px] font-mono text-text-secondary break-all">
                {previewHit.deepLinkUri}
              </div>
            </div>
            <button
              type="button"
              data-testid="cmdk-preview-navigate-btn"
              onClick={() => handleExecuteHit(previewHit)}
              onKeyDown={(e) => handleRgaaSubmitKeyDown(e, () => handleExecuteHit(previewHit))}
              className="w-full py-1 rounded text-xs bg-brand-primary text-surface-elevated font-medium"
            >
              {labels.deepLinkActionLabel}
            </button>
          </aside>
        )}
      </div>

      {/* Auto-Focus Deep-Link Feedback Banner (2s Yellow Highlight Status) */}
      {lastDeepLink !== null && (
        <div
          data-testid="cmdk-deeplink-highlight-banner"
          className="px-3 py-1.5 bg-surface-secondary border-t border-surface-border text-xs font-mono text-text-primary"
        >
          {lastDeepLink.opensContextualHelpColumn
            ? `❓ Help Column -> ${lastDeepLink.deepLinkUri}`
            : `🎯 Deep-Link Auto-Focus (${lastDeepLink.highlightDurationMs} ms) -> ${lastDeepLink.deepLinkUri}`}
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
            className="px-2.5 py-1 rounded text-xs bg-brand-primary text-surface-elevated font-medium disabled:opacity-50"
          >
            {resolvedRgaaLabels.submitCta}
          </button>
        </div>
      </div>
    </div>
  );
}
