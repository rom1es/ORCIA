import { OrciaIcon } from "@orcia/ui";
import React from "react";

export interface AssistantNoEmbeddingBannerProps {
  readonly title: string;
  readonly description: string;
  readonly configureCta: string;
  readonly onConfigure: () => void;
}

export function AssistantNoEmbeddingBanner(
  props: AssistantNoEmbeddingBannerProps,
): React.JSX.Element {
  const { title, description, configureCta, onConfigure } = props;
  return (
    <div
      role="status"
      data-testid="assistant-rag-inactive-notice"
      className="mb-2 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border-subtle bg-surface-secondary px-3 py-2 text-xs text-text-secondary"
    >
      <div className="flex flex-col gap-0.5">
        <span className="inline-flex items-center gap-1.5 font-medium text-text-primary">
          <OrciaIcon name="infoBadge" size={14} />
          <span>{title}</span>
        </span>
        <span>{description}</span>
      </div>
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
    </div>
  );
}
