import {
  createOrciaApiClient,
  OrciaProblemError,
  type WizardSessionResponse,
} from "@orcia/api-client";
import type { DurableWizardProfileType } from "@orcia/ui";
import { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../components/platformSetupStore";
import { extractWizardStepString } from "../features/bootstrap/WizardsStepForm";
import { useI18n } from "../i18n";
import { formatLocalizedProblemWithCode } from "../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../stores/authSessionStore";

const DEFAULT_WIZARD_SCOPE_ID = "0195f000-0000-7000-8000-000000000301";

export function useWizardsRouteController() {
  const { dictionary, locale, isFr } = useI18n();
  const labels = dictionary.settingsHub.wizardLabels;
  const wizardCopy = dictionary.categoryAControllers.wizards;
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
        formatLocalizedProblemWithCode(err, locale, "ERR_CLIENT_WIZARD_LOAD"),
      );
    }
  }, [apiClient, applySessionToForm, isHydratingAuth, locale, selectedProfile]);

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
          formatLocalizedProblemWithCode(err, locale, "ERR_CLIENT_WIZARD_START"),
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
          workspaceName: workspaceName.trim() || "ORCIA",
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
        formatLocalizedProblemWithCode(err, locale, "ERR_CLIENT_WIZARD_STEP_SAVE"),
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
        formatLocalizedProblemWithCode(err, locale, "ERR_CLIENT_WIZARD_STEP_BACK"),
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
        formatLocalizedProblemWithCode(err, locale, "ERR_CLIENT_WIZARD_DEMO_PROVISION"),
      );
    }
  };

  return {
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
  };
}
