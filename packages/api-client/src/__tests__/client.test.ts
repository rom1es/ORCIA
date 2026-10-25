import { describe, expect, it, vi } from "vitest";
import { createOrciaApiClient, OrciaProblemError } from "../index";

describe("createOrciaApiClient", () => {
  it("fetches /api/v1/health with Accept-Language and X-Trace-Id headers", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        version: "0.1.0",
        trace_id: "0192c4e0000070008000000000000001",
      }),
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      locale: "fr",
      traceId: "0192c4e0000070008000000000000001",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    const res = await client.getHealth();
    expect(res.status).toBe("ok");
    expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/v1/health", {
      method: "GET",
      headers: {
        Accept: "application/json, application/problem+json",
        "Accept-Language": "fr",
        "X-Trace-Id": "0192c4e0000070008000000000000001",
      },
    });
  });

  it("throws OrciaProblemError when backend returns RFC 9457 ProblemDetails", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        type: "https://orcia.io/problems/observer-mode-read-only",
        title: "Mode observateur en lecture seule",
        status: 403,
        detail: "Cette action de modification est interdite en mode READ_ONLY_OBSERVER.",
        instance: "/api/v1/navigation/shell",
        error_code: "ERR_OBSERVER_MODE_READ_ONLY",
        trace_id: "0192c4e0000070008000000000000002",
      }),
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await expect(client.getShellNavigation("scope-global")).rejects.toBeInstanceOf(
      OrciaProblemError,
    );
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/navigation/shell?scope_id=scope-global",
      {
        method: "GET",
        headers: {
          Accept: "application/json, application/problem+json",
          "Accept-Language": "fr",
        },
      },
    );
  });

  it("fetches /api/v1/navigation/shell on 200 OK without query string when scopeId is omitted", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        active_scope_id: "scope-ws-orcia",
        scopes: [],
        modules: [],
        human_profile: {
          archetype_key: "TECH_LEAD",
          display_name: "Tech Lead",
          access_mode: "CONTRIBUTOR_ACTION_REQUIRED",
        },
        trace_id: "0192c4e0000070008000000000000003",
      }),
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      locale: "en",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    const res = await client.getShellNavigation();
    expect(res.active_scope_id).toBe("scope-ws-orcia");
    expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/v1/navigation/shell", {
      method: "GET",
      headers: {
        Accept: "application/json, application/problem+json",
        "Accept-Language": "en",
      },
    });
  });

  it("synthesizes a fallback ProblemDetails when a non-2xx response has a non-JSON body", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      headers: {
        get: (name: string) =>
          name.toLowerCase() === "x-trace-id" ? "0192c4e0000070008000000000000099" : null,
      },
      json: async () => {
        throw new SyntaxError("Unexpected token < in JSON at position 0");
      },
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    try {
      await client.getHealth();
      expect.unreachable("Should have thrown OrciaProblemError");
    } catch (err) {
      expect(err).toBeInstanceOf(OrciaProblemError);
      const problemErr = err as OrciaProblemError;
      expect(problemErr.problem.status).toBe(502);
      expect(problemErr.problem.error_code).toBe("ERR_INTERNAL_SERVER_ERROR");
      expect(problemErr.problem.instance).toBe("/api/v1/health");
      expect(problemErr.problem.trace_id).toBe("0192c4e0000070008000000000000099");
    }
  });
});
