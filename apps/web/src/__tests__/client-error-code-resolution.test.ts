import { describe, expect, it } from "vitest";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import {
  CLIENT_ERROR_CODES,
  createClientErrorPayload,
  isClientErrorCode,
  isClientErrorPayload,
  resolveClientErrorMessage,
} from "../lib/clientErrorCodes";

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
