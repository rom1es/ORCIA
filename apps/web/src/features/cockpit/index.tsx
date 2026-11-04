import {
  ContextualInfoTriggerButton,
  ProgressiveDay0AccostageBanner,
  StatusBadge,
  StreamlinedCockpitView,
} from "@orcia/ui";
import type { Edge, Node } from "@xyflow/react";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function buildCockpitWorkflowPreviewGraph(): {
  nodes: Node[];
  edges: Edge[];
} {
  return {
    nodes: [
      { id: "intent-router", position: { x: 0, y: 0 }, data: { label: "1. Intent Router" } },
      { id: "query-planner", position: { x: 200, y: 0 }, data: { label: "2. Query Planner & Ontology" } },
      { id: "parallel-fan-out", position: { x: 400, y: 0 }, data: { label: "3. Parallel Fan-Out" } },
      { id: "critical-triage", position: { x: 600, y: 0 }, data: { label: "4. Critical Triage & Axioms" } },
      { id: "profile-synthesizer", position: { x: 800, y: 0 }, data: { label: "5. Profile Adaptive Synthesizer" } },
    ],
    edges: [
      { id: "e-intent-planner", source: "intent-router", target: "query-planner" },
      { id: "e-planner-fanout", source: "query-planner", target: "parallel-fan-out" },
      { id: "e-fanout-triage", source: "parallel-fan-out", target: "critical-triage" },
      { id: "e-triage-synthesizer", source: "critical-triage", target: "profile-synthesizer" },
    ],
  };
}

