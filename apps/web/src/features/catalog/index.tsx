import {
  CatalogExplorerPanel,
  RemoteServiceTestBenchAndMcpExposureView,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function CatalogFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { catalogItems } = usePlatformSetup();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";
  const [mcpExposed, setMcpExposed] = useState<boolean>(true);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {catalogItems.length === 0 && (
        <div
          data-testid="catalog-setup-guidance-card"
          className="orcia-bento-card"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <strong>
              {isFr
                ? "Aucun Pack ou Workflow personnalisé dans le Catalogue"
                : "No custom Pack or Workflow in the Catalog yet"}
            </strong>
            <p
              style={{
                margin: "4px 0 0 0",
                fontSize: "13px",
                color: "var(--color-muted-foreground)",
              }}
            >
              {isFr
                ? "Activez un Pack métier ou créez un Workflow dans le Studio (/settings) pour peupler le Catalogue fédéré."
                : "Activate a business Pack or create a Workflow in the Studio (/settings) to populate the federated Catalog."}
            </p>
          </div>
          <button
            type="button"
            data-testid="catalog-go-settings-btn"
            onClick={() => navigateToRoute("/settings")}
            style={{
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              backgroundColor: "var(--color-primary-cobalt)",
              color: "var(--color-primary-foreground)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isFr ? "Ouvrir Packs & Studio (/settings)" : "Open Packs & Studio (/settings)"}
          </button>
        </div>
      )}

      <div className="orcia-bento-card">
        <CatalogExplorerPanel
          activePersona="marc"
          items={[...catalogItems]}
          runLockTriplets={[]}
          labels={dictionary.catalogExplorer}
        />
      </div>

      {/* Story 11.3 — Banc de Test à Chaud MCP/A2A 🔌 (4 étapes) & Exposition MCP Gouvernée (/api/v1/mcp) */}
      <RemoteServiceTestBenchAndMcpExposureView
        endpointUrl="https://mcp.entreprise.internal/payments-agent/v1"
        steps={[
          {
            stepNumber: 1,
            stepCode: "1_NETWORK_TLS_ANTI_SSRF",
            status: "PASS",
            detailFr: "DNS & TLS 1.3 vérifiés · 0 IP privée / loopback (Anti-SSRF OK)",
          },
          {
            stepNumber: 2,
            stepCode: "2_AUTHENTICATION",
            status: "WAITING_USER_PASSTHROUGH_TOKEN",
            detailFr: "🟠 En attente de jeton utilisateur (Passthrough OAuth2/PAT non-bloquant)",
          },
          {
            stepNumber: 3,
            stepCode: "3_CONTRACT_DISCOVERY",
            status: "PASS",
            detailFr: "2 outils découverts et qualifiés (READ_ONLY vs WRITE_STAGED_REQUIRED)",
          },
          {
            stepNumber: 4,
            stepCode: "4_HOT_DRY_RUN",
            status: "PASS",
            detailFr: "Dry-Run < 5 s (184 ms, <= 1 MB) tracé dans audit_ledger (ADMIN_CONNECTION_TEST)",
          },
        ]}
        discoveredCapabilities={[
          {
            toolName: "payments.get_tra_score",
            qualification: "READ_ONLY",
            badgeFr: "🟢 Lecture seule (Autorisé en Vitesse 2)",
          },
          {
            toolName: "jira.transition_issue",
            qualification: "WRITE_STAGED_REQUIRED",
            badgeFr: "🟠 Écriture SI (Staged aux Gates uniquement)",
          },
        ]}
        canActivate={true}
        mcpExposed={mcpExposed}
        exposedToolNames={["assistant.ask", "agent.payments_architect.invoke"]}
        labels={dictionary.remoteServiceTestBench}
        onToggleMcpExposure={setMcpExposed}
      />
    </div>
  );
}
