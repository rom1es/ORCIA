/**
 * Bridge between `@orcia/api-client` and `/activity` screen (`Story 6.1`, `CAP-065`).
 *
 * Provides typed fetching of append-only audit entries, run provenance inspection,
 * and sealed JSON/Markdown compliance dossier exports.
 */

import {
  createOrciaApiClient,
  OrciaProblemError,
  type AuditExportResponse,
  type AuditLedgerEntrySchema,
  type AuditLedgerPageResponse,
  type AuditProvenanceSummaryResponse,
} from "@orcia/api-client";
import { useAuthSessionStore } from "../stores/authSessionStore";

export type {
  AuditExportResponse,
  AuditLedgerEntrySchema,
  AuditLedgerPageResponse,
  AuditProvenanceSummaryResponse,
};

export type AuditLedgerApiResult =
  | {
      readonly ok: true;
      readonly entries: readonly AuditLedgerEntrySchema[];
      readonly total: number;
    }
  | {
      readonly ok: false;
      readonly errorMessage: string;
      readonly errorCode?: string;
    };

export type AuditProvenanceApiResult =
  | {
      readonly ok: true;
      readonly summary: AuditProvenanceSummaryResponse;
    }
  | {
      readonly ok: false;
      readonly errorMessage: string;
      readonly errorCode?: string;
    };

export type AuditExportApiResult =
  | {
      readonly ok: true;
      readonly exportData: AuditExportResponse;
    }
  | {
      readonly ok: false;
      readonly errorMessage: string;
      readonly errorCode?: string;
    };

function buildAuditClient(locale: "fr" | "en") {
  const { readOnlyObserver, activeHat } = useAuthSessionStore.getState();
  const customFetch: typeof fetch = (input, init) => {
    const headers = new Headers(init?.headers);
    if (readOnlyObserver) {
      headers.set("X-Orcia-Access-Mode", "READ_ONLY_OBSERVER");
    }
    headers.set("X-Orcia-Active-Hat", activeHat);
    return globalThis.fetch(input, { ...init, headers });
  };
  return createOrciaApiClient({
    baseUrl: "",
    locale,
    fetchImpl: customFetch,
  });
}

function extractAuditApiError(
  err: unknown,
  locale: "fr" | "en",
): { readonly errorMessage: string; readonly errorCode?: string } {
  if (err instanceof OrciaProblemError) {
    return {
      errorMessage: err.problem.detail || err.problem.title,
      errorCode: err.problem.error_code,
    };
  }
  if (err instanceof Error && err.message.trim().length > 0) {
    return { errorMessage: err.message };
  }
  return {
    errorMessage:
      locale === "fr"
        ? "Une erreur réseau est survenue lors de la communication avec le registre d'audit."
        : "A network error occurred while communicating with the audit ledger.",
  };
}

export async function fetchAuditLedgerFromApi(
  locale: "fr" | "en" = "fr",
  params?: {
    scope_path?: string;
    workspace_id?: string;
    actor_type?: string;
    actor_id?: string;
    actor_query?: string;
    event_type?: string;
    run_id?: string;
    time_window?: "ALL" | "1H" | "24H" | "7D" | "30D";
    date_from?: string;
    date_to?: string;
    limit?: number;
    offset?: number;
  },
): Promise<AuditLedgerApiResult> {
  const query = new URLSearchParams();
  if (params?.scope_path) query.set("scope_path", params.scope_path);
  if (params?.workspace_id) query.set("workspace_id", params.workspace_id);
  if (params?.actor_type) query.set("actor_type", params.actor_type);
  if (params?.actor_id) query.set("actor_id", params.actor_id);
  if (params?.actor_query) query.set("actor_query", params.actor_query);
  if (params?.event_type) query.set("event_type", params.event_type);
  if (params?.run_id) query.set("run_id", params.run_id);
  if (params?.time_window) query.set("time_window", params.time_window);
  if (params?.date_from) query.set("date_from", params.date_from);
  if (params?.date_to) query.set("date_to", params.date_to);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const url = `/api/v1/audit/ledger${query.toString() ? `?${query.toString()}` : ""}`;
  try {
    const res = await globalThis.fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Accept-Language": locale,
      },
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      return {
        ok: false,
        errorMessage: errJson.detail || errJson.title || `HTTP ${res.status}`,
        errorCode: errJson.error_code,
      };
    }
    const rawData = (await res.json().catch(() => ({}))) as Partial<AuditLedgerPageResponse> & Record<string, unknown>;
    const entries: readonly AuditLedgerEntrySchema[] = Array.isArray(rawData?.entries)
      ? (rawData.entries as AuditLedgerEntrySchema[])
      : Array.isArray((rawData as { items?: unknown })?.items)
        ? ((rawData as { items: AuditLedgerEntrySchema[] }).items)
        : Array.isArray(rawData)
          ? (rawData as unknown as AuditLedgerEntrySchema[])
          : [];
    const total = typeof rawData?.total === "number"
      ? rawData.total
      : entries.length;
    return {
      ok: true,
      entries,
      total,
    };
  } catch (err) {
    return {
      ok: false,
      ...extractAuditApiError(err, locale),
    };
  }
}

export async function fetchRunProvenanceFromApi(
  runId: string,
  locale: "fr" | "en" = "fr",
): Promise<AuditProvenanceApiResult> {
  const url = `/api/v1/audit/ledger/${encodeURIComponent(runId)}/provenance`;
  try {
    const res = await globalThis.fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Accept-Language": locale,
      },
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      return {
        ok: false,
        errorMessage: errJson.detail || errJson.title || `HTTP ${res.status}`,
        errorCode: errJson.error_code,
      };
    }
    const data: AuditProvenanceSummaryResponse = await res.json();
    return {
      ok: true,
      summary: data,
    };
  } catch (err) {
    return {
      ok: false,
      ...extractAuditApiError(err, locale),
    };
  }
}

export async function exportRunProvenanceFromApi(
  runId: string,
  format: "json" | "md" = "json",
  locale: "fr" | "en" = "fr",
): Promise<AuditExportApiResult> {
  const url = `/api/v1/audit/ledger/${encodeURIComponent(runId)}/export?format=${format}`;
  try {
    const res = await globalThis.fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "Accept-Language": locale,
      },
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      return {
        ok: false,
        errorMessage: errJson.detail || errJson.title || `HTTP ${res.status}`,
        errorCode: errJson.error_code,
      };
    }
    const data: AuditExportResponse = await res.json();

    // Trigger browser file download if in a browser DOM environment
    if (typeof window !== "undefined" && typeof document !== "undefined" && data.content) {
      const mime = format === "json" ? "application/json" : "text/markdown";
      const blob = new Blob([data.content], { type: `${mime};charset=utf-8` });
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `audit-provenance-${runId}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(downloadUrl);
    }

    return {
      ok: true,
      exportData: data,
    };
  } catch (err) {
    return {
      ok: false,
      ...extractAuditApiError(err, locale),
    };
  }
}
