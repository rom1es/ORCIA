import type { components } from "@orcia/api-client";
import type {
  UiAgentTraceEventItem,
  UiFileBadgeCode,
  UiReflexivePendingWritePreview,
  UiReflexiveSessionStatus,
  UiTraceEventKind,
} from "@orcia/ui";

type ApiTraceEventLike =
  | components["schemas"]["AgentTraceEventItem"]
  | components["schemas"]["AgentTraceEvent"];
type ApiPendingWritePreview = components["schemas"]["PendingWritePreviewItem"];
type ApiSnapshot = components["schemas"]["ReflexiveExecutionSnapshotResponse"];

const fallbackReflexiveStorage = new Map<string, string>();

export interface MappedReflexiveSnapshot {
  readonly executionId: string;
  readonly actorSlug: string;
  readonly objective: string;
  readonly status: UiReflexiveSessionStatus;
  readonly events: readonly UiAgentTraceEventItem[];
  readonly pendingWritePreview: UiReflexivePendingWritePreview | null;
  readonly finalMarkdown: string | null;
  readonly artifactUri: string | null;
  readonly artifactSha256: string | null;
}

export function mapApiStatusToUi(
  rawStatus: string | undefined,
  forceFinal?: boolean,
): UiReflexiveSessionStatus {
  if (rawStatus === "WAITING_WRITE_PREVIEW") return "WAITING_WRITE_PREVIEW";
  if (rawStatus === "COMPLETED") return "COMPLETED";
  if (rawStatus === "CANCELLED") return "CANCELLED";
  if (rawStatus === "FAILED") return "FAILED";
  if (rawStatus === "RUNNING" && forceFinal) return "SYNTHESIZING";
  return "RUNNING";
}

export function inferFileBadgeFromUri(uri: string): UiFileBadgeCode {
  const clean = uri.split("#")[0]?.toLowerCase() ?? "";
  if (clean.endsWith(".md") || clean.endsWith(".mdx")) return "M↓";
  if (clean.endsWith(".yaml") || clean.endsWith(".yml")) return "Y";
  if (clean.endsWith(".ts") || clean.endsWith(".tsx")) return "TS";
  if (clean.endsWith(".py")) return "PY";
  if (clean.endsWith(".json")) return "JSON";
  if (clean.endsWith(".sql")) return "SQL";
  return "DOC";
}

export function mapApiKindToUiKind(rawKind: string): UiTraceEventKind {
  const upper = rawKind.trim().toUpperCase();
  if (
    upper === "GROUP_HEADER" ||
    upper === "THOUGHT_DELTA" ||
    upper === "THOUGHT_COMPLETED" ||
    upper === "CHECK_EXECUTED" ||
    upper === "FILE_ANALYZED" ||
    upper === "AGENT_DELEGATED" ||
    upper === "WRITE_PREVIEW_REQUESTED" ||
    upper === "SYNTHESIS_READY" ||
    upper === "EXECUTION_FINISHED"
  ) {
    return upper;
  }
  if (upper === "STATUS_WORKING") return "CHECK_EXECUTED";
  if (upper === "ANSWER_TOKEN_DELTA") return "SYNTHESIS_READY";
  if (upper === "LOOP_COMPLETED" || upper === "LOOP_CANCELLED") {
    return "EXECUTION_FINISHED";
  }
  return "CHECK_EXECUTED";
}

