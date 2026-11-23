import {
  buildKnownOrgUsersQuery,
  buildOrgUnitsQuery,
  buildPersonaQuery,
  dispatchSseBlock,
  OrciaClientError,
  OrciaProblemError,
  parseProblemError,
  type ListKnownOrgUsersParams,
  type ListOrgUnitsParams,
  type OrciaClientErrorParams,
  type SseEventHandler,
  type SseRequestParams,
} from "./sseAndQueryHelpers";

export {
  buildKnownOrgUsersQuery,
  buildOrgUnitsQuery,
  buildPersonaQuery,
  OrciaClientError,
  OrciaProblemError,
  type ListKnownOrgUsersParams,
  type ListOrgUnitsParams,
  type OrciaClientErrorParams,
  type SseEventHandler,
  type SseRequestParams,
};

export interface OrciaApiClientOptions {
  baseUrl: string;
  locale?: "fr" | "en";
  traceId?: string;
  accessToken?: string;
  getAccessToken?: () => string | null | undefined;
  extraHeaders?: Record<string, string> | (() => Record<string, string>);
  fetchImpl?: typeof fetch;
}

export type OrciaApiClientConfig = OrciaApiClientOptions;

let defaultAccessTokenProvider: (() => string | null | undefined) | null = null;
let defaultAccessTokenRefreshedHandler: ((token: string) => void) | null = null;
let inFlightRefreshPromise: Promise<string | null> | null = null;

export function registerDefaultAccessTokenProvider(
  provider: (() => string | null | undefined) | null,
): void {
  defaultAccessTokenProvider = provider;
  if (provider === null) {
    inFlightRefreshPromise = null;
  }
}

export function registerDefaultAccessTokenRefreshedHandler(
  handler: ((token: string) => void) | null,
): void {
  defaultAccessTokenRefreshedHandler = handler;
}

function resolveAccessToken(
  options: OrciaApiClientOptions,
  overrideToken?: string,
): string | undefined {
  if (overrideToken !== undefined) {
    return overrideToken || undefined;
  }
  if (options.accessToken !== undefined) {
    return options.accessToken || undefined;
  }
  return options.getAccessToken?.() ?? defaultAccessTokenProvider?.() ?? undefined;
}

function buildBaseHeaders(
  options: OrciaApiClientOptions,
  accept: string,
  extraHeaders?: Record<string, string>,
  overrideToken?: string,
): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: accept,
    "Accept-Language": options.locale ?? "fr",
  };
  if (options.traceId) {
    headers["X-Trace-Id"] = options.traceId;
  }
  const configuredExtra =
    typeof options.extraHeaders === "function" ? options.extraHeaders() : options.extraHeaders;
  if (configuredExtra) {
    Object.assign(headers, configuredExtra);
  }
  if (extraHeaders) {
    Object.assign(headers, extraHeaders);
  }
  const resolvedAccessToken = resolveAccessToken(options, overrideToken);
  if (resolvedAccessToken && !headers.Authorization && !headers.authorization) {
    headers.Authorization = `Bearer ${resolvedAccessToken}`;
  }
  return headers;
}

function shouldAttemptSingleFlightRefresh(
  status: number,
  path: string,
  options: OrciaApiClientOptions,
  headers: Record<string, string>,
  overrideToken?: string,
): boolean {
  return (
    status === 401 &&
    overrideToken === undefined &&
    options.accessToken === undefined &&
    !path.startsWith("/api/v1/auth/") &&
    Boolean(headers.Authorization || headers.authorization)
  );
}

async function refreshAccessTokenSingleFlight(
  options: OrciaApiClientOptions,
  fetcher: typeof fetch,
): Promise<string | null> {
  if (!inFlightRefreshPromise) {
    const refreshHeaders = buildBaseHeaders(
      { ...options, accessToken: "" },
      "application/json, application/problem+json",
    );
    inFlightRefreshPromise = (async () => {
      try {
        const refreshResp = await fetcher(`${options.baseUrl}/api/v1/auth/refresh`, {
          method: "POST",
          headers: refreshHeaders,
          credentials: "include",
        });
        if (!refreshResp.ok) {
          return null;
        }
        const refreshed = (await refreshResp.json()) as { access_token?: unknown };
        if (typeof refreshed.access_token === "string" && refreshed.access_token) {
          defaultAccessTokenRefreshedHandler?.(refreshed.access_token);
          return refreshed.access_token;
        }
        return null;
      } catch {
        return null;
      } finally {
        inFlightRefreshPromise = null;
      }
    })();
  }
  return inFlightRefreshPromise;
}

