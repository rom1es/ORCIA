import type { ProblemDetails } from "./generated/schema";

export interface OrciaApiClientOptions {
  baseUrl: string;
  locale?: "fr" | "en";
  traceId?: string;
  accessToken?: string;
  fetchImpl?: typeof fetch;
}

export class OrciaProblemError extends Error {
  public readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail);
    this.name = "OrciaProblemError";
    this.problem = problem;
  }
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

export function createRequestJson(options: OrciaApiClientOptions) {
  const fetcher = options.fetchImpl ?? globalThis.fetch;
  const baseHeaders: Record<string, string> = {
    Accept: "application/json, application/problem+json",
    "Accept-Language": options.locale ?? "fr",
  };
  if (options.traceId) {
    baseHeaders["X-Trace-Id"] = options.traceId;
  }
  if (options.accessToken) {
    baseHeaders.Authorization = `Bearer ${options.accessToken}`;
  }

  return async function requestJson<T>(
    path: string,
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" = "GET",
    body?: unknown,
  ): Promise<T> {
    const headers: Record<string, string> = { ...baseHeaders };
    const init: RequestInit = { method, headers, credentials: "include" };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    const response = await fetcher(`${options.baseUrl}${path}`, init);
    if (!response.ok) {
      const fallbackTraceId =
        response.headers?.get?.("x-trace-id") ??
        options.traceId ??
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
      throw new OrciaProblemError(problem);
    }
    return (await response.json()) as T;
  };
}
