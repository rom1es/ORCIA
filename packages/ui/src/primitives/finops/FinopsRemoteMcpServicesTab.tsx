import React, { useState } from "react";
import { StatusBadge } from "../StatusBadge";
import { FinopsConnectorQuotaModal } from "./FinopsConnectorQuotaModal";
import type {
  RemoteServiceRowData,
  RemoteServicesTabLabels,
  UpdateConnectorQuotaInput,
} from "./FinopsDashboardTypes";

export interface FinopsRemoteMcpServicesTabProps {
  readonly services: readonly RemoteServiceRowData[];
  readonly labels: RemoteServicesTabLabels;
  readonly onUpdateConnectorQuota?: (input: UpdateConnectorQuotaInput) => void;
  readonly onResetConnectorCircuit?: (connectorKey: string) => void;
  readonly onOpenHelpSection?: (sectionId: string) => void;
}

function formatEur(val: number): string {
  return `${val.toFixed(2).replace(".", ",")} €`;
}

function resolveServiceKindLabel(
  kind: string,
  kinds: RemoteServicesTabLabels["serviceKinds"],
): string {
  if (kind === "A2A_AGENT") return kinds.a2aAgent;
  if (kind === "OPENAPI_REST") return kinds.openapiRest;
  if (kind === "CONNECTOR") return kinds.connector;
  return kinds.mcpServer;
}

export function FinopsRemoteMcpServicesTab({
  services,
  labels,
  onUpdateConnectorQuota,
  onResetConnectorCircuit,
}: FinopsRemoteMcpServicesTabProps): React.ReactElement {
  const [editingService, setEditingService] = useState<RemoteServiceRowData | null>(null);

  return (
    <div
      className="finops-remote-services-tab"
      data-testid="finops-remote-services-tab"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h2
              data-testid="finops-remote-services-title"
              style={{ fontSize: "16px", fontWeight: 700, margin: 0, color: "var(--color-text-primary)" }}
            >
              {labels.tabTitle}
            </h2>
          </div>
          <p style={{ fontSize: "13px", color: "var(--color-text-muted)", margin: "4px 0 0 0" }}>
            {labels.tabSubtitle}
          </p>
        </div>
      </div>

      {services.length === 0 ? (
        <div
          className="orcia-bento-card"
          data-testid="finops-remote-services-empty"
          style={{
            padding: "24px",
            textAlign: "center",
            borderRadius: "8px",
            border: "1px dashed var(--color-border)",
            color: "var(--color-text-muted)",
            fontSize: "13px",
          }}
        >
          {labels.emptyStateText}
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table
            className="orcia-table"
            data-testid="finops-remote-services-table"
            style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}
          >
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", color: "var(--color-text-muted)" }}>
                <th style={{ padding: "10px 12px" }}>{labels.columns.serviceCol}</th>
                <th style={{ padding: "10px 12px" }}>{labels.columns.typeCol}</th>
                <th style={{ padding: "10px 12px" }}>{labels.columns.callsAndLatencyCol}</th>
                <th style={{ padding: "10px 12px" }}>{labels.columns.remoteTokensCol}</th>
                <th style={{ padding: "10px 12px" }}>{labels.columns.businessUnitsCol}</th>
                <th style={{ padding: "10px 12px" }}>{labels.columns.valuationModeCol}</th>
                <th style={{ padding: "10px 12px" }}>{labels.columns.consolidatedCostCol}</th>
                <th style={{ padding: "10px 12px" }}>{labels.columns.quotaCol}</th>
                <th style={{ padding: "10px 12px" }}>{labels.columns.circuitStatusCol}</th>
                <th style={{ padding: "10px 12px" }}>{labels.columns.actionsCol}</th>
              </tr>
            </thead>
            <tbody>
              {services.map((s) => {
                const isOpen = s.circuitState === "CIRCUIT_OPEN";
                const isHalfOpen = s.circuitState === "HALF_OPEN";
                const valuationBadge =
                  s.valuationMode === "FIXED_SCALE"
                    ? { tone: "cyan" as const, label: labels.valuationModes.fixedScale }
                    : s.valuationMode === "VOLUMETRIC_ONLY"
                      ? { tone: "neutral" as const, label: labels.valuationModes.volumetricOnly }
                      : { tone: "cobalt" as const, label: labels.valuationModes.nativeTelemetry };

                const circuitBadge = isOpen
                  ? { tone: "crimson" as const, label: labels.circuitStates.open }
                  : isHalfOpen
                    ? { tone: "amber" as const, label: labels.circuitStates.halfOpen }
                    : { tone: "emerald" as const, label: labels.circuitStates.closed };

                const unitLabel = s.defaultUnitName ? ` ${s.defaultUnitName}` : "";

                return (
                  <tr
                    key={s.connectorKey}
                    data-testid={`finops-remote-row-${s.connectorKey}`}
                    style={{ borderBottom: "1px solid var(--color-border)" }}
                  >
                    <td style={{ padding: "10px 12px" }}>
                      <div style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
                        {s.displayName}
                      </div>
                      <div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
                        {s.connectorKey}
                      </div>
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <StatusBadge
                        tone="neutral"
                        label={resolveServiceKindLabel(s.serviceKind, labels.serviceKinds)}
                      />
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <div>{s.dailyCallsCount} {labels.callsSuffix}</div>
                      <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                        {s.avgLatencyMs} ms
                      </div>
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      {s.totalRemoteTokens.toLocaleString()}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      {s.totalBusinessUnits > 0 ? `${s.totalBusinessUnits}${unitLabel}` : "—"}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <StatusBadge tone={valuationBadge.tone} label={valuationBadge.label} />
                    </td>
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>
                      {formatEur(s.consolidatedCostEur)}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <div>{Math.round(s.quotaUsedPct)} %</div>
                      <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                        {s.maxMonthlyCostEur != null
                          ? formatEur(s.maxMonthlyCostEur)
                          : s.maxDailyCalls != null
                            ? `${s.maxDailyCalls} ${labels.callsSuffix}`
                            : labels.unlimitedLabel}
                      </div>
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <StatusBadge
                        tone={circuitBadge.tone}
                        label={circuitBadge.label}
                        testId={`finops-circuit-badge-${s.connectorKey}`}
                      />
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                        <button
                          type="button"
                          data-testid={`finops-edit-quota-btn-${s.connectorKey}`}
                          className="orcia-ds-btn orcia-ds-btn-secondary"
                          style={{ fontSize: "12px", padding: "4px 8px" }}
                          onClick={() => setEditingService(s)}
                        >
                          {labels.editQuotaButton}
                        </button>
                        {isOpen && (
                          <button
                            type="button"
                            data-testid={`finops-reset-circuit-btn-${s.connectorKey}`}
                            className="orcia-ds-btn orcia-ds-btn-primary"
                            style={{ fontSize: "12px", padding: "4px 8px" }}
                            onClick={() => onResetConnectorCircuit?.(s.connectorKey)}
                          >
                            {labels.resetCircuitButton}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <FinopsConnectorQuotaModal
        open={editingService !== null}
        onOpenChange={(open) => {
          if (!open) setEditingService(null);
        }}
        service={editingService}
        labels={labels}
        onSaveQuota={onUpdateConnectorQuota}
      />
    </div>
  );
}
