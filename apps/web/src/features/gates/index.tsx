import { OrciaAlertBanner } from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { resolveGlobalScopeLabel } from "../../components/platformSetupWorkspaces";
import { useShellNavigation } from "../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import { GatesAdaptiveHumanReviewSection } from "./GatesAdaptiveHumanReviewSection";

export function GatesFeaturePanel() {
  const { dictionary, isFr } = useI18n();
  const gatesPanel = dictionary.featureCockpitGates.gates.panel;
  const { workspaces, scopes } = usePlatformSetup();
  const { activeScopeId, navigateToRoute } = useShellNavigation();
  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);
  const resolvedWsId = resolveEffectiveWorkspaceId(activeScopeId, workspaces);
  const activeWorkspace = workspaces.find((w) => w.workspaceId === resolvedWsId) ?? workspaces[0];

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
          {gatesPanel.activeScopeLabel}{" "}
          <strong style={{ color: "var(--color-text-primary)" }}>
            {activeScopeNode?.name ?? resolveGlobalScopeLabel(isFr)}
          </strong>
        </span>
      </div>

      {/* Dedicated Focus View: 4-block briefing, chunk validation, <15s guard & staged Jira */}
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
          <strong>{gatesPanel.emptyTitle}</strong>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {gatesPanel.emptyDescription}
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
          {gatesPanel.openProcessesBtn}
        </button>
      </div>
    </div>
  );
}
