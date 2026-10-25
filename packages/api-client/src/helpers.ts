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
    method: "GET" | "POST" = "GET",
    body?: unknown,
  ): Promise<T> {
    const headers: Record<string, string> = { ...baseHeaders };
    const init: RequestInit = { method, headers };
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
