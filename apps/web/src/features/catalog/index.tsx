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
  const { catalogItems, datasources } = usePlatformSetup();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";
  const [mcpExposed, setMcpExposed] = useState<boolean>(false);

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

      {/* Banc de Test à Chaud MCP/A2A & Exposition MCP Gouvernée (démarre 100 % vide) */}
      <RemoteServiceTestBenchAndMcpExposureView
        endpointUrl={datasources[0]?.uri ?? ""}
        steps={[]}
        discoveredCapabilities={[]}
        canActivate={datasources.length > 0}
        mcpExposed={mcpExposed}
        exposedToolNames={catalogItems.map((item) => item.resourceId)}
        labels={dictionary.remoteServiceTestBench}
        onToggleMcpExposure={setMcpExposed}
      />
    </div>
  );
}
