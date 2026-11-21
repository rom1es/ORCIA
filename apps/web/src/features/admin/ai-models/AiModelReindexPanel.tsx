import { createOrciaApiClient } from "@orcia/api-client";
import { OrciaIcon, OrciaSpinner } from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import { useI18n } from "../../../i18n";
import { AI_MODELS_HUB_EN, AI_MODELS_HUB_FR } from "../../../i18n/locales/ai_models_hub_labels";

export interface AiModelReindexPanelProps {
  readonly isFr: boolean;
  readonly canExecute: boolean;
  readonly hasActiveEmbeddingModel?: boolean;
  readonly refreshSignal?: number;
}

export function AiModelReindexPanel({
  isFr,
  canExecute,
  hasActiveEmbeddingModel,
  refreshSignal = 0,
}: AiModelReindexPanelProps): React.JSX.Element | null {
  const { dictionary, locale } = useI18n();
  const labels =
    locale === (isFr ? "fr" : "en")
      ? dictionary.aiModelsHub.reindexPanel
      : (isFr ? AI_MODELS_HUB_FR : AI_MODELS_HUB_EN).reindexPanel;

  const [status, setStatus] = useState<string>("IDLE");
  const [progressPercentage, setProgressPercentage] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [targetModelName, setTargetModelName] = useState<string | null>(null);
  const [totalChunks, setTotalChunks] = useState<number>(0);
  const [processedChunks, setProcessedChunks] = useState<number>(0);
  const [indexedChunksCount, setIndexedChunksCount] = useState<number>(0);
  const [indexedDocumentsCount, setIndexedDocumentsCount] = useState<number>(0);
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
      setIndexedChunksCount(res.indexed_chunks_count ?? 0);
      setIndexedDocumentsCount(res.indexed_documents_count ?? 0);
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
      setFeedback(labels.launchSuccess);
      await fetchStatus();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setFeedback(`${labels.launchFailedPrefix} ${msg}`);
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
  }, [fetchStatus, refreshSignal]);

  const isJobActive = status === "PENDING" || status === "IN_PROGRESS";
  const isJobFailed = status === "FAILED";
  const hasCorpus = indexedChunksCount > 0 || indexedDocumentsCount > 0 || totalChunks > 0;

  if (!isJobActive && !isJobFailed && !hasCorpus) {
    return null;
  }

  const effectiveHasEmbedding = hasActiveEmbeddingModel ?? Boolean(targetModelName);
  const statusLabels: Record<string, string> = labels.statuses;
  const localizedStatus = statusLabels[status] ?? status;
  const effectiveChunks = totalChunks > 0 ? totalChunks : indexedChunksCount;
  const badgeText =
    status === "IDLE"
      ? `${localizedStatus} · ${effectiveChunks} ${labels.chunksUnit}`
      : `${localizedStatus} (${progressPercentage}%)`;
  const disableRelaunch = isJobActive || isRelaunching || !effectiveHasEmbedding;

  return (
    <div
      data-testid="ai-model-reindex-panel"
      className="rounded-lg border border-surface-border bg-surface-card p-4 space-y-3"
    >
      <div className="flex justify-between items-center">
        <div>
          <h4
            className="text-sm font-semibold text-text-primary"
            data-testid="reindex-panel-title"
          >
            {labels.title}
          </h4>
          <p className="text-xs text-text-secondary mt-1">
            {targetModelName
              ? `${labels.activeModelPrefix} ${targetModelName} (${totalChunks > 0 ? `${processedChunks}/${totalChunks}` : indexedChunksCount} ${labels.chunksUnit})`
              : effectiveHasEmbedding
                ? `${indexedDocumentsCount} ${labels.documentsUnit} · ${indexedChunksCount} ${labels.indexedChunksLabel}`
                : labels.noActiveModel}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <span
            data-testid="reindex-status-badge"
            data-status={status}
            className={`text-xs px-2 py-0.5 rounded font-medium ${
              isJobActive
                ? "bg-status-info/15 text-status-info"
                : isJobFailed
                  ? "bg-status-danger/15 text-status-danger"
                  : "bg-status-success/15 text-status-success"
            }`}
          >
            {badgeText}
          </span>

          {canExecute && (
            <button
              type="button"
              data-testid="relaunch-reindex-button"
              onClick={() => void handleRelaunch()}
              disabled={disableRelaunch}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded text-white ${
                disableRelaunch
                  ? "bg-surface-muted opacity-50 cursor-not-allowed"
                  : "bg-action-primary hover:opacity-90 cursor-pointer"
              }`}
            >
              {isRelaunching ? (
                <OrciaSpinner size="xs" />
              ) : (
                <OrciaIcon name="regenerate" size={14} />
              )}
              <span>{labels.relaunchBtn}</span>
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
          className="inline-flex items-center gap-1.5 text-xs text-status-danger bg-status-danger/10 px-3 py-2 rounded"
        >
          <OrciaIcon name="warning" size={14} />
          <span>{errorMessage}</span>
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
