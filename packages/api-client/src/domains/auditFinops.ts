import type { components } from "../generated/schema";
import type { createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type AuditLedgerEntrySchema = components["schemas"]["AuditLedgerEntrySchema"];
export type AuditLedgerPageResponse = components["schemas"]["AuditLedgerPageResponse"];
export type AuditProvenanceSummaryResponse =
  components["schemas"]["AuditProvenanceSummaryResponse"];
export type AuditExportResponse = components["schemas"]["AuditExportResponse"];

export interface ListAuditLedgerParams {
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
}

export function createAuditFinopsDomainClient(requestJson: RequestJsonFn) {
  return {
    listAuditLedger(params?: ListAuditLedgerParams): Promise<AuditLedgerPageResponse> {
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
      if (params?.limit !== undefined) query.set("limit", String(params.limit));
      if (params?.offset !== undefined) query.set("offset", String(params.offset));
      const qs = query.toString();
      return requestJson<AuditLedgerPageResponse>(
        `/api/v1/audit/ledger${qs ? `?${qs}` : ""}`,
      );
    },

    getRunProvenance(runId: string): Promise<AuditProvenanceSummaryResponse> {
      return requestJson<AuditProvenanceSummaryResponse>(
        `/api/v1/audit/ledger/${encodeURIComponent(runId)}/provenance`,
      );
    },

    exportRunProvenance(
      runId: string,
      format: "json" | "md" = "json",
    ): Promise<AuditExportResponse> {
      return requestJson<AuditExportResponse>(
        `/api/v1/audit/ledger/${encodeURIComponent(runId)}/export?format=${format}`,
      );
    },
  };
}
