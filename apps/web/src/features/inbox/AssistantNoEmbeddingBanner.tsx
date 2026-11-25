import { OrciaIcon } from "@orcia/ui";
import React from "react";

export interface AssistantNoEmbeddingBannerProps {
  readonly title: string;
  readonly description: string;
  readonly configureCta: string;
  readonly adminContactGuidance: string;
  readonly canConfigureAiModels: boolean;
  readonly onConfigure: () => void;
}

export function AssistantNoEmbeddingBanner(
  props: AssistantNoEmbeddingBannerProps,
): React.JSX.Element {
  const {
    title,
    description,
    configureCta,
    adminContactGuidance,
    canConfigureAiModels,
    onConfigure,
  } = props;
  return (
    <div
      role="status"
      title={description}
      data-testid="assistant-rag-inactive-notice"
      className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-2 rounded-lg border border-border-subtle bg-surface-secondary px-3 py-1.5 text-[11px] text-text-secondary"
    >
      <span className="inline-flex min-w-0 items-center gap-1.5 font-medium text-text-primary">
        <OrciaIcon name="infoBadge" size={14} />
        <span className="truncate">{title}</span>
      </span>
      {canConfigureAiModels ? (
        <a
          href="/settings/ai-models"
          data-testid="assistant-configure-embedding-link"
          onClick={(e) => {
            e.preventDefault();
            onConfigure();
          }}
          className="shrink-0 font-medium text-action-primary underline hover:opacity-80"
        >
          {configureCta}
        </a>
      ) : (
        <span
          data-testid="assistant-rag-admin-guidance"
          className="shrink-0 text-[11px] text-text-secondary"
        >
          {adminContactGuidance}
        </span>
      )}
    </div>
  );
}
