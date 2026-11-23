/**
 * Bridge between `@orcia/api-client` and `/activity` screen (`Story 6.1`, `CAP-065`).
 *
 * Provides typed fetching of append-only audit entries, run provenance inspection,
 * and sealed JSON/Markdown compliance dossier exports.
 */

import {
  createOrciaApiClient,
  type AuditExportResponse,
  type AuditLedgerEntrySchema,
  type AuditLedgerPageResponse,
  type AuditProvenanceSummaryResponse,
  type ListAuditLedgerParams,
} from "@orcia/api-client";
import { extractLocalizedApiError } from "../lib/formatRfc9457ErrorToBanner";
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
  return createOrciaApiClient({
    baseUrl: "",
    locale,
    extraHeaders: () => ({
      ...(readOnlyObserver ? { "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER" } : {}),
      "X-Orcia-Active-Hat": activeHat,
    }),
  });
}

function extractAuditApiError(
  err: unknown,
  locale: "fr" | "en",
): { readonly errorMessage: string; readonly errorCode?: string } {
  return extractLocalizedApiError(err, locale, "ERR_CLIENT_AUDIT_NETWORK");
}

export async function fetchAuditLedgerFromApi(
  locale: "fr" | "en" = "fr",
  params?: ListAuditLedgerParams,
): Promise<AuditLedgerApiResult> {
  try {
    const client = buildAuditClient(locale);
    const rawData = (await client.auditFinops.listAuditLedger(params)) as
      | (Partial<AuditLedgerPageResponse> & Record<string, unknown>)
      | undefined;
    const entries: readonly AuditLedgerEntrySchema[] = Array.isArray(rawData?.entries)
      ? (rawData.entries as AuditLedgerEntrySchema[])
      : Array.isArray((rawData as { items?: unknown })?.items)
        ? (rawData as { items: AuditLedgerEntrySchema[] }).items
        : Array.isArray(rawData)
          ? (rawData as unknown as AuditLedgerEntrySchema[])
          : [];
    const total = typeof rawData?.total === "number" ? rawData.total : entries.length;
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
  try {
    const client = buildAuditClient(locale);
    const data = await client.auditFinops.getRunProvenance(runId);
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
  try {
    const client = buildAuditClient(locale);
    const data = await client.auditFinops.exportRunProvenance(runId, format);

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