export function createRequestJson(options: OrciaApiClientOptions) {
  const fetcher = options.fetchImpl ?? globalThis.fetch;

  return async function requestJson<T>(
    path: string,
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" = "GET",
    body?: unknown,
    extraHeaders?: Record<string, string>,
    signal?: AbortSignal,
  ): Promise<T> {
    const headers = buildBaseHeaders(
      options,
      "application/json, application/problem+json",
      extraHeaders,
    );
    const init: RequestInit = {
      method,
      headers,
      credentials: "include",
      ...(signal ? { signal } : {}),
    };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    let response = await fetcher(`${options.baseUrl}${path}`, init);
    if (shouldAttemptSingleFlightRefresh(response.status, path, options, headers)) {
      const refreshedToken = await refreshAccessTokenSingleFlight(options, fetcher);
      if (refreshedToken) {
        response = await fetcher(`${options.baseUrl}${path}`, {
          ...init,
          headers: {
            ...headers,
            Authorization: `Bearer ${refreshedToken}`,
          },
        });
      }
    }
    if (!response.ok) {
      throw await parseProblemError(response, path, options.traceId);
    }
    return (await response.json()) as T;
  };
}

export interface BinaryDownloadResult {
  readonly blob: Blob;
  readonly filename: string | null;
}

export function createRequestBinary(options: OrciaApiClientOptions) {
  const fetcher = options.fetchImpl ?? globalThis.fetch;

  return async function requestBinary(
    path: string,
    method: "GET" | "POST" = "POST",
    extraHeaders?: Record<string, string>,
  ): Promise<BinaryDownloadResult> {
    const headers = buildBaseHeaders(
      options,
      "application/zip, application/octet-stream, application/problem+json",
      extraHeaders,
    );
    const response = await fetcher(`${options.baseUrl}${path}`, {
      method,
      headers,
      credentials: "include",
    });
    if (!response.ok) {
      throw await parseProblemError(response, path, options.traceId);
    }
    const disposition = response.headers?.get?.("content-disposition") ?? "";
    const match = /filename="?([^";]+)"?/i.exec(disposition);
    const blob = await response.blob();
    return {
      blob,
      filename: match?.[1] ?? null,
    };
  };
}

export function createRequestSse(options: OrciaApiClientOptions) {
  const fetcher = options.fetchImpl ?? globalThis.fetch;

  return async function requestSse(params: SseRequestParams): Promise<void> {
    const method = params.method ?? "GET";
    const headers = buildBaseHeaders(
      options,
      "text/event-stream",
      params.headers,
      params.accessToken,
    );
    const init: RequestInit = {
      method,
      headers,
      credentials: "include",
      ...(params.signal ? { signal: params.signal } : {}),
    };
    if (params.body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(params.body);
    }

    let response = await fetcher(`${options.baseUrl}${params.path}`, init);
    if (
      shouldAttemptSingleFlightRefresh(
        response.status,
        params.path,
        options,
        headers,
        params.accessToken,
      )
    ) {
      const refreshedToken = await refreshAccessTokenSingleFlight(options, fetcher);
      if (params.signal?.aborted) {
        throw new DOMException("Aborted", "AbortError");
      }
      if (refreshedToken) {
        response = await fetcher(`${options.baseUrl}${params.path}`, {
          ...init,
          headers: {
            ...headers,
            Authorization: `Bearer ${refreshedToken}`,
          },
        });
      }
    }

    if (!response.ok) {
      throw await parseProblemError(response, params.path, options.traceId);
    }
    params.onOpen?.(response);
    if (!response.body) {
      throw new OrciaClientError("ERR_CLIENT_SSE_EMPTY_BODY", { detail: params.path });
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) dispatchSseBlock(block, params.onEvent);
    }
    if (buffer.trim().length > 0) dispatchSseBlock(buffer, params.onEvent);
  };
}
