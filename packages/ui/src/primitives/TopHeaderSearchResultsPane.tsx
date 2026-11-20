import React from "react";
import { handleRgaaSubmitKeyDown } from "../components/RgaaModalDialog.js";
import type {
  TopHeaderSearchCommandLabels,
  TopSearchHitItem,
} from "./TopHeaderSearchCommandTypes";

export function TopHeaderSearchResultsPane({
  labels,
  speed1Hits,
  deduplicatedSpeed2,
  combinedHits,
  safeSelectedIndex,
  speed2Executed,
  speed2Loading,
  previewHit,
  onSelectPreview,
  onExecuteHit,
}: {
  readonly labels: TopHeaderSearchCommandLabels;
  readonly speed1Hits: readonly TopSearchHitItem[];
  readonly deduplicatedSpeed2: readonly TopSearchHitItem[];
  readonly combinedHits: readonly TopSearchHitItem[];
  readonly safeSelectedIndex: number;
  readonly speed2Executed: boolean;
  readonly speed2Loading: boolean;
  readonly previewHit: TopSearchHitItem | null;
  readonly onSelectPreview: (itemId: string) => void;
  readonly onExecuteHit: (hit: TopSearchHitItem) => void;
}): React.ReactElement {
  return (
    <div className="flex-1 min-h-0 flex overflow-hidden">
      <div
        data-testid="cmdk-results-list"
        data-selected-index={safeSelectedIndex}
        className="flex-1 overflow-y-auto p-2.5 space-y-2"
      >
        {combinedHits.length === 0 && !speed2Executed && !speed2Loading ? (
          <p data-testid="cmdk-empty-results" className="text-xs text-text-secondary py-4 text-center">
            {labels.emptyResultsLabel}
          </p>
        ) : (
          <>
            {combinedHits.length === 0 ? (
              <p data-testid="cmdk-empty-results" className="text-xs text-text-secondary py-2 text-center">
                {labels.emptyResultsLabel}
              </p>
            ) : null}
            {speed1Hits.length > 0 && (
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
                        isSelected ? "border-brand-primary bg-surface-secondary" : "border-surface-border bg-surface-primary"
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-secondary text-text-secondary">
                            {labels.familyLabels[hit.family]}
                          </span>
                          <span className="text-xs font-semibold truncate">{hit.title}</span>
                        </div>
                        <p className="text-[11px] text-text-secondary truncate mt-0.5">{hit.snippet}</p>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          data-testid={`cmdk-preview-btn-${hit.itemId}`}
                          onClick={() => onSelectPreview(hit.itemId)}
                          className="px-1.5 py-0.5 rounded text-[10px] border border-surface-border text-text-secondary"
                        >
                          ⌘↵
                        </button>
                        <button
                          type="button"
                          data-testid={`cmdk-open-btn-${hit.itemId}`}
                          onClick={() => onExecuteHit(hit)}
                          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, () => onExecuteHit(hit))}
                          className="px-2 py-0.5 rounded text-[11px] bg-brand-primary text-surface-elevated font-medium"
                        >
                          {hit.opensContextualHelpColumn ? labels.openHelpColumnActionLabel : labels.deepLinkActionLabel}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {(deduplicatedSpeed2.length > 0 || speed2Loading) && (
              <div data-testid="cmdk-speed2-appended-group" className="space-y-1 pt-2 border-t border-surface-border">
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
                        isSelected ? "border-brand-primary bg-surface-secondary" : "border-surface-border bg-surface-primary"
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
                          <span className="text-xs font-semibold truncate">{hit.title}</span>
                        </div>
                        <p className="text-[11px] text-text-secondary truncate mt-0.5">{hit.snippet}</p>
                      </div>
                      <button
                        type="button"
                        data-testid={`cmdk-open-btn-${hit.itemId}`}
                        onClick={() => onExecuteHit(hit)}
                        onKeyDown={(e) => handleRgaaSubmitKeyDown(e, () => onExecuteHit(hit))}
                        className="px-2 py-0.5 rounded text-[11px] bg-brand-primary text-surface-elevated font-medium shrink-0"
                      >
                        {hit.opensContextualHelpColumn ? labels.openHelpColumnActionLabel : labels.deepLinkActionLabel}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>

      {previewHit !== null && (
        <aside data-testid="cmdk-preview-pane" className="w-60 border-l border-surface-border bg-surface-secondary p-3 flex flex-col justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase text-text-secondary">{labels.previewPaneTitle}</div>
            <h4 className="text-xs font-semibold mt-1">{previewHit.title}</h4>
            <p className="text-xs text-text-secondary mt-1.5">{previewHit.snippet}</p>
            <div className="mt-2 text-[11px] font-mono text-text-secondary break-all">{previewHit.deepLinkUri}</div>
          </div>
          <button
            type="button"
            data-testid="cmdk-preview-navigate-btn"
            onClick={() => onExecuteHit(previewHit)}
            onKeyDown={(e) => handleRgaaSubmitKeyDown(e, () => onExecuteHit(previewHit))}
            className="w-full py-1 rounded text-xs bg-brand-primary text-surface-elevated font-medium"
          >
            {labels.deepLinkActionLabel}
          </button>
        </aside>
      )}
    </div>
  );
}
