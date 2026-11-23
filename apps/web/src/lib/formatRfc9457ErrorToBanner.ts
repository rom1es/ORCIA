import { OrciaClientError, OrciaProblemError, type ProblemDetails } from "@orcia/api-client";
import { CLIENT_ERRORS_BY_LOCALE } from "../i18n/locales/client_errors_labels";
import {
  RFC9457_BANNER_BY_LOCALE,
  type BannerErrorCopy,
  type Rfc9457BannerDictionary,
} from "../i18n/locales/rfc9457_banner_labels";
import {
  ClientCodedError,
  isClientErrorCode,
  isClientErrorPayload,
  resolveClientErrorMessage,
  type ClientErrorCode,
  type ClientErrorParams,
} from "./clientErrorCodes";
import type { SupportedUiLocale } from "./formatters";

export interface FormattedRfc9457Banner {
  readonly title: string;
  readonly message: string;
  readonly remediation: string;
  readonly fullText: string;
  readonly status?: number;
  readonly errorCode?: string;
}

/**
 * Resolve a structured `ClientErrorCode` into a localized user-facing message
 * without inline locale branches.
 */
export function resolveLocalizedClientError(
  code: ClientErrorCode,
  locale: SupportedUiLocale = "fr",
  params?: ClientErrorParams,
): string {
  return resolveClientErrorMessage(code, CLIENT_ERRORS_BY_LOCALE[locale], params);
}

function resolveStatusFallback(
  status: number | undefined,
  dict: Rfc9457BannerDictionary,
  resourceLabel?: string,
): BannerErrorCopy {
  const quotedTarget = resourceLabel
    ? dict.quotedTargetPattern.replace("{resource}", resourceLabel)
    : "";
  const prepTarget = resourceLabel
    ? dict.prepositionTargetPattern.replace("{resource}", resourceLabel)
    : dict.fallbackOperationTarget;

  const entry =
    status === 401
      ? dict.statusFallbacks[401]
      : status === 403
        ? dict.statusFallbacks[403]
        : status === 404
          ? dict.statusFallbacks[404]
          : status === 409
            ? dict.statusFallbacks[409]
            : status === 422
              ? dict.statusFallbacks[422]
              : status === 503
                ? dict.statusFallbacks[503]
                : dict.statusFallbacks.default;

  const target =
    status === 422 || status === 503 ? prepTarget : quotedTarget;
  return {
    title: entry.title,
    message: entry.message.replace("{target}", target),
    remediation: entry.remediation,
  };
}

