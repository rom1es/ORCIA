import {
  DurableWizardRunnerView,
  OrciaAlertBanner,
  type DurableWizardProfileType,
} from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React from "react";
import {
  WIZARD_STEPS_BY_LOCALE,
  WizardsStepForm,
} from "../features/bootstrap/WizardsStepForm";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";
import { useWizardsRouteController } from "./useWizardsRouteController";

function WizardsRouteComponent() {
  const {
    locale,
    isFr,
    labels,
    wizardCopy,
    activeSession,
    selectedProfile,
    currentStep,
    status,
    isSubmitting,
    errorMessage,
    demoNotice,
    orgUnitName,
    setOrgUnitName,
    workspaceName,
    setWorkspaceName,
    connectorAlias,
    setConnectorAlias,
    connectorUri,
    setConnectorUri,
    primaryModelId,
    setPrimaryModelId,
    handleProfileChange,
    handleCompleteStep,
    handleStepBack,
    handleProvisionDemoWorkspace,
  } = useWizardsRouteController();

  return (
    <div
      data-testid="wizards-route-page"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      {errorMessage ? (
        <OrciaAlertBanner tone="crimson" role="alert" testId="wizards-error-banner">
          {errorMessage}
        </OrciaAlertBanner>
      ) : null}

      {demoNotice ? (
        <OrciaAlertBanner tone="emerald" role="status" testId="wizards-demo-banner">
          {demoNotice}
        </OrciaAlertBanner>
      ) : null}

      <DurableWizardRunnerView
        sessionId={activeSession?.id ?? "wiz-session-pending"}
        wizardType={selectedProfile}
        currentStep={currentStep}
        totalSteps={activeSession?.total_steps ?? 5}
        status={status}
        steps={WIZARD_STEPS_BY_LOCALE[locale]}
        resumedFromCheckpoint={Boolean(
          activeSession &&
            activeSession.status === "IN_PROGRESS" &&
            activeSession.current_step_index > 1,
        )}
        isSubmitting={isSubmitting}
        reciprocityCitationUri={
          activeSession?.rag_reciprocity_verified
            ? "orcia://catalog/workflows/architecture-review"
            : null
        }
        onCompleteStep={(stepNumber) => void handleCompleteStep(stepNumber)}
        onStepBack={() => void handleStepBack()}
        onProvisionDemoWorkspace={() => void handleProvisionDemoWorkspace()}
        headerActions={
          <select
            aria-label={wizardCopy.profileSelectorAriaLabel}
            data-testid="wizard-profile-selector"
            value={selectedProfile}
            onChange={(e) => void handleProfileChange(e.target.value as DurableWizardProfileType)}
            style={{
              padding: "6px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              fontSize: "12px",
            }}
          >
            <option value="sdlc_tech_lead">{labels.profileLabels.sdlc_tech_lead}</option>
            <option value="secops_admin">{labels.profileLabels.secops_admin}</option>
            <option value="ops_manager">{labels.profileLabels.ops_manager}</option>
          </select>
        }
        labels={labels}
      >
        <WizardsStepForm
          currentStep={currentStep}
          status={status}
          isFr={isFr}
          orgUnitName={orgUnitName}
          workspaceName={workspaceName}
          connectorAlias={connectorAlias}
          connectorUri={connectorUri}
          primaryModelId={primaryModelId}
          onOrgUnitNameChange={setOrgUnitName}
          onWorkspaceNameChange={setWorkspaceName}
          onConnectorAliasChange={setConnectorAlias}
          onConnectorUriChange={setConnectorUri}
          onPrimaryModelIdChange={setPrimaryModelId}
        />
      </DurableWizardRunnerView>
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/wizards",
  validateSearch: validateOrciaRouteSearch,
  component: WizardsRouteComponent,
});
