import type { ProblemDetails } from "./generated/schema";

export class OrciaProblemError extends Error {
  public readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail);
    this.name = "OrciaProblemError";
    this.problem = problem;
  }
}

export async function parseProblemError(
  response: Response,
  path: string,
  traceIdFallback?: string,
): Promise<OrciaProblemError> {
  const fallbackTraceId =
    response.headers?.get?.("x-trace-id") ??
    traceIdFallback ??
    "00000000000000000000000000000000";
  const problem = (await Promise.resolve()
    .then(() => response.json())
    .catch(
      (): ProblemDetails => ({
        type: "about:blank",
        title: response.statusText || "HTTP Error",
        status: response.status || 500,
        detail: response.statusText || "Unexpected non-JSON error response",
        instance: path,
        error_code: "ERR_INTERNAL_SERVER_ERROR",
        trace_id: fallbackTraceId,
      }),
    )) as ProblemDetails;
  return new OrciaProblemError(problem);
}

export function buildPersonaQuery(personaKey?: string): string {
  return personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
}

export interface ListOrgUnitsParams {
  readonly personaKey?: string;
  readonly q?: string;
  readonly kind?: "BU" | "TEAM";
  readonly limit?: number;
}

export function buildOrgUnitsQuery(params?: ListOrgUnitsParams | string): string {
  if (!params) return "";
  if (typeof params === "string") {
    return buildPersonaQuery(params);
  }
  const searchParams = new URLSearchParams();
  if (params.personaKey) searchParams.set("persona_key", params.personaKey);
  if (params.q) searchParams.set("q", params.q);
  if (params.kind) searchParams.set("kind", params.kind);
  if (params.limit !== undefined && params.limit !== null) {
    searchParams.set("limit", String(params.limit));
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

export interface ListKnownOrgUsersParams {
  readonly personaKey?: string;
  readonly q?: string;
  readonly limit?: number;
}

export function buildKnownOrgUsersQuery(params?: ListKnownOrgUsersParams | string): string {
  if (!params) return "";
  if (typeof params === "string") {
    return buildPersonaQuery(params);
  }
  const searchParams = new URLSearchParams();
  if (params.personaKey) searchParams.set("persona_key", params.personaKey);
  if (params.q) searchParams.set("q", params.q);
  if (params.limit !== undefined && params.limit !== null) {
    searchParams.set("limit", String(params.limit));
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

export type SseEventHandler = (
  eventName: string,
  data: Record<string, unknown>,
  eventId?: string,
) => void;

export interface SseRequestParams {
  readonly path: string;
  readonly method?: "GET" | "POST";
  readonly body?: unknown;
  readonly headers?: Record<string, string>;
  readonly signal?: AbortSignal;
  readonly accessToken?: string;
  readonly onOpen?: (response: Response) => void;
  readonly onEvent?: SseEventHandler;
}

export function dispatchSseBlock(block: string, onEvent?: SseEventHandler): void {
  let eventName = "message";
  let eventId: string | undefined;
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("id:")) {
      eventId = line.slice(3).trim();
    } else if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) return;
  try {
    const parsed = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
    onEvent?.(eventName, parsed, eventId);
  } catch {
    // Ignore non-JSON keepalive or comment payloads
  }
}
