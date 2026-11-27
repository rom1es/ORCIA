import type { ProblemDetails } from "./generated/schema";
import { buildBaseHeaders, type OrciaApiClientOptions } from "./helpers";
import { OrciaProblemError, parseProblemError } from "./sseAndQueryHelpers";

export interface DraftPackReferenceInfo {
  readonly bundleId: string;
  readonly slug: string;
  readonly name: string;
  readonly version: string;
}

export interface MissingClosureDependencyInfo {
  readonly entityType: string;
  readonly entityId: string;
  readonly reason: string;
  readonly referencedBy: string;
}

export interface PackLeakFindingInfo {
  readonly path: string;
  readonly kind: string;
  readonly detail: string;
}

export function createRequestMultipart(options: OrciaApiClientOptions) {
  const fetcher = options.fetchImpl ?? globalThis.fetch;

  return async function requestMultipart<T>(
    path: string,
    formData: FormData,
    extraHeaders?: Record<string, string>,
    signal?: AbortSignal,
  ): Promise<T> {
    const headers = buildBaseHeaders(
      options,
      "application/json, application/problem+json",
      extraHeaders,
    );
    delete headers["Content-Type"];
    delete headers["content-type"];
    const response = await fetcher(`${options.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: formData,
      credentials: "include",
      ...(signal ? { signal } : {}),
    });
    if (!response.ok) {
      throw await parseProblemError(response, path, options.traceId);
    }
    return (await response.json()) as T;
  };
}

function asProblemRecord(error: unknown): (ProblemDetails & Record<string, unknown>) | null {
  if (error instanceof OrciaProblemError) {
    return error.problem as ProblemDetails & Record<string, unknown>;
  }
  if (typeof error === "object" && error !== null && "error_code" in error) {
    return error as ProblemDetails & Record<string, unknown>;
  }
  return null;
}

export function extractDraftPackReferences(error: unknown): readonly DraftPackReferenceInfo[] {
  const problem = asProblemRecord(error);
  if (!problem || !Array.isArray(problem.draft_packs)) {
    return [];
  }
  return (problem.draft_packs as readonly unknown[])
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => ({
      bundleId: String(item.bundle_id ?? item.id ?? ""),
      slug: String(item.slug ?? item.pack_slug ?? ""),
      name: String(item.name ?? item.slug ?? item.bundle_id ?? ""),
      version: String(item.version ?? "0.1.0"),
    }))
    .filter((item) => item.bundleId.length > 0 || item.slug.length > 0 || item.name.length > 0);
}

export function extractMissingClosureDependencies(
  error: unknown,
): readonly MissingClosureDependencyInfo[] {
  const problem = asProblemRecord(error);
  if (!problem || !Array.isArray(problem.missing_dependencies)) {
    return [];
  }
  return (problem.missing_dependencies as readonly unknown[])
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => ({
      entityType: String(item.entity_type ?? ""),
      entityId: String(item.entity_id ?? ""),
      reason: String(item.reason ?? ""),
      referencedBy: String(item.referenced_by ?? ""),
    }));
}

export function extractPackLeakFindings(error: unknown): readonly PackLeakFindingInfo[] {
  const problem = asProblemRecord(error);
  if (!problem || !Array.isArray(problem.leak_findings)) {
    return [];
  }
  return (problem.leak_findings as readonly unknown[])
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => ({
      path: String(item.path ?? ""),
      kind: String(item.kind ?? ""),
      detail: String(item.detail ?? ""),
    }));
}

export function extractMissingSlotsFromProblem(error: unknown): readonly string[] {
  const problem = asProblemRecord(error);
  if (!problem) return [];
  const rawList = problem.missing_slots;
  if (Array.isArray(rawList)) {
    return rawList.map((item) => String(item).trim()).filter(Boolean);
  }
  const detail = typeof problem.detail === "string" ? problem.detail : "";
  const colonIdx = detail.lastIndexOf(":");
  if (colonIdx >= 0) {
    const tail = detail.slice(colonIdx + 1).replace(/[.]+$/, "").trim();
    if (tail.length > 0) {
      return tail
        .split(",")
        .map((s) => s.trim())
        .filter((s) => /^[a-z0-9][a-z0-9._-]{0,127}$/i.test(s));
    }
  }
  return [];
}
