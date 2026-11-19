import {
  createOrciaApiClient,
  OrciaProblemError,
  type WizardSessionResponse,
} from "@orcia/api-client";
import {
  DurableWizardRunnerView,
  OrciaAlertBanner,
  type DurableWizardProfileType,
} from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../components/platformSetupStore";
import {
  extractWizardStepString,
  formatWizardError,
  WIZARD_STEPS_EN,
  WIZARD_STEPS_FR,
  WizardsStepForm,
} from "../features/bootstrap/WizardsStepForm";
import { useI18n } from "../i18n";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

const DEFAULT_WIZARD_SCOPE_ID = "0195f000-0000-7000-8000-000000000301";

function WizardsRouteComponent() {
  const { dictionary, locale } = useI18n();
  const labels = dictionary.settingsHub.wizardLabels;
  const isFr = locale === "fr";
  const accessToken = useAuthSessionStore((s) => s.accessToken);
  const isHydratingAuth = useAuthSessionStore((s) => s.isHydrating);
  const { addOrgUnit, createWorkspace, registerDatasource, upsertLlmTier } = usePlatformSetup();

  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "", locale }), [locale]);

  const [sessions, setSessions] = useState<readonly WizardSessionResponse[]>([]);
  const [selectedProfile, setSelectedProfile] =
    useState<DurableWizardProfileType>("sdlc_tech_lead");
  const [activeSession, setActiveSession] = useState<WizardSessionResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [demoNotice, setDemoNotice] = useState<string | null>(null);

  const [orgUnitName, setOrgUnitName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [connectorAlias, setConnectorAlias] = useState("");
  const [connectorUri, setConnectorUri] = useState("");
  const [primaryModelId, setPrimaryModelId] = useState("");

  const applySessionToForm = useCallback((rec: WizardSessionResponse | null) => {
    setActiveSession(rec);
    if (!rec) return;
    setSelectedProfile(rec.wizard_type);
    const state = rec.state_jsonb;
    setOrgUnitName(extractWizardStepString(state, "step_1", "org_unit_name"));
    setWorkspaceName(extractWizardStepString(state, "step_2", "workspace_name"));
    setConnectorAlias(extractWizardStepString(state, "step_3", "connector_alias"));
    setConnectorUri(extractWizardStepString(state, "step_3", "connector_uri"));
    setPrimaryModelId(extractWizardStepString(state, "step_4", "primary_model_id"));
  }, []);

  const hydrateFromBackend = useCallback(async () => {
    if (isHydratingAuth) return;
    setErrorMessage(null);
    try {
      const res = await apiClient.listWizardSessions();
      setSessions(res.sessions);
      const preferred =
        res.sessions.find((s) => s.wizard_type === selectedProfile) ?? res.sessions[0] ?? null;
      if (preferred) {
        applySessionToForm(preferred);
      }
    } catch (err: unknown) {
      if (err instanceof OrciaProblemError && err.problem.status === 401) return;
      setErrorMessage(
        formatWizardError(
          err,
          isFr
            ? "Impossible de charger vos parcours d'initialisation."
            : "Unable to load your guided setup sessions.",
        ),
      );
    }
  }, [apiClient, applySessionToForm, isFr, isHydratingAuth, selectedProfile]);

  useEffect(() => {
    void hydrateFromBackend();
  }, [accessToken, hydrateFromBackend, isHydratingAuth]);

  const currentStep = activeSession?.current_step_index ?? 1;
  const status = activeSession?.status ?? "IN_PROGRESS";

  const buildStepPayload = (stepNumber: number): Record<string, unknown> => {
    if (stepNumber === 1) return { org_unit_name: orgUnitName.trim() };
    if (stepNumber === 2) return { workspace_name: workspaceName.trim() };
    if (stepNumber === 3) {
      return { connector_alias: connectorAlias.trim(), connector_uri: connectorUri.trim() };
    }
    if (stepNumber === 4) return { primary_model_id: primaryModelId.trim() };
    return { verify_rag_reciprocity: true };
  };

  const ensureSession = async (
    profile: DurableWizardProfileType,
  ): Promise<WizardSessionResponse> => {
    if (activeSession && activeSession.wizard_type === profile) return activeSession;
    const created = await apiClient.startOrResumeWizard({
      wizard_type: profile,
      scope_id: DEFAULT_WIZARD_SCOPE_ID,
    });
    setSessions((prev) => [created, ...prev.filter((s) => s.id !== created.id)]);
    applySessionToForm(created);
    return created;
  };

  const handleProfileChange = async (nextProfile: DurableWizardProfileType) => {
    setSelectedProfile(nextProfile);
    setErrorMessage(null);
    const matching = sessions.find((s) => s.wizard_type === nextProfile) ?? null;
    if (matching) {
      applySessionToForm(matching);
      return;
    }
    setActiveSession(null);
    setOrgUnitName("");
    setWorkspaceName("");
    setConnectorAlias("");
    setConnectorUri("");
    setPrimaryModelId("");
    if (accessToken) {
      try {
        await ensureSession(nextProfile);
      } catch (err: unknown) {
        setErrorMessage(
          formatWizardError(
            err,
            isFr ? "Impossible d'ouvrir ce parcours." : "Unable to start this wizard.",
          ),
        );
      }
    }
  };

  const handleCompleteStep = async (stepNumber: number) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const targetSession = await ensureSession(selectedProfile);
      const updated = await apiClient.saveWizardStep(targetSession.id, {
        step_index: stepNumber,
        step_payload: buildStepPayload(stepNumber),
      });
      setSessions((prev) => [updated, ...prev.filter((s) => s.id !== updated.id)]);
      applySessionToForm(updated);

      if (stepNumber === 1 && orgUnitName.trim()) {
        addOrgUnit({
          name: orgUnitName.trim(),
          slug: orgUnitName.trim().toLowerCase().replace(/\s+/g, "-"),
          level: "TEAM",
          parentId: "scope-global",
        });
      } else if (stepNumber === 2 && workspaceName.trim()) {
        await createWorkspace({
          name: workspaceName.trim(),
          slug: workspaceName.trim().toLowerCase().replace(/\s+/g, "-"),
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
        });
      } else if (stepNumber === 3 && connectorAlias.trim() && connectorUri.trim()) {
        await registerDatasource({
          workspaceName: workspaceName.trim() || "Plateforme Globale ORCIA",
          alias: connectorAlias.trim(),
          scheme: "git",
          uri: connectorUri.trim(),
          executionIdentity: "passthrough",
          freshnessTtlDays: 30,
        });
      } else if (stepNumber === 4 && primaryModelId.trim()) {
        upsertLlmTier({
          tier: "medium",
          primaryModel: primaryModelId.trim(),
          secondaryModel: primaryModelId.trim(),
          modelFamily: "family-a",
          defaultEffort: "balanced",
        });
      }
    } catch (err: unknown) {
      setErrorMessage(
        formatWizardError(
          err,
          isFr ? "Erreur lors de l'enregistrement de l'étape." : "Failed to save wizard step.",
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStepBack = async () => {
    if (!activeSession || currentStep <= 1) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const updated = await apiClient.stepBackWizard(activeSession.id, {
        step_index: currentStep,
        step_payload: buildStepPayload(currentStep),
      });
      setSessions((prev) => [updated, ...prev.filter((s) => s.id !== updated.id)]);
      applySessionToForm(updated);
    } catch (err: unknown) {
      setErrorMessage(
        formatWizardError(
          err,
          isFr
            ? "Impossible de revenir à l'étape précédente."
            : "Unable to step back to the previous step.",
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleProvisionDemoWorkspace = async () => {
    setErrorMessage(null);
    try {
      const demo = await apiClient.provisionWizardDemoWorkspace();
      setDemoNotice(`${demo.workspace_name} (${demo.published_workflow_uri})`);
    } catch (err: unknown) {
      setErrorMessage(
        formatWizardError(
          err,
          isFr
            ? "Impossible de provisionner l'espace de démonstration."
            : "Unable to provision demo workspace.",
        ),
      );
    }
  };

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
        steps={isFr ? WIZARD_STEPS_FR : WIZARD_STEPS_EN}
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
            aria-label={
              isFr
                ? "Choisir un Parcours de Configuration Guidé"
                : "Choose a Guided Setup Journey"
            }
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
