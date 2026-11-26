import React from "react";
import { resolveDictionaryForFlag } from "../../../i18n";
import type {
  DeterministicSubStepItem,
  WorkflowDefinitionV2Item,
} from "../processStudioV2Data";
import { buildStatusHumanLabelMap } from "./interactiveRunFormatters";
import { ProcessRunActionBanner } from "./ProcessRunActionBanner";
import { ProcessRunArtifactPane } from "./ProcessRunArtifactPane";
import type { InteractiveProcessDrawerStatus } from "./useInteractiveProcessRunController";

export interface InteractiveRunDeliverableAndHitlPanelsProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly isFr: boolean;
  readonly status: InteractiveProcessDrawerStatus;
  readonly currentSubStep: DeterministicSubStepItem | undefined;
  readonly artifactMarkdown: string;
  readonly isEditingDiff: boolean;
  readonly signedTokenPreview: string | null;
  readonly returnLoopTargetStep: string;
  readonly returnLoopRemarks: string;
  readonly isStartingRun?: boolean;
  readonly isSubmittingDecision?: boolean;
  readonly onChangeArtifactMarkdown: (val: string) => void;
  readonly onSetIsEditingDiff: (editing: boolean) => void;
  readonly onSimulateExternalWebhook: () => void;
  readonly onApproveCurrentSubStep: () => void;
  readonly onAction1AcceptAndSign: () => void;
  readonly onAction2SaveAmendedDiff: () => void;
  readonly onAction3RejectAndLoop: () => void;
  readonly onAction4SuspendSla: () => void;
  readonly onChangeReturnLoopTarget: (step: string) => void;
  readonly onChangeReturnLoopRemarks: (remarks: string) => void;
}

export function InteractiveRunDeliverableAndHitlPanels({
  workflow,
  isFr,
  status,
  currentSubStep,
  artifactMarkdown,
  isEditingDiff,
  signedTokenPreview,
  returnLoopTargetStep,
  returnLoopRemarks,
  isStartingRun = false,
  isSubmittingDecision = false,
  onChangeArtifactMarkdown,
  onSetIsEditingDiff,
  onSimulateExternalWebhook,
  onApproveCurrentSubStep,
  onAction1AcceptAndSign,
  onAction2SaveAmendedDiff,
  onAction3RejectAndLoop,
  onAction4SuspendSla,
  onChangeReturnLoopTarget,
  onChangeReturnLoopRemarks,
}: InteractiveRunDeliverableAndHitlPanelsProps): React.JSX.Element {
  const execCopy = resolveDictionaryForFlag(isFr).processVsmExecutionUi.execution;
  const statusHumanLabel = buildStatusHumanLabelMap(execCopy, 1);

  return (
    <div className="flex flex-col gap-3">
      <ProcessRunActionBanner
        workflow={workflow}
        isFr={isFr}
        status={status}
        statusLabel={statusHumanLabel[status]}
        currentSubStep={currentSubStep}
        iteration={1}
        reentryMode="initial"
        signedTokenPreview={signedTokenPreview}
        returnLoopTargetStep={returnLoopTargetStep}
        returnLoopRemarks={returnLoopRemarks}
        isStartingRun={isStartingRun}
        isSubmittingDecision={isSubmittingDecision}
        isSticky={false}
        onSimulateExternalWebhook={onSimulateExternalWebhook}
        onApproveCurrentSubStep={onApproveCurrentSubStep}
        onAction1AcceptAndSign={onAction1AcceptAndSign}
        onAction3RejectAndLoop={onAction3RejectAndLoop}
        onAction4SuspendSla={onAction4SuspendSla}
        onChangeReturnLoopTarget={onChangeReturnLoopTarget}
        onChangeReturnLoopRemarks={onChangeReturnLoopRemarks}
      />
      <ProcessRunArtifactPane
        workflow={workflow}
        isFr={isFr}
        currentSubStep={currentSubStep}
        artifactMarkdown={artifactMarkdown}
        isEditingDiff={isEditingDiff}
        onChangeArtifactMarkdown={onChangeArtifactMarkdown}
        onSetIsEditingDiff={onSetIsEditingDiff}
        onSaveAmendedDiff={onAction2SaveAmendedDiff}
      />
    </div>
  );
}
