import React from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function GatesFeaturePanel() {
  const { locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";

  return (
    <div
      data-testid="gates-empty-state-panel"
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
            ? "Aucune Gate de Qualité ou d'Approbation en attente"
            : "No Quality or Approval Gate currently awaiting review"}
        </strong>
        <p
          style={{
            margin: "4px 0 0 0",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
          }}
        >
          {isFr
            ? "Les Gates déterministes, agentiques (5 lentilles) et humaines adaptatives s'affichent lors de l'exécution d'un Workflow Run. Vous pouvez configurer vos règles d'habilitation et vos workflows dans Paramètres."
            : "Deterministic, agentic (5-lens), and adaptive human Gates are displayed during Workflow Run execution. You can configure permission rules and workflows in Settings."}
        </p>
      </div>
      <button
        type="button"
        data-testid="gates-open-settings-btn"
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
        {isFr ? "Paramétrer IAM & Workflows (/settings)" : "Configure IAM & Workflows (/settings)"}
      </button>
    </div>
  );
}