function sanitizeDetailText(
  raw: string | undefined,
  dict: Rfc9457BannerDictionary,
): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const { sanitizeReplacements } = dict;
  return trimmed
    .replace(/\bREAD_ONLY_OBSERVER\b/g, sanitizeReplacements.readOnlyObserver)
    .replace(/\bhuman_authored_required\b/g, sanitizeReplacements.humanAuthoredRequired)
    .replace(/\bAUTONOMOUS_CONTRACT\b/g, sanitizeReplacements.autonomousContract)
    .replace(/\bHIGH_CRITICAL\b/g, sanitizeReplacements.highCritical)
    .replace(/\bERR_[A-Z0-9_]+\b/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function resolveErrorPayloadDetails(
  error: unknown,
): { readonly code: ClientErrorCode; readonly params?: ClientErrorParams } | null {
  if (error instanceof ClientCodedError || error instanceof OrciaClientError) {
    if (isClientErrorCode(error.code)) {
      return { code: error.code, params: error.params };
    }
    return { code: "ERR_CLIENT_UNKNOWN", params: error.params };
  }
  if (isClientErrorPayload(error)) {
    return { code: error.code, params: error.params };
  }
  if (error instanceof Error && isClientErrorCode(error.message.trim())) {
    return { code: error.message.trim() as ClientErrorCode };
  }
  if (typeof error === "string" && isClientErrorCode(error.trim())) {
    return { code: error.trim() as ClientErrorCode };
  }
  return null;
}

function isProblemLike(error: unknown): error is Partial<ProblemDetails> {
  return (
    typeof error === "object" &&
    error !== null &&
    !(error instanceof OrciaClientError) &&
    !(error instanceof ClientCodedError) &&
    ("error_code" in error || "status" in error || "detail" in error)
  );
}

/**
 * Format an API problem, typed client error, or unknown exception into a
 * localized banner structure in French or English.
 */
export function formatRfc9457ErrorToBanner(
  error: unknown,
  locale: SupportedUiLocale = "fr",
  resourceLabel?: string,
): FormattedRfc9457Banner {
  const dict = RFC9457_BANNER_BY_LOCALE[locale];
  const clientDict = CLIENT_ERRORS_BY_LOCALE[locale];

  const problem =
    error instanceof OrciaProblemError
      ? error.problem
      : isProblemLike(error)
        ? error
        : null;

  if (problem) {
    const code = problem.error_code;
    const status = typeof problem.status === "number" ? problem.status : undefined;
    const catalogEntry = code ? dict.catalog[code] : undefined;
    const resourceSuffix = resourceLabel
      ? dict.resourceSuffixPattern.replace("{resource}", resourceLabel)
      : "";
    const hint = sanitizeDetailText(problem.permission_broker_hint ?? undefined, dict);

    if (catalogEntry) {
      const remediation = hint || catalogEntry.remediation;
      const message = `${catalogEntry.message}${resourceSuffix}`;
      return {
        title: catalogEntry.title,
        message,
        remediation,
        fullText: `${catalogEntry.title} — ${message} ${remediation}`,
        status,
        errorCode: code,
      };
    }

    const fallback = resolveStatusFallback(status, dict, resourceLabel);
    const rawDetail = typeof problem.detail === "string" ? problem.detail.trim() : "";
    const clientCodeMessage = isClientErrorCode(rawDetail)
      ? resolveClientErrorMessage(rawDetail, clientDict)
      : null;
    const sanitizedDetail = clientCodeMessage ? null : sanitizeDetailText(rawDetail, dict);
    const message =
      clientCodeMessage ??
      (sanitizedDetail && sanitizedDetail.length > 8 ? sanitizedDetail : fallback.message);
    const remediation = hint || fallback.remediation;
    return {
      title: fallback.title,
      message,
      remediation,
      fullText: `${fallback.title} — ${message} ${remediation}`,
      status,
      errorCode: code,
    };
  }

  const clientError = resolveErrorPayloadDetails(error);
  const fallback = resolveStatusFallback(undefined, dict, resourceLabel);
  if (clientError) {
    const message = resolveClientErrorMessage(clientError.code, clientDict, clientError.params);
    return {
      title: fallback.title,
      message,
      remediation: fallback.remediation,
      fullText: `${fallback.title} — ${message} ${fallback.remediation}`,
      errorCode: clientError.code,
    };
  }

  const rawMsg =
    error instanceof Error
      ? sanitizeDetailText(error.message, dict)
      : typeof error === "string"
        ? sanitizeDetailText(error, dict)
        : null;
  const message = rawMsg || fallback.message;
  return {
    title: fallback.title,
    message,
    remediation: fallback.remediation,
    fullText: `${fallback.title} — ${message} ${fallback.remediation}`,
  };
}

/**
 * Extract a concise localized error message and optional `errorCode` for API
 * bridges and controllers without inline locale conditionals.
 */
export function extractLocalizedApiError(
  err: unknown,
  locale: SupportedUiLocale,
  fallbackCode: ClientErrorCode = "ERR_CLIENT_UNKNOWN",
  fallbackParams?: ClientErrorParams,
): { readonly errorMessage: string; readonly errorCode?: string } {
  if (err instanceof OrciaProblemError) {
    const rawDetail = (err.problem.detail || "").trim();
    if (isClientErrorCode(rawDetail)) {
      return {
        errorMessage: resolveLocalizedClientError(rawDetail, locale),
        errorCode: err.problem.error_code,
      };
    }
    return {
      errorMessage:
        rawDetail ||
        (isClientErrorCode(err.problem.title)
          ? resolveLocalizedClientError(err.problem.title, locale)
          : err.problem.title) ||
        resolveLocalizedClientError(fallbackCode, locale, fallbackParams),
      errorCode: err.problem.error_code,
    };
  }
  const clientErr = resolveErrorPayloadDetails(err);
  if (clientErr) {
    return {
      errorMessage: resolveLocalizedClientError(clientErr.code, locale, clientErr.params),
      errorCode: clientErr.code,
    };
  }
  if (
    (err instanceof Error && (err.name === "TimeoutError" || err.name === "AbortError")) ||
    (typeof DOMException !== "undefined" &&
      err instanceof DOMException &&
      (err.name === "TimeoutError" || err.name === "AbortError"))
  ) {
    return {
      errorMessage: resolveLocalizedClientError("ERR_CLIENT_TIMEOUT", locale, { seconds: 16 }),
      errorCode: "ERR_CLIENT_TIMEOUT",
    };
  }
  if (err instanceof Error && err.message.trim().length > 0) {
    return { errorMessage: err.message };
  }
  return {
    errorMessage: resolveLocalizedClientError(fallbackCode, locale, fallbackParams),
    errorCode: fallbackCode,
  };
}

/**
 * Format an API error with its server error code suffix when available, falling
 * back to localized `ClientErrorCode` resolution on client/network failures.
 */
export function formatLocalizedProblemWithCode(
  err: unknown,
  locale: SupportedUiLocale,
  fallbackCode: ClientErrorCode,
): string {
  const extracted = extractLocalizedApiError(err, locale, fallbackCode);
  if (err instanceof OrciaProblemError && extracted.errorCode) {
    return `${extracted.errorMessage} (${extracted.errorCode})`;
  }
  return extracted.errorMessage;
}
