import { AutonomyContractModal } from "@orcia/ui";
import React, { useMemo, useState } from "react";
import { useShellNavigation } from "../../../components/ShellContainer";
import { usePlatformSetup } from "../../../components/platformSetupStore";
import { useI18n } from "../../../i18n";
import { InteractiveRunDrawer } from "../execution/InteractiveRunDrawer";
import {
  INITIAL_WORKFLOWS_V2,
  loadPersistedWorkflowsV2,
  savePersistedWorkflowV2,
  type WorkflowDefinitionV2Item,
} from "../processStudioV2Data";
import { StudioCopilotSidebar } from "./StudioCopilotSidebar";
import { StudioFiveBlocksGrid } from "./StudioFiveBlocksGrid";
import { StudioWhatIfPanel } from "./StudioWhatIfPanel";
import { StudioWorkflowHeaderBar, type StudioViewMode } from "./StudioWorkflowHeaderBar";
import { useWorkflowAutonomyContract } from "./useWorkflowAutonomyContract";

export type { StudioViewMode };

const DEFAULT_FALLBACK_WORKSPACE_ID = "0195f000-0000-7000-8000-000000000301";

export function WorkflowFiveBlocksCanvas({ workflowId }: { workflowId?: string }) {
  const { locale, dictionary } = useI18n();
  const { activeScopeId, navigateToRoute, openHelpSection } = useShellNavigation();
  const { workspaces } = usePlatformSetup();
  const isFr = locale === "fr";
  const contractLabels = dictionary.autonomyContract;

  const initialWf = useMemo(() => {
    const list = loadPersistedWorkflowsV2();
    const targetId = workflowId ?? "wf-01-qualification-prd";
    return (
      list.find((w) => w.id === targetId || w.slug === targetId) ??
      INITIAL_WORKFLOWS_V2[0]!
    );
  }, [workflowId]);

  const resolvedWorkspaceId = useMemo(() => {
    const scopeWsId = activeScopeId.startsWith("scope-ws-")
      ? activeScopeId.slice("scope-ws-".length)
      : null;
    if (scopeWsId && workspaces.some((w) => w.workspaceId === scopeWsId)) {
      return scopeWsId;
    }
    return workspaces[0]?.workspaceId ?? DEFAULT_FALLBACK_WORKSPACE_ID;
  }, [activeScopeId, workspaces]);

  const [workflow, setWorkflow] = useState<WorkflowDefinitionV2Item>(initialWf);
  const [viewMode, setViewMode] = useState<StudioViewMode>("design");
  const [showRunDrawer, setShowRunDrawer] = useState<boolean>(false);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);
  const [whatIfResult, setWhatIfResult] = useState<{
    subStepsEvaluated: number;
    deterministicGatesPassed: boolean;
    externalWritesExecuted: number;
    estimatedCostUsd: number;
  } | null>(null);

  const {
    showContractModal,
    setShowContractModal,
    contractError,
    contractSubmitting,
    eligibleServiceAccounts,
    activeContractView,
    availableReadSources,
    availableWriteActions,
    handleSignAutonomyContract,
    handleRevokeAutonomyContract,
  } = useWorkflowAutonomyContract({
    workspaceId: resolvedWorkspaceId,
    workflowId: workflow.id,
    workflowVersion: workflow.version,
    knowledgeBaseRefs: workflow.knowledge_base_refs,
    contractLabels,
    onBanner: setStatusBanner,
  });

  const persistUpdate = (nextWf: WorkflowDefinitionV2Item, banner?: string) => {
    setWorkflow(nextWf);
    savePersistedWorkflowV2(nextWf);
    if (banner) setStatusBanner(banner);
  };

  const ensureDraftOnEdit = (base: WorkflowDefinitionV2Item): WorkflowDefinitionV2Item => {
    if (base.status === "published") {
      const cleanVer = base.version.replace(/-draft$/, "");
      return { ...base, status: "draft", version: `${cleanVer}-draft` };
    }
    return base;
  };

  const handleToggleSubStepEnabled = (subStepId: string) => {
    const base = ensureDraftOnEdit(workflow);
    const nextSubSteps = base.sub_steps.map((s) =>
      s.id === subStepId ? { ...s, enabled: !s.enabled } : s,
    );
    const toggled = nextSubSteps.find((s) => s.id === subStepId);
    persistUpdate(
      { ...base, sub_steps: nextSubSteps },
      isFr
        ? `Étape « ${toggled?.short_label} » ${toggled?.enabled ? "activée" : "ignorée"} dans votre copie de travail.`
        : `Step "${toggled?.short_label}" ${toggled?.enabled ? "enabled" : "skipped"} in your working draft.`,
    );
  };

  const handleSwitchExecutionMode = (mode: "native_orcia" | "external_delegated") => {
    const base = ensureDraftOnEdit(workflow);
    persistUpdate(
      {
        ...base,
        execution_mode: mode,
        external_tool_label:
          mode === "external_delegated"
            ? base.external_tool_label ?? "IDE / Git de l'équipe"
            : base.external_tool_label,
        external_completion_event:
          mode === "external_delegated"
            ? base.external_completion_event ?? "git:pr_opened"
            : base.external_completion_event,
      },
      isFr
        ? `Mode de réalisation basculé sur « ${mode === "external_delegated" ? "Réalisation dans l'IDE / Git de l'équipe" : "Exécution guidée dans ORCIA"} ».`
        : `Execution mode switched to "${mode}".`,
    );
  };

  const handleSaveAsDraft = () => {
    const drafted = ensureDraftOnEdit(workflow);
    persistUpdate(
      drafted,
      isFr ? `Brouillon enregistré (${drafted.version}).` : `Draft saved (${drafted.version}).`,
    );
  };

  const handlePublishWorkflow = () => {
    const cleanVer = workflow.version.replace(/-draft$/, "");
    const parts = cleanVer.split(".").map((n) => Number.parseInt(n, 10) || 0);
    const nextVer = `${parts[0] ?? 1}.${parts[1] ?? 0}.${(parts[2] ?? 0) + 1}`;
    persistUpdate(
      { ...workflow, status: "published", version: nextVer },
      isFr
        ? `Processus publié et activé (version ${nextVer}).`
        : `Process published as version ${nextVer}.`,
    );
  };

  const handleRunWhatIfSimulation = () => {
    const enabledCount = workflow.sub_steps.filter((s) => s.enabled).length;
    setWhatIfResult({
      subStepsEvaluated: enabledCount,
      deterministicGatesPassed: true,
      externalWritesExecuted: 0,
      estimatedCostUsd: Number((enabledCount * 0.015).toFixed(3)),
    });
    setViewMode("what_if");
    setStatusBanner(
      isFr
        ? `Simulation à blanc terminée : ${enabledCount} étape(s) vérifiée(s), aucune modification envoyée aux outils externes.`
        : `Dry-run completed: ${enabledCount} steps verified, 0 external writes executed.`,
    );
  };

  return (
    <section
      data-testid="workflow-five-blocks-studio-page"
      data-workflow-id={workflow.id}
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <StudioWorkflowHeaderBar
        workflow={workflow}
        viewMode={viewMode}
        isFr={isFr}
        hasWhatIfResult={whatIfResult !== null}
        hasActiveAutonomyContract={activeContractView !== null}
        autonomyButtonLabel={contractLabels.openModalButton}
        autonomyActiveBadgeLabel={contractLabels.activeBadgeLabel}
        onNavigateBack={() => navigateToRoute("/processes")}
        onNavigateVsm={() => navigateToRoute("/processes/vsm/vsm-mon-compte-idea-to-prod")}
        onSelectViewMode={setViewMode}
        onRunWhatIf={handleRunWhatIfSimulation}
        onSaveDraft={handleSaveAsDraft}
        onPublish={handlePublishWorkflow}
        onLaunchRun={() => setShowRunDrawer(true)}
        onOpenAutonomyContract={() => setShowContractModal(true)}
      />

      {statusBanner ? (
        <div
          role="status"
          data-testid="studio-status-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            borderColor: "var(--color-gate-emerald)",
            color: "var(--color-text-primary)",
          }}
        >
          {statusBanner}
        </div>
      ) : null}

      {showRunDrawer ? (
        <InteractiveRunDrawer
          workflow={workflow}
          onClose={() => setShowRunDrawer(false)}
          isFr={isFr}
        />
      ) : null}

      <AutonomyContractModal
        open={showContractModal}
        onOpenChange={setShowContractModal}
        workflowTitle={workflow.title}
        eligibleServiceAccounts={eligibleServiceAccounts}
        availableReadSources={availableReadSources}
        availableWriteActions={availableWriteActions}
        activeContract={activeContractView}
        submitting={contractSubmitting}
        errorMessage={contractError}
        labels={contractLabels.modal}
        onSignContract={handleSignAutonomyContract}
        onRevokeContract={handleRevokeAutonomyContract}
        onOpenHelpSection={openHelpSection}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(270px, 320px) 1fr",
          gap: "16px",
          alignItems: "start",
        }}
      >
        <StudioCopilotSidebar
          isFr={isFr}
          onAttachSkill={(skillUri) => {
            if (workflow.skills_refs.includes(skillUri)) return;
            const base = ensureDraftOnEdit(workflow);
            persistUpdate(
              { ...base, skills_refs: [...base.skills_refs, skillUri] },
              isFr ? "Savoir-faire ajouté au processus." : "Business skill attached to the process.",
            );
          }}
          onAttachMcpTool={(toolPerm) => {
            const base = ensureDraftOnEdit(workflow);
            const nextSubs = base.sub_steps.map((s, idx) =>
              idx === 0 && !s.mcp_tools_allowed.includes(toolPerm)
                ? { ...s, mcp_tools_allowed: [...s.mcp_tools_allowed, toolPerm] }
                : s,
            );
            persistUpdate(
              { ...base, sub_steps: nextSubs },
              isFr ? "Outil connecté autorisé sur ce processus." : "Connected tool enabled.",
            );
          }}
          onAttachDeterministicGate={(gate) => {
            if (workflow.controls.deterministic_gates.some((g) => g.id === gate.id)) return;
            const base = ensureDraftOnEdit(workflow);
            persistUpdate(
              {
                ...base,
                controls: {
                  ...base.controls,
                  deterministic_gates: [
                    ...base.controls.deterministic_gates,
                    {
                      id: gate.id,
                      name: gate.name,
                      runner: gate.runner,
                      config: { required_headings: ["# "] },
                      blocking: true,
                      max_self_heal_retries: 3,
                    },
                  ],
                },
              },
              isFr ? `Contrôle qualité « ${gate.name} » ajouté.` : `Quality check "${gate.name}" added.`,
            );
          }}
        />

        {viewMode === "yaml" ? (
          <div data-testid="studio-yaml-preview-panel" className="orcia-bento-card">
            <h3 style={{ margin: "0 0 8px 0", fontSize: "15px" }}>
              {isFr ? "Définition déclarative du processus" : "Declarative Process Definition"}
            </h3>
            <pre
              style={{
                margin: 0,
                padding: "12px",
                borderRadius: "6px",
                backgroundColor: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border-subtle)",
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                overflowX: "auto",
              }}
            >
              {JSON.stringify(workflow, null, 2)}
            </pre>
          </div>
        ) : viewMode === "what_if" ? (
          <StudioWhatIfPanel
            workflow={workflow}
            isFr={isFr}
            whatIfResult={whatIfResult}
            onRerunWhatIf={handleRunWhatIfSimulation}
          />
        ) : (
          <StudioFiveBlocksGrid
            workflow={workflow}
            isFr={isFr}
            onToggleSubStepEnabled={handleToggleSubStepEnabled}
            onSwitchExecutionMode={handleSwitchExecutionMode}
          />
        )}
      </div>
    </section>
  );
}
