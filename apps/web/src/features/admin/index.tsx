import { BootstrapOnboardingPanel, type UiBootstrapWorkflowView } from "@orcia/ui";
import React from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export const DEFAULT_BOOTSTRAP_WORKFLOWS: UiBootstrapWorkflowView[] = [
  { uri: "orcia://system/bootstrap/init-organization", title: "Configuration de l'organisation", requiredRole: "PLATFORM_ADMIN", scopeLevel: "GLOBAL", gateRules: ["Au moins 2 fournisseurs IA distincts"] },
  { uri: "orcia://system/bootstrap/init-workspace", title: "Création d'un Espace de travail", requiredRole: "TEAM_LEAD", scopeLevel: "TEAM", gateRules: ["Alignement avec le glossaire parent"] },
  { uri: "orcia://system/bootstrap/init-datasource", title: "Connexion d'une source documentaire", requiredRole: "TEAM_LEAD", scopeLevel: "WORKSPACE", gateRules: ["Justification signée par le responsable"] },
  { uri: "orcia://system/bootstrap/init-existing-project", title: "Intégration d'un projet existant", requiredRole: "TEAM_LEAD", scopeLevel: "WORKSPACE", gateRules: ["Analyse préalable de l'existant"] },
  { uri: "orcia://system/bootstrap/init-skill", title: "Ajout d'une compétence métier", requiredRole: "CONTRIBUTOR", scopeLevel: "WORKSPACE", gateRules: ["Structure et paramètres vérifiés"] },
  { uri: "orcia://system/bootstrap/init-user", title: "Configuration de mon profil personnel", requiredRole: "CONTRIBUTOR", scopeLevel: "WORKSPACE", gateRules: ["Identifiants personnels protégés"] },
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
              ? "Administration de la Plateforme & Assistants Guidés"
              : "Platform Administration & Guided Assistants"}
          </strong>
          <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr
              ? "Accédez aux 5 rubriques d'administration (Comptes & Habilitations, Authentification, Modèles IA, Connecteurs, Packs Métiers) ou lancez un assistant pas à pas."
              : "Access the 5 administration sections (Accounts & Permissions, Authentication, AI Models, Connectors, Business Packs) or launch a step-by-step assistant."}
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
            {isFr ? "Ouvrir l'Administration" : "Open Administration"}
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
            {isFr ? "Ouvrir les Assistants Guidés" : "Open Guided Assistants"}
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
