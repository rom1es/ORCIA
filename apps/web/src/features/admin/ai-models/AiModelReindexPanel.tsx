import { createOrciaApiClient } from "@orcia/api-client";
import React, { useCallback, useEffect, useState } from "react";

export interface AiModelReindexPanelProps {
  readonly isFr: boolean;
  readonly canExecute: boolean;
}

export function AiModelReindexPanel({ isFr, canExecute }: AiModelReindexPanelProps): React.JSX.Element {
  const [status, setStatus] = useState<string>("IDLE");
  const [progressPercentage, setProgressPercentage] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [targetModelName, setTargetModelName] = useState<string | null>(null);
  const [totalChunks, setTotalChunks] = useState<number>(0);
  const [processedChunks, setProcessedChunks] = useState<number>(0);
  const [isRelaunching, setIsRelaunching] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const client = createOrciaApiClient({ baseUrl: "" });
      const res = await client.aiModelsHub.getReindexStatus();
      setStatus(res.status ?? "IDLE");
      setProgressPercentage(res.progress_percentage ?? 0);
      setErrorMessage(res.error_message ?? null);
      setTargetModelName(res.target_model_name ?? null);
      setTotalChunks(res.total_chunks ?? 0);
      setProcessedChunks(res.processed_chunks ?? 0);
    } catch (err: unknown) {
      console.warn("[ORCIA-UI] Failed to fetch reindex status:", err);
    }
  }, []);

  const handleRelaunch = async () => {
    if (!canExecute || isRelaunching) return;
    setIsRelaunching(true);
    setFeedback(null);
    try {
      const client = createOrciaApiClient({ baseUrl: "" });
      await client.aiModelsHub.reindexEmbeddings();
      setFeedback(isFr ? "Réindexation globale lancée avec succès." : "Global reindexing triggered successfully.");
      await fetchStatus();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setFeedback(isFr ? `Échec du lancement : ${msg}` : `Trigger failed: ${msg}`);
    } finally {
      setIsRelaunching(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    void fetchStatus();
    const interval = setInterval(() => {
      if (isMounted) void fetchStatus();
    }, 2500);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [fetchStatus]);

  const isJobActive = status === "PENDING" || status === "IN_PROGRESS";
  const isJobFailed = status === "FAILED";

  return (
    <div
      data-testid="ai-model-reindex-panel"
      className="rounded-lg border border-border-default bg-surface-card p-4 space-y-3"
    >
      <div className="flex justify-between items-center">
        <div>
          <h4
            className="text-sm font-semibold text-text-primary"
            data-testid="reindex-panel-title"
          >
            {isFr ? "Réindexation Sémantique & Corpus Vectoriel (AD-24.7)" : "Semantic Reindexing & Vector Corpus (AD-24.7)"}
          </h4>
          <p className="text-xs text-text-secondary mt-1">
            {targetModelName
              ? isFr
                ? `Modèle actif : ${targetModelName} (${processedChunks}/${totalChunks} chunks)`
                : `Active model: ${targetModelName} (${processedChunks}/${totalChunks} chunks)`
              : isFr
                ? "Aucun modèle d'embedding actif"
                : "No active embedding model"}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <span
            data-testid="reindex-status-badge"
            className={`text-xs px-2 py-0.5 rounded font-medium ${
              isJobActive
                ? "bg-blue-500/20 text-blue-400"
                : isJobFailed
                  ? "bg-red-500/20 text-red-400"
                  : "bg-emerald-500/20 text-emerald-400"
            }`}
          >
            {status} ({progressPercentage}%)
          </span>

          {canExecute && (
            <button
              type="button"
              data-testid="relaunch-reindex-button"
              onClick={() => void handleRelaunch()}
              disabled={isJobActive || isRelaunching}
              className={`px-3 py-1.5 text-xs font-semibold rounded text-white ${
                isJobActive || isRelaunching
                  ? "bg-surface-muted opacity-50 cursor-not-allowed"
                  : "bg-action-primary hover:bg-action-primary-hover cursor-pointer"
              }`}
            >
              🔄 {isFr ? "Relancer la réindexation" : "Relaunch reindexing"}
            </button>
          )}
        </div>
      </div>

      {isJobActive && (
        <div
          data-testid="reindex-progress-bar-container"
          className="w-full h-1.5 bg-surface-muted rounded overflow-hidden"
        >
          <div
            data-testid="reindex-progress-bar"
            className="h-full bg-action-primary transition-all duration-300"
            style={{
              width: `${Math.max(5, Math.min(100, progressPercentage))}%`,
            }}
          />
        </div>
      )}

      {errorMessage && (
        <div
          role="alert"
          data-testid="reindex-error-message"
          className="text-xs text-red-400 bg-red-500/10 px-3 py-2 rounded"
        >
          ⚠️ {errorMessage}
        </div>
      )}

      {feedback && (
        <div
          data-testid="reindex-feedback"
          className="text-xs text-text-secondary"
        >
          {feedback}
        </div>
      )}
    </div>
  );
}
