/**
 * Structured client-side error codes and localized message resolution.
 *
 * Used when network requests, streams, or local validations fail without a
 * localized server error payload.
 */

export const CLIENT_ERROR_CODES = [
  "ERR_CLIENT_TIMEOUT",
  "ERR_CLIENT_NETWORK",
  "ERR_CLIENT_ABORTED",
  "ERR_CLIENT_SSE_DISCONNECTED",
  "ERR_CLIENT_SSE_EMPTY_BODY",
  "ERR_CLIENT_HTTP_FALLBACK",
  "ERR_CLIENT_INVALID_PAYLOAD",
  "ERR_CLIENT_NOT_CONFIGURED",
  "ERR_CLIENT_AUTH_HYDRATION_TIMEOUT",
  "ERR_CLIENT_SESSION_EXPIRED",
  "ERR_CLIENT_AI_UNAVAILABLE",
  "ERR_CLIENT_AI_HUB_COMMUNICATION",
  "ERR_CLIENT_AI_MODEL_ID_REQUIRED",
  "ERR_CLIENT_AI_ENDPOINT_URL_INVALID",
  "ERR_CLIENT_AI_API_KEY_REQUIRED",
  "ERR_CLIENT_AI_PROVIDER_UNREACHABLE",
  "ERR_CLIENT_IAM_NETWORK",
  "ERR_CLIENT_ORG_UNITS_NETWORK",
  "ERR_CLIENT_AUDIT_NETWORK",
  "ERR_CLIENT_CONNECTORS_LOAD",
  "ERR_CLIENT_CONNECTOR_SAVE",
  "ERR_CLIENT_CONNECTOR_DELETE",
  "ERR_CLIENT_FEDERATED_SEARCH",
  "ERR_CLIENT_PLATFORM_HYDRATION",
  "ERR_CLIENT_CONTEXT_MISSING",
  "ERR_CLIENT_PERMISSION_LOAD",
  "ERR_CLIENT_PERMISSION_ACTION",
  "ERR_CLIENT_PACKS_LOAD",
  "ERR_CLIENT_PACKS_HEALTH_REFRESH",
  "ERR_CLIENT_PACKS_EXPORT_ZIP",
  "ERR_CLIENT_PACKS_WORKSPACE_REQUIRED",
  "ERR_CLIENT_PACKS_HEALTH_DEGRADED",
  "ERR_CLIENT_PROCESS_RUN_START",
  "ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE",
  "ERR_CLIENT_PROCESS_SIMULATION_UNAVAILABLE",
  "ERR_CLIENT_HELP_ARTICLE_ATTACHED_LOCAL",
  "ERR_CLIENT_WIZARD_LOAD",
  "ERR_CLIENT_WIZARD_START",
  "ERR_CLIENT_WIZARD_STEP_SAVE",
  "ERR_CLIENT_WIZARD_STEP_BACK",
  "ERR_CLIENT_WIZARD_DEMO_PROVISION",
  "ERR_CLIENT_WORKSPACE_SOURCE_ACTION",
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

/**
 * Typed client-side error carrying a structured `ClientErrorCode` and optional
 * interpolation parameters for locale-aware resolution in the UI layer.
 */
export class ClientCodedError extends Error {
  public readonly code: ClientErrorCode;
  public readonly params?: ClientErrorParams;

  constructor(code: ClientErrorCode, params?: ClientErrorParams) {
    super(code);
    this.name = "ClientCodedError";
    this.code = code;
    this.params = params;
  }
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
