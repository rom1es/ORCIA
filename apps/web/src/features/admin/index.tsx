import { BootstrapOnboardingPanel, type UiBootstrapWorkflowView } from "@orcia/ui";
import React from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export const DEFAULT_BOOTSTRAP_WORKFLOWS: UiBootstrapWorkflowView[] = [
  { uri: "orcia://system/bootstrap/init-organization", title: "init-organization", requiredRole: "PLATFORM_ADMIN", scopeLevel: "GLOBAL", gateRules: ["GATE-LLM-ORTHOGONALITY-MIN-2-FAMILIES"] },
  { uri: "orcia://system/bootstrap/init-workspace", title: "init-workspace", requiredRole: "TEAM_LEAD", scopeLevel: "TEAM", gateRules: ["GATE-ONTOLOGY-L3-NO-UPSTREAM-CONFLICT"] },
  { uri: "orcia://system/bootstrap/init-datasource", title: "init-datasource", requiredRole: "TEAM_LEAD", scopeLevel: "WORKSPACE", gateRules: ["GATE-PERMISSION-BROKER-HUMAN-ANCHOR-SIGNED"] },
  { uri: "orcia://system/bootstrap/init-existing-project", title: "init-existing-project", requiredRole: "TEAM_LEAD", scopeLevel: "WORKSPACE", gateRules: ["GATE-BROWNFIELD-SCAN-VERIFIED"] },
  { uri: "orcia://system/bootstrap/init-skill", title: "init-skill", requiredRole: "CONTRIBUTOR", scopeLevel: "WORKSPACE", gateRules: ["GATE-SKILL-SCHEMA-VALID"] },
  { uri: "orcia://system/bootstrap/init-user", title: "init-user", requiredRole: "CONTRIBUTOR", scopeLevel: "WORKSPACE", gateRules: ["GATE-PASSTHROUGH-AES256GCM-ENCRYPTED"] },
];

export function AdminFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";

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
          <strong style={{ fontSize: "15px" }}>
            {isFr
              ? "Hub de Paramétrage (/settings) & Assistants Guidés (/wizards)"
              : "Settings Hub (/settings) & Guided Wizards (/wizards)"}
          </strong>
          <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr
              ? "Accédez aux 6 onglets de paramétrage (IAM, Modèles IA, Connecteurs, Packs, Studio Workflows, Audit) ou lancez un assistant pas-à-pas."
              : "Access the 6 configuration tabs (IAM, AI Models, Connectors, Packs, Workflow Studio, Audit) or launch a step-by-step wizard."}
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
            {isFr ? "Ouvrir Paramètres (/settings)" : "Open Settings (/settings)"}
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
            {isFr ? "Ouvrir les Assistants (/wizards)" : "Open Wizards (/wizards)"}
          </button>
        </div>
      </div>

      <div className="orcia-bento-card">
        <BootstrapOnboardingPanel
          activePersona="marc"
          workflows={DEFAULT_BOOTSTRAP_WORKFLOWS}
          labels={dictionary.bootstrapOnboarding}
        />
      </div>
    </div>
  );
}
