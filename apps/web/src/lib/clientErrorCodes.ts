/**
 * Structured client-side error codes and localized message resolution.
 *
 * Used when network requests, streams, or local validations fail without a
 * localized server RFC 9457 Problem Details payload.
 */

export const CLIENT_ERROR_CODES = [
  "ERR_CLIENT_TIMEOUT",
  "ERR_CLIENT_NETWORK",
  "ERR_CLIENT_ABORTED",
  "ERR_CLIENT_SSE_DISCONNECTED",
  "ERR_CLIENT_INVALID_PAYLOAD",
  "ERR_CLIENT_UNKNOWN",
] as const;

export type ClientErrorCode = (typeof CLIENT_ERROR_CODES)[number];

export interface ClientErrorParams {
  readonly seconds?: number;
  readonly detail?: string;
}

export type ClientErrorLabels = Record<ClientErrorCode, string>;

export interface ClientErrorPayload {
  readonly code: ClientErrorCode;
  readonly params?: ClientErrorParams;
}

const CLIENT_ERROR_CODE_SET: ReadonlySet<string> = new Set<string>(CLIENT_ERROR_CODES);

/**
 * Return `true` when `value` is a recognized `ClientErrorCode`.
 */
export function isClientErrorCode(value: unknown): value is ClientErrorCode {
  return typeof value === "string" && CLIENT_ERROR_CODE_SET.has(value);
}

/**
 * Construct a typed `ClientErrorPayload` for bridges, stores, and controllers.
 */
export function createClientErrorPayload(
  code: ClientErrorCode,
  params?: ClientErrorParams,
): ClientErrorPayload {
  return params ? { code, params } : { code };
}

/**
 * Type guard checking whether an unknown error/object is a `ClientErrorPayload`.
 */
export function isClientErrorPayload(value: unknown): value is ClientErrorPayload {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  if (!isClientErrorCode(candidate.code)) {
    return false;
  }
  if (candidate.params !== undefined) {
    if (typeof candidate.params !== "object" || candidate.params === null) {
      return false;
    }
    const params = candidate.params as Record<string, unknown>;
    if (params.seconds !== undefined && typeof params.seconds !== "number") {
      return false;
    }
    if (params.detail !== undefined && typeof params.detail !== "string") {
      return false;
    }
  }
  return true;
}

/**
 * Resolve a `ClientErrorCode` against the active locale dictionary with safe
 * `{seconds}` / `{detail}` interpolation and unknown-code fallback.
 */
export function resolveClientErrorMessage(
  code: string | ClientErrorCode | null | undefined,
  labels: ClientErrorLabels,
  params?: ClientErrorParams,
): string {
  const safeCode: ClientErrorCode = isClientErrorCode(code) ? code : "ERR_CLIENT_UNKNOWN";
  let message = labels[safeCode] || labels.ERR_CLIENT_UNKNOWN || "";

  const hasValidSeconds =
    typeof params?.seconds === "number" && Number.isFinite(params.seconds) && params.seconds >= 0;
  if (hasValidSeconds) {
    message = message.replace(/\{seconds\}/g, String(params.seconds));
  } else {
    message = message
      .replace(/\s*\bde\s+\{seconds\}\s*s\b/gi, "")
      .replace(/\s*\{seconds\}\s*s\b/gi, "")
      .replace(/\{seconds\}/g, "");
  }

  const cleanDetail = typeof params?.detail === "string" ? params.detail.trim() : "";
  if (cleanDetail) {
    if (message.includes("{detail}")) {
      message = message.replace(/\{detail\}/g, cleanDetail);
    } else {
      message = `${message} (${cleanDetail})`;
    }
  } else {
    message = message.replace(/\s*\(\{detail\}\)/g, "").replace(/\{detail\}/g, "");
  }

  return message.replace(/\s{2,}/g, " ").trim();
}
