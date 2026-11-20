import type { DeclarativePackSummaryResponse } from "@orcia/api-client";
import React from "react";
import {
  formatConnectorDisplayName,
  formatConnectorScopes,
  formatPackAgentDisplayName,
  formatPackCounterLabel,
} from "./packDisplayFormatters";

export interface PackCardItemProps {
  readonly pack: DeclarativePackSummaryResponse;
  readonly isFr: boolean;
  readonly onExportZip: (packId: string) => void;
}

export function PackCardItem({ pack, isFr, onExportZip }: PackCardItemProps) {
  const counters = [
    {
      key: "agents",
      label: formatPackCounterLabel(pack.agents_count, "Agent", "Agents", "Agent", "Agents", isFr),
      count: pack.agents_count,
    },
    {
      key: "skills",
      label: formatPackCounterLabel(pack.skills_count, "Compétence", "Compétences", "Skill", "Skills", isFr),
      count: pack.skills_count,
    },
    {
      key: "gates",
      label: formatPackCounterLabel(pack.gates_count, "Validation", "Validations", "Gate", "Gates", isFr),
      count: pack.gates_count,
    },
    {
      key: "vsm",
      label: formatPackCounterLabel(pack.vsm_count, "Chaîne", "Chaînes", "Stream", "Streams", isFr),
      count: pack.vsm_count,
    },
    {
      key: "workflows",
      label: formatPackCounterLabel(pack.workflows_count, "Processus", "Processus", "Process", "Processes", isFr),
      count: pack.workflows_count,
    },
  ];
  const readableAgents = (pack.agents_slugs ?? []).map((slug) =>
    formatPackAgentDisplayName(slug, isFr),
  );

  return (
    <article
      data-testid={`declarative-pack-card-${pack.slug}`}
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "8px",
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: "16px" }}>{pack.name}</h3>
          <div
            style={{
              fontSize: "12px",
              fontFamily: "var(--font-mono)",
              color: "var(--color-text-secondary)",
              marginTop: "2px",
            }}
          >
            v{pack.version} · {pack.rbac_namespace}
          </div>
        </div>
        <span
          className="rounded px-2 py-0.5 text-xs font-semibold"
          style={{
            backgroundColor: "var(--color-action-primary-subtle)",
            color: "var(--color-primary-cobalt)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {pack.bundle_sha256.slice(0, 10)}
        </span>
      </div>

      <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)" }}>
        {pack.description}
      </p>

      <div
        data-testid={`pack-counters-${pack.slug}`}
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(105px, 1fr))",
          gap: "8px",
        }}
      >
        {counters.map((stat) => (
          <div
            key={stat.key}
            className="rounded border p-2 text-center min-w-0"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--color-primary-cobalt)" }}>
              {stat.count}
            </div>
            <div className="truncate" style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px", color: "var(--color-text-primary)" }}>
          {isFr ? "Connecteurs requis :" : "Required Connectors:"}
        </strong>
        {(pack.connector_health ?? []).map((conn) => {
          const readableName = formatConnectorDisplayName(conn.connector_type, isFr);
          const readableScopes = formatConnectorScopes(conn.required_scopes ?? [], isFr);
          return (
            <div
              key={conn.connector_type}
              data-testid={`pack-${pack.slug}-connector-${conn.connector_type}`}
              data-connector-type={conn.connector_type}
              className="flex flex-wrap items-center justify-between gap-2 rounded border px-2.5 py-1.5 text-xs"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div>
                <span style={{ fontWeight: 600 }}>{readableName}</span>
                {readableScopes ? (
                  <span style={{ marginLeft: "6px", color: "var(--color-text-secondary)" }}>
                    ({readableScopes})
                  </span>
                ) : null}
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
                  {conn.used_for}
                </div>
              </div>
              <span
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: conn.health.ok
                    ? "var(--color-gate-emerald-bg)"
                    : "var(--color-stale-bg)",
                  color: conn.health.ok
                    ? "var(--color-gate-emerald)"
                    : "var(--color-stale-crimson)",
                }}
              >
                {conn.health.ok
                  ? isFr
                    ? `✓ Connecté (${conn.health.latency_ms} ms)`
                    : `✓ Connected (${conn.health.latency_ms} ms)`
                  : conn.health.error_message || (isFr ? "✗ Déconnecté" : "✗ Disconnected")}
              </span>
            </div>
          );
        })}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
          {readableAgents.length <= 1 ? "Agent" : "Agents"} : {readableAgents.join(", ")}
        </div>
        <button
          type="button"
          data-testid={`export-pack-${pack.slug}-zip-btn`}
          onClick={() => onExportZip(pack.id)}
          className="orcia-ds-btn-secondary"
        >
          {isFr ? `Exporter ${pack.name} (.zip)` : `Export ${pack.name} (.zip)`}
        </button>
      </div>
    </article>
  );
}
