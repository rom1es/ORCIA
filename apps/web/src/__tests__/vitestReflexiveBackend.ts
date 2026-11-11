import type { components } from "@orcia/api-client";

type SnapshotResponse =
  components["schemas"]["ReflexiveExecutionSnapshotResponse"];
type InspectLinesResponse =
  components["schemas"]["SurgicalInspectLinesResponse"];
type TraceEventItem = components["schemas"]["AgentTraceEventItem"];

const reflexiveSessions = new Map<string, SnapshotResponse>();
let reflexiveSeqCounter = 1;
let forceNextSourceRedacted = false;

export function setVitestForceNextSourceRedacted(redacted: boolean): void {
  forceNextSourceRedacted = redacted;
}

export function resetVitestReflexiveBackend(): void {
  reflexiveSessions.clear();
  reflexiveSeqCounter = 1;
  forceNextSourceRedacted = false;
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.length === "number"
  ) {
    const keysToRemove: string[] = [];
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const k = window.localStorage.key(i);
      if (
        k &&
        (k.startsWith("orcia.reflexive_exec.") ||
          k === "orcia.processes.active_run_workflow_id.v1")
      ) {
        keysToRemove.push(k);
      }
    }
    for (const k of keysToRemove) {
      window.localStorage.removeItem(k);
    }
  }
}

function buildDefaultTraceEvents(
  executionId: string,
  actorSlug: string,
  objective: string,
  hasWritePreview: boolean,
): TraceEventItem[] {
  const now = "2026-11-11T10:00:00Z";
  const ev = (
    seq: number,
    kind: TraceEventItem["kind"],
    extra: Partial<TraceEventItem>,
    actor = actorSlug,
  ): TraceEventItem => ({
    event_id: `${executionId}-ev-${seq}`,
    execution_id: executionId,
    sequence_index: seq,
    turn_index: seq >= 6 ? 2 : 1,
    kind,
    timestamp_utc: now,
    metadata: { actor_slug: actor },
    ...extra,
  });
  const events: TraceEventItem[] = [
    ev(1, "group_header", { group_title: "Exploration documentaire & cadrage" }),
    ev(2, "thought_completed", {
      delta_text: `Analyse structurée de l'objectif :\n- Sujet : ${objective}\n- Vérification des sources métier autorisées.`,
      thought_duration_ms: 4000,
    }),
    ev(3, "file_analyzed", {
      resource_uri: "docs/product/capabilities.yaml",
      display_filename: "capabilities.yaml",
      file_badge_code: "Y",
      formatted_badge: "Y capabilities.yaml#L1-18",
      start_line: 1,
      end_line: 18,
      redacted: false,
    }),
    ev(4, "agent_delegated", {
      delegate_agent_slug: "analyste-metier",
      status_label: "Vérification croisée par @analyste-metier",
    }),
    ev(
      5,
      "file_analyzed",
      {
        resource_uri: "packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml",
        display_filename: "wf-generate-orcia-documentation.yaml",
        file_badge_code: "Y",
        formatted_badge: "Y wf-generate-orcia-documentation.yaml#L1-16",
        start_line: 1,
        end_line: 16,
        redacted: false,
      },
      "analyste-metier",
    ),
  ];
  if (hasWritePreview) {
    events.push(
      ev(6, "write_preview_requested", {
        status_label: "Publication externe en attente de votre accord",
        write_preview_id: `wp-${executionId}`,
      }),
    );
  }
  return events;
}

