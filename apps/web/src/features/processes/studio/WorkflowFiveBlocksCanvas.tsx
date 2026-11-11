import React, { useState } from "react";
import { useShellNavigation } from "../../../components/ShellContainer";
import { useI18n } from "../../../i18n";
import { InteractiveRunDrawer } from "../execution/InteractiveRunDrawer";
import { StudioCopilotSidebar } from "./StudioCopilotSidebar";
import {
  attachDeterministicGateToWorkflow,
  attachMcpToolToWorkflow,
  attachSkillToWorkflow,
} from "./studioLabelsAndMappers";
import { useStudioWorkflowController } from "./useStudioWorkflowController";
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

export function WorkflowFiveBlocksCanvas({ workflowId }: { workflowId?: string }) {
  const { locale, dictionary } = useI18n();
  const { navigateToRoute, openHelpSection } = useShellNavigation();
  const isFr = locale === "fr";
  const modesCopy = dictionary.processOrchestrationModes;
  const targetId = workflowId ?? "wf-01-qualification-prd";
  const [showRunDrawer, setShowRunDrawer] = useState<boolean>(false);

  const {
    workflow,
    viewMode,
    setViewMode,
    statusBanner,
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
  } = useStudioWorkflowController({ targetId, locale, modesCopy });

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
      />

      {showRunDrawer ? (
        <InteractiveRunDrawer
          workflow={workflow}
          onClose={() => setShowRunDrawer(false)}
          isFr={isFr}
        />
      ) : null}

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
