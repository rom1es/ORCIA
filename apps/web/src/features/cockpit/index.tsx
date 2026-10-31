import { ScopedPromptBox, StatusBadge, StreamlinedCockpitView } from "@orcia/ui";
import type { Edge, Node } from "@xyflow/react";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { PlatformOnboardingChecklistCard } from "./PlatformOnboardingChecklistCard";

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
  const { navigateToRoute } = useShellNavigation();
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

  const checklistSteps = [
    {
      id: "step-llm",
      number: 1,
      title: isFr
        ? "1. Modèles IA & Paliers Cognitifs (simple / medium / complex / auto)"
        : "1. AI Models & Cognitive Tiers (simple / medium / complex / auto)",
      done: llmTiers.length > 0,
      countLabel: isFr
        ? `${llmTiers.length} palier(s) configuré(s)`
        : `${llmTiers.length} tier(s) configured`,
      settingsHref: "/settings",
      wizardHref: "/wizards",
      ctaLabel: isFr ? "Paramétrer les modèles IA" : "Configure AI models",
    },
    {
      id: "step-iam",
      number: 2,
      title: isFr
        ? "2. Structure Organisationnelle (BU / Équipe) & Habilitations 6 verbes"
        : "2. Organization Tree (BU / Team) & 6-Verb Permissions",
      done: orgUnits.length > 0 || rbacGrants.length > 0,
      countLabel: isFr
        ? `${orgUnits.length} unité(s) · ${rbacGrants.length} règle(s)`
        : `${orgUnits.length} unit(s) · ${rbacGrants.length} grant(s)`,
      settingsHref: "/settings",
      wizardHref: "/wizards",
      ctaLabel: isFr ? "Configurer l'organisation & IAM" : "Configure Org & IAM",
    },
    {
      id: "step-workspaces",
      number: 3,
      title: isFr
        ? "3. Espaces de Travail (Workspaces)"
        : "3. Solution Workspaces",
      done: workspaces.length > 0,
      countLabel: isFr
        ? `${workspaces.length} espace(s) créé(s)`
        : `${workspaces.length} workspace(s) created`,
      settingsHref: "/workspaces",
      wizardHref: "/wizards",
      ctaLabel: isFr ? "Créer un Workspace" : "Create a Workspace",
    },
    {
      id: "step-connectors",
      number: 4,
      title: isFr
        ? "4. Connecteurs & Sources Documentaires RAG"
        : "4. Connectors & RAG Knowledge Sources",
      done: datasources.length > 0,
      countLabel: isFr
        ? `${datasources.length} connecteur(s) rattaché(s)`
        : `${datasources.length} connector(s) attached`,
      settingsHref: "/settings",
      wizardHref: "/wizards",
      ctaLabel: isFr ? "Ajouter un connecteur" : "Add a connector",
    },
    {
      id: "step-workflows",
      number: 5,
      title: isFr
        ? "5. Packs Métiers & Studio de Workflows"
        : "5. Business Packs & Workflow Studio",
      done: workflows.length > 0 || packs.length > 0,
      countLabel: isFr
        ? `${packs.length} pack(s) · ${workflows.length} workflow(s)`
        : `${packs.length} pack(s) · ${workflows.length} workflow(s)`,
      settingsHref: "/settings",
      wizardHref: "/wizards",
      ctaLabel: isFr ? "Ouvrir le Studio / Packs" : "Open Studio / Packs",
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
        onNavigateModule={(href) => navigateToRoute(href)}
      />

      <PlatformOnboardingChecklistCard
        isFr={isFr}
        completedSetupStepsCount={completedSetupStepsCount}
        checklistSteps={checklistSteps}
        onNavigateToRoute={navigateToRoute}
      />

      <section
        data-testid="cockpit-prompt-and-runs-section"
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "14px" }}
      >
        <ScopedPromptBox
          availableSources={datasources.map((ds) => ({
            sourceUri: ds.uri,
            alias: ds.alias,
            authorized: true,
          }))}
          labels={dictionary.scopedPrompt}
        />

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
                  ? "Aucun Espace de Travail ni Workflow Run actif"
                  : "No Workspace or active Workflow Run yet"}
              </strong>
              <p
                style={{
                  margin: "4px 0 0 0",
                  fontSize: "13px",
                  color: "var(--color-muted-foreground)",
                }}
              >
                {isFr
                  ? "Créez votre premier Espace de Travail pour activer le lancement de Runs supervisés, la boîte de notifications et les Gates."
                  : "Create your first Workspace to enable supervised Workflow Runs, the notification inbox, and Gates."}
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
              <option value="assistant-agent">orcia://system/workflows/assistant-agent</option>
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
                isFr ? "Intitulé du Workflow Run..." : "Workflow Run title..."
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
              {isFr ? "Lancer le Run" : "Launch Run"}
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
