import {
  createOrciaApiClient,
  type components,
} from "@orcia/api-client";
import type {
  UiAgentTraceEventItem,
  UiReflexivePendingWritePreview,
  UiReflexiveSessionStatus,
} from "@orcia/ui";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  mapApiSnapshotToUi,
  mapApiTraceEventToUi,
  readPersistedReflexiveId,
  writePersistedReflexiveId,
  type MappedReflexiveSnapshot,
} from "./reflexiveTraceMappers";

type StartReflexiveExecutionRequest =
  components["schemas"]["StartReflexiveExecutionRequest"];
type ApiTraceEventItem = components["schemas"]["AgentTraceEventItem"];

export interface UseReflexiveExecutionControllerOptions {
  readonly storageKey: string;
  readonly locale?: "fr" | "en";
  readonly initialExecutionId?: string | null;
  readonly onSnapshotUpdated?: (snapshot: MappedReflexiveSnapshot) => void;
  readonly onFeedback?: (message: string) => void;
}

function mergeEventBySequence(
  prev: readonly UiAgentTraceEventItem[],
  incoming: UiAgentTraceEventItem,
): readonly UiAgentTraceEventItem[] {
  const idx = prev.findIndex(
    (item) =>
      item.eventId === incoming.eventId || item.sequence === incoming.sequence,
  );
  if (idx === -1) {
    return [...prev, incoming].sort((a, b) => a.sequence - b.sequence);
  }
  const next = [...prev];
  next[idx] = incoming;
  return next.sort((a, b) => a.sequence - b.sequence);
}

