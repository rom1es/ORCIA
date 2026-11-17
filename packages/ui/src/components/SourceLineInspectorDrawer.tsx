import * as DialogPrimitive from "@radix-ui/react-dialog";
import React, { useEffect, useRef } from "react";
import type {
  SourceLineInspectorLabels,
  SourceLineInspectorLineItem,
  UiFileBadgeCode,
} from "./AgentExecutionTraceTypes";
import { OrciaIcon } from "./icons";

export interface SourceLineInspectorDrawerProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly resourceUri: string;
  readonly displayFilename?: string;
  readonly fileBadgeCode?: UiFileBadgeCode;
  readonly startLine: number;
  readonly endLine: number;
  readonly totalLines: number;
  readonly lines: readonly SourceLineInspectorLineItem[];
  readonly isLoading?: boolean;
  readonly redacted?: boolean;
  readonly redactedReason?: string | null;
  readonly permissionRequestHint?: string | null;
  readonly errorMessage?: string | null;
  readonly copiedFeedback?: boolean;
  readonly labels: SourceLineInspectorLabels;
  readonly onCopySlice: () => void;
}

export function SourceLineInspectorDrawer({
  open,
  onOpenChange,
  resourceUri,
  displayFilename,
  fileBadgeCode = "DOC",
  startLine,
  endLine,
  totalLines,
  lines,
  isLoading = false,
  redacted = false,
  permissionRequestHint = null,
  errorMessage = null,
  copiedFeedback = false,
  labels,
  onCopySlice,
}: SourceLineInspectorDrawerProps): React.JSX.Element {
  const firstHighlightedRef = useRef<HTMLDivElement | null>(null);
  const effectiveTitle =
    displayFilename || resourceUri.split("/").pop() || resourceUri || labels.dialogAriaLabel;
  const safeStart = Math.max(1, startLine);
  const safeEnd = Math.max(safeStart, endLine);
  const safeTotal = Math.max(totalLines, lines.length, safeEnd);

  useEffect(() => {
    if (!open || isLoading || redacted || lines.length === 0) return;
    const node = firstHighlightedRef.current;
    if (node && typeof node.scrollIntoView === "function") {
      node.scrollIntoView({ block: "center" });
    }
  }, [open, isLoading, redacted, lines, safeStart]);

  const canCopy = !isLoading && !redacted && lines.length > 0;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          data-testid="source-line-inspector-overlay"
          className="orcia-line-inspector-overlay"
        />
        <DialogPrimitive.Content
          data-testid="source-line-inspector-drawer"
          aria-label={labels.dialogAriaLabel}
          className="orcia-line-inspector-drawer"
        >
          <header
            className="flex flex-col gap-2 border-b p-3.5"
            style={{
              borderColor: "var(--color-border-subtle)",
              backgroundColor: "var(--color-surface-card)",
            }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    data-testid="inspector-file-badge"
                    className="orcia-execution-trace-badge"
                  >
                    {fileBadgeCode}
                  </span>
                  <DialogPrimitive.Title className="m-0 truncate text-sm font-semibold text-text-primary">
                    {effectiveTitle}
                  </DialogPrimitive.Title>
                </div>
                <DialogPrimitive.Description className="m-0 break-all font-mono text-[11px] text-text-secondary">
                  {resourceUri}
                </DialogPrimitive.Description>
              </div>

              <DialogPrimitive.Close asChild>
                <button
                  type="button"
                  data-testid="inspector-close-btn"
                  aria-label={labels.closeButtonLabel}
                  className="orcia-ds-btn orcia-ds-btn-secondary text-xs shrink-0"
                >
                  <OrciaIcon name="close" />
                  <span>{labels.closeButtonLabel}</span>
                </button>
              </DialogPrimitive.Close>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
              <span
                data-testid="inspector-slice-summary"
                className="font-medium text-text-secondary"
              >
                {labels.linesSliceSummary(safeStart, safeEnd, safeTotal)}
              </span>

              <button
                type="button"
                data-testid="inspector-copy-slice-btn"
                disabled={!canCopy}
                onClick={onCopySlice}
                className="orcia-ds-btn orcia-ds-btn-secondary text-xs"
              >
                <OrciaIcon name={copiedFeedback ? "check" : "copy"} />
                <span>
                  {copiedFeedback
                    ? labels.copiedSliceFeedbackLabel
                    : labels.copySliceButtonLabel(safeStart, safeEnd)}
                </span>
              </button>
            </div>
          </header>

          <div className="flex-1 min-h-0 flex flex-col">
            {isLoading ? (
              <div
                role="status"
                data-testid="inspector-loading-state"
                className="p-5 text-xs font-medium text-text-secondary flex items-center gap-2"
              >
                <OrciaIcon name="hourglass" />
                <span>{labels.loadingLabel}</span>
              </div>
            ) : errorMessage ? (
              <div className="p-4">
                <div
                  role="alert"
                  data-testid="inspector-error-banner"
                  className="orcia-ds-alert orcia-ds-alert-error"
                >
                  {errorMessage}
                </div>
              </div>
            ) : redacted ? (
              <div className="p-4">
                <div
                  role="region"
                  aria-label={labels.redactedTitle}
                  data-testid="inspector-redacted-banner"
                  className="rounded-lg border p-4 space-y-2 text-xs"
                  style={{
                    backgroundColor: "var(--color-arbitration-bg)",
                    borderColor: "var(--color-arbitration-amber)",
                    color: "var(--color-text-primary)",
                  }}
                >
                  <div className="flex items-center gap-2 font-semibold text-sm">
                    <OrciaIcon name="lock" />
                    <span>{labels.redactedTitle}</span>
                  </div>
                  <p className="m-0 leading-relaxed text-text-secondary">
                    {labels.redactedBody}
                  </p>
                  {permissionRequestHint ? (
                    <div
                      data-testid="inspector-redacted-hint"
                      className="rounded border p-2 font-medium"
                      style={{
                        backgroundColor: "var(--color-surface-card)",
                        borderColor: "var(--color-border-subtle)",
                      }}
                    >
                      {labels.redactedHintPrefix} {permissionRequestHint}
                    </div>
                  ) : null}
                </div>
              </div>
            ) : lines.length === 0 ? (
              <div
                data-testid="inspector-empty-state"
                className="p-5 text-xs text-text-secondary"
              >
                {labels.emptySliceLabel}
              </div>
            ) : (
              <div
                data-testid="inspector-code-lines-list"
                className="orcia-line-inspector-code-scroll py-2"
              >
                {lines.map((line, idx) => {
                  const isHighlighted =
                    line.lineNumber >= safeStart && line.lineNumber <= safeEnd;
                  const isFirstHighlighted =
                    isHighlighted &&
                    (idx === 0 || lines[idx - 1]!.lineNumber < safeStart);

                  return (
                    <div
                      key={line.lineNumber}
                      ref={isFirstHighlighted ? firstHighlightedRef : undefined}
                      data-testid={`inspector-code-line-${line.lineNumber}`}
                      data-line-number={line.lineNumber}
                      data-highlighted={isHighlighted ? "true" : "false"}
                      className="orcia-line-inspector-row"
                    >
                      <span className="orcia-line-inspector-gutter">
                        {line.lineNumber}
                      </span>
                      <span style={{ whiteSpace: "pre" }}>{line.content}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
