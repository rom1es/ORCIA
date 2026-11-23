import { BootstrapOnboardingPanel, type UiBootstrapWorkflowView } from "@orcia/ui";
import React from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { FEATURE_ADMIN_CATALOG_SETTINGS_FR } from "../../i18n/locales/feature_admin_catalog_settings_labels_fr";

export const DEFAULT_BOOTSTRAP_WORKFLOWS: readonly UiBootstrapWorkflowView[] =
  FEATURE_ADMIN_CATALOG_SETTINGS_FR.adminPanel.bootstrapWorkflows;

export function AdminFeaturePanel() {
  const { dictionary } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const adminCopy = dictionary.featureAdminCatalogSettings.adminPanel;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div
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
          <strong style={{ fontSize: "15px" }}>{adminCopy.title}</strong>
          <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {adminCopy.subtitle}
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            data-testid="admin-open-settings-hub-btn"
            onClick={() => navigateToRoute("/settings")}
            style={{
              padding: "7px 12px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              backgroundColor: "var(--color-primary-cobalt)",
              color: "var(--color-primary-foreground)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {adminCopy.openSettingsBtn}
          </button>
          <button
            type="button"
            data-testid="admin-open-wizards-btn"
            onClick={() => navigateToRoute("/wizards")}
            style={{
              padding: "7px 12px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-card)",
              color: "var(--color-foreground)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {adminCopy.openWizardsBtn}
          </button>
        </div>
      </div>

      <div className="orcia-bento-card">
        <BootstrapOnboardingPanel
          activePersona="marc"
          workflows={[...adminCopy.bootstrapWorkflows]}
          labels={dictionary.bootstrapOnboarding}
        />
      </div>
    </div>
  );
}
