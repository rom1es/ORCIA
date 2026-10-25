export type {
  components,
  HealthResponse,
  HumanProfileBadge,
  paths,
  ProblemDetails,
  ScopeNode,
  ShellModuleItem,
  ShellNavigationResponse,
} from "./generated/schema";

import type {
  HealthResponse,
  ProblemDetails,
  ShellNavigationResponse,
} from "./generated/schema";

export interface OrciaApiClientOptions {
  baseUrl: string;
  locale?: "fr" | "en";
  traceId?: string;
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

export function createOrciaApiClient(options: OrciaApiClientOptions) {
  const fetcher = options.fetchImpl ?? globalThis.fetch;
  const baseHeaders: Record<string, string> = {
    Accept: "application/json, application/problem+json",
    "Accept-Language": options.locale ?? "fr",
  };
  if (options.traceId) {
    baseHeaders["X-Trace-Id"] = options.traceId;
  }

  async function requestJson<T>(path: string): Promise<T> {
    const response = await fetcher(`${options.baseUrl}${path}`, {
      method: "GET",
      headers: baseHeaders,
    });
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
  }

  return {
    getHealth(): Promise<HealthResponse> {
      return requestJson<HealthResponse>("/api/v1/health");
    },
    getShellNavigation(scopeId?: string): Promise<ShellNavigationResponse> {
      const query = scopeId ? `?scope_id=${encodeURIComponent(scopeId)}` : "";
      return requestJson<ShellNavigationResponse>(`/api/v1/navigation/shell${query}`);
    },
  };
}
