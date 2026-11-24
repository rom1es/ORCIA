import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import type {
  ChunkValidationCardLabels,
  UiChunkDecisionAction,
  UiChunkValidationItem,
} from "./ChunkValidationCard";

export interface ChunkValidationItemsListProps {
  chunks: readonly UiChunkValidationItem[];
  activeIndex: number;
  readOnly: boolean;
  labels: ChunkValidationCardLabels;
  onSelectIndex: (index: number) => void;
  onDecideChunk: (
    chunkKey: string,
    action: UiChunkDecisionAction,
    coEditedContent?: string,
  ) => void;
}

export function ChunkValidationItemsList({
  chunks,
  activeIndex,
  readOnly,
  labels,
  onSelectIndex,
  onDecideChunk,
}: ChunkValidationItemsListProps): React.ReactElement {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {chunks.map((chunk, idx) => {
        const isFocused = idx === activeIndex;
        const isApproved =
          chunk.status === "APPROVED" || chunk.status === "CO_EDITED";
        const statusText =
          chunk.status === "PENDING"
            ? (labels.statusLabels?.pending ?? chunk.status)
            : chunk.status === "APPROVED"
              ? (labels.statusLabels?.approved ?? chunk.status)
              : chunk.status === "CO_EDITED"
                ? (labels.statusLabels?.coEdited ?? chunk.status)
                : chunk.status;
        return (
          <article
            key={chunk.chunkKey}
            data-testid={`chunk-validation-card-${chunk.chunkKey}`}
            data-active={isFocused ? "true" : "false"}
            data-status={chunk.status}
            onClick={() => onSelectIndex(idx)}
            style={{
              padding: "12px",
              borderRadius: "var(--radius-md)",
              backgroundColor: isApproved
                ? "var(--color-gate-emerald-bg)"
                : "var(--color-surface-hover)",
              border: isFocused
                ? "2px solid var(--color-primary-cobalt)"
                : "1px solid var(--color-border)",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span style={{ fontWeight: 600 }}>
                {chunk.sectionTitle}{" "}
                <small
                  style={{
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-muted-foreground)",
                  }}
                >
                  {`(${chunk.wordCount}${labels.wordsUnitLabel ? ` ${labels.wordsUnitLabel}` : ""})`}
                </small>
              </span>
              <span
                data-testid={`chunk-status-badge-${chunk.chunkKey}`}
                data-status={chunk.status}
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--font-size-mono)",
                  color: isApproved
                    ? "var(--color-gate-emerald)"
                    : "var(--color-arbitration-amber)",
                }}
              >
                {statusText}
              </span>
            </div>

            <p style={{ margin: 0, color: "var(--color-foreground)" }}>
              {chunk.contentMarkdown}
            </p>

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                data-testid={`chunk-approve-btn-${chunk.chunkKey}`}
                disabled={readOnly}
                onClick={(e) => {
                  e.stopPropagation();
                  onDecideChunk(chunk.chunkKey, "APPROVE");
                }}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  backgroundColor: "var(--color-gate-emerald)",
                  color: "var(--color-primary-foreground)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  padding: "6px 10px",
                  fontWeight: 600,
                  cursor: readOnly ? "not-allowed" : "pointer",
                }}
              >
                <span>
                  <OrciaIcon name="check" /> {labels.approveSectionLabel}
                </span>
                <DisabledButtonAlertIndicator
                  disabled={Boolean(readOnly)}
                  reason={labels.readOnlyApproveReason ?? labels.pendingSectionsNotice}
                  testIdSuffix={`chunk-approve-btn-${chunk.chunkKey}`}
                />
              </button>

              <button
                type="button"
                data-testid={`chunk-coedit-btn-${chunk.chunkKey}`}
                disabled={readOnly}
                onClick={(e) => {
                  e.stopPropagation();
                  const tag = labels.coEditedTagLabel ?? "CO_EDITED";
                  onDecideChunk(
                    chunk.chunkKey,
                    "CO_EDIT",
                    `${chunk.contentMarkdown} [${tag}]`,
                  );
                }}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  backgroundColor: "var(--color-surface-card)",
                  color: "var(--color-foreground)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                  padding: "6px 10px",
                  fontWeight: 600,
                  cursor: readOnly ? "not-allowed" : "pointer",
                }}
              >
                <span>
                  <OrciaIcon name="pen" /> {labels.coEditSectionLabel}
                </span>
                <DisabledButtonAlertIndicator
                  disabled={Boolean(readOnly)}
                  reason={labels.readOnlyCoEditReason ?? labels.pendingSectionsNotice}
                  testIdSuffix={`chunk-coedit-btn-${chunk.chunkKey}`}
                />
              </button>

              <button
                type="button"
                data-testid={`chunk-challenge-btn-${chunk.chunkKey}`}
                disabled={readOnly}
                onClick={(e) => {
                  e.stopPropagation();
                  onDecideChunk(chunk.chunkKey, "CHALLENGE");
                }}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  backgroundColor: "var(--color-stale-bg)",
                  color: "var(--color-stale-crimson)",
                  border: "1px solid var(--color-stale-crimson)",
                  borderRadius: "var(--radius-sm)",
                  padding: "6px 10px",
                  fontWeight: 600,
                  cursor: readOnly ? "not-allowed" : "pointer",
                }}
              >
                <span>
                  <OrciaIcon name="rollback" /> {labels.challengeSectionLabel}
                </span>
                <DisabledButtonAlertIndicator
                  disabled={Boolean(readOnly)}
                  reason={labels.readOnlyChallengeReason ?? labels.pendingSectionsNotice}
                  testIdSuffix={`chunk-challenge-btn-${chunk.chunkKey}`}
                />
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}
