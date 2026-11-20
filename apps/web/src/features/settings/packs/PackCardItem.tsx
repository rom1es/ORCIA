import type { DeclarativePackSummaryResponse } from "@orcia/api-client";
import React from "react";

export interface PackCardItemProps {
  readonly pack: DeclarativePackSummaryResponse;
  readonly isFr: boolean;
  readonly onExportZip: (packId: string) => void;
}

export function PackCardItem({ pack, isFr, onExportZip }: PackCardItemProps) {
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
            packs/{pack.slug}/ · v{pack.version} · {pack.rbac_namespace}
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
          SHA256: {pack.bundle_sha256.slice(0, 10)}
        </span>
      </div>

      <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)" }}>
        {pack.description}
      </p>

      <div
        data-testid={`pack-counters-${pack.slug}`}
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
          gap: "8px",
        }}
      >
        {[
          { label: isFr ? "Agents" : "Agents", count: pack.agents_count },
          { label: isFr ? "Compétences" : "Skills", count: pack.skills_count },
          { label: isFr ? "Validations" : "Gates", count: pack.gates_count },
          { label: isFr ? "Chaînes" : "Streams", count: pack.vsm_count },
          { label: isFr ? "Processus" : "Processes", count: pack.workflows_count },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded border p-2 text-center"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--color-primary-cobalt)" }}>
              {stat.count}
            </div>
            <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>{stat.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px", color: "var(--color-text-primary)" }}>
          {isFr ? "Connecteurs requis :" : "Required Connectors:"}
        </strong>
        {(pack.connector_health ?? []).map((conn) => (
          <div
            key={conn.connector_type}
            data-testid={`pack-${pack.slug}-connector-${conn.connector_type}`}
            className="flex flex-wrap items-center justify-between gap-2 rounded border px-2.5 py-1.5 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div>
              <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                {conn.connector_type}
              </span>
              <span style={{ marginLeft: "6px", color: "var(--color-text-secondary)" }}>
                ({(conn.required_scopes ?? []).join(", ")})
              </span>
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
                ? `✓ Connecté (${conn.health.latency_ms} ms)`
                : conn.health.error_message || "✗ Déconnecté"}
            </span>
          </div>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
          Agents : {(pack.agents_slugs ?? []).join(", ")}
        </div>
        <button
          type="button"
          data-testid={`export-pack-${pack.slug}-zip-btn`}
          onClick={() => onExportZip(pack.id)}
          className="orcia-ds-btn-secondary"
        >
          {isFr ? `Exporter ${pack.slug}.zip` : `Export ${pack.slug}.zip`}
        </button>
      </div>
    </article>
  );
}
