import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  createOrciaApiClient,
  registerDefaultAccessTokenProvider,
} from "../index";

describe("registerDefaultAccessTokenProvider (@orcia/api-client)", () => {
  beforeEach(() => {
    registerDefaultAccessTokenProvider(null);
  });

  it("injects Authorization: Bearer <token> automatically when default provider is registered and options.accessToken is omitted", async () => {
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      capturedHeaders = (init?.headers ?? {}) as Record<string, string>;
      return Promise.resolve(
        new Response(JSON.stringify({ status: "healthy", version: "0.1.0" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    registerDefaultAccessTokenProvider(() => "global-jwt-session-token");

    const client = createOrciaApiClient({
      baseUrl: "http://api.test",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await client.getHealth();

    expect(capturedHeaders.Authorization).toBe("Bearer global-jwt-session-token");
  });

  it("prioritizes options.accessToken over registered default provider", async () => {
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      capturedHeaders = (init?.headers ?? {}) as Record<string, string>;
      return Promise.resolve(
        new Response(JSON.stringify({ status: "healthy", version: "0.1.0" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    registerDefaultAccessTokenProvider(() => "global-jwt-session-token");

    const client = createOrciaApiClient({
      baseUrl: "http://api.test",
      accessToken: "explicit-override-token",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await client.getHealth();

    expect(capturedHeaders.Authorization).toBe("Bearer explicit-override-token");
  });

  it("prioritizes options.getAccessToken over registered default provider", async () => {
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      capturedHeaders = (init?.headers ?? {}) as Record<string, string>;
      return Promise.resolve(
        new Response(JSON.stringify({ status: "healthy", version: "0.1.0" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    registerDefaultAccessTokenProvider(() => "global-jwt-session-token");

    const client = createOrciaApiClient({
      baseUrl: "http://api.test",
      getAccessToken: () => "options-callback-token",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await client.getHealth();

    expect(capturedHeaders.Authorization).toBe("Bearer options-callback-token");
  });

  it("disables Authorization header completely when options.accessToken is explicitly empty string", async () => {
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      capturedHeaders = (init?.headers ?? {}) as Record<string, string>;
      return Promise.resolve(
        new Response(JSON.stringify({ status: "healthy", version: "0.1.0" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    registerDefaultAccessTokenProvider(() => "global-jwt-session-token");

    const client = createOrciaApiClient({
      baseUrl: "http://api.test",
      accessToken: "",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await client.getHealth();

    expect(capturedHeaders.Authorization).toBeUndefined();
  });

  it("does not inject Authorization header when provider returns null or undefined", async () => {
    let capturedHeaders: Record<string, string> = {};
    const mockFetch = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      capturedHeaders = (init?.headers ?? {}) as Record<string, string>;
      return Promise.resolve(
        new Response(JSON.stringify({ status: "healthy", version: "0.1.0" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    registerDefaultAccessTokenProvider(() => null);

    const client = createOrciaApiClient({
      baseUrl: "http://api.test",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await client.getHealth();

    expect(capturedHeaders.Authorization).toBeUndefined();
  });
});