export function mapApiTraceEventToUi(
  item: ApiTraceEventLike,
  fallbackActorSlug = "assistant",
): UiAgentTraceEventItem {
  const metaActor =
    item.metadata && typeof item.metadata.actor_slug === "string"
      ? item.metadata.actor_slug
      : null;
  const actorSlug = metaActor || fallbackActorSlug;
  const kind = mapApiKindToUiKind(String(item.kind || "check_executed"));
  const label =
    item.group_title ||
    item.check_label ||
    item.status_label ||
    item.display_filename ||
    item.delegate_agent_slug ||
    kind;
  const durationSeconds =
    typeof item.thought_duration_ms === "number"
      ? Math.max(1, Math.round(item.thought_duration_ms / 1000))
      : null;
  const groupKey =
    typeof item.turn_index === "number" ? `turn-${item.turn_index}` : null;

  return {
    eventId: item.event_id || `ev-${item.execution_id}-${item.sequence_index}`,
    sequence: item.sequence_index,
    kind,
    label,
    actorSlug,
    groupKey,
    durationSeconds,
    thoughtContent: item.delta_text ?? null,
    resourceUri: item.resource_uri ?? null,
    displayFilename: item.display_filename ?? null,
    fileBadgeCode:
      (item.file_badge_code as UiFileBadgeCode | null | undefined) ??
      (item.resource_uri ? inferFileBadgeFromUri(item.resource_uri) : null),
    startLine: item.start_line ?? null,
    endLine: item.end_line ?? null,
    redacted: Boolean(item.redacted),
    delegatedAgentSlug: item.delegate_agent_slug ?? null,
    writePreviewSummary:
      kind === "WRITE_PREVIEW_REQUESTED" ? (item.status_label ?? label) : null,
    ...(item.timestamp_utc ? { createdAtIso: item.timestamp_utc } : {}),
  };
}

export function mapApiPendingWritePreviewToUi(
  pending: ApiPendingWritePreview | null | undefined,
): UiReflexivePendingWritePreview | null {
  if (!pending) return null;
  return {
    previewId: pending.preview_id,
    targetConnector: `${pending.connector_type} · ${pending.target_resource_uri}`,
    actionSummary: pending.action_summary,
    ...(pending.payload ? { payloadPreview: pending.payload } : {}),
  };
}

export function mapApiSnapshotToUi(snap: ApiSnapshot): MappedReflexiveSnapshot {
  const actorSlug = snap.actor_slug || "assistant";
  const events = (snap.trace_events ?? []).map((ev) =>
    mapApiTraceEventToUi(ev, actorSlug),
  );
  return {
    executionId: snap.execution_id,
    actorSlug,
    objective: snap.objective,
    status: mapApiStatusToUi(snap.status, snap.force_final),
    events,
    pendingWritePreview: mapApiPendingWritePreviewToUi(
      snap.pending_write_preview,
    ),
    finalMarkdown: snap.final_markdown ?? null,
    artifactUri: snap.artifact_pointer?.s3_uri ?? null,
    artifactSha256: snap.artifact_pointer?.sha256 ?? null,
  };
}

export function parseUriWithLineRange(rawUri: string): {
  readonly uri: string;
  readonly startLine: number;
  readonly endLine: number;
} {
  const trimmed = rawUri.trim();
  const match = /^(.*?)#L(\d+)(?:-L?(\d+))?$/i.exec(trimmed);
  if (!match) {
    return { uri: trimmed, startLine: 1, endLine: 40 };
  }
  const baseUri = (match[1] ?? "").trim() || trimmed;
  const start = Math.max(1, Number.parseInt(match[2] ?? "1", 10) || 1);
  const end = Math.max(
    start,
    Number.parseInt(match[3] ?? String(start), 10) || start,
  );
  return { uri: baseUri, startLine: start, endLine: end };
}

export function readPersistedReflexiveId(storageKey: string): string | null {
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.getItem === "function"
  ) {
    try {
      const val = window.localStorage.getItem(storageKey);
      return val && val.trim().length > 0 ? val.trim() : null;
    } catch {
      return fallbackReflexiveStorage.get(storageKey) ?? null;
    }
  }
  return fallbackReflexiveStorage.get(storageKey) ?? null;
}

export function writePersistedReflexiveId(
  storageKey: string,
  executionId: string | null,
): void {
  if (!executionId) {
    fallbackReflexiveStorage.delete(storageKey);
    if (
      typeof window !== "undefined" &&
      window.localStorage &&
      typeof window.localStorage.removeItem === "function"
    ) {
      try {
        window.localStorage.removeItem(storageKey);
      } catch {
        // Ignore storage errors
      }
    }
    return;
  }
  fallbackReflexiveStorage.set(storageKey, executionId);
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.setItem === "function"
  ) {
    try {
      window.localStorage.setItem(storageKey, executionId);
    } catch {
      // Ignore storage quota errors
    }
  }
}
