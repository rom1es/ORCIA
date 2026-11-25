import { OrciaIcon, OrciaSpinner } from "@orcia/ui";
import React from "react";
import type { TranslationDictionary } from "../../i18n/types";

export interface AssistantReindexingBannerProps {
  readonly status: "PENDING" | "IN_PROGRESS" | "FAILED";
  readonly progressPercentage: number;
  readonly errorMessage?: string | null;
  readonly labels: TranslationDictionary["assistantRagNotice"];
  readonly canConfigureAiModels?: boolean;
  readonly onRelaunch?: () => void;
  readonly onConfigure?: () => void;
}

export function AssistantReindexingBanner(
  props: AssistantReindexingBannerProps,
): React.JSX.Element {
  const {
    status,
    progressPercentage,
    errorMessage,
    labels,
    canConfigureAiModels = false,
    onRelaunch,
    onConfigure,
  } = props;

  if (status === "FAILED") {
    return (
      <div
        role="status"
        data-testid="assistant-rag-inactive-notice"
        className="flex flex-1 flex-col gap-1 rounded-lg border border-status-warning/40 bg-status-warning/10 px-3 py-1.5 text-xs text-text-primary"
      >
        <div className="flex items-center gap-2 font-medium text-status-warning">
          <OrciaIcon name="warning" size={14} />
          <span>{labels.reindexFailedTitle}</span>
        </div>
        <p className="text-text-secondary">{errorMessage || labels.reindexFailedDescription}</p>
        <div className="flex flex-wrap items-center gap-3">
          {canConfigureAiModels && onRelaunch && (
            <button
              type="button"
              data-testid="assistant-relaunch-reindex-btn"
              onClick={onRelaunch}
              className="inline-flex items-center gap-1 rounded bg-surface-elevated px-2.5 py-1 font-medium text-text-primary hover:opacity-90"
            >
              <OrciaIcon name="regenerate" size={13} />
              <span>{labels.relaunchReindexCta}</span>
            </button>
          )}
          {canConfigureAiModels && onConfigure ? (
            <a
              href="/settings/ai-models"
              data-testid="assistant-configure-embedding-link"
              onClick={(e) => {
                e.preventDefault();
                onConfigure();
              }}
              className="inline-flex items-center gap-1 font-medium text-action-primary underline hover:opacity-80"
            >
              {labels.checkEmbeddingCta}
            </a>
          ) : (
            <span data-testid="assistant-rag-admin-guidance" className="text-[11px] text-text-secondary">
              {labels.contactAdminGuidance}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      role="status"
      data-testid="assistant-rag-inactive-notice"
      className="flex flex-1 flex-col gap-1.5 rounded-lg border border-border-subtle bg-surface-secondary px-3 py-1.5 text-xs text-text-primary"
    >
      <div className="flex items-center justify-between font-medium text-text-primary">
        <span className="inline-flex items-center gap-1.5">
          <OrciaSpinner size="xs" />
          <span>
            {labels.reindexingTitle} ({progressPercentage}%)
          </span>
        </span>
        <span className="font-mono text-xs text-text-secondary">{progressPercentage}%</span>
      </div>
      <p className="text-text-secondary">{labels.reindexingDescription}</p>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-muted">
        <div
          data-testid="assistant-reindexing-progress-bar"
          className="h-full bg-action-primary transition-all duration-300"
          style={{ width: `${Math.max(5, Math.min(100, progressPercentage))}%` }}
        />
      </div>
    </div>
  );
}
