import { OrciaAlertBanner } from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { GatesAdaptiveHumanReviewSection } from "./GatesAdaptiveHumanReviewSection";

export function GatesFeaturePanel() {
  const { locale } = useI18n();
  const { workspaces, scopes } = usePlatformSetup();
  const { activeScopeId, navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";
  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);
  const activeWorkspace =
    activeScopeNode?.level === "WORKSPACE"
      ? workspaces.find((w) => w.workspaceId === activeScopeId) ?? workspaces[0]
      : activeScopeNode?.level === "TEAM"
        ? workspaces.find((w) => w.ownerOrgUnitId === activeScopeId) ?? workspaces[0]
        : workspaces[0];

  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  return (
    <div
      data-testid="gates-dedicated-review-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {actionFeedback ? (
        <OrciaAlertBanner
          tone={actionFeedback.startsWith("⚠️") ? "crimson" : "emerald"}
          role={actionFeedback.startsWith("⚠️") ? "alert" : "status"}
          testId="gates-action-feedback-banner"
        >
          {actionFeedback}
        </OrciaAlertBanner>
      ) : null}

      <div
        data-testid="gates-active-scope-badge"
        className="flex flex-wrap items-center justify-between gap-2 rounded border px-3 py-1.5 text-xs"
        style={{
          backgroundColor: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-secondary)",
        }}
      >
        <span>
          {isFr ? "Périmètre de validation actif :" : "Active review scope:"}{" "}
          <strong style={{ color: "var(--color-text-primary)" }}>
            {activeScopeNode?.name ?? (isFr ? "Plateforme Globale ORCIA" : "Global Platform")}
          </strong>
        </span>
      </div>

      {/* Vue Fokus dédiée : Briefing 4 blocs, Validation par découpage, Garde-fou < 15 s & Jira Staged */}
      <GatesAdaptiveHumanReviewSection
        activeWorkspaceId={activeWorkspace?.workspaceId}
        isFr={isFr}
        onFeedback={setActionFeedback}
      />

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
              ? "Aucune étape de validation en attente actuellement"
              : "No review checkpoint currently awaiting approval"}
          </strong>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {isFr
              ? "Les contrôles automatiques, revues croisées et étapes de validation humaine s'affichent ici lors de l'exécution d'un processus."
              : "Automated checks, cross-checked reviews, and human approval steps appear here during process runs."}
          </p>
        </div>
        <button
          type="button"
          data-testid="gates-open-settings-btn"
          onClick={() => navigateToRoute("/processes")}
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
          {isFr ? "Ouvrir Mes Processus" : "Open My Processes"}
        </button>
      </div>
    </div>
  );
}
