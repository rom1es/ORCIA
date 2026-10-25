import React, { useState } from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import type {
  UiCatalogResourcePermissionView,
  UiPersonaKey,
  UiWorkspaceCardView,
  UiWorkspaceTopologyLabels,
} from "./types";

export interface WorkspaceTopologyPanelProps {
  activePersona: UiPersonaKey;
  workspaces: UiWorkspaceCardView[];
  consolidatedFinopsUsd: number;
  catalogResources: UiCatalogResourcePermissionView[];
  labels: UiWorkspaceTopologyLabels;
  onSelectPersona: (persona: UiPersonaKey) => void;
}

const PERSONA_ORDER: UiPersonaKey[] = [
  "karim",
  "claire",
  "marc",
  "nadia",
  "partenaire",
];

export function WorkspaceTopologyPanel({
  activePersona,
  workspaces,
  consolidatedFinopsUsd,
  catalogResources,
  labels,
  onSelectPersona,
}: WorkspaceTopologyPanelProps) {
  const [mutationBannerByWs, setMutationBannerByWs] = useState<Record<string, string>>({});
  const [sourceBannerByRes, setSourceBannerByRes] = useState<Record<string, string>>({});

  return (
    <section
      data-testid="workspace-topology-panel"
      style={{
        backgroundColor: "var(--color-surface-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>{labels.panelTitle}</h2>
          <p style={{ margin: "4px 0 0 0", color: "var(--color-muted-foreground)" }}>
            {labels.panelSubtitle}
          </p>
        </div>
        <StatusBadge
          testId="finops-rollup-badge"
          label={`${labels.finopsRollupPrefix}: ${consolidatedFinopsUsd.toFixed(2)} USD`}
          tone="cyan"
          monospace
        />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <span style={{ fontWeight: 600 }}>{labels.personaSelectorLabel}</span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {PERSONA_ORDER.map((pKey) => {
            const isSelected = pKey === activePersona;
            return (
              <button
                key={pKey}
                type="button"
                data-testid={`persona-switch-${pKey}`}
                data-active={isSelected ? "true" : "false"}
                onClick={() => {
                  setMutationBannerByWs({});
                  setSourceBannerByRes({});
                  onSelectPersona(pKey);
                }}
                style={{
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: isSelected
                    ? "var(--color-primary-cobalt)"
                    : "var(--color-surface)",
                  color: isSelected
                    ? "var(--color-primary-foreground)"
                    : "var(--color-foreground)",
                  cursor: "pointer",
                  fontFamily: "var(--font-sans)",
                }}
              >
                {labels.personas[pKey]}
              </button>
            );
          })}
        </div>
      </div>

      <div
        data-testid="confidential-rollup-notice"
        style={{
          fontSize: "var(--font-size-mono)",
          color: "var(--color-muted-foreground)",
        }}
      >
        {labels.confidentialExcludedNotice}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "12px",
        }}
      >
        {workspaces.map((ws) => (
          <div
            key={ws.id}
            data-testid={`workspace-card-${ws.id}`}
            style={{
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "12px",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              backgroundColor: "var(--color-surface)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
              <strong>{ws.name}</strong>
              <StatusBadge
                label={ws.visibilityMode}
                tone={ws.visibilityMode === "CONFIDENTIAL_RESTRICTED" ? "crimson" : "emerald"}
                monospace
              />
            </div>
            <div style={{ fontSize: "var(--font-size-mono)", color: "var(--color-muted-foreground)" }}>
              {ws.ownerOrgUnitName} · {ws.effectiveRole} ({ws.accessOrigin})
            </div>
            <div style={{ fontSize: "var(--font-size-mono)" }}>
              {labels.datasourcesCountPrefix}: {ws.datasources.length}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
              {ws.datasources.map((ds) => (
                <StatusBadge
                  key={ds.id}
                  testId={`ws-datasource-badge-${ds.alias}`}
                  label={`${ds.scheme}://${ds.alias}`}
                  tone="cobalt"
                  monospace
                />
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
              <button
                type="button"
                data-testid={`mutation-guard-btn-${ws.id}`}
                onClick={() => {
                  const msg =
                    ws.accessMode === "READ_ONLY_OBSERVER"
                      ? labels.mutationDeniedObserverBanner
                      : labels.mutationAllowedBanner;
                  setMutationBannerByWs((prev) => ({ ...prev, [ws.id]: msg }));
                }}
                style={{
                  padding: "4px 8px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface-card)",
                  color: "var(--color-foreground)",
                  cursor: "pointer",
                  fontSize: "var(--font-size-mono)",
                }}
              >
                {labels.mutationGuardButtonLabel}
              </button>
              {mutationBannerByWs[ws.id] && (
                <span
                  data-testid={`mutation-guard-result-${ws.id}`}
                  style={{ fontSize: "var(--font-size-mono)" }}
                >
                  {mutationBannerByWs[ws.id]}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <strong>{labels.catalogPermissionsTitle}</strong>
        {catalogResources.map((res) => (
          <div
            key={res.resourceId}
            data-testid={`catalog-resource-card-${res.resourceId}`}
            style={{
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "10px",
              display: "flex",
              flexDirection: "column",
              gap: "6px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
              <span>{res.title}</span>
              <StatusBadge
                testId={`source-mask-badge-${res.resourceId}`}
                label={res.sourceMasked ? labels.sourceMaskedBadgeLabel : labels.sourceOpenBadgeLabel}
                tone={res.sourceMasked ? "amber" : "emerald"}
                monospace
              />
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", alignItems: "center" }}>
              {res.grantedPermissions.map((perm) => (
                <StatusBadge key={perm} label={perm} tone="neutral" monospace />
              ))}
              <button
                type="button"
                data-testid={`inspect-source-btn-${res.resourceId}`}
                onClick={() => {
                  const text = res.sourceMasked
                    ? labels.sourceDeniedErrorBanner
                    : `${labels.sourceAllowedBannerPrefix}: ${res.resourceUri}`;
                  setSourceBannerByRes((prev) => ({ ...prev, [res.resourceId]: text }));
                }}
                style={{
                  padding: "3px 8px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface)",
                  color: "var(--color-foreground)",
                  cursor: "pointer",
                  fontSize: "var(--font-size-mono)",
                }}
              >
                {labels.inspectSourceButtonLabel}
              </button>
              {sourceBannerByRes[res.resourceId] && (
                <span
                  data-testid={`inspect-source-result-${res.resourceId}`}
                  style={{ fontSize: "var(--font-size-mono)" }}
                >
                  {sourceBannerByRes[res.resourceId]}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
