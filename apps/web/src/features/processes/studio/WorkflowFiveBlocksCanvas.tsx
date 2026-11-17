import { AutonomyContractModal, WorkflowTriggersModal } from "@orcia/ui";
import React, { useMemo, useState } from "react";
import { useShellNavigation } from "../../../components/ShellContainer";
import { usePlatformSetup } from "../../../components/platformSetupStore";
import { useI18n } from "../../../i18n";
import { InteractiveRunDrawer } from "../execution/InteractiveRunDrawer";
import { StudioCopilotSidebar } from "./StudioCopilotSidebar";
import {
  attachDeterministicGateToWorkflow,
  attachMcpToolToWorkflow,
  attachSkillToWorkflow,
} from "./studioLabelsAndMappers";
import { useStudioWorkflowController } from "./useStudioWorkflowController";
import { useWorkflowAutonomyContract } from "./useWorkflowAutonomyContract";
import { useWorkflowTriggers } from "./useWorkflowTriggers";
import { WorkflowBlock2ExecutionSection } from "./WorkflowBlock2ExecutionSection";
import {
  WorkflowBlock1ContractSection,
  WorkflowBlocks345Sections,
  WorkflowDeclarativePreviewPanel,
  WorkflowWhatIfSandboxPanel,
} from "./WorkflowBlocks1345Sections";
import {
  WorkflowOrchestrationModeSelector,
  type UiProcessOrchestrationType,
} from "./WorkflowOrchestrationModeSelector";
import {
  WorkflowStudioHeaderBar,
  type StudioViewMode,
} from "./WorkflowStudioHeaderBar";

export type { StudioViewMode };

const DEFAULT_FALLBACK_WORKSPACE_ID = "0192c4e0-0000-7000-8000-000000000201";