export function useReflexiveExecutionController(
  options: UseReflexiveExecutionControllerOptions,
) {
  const {
    storageKey,
    locale = "fr",
    initialExecutionId = null,
    onSnapshotUpdated,
    onFeedback,
  } = options;

  const [executionId, setExecutionId] = useState<string | null>(
    () => initialExecutionId || readPersistedReflexiveId(storageKey),
  );
  const [status, setStatus] = useState<UiReflexiveSessionStatus | null>(null);
  const [events, setEvents] = useState<readonly UiAgentTraceEventItem[]>([]);
  const [pendingWritePreview, setPendingWritePreview] =
    useState<UiReflexivePendingWritePreview | null>(null);
  const [finalMarkdown, setFinalMarkdown] = useState<string | null>(null);
  const [artifactUri, setArtifactUri] = useState<string | null>(null);
  const [artifactSha256, setArtifactSha256] = useState<string | null>(null);
  const [actorSlug, setActorSlug] = useState<string>("assistant");
  const streamAbortRef = useRef<AbortController | null>(null);
  const snapshotCallbackRef = useRef(onSnapshotUpdated);
  snapshotCallbackRef.current = onSnapshotUpdated;
  const feedbackCallbackRef = useRef(onFeedback);
  feedbackCallbackRef.current = onFeedback;

  const applyMappedSnapshot = useCallback(
    (mapped: MappedReflexiveSnapshot) => {
      setExecutionId(mapped.executionId);
      writePersistedReflexiveId(storageKey, mapped.executionId);
      setActorSlug(mapped.actorSlug);
      setStatus(mapped.status);
      setEvents(mapped.events);
      setPendingWritePreview(mapped.pendingWritePreview);
      setFinalMarkdown(mapped.finalMarkdown);
      setArtifactUri(mapped.artifactUri);
      setArtifactSha256(mapped.artifactSha256);
      snapshotCallbackRef.current?.(mapped);
    },
    [storageKey],
  );

  const refreshSnapshot = useCallback(
    async (targetId: string): Promise<MappedReflexiveSnapshot | null> => {
      const client = createOrciaApiClient({ baseUrl: "", locale });
      try {
        const snap = await client.getReflexiveExecutionSnapshot(targetId);
        const mapped = mapApiSnapshotToUi(snap);
        applyMappedSnapshot(mapped);
        return mapped;
      } catch (err: unknown) {
        writePersistedReflexiveId(storageKey, null);
        setExecutionId(null);
        setStatus(null);
        const detail =
          err instanceof Error ? err.message : "Session introuvable";
        feedbackCallbackRef.current?.(detail);
        return null;
      }
    },
    [locale, storageKey, applyMappedSnapshot],
  );

  useEffect(() => {
    const savedId = initialExecutionId || readPersistedReflexiveId(storageKey);
    if (!savedId) return;
    void refreshSnapshot(savedId);
  }, [initialExecutionId, storageKey, refreshSnapshot]);

  useEffect(() => {
    if (!executionId || (status !== "RUNNING" && status !== "SYNTHESIZING")) {
      return;
    }
    const controller = new AbortController();
    streamAbortRef.current = controller;
    const client = createOrciaApiClient({ baseUrl: "", locale });
    const streamUrl = client.buildReflexiveTraceStreamUrl(executionId);

    void fetch(streamUrl, {
      method: "GET",
      headers: { Accept: "text/event-stream", "Accept-Language": locale },
      signal: controller.signal,
    })
      .then(async (resp) => {
        if (!resp.ok || !resp.body) return;
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() ?? "";
          for (const block of blocks) {
            const dataLine = block
              .split("\n")
              .find((ln) => ln.startsWith("data:"));
            if (!dataLine) continue;
            const rawJson = dataLine.slice(5).trim();
            if (!rawJson) continue;
            try {
              const parsed = JSON.parse(rawJson) as ApiTraceEventItem;
              const uiEv = mapApiTraceEventToUi(parsed, actorSlug);
              setEvents((prev) => mergeEventBySequence(prev, uiEv));
            } catch {
              // Ignore malformed SSE comment/heartbeat
            }
          }
        }
        if (!controller.signal.aborted) {
          await refreshSnapshot(executionId);
        }
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        const detail = err instanceof Error ? err.message : String(err);
        feedbackCallbackRef.current?.(detail);
      });

    return () => {
      controller.abort();
    };
  }, [executionId, status, locale, actorSlug, refreshSnapshot]);

  const startExecution = useCallback(
    async (
      payload: StartReflexiveExecutionRequest,
    ): Promise<MappedReflexiveSnapshot | null> => {
      streamAbortRef.current?.abort();
      const client = createOrciaApiClient({ baseUrl: "", locale });
      try {
        const snap = await client.startReflexiveExecution(payload);
        const mapped = mapApiSnapshotToUi(snap);
        applyMappedSnapshot(mapped);
        return mapped;
      } catch (err: unknown) {
        const detail = err instanceof Error ? err.message : String(err);
        feedbackCallbackRef.current?.(detail);
        return null;
      }
    },
    [locale, applyMappedSnapshot],
  );

  const synthesizeNow = useCallback(async () => {
    if (!executionId) return null;
    setStatus("SYNTHESIZING");
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const snap = await client.synthesizeReflexiveExecutionNow(executionId);
      const mapped = mapApiSnapshotToUi(snap);
      applyMappedSnapshot(mapped);
      return mapped;
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : String(err);
      feedbackCallbackRef.current?.(detail);
      return null;
    }
  }, [executionId, locale, applyMappedSnapshot]);

  const cancelExecution = useCallback(async () => {
    streamAbortRef.current?.abort();
    if (!executionId) return null;
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const snap = await client.cancelReflexiveExecution(executionId);
      const mapped = mapApiSnapshotToUi(snap);
      applyMappedSnapshot(mapped);
      return mapped;
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : String(err);
      feedbackCallbackRef.current?.(detail);
      return null;
    }
  }, [executionId, locale, applyMappedSnapshot]);

  const decideWritePreview = useCallback(
    async (previewId: string, approved: boolean) => {
      if (!executionId) return null;
      const client = createOrciaApiClient({ baseUrl: "", locale });
      try {
        const snap = await client.approveReflexiveWrite(executionId, {
          approved,
          preview_id: previewId,
          ...(approved ? {} : { rejection_reason: "Refusé par l'utilisateur" }),
        });
        const mapped = mapApiSnapshotToUi(snap);
        applyMappedSnapshot(mapped);
        return mapped;
      } catch (err: unknown) {
        const detail = err instanceof Error ? err.message : String(err);
        feedbackCallbackRef.current?.(detail);
        return null;
      }
    },
    [executionId, locale, applyMappedSnapshot],
  );

  const clearExecution = useCallback(() => {
    streamAbortRef.current?.abort();
    writePersistedReflexiveId(storageKey, null);
    setExecutionId(null);
    setStatus(null);
    setEvents([]);
    setPendingWritePreview(null);
    setFinalMarkdown(null);
    setArtifactUri(null);
    setArtifactSha256(null);
  }, [storageKey]);

  return {
    executionId,
    status,
    events,
    pendingWritePreview,
    finalMarkdown,
    artifactUri,
    artifactSha256,
    startExecution,
    refreshSnapshot,
    synthesizeNow,
    cancelExecution,
    approveWrite: (previewId: string) => decideWritePreview(previewId, true),
    rejectWrite: (previewId: string) => decideWritePreview(previewId, false),
    clearExecution,
  };
}
