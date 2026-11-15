import React from "react";

export interface AssistantNoEmbeddingBannerProps {
  readonly title: string;
  readonly description: string;
  readonly configureCta: string;
  readonly onConfigure: () => void;
}

export function AssistantNoEmbeddingBanner(props: AssistantNoEmbeddingBannerProps): React.JSX.Element {
  const { title, description, configureCta, onConfigure } = props;
  return (
    <div
      role="alert"
      data-testid="assistant-no-embedding-banner"
      className="mb-2 flex flex-col gap-1.5 rounded-lg border border-status-warning/40 bg-status-warning/10 p-3 text-xs text-text-primary"
    >
      <div className="flex items-center gap-2 font-semibold text-status-warning">
        <span>⚠️ {title}</span>
      </div>
      <p className="text-text-secondary">{description}</p>
      <div>
        <a
          href="/settings/ai-models"
          data-testid="assistant-configure-embedding-link"
          onClick={(e) => {
            e.preventDefault();
            onConfigure();
          }}
          className="inline-flex items-center gap-1 font-medium text-action-primary underline hover:opacity-80"
        >
          {configureCta}
        </a>
      </div>
    </div>
  );
}
