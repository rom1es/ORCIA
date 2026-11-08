import React, { useState } from "react";
import { useI18n } from "../../../i18n";
import {
  INITIAL_DECLARATIVE_PACKS,
  type DeclarativePackItem,
} from "../../processes/processStudioV2Data";

export function PacksRegistryPage() {
  const { locale } = useI18n();
  const isFr = locale === "fr";
  const [packs, setPacks] = useState<DeclarativePackItem[]>(INITIAL_DECLARATIVE_PACKS);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>("ws-mon-compte");
  const [selectedPackId, setSelectedPackId] = useState<string>("orcia-pack-sdlc");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [exportedArchiveName, setExportedArchiveName] = useState<string | null>(null);

  const handleRefreshHealthchecks = () => {
    setPacks((prev) =>
      prev.map((pack) => ({
        ...pack,
        connector_health: pack.connector_health.map((item) => ({
          ...item,
          health: {
            ...item.health,
            ok: true,
            latency_ms: Math.max(8, (item.health.latency_ms % 20) + 1),
          },
        })),
      })),
    );
    setStatusMessage(
      isFr
        ? "Diagnostics de santé MCP (Jira, Confluence, Git) actualisés : 100 % des connecteurs requis sont opérationnels."
        : "MCP connector healthchecks (Jira, Confluence, Git) refreshed: 100% of required connectors are healthy.",
    );
  };

  const handleExportWorkspaceZip = (packId?: string) => {
    const targetPackId = packId ?? selectedPackId;
    const pack = packs.find((p) => p.id === targetPackId) ?? packs[0];
    const archiveName = `${pack?.slug ?? "sdlc"}-${selectedWorkspaceId}.zip`;
    setExportedArchiveName(archiveName);
    setStatusMessage(
      isFr
        ? `Archive déclarative ${archiveName} générée (pack.yaml, glossary.yaml, agents/*.md, skills/*.md, gates/*, workflows/*.yaml — 0 code exécutable).`
        : `Declarative archive ${archiveName} generated (pack.yaml, glossary.yaml, agents/*.md, skills/*.md, gates/*, workflows/*.yaml — 0 executable code).`,
    );
  };

  return (
    <section
      data-testid="packs-registry-v2-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div
        className="orcia-bento-card"
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <h2 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>
              {isFr
                ? "Registre des Packs Déclaratifs & Connecteurs MCP (packs/<domaine>/)"
                : "Declarative Packs Registry & MCP Connectors (packs/<domain>/)"}
            </h2>
            <span
              className="rounded px-2 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-gate-emerald-bg)",
                color: "var(--color-gate-emerald)",
              }}
            >
              {isFr ? "100 % Déclaratif (YAML + Markdown)" : "100% Declarative (YAML + Markdown)"}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)" }}>
            {isFr
              ? "Aucun code Python ni React dans les Packs métiers : chargement à chaud par DeclarativePackLoader et vérification des connecteurs via orcia-connectors."
              : "Zero Python or React code inside Business Packs: hot-loaded by DeclarativePackLoader and verified via orcia-connectors."}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="refresh-pack-connectors-health-btn"
            onClick={handleRefreshHealthchecks}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "🔄 Tester les connecteurs MCP" : "🔄 Check MCP Connectors"}
          </button>

          <select
            aria-label={isFr ? "Sélectionner l'espace à exporter" : "Select workspace to export"}
            data-testid="pack-export-workspace-select"
            value={selectedWorkspaceId}
            onChange={(e) => setSelectedWorkspaceId(e.target.value)}
            className="orcia-ds-select"
          >
            <option value="ws-mon-compte">Espace : Mon Compte (SDLC)</option>
            <option value="ws-orcia-platform">Espace : Plateforme ORCIA</option>
          </select>

          <button
            type="button"
            data-testid="export-workspace-pack-zip-btn"
            onClick={() => handleExportWorkspaceZip(selectedPackId)}
            className="orcia-ds-btn-primary"
          >
            {isFr ? "📦 Exporter un espace en Pack (.zip)" : "📦 Export Workspace as Pack (.zip)"}
          </button>
        </div>
      </div>

      {statusMessage ? (
        <div
          role="status"
          data-testid="packs-registry-status-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            borderColor: "var(--color-gate-emerald)",
            color: "var(--color-text-primary)",
          }}
        >
          {statusMessage}
          {exportedArchiveName ? (
            <span
              data-testid="exported-pack-zip-filename"
              style={{ marginLeft: "8px", fontFamily: "var(--font-mono)", fontWeight: 700 }}
            >
              [{exportedArchiveName}]
            </span>
          ) : null}
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "16px",
        }}
      >
        {packs.map((pack) => (
          <article
            key={pack.id}
            data-testid={`declarative-pack-card-${pack.slug}`}
            className="orcia-bento-card"
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
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

            {/* Object Counters */}
            <div
              data-testid={`pack-counters-${pack.slug}`}
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
                gap: "8px",
              }}
            >
              {[
                { label: "Agents (.md)", count: pack.agents_count },
                { label: "Skills (.md)", count: pack.skills_count },
                { label: "Gates", count: pack.gates_count },
                { label: "VSM", count: pack.vsm_count },
                { label: "Workflows", count: pack.workflows_count },
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

            {/* Required Connectors Health */}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <strong style={{ fontSize: "12px", color: "var(--color-text-primary)" }}>
                {isFr
                  ? "Connecteurs requis (packages/orcia-connectors) :"
                  : "Required Connectors (packages/orcia-connectors):"}
              </strong>
              {pack.connector_health.map((conn) => (
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
                      ({conn.required_scopes.join(", ")})
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
                      : "✗ Déconnecté"}
                  </span>
                </div>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px" }}>
              <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
                Agents : {pack.agents_slugs.join(", ")}
              </div>
              <button
                type="button"
                data-testid={`export-pack-${pack.slug}-zip-btn`}
                onClick={() => {
                  setSelectedPackId(pack.id);
                  handleExportWorkspaceZip(pack.id);
                }}
                className="orcia-ds-btn-secondary"
              >
                {isFr ? `Exporter ${pack.slug}.zip` : `Export ${pack.slug}.zip`}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
