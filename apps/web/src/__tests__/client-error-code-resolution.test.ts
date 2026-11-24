import { OrciaClientError, OrciaProblemError } from "@orcia/api-client";
import { describe, expect, it } from "vitest";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import {
  CLIENT_ERROR_CODES,
  ClientCodedError,
  createClientErrorPayload,
  isClientErrorCode,
  isClientErrorPayload,
  resolveClientErrorMessage,
} from "../lib/clientErrorCodes";
import {
  extractLocalizedApiError,
  formatRfc9457ErrorToBanner,
  resolveLocalizedClientError,
} from "../lib/formatRfc9457ErrorToBanner";

describe("Story 27.1 — Shared ClientErrorCode resolution foundation", () => {
  it("resolves every ClientErrorCode to non-empty distinct French and English messages", () => {
    for (const code of CLIENT_ERROR_CODES) {
      const frMsg = resolveClientErrorMessage(code, frDictionary.clientErrors, {
        seconds: 16,
        detail: "champ manquant",
      });
      const enMsg = resolveClientErrorMessage(code, enDictionary.clientErrors, {
        seconds: 16,
        detail: "missing field",
      });
      expect(frMsg.length).toBeGreaterThan(10);
      expect(enMsg.length).toBeGreaterThan(10);
      expect(frMsg).not.toEqual(enMsg);
      expect(frMsg).not.toContain("{seconds}");
      expect(frMsg).not.toContain("{detail}");
      expect(enMsg).not.toContain("{seconds}");
      expect(enMsg).not.toContain("{detail}");
    }
  });

  it("interpolates {seconds} on ERR_CLIENT_TIMEOUT and strips it cleanly when omitted", () => {
    const frWithSeconds = resolveClientErrorMessage("ERR_CLIENT_TIMEOUT", frDictionary.clientErrors, {
      seconds: 16,
    });
    const enWithSeconds = resolveClientErrorMessage("ERR_CLIENT_TIMEOUT", enDictionary.clientErrors, {
      seconds: 16,
    });
    expect(frWithSeconds).toContain("16");
    expect(enWithSeconds).toContain("16s");

    const frWithoutSeconds = resolveClientErrorMessage("ERR_CLIENT_TIMEOUT", frDictionary.clientErrors);
    const enWithoutSeconds = resolveClientErrorMessage("ERR_CLIENT_TIMEOUT", enDictionary.clientErrors);
    expect(frWithoutSeconds).not.toContain("{seconds}");
    expect(enWithoutSeconds).not.toContain("{seconds}");
    expect(frWithoutSeconds).toContain("délai");
    expect(enWithoutSeconds).toContain("timeout");
  });

  it("interpolates {detail} on ERR_CLIENT_INVALID_PAYLOAD and omits empty placeholders cleanly", () => {
    const frWithDetail = resolveClientErrorMessage(
      "ERR_CLIENT_INVALID_PAYLOAD",
      frDictionary.clientErrors,
      { detail: "champ email requis" },
    );
    const enWithDetail = resolveClientErrorMessage(
      "ERR_CLIENT_INVALID_PAYLOAD",
      enDictionary.clientErrors,
      { detail: "email field required" },
    );
    expect(frWithDetail).toContain("(champ email requis)");
    expect(enWithDetail).toContain("(email field required)");

    const frBare = resolveClientErrorMessage("ERR_CLIENT_INVALID_PAYLOAD", frDictionary.clientErrors);
    const enBare = resolveClientErrorMessage("ERR_CLIENT_INVALID_PAYLOAD", enDictionary.clientErrors);
    expect(frBare).not.toContain("{detail}");
    expect(frBare).not.toContain("()");
    expect(enBare).not.toContain("{detail}");
    expect(enBare).not.toContain("()");
  });

  it("falls back safely to ERR_CLIENT_UNKNOWN on unrecognized or nullish codes", () => {
    expect(resolveClientErrorMessage("ERR_NOT_A_REAL_CODE", frDictionary.clientErrors)).toBe(
      frDictionary.clientErrors.ERR_CLIENT_UNKNOWN,
    );
    expect(resolveClientErrorMessage(null, enDictionary.clientErrors)).toBe(
      enDictionary.clientErrors.ERR_CLIENT_UNKNOWN,
    );
    expect(
      resolveClientErrorMessage(undefined, enDictionary.clientErrors, {
        detail: "stream reset",
      }),
    ).toBe(`${enDictionary.clientErrors.ERR_CLIENT_UNKNOWN} (stream reset)`);
  });

  it("creates and validates structured ClientErrorPayload objects", () => {
    const payload = createClientErrorPayload("ERR_CLIENT_SSE_DISCONNECTED", { seconds: 10 });
    expect(isClientErrorCode(payload.code)).toBe(true);
    expect(isClientErrorCode("ERR_NONEXISTENT")).toBe(false);
    expect(isClientErrorPayload(payload)).toBe(true);
    expect(isClientErrorPayload({ code: "ERR_CLIENT_NETWORK" })).toBe(true);
    expect(isClientErrorPayload({ code: "ERR_CLIENT_NETWORK", params: { seconds: "bad" } })).toBe(
      false,
    );
    expect(isClientErrorPayload(null)).toBe(false);
  });
});

