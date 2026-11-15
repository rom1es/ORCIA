import React from "react";

export interface AssistantReindexingBannerProps {
  readonly status: "PENDING" | "IN_PROGRESS" | "FAILED";
  readonly progressPercentage: number;
  readonly errorMessage?: string | null;
  readonly isFr?: boolean;
  readonly onRelaunch?: () => void;
  readonly onConfigure?: () => void;
}

export function AssistantReindexingBanner(props: AssistantReindexingBannerProps): React.JSX.Element {
  const { status, progressPercentage, errorMessage, isFr = true, onRelaunch, onConfigure } = props;

  if (status === "FAILED") {
    return (
      <div
        role="alert"
        data-testid="assistant-reindex-failed-banner"
        className="mb-2 flex flex-col gap-2 rounded-lg border border-status-danger/40 bg-status-danger/10 p-3 text-xs text-text-primary"
      >
        <div className="flex items-center gap-2 font-semibold text-status-danger">
          <span>❌ {isFr ? "Échec de la réindexation sémantique" : "Semantic reindexing failed"}</span>
        </div>
        <p className="text-text-secondary">
          {errorMessage ||
            (isFr
              ? "Le recalcul vectoriel a échoué. Mon Assistant reste bloqué pour éviter tout résultat incohérent."
              : "Vector recalculation failed. My Assistant remains locked to prevent inconsistent results.")}
        </p>
        <div className="flex items-center gap-3">
          {onRelaunch && (
            <button
              type="button"
              data-testid="assistant-relaunch-reindex-btn"
              onClick={onRelaunch}
              className="inline-flex items-center gap-1 rounded bg-status-danger/20 px-2.5 py-1 font-medium text-status-danger hover:bg-status-danger/30"
            >
              🔄 {isFr ? "Relancer la réindexation" : "Relaunch reindexing"}
            </button>
          )}
          {onConfigure && (
            <a
              href="/settings/ai-models"
              data-testid="assistant-configure-embedding-link"
              onClick={(e) => {
                e.preventDefault();
                onConfigure();
              }}
              className="inline-flex items-center gap-1 font-medium text-action-primary underline hover:opacity-80"
            >
              {isFr ? "Vérifier le modèle d'embedding" : "Check embedding model"}
            </a>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      role="alert"
      data-testid="assistant-reindexing-banner"
      className="mb-2 flex flex-col gap-2 rounded-lg border border-accent-brand/40 bg-accent-brand/10 p-3 text-xs text-text-primary"
    >
      <div className="flex items-center justify-between font-semibold text-accent-brand">
        <span className="flex items-center gap-2">
          ⏳ {isFr ? "Réindexation sémantique en cours" : "Semantic reindexing in progress"} : {progressPercentage}%
        </span>
        <span className="text-xs font-mono">{progressPercentage}%</span>
      </div>
      <p className="text-text-secondary">
        {isFr
          ? "Un nouveau modèle d'embedding est activé. Le corpus vectoriel est en cours de réindexation complète. Mon Assistant et la recherche sont temporairement indisponibles."
          : "A new embedding model is active. The vector corpus is currently undergoing complete reindexing. My Assistant and search are temporarily unavailable."}
      </p>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-muted">
        <div
          data-testid="assistant-reindexing-progress-bar"
          className="h-full bg-accent-brand transition-all duration-300"
          style={{ width: `${Math.max(5, Math.min(100, progressPercentage))}%` }}
        />
      </div>
    </div>
  );
}
