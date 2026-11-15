import { createOrciaApiClient } from "@orcia/api-client";
import { useCallback, useEffect, useState } from "react";

export interface RagReindexState {
  readonly status: "IDLE" | "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "CANCELLED";
  readonly progressPercentage: number;
  readonly errorMessage: string | null;
  readonly isReindexing: boolean;
  readonly isReindexFailed: boolean;
  readonly relaunchReindex: () => Promise<void>;
  readonly refreshStatus: () => Promise<void>;
}

export function useRagReindexStatus(): RagReindexState {
  const [status, setStatus] = useState<
    "IDLE" | "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "CANCELLED"
  >("IDLE");
  const [progressPercentage, setProgressPercentage] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const client = createOrciaApiClient({ baseUrl: "" });
      const res = await client.aiModelsHub.getReindexStatus();
      setStatus(res.status ?? "IDLE");
      setProgressPercentage(res.progress_percentage ?? 0);
      setErrorMessage(res.error_message ?? null);
    } catch (err: unknown) {
      console.warn("[ORCIA-UI] Failed to fetch RAG reindex status:", err);
    }
  }, []);

  const relaunchReindex = useCallback(async () => {
    try {
      const client = createOrciaApiClient({ baseUrl: "" });
      await client.aiModelsHub.reindexEmbeddings();
      await fetchStatus();
    } catch (err: unknown) {
      console.error("[ORCIA-UI] Failed to relaunch reindexing:", err);
    }
  }, [fetchStatus]);

  useEffect(() => {
    let isMounted = true;
    void fetchStatus();

    const intervalId = window.setInterval(() => {
      if (isMounted) {
        void fetchStatus();
      }
    }, 2000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [fetchStatus]);

  const isReindexing = status === "PENDING" || status === "IN_PROGRESS";
  const isReindexFailed = status === "FAILED";

  return {
    status,
    progressPercentage,
    errorMessage,
    isReindexing,
    isReindexFailed,
    relaunchReindex,
    refreshStatus: fetchStatus,
  };
}