function buildAutoWorkflowSnapshot(executionId: string): SnapshotResponse {
  const actorSlug = "redacteur-documentation-orcia";
  const objective = "Synthèse documentaire ORCIA vérifiée";
  const snap: SnapshotResponse = {
    execution_id: executionId,
    workspace_id: null,
    actor_slug: actorSlug,
    objective,
    orchestration_type: "non_deterministic",
    effort_level: "high",
    effort_mode: "approfondi",
    status: "COMPLETED",
    force_final: false,
    allow_sub_agent_delegation: true,
    delegation_depth: 0,
    available_delegate_agents: ["analyste-metier"],
    turns_used: 2,
    max_turns: 25,
    tokens_used: 1240,
    max_budget_tokens: 48000,
    scratchpad: [
      {
        turn_index: 1,
        action_kind: "inspect_lines",
        resource_uri: "docs/product/capabilities.yaml",
        line_anchor: "docs/product/capabilities.yaml#L1-18",
        summary: "CAP-160 référencé dans capabilities.yaml.",
      },
    ],
    trace_events: buildDefaultTraceEvents(executionId, actorSlug, objective, false),
    pending_write_preview: null,
    final_markdown: `# Synthèse vérifiée\n\nRéférences contrôlées :\n- \`docs/product/capabilities.yaml#L1-18\`\n- \`packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml#L1-16\``,
    artifact_pointer: null,
    created_at_utc: "2026-11-11T10:00:00Z",
    updated_at_utc: "2026-11-11T10:00:05Z",
    expires_at_utc: "2026-11-12T10:00:00Z",
    trace_id: "0195f000000070008000000000000164",
  };
  reflexiveSessions.set(executionId, snap);
  return snap;
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function tryHandleVitestReflexiveEndpoint(params: {
  readonly path: string;
  readonly parsedUrl: URL;
  readonly method: string;
  readonly body: Record<string, unknown>;
  readonly init?: RequestInit;
}): Promise<Response> | Response | null {
  const { path, parsedUrl, method, body, init } = params;

  if (path === "/api/v1/sources/inspect-lines" && method === "GET") {
    const uri = parsedUrl.searchParams.get("uri") ?? "docs/README.md";
    const startLine = Math.max(1, Number.parseInt(parsedUrl.searchParams.get("start_line") ?? "1", 10) || 1);
    const endLine = Math.max(startLine, Number.parseInt(parsedUrl.searchParams.get("end_line") ?? "18", 10) || 18);
    const headersObj = new Headers(init?.headers);
    const isRedacted =
      forceNextSourceRedacted ||
      headersObj.get("x-orcia-read-source") === "denied" ||
      uri.includes("restricted") ||
      uri.includes("confidentiel");
    forceNextSourceRedacted = false;

    const displayFilename = uri.split("/").pop() ?? uri;
    const badge = uri.endsWith(".yaml") ? "Y" : uri.endsWith(".md") ? "M↓" : uri.endsWith(".ts") || uri.endsWith(".tsx") ? "TS" : "DOC";

    const payload: InspectLinesResponse = isRedacted
      ? {
          resource_uri: uri,
          display_filename: displayFilename,
          file_badge_code: badge,
          formatted_badge: `${badge} ${displayFilename}`,
          exists: true,
          start_line: startLine,
          end_line: endLine,
          total_lines: 120,
          lines: [],
          redacted: true,
          redacted_reason: "Accès restreint au contenu source.",
          permission_request_hint: "Demandez l'autorisation de lecture à un responsable de l'Espace.",
          trace_id: "0195f000000070008000000000000164",
        }
      : {
          resource_uri: uri,
          display_filename: displayFilename,
          file_badge_code: badge,
          formatted_badge: `${badge} ${displayFilename}#L${startLine}-${endLine}`,
          exists: true,
          start_line: startLine,
          end_line: endLine,
          total_lines: Math.max(endLine + 20, 60),
          lines: Array.from({ length: endLine - startLine + 1 }, (_, idx) => ({
            line_number: startLine + idx,
            content: `ligne_${startLine + idx}: Extrait vérifié de ${displayFilename}`,
          })),
          redacted: false,
          redacted_reason: null,
          permission_request_hint: null,
          trace_id: "0195f000000070008000000000000164",
        };
    return jsonResponse(payload);
  }

  if (path === "/api/v1/executions/reflexive" && method === "POST") {
    const execId = `exec-vitest-${reflexiveSeqCounter++}`;
    const actorSlug = String(body.actor_slug ?? "assistant");
    const objective = String(body.objective ?? "Analyse");
    const runInBg = Boolean(body.run_in_background);
    const reqWrite = body.requested_write_preview as Record<string, unknown> | undefined;
    const hasWrite = Boolean(reqWrite);
    const status: SnapshotResponse["status"] = hasWrite
      ? "WAITING_WRITE_PREVIEW"
      : runInBg
        ? "RUNNING"
        : "COMPLETED";
    const writePayload = (reqWrite?.payload as Record<string, unknown>) ?? {};
    const snap: SnapshotResponse = {
      execution_id: execId,
      workspace_id: body.workspace_id ? String(body.workspace_id) : null,
      actor_slug: actorSlug,
      objective,
      orchestration_type: "non_deterministic",
      effort_level: (body.effort_level as SnapshotResponse["effort_level"]) ?? "high",
      effort_mode: (body.effort_mode as SnapshotResponse["effort_mode"]) ?? "approfondi",
      status,
      force_final: false,
      allow_sub_agent_delegation: Boolean(body.allow_sub_agent_delegation ?? true),
      delegation_depth: 0,
      available_delegate_agents: ["analyste-metier"],
      turns_used: 2,
      max_turns: 25,
      tokens_used: 980,
      max_budget_tokens: 48000,
      scratchpad: [],
      trace_events: buildDefaultTraceEvents(execId, actorSlug, objective, hasWrite),
      pending_write_preview: hasWrite
        ? {
            preview_id: `wp-${execId}`,
            connector_type: String(reqWrite?.connector_type ?? "confluence"),
            action: String(reqWrite?.action ?? "publish_page"),
            target_resource_uri: String(reqWrite?.target_resource_uri ?? "confluence://Architecture/Documentation-ORCIA"),
            action_summary: String(reqWrite?.action_summary ?? "Publier la synthèse validée"),
            diff_or_payload_preview: writePayload,
            payload: writePayload,
            payload_sha256: "b".repeat(64),
            created_at_utc: "2026-11-11T10:00:00Z",
          }
        : null,
      ...(status === "COMPLETED"
        ? { final_markdown: `# Résultat vérifié\n\nSynthèse produite pour : ${objective}` }
        : {}),
      artifact_pointer: null,
      created_at_utc: "2026-11-11T10:00:00Z",
      updated_at_utc: "2026-11-11T10:00:05Z",
      expires_at_utc: "2026-11-12T10:00:00Z",
      trace_id: "0195f000000070008000000000000164",
    };
    reflexiveSessions.set(execId, snap);
    return jsonResponse(snap);
  }

  const streamMatch = /^\/api\/v1\/executions\/([^/]+)\/trace-stream$/.exec(path);
  if (streamMatch && method === "GET") {
    const execId = decodeURIComponent(streamMatch[1] ?? "");
    const snap = reflexiveSessions.get(execId) ?? buildAutoWorkflowSnapshot(execId);
    if (snap.status === "RUNNING") {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    }
    const encoder = new TextEncoder();
    const sseBody = (snap.trace_events ?? [])
      .map((ev) => `event: ${ev.kind}\ndata: ${JSON.stringify(ev)}\n\n`)
      .join("");
    return new Response(encoder.encode(sseBody), {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });
  }

  const actionMatch = /^\/api\/v1\/executions\/([^/]+)\/(synthesize-now|cancel|approve-write)$/.exec(path);
  if (actionMatch && method === "POST") {
    const execId = decodeURIComponent(actionMatch[1] ?? "");
    const action = actionMatch[2];
    const current = reflexiveSessions.get(execId) ?? buildAutoWorkflowSnapshot(execId);
    let updated: SnapshotResponse = current;
    if (action === "synthesize-now") {
      updated = {
        ...current,
        force_final: true,
        status: "COMPLETED",
        final_markdown:
          current.final_markdown ??
          `# Synthèse immédiate\n\nSynthèse produite à partir des constats déjà vérifiés.`,
      };
    } else if (action === "cancel") {
      updated = { ...current, status: "CANCELLED", pending_write_preview: null };
    } else if (action === "approve-write") {
      const approved = Boolean(body.approved);
      updated = {
        ...current,
        status: "COMPLETED",
        pending_write_preview: null,
        final_markdown: approved
          ? `# Publication externe exécutée\n\nAction confirmée et publiée avec succès.`
          : `# Publication externe refusée\n\nAucune écriture externe n'a été effectuée.`,
      };
    }
    reflexiveSessions.set(execId, updated);
    return jsonResponse(updated);
  }

  const getMatch = /^\/api\/v1\/executions\/([^/]+)$/.exec(path);
  if (getMatch && method === "GET") {
    const execId = decodeURIComponent(getMatch[1] ?? "");
    const existing =
      reflexiveSessions.get(execId) ??
      (execId.startsWith("reflx-") ? buildAutoWorkflowSnapshot(execId) : null);
    return existing
      ? jsonResponse(existing)
      : jsonResponse({ detail: `Execution '${execId}' introuvable.` }, 404);
  }

  return null;
}
