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

  it("returns HTTP 401 application/problem+json when calling a secured OpenAPI operation without Bearer token", async () => {
    const resp = await vitestFetchTransport(
      "/api/v1/workspaces/0195f000-0000-7000-8000-000000000301/dna-mechanisms/compile",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rule_id: "rule-1",
          directive_title: "Directive test",
          norm_title: "Norme test",
          natural_language_rule_fr: "Invariant de validation métier",
          required_field: "owner_id",
        }),
      },
    );
    expect(resp.status).toBe(401);
    expect(resp.headers.get("content-type")).toContain("application/problem+json");
    const payload = (await resp.json()) as { title?: string; detail?: string; status?: number };
    expect(payload.status).toBe(401);
    expect(payload.title).toBeTruthy();
    expect(payload.detail).toBeTruthy();
  });

  it("rejects routes present in OpenAPI with Bearer token but lacking an explicit Vitest handler", async () => {
    await expect(
      vitestFetchTransport("/api/v1/admin/outbox/replays", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer mock-token",
        },
        body: JSON.stringify({ dry_run: true }),
      }),
    ).rejects.toThrow(/\[vitestFetchTransport FAIL-CLOSED\] Route non gérée/i);
  });

  it("rejects undeclared HTTP methods on a known OpenAPI path", async () => {
    await expect(
      vitestFetchTransport("/api/v1/health", {
        method: "DELETE",
      }),
    ).rejects.toThrow(/méthode DELETE non déclarée/i);
  });

  it("rejects POST requests missing a mandatory JSON requestBody", async () => {
    await expect(
      vitestFetchTransport("/api/v1/auth/login/local", {
        method: "POST",
      }),
    ).rejects.toThrow(/corps JSON requestBody obligatoire manquant/i);
  });
});