export function CockpitFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute, openHelpSection } = useShellNavigation();
  const {
    llmTiers,
    orgUnits,
    rbacGrants,
    workspaces,
    datasources,
    workflows,
    packs,
    runs,
    completedSetupStepsCount,
    launchRun,
  } = usePlatformSetup();

  const [selectedWsId, setSelectedWsId] = useState<string>("");
  const [selectedWfKey, setSelectedWfKey] = useState<string>("");
  const [runTitle, setRunTitle] = useState<string>("");

  const isFr = locale === "fr";

  const milestones = [
    {
      index: 1,
      key: "step-llm",
      title: isFr
        ? "1. Modèles IA"
        : "1. AI Models",
      completed: llmTiers.length > 0,
      targetRoute: "/settings",
    },
    {
      index: 2,
      key: "step-iam",
      title: isFr
        ? "2. Structure Organisationnelle & Habilitations"
        : "2. Organization Structure & Permissions",
      completed: orgUnits.length > 0 || rbacGrants.length > 0,
      targetRoute: "/settings",
    },
    {
      index: 3,
      key: "step-workspaces",
      title: isFr
        ? "3. Espaces de Travail"
        : "3. Workspaces",
      completed: workspaces.length > 0,
      targetRoute: "/workspaces",
    },
    {
      index: 4,
      key: "step-connectors",
      title: isFr
        ? "4. Sources Documentaires & Outils"
        : "4. Document Sources & Tools",
      completed: datasources.length > 0,
      targetRoute: "/settings",
    },
    {
      index: 5,
      key: "step-workflows",
      title: isFr
        ? "5. Packs Métiers & Atelier de Processus"
        : "5. Business Packs & Process Studio",
      completed: workflows.length > 0 || packs.length > 0,
      targetRoute: "/processes",
    },
  ];

  const handleLaunchRun = (event: React.FormEvent) => {
    event.preventDefault();
    const targetWs =
      workspaces.find((w) => w.workspaceId === selectedWsId) ?? workspaces[0];
    if (!targetWs || !runTitle.trim()) {
      return;
    }
    const wfKey = selectedWfKey || workflows[0]?.workflowKey || "assistant-agent";
    launchRun({
      workspaceId: targetWs.workspaceId,
      workspaceName: targetWs.name,
      title: runTitle.trim(),
      workflowKey: wfKey,
    });
    setRunTitle("");
  };

  return (
    <div
      data-testid="cockpit-empty-first-panel"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            data-testid="onboarding-progress-badge"
            className="rounded px-2.5 py-0.5 font-mono text-xs font-semibold"
            style={{
              backgroundColor: "var(--color-action-primary-subtle)",
              color: "var(--color-action-primary)",
            }}
          >
            {completedSetupStepsCount}/5
          </span>
          <ContextualInfoTriggerButton
            sectionId="cockpit-decisions"
            label={
              isFr
                ? "Comprendre le fonctionnement du Cockpit et des décisions"
                : "Understand how the Cockpit and decisions work"
            }
            onOpenHelpSection={openHelpSection}
          />
        </div>
      </div>

      <StreamlinedCockpitView
        decisions={runs.map((r) => ({
          decisionId: `dec-${r.runId}`,
          kind: "REVIEW_BRIEFING" as const,
          runId: r.runId,
          stepExecutionId: r.currentStepKey,
          title: r.title,
          summary: `${r.workspaceName} · ${r.currentStepKey}`,
        }))}
        currentUserId="local-operator"
        labels={dictionary.streamlinedCockpit}
        onOpenAssistant={() => navigateToRoute("/assistant")}
        onNavigateModule={(href) => navigateToRoute(href)}
      />

      <ProgressiveDay0AccostageBanner
        completedCount={completedSetupStepsCount}
        totalCount={5}
        milestones={milestones}
        labels={dictionary.progressiveAccostage}
        onNavigateMilestone={(href) => navigateToRoute(href)}
      />

      <section
        data-testid="cockpit-prompt-and-runs-section"
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "14px" }}
      >
        {workspaces.length === 0 ? (
          <div
            data-testid="cockpit-no-workspace-empty-state"
            style={{
              padding: "16px",
              borderRadius: "var(--radius-md)",
              border: "1px dashed var(--color-border)",
              backgroundColor: "var(--color-surface-bg)",
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
                  ? "Aucun Espace de Travail ni processus en cours"
                  : "No Workspace or active process yet"}
              </strong>
              <p
                style={{
                  margin: "4px 0 0 0",
                  fontSize: "13px",
                  color: "var(--color-muted-foreground)",
                }}
              >
                {isFr
                  ? "Créez votre premier Espace de Travail pour lancer vos processus, utiliser Mon Assistant et suivre vos validations."
                  : "Create your first Workspace to run processes, use My Assistant, and track your reviews."}
              </p>
            </div>
            <button
              type="button"
              data-testid="cockpit-go-create-workspace-btn"
              onClick={() => navigateToRoute("/workspaces")}
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
              {isFr ? "+ Créer un Espace de Travail" : "+ Create a Workspace"}
            </button>
          </div>
        ) : (
          <form
            data-testid="cockpit-launch-run-form"
            onSubmit={handleLaunchRun}
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "10px",
              alignItems: "center",
              padding: "12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-bg)",
            }}
          >
            <select
              data-testid="cockpit-select-workspace"
              value={selectedWsId || workspaces[0]?.workspaceId || ""}
              onChange={(e) => setSelectedWsId(e.target.value)}
              style={{
                padding: "7px 10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
              }}
            >
              {workspaces.map((ws) => (
                <option key={ws.workspaceId} value={ws.workspaceId}>
                  {ws.name}
                </option>
              ))}
            </select>

            <select
              data-testid="cockpit-select-workflow"
              value={selectedWfKey || workflows[0]?.workflowKey || "assistant-agent"}
              onChange={(e) => setSelectedWfKey(e.target.value)}
              style={{
                padding: "7px 10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
              }}
            >
              <option value="assistant-agent">
                {isFr ? "Assistant ORCIA (Processus standard)" : "ORCIA Assistant (Standard process)"}
              </option>
              {workflows.map((wf) => (
                <option key={wf.workflowKey} value={wf.workflowKey}>
                  {wf.title} (v{wf.version})
                </option>
              ))}
            </select>

            <input
              type="text"
              data-testid="cockpit-run-title-input"
              value={runTitle}
              onChange={(e) => setRunTitle(e.target.value)}
              placeholder={
                isFr ? "Intitulé de l'exécution..." : "Execution title..."
              }
              style={{
                flex: 1,
                minWidth: "200px",
                padding: "7px 10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
              }}
            />

            <button
              type="submit"
              data-testid="cockpit-launch-run-submit-btn"
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
              {isFr ? "Démarrer le processus" : "Start process"}
            </button>
          </form>
        )}

        {runs.length > 0 && (
          <div
            data-testid="cockpit-active-runs-list"
            style={{ display: "grid", gap: "8px" }}
          >
            {runs.map((run) => (
              <div
                key={run.runId}
                data-testid={`cockpit-run-card-${run.runId}`}
                style={{
                  padding: "10px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface-bg)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <strong>{run.title}</strong>
                  <span
                    style={{
                      marginLeft: "8px",
                      fontSize: "12px",
                      color: "var(--color-muted-foreground)",
                    }}
                  >
                    ({run.workspaceName} · {run.currentStepKey})
                  </span>
                </div>
                <StatusBadge label={run.status} tone="emerald" monospace />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