export function WorkflowFiveBlocksCanvas({ workflowId }: { workflowId?: string }) {
  const { locale, dictionary } = useI18n();
  const { activeScopeId, navigateToRoute, openHelpSection } = useShellNavigation();
  const { workspaces } = usePlatformSetup();
  const isFr = locale === "fr";
  const modesCopy = dictionary.processOrchestrationModes;
  const contractLabels = dictionary.autonomyContract;
  const triggersLabels = dictionary.workflowTriggers;
  const targetId = workflowId ?? "wf-01-qualification-prd";
  const [showRunDrawer, setShowRunDrawer] = useState<boolean>(false);

  const resolvedWorkspaceId = useMemo(() => {
    const scopeWsId = activeScopeId.startsWith("scope-ws-")
      ? activeScopeId.slice("scope-ws-".length)
      : null;
    if (scopeWsId && workspaces.some((w) => w.workspaceId === scopeWsId)) {
      return scopeWsId;
    }
    return workspaces[0]?.workspaceId ?? DEFAULT_FALLBACK_WORKSPACE_ID;
  }, [activeScopeId, workspaces]);

  const {
    workflow,
    viewMode,
    setViewMode,
    statusBanner,
    setStatusBanner,
    whatIfResult,
    persistUpdate,
    handleSelectOrchestrationType,
    handleChangeGoalObjective,
    handleToggleDelegateAgent,
    handleToggleSubStepEnabled,
    handleSwitchExecutionMode,
    handleSaveAsDraft,
    handlePublishWorkflow,
    handleRunWhatIfSimulation,
  } = useStudioWorkflowController({
    targetId,
    locale,
    modesCopy,
    workspaceId: resolvedWorkspaceId,
  });

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
    onBanner: (msg) =>
      setStatusBanner(msg ? { tone: "success", message: msg } : null),
  });

  const {
    showTriggersModal,
    setShowTriggersModal,
    triggers,
    activeTriggersCount,
    triggersError,
    triggersSubmitting,
    handleCreateTrigger,
    handleUpdateTrigger,
    handleDeleteTrigger,
    handleFireTrigger,
    handleResetCircuit,
  } = useWorkflowTriggers({
    workspaceId: resolvedWorkspaceId,
    workflowId: workflow.id,
    triggersLabels,
    onBanner: (msg) =>
      setStatusBanner(msg ? { tone: "success", message: msg } : null),
  });

  const activeOrchestrationType: UiProcessOrchestrationType =
    workflow.orchestration_type ?? "deterministic_dbos";
  const modeBadgeLabel =
    activeOrchestrationType === "non_deterministic"
      ? modesCopy.goalDrivenBadge
      : modesCopy.milestoneDrivenBadge;

  return (
    <section
      data-testid="workflow-five-blocks-studio-page"
      data-workflow-id={workflow.id}
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <WorkflowStudioHeaderBar
        workflow={workflow}
        viewMode={viewMode}
        isFr={isFr}
        statusBanner={statusBanner}
        hasActiveAutonomyContract={activeContractView !== null}
        autonomyButtonLabel={contractLabels.openModalButton}
        autonomyActiveBadgeLabel={contractLabels.activeBadgeLabel}
        triggersButtonLabel={triggersLabels.openModalButton}
        activeTriggersCount={activeTriggersCount}
        onBackToHub={() => navigateToRoute("/processes")}
        onOpenParentVsm={() => navigateToRoute("/processes/vsm/vsm-mon-compte-idea-to-prod")}
        onSelectViewMode={(mode) => {
          if (mode === "what_if" && !whatIfResult) {
            handleRunWhatIfSimulation();
          } else {
            setViewMode(mode);
          }
        }}
        onSaveAsDraft={handleSaveAsDraft}
        onPublishWorkflow={handlePublishWorkflow}
        onOpenRunDrawer={() => setShowRunDrawer(true)}
        onOpenHelpSection={openHelpSection}
        onOpenAutonomyContract={() => setShowContractModal(true)}
        onOpenTriggers={() => setShowTriggersModal(true)}
      />

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

      <WorkflowTriggersModal
        open={showTriggersModal}
        onOpenChange={setShowTriggersModal}
        workflowTitle={workflow.title}
        hasActiveContract={activeContractView !== null}
        triggers={triggers}
        submitting={triggersSubmitting}
        errorMessage={triggersError}
        labels={triggersLabels.modal}
        onCreateTrigger={handleCreateTrigger}
        onUpdateTrigger={handleUpdateTrigger}
        onDeleteTrigger={handleDeleteTrigger}
        onFireTrigger={handleFireTrigger}
        onResetCircuit={handleResetCircuit}
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
            const nextWf = attachSkillToWorkflow(workflow, skillUri);
            if (!nextWf) return;
            persistUpdate(
              nextWf,
              isFr
                ? "Savoir-faire ajouté au processus."
                : "Business skill attached to the process.",
            );
          }}
          onAttachMcpTool={(toolPerm) => {
            persistUpdate(
              attachMcpToolToWorkflow(workflow, toolPerm),
              isFr
                ? "Outil connecté autorisé sur ce processus."
                : "Connected tool enabled for this process.",
            );
          }}
          onAttachDeterministicGate={(gate) => {
            const nextWf = attachDeterministicGateToWorkflow(workflow, gate);
            if (!nextWf) return;
            persistUpdate(
              nextWf,
              isFr
                ? `Contrôle qualité « ${gate.name} » ajouté.`
                : `Quality check "${gate.name}" added.`,
            );
          }}
        />

        {viewMode === "yaml" ? (
          <WorkflowDeclarativePreviewPanel
            workflow={workflow}
            modeBadgeLabel={modeBadgeLabel}
            isFr={isFr}
          />
        ) : viewMode === "what_if" ? (
          <WorkflowWhatIfSandboxPanel
            workflow={workflow}
            whatIfResult={whatIfResult}
            isFr={isFr}
            onRerun={handleRunWhatIfSimulation}
          />
        ) : (
          <div
            data-testid="studio-five-blocks-canvas"
            style={{ display: "flex", flexDirection: "column", gap: "14px" }}
          >
            <WorkflowOrchestrationModeSelector
              orchestrationType={activeOrchestrationType}
              copy={modesCopy}
              isFr={isFr}
              onSelectOrchestrationType={handleSelectOrchestrationType}
              onOpenHelpSection={openHelpSection}
            />

            <WorkflowBlock1ContractSection workflow={workflow} isFr={isFr} />

            <WorkflowBlock2ExecutionSection
              workflow={workflow}
              goalObjectiveDraft={workflow.reflexive_objective ?? ""}
              goalDelegateAgentsDraft={workflow.allowed_delegate_agents ?? []}
              copy={modesCopy}
              isFr={isFr}
              onChangeGoalObjective={handleChangeGoalObjective}
              onToggleDelegateAgent={handleToggleDelegateAgent}
              onToggleSubStepEnabled={handleToggleSubStepEnabled}
              onSwitchExecutionMode={handleSwitchExecutionMode}
            />

            <WorkflowBlocks345Sections workflow={workflow} isFr={isFr} />
          </div>
        )}
      </div>
    </section>
  );
}
