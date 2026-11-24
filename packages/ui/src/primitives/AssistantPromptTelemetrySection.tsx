import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import type {
  AssistantGovernanceModalAndStudioLabels,
  UiAssistantPromptTelemetryRecord,
} from "./AssistantGovernanceTypes";

export function AssistantPromptTelemetrySection({
  promptTelemetryLog,
  labels,
}: {
  readonly promptTelemetryLog: readonly UiAssistantPromptTelemetryRecord[];
  readonly labels: AssistantGovernanceModalAndStudioLabels;
}): React.JSX.Element {
  const [expandedTelemetryTurnId, setExpandedTelemetryTurnId] = useState<string | null>(null);

  return (
    <div
      data-testid="assistant-prompt-telemetry-log-section"
      className="rounded-lg border border-surface-border bg-surface-primary p-3 space-y-2"
    >
      <div className="flex items-center justify-between">
        <span className="font-semibold text-xs">
          <OrciaIcon name="finops" /> {labels.telemetryHeading} ({promptTelemetryLog.length})
        </span>
        <span className="text-[11px] text-text-secondary">{labels.telemetrySubtitle}</span>
      </div>
      {promptTelemetryLog.length === 0 ? (
        <p data-testid="assistant-prompt-telemetry-empty" className="text-[11px] text-text-secondary">
          {labels.telemetryEmptyIntro} (<OrciaIcon name="thumbUp" /> {labels.telemetryLikeLabel} /{" "}
          <OrciaIcon name="thumbDown" /> {labels.telemetryDislikeLabel}).
        </p>
      ) : (
        <ul className="space-y-2 max-h-60 overflow-y-auto pr-1">
          {promptTelemetryLog.map((entry, idx) => {
            const isExpanded = expandedTelemetryTurnId === entry.turnId;
            return (
              <li
                key={`${entry.turnId}-${idx}`}
                data-testid={`assistant-prompt-telemetry-item-${idx}`}
                className="rounded border border-surface-border bg-surface-secondary p-2.5 space-y-1.5 text-[11px]"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-text-primary">{entry.userPrompt}</span>
                  <div className="flex items-center gap-1.5">
                    {entry.userFeedback === "LIKE" && (
                      <span
                        data-testid={`assistant-telemetry-feedback-${idx}`}
                        className="rounded-full bg-action-primary/15 px-2 py-0.5 font-semibold text-action-primary"
                      >
                        <OrciaIcon name="thumbUp" /> {labels.telemetryLikeLabel}
                      </span>
                    )}
                    {entry.userFeedback === "DISLIKE" && (
                      <span
                        data-testid={`assistant-telemetry-feedback-${idx}`}
                        className="rounded-full bg-status-warning/15 px-2 py-0.5 font-semibold text-status-warning"
                      >
                        <OrciaIcon name="thumbDown" /> {labels.telemetryDislikeLabel}
                      </span>
                    )}
                    {!entry.userFeedback && (
                      <span data-testid={`assistant-telemetry-feedback-${idx}`} className="text-text-secondary">
                        {labels.telemetryUnratedLabel}
                      </span>
                    )}
                    <button
                      type="button"
                      data-testid={`assistant-telemetry-toggle-context-${idx}`}
                      onClick={() => setExpandedTelemetryTurnId(isExpanded ? null : entry.turnId)}
                      className="rounded border border-surface-border bg-surface-primary px-2 py-0.5 text-[10px] font-medium text-text-primary"
                    >
                      {isExpanded ? labels.telemetryHideContextCta : labels.telemetryInspectContextCta}
                    </button>
                  </div>
                </div>
                <div className="text-[10px] text-text-secondary">
                  {`${labels.telemetryModelPrefix} ${entry.modelLabel} · ${labels.telemetryThinkingPrefix} ${entry.thinkingEffort} (${entry.thinkingElapsedSeconds}s) · ${labels.telemetryHistoryPrefix} ${entry.conversationHistoryCount} ${labels.telemetryMessagesUnit}`}
                  {entry.folderTitle ? (
                    <>
                      {" · "}
                      <OrciaIcon name="folder" /> {`${labels.telemetryFolderPrefix} ${entry.folderTitle}`}
                    </>
                  ) : (
                    ""
                  )}
                </div>
                {isExpanded && (
                  <div
                    data-testid={`assistant-telemetry-context-box-${idx}`}
                    className="rounded border border-surface-border bg-surface-primary p-2 space-y-1"
                  >
                    <div className="font-semibold text-[10px] text-text-secondary">
                      {labels.telemetrySystemPromptHeading}
                    </div>
                    <pre className="text-[10px] font-mono text-text-secondary whitespace-pre-wrap max-h-40 overflow-y-auto">
                      {entry.assembledSystemPrompt || labels.telemetryDefaultContextFallback}
                    </pre>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
