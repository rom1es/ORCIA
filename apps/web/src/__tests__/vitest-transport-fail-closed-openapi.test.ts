import { describe, expect, it } from "vitest";
import { vitestFetchTransport } from "./vitest.setup";

describe("vitestFetchTransport OpenAPI 3.1 fail-closed contract enforcement", () => {
  it("rejects unknown routes instead of returning an empty jsonResponse", async () => {
    await expect(
      vitestFetchTransport("/api/v1/route-inconnue-fail-closed", {
        method: "GET",
      }),
    ).rejects.toThrow(/FAIL-CLOSED OpenAPI.*route absente/i);
  });

  it("rejects non-UUID path identifiers on parameters declared with format uuid", async () => {
    await expect(
      vitestFetchTransport("/api/v1/workspaces/ws-1/dna-mechanisms/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }),
    ).rejects.toThrow(/UUID invalide \("ws-1"\)/);
  });

  it("rejects POST JSON payloads missing OpenAPI required fields", async () => {
    await expect(
      vitestFetchTransport(
        "/api/v1/workspaces/0195f000-0000-7000-8000-000000000301/datasources",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            alias: "incomplete-source",
          }),
        },
      ),
    ).rejects.toThrow(/champ obligatoire 'scheme' manquant/i);
  });

  it("rejects undeclared fields on schemas with additionalProperties false (SecretInputPayload)", async () => {
    await expect(
      vitestFetchTransport("/api/v1/settings/ai-models/mappings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider_slug: "openai",
          model_family: "OpenAI",
          model_name: "gpt-4o-mini",
          endpoint_uri: "https://api.openai.com/v1",
          secret_input: {
            action: "set",
            value: "sk-undeclared-field",
          },
        }),
      }),
    ).rejects.toThrow(/champ non déclaré 'value' interdit \(additionalProperties: false\)/i);
  });

  it("rejects routes present in OpenAPI but lacking an explicit Vitest handler", async () => {
    await expect(
      vitestFetchTransport(
        "/api/v1/workspaces/0195f000-0000-7000-8000-000000000301/dna-mechanisms/compile",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_text: "Invariant de validation",
          }),
        },
      ),
    ).rejects.toThrow(/vitestFetchTransport FAIL-CLOSED/i);
  });
});
