import {
  FormattedMarkdownContent,
  OrciaDataCard,
  OrciaTabStrip,
  type UiAgentTraceEventItem,
  type UiSourceLineInspectTarget,
} from "@orcia/ui";
import React, { useMemo } from "react";
import { resolveDictionaryForFlag } from "../../../i18n";
import type {
  DeterministicSubStepItem,
  WorkflowDefinitionV2Item,
} from "../processStudioV2Data";

export interface ProcessRunArtifactPaneProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly isFr: boolean;
  readonly currentSubStep: DeterministicSubStepItem | undefined;
  readonly artifactMarkdown: string;
  readonly isEditingDiff: boolean;
  readonly traceEvents?: readonly UiAgentTraceEventItem[];
  readonly onChangeArtifactMarkdown: (value: string) => void;
  readonly onSetIsEditingDiff: (editing: boolean) => void;
  readonly onSaveAmendedDiff: () => void;
  readonly onInspectSourceLines?: (target: UiSourceLineInspectTarget) => void;
}

function extractSourceChips(
  events: readonly UiAgentTraceEventItem[],
): readonly UiSourceLineInspectTarget[] {
  const seen = new Set<string>();
  const chips: UiSourceLineInspectTarget[] = [];
  for (const ev of events) {
    if (!ev.resourceUri) continue;
    const startLine = ev.startLine ?? 1;
    const endLine = ev.endLine ?? startLine;
    const key = `${ev.resourceUri}:${startLine}-${endLine}`;
    if (seen.has(key)) continue;
    seen.add(key);
    chips.push({
      uri: ev.resourceUri,
      filename: ev.displayFilename ?? ev.resourceUri,
      startLine,
      endLine,
      ...(ev.fileBadgeCode ? { badgeCode: ev.fileBadgeCode } : {}),
    });
  }
  return chips;
}

export function ProcessRunArtifactPane({
  workflow,
  isFr,
  currentSubStep,
  artifactMarkdown,
  isEditingDiff,
  traceEvents = [],
  onChangeArtifactMarkdown,
  onSetIsEditingDiff,
  onSaveAmendedDiff,
  onInspectSourceLines,
}: ProcessRunArtifactPaneProps): React.JSX.Element {
  const copy = resolveDictionaryForFlag(isFr).processVsmExecutionUi.execution;
  const sourceChips = useMemo(() => extractSourceChips(traceEvents), [traceEvents]);
  const modeTab: "preview" | "edit" = isEditingDiff ? "edit" : "preview";

  return (
    <OrciaDataCard
      testId="claim-check-s3-artifact-box"
      icon="document"
      title={`${copy.proposedDeliverablePrefix} — ${currentSubStep?.name ?? workflow.title}`}
      subtitle={currentSubStep?.output_description || undefined}
      actions={
        <OrciaTabStrip<"preview" | "edit">
          testId="artifact-mode-toggle-tabs"
          ariaLabel={copy.deliverableModeAriaLabel}
          variant="segmented"
          activeTabId={modeTab}
          onSelectTab={(nextMode) => onSetIsEditingDiff(nextMode === "edit")}
          tabs={[
            {
              key: "preview",
              label: copy.modePreviewLabel,
              testId: "artifact-mode-preview-btn",
            },
            {
              key: "edit",
              label: copy.modeEditLabel,
              testId: "artifact-mode-edit-btn",
            },
          ]}
        />
      }
    >
      {sourceChips.length > 0 && onInspectSourceLines ? (
        <div
          data-testid="focus-artifact-source-chips"
          className="mb-3 flex flex-wrap items-center gap-1.5"
        >
          <span className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>
            {copy.sourcesChipsHeading}
          </span>
          {sourceChips.map((chip, idx) => (
            <button
              key={`${chip.uri}-${chip.startLine}-${idx}`}
              type="button"
              data-testid={`focus-artifact-source-chip-${idx}`}
              onClick={() => onInspectSourceLines(chip)}
              className="orcia-ds-filter-pill font-mono text-xs"
            >
              {chip.filename ?? chip.uri}
              {chip.startLine > 0 ? ` #L${chip.startLine}-${chip.endLine}` : ""}
            </button>
          ))}
        </div>
      ) : null}

      {isEditingDiff ? (
        <div className="flex flex-col gap-2.5">
          <textarea
            aria-label={copy.deliverableContentAriaLabel}
            data-testid="amend-diff-markdown-textarea"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            rows={12}
            value={artifactMarkdown}
            onChange={(e) => onChangeArtifactMarkdown(e.target.value)}
            className="orcia-ds-textarea"
            style={{ fontSize: "13px" }}
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              data-testid="confirm-amend-diff-btn"
              onClick={onSaveAmendedDiff}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
            >
              {copy.saveChangesBtn}
            </button>
            <button
              type="button"
              data-testid="cancel-amend-diff-btn"
              onClick={() => onSetIsEditingDiff(false)}
              className="orcia-ds-btn orcia-ds-btn-ghost orcia-ds-btn-sm"
            >
              {copy.cancelBtn}
            </button>
          </div>
        </div>
      ) : (
        <div
          data-testid="artifact-markdown-preview"
          className="rounded-md border p-3.5"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <FormattedMarkdownContent
            content={artifactMarkdown}
            testId="artifact-markdown-formatted"
          />
        </div>
      )}
    </OrciaDataCard>
  );
}