describe("Story 27.2 — Bilingual ClientErrorCode & RFC 9457 banner resolution", () => {
  it("formats OrciaClientError and ClientCodedError in both fr and en without hardcoded leaks", () => {
    const sseErr = new OrciaClientError("ERR_CLIENT_SSE_EMPTY_BODY", {
      detail: "/api/v1/assistant/turns/1/stream",
    });
    const frBanner = formatRfc9457ErrorToBanner(sseErr, "fr");
    const enBanner = formatRfc9457ErrorToBanner(sseErr, "en");
    expect(frBanner.title).toBe("Échec de l'opération");
    expect(enBanner.title).toBe("Operation failed");
    expect(frBanner.message).toContain("/api/v1/assistant/turns/1/stream");
    expect(enBanner.message).toContain("/api/v1/assistant/turns/1/stream");
    expect(frBanner.message).not.toEqual(enBanner.message);

    const timeoutErr = new ClientCodedError("ERR_CLIENT_AUTH_HYDRATION_TIMEOUT", {
      seconds: 5,
    });
    expect(formatRfc9457ErrorToBanner(timeoutErr, "fr").message).toContain("5 s");
    expect(formatRfc9457ErrorToBanner(timeoutErr, "en").message).toContain("5s");
  });

  it("resolves ProblemDetails carrying ERR_CLIENT_* fallback codes into localized fr/en banners", () => {
    const problem = new OrciaProblemError({
      type: "about:blank",
      title: "ERR_CLIENT_HTTP_FALLBACK",
      status: 500,
      detail: "ERR_CLIENT_INVALID_PAYLOAD",
      instance: "/api/v1/workspaces",
      error_code: "ERR_INTERNAL_SERVER_ERROR",
      trace_id: "0195f000000070008000000000000001",
    });

    const frBanner = formatRfc9457ErrorToBanner(problem, "fr");
    const enBanner = formatRfc9457ErrorToBanner(problem, "en");
    expect(frBanner.message).toContain("données reçues du serveur sont invalides");
    expect(enBanner.message).toContain("data received from the server is invalid");
    expect(frBanner.fullText).not.toContain("ERR_CLIENT_");
    expect(enBanner.fullText).not.toContain("ERR_CLIENT_");
  });

  it("sanitizes internal enum tokens in the active locale (fr and en)", () => {
    const problem = new OrciaProblemError({
      type: "https://orcia.io/problems/test",
      title: "Error",
      status: 403,
      detail: "Action blocked because READ_ONLY_OBSERVER and HIGH_CRITICAL apply",
      error_code: "ERR_UNKNOWN_CODE",
      trace_id: "0195f000000070008000000000000002",
    });

    const frBanner = formatRfc9457ErrorToBanner(problem, "fr");
    const enBanner = formatRfc9457ErrorToBanner(problem, "en");
    expect(frBanner.message).toContain("lecture seule");
    expect(frBanner.message).toContain("critique");
    expect(enBanner.message).toContain("read-only mode");
    expect(enBanner.message).toContain("critical");
    expect(enBanner.message).not.toContain("lecture seule");
  });

  it("extracts timeout and client error codes cleanly via extractLocalizedApiError", () => {
    const timeoutDom = new DOMException("Timed out", "TimeoutError");
    const frExtracted = extractLocalizedApiError(timeoutDom, "fr");
    const enExtracted = extractLocalizedApiError(timeoutDom, "en");
    expect(frExtracted.errorCode).toBe("ERR_CLIENT_TIMEOUT");
    expect(frExtracted.errorMessage).toContain("16 s");
    expect(enExtracted.errorMessage).toContain("16s");

    expect(resolveLocalizedClientError("ERR_CLIENT_WIZARD_STEP_BACK", "fr")).toContain(
      "étape précédente",
    );
    expect(resolveLocalizedClientError("ERR_CLIENT_WIZARD_STEP_BACK", "en")).toContain(
      "previous step",
    );
  });
});
